"""Fetch RSS/Atom feeds registered in knowledge_sources (kind=rss) into knowledge_items."""

from __future__ import annotations

import hashlib
import logging
import sys
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path

import ada
import feedparser
import httpx

from ada.config import Settings
from ada.knowledge_embeddings import embed_document_text, float32_list_to_blob
from ada.query_engine import QueryEngine

log = logging.getLogger("ada.ingest.rss")

MAX_EXCERPT_CHARS = 65536


@dataclass
class IngestRssResult:
    feeds_attempted: int = 0
    feeds_ok: int = 0
    items_inserted: int = 0
    items_deduped: int = 0
    errors: list[str] = field(default_factory=list)


def _sha256_hex(parts: list[str]) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8", errors="replace"))
        h.update(b"\n")
    return "sha256:" + h.hexdigest()


def _entry_external_id(entry: dict) -> str:
    eid = (
        str(entry.get("id") or "")
        or str(entry.get("guid") or "")
        or str(entry.get("link") or "")
    ).strip()
    return eid[:500] if eid else ""


def _tags_from_entry(entry: dict) -> list[str]:
    tags: list[str] = ["rss"]
    for t in entry.get("tags", []) or []:
        if isinstance(t, dict):
            term = t.get("term")
            if term:
                tags.append(str(term)[:200])
        elif isinstance(t, str) and t:
            tags.append(t[:200])
    return tags[:48]


async def ingest_rss_feeds(
    qe: QueryEngine,
    *,
    settings: Settings | None = None,
    max_items_per_feed: int = 50,
    max_response_bytes: int = 2_000_000,
    timeout_sec: float = 45.0,
    fetch_text: Callable[[str], Awaitable[str]] | None = None,
) -> IngestRssResult:
    """
    For each knowledge_sources row with kind=rss and non-empty base_url, GET the feed,
    parse with feedparser, insert knowledge_items (dedupe via insert_knowledge_item).

    If ``fetch_text`` is provided, it is called with the feed URL and must return the
    raw XML/string body (for tests without network).
    """
    result = IngestRssResult()
    rows = await qe.list_knowledge_sources(kind="rss")
    candidates = [r for r in rows if str(r.get("base_url") or "").strip()]
    result.feeds_attempted = len(candidates)
    if not candidates:
        return result

    async def _download(url: str) -> str:
        if fetch_text is not None:
            return await fetch_text(url)
        async with httpx.AsyncClient(
            timeout=timeout_sec,
            follow_redirects=True,
            headers={"User-Agent": "ADA-ingest/0.1"},
        ) as client:
            r = await client.get(url)
            r.raise_for_status()
            if len(r.content) > max_response_bytes:
                raise ValueError(
                    f"response exceeds max_response_bytes={max_response_bytes}"
                )
            return r.text

    for src in candidates:
        sid = int(src["id"])
        url = str(src["base_url"]).strip()
        label = src.get("label") or ""
        try:
            body = await _download(url)
            parsed = feedparser.parse(body)
            if getattr(parsed, "bozo", False) and not getattr(parsed, "entries", None):
                raise ValueError(
                    f"feed parse error: {getattr(parsed, 'bozo_exception', 'unknown')}"
                )
            entries = list(getattr(parsed, "entries", []) or [])[:max_items_per_feed]
            result.feeds_ok += 1
            for entry in entries:
                title = str(entry.get("title") or "").strip()
                link = str(entry.get("link") or "").strip()
                summary = (
                    str(entry.get("summary") or entry.get("description") or "")
                    or ""
                ).strip()
                excerpt = f"{title}\n\n{summary}".strip()
                if len(excerpt) > MAX_EXCERPT_CHARS:
                    excerpt = excerpt[: MAX_EXCERPT_CHARS - 1] + "…"
                ext_id = _entry_external_id(entry)
                if not ext_id:
                    ext_id = None
                chash = _sha256_hex([str(sid), title, link, summary[:8000]])
                pub = entry.get("published") or entry.get("updated")
                published_at = str(pub) if pub else None
                tags = _tags_from_entry(entry)
                if label:
                    tags = tags + [f"src:{str(label)[:80]}"]
                    tags = tags[:48]
                ins = await qe.insert_knowledge_item(
                    sid,
                    chash,
                    tags=tags,
                    content_excerpt=excerpt or "(no title)",
                    payload={
                        "feed_url": url,
                        "link": link or None,
                        "title": title or None,
                    },
                    external_id=ext_id,
                    published_at=published_at,
                )
                if ins.inserted:
                    result.items_inserted += 1
                    if (
                        settings is not None
                        and settings.enable_knowledge_embeddings
                        and settings.gemini_api_key.strip()
                    ):
                        blob = "\n".join(
                            x for x in (title, excerpt, link) if x
                        ).strip()
                        if blob:
                            try:
                                vec = await embed_document_text(
                                    settings.gemini_api_key,
                                    blob,
                                    model=settings.knowledge_embedding_model,
                                    output_dimensionality=settings.knowledge_embedding_dim,
                                )
                                await qe.upsert_knowledge_item_embedding(
                                    ins.id,
                                    model=settings.knowledge_embedding_model,
                                    dim=len(vec),
                                    embedding=float32_list_to_blob(vec),
                                    content_hash=chash,
                                )
                            except Exception as ex:
                                log.warning(
                                    "knowledge embed failed item_id=%s: %s",
                                    ins.id,
                                    ex,
                                )
                else:
                    result.items_deduped += 1
        except Exception as e:
            msg = f"feed id={sid} url={url!r}: {e}"
            log.warning("%s", msg)
            result.errors.append(msg)

    return result


async def run_ingest_rss_cli(settings: Settings) -> int:
    """CLI entry: connect DB, ingest all rss knowledge_sources, print summary. Returns exit code."""
    settings.ensure_data_dir()
    schema_path = Path(ada.__path__[0]) / "db" / "schema.sql"
    qe = QueryEngine(
        settings.state_db_path,
        schema_path,
        debounce_ms=settings.persist_debounce_ms,
    )
    await qe.connect()
    try:
        res = await ingest_rss_feeds(
            qe,
            settings=settings,
            max_items_per_feed=settings.ingest_rss_max_items,
            max_response_bytes=settings.ingest_rss_max_response_bytes,
            timeout_sec=settings.ingest_rss_timeout_sec,
        )
        print(
            f"ingest-rss: feeds_attempted={res.feeds_attempted} feeds_ok={res.feeds_ok} "
            f"items_inserted={res.items_inserted} items_deduped={res.items_deduped}"
        )
        for err in res.errors:
            print(err, file=sys.stderr)
        if res.feeds_attempted > 0 and res.feeds_ok == 0:
            return 1
        return 0
    finally:
        await qe.close()
