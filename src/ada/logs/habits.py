"""Habit ticks and routines — append-only (M19a P1)."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from ada.body.vitals import utc_now_iso
from ada.io.paths import DataPaths
from ada.logs.connection import open_life_db
from ada.logs.tz_util import preferred_tz_name, utc_to_local_day

_DEFAULT_WINDOW_DAYS = 7


def _normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip().lower())


def _load_aliases(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [str(x).strip().lower() for x in data if str(x).strip()]


def list_habit_definitions(*, paths: DataPaths | None = None) -> list[dict[str, Any]]:
    with open_life_db(paths=paths) as conn:
        rows = conn.execute(
            """
            SELECT habit_id, display_name, aliases_json, schedule_json, active, source
            FROM habit_definitions WHERE active = 1 ORDER BY display_name
            """
        ).fetchall()
    out: list[dict[str, Any]] = []
    for row in rows:
        schedule = {}
        if row["schedule_json"]:
            try:
                schedule = json.loads(row["schedule_json"])
            except json.JSONDecodeError:
                schedule = {}
        out.append(
            {
                "habit_id": row["habit_id"],
                "display_name": row["display_name"],
                "aliases": _load_aliases(row["aliases_json"]),
                "schedule": schedule,
                "source": row["source"],
            }
        )
    return out


def resolve_habit(name: str, *, paths: DataPaths | None = None) -> dict[str, Any]:
    """Resolve habit name/alias to 0/1/many."""
    needle = _normalize_name(name)
    if not needle:
        return {"ok": False, "reason": "empty_name", "matches": []}
    matches: list[dict[str, Any]] = []
    for habit in list_habit_definitions(paths=paths):
        names = {_normalize_name(habit["display_name"])} | set(habit.get("aliases") or [])
        if needle in names or needle == _normalize_name(habit["habit_id"].removeprefix("habit_")):
            matches.append(habit)
    if len(matches) == 1:
        return {"ok": True, "habit_id": matches[0]["habit_id"], "habit": matches[0], "matches": matches}
    return {
        "ok": False,
        "reason": "ambiguous" if len(matches) > 1 else "not_found",
        "match_count": len(matches),
        "matches": matches,
    }


def list_routine_definitions(*, paths: DataPaths | None = None) -> list[dict[str, Any]]:
    with open_life_db(paths=paths) as conn:
        rows = conn.execute(
            """
            SELECT routine_id, display_name, steps_json, eod_sweep, active, source
            FROM routine_definitions WHERE active = 1 ORDER BY display_name
            """
        ).fetchall()
    out: list[dict[str, Any]] = []
    for row in rows:
        steps: list[Any] = []
        if row["steps_json"]:
            try:
                steps = json.loads(row["steps_json"])
            except json.JSONDecodeError:
                steps = []
        out.append(
            {
                "routine_id": row["routine_id"],
                "display_name": row["display_name"],
                "steps": steps,
                "eod_sweep": bool(row["eod_sweep"]),
                "source": row["source"],
            }
        )
    return out


def resolve_routine(name: str, *, paths: DataPaths | None = None) -> dict[str, Any]:
    needle = _normalize_name(name)
    if not needle:
        return {"ok": False, "reason": "empty_name", "matches": []}
    matches: list[dict[str, Any]] = []
    for routine in list_routine_definitions(paths=paths):
        names = {
            _normalize_name(routine["display_name"]),
            _normalize_name(routine["routine_id"].removeprefix("routine_")),
        }
        if needle in names:
            matches.append(routine)
    if len(matches) == 1:
        return {
            "ok": True,
            "routine_id": matches[0]["routine_id"],
            "routine": matches[0],
            "matches": matches,
        }
    return {
        "ok": False,
        "reason": "ambiguous" if len(matches) > 1 else "not_found",
        "match_count": len(matches),
        "matches": matches,
    }


def upsert_habit_definition(
    *,
    habit_id: str,
    display_name: str,
    aliases: list[str] | None = None,
    schedule: dict[str, Any] | None = None,
    source: str = "seed",
    receipt_id: str | None = None,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    now = utc_now_iso()
    with open_life_db(paths=paths) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO habit_definitions (
              habit_id, display_name, aliases_json, schedule_json, active, source,
              receipt_id, created_at
            ) VALUES (?, ?, ?, ?, 1, ?, ?, COALESCE(
              (SELECT created_at FROM habit_definitions WHERE habit_id = ?), ?
            ))
            """,
            (
                habit_id,
                display_name,
                json.dumps(aliases or []),
                json.dumps(schedule or {"windows": ["morning"]}),
                source,
                receipt_id,
                habit_id,
                now,
            ),
        )
    return {"ok": True, "habit_id": habit_id, "display_name": display_name}


