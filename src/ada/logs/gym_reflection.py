"""Deterministic gym reflection on structured logs (M26) — not Dream, not LLM."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from ada.io.paths import DataPaths, require_ada_data
from ada.logs.connection import open_life_db
from ada.logs.gym import _muscles_for
from ada.logs.gym_split import has_gym_split
from ada.logs.tz_util import preferred_tz_name, utc_to_local_day
from ada.memory.facts import get_fact

MAX_SUMMARY_CHARS = 2_000
_DAY_KEYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def _cap_days(days: int) -> int:
    return max(1, min(int(days), 31))


def _local_days_window(*, days: int, paths: DataPaths | None = None) -> list[str]:
    tz = ZoneInfo(preferred_tz_name(paths=paths))
    today = datetime.now(timezone.utc).astimezone(tz).date()
    return [(today - timedelta(days=i)).isoformat() for i in range(days)]


def _weekday_key(local_day: str) -> str:
    d = datetime.fromisoformat(local_day).date()
    return _DAY_KEYS[d.weekday()]


def _utc_iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _window_utc_bounds(
    calendar_days: list[str], *, paths: DataPaths | None = None
) -> tuple[str, str] | None:
    if not calendar_days:
        return None
    tz = ZoneInfo(preferred_tz_name(paths=paths))
    first = min(calendar_days)
    last = max(calendar_days)
    start_local = datetime.fromisoformat(first).replace(tzinfo=tz)
    end_local = datetime.fromisoformat(last).replace(tzinfo=tz) + timedelta(days=1)
    return _utc_iso_z(start_local), _utc_iso_z(end_local)


def _parse_logged_at(logged: str) -> datetime | None:
    try:
        return datetime.fromisoformat(str(logged or "").replace("Z", "+00:00"))
    except ValueError:
        return None


def _tonnage_of(rows: list[Any]) -> float:
    total = 0.0
    for r in rows:
        load = r["load_kg"] if not isinstance(r, dict) else r.get("load_kg")
        reps = r["reps"] if not isinstance(r, dict) else r.get("reps")
        if load is not None and reps is not None:
            total += float(load) * int(reps)
    return round(total, 1)


def _load_split(paths: DataPaths) -> dict[str, Any] | None:
    if not has_gym_split(paths=paths):
        return None
    doc = get_fact("gym_split", paths=paths)
    val = doc.get("value") if doc.get("found") else None
    return val if isinstance(val, dict) else None


def _split_for_day(
    gym_split: dict[str, Any] | None, local_day: str
) -> dict[str, Any]:
    days = (gym_split or {}).get("days") if isinstance(gym_split, dict) else None
    if not isinstance(days, dict):
        return {"weekday": _weekday_key(local_day), "label": None, "body_parts": []}
    key = _weekday_key(local_day)
    row = days.get(key) if isinstance(days.get(key), dict) else {}
    label = str((row or {}).get("label") or "").strip() or None
    parts_raw = (row or {}).get("body_parts") or []
    parts = [str(p).strip() for p in parts_raw if str(p).strip()] if isinstance(parts_raw, list) else []
    return {"weekday": key, "label": label, "body_parts": parts}


def _set_payload(
    conn,
    row,
    *,
    local_day: str,
    paths: DataPaths | None,
) -> dict[str, Any]:
    muscles, canonical = _muscles_for(
        conn,
        exercise_id=str(row["exercise_id"] or "") or None,
        name=str(row["exercise_name_raw"] or ""),
        paths=paths,
    )
    return {
        "set_id": row["set_id"],
        "session_id": row["session_id"],
        "exercise_id": row["exercise_id"],
        "exercise_name": row["exercise_name_raw"],
        "canonical_name": canonical or row["exercise_name_raw"],
        "load_kg": row["load_kg"],
        "reps": row["reps"],
        "logged_at": row["logged_at"],
        "muscles": muscles,
        "local_day": local_day,
    }


def _session_payloads(conn, session_ids: list[str]) -> list[dict[str, Any]]:
    if not session_ids:
        return []
    placeholders = ",".join("?" for _ in session_ids)
    rows = conn.execute(
        f"""
        SELECT session_id, started_at, ended_at, split_day, status
        FROM gym_sessions
        WHERE session_id IN ({placeholders})
        """,
        session_ids,
    ).fetchall()
    order = {sid: i for i, sid in enumerate(session_ids)}
    out = [
        {
            "session_id": r["session_id"],
            "started_at": r["started_at"],
            "ended_at": r["ended_at"],
            "split_day": r["split_day"],
            "status": r["status"],
        }
        for r in rows
    ]
    out.sort(key=lambda s: order.get(str(s["session_id"]), 0))
    return out


def _collect_window_rows(
    conn,
    calendar_days: list[str],
    *,
    paths: DataPaths,
) -> dict[str, list[Any]]:
    by_day: dict[str, list[Any]] = {d: [] for d in calendar_days}
    bounds = _window_utc_bounds(calendar_days, paths=paths)
    if bounds is None:
        return by_day
    start_utc, end_utc = bounds
    rows = conn.execute(
        """
        SELECT set_id, session_id, exercise_id, exercise_name_raw,
               load_kg, reps, logged_at, sort_order
        FROM gym_sets
        WHERE logged_at >= ? AND logged_at < ?
        ORDER BY logged_at, sort_order
        """,
        (start_utc, end_utc),
    ).fetchall()
    wanted = set(calendar_days)
    for row in rows:
        ts = _parse_logged_at(str(row["logged_at"] or ""))
        if ts is None:
            continue
        local_day = utc_to_local_day(ts, paths=paths)
        if local_day in wanted:
            by_day[local_day].append(row)
    return by_day


def gym_day(
    *,
    date: str | None = None,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    """One local calendar day of gym_sets / sessions — SQL + rules only."""
    p = paths or require_ada_data()
    local_day = date or utc_to_local_day(paths=p)
    gym_split = _load_split(p)
    split_info = _split_for_day(gym_split, local_day)
    try:
        with open_life_db(paths=p) as conn:
            by_day = _collect_window_rows(conn, [local_day], paths=p)
            raw_rows = by_day.get(local_day) or []
            sets = [_set_payload(conn, row, local_day=local_day, paths=p) for row in raw_rows]
            session_ids: list[str] = []
            for row in raw_rows:
                sid = str(row["session_id"] or "")
                if sid and sid not in session_ids:
                    session_ids.append(sid)
            sessions = _session_payloads(conn, session_ids)
    except Exception:  # noqa: BLE001 — reflection must not fail closed on reads
        sets = []
        sessions = []

    tonnage = _tonnage_of(sets)
    cite = f"gym:day:{local_day}"
    if not sets:
        return {
            "ok": True,
            "date": local_day,
            "cite": cite,
            "sessions": [],
            "sets": [],
            "set_count": 0,
            "tonnage_kg": 0.0,
            "split_label": split_info["label"],
            "split_weekday": split_info["weekday"],
            "gym_split": gym_split,
            "summary_text": f"No gym sets logged for {local_day}.",
            "message": f"No gym sets logged for {local_day}.",
        }

    hit_parts: list[str] = []
    for s in sets:
        for m in s.get("muscles") or []:
            token = str(m or "").strip()
            if token and token not in hit_parts:
                hit_parts.append(token)

    summary = (
        f"{cite}: sets={len(sets)} tonnage_kg={tonnage} "
        f"sessions={len(sessions)}"
    )
    if split_info["label"]:
        summary += f" split={split_info['label']}"
    return {
        "ok": True,
        "date": local_day,
        "cite": cite,
        "sessions": sessions,
        "sets": sets,
        "set_count": len(sets),
        "tonnage_kg": tonnage,
        "body_parts": hit_parts,
        "split_label": split_info["label"],
        "split_weekday": split_info["weekday"],
        "gym_split": gym_split,
        "summary_text": summary,
    }


def gym_window(
    *,
    days: int = 7,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    """Last N local calendar days of gym_sets — SQL + rules only."""
    p = paths or require_ada_data()
    window_days = _cap_days(days)
    calendar_days = _local_days_window(days=window_days, paths=p)
    gym_split = _load_split(p)

    try:
        with open_life_db(paths=p) as conn:
            by_day = _collect_window_rows(conn, calendar_days, paths=p)
            days_out: list[dict[str, Any]] = []
            days_logged = 0
            rest_days: list[str] = []
            all_sets_n = 0
            session_ids: set[str] = set()
            tonnage_vals: list[float] = []
            patterns: list[str] = []
            coverage_days: list[dict[str, Any]] = []

            for local_day in calendar_days:
                raw_rows = by_day.get(local_day) or []
                sets = [
                    _set_payload(conn, row, local_day=local_day, paths=p)
                    for row in raw_rows
                ]
                split_info = _split_for_day(gym_split, local_day)
                tonnage = _tonnage_of(sets)
                cite = f"gym:day:{local_day}"
                day_sids: list[str] = []
                for row in raw_rows:
                    sid = str(row["session_id"] or "")
                    if sid and sid not in day_sids:
                        day_sids.append(sid)
                    if sid:
                        session_ids.add(sid)
                hit_parts: list[str] = []
                hit_l: set[str] = set()
                for s in sets:
                    for m in s.get("muscles") or []:
                        token = str(m or "").strip()
                        if token and token not in hit_parts:
                            hit_parts.append(token)
                        if token:
                            hit_l.add(token.lower())
                expected = split_info["body_parts"]
                expected_l = [e.lower() for e in expected]
                missing = [
                    expected[i]
                    for i, el in enumerate(expected_l)
                    if el not in hit_l
                ]
                set_count = len(sets)
                if set_count > 0:
                    days_logged += 1
                    all_sets_n += set_count
                    tonnage_vals.append(tonnage)
                else:
                    rest_days.append(local_day)
                    label = split_info["label"]
                    if label and label.lower() != "rest":
                        patterns.append(f"missed {label} {local_day}")
                if gym_split and expected and set_count > 0 and missing:
                    patterns.append(
                        f"coverage miss {local_day} {split_info['label']}: "
                        + ", ".join(missing)
                    )
                coverage_days.append(
                    {
                        "day": local_day,
                        "label": split_info["label"],
                        "expected_body_parts": expected,
                        "hit_body_parts": hit_parts,
                        "missing_body_parts": missing,
                    }
                )
                days_out.append(
                    {
                        "day": local_day,
                        "cite": cite,
                        "set_count": set_count,
                        "tonnage_kg": tonnage,
                        "session_ids": day_sids,
                        "rest": set_count == 0,
                        "split_label": split_info["label"],
                        "body_parts": hit_parts,
                    }
                )
    except Exception:  # noqa: BLE001
        return {
            "ok": True,
            "window_days": window_days,
            "days_logged": 0,
            "days": [],
            "aggregates": {},
            "rest_days": [],
            "coverage": {"has_split": bool(gym_split)},
            "patterns": [],
            "summary_text": f"No gym sets logged in the last {window_days} days.",
            "message": f"No gym sets logged in the last {window_days} days.",
        }

    if days_logged == 0:
        return {
            "ok": True,
            "window_days": window_days,
            "days_logged": 0,
            "days": [],
            "aggregates": {},
            "rest_days": list(calendar_days),
            "coverage": {"has_split": bool(gym_split)},
            "patterns": [],
            "summary_text": f"No gym sets logged in the last {window_days} days.",
            "message": f"No gym sets logged in the last {window_days} days.",
        }

    aggregates: dict[str, float | int] = {
        "set_count": all_sets_n,
        "session_count": len(session_ids),
        "days_trained": days_logged,
        "rest_day_count": len(rest_days),
    }
    if tonnage_vals:
        aggregates["sum_tonnage_kg"] = round(sum(tonnage_vals), 1)
        aggregates["avg_tonnage_kg"] = round(sum(tonnage_vals) / len(tonnage_vals), 1)

    if rest_days:
        patterns.insert(0, f"rest days {len(rest_days)}/{window_days}")

    lines = [
        f"gym_window (last {window_days} local days, {days_logged} logged):",
    ]
    for d in days_out:
        if d["set_count"] == 0:
            continue
        lines.append(
            f"  {d['cite']}: sets={d['set_count']} tonnage_kg={d['tonnage_kg']}"
        )
    if aggregates:
        lines.append(f"aggregates={json.dumps(aggregates, ensure_ascii=False)}")
    for pat in patterns:
        lines.append(f"pattern: {pat}")
    summary_text = "\n".join(lines)
    if len(summary_text) > MAX_SUMMARY_CHARS:
        summary_text = summary_text[: MAX_SUMMARY_CHARS - 1] + "…"

    return {
        "ok": True,
        "window_days": window_days,
        "days_logged": days_logged,
        "days": days_out,
        "aggregates": aggregates,
        "rest_days": rest_days,
        "coverage": {
            "has_split": bool(gym_split),
            "days": coverage_days if gym_split else [],
        },
        "patterns": patterns,
        "summary_text": summary_text,
    }


def write_gym_reflection_scratch(
    payload: dict[str, Any],
    *,
    paths: DataPaths | None = None,
) -> None:
    """Overwrite scratch artifact for brief/HUD (not WORLDVIEW)."""
    from ada.io.atomic import atomic_write_text

    p = paths or require_ada_data()
    p.scratch.mkdir(parents=True, exist_ok=True)
    target = p.scratch / "gym_reflection_latest.json"
    atomic_write_text(
        target,
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
    )
