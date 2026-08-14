"""Allowlisted RSS/Atom feed pull + normalize (M09 §7.2).

Deterministic pre-step before web_fetch — no Gemini. Feed GET honors
allowlist + SSRF (same gates as M07 fetch).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import feedparser
import httpx

from ada.body.vitals import utc_now_iso
from ada.io.paths import DataPaths, require_ada_data
from ada.web import allowlist as allowlist_mod
from ada.web.fetch import USER_AGENT, _manual_get
from ada.web.ssrf import SsrfError

MAX_FEED_BYTES = 2 * 1024 * 1024  # M09 §7.6
REQUEST_TIMEOUT = 15.0

_TRACKING_QUERY_PREFIXES = ("utm_", "fbclid", "gclid", "mc_cid", "mc_eid")


@dataclass(frozen=True)
class FeedItem:
    guid: str
    url: str
    title: str | None
    published_at: datetime | None


def normalize_url(url: str) -> str:
    """Canonical URL for cite lookup — strip tracking params, prefer https."""
    raw = (url or "").strip()
    if not raw:
        return raw
    parsed = urlparse(raw)
    scheme = "https" if parsed.scheme == "http" else (parsed.scheme or "https")
    query_pairs = []
    for key, val in parse_qsl(parsed.query, keep_blank_values=True):
        low = key.lower()
        if low.startswith(_TRACKING_QUERY_PREFIXES):
            continue
        query_pairs.append((key, val))
    query = urlencode(query_pairs)
    netloc = (parsed.netloc or "").lower()
    path = parsed.path or ""
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return urlunparse((scheme, netloc, path, parsed.params, query, ""))


def _parse_pubdate(value: str | None) -> datetime | None:
    if not value or not str(value).strip():
        return None
    text = str(value).strip()
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
    except ValueError:
        try:
            dt = parsedate_to_datetime(text)
        except (TypeError, ValueError):
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _item_guid(entry: dict[str, Any], *, fallback_url: str) -> str:
    for key in ("id", "guid", "link"):
        val = entry.get(key)
        if val and str(val).strip():
            return str(val).strip()
    title = entry.get("title") or ""
    return hashlib.sha256(f"{fallback_url}|{title}".encode()).hexdigest()[:32]


def _entry_url(entry: dict[str, Any]) -> str | None:
    link = entry.get("link")
    if link and str(link).strip():
        return normalize_url(str(link).strip())
    links = entry.get("links") or []
    for item in links:
        if not isinstance(item, dict):
            continue
        href = item.get("href")
        rel = str(item.get("rel") or "alternate").lower()
        if href and rel in ("alternate", "self", ""):
            return normalize_url(str(href).strip())
    return None


def parse_feed_bytes(
    body: bytes,
    *,
    feed_url: str,
    kind: str = "rss",
) -> list[FeedItem]:
    """Parse RSS/Atom XML into normalized FeedItem rows (newest-first)."""
    _ = kind  # feedparser handles rss + atom
    parsed = feedparser.parse(body)
    items: list[FeedItem] = []
    for entry in parsed.entries or []:
        url = _entry_url(entry)
        if not url:
            continue
        guid = _item_guid(entry, fallback_url=url)
        pub = None
        if entry.get("published"):
            pub = _parse_pubdate(str(entry.get("published")))
        elif entry.get("updated"):
            pub = _parse_pubdate(str(entry.get("updated")))
        title = entry.get("title")
        items.append(
            FeedItem(
                guid=guid,
                url=url,
                title=str(title).strip() if title else None,
                published_at=pub,
            )
        )
    items.sort(
        key=lambda it: it.published_at or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return items


def fixed_url_items(urls: list[str]) -> list[FeedItem]:
    """Synthetic feed items for kind=fixed_urls watches."""
    out: list[FeedItem] = []
    for raw in urls:
        url = normalize_url(str(raw).strip())
        if not url:
            continue
        out.append(
            FeedItem(
                guid=url,
                url=url,
                title=url,
                published_at=None,
            )
        )
    return out


def pull_feed(
    url: str,
    *,
    kind: str = "rss",
    etag: str | None = None,
    paths: DataPaths | None = None,
    http_get=None,
    confirm_host: bool = False,
) -> dict[str, Any]:
    """GET allowlisted feed URL → parse items. M09 §7.2."""
    p = paths or require_ada_data()
    policy = allowlist_mod.check_host_access(
        url,
        paths=p,
        user_pasted=False,
        confirm_host=confirm_host,
    )
    if policy.get("needs_confirm"):
        return {
            "ok": False,
            "outcome": "needs_confirm",
            "needs_confirm": True,
            "host": policy.get("host"),
            "error": policy.get("denied_reason") or policy.get("reason"),
        }
    if not policy.get("ok"):
        return {
            "ok": False,
            "outcome": "error",
            "error": policy.get("error") or policy.get("denied_reason") or "denied",
        }

    if kind == "fixed_urls":
        return {
            "ok": False,
            "outcome": "error",
            "error": "fixed_urls watches use urls[] not pull_feed(url)",
        }

    host = policy["host"]
    allowlisted = allowlist_mod.allowlist_hosts(p)
    headers: dict[str, str] = {}
    if etag:
        headers["If-None-Match"] = etag

    try:
        if http_get is not None:
            resp, final_url, _hops = http_get(
                url,
                headers=headers,
                allowlisted=allowlisted,
                pasted=set(),
            )
        else:
            resp, final_url, _hops = _manual_get(
                url,
                allowlisted=allowlisted,
                pasted=set(),
                headers=headers,
                allow_http_hosts=allowlisted,
            )
    except SsrfError as exc:
        return {"ok": False, "outcome": "error", "error": str(exc)}
    except httpx.HTTPError as exc:
        return {"ok": False, "outcome": "error", "error": f"http error: {exc}"}

    resp_etag = resp.headers.get("etag")
    if resp.status_code == 304:
        return {
            "ok": True,
            "outcome": "ok",
            "not_modified": True,
            "items": [],
            "etag": resp_etag or etag,
            "final_url": final_url,
            "host": host,
            "fetched_at": utc_now_iso(),
        }

    if resp.status_code != 200:
        return {
            "ok": False,
            "outcome": "error",
            "error": f"HTTP {resp.status_code}",
            "status": resp.status_code,
            "final_url": final_url,
        }

    body = resp.content
    truncated = False
    if len(body) > MAX_FEED_BYTES:
        body = body[:MAX_FEED_BYTES]
        truncated = True

    items = parse_feed_bytes(body, feed_url=final_url, kind=kind)
    return {
        "ok": True,
        "outcome": "ok",
        "not_modified": False,
        "items": items,
        "etag": resp_etag,
        "final_url": final_url,
        "host": host,
        "truncated": truncated,
        "fetched_at": utc_now_iso(),
    }
