"""Today strip payload — dues, reminds, pending, shelf (M16 Phase 1)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ada.io.paths import DataPaths, get_paths
from ada.memory.artifacts import list_artifacts
from ada.memory.open_loops import due_todos, remind_soon_todos
from ada.memory.proactivity import proactivity_suppressed


def _continuity_pulse(paths: DataPaths) -> dict[str, Any] | None:
    """Soft body continuity — no guilt/XP copy."""
    try:
        from ada.body.vitals import collect_vitals, urgent_faults

        snap = collect_vitals()
        urgent = urgent_faults(snap)
        ada_ok = bool(snap.mounts.ada_data_ok) if snap.mounts is not None else None
        if urgent:
            return {
                "kind": "body_attention",
                "label": "Body needs a look",
                "detail": ", ".join(str(u) for u in urgent[:3]),
            }
        if ada_ok is True:
            return {
                "kind": "body_ok",
                "label": "ada-data healthy",
                "detail": "mount ok",
            }
    except Exception:  # noqa: BLE001
        return None
    return None


def _overnight_heads(paths: DataPaths) -> list[dict[str, Any]]:
    """Cheap overnight crumbs for brief/Today (dream/watch heads)."""
    heads: list[dict[str, Any]] = []
    try:
        from ada.dream.run import dream_status

        status = dream_status(paths=paths)
        last_ok = status.get("last_dream_ok")
        if isinstance(last_ok, dict) and last_ok.get("ts"):
            heads.append(
                {
                    "kind": "dream",
                    "ts": last_ok.get("ts"),
                    "label": "Overnight dream",
                    "detail": "dream_ok",
                }
            )
    except Exception:  # noqa: BLE001
        pass
    return heads[:3]


def _running_timer(paths: DataPaths) -> dict[str, Any] | None:
    try:
        from ada.logs.time import get_running

        row = get_running(paths=paths)
        if not row:
            return None
        return {
            "block_id": row["block_id"],
            "kind": row["kind"],
            "label": row.get("label"),
            "started_at": row["started_at"],
        }
    except Exception:  # noqa: BLE001
        return None


def _nutrition_headline(paths: DataPaths) -> dict[str, Any] | None:
    try:
        from ada.logs.meals import nutrition_day

        day = nutrition_day(paths=paths)
        totals = day.get("totals") or {}
        if not totals:
            return None
        return {
            "local_day": day.get("date"),
            "kcal": totals.get("energy_kcal"),
            "protein_g": totals.get("protein_g"),
            "partial": bool(day.get("honest_partial")),
        }
    except Exception:  # noqa: BLE001
        return None


def _meal_gap_nudge(
    paths: DataPaths,
    *,
    now: datetime,
    suppressed: bool,
) -> dict[str, Any] | None:
    if suppressed:
        return None
    try:
        from zoneinfo import ZoneInfo

        from ada.logs.connection import open_life_db
        from ada.logs.tz_util import preferred_tz_name, utc_to_local_day

        tz = ZoneInfo(preferred_tz_name(paths=paths))
        local_now = now.astimezone(tz)
        if local_now.hour < 14:
            return None
        local_day = utc_to_local_day(now=now, paths=paths)
        with open_life_db(paths=paths) as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM meals WHERE local_day = ? AND meal_slot IN ('lunch','dinner')",
                (local_day,),
            ).fetchone()[0]
            last = conn.execute(
                "SELECT logged_at FROM meals WHERE local_day = ? ORDER BY logged_at DESC LIMIT 1",
                (local_day,),
            ).fetchone()
        if count > 0:
            return None
        since_hours = None
        if last:
            from datetime import datetime as dt

            last_ts = dt.fromisoformat(last["logged_at"].replace("Z", "+00:00"))
            since_hours = round((now - last_ts).total_seconds() / 3600, 1)
        return {"suggested_slot": "lunch", "since_hours": since_hours or 5}
    except Exception:  # noqa: BLE001
        return None


def build_today(
    *,
    paths: DataPaths | None = None,
    pending_confirms: list[dict[str, Any]] | None = None,
    last_plan: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Assemble Today strip JSON for HUD / brief."""
    p = paths or get_paths()
    now = now or datetime.now(timezone.utc)
    dues = due_todos(paths=p, now=now, limit=8)
    reminds = remind_soon_todos(paths=p, now=now, within_hours=24.0, limit=8)
    shelf = list_artifacts(paths=p, limit=5)
    suppress = proactivity_suppressed(paths=p, now=now)

    plan_sticky = None
    if last_plan and last_plan.get("status") not in {"accepted", "rejected"}:
        plan_sticky = {
            "plan_id": last_plan.get("plan_id"),
            "status": last_plan.get("status") or "proposed",
            "step_count": len(last_plan.get("steps") or []),
            "summary": (last_plan.get("summary") or last_plan.get("raw_text") or "")[
                :160
            ],
        }

    confirms = list(pending_confirms or [])[:8]
    running_timer = _running_timer(p)
    nutrition_headline = _nutrition_headline(p)
    meal_gap_nudge = _meal_gap_nudge(
        p, now=now, suppressed=bool(suppress.get("suppressed"))
    )

    return {
        "ok": True,
        "ts": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "due_todos": [
            {
                "id": t.get("id"),
                "text": t.get("text"),
                "title": t.get("title"),
                "due_at": t.get("due_at"),
                "remind_at": t.get("remind_at"),
                "starts_at": t.get("starts_at"),
                "ends_at": t.get("ends_at"),
                "people_ids": t.get("people_ids"),
                "artifact_path": t.get("artifact_path"),
            }
            for t in dues
        ],
        "remind_soon": [
            {
                "id": t.get("id"),
                "text": t.get("text"),
                "title": t.get("title"),
                "remind_at": t.get("remind_at"),
                "due_at": t.get("due_at"),
            }
            for t in reminds
        ],
        "pending_confirms": confirms,
        "plan_sticky": plan_sticky,
        "artifacts": shelf,
        "overnight": _overnight_heads(p),
        "continuity": _continuity_pulse(p),
        "suppressed": suppress.get("suppressed"),
        "suppress_reasons": suppress.get("reasons") or [],
        "running_timer": running_timer,
        "nutrition_headline": nutrition_headline,
        "meal_gap_nudge": meal_gap_nudge,
    }
