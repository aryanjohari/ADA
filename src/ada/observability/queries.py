"""Read-only SQL helpers for observability (sqlite3, SELECT only)."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from ada.observability.sanitize import (
    action_payload_safe,
    field_digest,
    json_blob_digest,
    truncate_error,
)


def open_readonly_connection(db_path: Path) -> sqlite3.Connection:
    """Open SQLite in URI read-only mode (WAL-compatible shared cache)."""
    abs_path = db_path.expanduser().resolve()
    uri_path = abs_path.as_posix()
    uri = f"file:{uri_path}?mode=ro&cache=shared"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (name,),
    )
    return cur.fetchone() is not None


def tasks_pending_failed(conn: sqlite3.Connection, *, limit: int = 200) -> list[dict[str, Any]]:
    cur = conn.execute(
        """
        SELECT id, status, task_kind, created_at, updated_at, goal, current_output, plan_json
        FROM tasks
        WHERE status IN ('pending', 'failed')
        ORDER BY updated_at DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows: list[dict[str, Any]] = []
    for r in cur.fetchall():
        g = r["goal"] or ""
        co = r["current_output"] or ""
        pj = r["plan_json"] or ""
        rows.append(
            {
                "id": r["id"],
                "status": r["status"],
                "task_kind": r["task_kind"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
                "goal_digest": field_digest(g),
                "current_output_digest": field_digest(co),
                "plan_json_digest": field_digest(pj),
            }
        )
    return rows


def workflows_recent(conn: sqlite3.Connection, *, limit: int = 80) -> list[dict[str, Any]]:
    if not _table_exists(conn, "workflows"):
        return []
    cur = conn.execute(
        """
        SELECT id, kind, status, parent_task_id, created_at, updated_at, idempotency_key, goal_text
        FROM workflows
        ORDER BY updated_at DESC
        LIMIT ?
        """,
        (limit,),
    )
    out: list[dict[str, Any]] = []
    for r in cur.fetchall():
        gt = r["goal_text"] or ""
        out.append(
            {
                "id": r["id"],
                "kind": r["kind"],
                "status": r["status"],
                "parent_task_id": r["parent_task_id"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
                "idempotency_key": r["idempotency_key"],
                "goal_text_digest": field_digest(gt),
            }
        )
    return out


def workflow_steps_recent(conn: sqlite3.Connection, *, limit: int = 150) -> list[dict[str, Any]]:
    if not _table_exists(conn, "workflow_steps"):
        return []
    cur = conn.execute(
        """
        SELECT ws.id, ws.workflow_id, ws.step_index, ws.step_type, ws.status,
               ws.attempt_count, ws.error, ws.input_json, ws.output_json, ws.task_id,
               ws.created_at, ws.updated_at, w.kind AS workflow_kind
        FROM workflow_steps ws
        JOIN workflows w ON w.id = ws.workflow_id
        ORDER BY ws.updated_at DESC
        LIMIT ?
        """,
        (limit,),
    )
    out: list[dict[str, Any]] = []
    for r in cur.fetchall():
        err = r["error"] or ""
        ij = r["input_json"] or ""
        oj = r["output_json"] or ""
        out.append(
            {
                "id": r["id"],
                "workflow_id": r["workflow_id"],
                "workflow_kind": r["workflow_kind"],
                "step_index": r["step_index"],
                "step_type": r["step_type"],
                "status": r["status"],
                "attempt_count": r["attempt_count"],
                "error_preview": truncate_error(err),
                "input_json_digest": json_blob_digest(ij),
                "output_json_digest": json_blob_digest(oj),
                "task_id": r["task_id"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            }
        )
    return out


def usage_rollup_by_utc_day(conn: sqlite3.Connection, *, days: int = 14) -> list[dict[str, Any]]:
    cur = conn.execute(
        """
        SELECT date(recorded_at) AS d,
               SUM(COALESCE(input_tokens, 0)) AS input_tokens,
               SUM(COALESCE(output_tokens, 0)) AS output_tokens,
               COUNT(*) AS rows_n
        FROM usage_ledger
        WHERE recorded_at >= datetime('now', ?)
        GROUP BY date(recorded_at)
        ORDER BY d DESC
        """,
        (f"-{int(days)} days",),
    )
    return [dict(r) for r in cur.fetchall()]


def usage_rollup_by_iso_week(conn: sqlite3.Connection, *, weeks: int = 8) -> list[dict[str, Any]]:
    cur = conn.execute(
        """
        SELECT strftime('%Y-W%W', recorded_at) AS wk,
               SUM(COALESCE(input_tokens, 0)) AS input_tokens,
               SUM(COALESCE(output_tokens, 0)) AS output_tokens,
               COUNT(*) AS rows_n
        FROM usage_ledger
        WHERE recorded_at >= datetime('now', ?)
        GROUP BY strftime('%Y-W%W', recorded_at)
        ORDER BY wk DESC
        """,
        (f"-{int(weeks) * 7} days",),
    )
    return [dict(r) for r in cur.fetchall()]


def usage_by_session_and_kind(
    conn: sqlite3.Connection, *, limit_sessions: int = 30
) -> list[dict[str, Any]]:
    cur = conn.execute(
        """
        SELECT u.session_id,
               t.task_kind,
               SUM(COALESCE(u.input_tokens, 0)) AS input_tokens,
               SUM(COALESCE(u.output_tokens, 0)) AS output_tokens,
               COUNT(*) AS rows_n
        FROM usage_ledger u
        JOIN tasks t ON t.id = u.session_id
        GROUP BY u.session_id, t.task_kind
        ORDER BY (SUM(COALESCE(u.input_tokens, 0)) + SUM(COALESCE(u.output_tokens, 0))) DESC
        LIMIT ?
        """,
        (limit_sessions,),
    )
    return [dict(r) for r in cur.fetchall()]


def usage_today_month_totals(conn: sqlite3.Connection) -> dict[str, int]:
    day_row = conn.execute(
        """
        SELECT SUM(COALESCE(input_tokens, 0)) AS inp, SUM(COALESCE(output_tokens, 0)) AS out
        FROM usage_ledger
        WHERE date(recorded_at) = date('now')
        """,
    ).fetchone()
    month_row = conn.execute(
        """
        SELECT SUM(COALESCE(input_tokens, 0)) AS inp, SUM(COALESCE(output_tokens, 0)) AS out
        FROM usage_ledger
        WHERE strftime('%Y-%m', recorded_at) = strftime('%Y-%m', 'now')
        """,
    ).fetchone()
    d_in = int(day_row["inp"] or 0) if day_row else 0
    d_out = int(day_row["out"] or 0) if day_row else 0
    m_in = int(month_row["inp"] or 0) if month_row else 0
    m_out = int(month_row["out"] or 0) if month_row else 0
    return {
        "day_input": d_in,
        "day_output": d_out,
        "day_total": d_in + d_out,
        "month_input": m_in,
        "month_output": m_out,
        "month_total": m_in + m_out,
    }


def action_log_recent(conn: sqlite3.Connection, *, limit: int = 120) -> list[dict[str, Any]]:
    cur = conn.execute(
        """
        SELECT id, session_id, kind, payload_json, created_at
        FROM action_log
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (limit,),
    )
    out: list[dict[str, Any]] = []
    for r in cur.fetchall():
        kind = r["kind"] or ""
        pj = r["payload_json"] or "{}"
        out.append(
            {
                "id": r["id"],
                "session_id": r["session_id"],
                "kind": kind,
                "created_at": r["created_at"],
                "payload_safe": action_payload_safe(kind, pj),
            }
        )
    return out


def web_source_counts_by_week(conn: sqlite3.Connection, *, weeks: int = 8) -> list[dict[str, Any]]:
    if not _table_exists(conn, "web_sources"):
        return []
    cur = conn.execute(
        """
        SELECT strftime('%Y-W%W', fetched_at) AS wk,
               COUNT(*) AS fetch_count,
               COUNT(DISTINCT session_id) AS sessions_distinct
        FROM web_sources
        WHERE fetched_at >= datetime('now', ?)
        GROUP BY strftime('%Y-W%W', fetched_at)
        ORDER BY wk DESC
        """,
        (f"-{int(weeks) * 7} days",),
    )
    return [dict(r) for r in cur.fetchall()]


def workflow_status_counts(conn: sqlite3.Connection) -> dict[str, int]:
    if not _table_exists(conn, "workflows"):
        return {}
    cur = conn.execute(
        "SELECT status, COUNT(*) AS n FROM workflows GROUP BY status"
    )
    return {str(r["status"]): int(r["n"]) for r in cur.fetchall()}


def gate_failed_steps_recent(
    conn: sqlite3.Connection,
    *,
    limit: int = 50,
    publish_entity_only: bool = True,
) -> list[dict[str, Any]]:
    """
    Failed GATE steps (read-only). Error text is truncated; workflow goal text is not selected.
    """
    if not _table_exists(conn, "workflows") or not _table_exists(conn, "workflow_steps"):
        return []
    lim = max(1, min(500, int(limit)))
    kind_clause = "AND w.kind = 'publish_entity_v1'" if publish_entity_only else ""
    cur = conn.execute(
        f"""
        SELECT ws.id, ws.workflow_id, ws.step_index, w.kind AS workflow_kind,
               ws.status, ws.updated_at, ws.error
        FROM workflow_steps ws
        JOIN workflows w ON w.id = ws.workflow_id
        WHERE ws.step_type = 'GATE'
          AND ws.status = 'failed'
          {kind_clause}
        ORDER BY ws.updated_at DESC
        LIMIT ?
        """,
        (lim,),
    )
    out: list[dict[str, Any]] = []
    for r in cur.fetchall():
        err = r["error"] or ""
        out.append(
            {
                "step_id": int(r["id"]),
                "workflow_id": int(r["workflow_id"]),
                "step_index": int(r["step_index"]),
                "workflow_kind": str(r["workflow_kind"] or ""),
                "updated_at": str(r["updated_at"] or ""),
                "error_preview": truncate_error(err),
            }
        )
    return out


def gate_failure_buckets(
    conn: sqlite3.Connection, *, publish_entity_only: bool = True
) -> list[dict[str, Any]]:
    """
    Aggregate counts by normalized GATE failure bucket (derived from workflow_steps.error only).
    """
    if not _table_exists(conn, "workflows") or not _table_exists(conn, "workflow_steps"):
        return []
    kind_clause = "AND w.kind = 'publish_entity_v1'" if publish_entity_only else ""
    cur = conn.execute(
        f"""
        SELECT sub.bucket AS bucket,
               COUNT(*) AS count,
               MAX(sub.updated_at) AS latest_updated_at
        FROM (
            SELECT ws.updated_at AS updated_at,
                   CASE
                     WHEN IFNULL(ws.error, '') LIKE 'GATE: unique_local_facts%%'
                       THEN 'below_min_unique_facts'
                     WHEN IFNULL(ws.error, '') LIKE '%%GATE:%%'
                       THEN 'gate_other'
                     ELSE 'unknown'
                   END AS bucket
            FROM workflow_steps ws
            JOIN workflows w ON w.id = ws.workflow_id
            WHERE ws.step_type = 'GATE'
              AND ws.status = 'failed'
              {kind_clause}
        ) AS sub
        GROUP BY sub.bucket
        ORDER BY count DESC, sub.bucket ASC
        """
    )
    rows: list[dict[str, Any]] = []
    for r in cur.fetchall():
        rows.append(
            {
                "bucket": str(r["bucket"] or ""),
                "count": int(r["count"] or 0),
                "latest_updated_at": str(r["latest_updated_at"] or ""),
            }
        )
    return rows


def task_status_counts(conn: sqlite3.Connection) -> dict[str, int]:
    cur = conn.execute("SELECT status, COUNT(*) AS n FROM tasks GROUP BY status")
    return {str(r["status"]): int(r["n"]) for r in cur.fetchall()}
