"""Read-only SQL helpers for observability (sqlite3, SELECT only)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from ada.observability.sanitize import (
    action_payload_safe,
    field_digest,
    json_blob_digest,
    system_job_payload_safe,
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


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cur = conn.execute(f"PRAGMA table_info({table})")
    for row in cur.fetchall():
        if str(row[1]) == column:
            return True
    return False


def tasks_pending_failed(
    conn: sqlite3.Connection,
    *,
    limit: int = 200,
    mission_id: int | None = None,
) -> list[dict[str, Any]]:
    has_tm = _column_exists(conn, "tasks", "mission_id")
    cols = (
        "id, status, task_kind, created_at, updated_at, goal, current_output, plan_json"
    )
    if has_tm:
        cols += ", mission_id"
    where = "status IN ('pending', 'failed')"
    args: list[Any] = []
    if mission_id is not None and has_tm:
        where += " AND mission_id = ?"
        args.append(mission_id)
    elif mission_id is not None and not has_tm:
        return []
    args.append(limit)
    cur = conn.execute(
        f"""
        SELECT {cols}
        FROM tasks
        WHERE {where}
        ORDER BY updated_at DESC
        LIMIT ?
        """,
        tuple(args),
    )
    rows: list[dict[str, Any]] = []
    for r in cur.fetchall():
        g = r["goal"] or ""
        co = r["current_output"] or ""
        pj = r["plan_json"] or ""
        item: dict[str, Any] = {
            "id": r["id"],
            "status": r["status"],
            "task_kind": r["task_kind"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
            "goal_digest": field_digest(g),
            "current_output_digest": field_digest(co),
            "plan_json_digest": field_digest(pj),
        }
        if has_tm:
            mid = r["mission_id"]
            item["mission_id"] = int(mid) if mid is not None else None
        rows.append(item)
    return rows


def workflows_recent(
    conn: sqlite3.Connection,
    *,
    limit: int = 80,
    mission_id: int | None = None,
) -> list[dict[str, Any]]:
    if not _table_exists(conn, "workflows"):
        return []
    has_wm = _column_exists(conn, "workflows", "mission_id")
    cols = (
        "id, kind, status, parent_task_id, created_at, updated_at, idempotency_key, goal_text"
    )
    if has_wm:
        cols += ", mission_id"
    where_sql = ""
    args: list[Any] = [limit]
    if mission_id is not None and has_wm:
        where_sql = " WHERE mission_id = ?"
        args = [mission_id, limit]
    elif mission_id is not None and not has_wm:
        return []
    cur = conn.execute(
        f"""
        SELECT {cols}
        FROM workflows
        {where_sql}
        ORDER BY updated_at DESC
        LIMIT ?
        """,
        tuple(args),
    )
    out: list[dict[str, Any]] = []
    for r in cur.fetchall():
        gt = r["goal_text"] or ""
        item: dict[str, Any] = {
            "id": r["id"],
            "kind": r["kind"],
            "status": r["status"],
            "parent_task_id": r["parent_task_id"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
            "idempotency_key": r["idempotency_key"],
            "goal_text_digest": field_digest(gt),
        }
        if has_wm:
            wid = r["mission_id"]
            item["mission_id"] = int(wid) if wid is not None else None
        out.append(item)
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


def workflow_status_counts(
    conn: sqlite3.Connection, *, mission_id: int | None = None
) -> dict[str, int]:
    if not _table_exists(conn, "workflows"):
        return {}
    has_wm = _column_exists(conn, "workflows", "mission_id")
    if mission_id is not None and not has_wm:
        return {}
    if mission_id is not None and has_wm:
        cur = conn.execute(
            "SELECT status, COUNT(*) AS n FROM workflows WHERE mission_id = ? GROUP BY status",
            (mission_id,),
        )
    else:
        cur = conn.execute("SELECT status, COUNT(*) AS n FROM workflows GROUP BY status")
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


def task_status_counts(
    conn: sqlite3.Connection, *, mission_id: int | None = None
) -> dict[str, int]:
    has_tm = _column_exists(conn, "tasks", "mission_id")
    if mission_id is not None and not has_tm:
        return {}
    if mission_id is not None and has_tm:
        cur = conn.execute(
            "SELECT status, COUNT(*) AS n FROM tasks WHERE mission_id = ? GROUP BY status",
            (mission_id,),
        )
    else:
        cur = conn.execute("SELECT status, COUNT(*) AS n FROM tasks GROUP BY status")
    return {str(r["status"]): int(r["n"]) for r in cur.fetchall()}


def task_status_counts_by_mission(
    conn: sqlite3.Connection,
) -> list[dict[str, Any]]:
    """Group task counts by mission_id (NULL = unassigned). Requires tasks.mission_id."""
    if not _column_exists(conn, "tasks", "mission_id"):
        return []
    cur = conn.execute(
        """
        SELECT mission_id, status, COUNT(*) AS n
        FROM tasks
        GROUP BY mission_id, status
        ORDER BY (mission_id IS NULL), mission_id, status
        """
    )
    out: list[dict[str, Any]] = []
    for r in cur.fetchall():
        mid = r["mission_id"]
        out.append(
            {
                "mission_id": int(mid) if mid is not None else None,
                "status": str(r["status"] or ""),
                "n": int(r["n"] or 0),
            }
        )
    return out


def workflow_status_counts_by_mission(
    conn: sqlite3.Connection,
) -> list[dict[str, Any]]:
    """Group workflow counts by mission_id (NULL = unassigned)."""
    if not _table_exists(conn, "workflows") or not _column_exists(
        conn, "workflows", "mission_id"
    ):
        return []
    cur = conn.execute(
        """
        SELECT mission_id, status, COUNT(*) AS n
        FROM workflows
        GROUP BY mission_id, status
        ORDER BY (mission_id IS NULL), mission_id, status
        """
    )
    out: list[dict[str, Any]] = []
    for r in cur.fetchall():
        mid = r["mission_id"]
        out.append(
            {
                "mission_id": int(mid) if mid is not None else None,
                "status": str(r["status"] or ""),
                "n": int(r["n"] or 0),
            }
        )
    return out


def pending_task_counts_by_mission(
    conn: sqlite3.Connection,
) -> list[dict[str, Any]]:
    if not _column_exists(conn, "tasks", "mission_id"):
        return []
    cur = conn.execute(
        """
        SELECT mission_id, COUNT(*) AS n
        FROM tasks
        WHERE status = 'pending'
        GROUP BY mission_id
        ORDER BY (mission_id IS NULL), mission_id
        """
    )
    out: list[dict[str, Any]] = []
    for r in cur.fetchall():
        mid = r["mission_id"]
        out.append(
            {
                "mission_id": int(mid) if mid is not None else None,
                "n": int(r["n"] or 0),
            }
        )
    return out


def mission_id_from_slug(conn: sqlite3.Connection, slug: str) -> int | None:
    if not _table_exists(conn, "missions"):
        return None
    cur = conn.execute(
        "SELECT id FROM missions WHERE slug = ? LIMIT 1",
        (slug.strip(),),
    )
    row = cur.fetchone()
    return int(row[0]) if row is not None else None


def _parse_schedule_job_ids(schedule_hint_json: str | None) -> list[str]:
    if not schedule_hint_json or not str(schedule_hint_json).strip():
        return []
    try:
        data = json.loads(schedule_hint_json)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, dict) or data.get("version") != 1:
        return []
    jobs = data.get("jobs")
    if not isinstance(jobs, list):
        return []
    out: list[str] = []
    for j in jobs:
        if isinstance(j, dict):
            jid = str(j.get("id") or "").strip()
            if jid:
                out.append(jid)
    return out


def _count_map(rows: list[dict[str, Any]], *, key: str = "mission_id") -> dict[int | None, int]:
    m: dict[int | None, int] = {}
    for r in rows:
        mid = r.get(key)
        m[mid] = m.get(mid, 0) + int(r.get("n") or 0)
    return m


def missions_overview_list(
    conn: sqlite3.Connection,
    *,
    slug_filter: str | None = None,
) -> list[dict[str, Any]]:
    """
    One row per mission: slug, title, schedule job ids, defaults digest, work counts.
    """
    if not _table_exists(conn, "missions"):
        return []
    where = ""
    args: list[Any] = []
    if slug_filter and str(slug_filter).strip():
        where = " WHERE slug = ?"
        args.append(str(slug_filter).strip())
    cur = conn.execute(
        f"""
        SELECT id, slug, title, niche, topic, defaults_json, schedule_hint_json,
               created_at, updated_at
        FROM missions
        {where}
        ORDER BY slug ASC
        """,
        tuple(args),
    )
    mission_rows = cur.fetchall()
    pending_goals = _count_map(pending_task_counts_by_mission(conn))
    pending_wf = _count_map(pending_workflow_counts_by_mission(conn))
    pending_sj: dict[int | None, int] = {}
    if _table_exists(conn, "system_jobs"):
        cur2 = conn.execute(
            """
            SELECT mission_id, COUNT(*) AS n
            FROM system_jobs
            WHERE status IN ('pending', 'running')
            GROUP BY mission_id
            """
        )
        for r in cur2.fetchall():
            mid = r["mission_id"]
            pending_sj[int(mid) if mid is not None else None] = int(r["n"] or 0)

    out: list[dict[str, Any]] = []
    for r in mission_rows:
        mid = int(r["id"])
        defaults_raw = str(r["defaults_json"] or "{}")
        sched_raw = r["schedule_hint_json"]
        sched_s = str(sched_raw) if sched_raw is not None else ""
        out.append(
            {
                "id": mid,
                "slug": str(r["slug"] or ""),
                "title": str(r["title"] or ""),
                "niche": r["niche"],
                "topic": r["topic"],
                "defaults_json_digest": json_blob_digest(defaults_raw),
                "schedule_job_ids": _parse_schedule_job_ids(sched_s),
                "pending_goals": pending_goals.get(mid, 0),
                "pending_workflows": pending_wf.get(mid, 0),
                "pending_system_jobs": pending_sj.get(mid, 0),
                "created_at": str(r["created_at"] or ""),
                "updated_at": str(r["updated_at"] or ""),
            }
        )
    return out


def mission_tick_state_rows(
    conn: sqlite3.Connection,
    *,
    mission_slug: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Read-only ``state`` rows for ``mission.tick.{slug}.*`` keys."""
    if not _table_exists(conn, "state"):
        return []
    prefix = f"mission.tick.{mission_slug.strip()}."
    cur = conn.execute(
        """
        SELECT key, value FROM state
        WHERE key LIKE ?
        ORDER BY key ASC
        LIMIT ?
        """,
        (prefix + "%", limit),
    )
    return [{"key": str(r["key"]), "value": str(r["value"])} for r in cur.fetchall()]


