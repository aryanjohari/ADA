"""Gym session and lift logging (M19a)."""

from __future__ import annotations

import json
import uuid
from typing import Any

from ada.body.vitals import utc_now_iso
from ada.io.paths import DataPaths
from ada.logs.connection import open_life_db
from ada.logs.gym_custom import find_custom_exercise, save_custom_exercise


def _duration_s(started_at: str, ended_at: str) -> int:
    from datetime import datetime

    start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    end = datetime.fromisoformat(ended_at.replace("Z", "+00:00"))
    return max(0, int((end - start).total_seconds()))


def _lookup_exercise(
    conn, name: str, *, paths: DataPaths | None = None
) -> dict[str, Any]:
    row = conn.execute(
        "SELECT * FROM exercise_catalog WHERE lower(canonical_name) = lower(?)",
        (name.strip(),),
    ).fetchone()
    if row:
        return {"exercise_id": row["exercise_id"], "catalog": dict(row), "source": "catalog"}
    rows = conn.execute("SELECT * FROM exercise_catalog").fetchall()
    needle = name.strip().lower()
    for row in rows:
        aliases = json.loads(row["aliases_json"] or "[]")
        if needle == row["canonical_name"].lower():
            return {"exercise_id": row["exercise_id"], "catalog": dict(row), "source": "catalog"}
        if any(needle == a.lower() for a in aliases):
            return {"exercise_id": row["exercise_id"], "catalog": dict(row), "source": "catalog"}
    custom = find_custom_exercise(name, paths=paths)
    if custom:
        return {
            "exercise_id": custom["id"],
            "custom": custom,
            "source": "facts_custom",
            "body_parts": custom.get("body_parts") or [],
        }
    created = save_custom_exercise(display_name=name.strip(), paths=paths)
    return {
        "exercise_id": created["id"],
        "custom": created,
        "source": "facts_custom_new",
        "body_parts": created.get("body_parts") or [],
    }


def gym_start(
    *,
    receipt_id: str,
    split_day: str | None = None,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    session_id = uuid.uuid4().hex
    now = utc_now_iso()
    with open_life_db(paths=paths) as conn:
        conn.execute(
            """
            INSERT INTO gym_sessions (
              session_id, started_at, split_day, status, receipt_id
            ) VALUES (?, ?, ?, 'open', ?)
            """,
            (session_id, now, split_day, receipt_id),
        )
    return {
        "ok": True,
        "session_id": session_id,
        "started_at": now,
        "split_day": split_day,
        "receipt_id": receipt_id,
    }


def _active_session(conn) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM gym_sessions WHERE status = 'open' ORDER BY started_at DESC LIMIT 1"
    ).fetchone()
    return dict(row) if row else None


