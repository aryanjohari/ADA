"""Thin wrappers → ada.web.* (M07)."""

from __future__ import annotations

from typing import Any

from ada.web import fetch as fetch_mod


def run_web_fetch(args: dict[str, Any]) -> dict[str, Any]:
    url = args.get("url")
    if not url:
        return {
            "ok": False,
            "outcome": "error",
            "error": "url required",
            "denied_reason": "url required",
        }
    return fetch_mod.web_fetch(
        str(url),
        force=bool(args.get("force", False)),
        user_pasted=bool(args.get("user_pasted", False)),
        pasted_text=args.get("pasted_text"),
        ignore_robots=bool(args.get("ignore_robots", False)),
        confirm_host=bool(args.get("confirm_host", False)),
        receipt_id=args.get("receipt_id"),
        question=args.get("question"),
    )


def run_web_cite_get(args: dict[str, Any]) -> dict[str, Any]:
    cite_id = args.get("cite_id") or args.get("id")
    if not cite_id:
        return {
            "ok": False,
            "outcome": "error",
            "error": "cite_id required",
            "denied_reason": "cite_id required",
        }
    return fetch_mod.web_cite_get(str(cite_id))


def run_web_cite_search(args: dict[str, Any]) -> dict[str, Any]:
    query = args.get("query") or args.get("q") or ""
    max_hits = int(args.get("max_hits") or 10)
    return fetch_mod.web_cite_search(str(query), max_hits=max_hits)


DISPATCH = {
    "web_fetch": run_web_fetch,
    "web_cite_get": run_web_cite_get,
    "web_cite_search": run_web_cite_search,
}
