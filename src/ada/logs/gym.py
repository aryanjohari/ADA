"""Gym session and lift logging (M19a)."""

from __future__ import annotations

import json
import uuid
from typing import Any

from ada.body.vitals import utc_now_iso
from ada.io.paths import DataPaths
from ada.logs.connection import open_life_db
from ada.logs.gym_custom import find_custom_exercise, save_custom_exercise
from ada.logs.gym_import import names_fold_match


def _duration_s(started_at: str, ended_at: str) -> int:
    from datetime import datetime

    start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    end = datetime.fromisoformat(ended_at.replace("Z", "+00:00"))
    return max(0, int((end - start).total_seconds()))


def _catalog_hit(row) -> dict[str, Any]:
    return {
        "exercise_id": row["exercise_id"],
        "catalog": dict(row),
        "source": "catalog",
        "canonical_name": row["canonical_name"],
        "body_parts": json.loads(row["body_parts_json"] or "[]"),
        "movement": row["movement"],
    }


def _lookup_exercise(
    conn, name: str, *, paths: DataPaths | None = None, create_custom: bool = True
) -> dict[str, Any]:
    needle = name.strip()
    row = conn.execute(
        "SELECT * FROM exercise_catalog WHERE lower(canonical_name) = lower(?)",
        (needle,),
    ).fetchone()
    if row:
        return _catalog_hit(row)
    rows = conn.execute("SELECT * FROM exercise_catalog").fetchall()
    needle_l = needle.lower()
    for row in rows:
        aliases = json.loads(row["aliases_json"] or "[]")
        if needle_l == row["canonical_name"].lower():
            return _catalog_hit(row)
        if any(needle_l == str(a).lower() for a in aliases):
            return _catalog_hit(row)
    for row in rows:
        if names_fold_match(needle, row["canonical_name"]):
            return _catalog_hit(row)
        aliases = json.loads(row["aliases_json"] or "[]")
        if any(names_fold_match(needle, str(a)) for a in aliases):
            return _catalog_hit(row)
    custom = find_custom_exercise(name, paths=paths)
    if custom:
        return {
            "exercise_id": custom["id"],
            "custom": custom,
            "source": "facts_custom",
            "canonical_name": custom.get("display_name"),
            "body_parts": custom.get("body_parts") or [],
            "movement": custom.get("movement"),
        }
    if not create_custom:
        return {
            "exercise_id": None,
            "source": "miss",
            "canonical_name": needle,
            "body_parts": [],
            "movement": None,
        }
    created = save_custom_exercise(display_name=name.strip(), paths=paths)
    return {
        "exercise_id": created["id"],
        "custom": created,
        "source": "facts_custom_new",
        "canonical_name": created.get("display_name"),
        "body_parts": created.get("body_parts") or [],
        "movement": created.get("movement"),
    }


def exercise_name_known(name: str, *, paths: DataPaths | None = None) -> bool:
    """True when *name* folds to catalog or an existing custom exercise.

    Does not create a custom on miss — name-only incomplete ask must not
    invent a bind.
    """
    needle = (name or "").strip()
    if not needle:
        return False
    with open_life_db(paths=paths) as conn:
        hit = _lookup_exercise(conn, needle, paths=paths, create_custom=False)
    return str(hit.get("source") or "") in {"catalog", "facts_custom"}


def _muscles_for(
    conn, *, exercise_id: str | None, name: str, paths: DataPaths | None = None
) -> tuple[list[str], str | None]:
    """Catalog (or custom) muscle tags — never invent. Empty list if unknown."""
    if exercise_id:
        row = conn.execute(
            "SELECT body_parts_json, canonical_name FROM exercise_catalog WHERE exercise_id = ?",
            (exercise_id,),
        ).fetchone()
        if row:
            return json.loads(row["body_parts_json"] or "[]"), row["canonical_name"]
    hit = _lookup_exercise(conn, name, paths=paths, create_custom=False)
    muscles = list(hit.get("body_parts") or [])
    canonical = hit.get("canonical_name") if hit.get("source") != "miss" else None
    return muscles, canonical


def _exercise_muscle_summary(
    conn, rows, *, paths: DataPaths | None = None
) -> list[dict[str, Any]]:
    """Unique exercises with catalog muscles for mouth/register (receipt JSON)."""
    summary: list[dict[str, Any]] = []
    index: dict[str, dict[str, Any]] = {}
    for row in rows:
        exercise_id = str(row["exercise_id"] or "")
        name = str(row["exercise_name_raw"] or "")
        key = exercise_id or name.lower()
        if key not in index:
            muscles, canonical = _muscles_for(
                conn, exercise_id=exercise_id or None, name=name, paths=paths
            )
            entry = {
                "exercise_id": exercise_id or None,
                "name": name,
                "canonical_name": canonical or name,
                "set_count": 0,
                "muscles": muscles,
            }
            index[key] = entry
            summary.append(entry)
        index[key]["set_count"] += 1
    return summary


