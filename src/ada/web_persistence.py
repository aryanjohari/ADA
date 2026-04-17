"""Normalize Phase A web tool responses into bounded `web_sources` rows (no HTTP)."""

from __future__ import annotations

import hashlib
from typing import Any

MAX_URL_CHARS = 2048
MAX_QUERY_CHARS = 512
MAX_EXCERPT_CHARS = 4096
MAX_ROWS_PER_TOOL = 20


def _trunc(s: str, max_chars: int) -> str:
    if len(s) <= max_chars:
        return s
    return s[: max_chars - 1] + "…"


def content_sha256_hex(source_kind: str, url: str, excerpt: str) -> str:
    h = hashlib.sha256()
    h.update(source_kind.encode("utf-8"))
    h.update(b"\n")
    h.update(url.encode("utf-8"))
    h.update(b"\n")
    h.update(excerpt.encode("utf-8"))
    return h.hexdigest()


def rows_for_web_tool(
    tool_name: str,
    args: dict[str, Any],
    response: dict[str, Any],
) -> list[tuple[str, str, str | None, str, str]]:
    """
    Return list of (url, source_kind, query_text|None, content_excerpt, content_sha256).
    Empty if tool is not web, on error responses, or nothing to persist.
    """
    if tool_name == "web_search":
        return _rows_web_search(args, response)
    if tool_name == "fetch_url_text":
        return _rows_fetch(response)
    return []


def _rows_web_search(
    args: dict[str, Any], response: dict[str, Any]
) -> list[tuple[str, str, str | None, str, str]]:
    if response.get("error"):
        return []
    results = response.get("results")
    if not isinstance(results, list) or not results:
        return []
    qraw = str(args.get("query") or "").strip()
    query_text = _trunc(qraw, MAX_QUERY_CHARS) if qraw else None
    out: list[tuple[str, str, str | None, str, str]] = []
    for item in results[:MAX_ROWS_PER_TOOL]:
        if not isinstance(item, dict):
            continue
        url = _trunc(str(item.get("url") or "").strip(), MAX_URL_CHARS)
        if not url:
            continue
        snippet = _trunc(str(item.get("snippet") or ""), MAX_EXCERPT_CHARS)
        kind = "search_hit"
        sha = content_sha256_hex(kind, url, snippet)
        out.append((url, kind, query_text, snippet, sha))
    return out


def _rows_fetch(response: dict[str, Any]) -> list[tuple[str, str, str | None, str, str]]:
    if response.get("error"):
        return []
    pages = response.get("pages")
    if not isinstance(pages, list) or not pages:
        return []
    out: list[tuple[str, str, str | None, str, str]] = []
    for page in pages[:MAX_ROWS_PER_TOOL]:
        if not isinstance(page, dict):
            continue
        if page.get("error"):
            continue
        url = _trunc(str(page.get("url") or "").strip(), MAX_URL_CHARS)
        if not url:
            continue
        text = _trunc(str(page.get("text") or ""), MAX_EXCERPT_CHARS)
        kind = "page_fetch"
        sha = content_sha256_hex(kind, url, text)
        out.append((url, kind, None, text, sha))
    return out
