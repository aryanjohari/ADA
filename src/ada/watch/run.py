"""Campaign watch wake — Phase A ingest (M09 §7.3).

One campaign per tick; bounded web_fetch; runs/ receipt + cursor persist.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ada.body.vitals import utc_now_iso
from ada.io.atomic import append_jsonl_line
from ada.io.paths import DataPaths, require_ada_data
from ada.memory.open_loops import (
    due_watch_campaigns,
    get_loop,
    mark_guid_seen,
    upsert_loop,
)
from ada.runs.append import new_receipt_id, utc_date_dir
from ada.web import fetch as fetch_mod
from ada.web.feeds import FeedItem, fixed_url_items, pull_feed
from ada.watch.triage import triage_feed_items

WATCH_EVENT_TYPES = frozenset(
    {"watch_wake_start", "feed_pulled", "item_skipped", "item_fetch", "watch_wake_end"}
)


def _watch_session_path(campaign_id: str, *, paths: DataPaths) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return paths.runs / utc_date_dir() / f"watch_{campaign_id}_{ts}.jsonl"


def _append_watch_event(
    session_path: Path,
    event_type: str,
    *,
    campaign_id: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if event_type not in WATCH_EVENT_TYPES:
        raise ValueError(f"unknown watch event: {event_type}")
    record = {
        "schema_version": 1,
        "id": new_receipt_id(),
        "ts": utc_now_iso(),
        "type": event_type,
        "campaign_id": campaign_id,
        "payload": payload or {},
    }
    session_path.parent.mkdir(parents=True, exist_ok=True)
    append_jsonl_line(session_path, record)
    return record


def _advance_next_wake_at(campaign: dict[str, Any], now: datetime) -> str | None:
    cadence = str(campaign.get("cadence") or "on_open_only")
    if cadence == "daily":
        nxt = now + timedelta(days=1)
        return nxt.isoformat()
    return campaign.get("next_wake_at") if isinstance(campaign.get("next_wake_at"), str) else None


def _pull_watch_items(
    watch: dict[str, Any],
    *,
    paths: DataPaths,
    http_get=None,
) -> tuple[list[FeedItem], dict[str, Any], dict[str, Any]]:
    """Pull items for one watch; return (items, pull_meta, updated_cursor_bits)."""
    cursor = dict(watch.get("cursor") or {})
    kind = str(watch.get("kind") or "rss")

    if kind == "fixed_urls":
        items = fixed_url_items(list(watch.get("urls") or []))
        meta = {
            "ok": True,
            "outcome": "ok",
            "kind": "fixed_urls",
            "item_count": len(items),
            "fetched_at": utc_now_iso(),
        }
        return items, meta, {}

    url = str(watch.get("url") or "")
    pulled = pull_feed(
        url,
        kind=kind,
        etag=cursor.get("etag"),
        paths=paths,
        http_get=http_get,
        confirm_host=False,
    )
    bits: dict[str, Any] = {"last_checked_at": utc_now_iso()}
    if pulled.get("etag"):
        bits["etag"] = pulled.get("etag")
    if not pulled.get("ok"):
        bits["last_error"] = pulled.get("error")
        return [], pulled, bits
    bits["last_error"] = None
    items = list(pulled.get("items") or [])
    return items, pulled, bits


def watch_run(
    *,
    campaign_id: str | None = None,
    ingest_only: bool = True,
    dry_run: bool = False,
    paths: DataPaths | None = None,
    now: datetime | None = None,
    http_get=None,
    web_fetch_fn=None,
) -> dict[str, Any]:
    """Execute one campaign watch wake (Phase A). M09 §7.3."""
    _ = ingest_only  # Phase B digest deferred
    p = paths or require_ada_data()
    p.ensure_memory_dirs()
    p.ensure_cite_dirs()
    now = now or datetime.now(timezone.utc)

    campaign: dict[str, Any] | None = None
    if campaign_id:
        raw = get_loop(campaign_id, paths=p)
        if raw is None or raw.get("kind") != "campaign":
            return {
                "ok": False,
                "outcome": "error",
                "error": f"campaign not found: {campaign_id}",
            }
        if not raw.get("watches"):
            return {
                "ok": False,
                "outcome": "error",
                "error": f"campaign {campaign_id} has no watches[]",
            }
        campaign = raw
    else:
        due = due_watch_campaigns(paths=p, now=now, limit=1)
        if not due:
            return {
                "ok": True,
                "outcome": "idle",
                "reason": "no_due_watch_campaign",
                "count": 0,
            }
        campaign = due[0]

    cid = str(campaign.get("id") or "")
    watches = list(campaign.get("watches") or [])
    session_path = _watch_session_path(cid, paths=p)
    rel_session = session_path.relative_to(p.root).as_posix()

    start_evt = _append_watch_event(
        session_path,
        "watch_wake_start",
        campaign_id=cid,
        payload={"dry_run": dry_run, "watch_count": len(watches)},
    )

    fetch_impl = web_fetch_fn or fetch_mod.web_fetch
    total_fetched = 0
    total_skipped = 0
    last_fetch_evt: dict[str, Any] | None = None
    updated_watches: list[dict[str, Any]] = []

    for watch in watches:
        wcopy = dict(watch)
        cursor = dict(wcopy.get("cursor") or {})
        items, pull_meta, cursor_bits = _pull_watch_items(
            wcopy,
            paths=p,
            http_get=http_get,
        )
        cursor.update(cursor_bits)

        if pull_meta.get("ok"):
            _append_watch_event(
                session_path,
                "feed_pulled",
                campaign_id=cid,
                payload={
                    "watch_id": wcopy.get("id"),
                    "url": wcopy.get("url"),
                    "item_count": len(items),
                    "not_modified": pull_meta.get("not_modified"),
                    "truncated": pull_meta.get("truncated"),
                },
            )
        elif not pull_meta.get("ok"):
            _append_watch_event(
                session_path,
                "feed_pulled",
                campaign_id=cid,
                payload={
                    "watch_id": wcopy.get("id"),
                    "url": wcopy.get("url"),
                    "error": pull_meta.get("error"),
                    "outcome": pull_meta.get("outcome"),
                },
            )

        selected, skips = triage_feed_items(
            items,
            watch=wcopy,
            cursor=cursor,
            paths=p,
            now=now,
        )
        for skip in skips:
            total_skipped += 1
            _append_watch_event(
                session_path,
                "item_skipped",
                campaign_id=cid,
                payload=skip,
            )
            if skip.get("reason") == "cite_fresh":
                mark_guid_seen(cursor, str(skip.get("guid") or ""))

        for item in selected:
            if dry_run:
                total_fetched += 1
                _append_watch_event(
                    session_path,
                    "item_fetch",
                    campaign_id=cid,
                    payload={
                        "dry_run": True,
                        "guid": item.guid,
                        "url": item.url,
                        "title": item.title,
                    },
                )
                mark_guid_seen(cursor, item.guid)
                continue

            result = fetch_impl(
                item.url,
                user_pasted=False,
                confirm_host=False,
                ignore_robots=False,
                receipt_id=start_evt["id"],
                paths=p,
                http_get=http_get,
            )
            evt_payload: dict[str, Any] = {
                "guid": item.guid,
                "url": item.url,
                "title": item.title,
                "fetch_ok": result.get("ok"),
                "cite_id": result.get("cite_id"),
                "cache": result.get("cache"),
                "error": result.get("error"),
                "needs_confirm": result.get("needs_confirm"),
            }
            last_fetch_evt = _append_watch_event(
                session_path,
                "item_fetch",
                campaign_id=cid,
                payload=evt_payload,
            )
            mark_guid_seen(cursor, item.guid)
            if result.get("ok"):
                total_fetched += 1

        cursor["last_checked_at"] = cursor.get("last_checked_at") or utc_now_iso()
        wcopy["cursor"] = cursor
        updated_watches.append(wcopy)

    end_evt = _append_watch_event(
        session_path,
        "watch_wake_end",
        campaign_id=cid,
        payload={
            "fetched": total_fetched,
            "skipped": total_skipped,
            "dry_run": dry_run,
        },
    )

    receipt_pointer = f"{rel_session}#{last_fetch_evt['id'] if last_fetch_evt else end_evt['id']}"
    if not dry_run:
        upsert_loop(
            loop_id=cid,
            watches=updated_watches,
            last_receipt=receipt_pointer,
            last_progress_at=utc_now_iso(),
            next_wake_at=_advance_next_wake_at(campaign, now),
            paths=p,
        )

    return {
        "ok": True,
        "outcome": "ok" if total_fetched or dry_run else "idle",
        "campaign_id": cid,
        "dry_run": dry_run,
        "fetched": total_fetched,
        "skipped": total_skipped,
        "session": rel_session,
        "last_receipt": receipt_pointer,
        "watch_count": len(watches),
    }