def last_closed_sets(
    exercise_id: str,
    *,
    paths: DataPaths | None = None,
    exclude_session_id: str | None = None,
    conn=None,
) -> list[dict[str, Any]]:
    """Sets for exercise_id from the most recent *closed* session.

    Open sessions are ignored (F-M22 last-weights hygiene). Empty list if none.
    Each row: load_kg, reps, session_id, logged_at, sort_order, set_id.
    """
    eid = str(exercise_id or "").strip()
    if not eid:
        return []

    def _query(c) -> list[dict[str, Any]]:
        params: list[Any] = [eid]
        exclude_sql = ""
        if exclude_session_id:
            exclude_sql = "AND gs.session_id != ?"
            params.append(exclude_session_id)
        session_row = c.execute(
            f"""
            SELECT sess.session_id
            FROM gym_sets gs
            JOIN gym_sessions sess ON sess.session_id = gs.session_id
            WHERE gs.exercise_id = ?
              AND sess.status = 'closed'
              {exclude_sql}
            ORDER BY COALESCE(sess.ended_at, sess.started_at) DESC, gs.logged_at DESC
            LIMIT 1
            """,
            params,
        ).fetchone()
        if session_row is None:
            return []
        sid = session_row["session_id"]
        rows = c.execute(
            """
            SELECT set_id, session_id, load_kg, reps, logged_at, sort_order
            FROM gym_sets
            WHERE session_id = ? AND exercise_id = ?
            ORDER BY sort_order ASC, logged_at ASC
            """,
            (sid, eid),
        ).fetchall()
        return [
            {
                "set_id": r["set_id"],
                "session_id": r["session_id"],
                "load_kg": r["load_kg"],
                "reps": r["reps"],
                "logged_at": r["logged_at"],
                "sort_order": r["sort_order"],
            }
            for r in rows
        ]

    if conn is not None:
        return _query(conn)
    with open_life_db(paths=paths) as c:
        return _query(c)


def last_closed_receipt_fields(
    exercise_id: str,
    *,
    paths: DataPaths | None = None,
    exclude_session_id: str | None = None,
    conn=None,
) -> dict[str, Any] | None:
    """Singular last_* fields from the latest set in last_closed_sets (or None)."""
    rows = last_closed_sets(
        exercise_id,
        paths=paths,
        exclude_session_id=exclude_session_id,
        conn=conn,
    )
    if not rows:
        return None
    last = rows[-1]
    return {
        "last_load_kg": last.get("load_kg"),
        "last_reps": last.get("reps"),
        "last_session_id": last.get("session_id"),
        "last_logged_at": last.get("logged_at"),
    }


