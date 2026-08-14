"""Durable cite library under memory/cites/ (M07).

TTL gates refetch freshness only — never deletes cites.
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

CITE_ID_RE = re.compile(r"^(?:cite:)?(c_[A-Za-z0-9]+)$")
DEFAULT_TTL_SECONDS = 900
MAX_DIGEST_BODY_CHARS = 50_000


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


def _render_cite_md(record: dict[str, Any], excerpts: list[str]) -> str:
    front = {k: v for k, v in record.items() if k != "excerpts"}
    # Keep excerpts in frontmatter as list for machine read
    front["excerpts"] = excerpts
    dumped = yaml.safe_dump(front, sort_keys=False, allow_unicode=True)
    body_bits = [f"# {record.get('title') or record.get('id')}\n"]
    for i, ex in enumerate(excerpts, 1):
        body_bits.append(f"## Excerpt {i}\n\n{ex}\n")
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
) -> dict[str, Any]:
    """Atomically write cite md + index line (+ optional scratch raw)."""
    p = ensure_cite_dirs(paths)
    cid = cite_id or new_cite_id()
    ts = fetched_at or utc_now_iso()
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
        "truncated": truncated,
        "robots": robots,
        "allowlist_host": allowlist_host,
        "receipt_id": receipt_id,
    }
    md = _render_cite_md(record, excerpts)
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
        "truncated": truncated,
    }
    append_jsonl_line(index_path(p), index_line)
    return {**record, "excerpts": excerpts, "path": str(path)}


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
            "touch": True,
        },
    )
    return {"ok": True, "outcome": "ok", "cite": {**data, "excerpts": excerpts}}


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
    meta, _body = _parse_frontmatter(text)
    excerpts = meta.get("excerpts") or []
    if not isinstance(excerpts, list):
        excerpts = [str(excerpts)]
    cite = {**meta, "excerpts": excerpts, "path": str(path)}
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
    """Model-facing observation — never includes HTML."""
    return {
        "title": cite.get("title"),
        "url": cite.get("url"),
        "final_url": cite.get("final_url"),
        "cite_id": cite.get("id"),
        "excerpts": list(cite.get("excerpts") or []),
        "truncated": bool(cite.get("truncated")),
        "cache": cache,
        "receipt_id": receipt_id or cite.get("receipt_id"),
        "fetched_at": cite.get("fetched_at"),
        "content_hash": cite.get("content_hash"),
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


def search_cites(
    query: str,
    *,
    max_hits: int = 10,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    """Grep-first search over cite index heads (title/url/id). No network.

    Matcher v1.0.1: tokenized AND (each remaining token is a substring of the
    haystack), after punctuation normalize + stopword/genre-stop drop.
    Dedupes by cite_id keeping the newest index line. Not vendor web_search.
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
        # Non-empty but only stop/genre words — no invent; empty hits.
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

    # Newest-first; keep first seen id (most recent head).
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
        hay = " ".join(
            str(x or "")
            for x in (
                cid,
                obj.get("title"),
                obj.get("url"),
                obj.get("final_url"),
            )
        ).lower()
        if not all(tok in hay for tok in tokens):
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
