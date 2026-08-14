"""Open loops + campaigns — durable STATUS on disk (M04/M06).

Plain TODOs (`kind: todo`) and campaigns (`kind: campaign`) share one YAML file.
Campaigns add stages, gates, wake fields — not a second job framework.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import yaml

from ada.body.vitals import utc_now_iso
from ada.io.atomic import atomic_write_text, cleanup_orphan_tmps
from ada.io.paths import BodyFault, DataPaths, ada_data_mounted, require_ada_data

SCHEMA_VERSION = 2

KIND_TODO = "todo"
KIND_CAMPAIGN = "campaign"
KINDS = frozenset({KIND_TODO, KIND_CAMPAIGN})

TODO_STATUSES = frozenset({"open", "done", "cancelled"})
CAMPAIGN_STATUSES = frozenset(
    {"active", "blocked", "waiting_on_aryan", "paused", "done", "failed"}
)
STAGE_STATES = frozenset({"pending", "active", "done", "skipped"})
CADENCES = frozenset({"on_open_only", "daily"})

# M09 watches on campaigns (optional field).
WATCH_KINDS = frozenset({"rss", "atom", "fixed_urls"})
DEFAULT_MAX_ITEMS_PER_WAKE = 5
DEFAULT_MAX_AGE_HOURS = 168
SEEN_GUIDS_CAP = 2000

# Boot / check caps (scalability via caps, not a new framework).
K_CAMPAIGN_HEADS = 3
K_TODO_HEADS = 2
K_DUE_PER_WAKE = 5

# Prefer surfacing blocked / waiting first in boot.
_BOOT_STATUS_PRIORITY = {
    "waiting_on_aryan": 0,
    "blocked": 1,
    "active": 2,
    "paused": 3,
}


def _dump(obj: dict[str, Any]) -> str:
    return yaml.safe_dump(
        obj, sort_keys=False, allow_unicode=True, default_flow_style=False
    )


def _require(paths: DataPaths | None) -> DataPaths:
    p = paths or require_ada_data()
    if not ada_data_mounted(p.root):
        raise BodyFault(
            f"ada-data not mounted or missing at {p.root}; refusing durable writes"
        )
    return p


def _normalize_item(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    item = dict(raw)
    kind = str(item.get("kind") or KIND_TODO).strip() or KIND_TODO
    if kind not in KINDS:
        kind = KIND_TODO
    item["kind"] = kind
    if kind == KIND_TODO:
        status = str(item.get("status") or "open")
        if status not in TODO_STATUSES:
            status = "open"
        item["status"] = status
    else:
        status = str(item.get("status") or "active")
        if status not in CAMPAIGN_STATUSES:
            status = "active"
        item["status"] = status
        if not item.get("title") and item.get("text"):
            item["title"] = item["text"]
        if item.get("watches") is not None:
            try:
                item["watches"] = _normalize_watches(item.get("watches"))
            except ValueError:
                pass  # load-time lenient; upsert validates strictly
    return item


def _load(paths: DataPaths) -> dict[str, Any]:
    cleanup_orphan_tmps(paths.facts, "open_loops.yaml")
    if not paths.open_loops_yaml.is_file():
        return {"schema_version": SCHEMA_VERSION, "loops": []}
    raw = yaml.safe_load(paths.open_loops_yaml.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return {"schema_version": SCHEMA_VERSION, "loops": []}
    raw.setdefault("schema_version", SCHEMA_VERSION)
    raw["schema_version"] = max(int(raw.get("schema_version") or 1), SCHEMA_VERSION)
    loops_in = raw.get("loops") or []
    if not isinstance(loops_in, list):
        loops_in = []
    loops: list[dict[str, Any]] = []
    for entry in loops_in:
        norm = _normalize_item(entry)
        if norm is not None:
            loops.append(norm)
    raw["loops"] = loops
    return raw


def ensure_open_loops(paths: DataPaths | None = None) -> dict[str, Any]:
    p = _require(paths)
    p.ensure_memory_dirs()
    data = _load(p)
    if not p.open_loops_yaml.is_file():
        atomic_write_text(p.open_loops_yaml, _dump(data))
    return data


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts or not isinstance(ts, str):
        return None
    text = ts.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _validate_status(kind: str, status: str) -> str:
    if kind == KIND_CAMPAIGN:
        if status not in CAMPAIGN_STATUSES:
            raise ValueError(
                f"campaign status must be one of {sorted(CAMPAIGN_STATUSES)}; got {status!r}"
            )
        return status
    if status not in TODO_STATUSES:
        raise ValueError(
            f"todo status must be one of {sorted(TODO_STATUSES)}; got {status!r}"
        )
    return status


def _normalize_watch_cursor(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError("watch.cursor must be a mapping")
    cursor = dict(raw)
    seen = cursor.get("seen_guids")
    if seen is None:
        cursor["seen_guids"] = []
    elif not isinstance(seen, list):
        raise ValueError("watch.cursor.seen_guids must be a list")
    else:
        cursor["seen_guids"] = [str(x) for x in seen if str(x).strip()][-SEEN_GUIDS_CAP:]
    if cursor.get("last_checked_at") is not None:
        cursor["last_checked_at"] = str(cursor["last_checked_at"]).strip() or None
    if cursor.get("etag") is not None:
        cursor["etag"] = str(cursor["etag"]).strip() or None
    if cursor.get("last_error") is not None:
        cursor["last_error"] = str(cursor["last_error"]).strip() or None
    return cursor


def _normalize_watches(watches: Any) -> list[dict[str, Any]]:
    """Validate watches[] on a campaign (M09 §7.1)."""
    if watches is None:
        return []
    if not isinstance(watches, list):
        raise ValueError("watches must be a list")
    out: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for raw in watches:
        if not isinstance(raw, dict):
            raise ValueError("each watch must be a mapping")
        wid = str(raw.get("id") or "").strip()
        if not wid:
            raise ValueError("watch.id required")
        if wid in seen_ids:
            raise ValueError(f"duplicate watch.id: {wid}")
        seen_ids.add(wid)
        kind = str(raw.get("kind") or "rss").strip()
        if kind not in WATCH_KINDS:
            raise ValueError(
                f"watch.kind must be one of {sorted(WATCH_KINDS)}; got {kind!r}"
            )
        watch: dict[str, Any] = {"id": wid, "kind": kind}
        if kind == "fixed_urls":
            urls_raw = raw.get("urls")
            if not isinstance(urls_raw, list) or not urls_raw:
                raise ValueError("fixed_urls watch requires non-empty urls[]")
            watch["urls"] = [str(u).strip() for u in urls_raw if str(u).strip()]
            if not watch["urls"]:
                raise ValueError("fixed_urls watch requires non-empty urls[]")
        else:
            feed_url = str(raw.get("url") or "").strip()
            if not feed_url:
                raise ValueError(f"watch {wid!r} requires url")
            watch["url"] = feed_url
        cap = int(raw.get("max_items_per_wake") or DEFAULT_MAX_ITEMS_PER_WAKE)
        if cap < 1:
            raise ValueError("watch.max_items_per_wake must be >= 1")
        watch["max_items_per_wake"] = cap
        watch["max_age_hours"] = int(raw.get("max_age_hours") or DEFAULT_MAX_AGE_HOURS)
        if raw.get("pack"):
            watch["pack"] = str(raw.get("pack")).strip()
        watch["cursor"] = _normalize_watch_cursor(raw.get("cursor"))
        out.append(watch)
    return out


def _normalize_stages(stages: Any) -> list[dict[str, Any]]:
    if stages is None:
        return []
    if not isinstance(stages, list):
        raise ValueError("stages must be a list")
    out: list[dict[str, Any]] = []
    for raw in stages:
        if not isinstance(raw, dict):
            raise ValueError("each stage must be a mapping")
        sid = str(raw.get("id") or "").strip()
        if not sid:
            raise ValueError("stage.id required")
        state = str(raw.get("state") or "pending").strip()
        if state not in STAGE_STATES:
            raise ValueError(
                f"stage.state must be one of {sorted(STAGE_STATES)}; got {state!r}"
            )
        stage: dict[str, Any] = {"id": sid, "state": state}
        gate = raw.get("gate")
        if gate is not None and str(gate).strip():
            g = str(gate).strip()
            if g != "confirm":
                raise ValueError("stage.gate must be 'confirm' when set")
            stage["gate"] = "confirm"
        out.append(stage)
    return out


def _stage_by_id(stages: list[dict[str, Any]], stage_id: str) -> dict[str, Any] | None:
    for s in stages:
        if s.get("id") == stage_id:
            return s
    return None


def _gated_done_needs_confirm(
    *,
    existing: dict[str, Any] | None,
    new_stages: list[dict[str, Any]] | None,
    new_status: str | None,
    last_receipt: str | None,
    confirmed: bool,
) -> dict[str, Any] | None:
    """Return needs_confirm payload if a gated completion is attempted without proof."""
    if confirmed:
        return None
    has_receipt = bool(last_receipt and str(last_receipt).strip()) or bool(
        existing and existing.get("last_receipt")
    )

    if new_stages is not None and existing is not None:
        old_stages = _normalize_stages(existing.get("stages") or [])
        for ns in new_stages:
            if ns.get("state") != "done":
                continue
            if ns.get("gate") != "confirm":
                # Check old stage gate if new payload omitted it.
                old = _stage_by_id(old_stages, str(ns.get("id")))
                if not old or old.get("gate") != "confirm":
                    continue
            old = _stage_by_id(old_stages, str(ns.get("id")))
            if old and old.get("state") == "done":
                continue
            if has_receipt:
                continue
            return {
                "ok": False,
                "needs_confirm": True,
                "outcome": "needs_confirm",
                "reason": (
                    f"stage {ns.get('id')!r} has gate=confirm; "
                    "needs confirmed=true or last_receipt"
                ),
                "id": existing.get("id"),
            }

    if (
        new_status in {"done", "failed"}
        and existing
        and existing.get("kind") == KIND_CAMPAIGN
        and existing.get("status") not in {"done", "failed"}
        and not has_receipt
    ):
        # Campaign-level done/failed: confirm unless receipt already on record.
        stages = new_stages
        if stages is None:
            stages = _normalize_stages(existing.get("stages") or [])
        has_confirm_gate = any(s.get("gate") == "confirm" for s in stages)
        if has_confirm_gate or new_status == "done":
            return {
                "ok": False,
                "needs_confirm": True,
                "outcome": "needs_confirm",
                "reason": (
                    f"campaign status→{new_status} requires confirmed=true "
                    "or last_receipt when gated/completing"
                ),
                "id": existing.get("id"),
            }
    return None


def list_loops(
    *,
    paths: DataPaths | None = None,
    status: str | None = "open",
    kind: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    p = paths or require_ada_data()
    data = _load(p)
    loops = list(data.get("loops") or [])
    if kind:
        loops = [x for x in loops if x.get("kind") == kind]
    if status:
        loops = [x for x in loops if x.get("status") == status]
    return loops[: max(0, limit)]


def list_watch_campaigns(
    *,
    paths: DataPaths | None = None,
    status: str | None = None,
    limit: int = 50,
    include_done: bool = False,
) -> list[dict[str, Any]]:
    """Campaigns with non-empty watches[] (M09)."""
    camps = list_campaigns(
        paths=paths, status=status, limit=limit, include_done=include_done
    )
    return [c for c in camps if c.get("watches")]


def due_watch_campaigns(
    *,
    paths: DataPaths | None = None,
    now: datetime | None = None,
    limit: int = 1,
) -> list[dict[str, Any]]:
    """Due campaigns that have watches — at most one per timer tick (M09 F7)."""
    due = due_campaigns(paths=paths, now=now, limit=200)
    watch_due = [c for c in due if c.get("watches")]
    return watch_due[: max(0, limit)]


def mark_guid_seen(cursor: dict[str, Any], guid: str) -> None:
    """Ring-buffer append for watch cursor (M09 §7.2)."""
    seen = list(cursor.get("seen_guids") or [])
    if guid in seen:
        seen.remove(guid)
    seen.append(guid)
    if len(seen) > SEEN_GUIDS_CAP:
        seen = seen[-SEEN_GUIDS_CAP:]
    cursor["seen_guids"] = seen


def list_campaigns(
    *,
    paths: DataPaths | None = None,
    status: str | None = None,
    limit: int = 50,
    include_done: bool = False,
) -> list[dict[str, Any]]:
    p = paths or require_ada_data()
    data = _load(p)
    loops = [x for x in (data.get("loops") or []) if x.get("kind") == KIND_CAMPAIGN]
    if status:
        loops = [x for x in loops if x.get("status") == status]
    elif not include_done:
        loops = [x for x in loops if x.get("status") not in {"done", "failed"}]
    return loops[: max(0, limit)]


def format_campaign_head(item: dict[str, Any], *, max_len: int = 200) -> str:
    title = str(item.get("title") or item.get("text") or "?").strip()
    status = item.get("status") or "?"
    stage = item.get("current_stage") or "-"
    blocked = item.get("blocked_reason")
    parts = [f"[{item.get('id', '?')}]", title[:80], f"STATUS={status}", f"stage={stage}"]
    if blocked:
        parts.append(f"blocked={str(blocked)[:60]}")
    line = " ".join(parts)
    if len(line) > max_len:
        return line[: max_len - 1] + "…"
    return line


def campaign_heads(
    *,
    paths: DataPaths | None = None,
    limit: int = K_CAMPAIGN_HEADS,
) -> list[dict[str, Any]]:
    """Budgeted active campaign heads for boot (excludes done/failed)."""
    camps = list_campaigns(paths=paths, include_done=False, limit=200)

    def sort_key(c: dict[str, Any]) -> tuple[int, str]:
        pri = _BOOT_STATUS_PRIORITY.get(str(c.get("status")), 9)
        return (pri, str(c.get("updated_at") or ""))

    camps_sorted = sorted(camps, key=sort_key)
    return camps_sorted[: max(0, limit)]


def due_campaigns(
    *,
    paths: DataPaths | None = None,
    now: datetime | None = None,
    limit: int = K_DUE_PER_WAKE,
) -> list[dict[str, Any]]:
    """Campaigns due for a wake: next_wake_at passed, blocked/waiting, or daily-stale."""
    now = now or datetime.now(timezone.utc)
    camps = list_campaigns(paths=paths, include_done=False, limit=200)
    due: list[dict[str, Any]] = []
    for c in camps:
        reason: str | None = None
        status = c.get("status")
        if status in {"blocked", "waiting_on_aryan"}:
            reason = str(status)
        wake = _parse_iso(c.get("next_wake_at") if isinstance(c.get("next_wake_at"), str) else None)
        if wake is not None and wake <= now:
            reason = reason or "next_wake_at"
        cadence = str(c.get("cadence") or "on_open_only")
        if cadence == "daily":
            progress = _parse_iso(
                c.get("last_progress_at")
                if isinstance(c.get("last_progress_at"), str)
                else None
            )
            anchor = progress or _parse_iso(
                c.get("updated_at") if isinstance(c.get("updated_at"), str) else None
            )
            if anchor is not None and (now - anchor) >= timedelta(hours=48):
                reason = reason or "stale"
        if reason:
            item = dict(c)
            item["_due_reason"] = reason
            due.append(item)
    # Prefer blocked/waiting, then wake, then stale.
    order = {"waiting_on_aryan": 0, "blocked": 1, "next_wake_at": 2, "stale": 3}

    def due_key(c: dict[str, Any]) -> tuple[int, str]:
        return (order.get(str(c.get("_due_reason")), 9), str(c.get("id") or ""))

    due.sort(key=due_key)
    return due[: max(0, limit)]


def get_loop(
    loop_id: str,
    *,
    paths: DataPaths | None = None,
) -> dict[str, Any] | None:
    p = paths or require_ada_data()
    data = _load(p)
    for item in data.get("loops") or []:
        if item.get("id") == loop_id:
            return item
    return None


def upsert_loop(
    *,
    text: str | None = None,
    loop_id: str | None = None,
    status: str | None = None,
    kind: str | None = None,
    title: str | None = None,
    stages: Any = None,
    current_stage: str | None = None,
    blocked_reason: str | None = None,
    next_wake_at: str | None = None,
    last_progress_at: str | None = None,
    last_receipt: str | None = None,
    cadence: str | None = None,
    nudge_attribution: Any = None,
    watches: Any = None,
    delete: bool = False,
    confirmed: bool = False,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    """Create/update an open loop or campaign. Delete / gated done need confirmed."""
    p = _require(paths)
    p.ensure_memory_dirs()
    data = ensure_open_loops(p)
    loops: list[dict[str, Any]] = list(data.get("loops") or [])

    if delete:
        if not loop_id:
            raise ValueError("delete requires loop_id")
        if not confirmed:
            return {
                "ok": False,
                "needs_confirm": True,
                "outcome": "needs_confirm",
                "reason": "delete open_loop requires confirmation",
                "id": loop_id,
            }
        before = len(loops)
        loops = [x for x in loops if x.get("id") != loop_id]
        data["loops"] = loops
        data["schema_version"] = SCHEMA_VERSION
        atomic_write_text(p.open_loops_yaml, _dump(data))
        return {
            "ok": True,
            "outcome": "ok",
            "deleted": before - len(loops),
            "id": loop_id,
        }

    existing: dict[str, Any] | None = None
    if loop_id:
        for item in loops:
            if item.get("id") == loop_id:
                existing = item
                break
        if existing is None:
            return {
                "ok": False,
                "outcome": "error",
                "error": f"open_loop id not found: {loop_id}",
            }

    resolved_kind = str(
        kind
        or (existing.get("kind") if existing else None)
        or KIND_TODO
    ).strip()
    if resolved_kind not in KINDS:
        raise ValueError(f"kind must be one of {sorted(KINDS)}")

    default_status = "active" if resolved_kind == KIND_CAMPAIGN else "open"
    resolved_status = status if status is not None else (
        existing.get("status") if existing else default_status
    )
    resolved_status = _validate_status(resolved_kind, str(resolved_status))

    new_stages: list[dict[str, Any]] | None = None
    if stages is not None:
        new_stages = _normalize_stages(stages)
    elif existing and resolved_kind == KIND_CAMPAIGN:
        new_stages = None  # leave as-is unless provided

    gate_block = _gated_done_needs_confirm(
        existing=existing,
        new_stages=new_stages,
        new_status=resolved_status if status is not None else None,
        last_receipt=last_receipt,
        confirmed=confirmed,
    )
    if gate_block is not None:
        return gate_block

    if cadence is not None and str(cadence) not in CADENCES:
        raise ValueError(f"cadence must be one of {sorted(CADENCES)}")

    new_watches: list[dict[str, Any]] | None = None
    if watches is not None:
        new_watches = _normalize_watches(watches)

    if loop_id and existing is not None:
        if text is not None:
            existing["text"] = str(text).strip()
        if title is not None:
            existing["title"] = str(title).strip()
        elif resolved_kind == KIND_CAMPAIGN and not existing.get("title"):
            existing["title"] = existing.get("text")
        existing["kind"] = resolved_kind
        existing["status"] = resolved_status
        if new_stages is not None:
            existing["stages"] = new_stages
        if current_stage is not None:
            existing["current_stage"] = current_stage or None
        if blocked_reason is not None:
            existing["blocked_reason"] = blocked_reason or None
        if next_wake_at is not None:
            existing["next_wake_at"] = next_wake_at or None
        if last_progress_at is not None:
            existing["last_progress_at"] = last_progress_at or None
        if last_receipt is not None:
            existing["last_receipt"] = last_receipt or None
            if last_receipt:
                existing["last_progress_at"] = existing.get("last_progress_at") or utc_now_iso()
        if cadence is not None:
            existing["cadence"] = cadence
        if nudge_attribution is not None:
            existing["nudge_attribution"] = nudge_attribution
        if new_watches is not None:
            existing["watches"] = new_watches
        existing["updated_at"] = utc_now_iso()
        data["loops"] = loops
        data["schema_version"] = SCHEMA_VERSION
        atomic_write_text(p.open_loops_yaml, _dump(data))
        return {"ok": True, "outcome": "ok", "loop": existing}

    # Create
    if not text or not str(text).strip():
        raise ValueError("text required to create open_loop")
    item: dict[str, Any] = {
        "id": uuid.uuid4().hex[:12],
        "kind": resolved_kind,
        "text": str(text).strip(),
        "status": resolved_status,
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso(),
    }
    if resolved_kind == KIND_CAMPAIGN:
        item["title"] = (title or text).strip()
        item["stages"] = new_stages if new_stages is not None else []
        item["current_stage"] = current_stage
        item["blocked_reason"] = blocked_reason
        item["next_wake_at"] = next_wake_at
        item["last_progress_at"] = last_progress_at
        item["last_receipt"] = last_receipt
        item["cadence"] = cadence or "on_open_only"
        item["nudge_attribution"] = nudge_attribution
        if new_watches is not None:
            item["watches"] = new_watches
    elif title is not None:
        item["title"] = str(title).strip()

    loops.append(item)
    data["loops"] = loops
    data["schema_version"] = SCHEMA_VERSION
    atomic_write_text(p.open_loops_yaml, _dump(data))
    return {"ok": True, "outcome": "ok", "loop": item}


def campaign_check(
    *,
    paths: DataPaths | None = None,
    now: datetime | None = None,
    limit: int = K_DUE_PER_WAKE,
) -> dict[str, Any]:
    """Local due/stale/blocked list for timer/CLI — no LLM.

    Caller should consult proactivity.suppressed() first for quiet/mute.
    """
    due = due_campaigns(paths=paths, now=now, limit=limit)
    return {
        "ok": True,
        "outcome": "ok",
        "suppressed": False,
        "count": len(due),
        "due": [
            {
                "id": c.get("id"),
                "title": c.get("title") or c.get("text"),
                "status": c.get("status"),
                "current_stage": c.get("current_stage"),
                "blocked_reason": c.get("blocked_reason"),
                "due_reason": c.get("_due_reason"),
                "next_wake_at": c.get("next_wake_at"),
            }
            for c in due
        ],
    }
