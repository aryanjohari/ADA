"""Bounded brand ingest: homepage + key service/location pages."""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse, urlunparse

import ada
import httpx

from ada.config import Settings
from ada.query_engine import QueryEngine
from ada.profile_runtime import enforce_profile_identity

log = logging.getLogger("ada.ingest.brand")

_HREF_RE = re.compile(r'href=["\']([^"\']+)["\']', re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_SERVICE_HINTS = ("service", "services", "location", "locations", "about", "contact")


class BrandIngestError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass
class IngestBrandResult:
    site_url: str
    source_id: int = 0
    candidate_urls: list[str] = field(default_factory=list)
    pages_fetched: int = 0
    items_inserted: int = 0
    items_deduped: int = 0
    errors: list[dict[str, str]] = field(default_factory=list)
    dry_run: bool = False


def _sha256_hex(parts: list[str]) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8", errors="replace"))
        h.update(b"\n")
    return "sha256:" + h.hexdigest()


def _canonical_url(url: str) -> str:
    p = urlparse(url.strip())
    path = p.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
    return urlunparse((p.scheme.lower(), p.netloc.lower(), path, "", p.query, ""))


def _validate_site_url(site_url: str) -> str:
    raw = site_url.strip()
    if not raw:
        raise BrandIngestError("invalid_url", "site_url is required")
    p = urlparse(raw)
    if p.scheme not in ("http", "https") or not p.hostname:
        raise BrandIngestError("invalid_url", "site_url must be http(s) with hostname")
    return _canonical_url(raw)


def _extract_links(base_url: str, html: str, *, max_urls: int) -> list[str]:
    base = urlparse(base_url)
    picks: list[str] = [base_url]
    seen = {base_url}
    hinted: list[str] = []
    fallback: list[str] = []
    for m in _HREF_RE.finditer(html):
        href = (m.group(1) or "").strip()
        if not href or href.startswith("#"):
            continue
        full = _canonical_url(urljoin(base_url, href))
        p = urlparse(full)
        if p.scheme not in ("http", "https") or p.hostname != base.hostname:
            continue
        if full in seen:
            continue
        seen.add(full)
        lpath = (p.path or "").lower()
        if any(tok in lpath for tok in _SERVICE_HINTS):
            hinted.append(full)
        else:
            fallback.append(full)
    for seq in (hinted, fallback):
        for u in seq:
            picks.append(u)
            if len(picks) >= max_urls:
                return picks
    return picks


def _html_to_text(html: str) -> str:
    no_tags = _TAG_RE.sub(" ", html)
    return _WS_RE.sub(" ", no_tags).strip()


async def ingest_brand_site(
    qe: QueryEngine,
    settings: Settings,
    *,
    site_url: str,
    max_urls: int,
    dry_run: bool = False,
    fetch_text: Any | None = None,
) -> IngestBrandResult:
    site = _validate_site_url(site_url)
    cap = max(1, min(max_urls, settings.brand_ingest_max_urls))
    timeout_sec = settings.brand_ingest_timeout_sec
    max_bytes = settings.brand_ingest_max_response_bytes
    result = IngestBrandResult(site_url=site, dry_run=dry_run)

    async def _download(url: str) -> str:
        if fetch_text is not None:
            body = await fetch_text(url)
            if len(body.encode("utf-8", errors="replace")) > max_bytes:
                raise BrandIngestError("response_too_large", "response exceeds max bytes")
            return body
        async with httpx.AsyncClient(timeout=timeout_sec, follow_redirects=True) as client:
            r = await client.get(url, headers={"User-Agent": "ADA-brand-ingest/0.1"})
            r.raise_for_status()
            if len(r.content) > max_bytes:
                raise BrandIngestError("response_too_large", "response exceeds max bytes")
            return r.text

    homepage = await _download(site)
    result.candidate_urls = _extract_links(site, homepage, max_urls=cap)
    source_id = await qe.ensure_knowledge_source(
        "brand",
        label=f"brand:{urlparse(site).hostname}",
        base_url=site,
        config_json={
            "source_kind": "brand",
            "maps_to": "knowledge_items.brand",
            "crawl_mode": "bounded",
        },
    )
    result.source_id = source_id
    fetched_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    for idx, url in enumerate(result.candidate_urls):
        try:
            html = homepage if idx == 0 else await _download(url)
            text = _html_to_text(html)
            if not text:
                continue
            result.pages_fetched += 1
            payload = {
                "source_kind": "brand",
                "source_url": _canonical_url(url),
                "site_url": site,
                "ingested_at": fetched_at,
                "extract_ready": {"kind": "graph_lite_text", "version": "v1"},
            }
            chash = _sha256_hex([str(source_id), payload["source_url"], text[:12000]])
            if dry_run:
                continue
            ins = await qe.insert_knowledge_item(
                source_id,
                chash,
                tags=["brand", "site_ingest", "source_kind:brand"],
                content_excerpt=text[:65000],
                payload=payload,
                external_id=f"brand:{payload['source_url']}",
                relevance_score=1.0,
            )
            if ins.inserted:
                result.items_inserted += 1
            else:
                result.items_deduped += 1
        except Exception as e:
            code = e.code if isinstance(e, BrandIngestError) else "fetch_error"
            result.errors.append({"code": str(code), "message": str(e), "url": url})
    return result


async def run_ingest_brand_cli(
    settings: Settings,
    *,
    site_url: str | None,
    max_urls: int | None,
    dry_run: bool,
) -> int:
    url = (site_url or settings.brand_site_url or "").strip()
    if not url:
        print("ingest-brand: site URL required (flag or ADA_BRAND_SITE_URL)")
        return 2
    schema_path = Path(ada.__path__[0]) / "db" / "schema.sql"
    qe = QueryEngine(
        settings.state_db_path,
        schema_path,
        debounce_ms=settings.persist_debounce_ms,
    )
    await qe.connect()
    await enforce_profile_identity(qe, settings)
    try:
        try:
            res = await ingest_brand_site(
                qe,
                settings,
                site_url=url,
                max_urls=max_urls or settings.brand_ingest_max_urls,
                dry_run=dry_run,
            )
        except BrandIngestError as e:
            print(f"ingest-brand: error code={e.code} message={e}")
            return 2
        print(
            f"ingest-brand: dry_run={res.dry_run} source_id={res.source_id} "
            f"candidates={len(res.candidate_urls)} fetched={res.pages_fetched} "
            f"inserted={res.items_inserted} deduped={res.items_deduped}"
        )
        for err in res.errors:
            print(
                f"ingest-brand:error code={err['code']} url={err.get('url','')} msg={err['message']}"
            )
        return 0 if not res.errors else 1
    finally:
        await qe.close()
