"""Time block capture — single active timer policy (M19a)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from ada.body.vitals import utc_now_iso
from ada.io.paths import DataPaths
from ada.logs.connection import open_life_db


def _now_iso() -> str:
    return utc_now_iso()


def _duration_s(started_at: str, ended_at: str) -> int:
    start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    end = datetime.fromisoformat(ended_at.replace("Z", "+00:00"))
    return max(0, int((end - start).total_seconds()))


def get_running(*, paths: DataPaths | None = None) -> dict[str, Any] | None:
    with open_life_db(paths=paths) as conn:
        row = conn.execute(
            "SELECT * FROM time_blocks WHERE status = 'running' LIMIT 1"
        ).fetchone()
    if row is None:
        return None
    return dict(row)


def _close_running(
    conn,
    *,
    ended_at: str,
    status: str,
    auto_stopped_by: str | None = None,
) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM time_blocks WHERE status = 'running' LIMIT 1"
    ).fetchone()
    if row is None:
        return None
    duration = _duration_s(row["started_at"], ended_at)
    conn.execute(
        """
        UPDATE time_blocks
        SET ended_at = ?, duration_s = ?, status = ?, auto_stopped_by = ?
        WHERE block_id = ?
        """,
        (ended_at, duration, status, auto_stopped_by, row["block_id"]),
    )
    return dict(row)


def start_block(
    *,
    kind: str,
    label: str | None = None,
    receipt_id: str,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    """Start a time block; auto-stop any prior running block."""
    now = _now_iso()
    block_id = uuid.uuid4().hex
    stopped_prior: dict[str, Any] | None = None
    with open_life_db(paths=paths) as conn:
        stopped_prior = _close_running(
            conn,
            ended_at=now,
            status="orphan_closed",
            auto_stopped_by=block_id,
        )
        conn.execute(
            """
            INSERT INTO time_blocks (
              block_id, kind, label, started_at, status, receipt_id
            ) VALUES (?, ?, ?, ?, 'running', ?)
            """,
            (block_id, kind, label, now, receipt_id),
        )
    out: dict[str, Any] = {
        "ok": True,
        "block_id": block_id,
        "kind": kind,
        "label": label,
        "started_at": now,
        "receipt_id": receipt_id,
    }
    if stopped_prior:
        out["auto_stopped_prior"] = stopped_prior["block_id"]
    return out


def stop_block(
    *,
    block_id: str | None = None,
    receipt_id: str,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    now = _now_iso()
    with open_life_db(paths=paths) as conn:
        if block_id:
            row = conn.execute(
                "SELECT * FROM time_blocks WHERE block_id = ? AND status = 'running'",
                (block_id,),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM time_blocks WHERE status = 'running' LIMIT 1"
            ).fetchone()
        if row is None:
            return {"ok": False, "reason": "no_active_block", "receipt_id": receipt_id}
        duration = _duration_s(row["started_at"], now)
        conn.execute(
            """
            UPDATE time_blocks
            SET ended_at = ?, duration_s = ?, status = 'stopped'
            WHERE block_id = ?
            """,
            (now, duration, row["block_id"]),
        )
    return {
        "ok": True,
        "block_id": row["block_id"],
        "kind": row["kind"],
        "duration_s": duration,
        "receipt_id": receipt_id,
    }


def time_status(*, paths: DataPaths | None = None) -> dict[str, Any]:
    from ada.logs.tz_util import utc_to_local_day

    local_day = utc_to_local_day(paths=paths)
    with open_life_db(paths=paths) as conn:
        active = conn.execute(
            "SELECT * FROM time_blocks WHERE status = 'running' LIMIT 1"
        ).fetchone()
        rows = conn.execute(
            "SELECT * FROM time_blocks WHERE started_at >= ? ORDER BY started_at",
            (f"{local_day}T",),
        ).fetchall()
    blocks_today = [dict(r) for r in rows]
    by_kind: dict[str, int] = {}
    for b in blocks_today:
        if b.get("duration_s"):
            by_kind[b["kind"]] = by_kind.get(b["kind"], 0) + int(b["duration_s"])
    out: dict[str, Any] = {
        "ok": True,
        "blocks_today": blocks_today,
        "by_kind": by_kind,
    }
    if active:
        out["active"] = {
            "block_id": active["block_id"],
            "kind": active["kind"],
            "label": active["label"],
            "started_at": active["started_at"],
        }
    return out
