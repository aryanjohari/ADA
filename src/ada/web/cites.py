"""Durable cite library under memory/cites/ (M07 + M10).

TTL gates refetch freshness only — never deletes cites.
M10: extract_status / kind / chunks; observation head ≠ full disk extract.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from ada.body.vitals import utc_now_iso
from ada.io.atomic import append_jsonl_line, atomic_write_text, cleanup_orphan_tmps
from ada.io.paths import DataPaths, require_ada_data
from ada.web.chunk import STORE_EXTRACT_CHAR_CAP, chunk_text
from ada.web.classify import (
    KNOWLEDGE_OK_STATUSES,
    NON_KNOWLEDGE_KINDS,
    classify_fetch,
)

CITE_ID_RE = re.compile(r"^(?:cite:)?(c_[A-Za-z0-9]+)$")
DEFAULT_TTL_SECONDS = 900
MAX_DIGEST_BODY_CHARS = 50_000
# Observation-sized head kept in excerpts[0] for reversible old clients.
OBSERVATION_HEAD_CAP = 12_000
# Index haystack snippet — title + early chunk text (not full extract).
INDEX_SEARCH_TEXT_CAP = 4_000


def new_cite_id() -> str:
    return f"c_{uuid.uuid4().hex}"


def normalize_cite_id(raw: str) -> str:
    s = (raw or "").strip()
    m = CITE_ID_RE.match(s)
    if not m:
        raise ValueError(f"invalid cite_id: {raw!r}")
    return m.group(1)


def cites_dir(paths: DataPaths) -> Path:
    return paths.cites


def index_path(paths: DataPaths) -> Path:
    return paths.cites / "index.jsonl"


def cite_md_path(paths: DataPaths, cite_id: str) -> Path:
    return paths.cites / f"{cite_id}.md"


def ensure_cite_dirs(paths: DataPaths | None = None) -> DataPaths:
    p = paths or require_ada_data()
    p.ensure_cite_dirs()
    return p


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta = yaml.safe_load(parts[1]) or {}
    if not isinstance(meta, dict):
        meta = {}
    body = parts[2].lstrip("\n")
    return meta, body


def _head_excerpt(full: str, *, cap: int = OBSERVATION_HEAD_CAP) -> tuple[list[str], bool]:
    text = (full or "").strip()
    if not text:
        return [], False
    if len(text) <= cap:
        return [text], False
    return [text[:cap]], True


def _normalize_chunks(chunks: list[Any] | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not chunks:
        return out
    for i, raw in enumerate(chunks):
        if isinstance(raw, dict):
            text = str(raw.get("text") or "").strip()
            if not text:
                continue
            cr = raw.get("char_range")
            if not isinstance(cr, list) or len(cr) != 2:
                cr = [0, len(text)]
            out.append(
                {
                    "i": int(raw.get("i", i)),
                    "text": text,
                    "char_range": [int(cr[0]), int(cr[1])],
                }
            )
        elif isinstance(raw, str) and raw.strip():
            out.append({"i": i, "text": raw.strip(), "char_range": [0, len(raw.strip())]})
    return out


def _search_blob(title: str | None, chunks: list[dict[str, Any]], excerpts: list[str]) -> str:
    bits: list[str] = []
    if title:
        bits.append(str(title))
    for ch in chunks[:6]:
        bits.append(str(ch.get("text") or ""))
    if not chunks and excerpts:
        bits.append(str(excerpts[0]))
    blob = "\n".join(bits)
    if len(blob) > INDEX_SEARCH_TEXT_CAP:
        return blob[:INDEX_SEARCH_TEXT_CAP]
    return blob


def _render_cite_md(record: dict[str, Any], excerpts: list[str]) -> str:
    front = {k: v for k, v in record.items() if k not in ("excerpts", "full_extract")}
    front["excerpts"] = excerpts
    chunks = record.get("chunks")
    if chunks is not None:
        front["chunks"] = chunks
    dumped = yaml.safe_dump(front, sort_keys=False, allow_unicode=True)
    body_bits = [f"# {record.get('title') or record.get('id')}\n"]
    for i, ex in enumerate(excerpts, 1):
        body_bits.append(f"## Excerpt {i}\n\n{ex}\n")
    full = record.get("full_extract")
    if isinstance(full, str) and full.strip() and (
        not excerpts or full.strip() != str(excerpts[0]).strip()
    ):
        body_bits.append(f"## Full extract\n\n{full.strip()}\n")
    return f"---\n{dumped}---\n\n" + "\n".join(body_bits)


def write_cite(
    *,
    url: str,
    final_url: str,
    status: int,
    etag: str | None,
    last_modified: str | None,
    content_hash: str,
    title: str | None,
    excerpts: list[str],
    truncated: bool,
    robots: str,
    allowlist_host: str,
    receipt_id: str,
    cite_id: str | None = None,
    fetched_at: str | None = None,
    paths: DataPaths | None = None,
    save_raw_html: str | None = None,
    kind: str | None = None,
    extract_status: str | None = None,
    extract_ok: bool | None = None,
    extract_source: str | None = None,
    chunks: list[dict[str, Any]] | None = None,
    full_extract: str | None = None,
    knowledge_hidden: bool | None = None,
    campaign_id: str | None = None,
    watch_id: str | None = None,
) -> dict[str, Any]:
    """Atomically write cite md + index line (+ optional scratch raw)."""
    p = ensure_cite_dirs(paths)
    cid = cite_id or new_cite_id()
    ts = fetched_at or utc_now_iso()

    stored_full = (full_extract if full_extract is not None else "").strip()
    if not stored_full and excerpts:
        stored_full = "\n\n".join(str(e) for e in excerpts if e).strip()
    if len(stored_full) > STORE_EXTRACT_CHAR_CAP:
        stored_full = stored_full[:STORE_EXTRACT_CHAR_CAP]

    head, head_trunc = _head_excerpt(stored_full)
    if excerpts and not stored_full:
        head = [str(e) for e in excerpts if e][:1]
        head_trunc = False
    obs_truncated = bool(truncated) or head_trunc

    norm_chunks = _normalize_chunks(chunks)
    if not norm_chunks and stored_full:
        norm_chunks = chunk_text(stored_full)

    # Defaults for callers that predate M10.
    if kind is None and extract_status is None and extract_ok is None:
        kind = "page"
        extract_status = "ok" if stored_full else "empty"
        extract_ok = bool(stored_full)
    else:
        kind = kind or ("page" if stored_full else "empty")
        if extract_status is None:
            extract_status = "ok" if stored_full else "empty"
        if extract_ok is None:
            extract_ok = extract_status in KNOWLEDGE_OK_STATUSES

    if knowledge_hidden is None:
        knowledge_hidden = kind in NON_KNOWLEDGE_KINDS or not extract_ok

    record: dict[str, Any] = {
        "id": cid,
        "url": url,
        "final_url": final_url,
        "fetched_at": ts,
        "status": status,
        "etag": etag,
        "last_modified": last_modified,
        "content_hash": content_hash,
        "title": title,
        "truncated": obs_truncated,
        "robots": robots,
        "allowlist_host": allowlist_host,
        "receipt_id": receipt_id,
        "kind": kind,
        "extract_status": extract_status,
        "extract_ok": bool(extract_ok),
        "extract_source": extract_source or "html",
        "knowledge_hidden": bool(knowledge_hidden),
        "chunks": norm_chunks,
        "extract_chars": len(stored_full),
    }
    if campaign_id:
        record["campaign_id"] = campaign_id
    if watch_id:
        record["watch_id"] = watch_id
    if stored_full and (not head or stored_full != head[0]):
        record["full_extract"] = stored_full

    md = _render_cite_md(record, head)
    path = cite_md_path(p, cid)
    cleanup_orphan_tmps(path.parent, path.name)
    atomic_write_text(path, md)

    if save_raw_html is not None:
        raw_name = content_hash.replace("sha256:", "") + ".html"
        raw_path = p.scratch_web / raw_name
        atomic_write_text(raw_path, save_raw_html)

    index_line = {
        "id": cid,
        "url": url,
        "final_url": final_url,
        "fetched_at": ts,
        "content_hash": content_hash,
        "title": title,
        "truncated": obs_truncated,
        "kind": kind,
        "extract_status": extract_status,
        "extract_ok": bool(extract_ok),
        "knowledge_hidden": bool(knowledge_hidden),
        "search_text": _search_blob(title, norm_chunks, head),
        "campaign_id": campaign_id,
        "watch_id": watch_id,
    }
    append_jsonl_line(index_path(p), index_line)
    out = {**record, "excerpts": head, "path": str(path)}
    out.pop("full_extract", None)
    return out


def update_cite_fetched_at(
    cite_id: str,
    *,
    fetched_at: str | None = None,
    etag: str | None = None,
    last_modified: str | None = None,
    status: int | None = None,
    receipt_id: str | None = None,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    """Refresh freshness metadata on an existing cite (304 / same-hash)."""
    p = ensure_cite_dirs(paths)
    cid = normalize_cite_id(cite_id)
    existing = get_cite(cid, paths=p)
    if not existing.get("ok"):
        return existing
    data = dict(existing["cite"])
    data["fetched_at"] = fetched_at or utc_now_iso()
    if etag is not None:
        data["etag"] = etag
    if last_modified is not None:
        data["last_modified"] = last_modified
    if status is not None:
        data["status"] = status
    if receipt_id is not None:
        data["receipt_id"] = receipt_id
    excerpts = list(data.get("excerpts") or [])
    md = _render_cite_md(data, excerpts)
    path = cite_md_path(p, cid)
    atomic_write_text(path, md)
    append_jsonl_line(
        index_path(p),
        {
            "id": cid,
            "url": data.get("url"),
            "final_url": data.get("final_url"),
            "fetched_at": data["fetched_at"],
            "content_hash": data.get("content_hash"),
            "title": data.get("title"),
            "truncated": data.get("truncated"),
            "kind": data.get("kind"),
            "extract_status": data.get("extract_status"),
            "extract_ok": data.get("extract_ok"),
            "knowledge_hidden": data.get("knowledge_hidden"),
            "search_text": _search_blob(
                data.get("title"),
                _normalize_chunks(data.get("chunks")),
                excerpts,
            ),
            "campaign_id": data.get("campaign_id"),
            "watch_id": data.get("watch_id"),
            "touch": True,
        },
    )
    return {"ok": True, "outcome": "ok", "cite": {**data, "excerpts": excerpts}}


def rewrite_cite_record(
    cite_id: str,
    *,
    updates: dict[str, Any],
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    """Patch cite frontmatter fields and rewrite md + index (tombstone / fallback)."""
    p = ensure_cite_dirs(paths)
    cid = normalize_cite_id(cite_id)
    existing = get_cite(cid, paths=p)
    if not existing.get("ok"):
        return existing
    data = dict(existing["cite"])
    full = updates.pop("full_extract", None)
    if full is not None:
        stored = str(full).strip()
        if len(stored) > STORE_EXTRACT_CHAR_CAP:
            stored = stored[:STORE_EXTRACT_CHAR_CAP]
        head, head_trunc = _head_excerpt(stored)
        data["excerpts"] = head
        data["truncated"] = bool(data.get("truncated")) or head_trunc
        data["chunks"] = chunk_text(stored)
        data["extract_chars"] = len(stored)
        if stored and (not head or stored != head[0]):
            data["full_extract"] = stored
        else:
            data.pop("full_extract", None)
    for key, val in updates.items():
        if val is None and key in data:
            continue
        data[key] = val
    excerpts = list(data.get("excerpts") or [])
    if "chunks" in updates and updates["chunks"] is not None:
        data["chunks"] = _normalize_chunks(updates["chunks"])
    md = _render_cite_md(data, excerpts)
    path = cite_md_path(p, cid)
    atomic_write_text(path, md)
    append_jsonl_line(
        index_path(p),
        {
            "id": cid,
            "url": data.get("url"),
            "final_url": data.get("final_url"),
            "fetched_at": data.get("fetched_at"),
            "content_hash": data.get("content_hash"),
            "title": data.get("title"),
            "truncated": data.get("truncated"),
            "kind": data.get("kind"),
            "extract_status": data.get("extract_status"),
            "extract_ok": data.get("extract_ok"),
            "knowledge_hidden": data.get("knowledge_hidden"),
            "search_text": _search_blob(
                data.get("title"),
                _normalize_chunks(data.get("chunks")),
                excerpts,
            ),
            "campaign_id": data.get("campaign_id"),
            "watch_id": data.get("watch_id"),
            "rewrite": True,
        },
    )
    out_cite = {**data, "excerpts": excerpts}
    out_cite.pop("full_extract", None)
    return {"ok": True, "outcome": "ok", "cite": out_cite}


def apply_feed_item_fallback(
    cite_id: str,
    *,
    summary: str,
    title: str | None = None,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    """Replace js_shell/empty extract with RSS item description (M10 feed fallback)."""
    text = (summary or "").strip()
    if not text:
        return {
            "ok": False,
            "outcome": "error",
            "error": "empty feed summary",
        }
    updates: dict[str, Any] = {
        "full_extract": text,
        "kind": "page",
        "extract_status": "feed_item_fallback",
        "extract_ok": True,
        "extract_source": "feed_item",
        "knowledge_hidden": False,
    }
    if title:
        updates["title"] = title
    result = rewrite_cite_record(cite_id, updates=updates, paths=paths)
    if not result.get("ok"):
        return result
    cite = result["cite"]
    return {
        "ok": True,
        "outcome": "ok",
        **observation_from_cite(cite, cache="feed_fallback"),
    }


def mark_cite_hidden(
    cite_id: str,
    *,
    kind: str | None = None,
    extract_status: str | None = None,
    reason: str | None = None,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    """Tombstone: hide from knowledge search; do not delete (M10)."""
    updates: dict[str, Any] = {
        "knowledge_hidden": True,
        "extract_ok": False,
    }
    if kind:
        updates["kind"] = kind
    if extract_status:
        updates["extract_status"] = extract_status
    if reason:
        updates["tombstone_reason"] = reason
    return rewrite_cite_record(cite_id, updates=updates, paths=paths)


def reclassify_existing_cites(
    *,
    paths: DataPaths | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Mark legacy feed_blob / js_shell cites from on-disk md + scratch (M10 §17.5)."""
    p = ensure_cite_dirs(paths)
    idx = index_path(p)
    if not idx.is_file():
        return {"ok": True, "updated": [], "count": 0, "dry_run": dry_run}

    seen: set[str] = set()
    updated: list[dict[str, Any]] = []
    lines = idx.read_text(encoding="utf-8").splitlines()
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        cid = str(obj.get("id") or "")
        if not cid or cid in seen:
            continue
        seen.add(cid)
        got = get_cite(cid, paths=p)
        if not got.get("ok"):
            continue
        cite = got["cite"]
        url = str(cite.get("url") or "")
        excerpts = list(cite.get("excerpts") or [])
        extract_text = "\n\n".join(str(e) for e in excerpts if e)
        raw = ""
        ch = str(cite.get("content_hash") or "").replace("sha256:", "")
        if ch:
            scratch = p.scratch_web / f"{ch}.html"
            if scratch.is_file():
                try:
                    raw = scratch.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    raw = ""
        if not raw and extract_text:
            # Feed blobs often stored the XML-as-text in excerpts.
            raw = extract_text
        classified = classify_fetch(
            url=url,
            raw_body=raw,
            extracted_text=extract_text,
        )
        # Already correctly marked?
        if (
            cite.get("kind") == classified.kind
            and cite.get("extract_status") == classified.extract_status
            and bool(cite.get("extract_ok")) == classified.extract_ok
            and bool(cite.get("knowledge_hidden")) == (
                classified.kind in NON_KNOWLEDGE_KINDS or not classified.extract_ok
            )
        ):
            continue
        # Only auto-tombstone non-knowledge; still stamp abs_html / ok on good rows.
        hide = classified.kind in NON_KNOWLEDGE_KINDS or not classified.extract_ok
        entry = {
            "cite_id": cid,
            "url": url,
            "kind": classified.kind,
            "extract_status": classified.extract_status,
            "reason": classified.reason,
            "knowledge_hidden": hide,
        }
        if not dry_run:
            rewrite_cite_record(
                cid,
                updates={
                    "kind": classified.kind,
                    "extract_status": classified.extract_status,
                    "extract_ok": classified.extract_ok,
                    "knowledge_hidden": hide,
                    "tombstone_reason": classified.reason if hide else None,
                },
                paths=p,
            )
        updated.append(entry)

    return {
        "ok": True,
        "updated": updated,
        "count": len(updated),
        "dry_run": dry_run,
    }


