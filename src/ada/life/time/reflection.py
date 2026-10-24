"""Deterministic time reflection on structured logs (M26) — not Dream, not LLM."""

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


def _parse_started_at(started: str) -> datetime | None:
    try:
        return datetime.fromisoformat(str(started or "").replace("Z", "+00:00"))
    except ValueError:
        return None


def _block_payload(row, *, local_day: str) -> dict[str, Any]:
    duration = row["duration_s"] if not isinstance(row, dict) else row.get("duration_s")
    duration_s = int(duration) if duration is not None else None
    return {
        "block_id": row["block_id"] if not isinstance(row, dict) else row.get("block_id"),
        "kind": row["kind"] if not isinstance(row, dict) else row.get("kind"),
        "label": row["label"] if not isinstance(row, dict) else row.get("label"),
        "started_at": row["started_at"] if not isinstance(row, dict) else row.get("started_at"),
        "ended_at": row["ended_at"] if not isinstance(row, dict) else row.get("ended_at"),
        "duration_s": duration_s,
        "status": row["status"] if not isinstance(row, dict) else row.get("status"),
        "local_day": local_day,
    }


def _by_kind(blocks: list[dict[str, Any]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for b in blocks:
        dur = b.get("duration_s")
        if dur is None:
            continue
        kind = str(b.get("kind") or "custom")
        out[kind] = out.get(kind, 0) + int(dur)
    return out


def _sum_duration(blocks: list[dict[str, Any]]) -> int:
    total = 0
    for b in blocks:
        dur = b.get("duration_s")
        if dur is not None:
            total += int(dur)
    return total


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
        SELECT block_id, kind, label, started_at, ended_at, duration_s, status
        FROM time_blocks
        WHERE started_at >= ? AND started_at < ?
        ORDER BY started_at
        """,
        (start_utc, end_utc),
    ).fetchall()
    wanted = set(calendar_days)
    for row in rows:
        ts = _parse_started_at(str(row["started_at"] or ""))
        if ts is None:
            continue
        local_day = utc_to_local_day(ts, paths=paths)
        if local_day in wanted:
            by_day[local_day].append(row)
    return by_day


def time_day(
    *,
    date: str | None = None,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    """One local calendar day of time_blocks — SQL + rules only.

    Local-day attribution uses started_at (sleep spanning midnight = start day).
    duration_s is copied from the row — never invented.
    """
    p = paths or require_ada_data()
    local_day = date or utc_to_local_day(paths=p)
    cite = f"time:day:{local_day}"
    try:
        with open_life_db(paths=p) as conn:
            by_day = _collect_window_rows(conn, [local_day], paths=p)
            raw_rows = by_day.get(local_day) or []
            blocks = [_block_payload(row, local_day=local_day) for row in raw_rows]
    except Exception:  # noqa: BLE001 — reflection must not fail closed on reads
        blocks = []

    if not blocks:
        return {
            "ok": True,
            "date": local_day,
            "cite": cite,
            "blocks": [],
            "block_count": 0,
            "duration_s": 0,
            "by_kind": {},
            "summary_text": f"No time blocks logged for {local_day}.",
            "message": f"No time blocks logged for {local_day}.",
        }

    by_kind = _by_kind(blocks)
    duration_s = _sum_duration(blocks)
    summary = f"{cite}: blocks={len(blocks)} duration_s={duration_s}"
    if by_kind:
        summary += f" by_kind={json.dumps(by_kind, ensure_ascii=False)}"
    return {
        "ok": True,
        "date": local_day,
        "cite": cite,
        "blocks": blocks,
        "block_count": len(blocks),
        "duration_s": duration_s,
        "by_kind": by_kind,
        "summary_text": summary,
    }


def time_window(
    *,
    days: int = 7,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    """Last N local calendar days of time_blocks — SQL + rules only."""
    p = paths or require_ada_data()
    window_days = _cap_days(days)
    calendar_days = _local_days_window(days=window_days, paths=p)

    try:
        with open_life_db(paths=p) as conn:
            by_day = _collect_window_rows(conn, calendar_days, paths=p)
            days_out: list[dict[str, Any]] = []
            days_logged = 0
            empty_days: list[str] = []
            all_blocks_n = 0
            duration_vals: list[int] = []

            for local_day in calendar_days:
                raw_rows = by_day.get(local_day) or []
                blocks = [
                    _block_payload(row, local_day=local_day) for row in raw_rows
                ]
                duration_s = _sum_duration(blocks)
                cite = f"time:day:{local_day}"
                block_count = len(blocks)
                if block_count > 0:
                    days_logged += 1
                    all_blocks_n += block_count
                    duration_vals.append(duration_s)
                else:
                    empty_days.append(local_day)
                days_out.append(
                    {
                        "day": local_day,
                        "cite": cite,
                        "block_count": block_count,
                        "duration_s": duration_s,
                        "by_kind": _by_kind(blocks),
                        "empty": block_count == 0,
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
            "summary_text": f"No time blocks logged in the last {window_days} days.",
            "message": f"No time blocks logged in the last {window_days} days.",
        }

    if days_logged == 0:
        return {
            "ok": True,
            "window_days": window_days,
            "days_logged": 0,
            "days": [],
            "aggregates": {},
            "empty_days": list(calendar_days),
            "summary_text": f"No time blocks logged in the last {window_days} days.",
            "message": f"No time blocks logged in the last {window_days} days.",
        }

    aggregates: dict[str, int] = {
        "block_count": all_blocks_n,
        "days_logged": days_logged,
        "empty_day_count": len(empty_days),
        "sum_duration_s": sum(duration_vals),
    }

    lines = [
        f"time_window (last {window_days} local days, {days_logged} logged):",
    ]
    for d in days_out:
        if d["block_count"] == 0:
            continue
        lines.append(
            f"  {d['cite']}: blocks={d['block_count']} duration_s={d['duration_s']}"
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
        "summary_text": summary_text,
    }


def write_time_reflection_scratch(
    payload: dict[str, Any],
    *,
    paths: DataPaths | None = None,
) -> None:
    """Overwrite scratch artifact for brief/HUD (not WORLDVIEW)."""
    from ada.io.atomic import atomic_write_text

    p = paths or require_ada_data()
    p.scratch.mkdir(parents=True, exist_ok=True)
    target = p.scratch / "time_reflection_latest.json"
    atomic_write_text(
        target,
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
    )
