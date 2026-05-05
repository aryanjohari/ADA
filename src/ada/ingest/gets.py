"""GETS public tender index (ExternalIndex.htm) → ingest_raw + knowledge_items."""

from __future__ import annotations

import hashlib
import logging
import sys
import re
from dataclasses import dataclass, field
from typing import Any

import httpx

from ada.config import Settings
from ada.ingest.common import assert_gov_api_url_allowed
from ada.query_engine import QueryEngine
from ada.profile_runtime import enforce_profile_identity

log = logging.getLogger("ada.ingest.gets")

# RFx detail links on the public index
_DETAIL_LINK = re.compile(
    r'href="([^"]*ExternalTenderDetails\.htm\?id=(\d+)[^"]*)"[^>]*>([^<]*)</a>',
    re.IGNORECASE,
)


@dataclass
class IngestGetsResult:
    job_id: int
    raw_row_id: int
    items_inserted: int = 0
    items_deduped: int = 0
    tenders_parsed: int = 0
    error: str = ""
    errors: list[str] = field(default_factory=list)


def parse_gets_index_html(html: str) -> list[dict[str, str]]:
    """Extract public tender rows from GETS ExternalIndex HTML."""
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for m in _DETAIL_LINK.finditer(html):
        href, tid, title = m.group(1), m.group(2), (m.group(3) or "").strip()
        if tid in seen:
            continue
        seen.add(tid)
        if not title:
            title = f"Tender {tid}"
        rows.append(
            {
                "rfx_id": tid,
                "title": title,
                "detail_href": href.strip(),
            }
        )
    return rows


def _sha256_hex(parts: list[str]) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8", errors="replace"))
        h.update(b"\n")
    return "sha256:" + h.hexdigest()


async def ingest_gets_index(
    qe: QueryEngine,
    settings: Settings,
    *,
    idempotency_key: str | None = None,
    fetch_text: Any | None = None,
    mission_id: int | None = None,
) -> IngestGetsResult:
    """
    Fetch public index HTML, store raw snapshot, insert one knowledge_item per RFx id.
    Full tender documents require RealMe — not fetched here.
    """
    url = settings.ada_gets_poll_url.strip()
    if not url:
        return IngestGetsResult(0, 0, error="ADA_GETS_POLL_URL empty")

    assert_gov_api_url_allowed(url, settings.gov_api_host_allowlist)

    sid = await qe.ensure_knowledge_source(
        "api",
        label="gets_public_index",
        base_url=url,
        config_json={
            "maps_to": "knowledge_items.procurement",
            "region": "NZ",
            "trust_tier": "procurement",
            "source": "gets_public_index",
        },
        mission_id=mission_id,
    )

    job_id = 0
    try:
        job_id = await qe.create_ingest_job(
            "gov_gets",
            {"url": url},
            idempotency_key=idempotency_key,
        )
        await qe.update_ingest_job(job_id, status="running", set_started=True)

        if fetch_text is not None:
            html = await fetch_text(url)
        else:
            async with httpx.AsyncClient(
                timeout=settings.ingest_rss_timeout_sec,
                follow_redirects=True,
                headers={"User-Agent": "ADA-ingest/0.1"},
            ) as client:
                r = await client.get(url)
                r.raise_for_status()
                if len(r.content) > settings.ingest_rss_max_response_bytes:
                    raise ValueError(
                        f"response exceeds max bytes={settings.ingest_rss_max_response_bytes}"
                    )
                html = r.text

        raw_id = await qe.insert_ingest_raw(
            ingest_job_id=job_id,
            source="gets_external_index",
            uri=url,
            body=html,
            meta_json={"parser": "detail_link_v1"},
        )

        tenders = parse_gets_index_html(html)
        result = IngestGetsResult(
            job_id=job_id, raw_row_id=raw_id, tenders_parsed=len(tenders)
        )

        for t in tenders:
            ext = f"gets:{t['rfx_id']}"
            excerpt = f"{t['title']}\n\nRFx {t['rfx_id']} (public index metadata only)"
            chash = _sha256_hex([str(sid), ext, t["title"]])
            payload: dict[str, Any] = {
                "gets": True,
                "rfx_id": t["rfx_id"],
                "title": t["title"],
                "detail_href": t["detail_href"],
                "index_url": url,
            }
            tags = [
                "procurement",
                "gets",
                "region:NZ",
                "maps_to:knowledge_items.procurement",
            ]
            ins = await qe.insert_knowledge_item(
                sid,
                chash,
                tags=tags,
                content_excerpt=excerpt,
                payload=payload,
                external_id=ext,
                relevance_score=1.0,
            )
            if ins.inserted:
                result.items_inserted += 1
            else:
                result.items_deduped += 1

        await qe.update_ingest_job(job_id, status="completed", set_completed=True)
        return result
    except Exception as e:
        msg = str(e)
        log.warning("ingest gets: %s", msg)
        result = IngestGetsResult(job_id=job_id, raw_row_id=0, error=msg)
        result.errors.append(msg)
        if job_id:
            await qe.update_ingest_job(
                job_id,
                status="failed",
                error=msg[:2000],
                set_completed=True,
            )
        return result


async def run_ingest_gets_cli(
    settings: Settings, *, mission_slug: str | None = None
) -> int:
    from pathlib import Path
    from datetime import datetime, timezone

    import ada

    settings.ensure_data_dir()
    schema_path = Path(ada.__path__[0]) / "db" / "schema.sql"
    qe = QueryEngine(
        settings.state_db_path,
        schema_path,
        debounce_ms=settings.persist_debounce_ms,
    )
    await qe.connect()
    await enforce_profile_identity(qe, settings)
    mid: int | None = None
    if mission_slug is not None and str(mission_slug).strip():
        m = await qe.get_mission_by_slug(str(mission_slug).strip())
        if m is None:
            print(
                f"ingest-gets: unknown mission slug {str(mission_slug).strip()!r}",
                file=sys.stderr,
            )
            return 2
        mid = int(m["id"])
    try:
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        res = await ingest_gets_index(
            qe,
            settings,
            idempotency_key=f"gets-{day}",
            mission_id=mid,
        )
        if res.error and not res.raw_row_id:
            print(f"ingest-gets: error: {res.error}", flush=True)
            return 1
        print(
            f"ingest-gets: job_id={res.job_id} raw_id={res.raw_row_id} "
            f"tenders={res.tenders_parsed} inserted={res.items_inserted} "
            f"deduped={res.items_deduped}",
            flush=True,
        )
        return 0 if not res.error else 1
    finally:
        await qe.close()