def last_open_session_exercise_name(
    *,
    paths: DataPaths | None = None,
    conn=None,
) -> str | None:
    """Raw name of the latest set in the currently OPEN session.

    Follow-on lock target only. Last-closed (prior bout) is never returned.
    None if no open session or no set in this bout.
    """

    def _query(c) -> str | None:
        sess = _active_session(c)
        if sess is None:
            return None
        row = c.execute(
            """
            SELECT exercise_name_raw
            FROM gym_sets
            WHERE session_id = ?
            ORDER BY sort_order DESC, logged_at DESC
            LIMIT 1
            """,
            (sess["session_id"],),
        ).fetchone()
        if row is None:
            return None
        name = str(row["exercise_name_raw"] or "").strip()
        return name or None

    if conn is not None:
        return _query(conn)
    with open_life_db(paths=paths) as c:
        return _query(c)


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
        resolved_rows: list[dict[str, Any]] = []
        written_sets: list[dict[str, Any]] = []
        volume = 0.0
        for idx, s in enumerate(sets):
            ex_name = str(s.get("exercise_name") or s.get("name") or "unknown")
            resolved = _lookup_exercise(conn, ex_name, paths=paths)
            exercise_id = resolved["exercise_id"]
            body_parts = resolved.get("body_parts")
            if body_parts is None and resolved.get("catalog"):
                body_parts = json.loads(resolved["catalog"].get("body_parts_json") or "[]")
            prior = None
            if exercise_id:
                prior = last_closed_receipt_fields(
                    str(exercise_id),
                    exclude_session_id=session_id,
                    conn=conn,
                    paths=paths,
                )
            # Current set numbers — same values written to SQLite (mouth reads these).
            load = s.get("load_kg")
            reps = s.get("reps")
            row_out: dict[str, Any] = {
                "raw": ex_name,
                "exercise_name": ex_name,
                "source": resolved.get("source"),
                "exercise_id": exercise_id,
                "canonical_name": resolved.get("canonical_name"),
                "body_parts": body_parts or [],
                "movement": resolved.get("movement")
                or (resolved.get("custom") or {}).get("movement"),
                "load_kg": load,
                "reps": reps,
            }
            if prior:
                row_out.update(prior)
                # last_* must not overwrite the just-logged set.
                row_out["load_kg"] = load
                row_out["reps"] = reps
            resolved_rows.append(row_out)
            set_id = uuid.uuid4().hex
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
            written_sets.append(
                {
                    "set_id": set_id,
                    "exercise_id": exercise_id,
                    "exercise_name": ex_name,
                    "load_kg": load,
                    "reps": reps,
                }
            )
    # Top-level last_* from first resolved exercise that has prior closed data.
    prior_top: dict[str, Any] | None = None
    for row in resolved_rows:
        if row.get("last_session_id"):
            prior_top = {
                "last_load_kg": row.get("last_load_kg"),
                "last_reps": row.get("last_reps"),
                "last_session_id": row.get("last_session_id"),
                "last_logged_at": row.get("last_logged_at"),
            }
            break
    out: dict[str, Any] = {
        "ok": True,
        "session_id": session_id,
        "set_ids": set_ids,
        "exercise_names": names,
        "resolved": resolved_rows,
        "sets": written_sets,
        "volume_kg": round(volume, 1),
        "receipt_id": receipt_id,
    }
    if prior_top:
        out.update(prior_top)
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
        set_rows = conn.execute(
            """
            SELECT exercise_id, exercise_name_raw, load_kg, reps
            FROM gym_sets WHERE session_id = ?
            ORDER BY sort_order, logged_at
            """,
            (session_id,),
        ).fetchall()
        set_count = len(set_rows)
        tonnage = sum(
            float(r["load_kg"]) * int(r["reps"])
            for r in set_rows
            if r["load_kg"] is not None and r["reps"] is not None
        )
        exercises = _exercise_muscle_summary(conn, set_rows, paths=paths)
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
        "exercises": exercises,
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
            SELECT set_id, session_id, exercise_id, exercise_name_raw, load_kg, reps, logged_at
            FROM gym_sets
            ORDER BY logged_at, sort_order
            """
        ).fetchall()
        session_row = dict(active) if active else None
        sets_today: list[dict[str, Any]] = []
        today_rows = []
        for row in rows:
            logged = str(row["logged_at"] or "")
            try:
                ts = datetime.fromisoformat(logged.replace("Z", "+00:00"))
            except ValueError:
                continue
            if utc_to_local_day(ts, paths=paths) != local_day:
                continue
            today_rows.append(row)
            muscles, canonical = _muscles_for(
                conn,
                exercise_id=str(row["exercise_id"] or "") or None,
                name=str(row["exercise_name_raw"] or ""),
                paths=paths,
            )
            sets_today.append(
                {
                    "set_id": row["set_id"],
                    "session_id": row["session_id"],
                    "exercise_id": row["exercise_id"],
                    "exercise_name": row["exercise_name_raw"],
                    "canonical_name": canonical or row["exercise_name_raw"],
                    "load_kg": row["load_kg"],
                    "reps": row["reps"],
                    "logged_at": row["logged_at"],
                    "muscles": muscles,
                }
            )
        exercises_today = _exercise_muscle_summary(conn, today_rows, paths=paths)
        exclude_sid = session_row["session_id"] if session_row else None
        for ex in exercises_today:
            eid = ex.get("exercise_id")
            if not eid:
                continue
            prior = last_closed_receipt_fields(
                str(eid),
                exclude_session_id=exclude_sid,
                conn=conn,
                paths=paths,
            )
            if prior:
                ex.update(prior)
        for s in sets_today:
            eid = s.get("exercise_id")
            if not eid or s.get("last_session_id"):
                continue
            prior = last_closed_receipt_fields(
                str(eid),
                exclude_session_id=exclude_sid,
                conn=conn,
                paths=paths,
            )
            if prior:
                s.update(prior)
    split_doc = get_fact("gym_split", paths=paths)
    gym_split = split_doc.get("value") if split_doc.get("found") else None
    return {
        "ok": True,
        "date": local_day,
        "active_session": session_row,
        "sets_today": sets_today,
        "exercises_today": exercises_today,
        "set_count": len(sets_today),
        "gym_split": gym_split,
    }