def upsert_routine_definition(
    *,
    routine_id: str,
    display_name: str,
    steps: list[dict[str, Any]],
    eod_sweep: bool = False,
    source: str = "seed",
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    now = utc_now_iso()
    with open_life_db(paths=paths) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO routine_definitions (
              routine_id, display_name, steps_json, eod_sweep, active, source, created_at
            ) VALUES (?, ?, ?, ?, 1, ?, COALESCE(
              (SELECT created_at FROM routine_definitions WHERE routine_id = ?), ?
            ))
            """,
            (
                routine_id,
                display_name,
                json.dumps(steps),
                1 if eod_sweep else 0,
                source,
                routine_id,
                now,
            ),
        )
    return {"ok": True, "routine_id": routine_id, "display_name": display_name}


def seed_default_habits(*, paths: DataPaths | None = None) -> dict[str, Any]:
    """Seed minimal habit + routine defs for operator/tests."""
    habits = [
        upsert_habit_definition(
            habit_id="habit_skincare",
            display_name="Skincare",
            aliases=["skincare", "spf"],
            schedule={"windows": ["morning", "evening"]},
            paths=paths,
        ),
    ]
    routines = [
        upsert_routine_definition(
            routine_id="routine_evening",
            display_name="Evening wind-down",
            steps=[{"label": "Skincare", "habit_id": "habit_skincare"}],
            eod_sweep=True,
            paths=paths,
        ),
    ]
    return {"ok": True, "habits": habits, "routines": routines}


def _has_done_today(conn, habit_id: str, local_day: str) -> bool:
    row = conn.execute(
        """
        SELECT 1 FROM habit_events
        WHERE habit_id = ? AND local_day = ? AND kind = 'done'
          AND supersedes_event_id IS NULL
        LIMIT 1
        """,
        (habit_id, local_day),
    ).fetchone()
    return row is not None


def habit_do(
    *,
    habit_id: str | None = None,
    name: str | None = None,
    note: str | None = None,
    receipt_id: str,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    resolved = resolve_habit(name or "", paths=paths) if not habit_id else {"ok": True, "habit_id": habit_id}
    if not habit_id and not resolved.get("ok"):
        return {"ok": False, **resolved}
    hid = habit_id or str(resolved["habit_id"])
    now = utc_now_iso()
    local_day = utc_to_local_day(paths=paths)
    event_id = uuid.uuid4().hex
    with open_life_db(paths=paths) as conn:
        if _has_done_today(conn, hid, local_day):
            return {
                "ok": False,
                "reason": "already_done",
                "habit_id": hid,
                "local_day": local_day,
            }
        conn.execute(
            """
            INSERT INTO habit_events (
              event_id, habit_id, local_day, logged_at, kind, note,
              receipt_id, source_verb
            ) VALUES (?, ?, ?, ?, 'done', ?, ?, 'habit_do')
            """,
            (event_id, hid, local_day, now, note, receipt_id),
        )
    status = habit_status(habit_id=hid, paths=paths)
    return {
        "ok": True,
        "receipt_id": receipt_id,
        "event_id": event_id,
        "habit_id": hid,
        "local_day": local_day,
        "continuity_7d": status.get("habits", [{}])[0].get("continuity_rate")
        if status.get("habits")
        else None,
    }


def habit_miss(
    *,
    habit_id: str | None = None,
    name: str | None = None,
    note: str | None = None,
    receipt_id: str,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    resolved = resolve_habit(name or "", paths=paths) if not habit_id else {"ok": True, "habit_id": habit_id}
    if not habit_id and not resolved.get("ok"):
        return {"ok": False, **resolved}
    hid = habit_id or str(resolved["habit_id"])
    now = utc_now_iso()
    local_day = utc_to_local_day(paths=paths)
    event_id = uuid.uuid4().hex
    with open_life_db(paths=paths) as conn:
        conn.execute(
            """
            INSERT INTO habit_events (
              event_id, habit_id, local_day, logged_at, kind, note,
              receipt_id, source_verb
            ) VALUES (?, ?, ?, ?, 'miss', ?, ?, 'habit_miss')
            """,
            (event_id, hid, local_day, now, note, receipt_id),
        )
    return {
        "ok": True,
        "receipt_id": receipt_id,
        "event_id": event_id,
        "habit_id": hid,
        "local_day": local_day,
        "kind": "miss",
    }


def routine_run(
    *,
    routine_id: str | None = None,
    name: str | None = None,
    steps: list[str] | None = None,
    receipt_id: str,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    resolved = (
        resolve_routine(name or "", paths=paths)
        if not routine_id
        else {"ok": True, "routine_id": routine_id, "routine": {}}
    )
    if not routine_id and not resolved.get("ok"):
        return {"ok": False, **resolved}
    rid = routine_id or str(resolved["routine_id"])
    routine = resolved.get("routine") or {}
    if not routine and rid:
        for item in list_routine_definitions(paths=paths):
            if item["routine_id"] == rid:
                routine = item
                break
    step_defs = routine.get("steps") or []
    steps_done: list[dict[str, Any]] = []
    for step in step_defs:
        label = str(step.get("label") or "")
        habit_id = step.get("habit_id")
        if steps and label and label.lower() not in {s.lower() for s in steps}:
            continue
        tick: dict[str, Any] = {"label": label}
        if habit_id:
            tick_result = habit_do(
                habit_id=str(habit_id),
                receipt_id=receipt_id,
                paths=paths,
            )
            tick["habit_tick"] = tick_result
            if tick_result.get("reason") == "already_done":
                tick["already_done"] = True
        steps_done.append(tick)
    now = utc_now_iso()
    local_day = utc_to_local_day(paths=paths)
    run_id = uuid.uuid4().hex
    with open_life_db(paths=paths) as conn:
        conn.execute(
            """
            INSERT INTO routine_runs (
              run_id, routine_id, local_day, logged_at, steps_done_json, receipt_id
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (run_id, rid, local_day, now, json.dumps(steps_done), receipt_id),
        )
    return {
        "ok": True,
        "receipt_id": receipt_id,
        "run_id": run_id,
        "routine_id": rid,
        "local_day": local_day,
        "steps_done": steps_done,
    }


def _continuity_for_habit(
    conn,
    habit_id: str,
    *,
    window_days: int = _DEFAULT_WINDOW_DAYS,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    tz = ZoneInfo(preferred_tz_name(paths=paths))
    today = datetime.now(tz).date()
    days: list[str] = []
    for offset in range(window_days - 1, -1, -1):
        days.append((today - timedelta(days=offset)).isoformat())
    done_days = 0
    for day in days:
        if conn.execute(
            """
            SELECT 1 FROM habit_events
            WHERE habit_id = ? AND local_day = ? AND kind = 'done'
              AND supersedes_event_id IS NULL LIMIT 1
            """,
            (habit_id, day),
        ).fetchone():
            done_days += 1
    rate = done_days / window_days if window_days else 0.0
    return {
        "habit_id": habit_id,
        "window_days": window_days,
        "done_days": done_days,
        "continuity_rate": round(rate, 3),
    }


def habit_status(
    *,
    habit_id: str | None = None,
    date: str | None = None,
    window_days: int = _DEFAULT_WINDOW_DAYS,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    local_day = date or utc_to_local_day(paths=paths)
    defs = list_habit_definitions(paths=paths)
    if habit_id:
        defs = [d for d in defs if d["habit_id"] == habit_id]
    habits_out: list[dict[str, Any]] = []
    with open_life_db(paths=paths) as conn:
        for habit in defs:
            hid = habit["habit_id"]
            cont = _continuity_for_habit(conn, hid, window_days=window_days, paths=paths)
            done_row = conn.execute(
                """
                SELECT logged_at FROM habit_events
                WHERE habit_id = ? AND local_day = ? AND kind = 'done'
                  AND supersedes_event_id IS NULL LIMIT 1
                """,
                (hid, local_day),
            ).fetchone()
            habits_out.append(
                {
                    **cont,
                    "display_name": habit["display_name"],
                    "done_today": done_row is not None,
                    "logged_at": done_row["logged_at"] if done_row else None,
                }
            )
    overall_rate = (
        sum(h["continuity_rate"] for h in habits_out) / len(habits_out)
        if habits_out
        else 0.0
    )
    return {
        "ok": True,
        "date": local_day,
        "window_days": window_days,
        "habits": habits_out,
        "continuity_rate": round(overall_rate, 3),
    }


def habits_due_today(*, paths: DataPaths | None = None) -> list[dict[str, Any]]:
    """Active defs not ticked done today (morning window v1)."""
    local_day = utc_to_local_day(paths=paths)
    due: list[dict[str, Any]] = []
    with open_life_db(paths=paths) as conn:
        for habit in list_habit_definitions(paths=paths):
            if _has_done_today(conn, habit["habit_id"], local_day):
                continue
            windows = (habit.get("schedule") or {}).get("windows") or ["morning"]
            due.append(
                {
                    "habit_id": habit["habit_id"],
                    "display_name": habit["display_name"],
                    "window": windows[0] if windows else "morning",
                }
            )
    return due


def habits_done_today(*, paths: DataPaths | None = None) -> list[dict[str, Any]]:
    local_day = utc_to_local_day(paths=paths)
    out: list[dict[str, Any]] = []
    with open_life_db(paths=paths) as conn:
        rows = conn.execute(
            """
            SELECT he.habit_id, he.logged_at, hd.display_name
            FROM habit_events he
            JOIN habit_definitions hd ON hd.habit_id = he.habit_id
            WHERE he.local_day = ? AND he.kind = 'done'
              AND he.supersedes_event_id IS NULL
            ORDER BY he.logged_at
            """,
            (local_day,),
        ).fetchall()
        for row in rows:
            out.append(
                {
                    "habit_id": row["habit_id"],
                    "display_name": row["display_name"],
                    "logged_at": row["logged_at"],
                }
            )
    return out