def get_cite(cite_id: str, *, paths: DataPaths | None = None) -> dict[str, Any]:
    p = ensure_cite_dirs(paths)
    try:
        cid = normalize_cite_id(cite_id)
    except ValueError as exc:
        return {"ok": False, "outcome": "error", "error": str(exc)}
    path = cite_md_path(p, cid)
    if not path.is_file():
        return {
            "ok": False,
            "outcome": "error",
            "error": f"cite not found: {cid}",
            "denied_reason": f"cite not found: {cid}",
        }
    text = path.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(text)
    excerpts = meta.get("excerpts") or []
    if not isinstance(excerpts, list):
        excerpts = [str(excerpts)]
    chunks = _normalize_chunks(meta.get("chunks"))
    # Recover full extract from body section when present.
    full_extract = None
    if "## Full extract" in body:
        part = body.split("## Full extract", 1)[1]
        full_extract = part.lstrip("\n").strip()
    cite = {**meta, "excerpts": excerpts, "chunks": chunks, "path": str(path)}
    if full_extract:
        cite["full_extract"] = full_extract
    # Legacy cites without M10 fields — infer lightly for readers.
    if "extract_ok" not in cite:
        has_text = bool(excerpts and str(excerpts[0]).strip())
        cite.setdefault("kind", "page" if has_text else "empty")
        cite.setdefault("extract_status", "ok" if has_text else "empty")
        cite.setdefault("extract_ok", has_text)
        cite.setdefault(
            "knowledge_hidden",
            cite["kind"] in NON_KNOWLEDGE_KINDS or not has_text,
        )
    return {"ok": True, "outcome": "ok", "cite": cite}


