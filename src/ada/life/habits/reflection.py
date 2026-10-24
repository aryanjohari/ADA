"""Deterministic habit reflection on structured logs (M26) — not Dream, not LLM."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from ada.io.paths import DataPaths, require_ada_data
from ada.logs.connection import open_life_db
from ada.logs.tz_util import preferred_tz_name, utc_to_local_day

MAX_SUMMARY_CHARS = 2_000


def _cap_days(days: int) -> int:
    return max(1, min(int(days), 31))


def _local_days_window(*, days: int, paths: DataPaths | None = None) -> list[str]:
    tz = ZoneInfo(preferred_tz_name(paths=paths))
    today = datetime.now(timezone.utc).astimezone(tz).date()
    return [(today - timedelta(days=i)).isoformat() for i in range(days)]


def _event_payload(row, *, local_day: str) -> dict[str, Any]:
    kind = row["kind"] if not isinstance(row, dict) else row.get("kind")
    return {
        "event_id": row["event_id"] if not isinstance(row, dict) else row.get("event_id"),
        "habit_id": row["habit_id"] if not isinstance(row, dict) else row.get("habit_id"),
        "display_name": (
            row["display_name"] if not isinstance(row, dict) else row.get("display_name")
        ),
        "kind": kind,
        "logged_at": (
            row["logged_at"] if not isinstance(row, dict) else row.get("logged_at")
        ),
        "local_day": local_day,
    }


def _collect_window_rows(
    conn,
    calendar_days: list[str],
) -> dict[str, list[Any]]:
    by_day: dict[str, list[Any]] = {d: [] for d in calendar_days}
    if not calendar_days:
        return by_day
    placeholders = ",".join("?" for _ in calendar_days)
    rows = conn.execute(
        f"""
        SELECT he.event_id, he.habit_id, he.local_day, he.logged_at, he.kind,
               hd.display_name
        FROM habit_events he
        JOIN habit_definitions hd ON hd.habit_id = he.habit_id
        WHERE he.local_day IN ({placeholders})
          AND he.supersedes_event_id IS NULL
        ORDER BY he.logged_at
        """,
        tuple(calendar_days),
    ).fetchall()
    wanted = set(calendar_days)
    for row in rows:
        local_day = str(row["local_day"] or "")
        if local_day in wanted:
            by_day[local_day].append(row)
    return by_day


def _counts(events: list[dict[str, Any]]) -> tuple[int, int]:
    done = sum(1 for e in events if e.get("kind") == "done")
    miss = sum(1 for e in events if e.get("kind") == "miss")
    return done, miss


def habit_day(
    *,
    date: str | None = None,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    """One local calendar day of habit_events — SQL + rules only.

    Honest absence = empty events, not invented misses.
    """
    p = paths or require_ada_data()
    local_day = date or utc_to_local_day(paths=p)
    cite = f"habit:day:{local_day}"
    try:
        with open_life_db(paths=p) as conn:
            by_day = _collect_window_rows(conn, [local_day])
            raw_rows = by_day.get(local_day) or []
            events = [_event_payload(row, local_day=local_day) for row in raw_rows]
    except Exception:  # noqa: BLE001 — reflection must not fail closed on reads
        events = []

    done_count, miss_count = _counts(events)
    if not events:
        return {
            "ok": True,
            "date": local_day,
            "cite": cite,
            "events": [],
            "event_count": 0,
            "done_count": 0,
            "miss_count": 0,
            "summary_text": f"No habit ticks for {local_day}.",
            "message": f"No habit ticks for {local_day}.",
        }

    summary = (
        f"{cite}: events={len(events)} done={done_count} miss={miss_count}"
    )
    return {
        "ok": True,
        "date": local_day,
        "cite": cite,
        "events": events,
        "event_count": len(events),
        "done_count": done_count,
        "miss_count": miss_count,
        "summary_text": summary,
    }


def habit_window(
    *,
    days: int = 7,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    """Last N local calendar days of habit_events — SQL + rules only."""
    p = paths or require_ada_data()
    window_days = _cap_days(days)
    calendar_days = _local_days_window(days=window_days, paths=p)

    try:
        with open_life_db(paths=p) as conn:
            by_day = _collect_window_rows(conn, calendar_days)
            n_habits = int(
                conn.execute(
                    "SELECT COUNT(*) AS n FROM habit_definitions WHERE active = 1"
                ).fetchone()["n"]
            )
            days_out: list[dict[str, Any]] = []
            days_logged = 0
            empty_days: list[str] = []
            all_events_n = 0
            done_total = 0
            miss_total = 0
            done_habit_days = 0

            for local_day in calendar_days:
                raw_rows = by_day.get(local_day) or []
                events = [
                    _event_payload(row, local_day=local_day) for row in raw_rows
                ]
                done_count, miss_count = _counts(events)
                cite = f"habit:day:{local_day}"
                event_count = len(events)
                if event_count > 0:
                    days_logged += 1
                    all_events_n += event_count
                    done_total += done_count
                    miss_total += miss_count
                    done_habit_days += len(
                        {
                            e.get("habit_id")
                            for e in events
                            if e.get("kind") == "done" and e.get("habit_id")
                        }
                    )
                else:
                    empty_days.append(local_day)
                days_out.append(
                    {
                        "day": local_day,
                        "cite": cite,
                        "event_count": event_count,
                        "done_count": done_count,
                        "miss_count": miss_count,
                        "empty": event_count == 0,
                    }
                )
    except Exception:  # noqa: BLE001
        return {
            "ok": True,
            "window_days": window_days,
            "days_logged": 0,
            "days": [],
            "aggregates": {},
            "empty_days": [],
            "summary_text": f"No habit ticks in the last {window_days} days.",
            "message": f"No habit ticks in the last {window_days} days.",
        }

    if days_logged == 0:
        return {
            "ok": True,
            "window_days": window_days,
            "days_logged": 0,
            "days": [],
            "aggregates": {},
            "empty_days": list(calendar_days),
            "summary_text": f"No habit ticks in the last {window_days} days.",
            "message": f"No habit ticks in the last {window_days} days.",
        }

    denom = n_habits * window_days if n_habits else 0
    continuity_rate = round(done_habit_days / denom, 3) if denom else 0.0
    continuity_pct = int(round(continuity_rate * 100))
    aggregates: dict[str, Any] = {
        "event_count": all_events_n,
        "days_logged": days_logged,
        "empty_day_count": len(empty_days),
        "done_count": done_total,
        "miss_count": miss_total,
        "continuity_rate": continuity_rate,
        "continuity_pct": continuity_pct,
    }

    lines = [
        f"habit_window (last {window_days} local days, {days_logged} logged):",
    ]
    for d in days_out:
        if d["event_count"] == 0:
            continue
        lines.append(
            f"  {d['cite']}: events={d['event_count']} "
            f"done={d['done_count']} miss={d['miss_count']}"
        )
    lines.append(f"aggregates={json.dumps(aggregates, ensure_ascii=False)}")
    summary_text = "\n".join(lines)
    if len(summary_text) > MAX_SUMMARY_CHARS:
        summary_text = summary_text[: MAX_SUMMARY_CHARS - 1] + "…"

    return {
        "ok": True,
        "window_days": window_days,
        "days_logged": days_logged,
        "days": days_out,
        "aggregates": aggregates,
        "empty_days": empty_days,
        "continuity_rate": continuity_rate,
        "continuity_pct": continuity_pct,
        "summary_text": summary_text,
    }


def write_habit_reflection_scratch(
    payload: dict[str, Any],
    *,
    paths: DataPaths | None = None,
) -> None:
    """Overwrite scratch artifact for brief/HUD (not WORLDVIEW)."""
    from ada.io.atomic import atomic_write_text

    p = paths or require_ada_data()
    p.scratch.mkdir(parents=True, exist_ok=True)
    target = p.scratch / "habit_reflection_latest.json"
    atomic_write_text(
        target,
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
    )