def system_jobs_recent(
    conn: sqlite3.Connection,
    *,
    limit: int = 150,
    mission_id: int | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """Recent system_jobs with sanitized payload summaries (no raw JSON in rows)."""
    if not _table_exists(conn, "system_jobs"):
        return []
    lim = max(1, min(500, int(limit)))
    where_parts: list[str] = []
    args: list[Any] = []
    if mission_id is not None:
        where_parts.append("mission_id = ?")
        args.append(mission_id)
    if status and str(status).strip():
        where_parts.append("status = ?")
        args.append(str(status).strip())
    where_sql = (" WHERE " + " AND ".join(where_parts)) if where_parts else ""
    args.append(lim)
    cur = conn.execute(
        f"""
        SELECT id, kind, status, mission_id, payload_json, attempt_count, max_attempts,
               error, lease_owner, lease_expires_at, created_at, updated_at, started_at
        FROM system_jobs
        {where_sql}
        ORDER BY id DESC
        LIMIT ?
        """,
        tuple(args),
    )
    out: list[dict[str, Any]] = []
    for r in cur.fetchall():
        pj = str(r["payload_json"] or "{}")
        safe = system_job_payload_safe(pj)
        mid = r["mission_id"]
        out.append(
            {
                "id": int(r["id"]),
                "kind": str(r["kind"] or ""),
                "status": str(r["status"] or ""),
                "mission_id": int(mid) if mid is not None else None,
                "attempt_count": int(r["attempt_count"] or 0),
                "max_attempts": int(r["max_attempts"] or 0),
                "error_preview": truncate_error(str(r["error"] or "")),
                "lease_owner": str(r["lease_owner"] or ""),
                "lease_expires_at": r["lease_expires_at"],
                "created_at": str(r["created_at"] or ""),
                "updated_at": str(r["updated_at"] or ""),
                "started_at": r["started_at"],
                "payload_digest": safe["payload_digest"],
                "payload_keys": safe["payload_keys"],
                "payload_redacted": safe["payload_redacted"],
            }
        )
    return out


def system_jobs_stuck_summary(conn: sqlite3.Connection) -> dict[str, int]:
    """Counts useful for ada doctor (read-only)."""
    if not _table_exists(conn, "system_jobs"):
        return {}
    cur = conn.execute(
        """
        SELECT
          SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) AS pending_n,
          SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) AS running_n,
          SUM(CASE WHEN status = 'dead' THEN 1 ELSE 0 END) AS dead_n,
          SUM(CASE WHEN status = 'running'
                    AND lease_expires_at IS NOT NULL
                    AND datetime(lease_expires_at) < datetime('now') THEN 1 ELSE 0 END)
            AS expired_lease_n
        FROM system_jobs
        """
    )
    row = cur.fetchone()
    if row is None:
        return {}
    return {
        "pending": int(row["pending_n"] or 0),
        "running": int(row["running_n"] or 0),
        "dead": int(row["dead_n"] or 0),
        "expired_lease": int(row["expired_lease_n"] or 0),
    }


def pending_workflow_counts_by_mission(
    conn: sqlite3.Connection,
) -> list[dict[str, Any]]:
    if not _table_exists(conn, "workflows") or not _column_exists(
        conn, "workflows", "mission_id"
    ):
        return []
    cur = conn.execute(
        """
        SELECT mission_id, COUNT(*) AS n
        FROM workflows
        WHERE status = 'pending'
        GROUP BY mission_id
        ORDER BY (mission_id IS NULL), mission_id
        """
    )
    out: list[dict[str, Any]] = []
    for r in cur.fetchall():
        mid = r["mission_id"]
        out.append(
            {
                "mission_id": int(mid) if mid is not None else None,
                "n": int(r["n"] or 0),
            }
        )
    return out