def lift_log(
    *,
    receipt_id: str,
    sets: list[dict[str, Any]],
    session_id: str | None = None,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    now = utc_now_iso()
    auto_session = False
    with open_life_db(paths=paths) as conn:
        if session_id:
            sess = conn.execute(
                "SELECT * FROM gym_sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
        else:
            sess = _active_session(conn)
        if sess is None:
            auto_session = True
            session_id = uuid.uuid4().hex
            conn.execute(
                """
                INSERT INTO gym_sessions (
                  session_id, started_at, status, receipt_id
                ) VALUES (?, ?, 'open', ?)
                """,
                (session_id, now, receipt_id),
            )
        else:
            session_id = sess["session_id"]
        max_order = conn.execute(
            "SELECT COALESCE(MAX(sort_order), -1) FROM gym_sets WHERE session_id = ?",
            (session_id,),
        ).fetchone()[0]
        set_ids: list[str] = []
        names: list[str] = []
        volume = 0.0
        for idx, s in enumerate(sets):
            ex_name = str(s.get("exercise_name") or s.get("name") or "unknown")
            resolved = _lookup_exercise(conn, ex_name, paths=paths)
            exercise_id = resolved["exercise_id"]
            body_parts = resolved.get("body_parts")
            if body_parts is None and resolved.get("catalog"):
                body_parts = json.loads(resolved["catalog"].get("body_parts_json") or "[]")
            set_id = uuid.uuid4().hex
            load = s.get("load_kg")
            reps = s.get("reps")
            if load is not None and reps is not None:
                volume += float(load) * int(reps)
            conn.execute(
                """
                INSERT INTO gym_sets (
                  set_id, session_id, sort_order, exercise_id, exercise_name_raw,
                  set_type, load_kg, reps, logged_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    set_id,
                    session_id,
                    max_order + 1 + idx,
                    exercise_id,
                    ex_name,
                    s.get("set_type"),
                    load,
                    reps,
                    now,
                ),
            )
            set_ids.append(set_id)
            names.append(ex_name)
    out: dict[str, Any] = {
        "ok": True,
        "session_id": session_id,
        "set_ids": set_ids,
        "exercise_names": names,
        "volume_kg": round(volume, 1),
        "receipt_id": receipt_id,
    }
    if auto_session:
        out["auto_session"] = True
    return out


def gym_end(
    *,
    receipt_id: str,
    session_id: str | None = None,
    notes: str | None = None,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    now = utc_now_iso()
    with open_life_db(paths=paths) as conn:
        if session_id:
            sess = conn.execute(
                "SELECT * FROM gym_sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
        else:
            sess = _active_session(conn)
        if sess is None:
            return {"ok": False, "reason": "no_open_session", "receipt_id": receipt_id}
        session_id = sess["session_id"]
        duration = _duration_s(sess["started_at"], now)
        set_count = conn.execute(
            "SELECT COUNT(*) FROM gym_sets WHERE session_id = ?", (session_id,)
        ).fetchone()[0]
        rows = conn.execute(
            "SELECT load_kg, reps FROM gym_sets WHERE session_id = ?",
            (session_id,),
        ).fetchall()
        tonnage = sum(
            float(r["load_kg"]) * int(r["reps"])
            for r in rows
            if r["load_kg"] is not None and r["reps"] is not None
        )
        conn.execute(
            """
            UPDATE gym_sessions
            SET ended_at = ?, status = 'closed', session_notes = ?
            WHERE session_id = ?
            """,
            (now, notes, session_id),
        )
    return {
        "ok": True,
        "session_id": session_id,
        "duration_s": duration,
        "set_count": set_count,
        "tonnage_kg": round(tonnage, 1),
        "notes": notes,
        "receipt_id": receipt_id,
    }


def gym_status(
    *,
    date: str | None = None,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    """Active session + today's sets + gym_split FACT if present. No PRs/coaching."""
    from datetime import datetime

    from ada.logs.tz_util import utc_to_local_day
    from ada.memory.facts import get_fact

    local_day = date or utc_to_local_day(paths=paths)
    with open_life_db(paths=paths) as conn:
        active = _active_session(conn)
        rows = conn.execute(
            """
            SELECT set_id, session_id, exercise_name_raw, load_kg, reps, logged_at
            FROM gym_sets
            ORDER BY logged_at, sort_order
            """
        ).fetchall()
        session_row = None
        if active:
            session_row = dict(active)
    sets_today: list[dict[str, Any]] = []
    for row in rows:
        logged = str(row["logged_at"] or "")
        try:
            ts = datetime.fromisoformat(logged.replace("Z", "+00:00"))
        except ValueError:
            continue
        if utc_to_local_day(ts, paths=paths) != local_day:
            continue
        sets_today.append(
            {
                "set_id": row["set_id"],
                "session_id": row["session_id"],
                "exercise_name": row["exercise_name_raw"],
                "load_kg": row["load_kg"],
                "reps": row["reps"],
                "logged_at": row["logged_at"],
            }
        )
    split_doc = get_fact("gym_split", paths=paths)
    gym_split = split_doc.get("value") if split_doc.get("found") else None
    return {
        "ok": True,
        "date": local_day,
        "active_session": session_row,
        "sets_today": sets_today,
        "gym_split": gym_split,
    }
