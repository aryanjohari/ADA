"""Deterministic feed-item triage before web_fetch (M09 §7.2).

guid seen → skip; pubDate too old → skip; cite-index fresh → skip;
allowlist miss → deny; cap max_items_per_wake.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from ada.io.paths import DataPaths, require_ada_data
from ada.web import allowlist as allowlist_mod
from ada.web import cites as cites_mod
from ada.web.feeds import FeedItem, normalize_url


def cite_index_fresh(url: str, *, paths: DataPaths | None = None) -> bool:
    """True when URL has a cite within host TTL (M07 library-first)."""
    p = paths or require_ada_data()
    norm = normalize_url(url)
    existing = cites_mod.newest_cite_for_url(norm, paths=p)
    if existing is None:
        existing = cites_mod.newest_cite_for_url(url, paths=p)
    if existing is None:
        return False
    host = allowlist_mod.host_from_url(existing.get("final_url") or existing.get("url") or url)
    ttl = allowlist_mod.ttl_for_host(host, p)
    return cites_mod.is_fresh(existing, ttl_seconds=ttl)


def triage_feed_items(
    items: list[FeedItem],
    *,
    watch: dict[str, Any],
    cursor: dict[str, Any],
    paths: DataPaths | None = None,
    now: datetime | None = None,
    global_selected: int = 0,
    global_cap: int | None = None,
) -> tuple[list[FeedItem], list[dict[str, Any]]]:
    """Return (selected_for_fetch, skip_events). M09 §7.2 triage table."""
    p = paths or require_ada_data()
    now = now or datetime.now(timezone.utc)
    cap = int(watch.get("max_items_per_wake") or 5)
    if global_cap is not None:
        cap = min(cap, max(0, global_cap - global_selected))
    max_age = timedelta(hours=int(watch.get("max_age_hours") or 168))
    seen = set(cursor.get("seen_guids") or [])

    selected: list[FeedItem] = []
    skips: list[dict[str, Any]] = []

    for item in items:
        if len(selected) >= cap:
            skips.append(
                {
                    "reason": "cap_deferred",
                    "guid": item.guid,
                    "url": item.url,
                    "watch_id": watch.get("id"),
                }
            )
            continue
        if item.guid in seen:
            skips.append(
                {
                    "reason": "guid_seen",
                    "guid": item.guid,
                    "url": item.url,
                    "watch_id": watch.get("id"),
                }
            )
            continue
        if item.published_at is not None and item.published_at < (now - max_age):
            skips.append(
                {
                    "reason": "too_old",
                    "guid": item.guid,
                    "url": item.url,
                    "watch_id": watch.get("id"),
                    "published_at": item.published_at.isoformat(),
                }
            )
            continue
        norm_url = normalize_url(item.url)
        policy = allowlist_mod.check_host_access(
            norm_url,
            paths=p,
            user_pasted=False,
            confirm_host=False,
        )
        if policy.get("needs_confirm") or not policy.get("ok"):
            skips.append(
                {
                    "reason": "allowlist_deny",
                    "guid": item.guid,
                    "url": norm_url,
                    "watch_id": watch.get("id"),
                    "host": policy.get("host"),
                    "error": policy.get("denied_reason") or policy.get("error"),
                }
            )
            continue
        if cite_index_fresh(norm_url, paths=p):
            skips.append(
                {
                    "reason": "cite_fresh",
                    "guid": item.guid,
                    "url": norm_url,
                    "watch_id": watch.get("id"),
                }
            )
            seen.add(item.guid)
            continue
        selected.append(
            FeedItem(
                guid=item.guid,
                url=norm_url,
                title=item.title,
                published_at=item.published_at,
            )
        )

    return selected, skips