def cite_exists(cite_id: str, *, paths: DataPaths | None = None) -> bool:
    try:
        cid = normalize_cite_id(cite_id)
    except ValueError:
        return False
    p = paths or require_ada_data()
    return cite_md_path(p, cid).is_file()


def _parse_iso(ts: str) -> datetime | None:
    try:
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


def newest_cite_for_url(url: str, *, paths: DataPaths | None = None) -> dict[str, Any] | None:
    """Scan index newest-first for matching url; load full cite."""
    p = ensure_cite_dirs(paths)
    idx = index_path(p)
    if not idx.is_file():
        return None
    lines = idx.read_text(encoding="utf-8").splitlines()
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("url") == url or obj.get("final_url") == url:
            cid = obj.get("id")
            if not cid:
                continue
            got = get_cite(str(cid), paths=p)
            if got.get("ok"):
                return got["cite"]
    return None


def is_fresh(cite: dict[str, Any], *, ttl_seconds: int) -> bool:
    ts = cite.get("fetched_at")
    if not ts:
        return False
    dt = _parse_iso(str(ts))
    if dt is None:
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    age = (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds()
    return age < ttl_seconds


def observation_from_cite(
    cite: dict[str, Any],
    *,
    cache: str,
    receipt_id: str | None = None,
) -> dict[str, Any]:
    """Model-facing observation — never includes HTML; excerpts are observation-capped."""
    raw_excerpts = list(cite.get("excerpts") or [])
    # Cap again in case a legacy cite stored a long blob in excerpts.
    capped: list[str] = []
    budget = OBSERVATION_HEAD_CAP
    for ex in raw_excerpts:
        s = str(ex)
        if budget <= 0:
            break
        if len(s) <= budget:
            capped.append(s)
            budget -= len(s)
        else:
            capped.append(s[:budget])
            budget = 0
            break
    extract_ok = cite.get("extract_ok")
    if extract_ok is None:
        extract_ok = bool(capped and str(capped[0]).strip())
    return {
        "title": cite.get("title"),
        "url": cite.get("url"),
        "final_url": cite.get("final_url"),
        "cite_id": cite.get("id"),
        "excerpts": capped,
        "truncated": bool(cite.get("truncated")),
        "cache": cache,
        "receipt_id": receipt_id or cite.get("receipt_id"),
        "fetched_at": cite.get("fetched_at"),
        "content_hash": cite.get("content_hash"),
        "kind": cite.get("kind") or "page",
        "extract_status": cite.get("extract_status")
        or ("ok" if extract_ok else "empty"),
        "extract_ok": bool(extract_ok),
        "extract_source": cite.get("extract_source") or "html",
        "extract_chars": cite.get("extract_chars"),
    }


# Ultra-common function words — dropped so they don't force false misses.
_QUERY_STOPWORDS = frozenset({"the", "a", "an", "of", "and"})
# Genre words humans add when naming a work ("ReAct paper") — not required in title/url.
_QUERY_GENRE_STOP = frozenset({"paper", "article", "pdf"})
_PUNCT_TO_SPACE = re.compile(r"[^\w]+", re.UNICODE)


def _normalize_query_tokens(query: str) -> list[str]:
    """Lowercase, punctuation→space, drop stopwords + genre words. Token AND match."""
    raw = (query or "").strip().lower()
    if not raw:
        return []
    spaced = _PUNCT_TO_SPACE.sub(" ", raw)
    tokens: list[str] = []
    for tok in spaced.split():
        if not tok:
            continue
        if tok in _QUERY_STOPWORDS or tok in _QUERY_GENRE_STOP:
            continue
        tokens.append(tok)
    return tokens


def _is_knowledge_hit(obj: dict[str, Any]) -> bool:
    if obj.get("knowledge_hidden") is True:
        return False
    kind = str(obj.get("kind") or "")
    if kind in NON_KNOWLEDGE_KINDS:
        return False
    if obj.get("extract_ok") is False:
        return False
    return True


def search_cites(
    query: str,
    *,
    max_hits: int = 10,
    paths: DataPaths | None = None,
    include_non_knowledge: bool = False,
) -> dict[str, Any]:
    """Grep-first search over cite index + chunk/extract text. No network.

    Matcher: tokenized AND over id/title/url/search_text (and loaded chunks on miss).
    Default excludes js_shell / feed_blob / empty / knowledge_hidden (M10 F1/F6).
    Dedupes by cite_id keeping the newest index line.
    """
    p = ensure_cite_dirs(paths)
    if not (query or "").strip():
        return {
            "ok": False,
            "outcome": "error",
            "error": "query required",
            "denied_reason": "query required",
            "hits": [],
            "count": 0,
        }
    tokens = _normalize_query_tokens(query)
    if not tokens:
        return {
            "ok": True,
            "outcome": "ok",
            "query": query,
            "hits": [],
            "count": 0,
        }
    limit = max(1, min(int(max_hits or 10), 50))
    idx = index_path(p)
    if not idx.is_file():
        return {"ok": True, "outcome": "ok", "hits": [], "count": 0, "query": query}

    seen: set[str] = set()
    hits: list[dict[str, Any]] = []
    lines = idx.read_text(encoding="utf-8").splitlines()
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        cid = str(obj.get("id") or "")
        if not cid or cid in seen:
            continue
        if not include_non_knowledge and not _is_knowledge_hit(obj):
            # Legacy index rows lack kind — load cite once to decide.
            if "kind" not in obj and "knowledge_hidden" not in obj and "extract_ok" not in obj:
                got = get_cite(cid, paths=p)
                if got.get("ok"):
                    cite = got["cite"]
                    obj = {
                        **obj,
                        "kind": cite.get("kind"),
                        "extract_ok": cite.get("extract_ok"),
                        "knowledge_hidden": cite.get("knowledge_hidden"),
                        "extract_status": cite.get("extract_status"),
                        "search_text": _search_blob(
                            cite.get("title"),
                            _normalize_chunks(cite.get("chunks")),
                            list(cite.get("excerpts") or []),
                        ),
                    }
                    if not _is_knowledge_hit(obj):
                        seen.add(cid)
                        continue
                else:
                    seen.add(cid)
                    continue
            else:
                seen.add(cid)
                continue
        hay = " ".join(
            str(x or "")
            for x in (
                cid,
                obj.get("title"),
                obj.get("url"),
                obj.get("final_url"),
                obj.get("search_text"),
            )
        ).lower()
        if not all(tok in hay for tok in tokens):
            # Fall through: load cite chunks if index search_text missing/stale.
            if not obj.get("search_text"):
                got = get_cite(cid, paths=p)
                if got.get("ok"):
                    cite = got["cite"]
                    hay2 = " ".join(
                        str(x or "")
                        for x in (
                            cid,
                            cite.get("title"),
                            cite.get("url"),
                            cite.get("final_url"),
                            _search_blob(
                                cite.get("title"),
                                _normalize_chunks(cite.get("chunks")),
                                list(cite.get("excerpts") or []),
                            ),
                        )
                    ).lower()
                    if not all(tok in hay2 for tok in tokens):
                        continue
                else:
                    continue
            else:
                continue
        seen.add(cid)
        hits.append(
            {
                "cite_id": cid,
                "title": obj.get("title"),
                "url": obj.get("url"),
                "final_url": obj.get("final_url"),
                "fetched_at": obj.get("fetched_at"),
                "content_hash": obj.get("content_hash"),
                "truncated": bool(obj.get("truncated")),
                "kind": obj.get("kind"),
                "extract_status": obj.get("extract_status"),
                "extract_ok": obj.get("extract_ok"),
            }
        )
        if len(hits) >= limit:
            break

    return {
        "ok": True,
        "outcome": "ok",
        "query": query,
        "hits": hits,
        "count": len(hits),
    }


def cite_heads_since(
    *,
    paths: DataPaths | None = None,
    since: str | None = None,
    max_heads: int = 20,
    first_chunk_chars: int = 400,
) -> list[dict[str, Any]]:
    """New/updated cite heads for Dream delta (M10) — not full extracts."""
    p = ensure_cite_dirs(paths)
    idx = index_path(p)
    if not idx.is_file():
        return []
    since_dt = _parse_iso(since) if since else None
    seen: set[str] = set()
    heads: list[dict[str, Any]] = []
    lines = idx.read_text(encoding="utf-8").splitlines()
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        cid = str(obj.get("id") or "")
        if not cid or cid in seen:
            continue
        seen.add(cid)
        fetched = obj.get("fetched_at")
        if since_dt and fetched:
            ft = _parse_iso(str(fetched))
            if ft is not None and ft <= since_dt:
                continue
        got = get_cite(cid, paths=p)
        if not got.get("ok"):
            continue
        cite = got["cite"]
        chunks = _normalize_chunks(cite.get("chunks"))
        first = ""
        # Only attach chunk text when the extract is usable knowledge (M10).
        if cite.get("extract_ok"):
            if chunks:
                first = str(chunks[0].get("text") or "")[:first_chunk_chars]
            elif cite.get("excerpts"):
                first = str(cite["excerpts"][0])[:first_chunk_chars]
        heads.append(
            {
                "id": cid,
                "title": cite.get("title"),
                "url": cite.get("url"),
                "extract_status": cite.get("extract_status"),
                "extract_ok": cite.get("extract_ok"),
                "kind": cite.get("kind"),
                "campaign_id": cite.get("campaign_id") or obj.get("campaign_id"),
                "watch_id": cite.get("watch_id") or obj.get("watch_id"),
                "first_chunk": first,
                "fetched_at": cite.get("fetched_at"),
            }
        )
        if len(heads) >= max_heads:
            break
    return heads
