"""Read-only SQLite access for ADA state.db (operator panel)."""

from __future__ import annotations

import sqlite3
from pathlib import Path


def db_uri(path: Path) -> str:
    return f"file:{path.resolve()}?mode=ro"


def connect_ro(db_path: Path) -> sqlite3.Connection:
    p = Path(db_path).expanduser().resolve()
    if not p.is_file():
        raise FileNotFoundError(f"state.db not found: {p}")
    conn = sqlite3.connect(db_uri(p), uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (name,),
    )
    return cur.fetchone() is not None


def overview_stats(conn: sqlite3.Connection, mission_slug: str | None) -> dict:
    out: dict = {}
    ms = mission_slug.strip() if mission_slug else ""

    if table_exists(conn, "missions"):
        cur = conn.execute("SELECT COUNT(*) AS c FROM missions")
        out["missions"] = cur.fetchone()["c"]
    else:
        out["missions"] = 0

    if ms and table_exists(conn, "missions"):
        cur = conn.execute(
            """SELECT COUNT(*) AS c FROM tasks t
               JOIN missions m ON m.id = t.mission_id
               WHERE m.slug = ?""",
            (ms,),
        )
        out["tasks_filtered"] = cur.fetchone()["c"]

    cur = conn.execute(
        """SELECT status, COUNT(*) AS c FROM tasks GROUP BY status ORDER BY status"""
    )
    out["tasks_by_status"] = {row["status"]: row["c"] for row in cur.fetchall()}

    if table_exists(conn, "workflows"):
        cur = conn.execute(
            "SELECT status, COUNT(*) AS c FROM workflows GROUP BY status ORDER BY status"
        )
        out["workflows_by_status"] = {row["status"]: row["c"] for row in cur.fetchall()}
        cur = conn.execute(
            "SELECT id, kind, status, parent_task_id FROM workflows ORDER BY id DESC LIMIT 10"
        )
        out["recent_workflows"] = [dict(r) for r in cur.fetchall()]

    return out


def missions_tasks_preview(
    conn: sqlite3.Connection, mission_slug: str | None, limit: int = 100
) -> tuple[list[dict], list[dict]]:
    """Missions newest first; tasks with mission slug."""
    lim = max(10, min(500, limit))
    ms = mission_slug.strip() if mission_slug else ""

    missions = []
    if table_exists(conn, "missions"):
        mcur = conn.execute(
            "SELECT id, slug, title, created_at FROM missions ORDER BY id DESC LIMIT ?",
            (lim,),
        )
        missions = [dict(r) for r in mcur.fetchall()]

    if not table_exists(conn, "missions"):
        tcur = conn.execute(
            """
            SELECT t.id, t.goal, t.status, t.task_kind, t.created_at, CAST(NULL AS TEXT) AS mission_slug
            FROM tasks t
            ORDER BY t.id DESC
            LIMIT ?
            """,
            (lim,),
        )
    elif ms:
        tcur = conn.execute(
            """
            SELECT t.id, t.goal, t.status, t.task_kind, t.created_at, m.slug AS mission_slug
            FROM tasks t
            LEFT JOIN missions m ON m.id = t.mission_id
            WHERE m.slug = ?
            ORDER BY t.id DESC
            LIMIT ?
            """,
            (ms, lim),
        )
    else:
        tcur = conn.execute(
            """
            SELECT t.id, t.goal, t.status, t.task_kind, t.created_at, m.slug AS mission_slug
            FROM tasks t
            LEFT JOIN missions m ON m.id = t.mission_id
            ORDER BY t.id DESC
            LIMIT ?
            """,
            (lim,),
        )
    tasks = [dict(r) for r in tcur.fetchall()]
    return missions, tasks


def costs_aggregate(
    conn: sqlite3.Connection, days: int
) -> tuple[list[dict], dict]:
    """Return per-model rows + totals for recorded_at window."""
    if not table_exists(conn, "usage_ledger"):
        return [], {}
    days = max(1, min(366, days))
    cur = conn.execute(
        """
        SELECT
            COALESCE(model, '') AS model,
            SUM(COALESCE(input_tokens, 0) + COALESCE(output_tokens, 0)) AS tokens,
            SUM(COALESCE(input_tokens, 0)) AS input_tokens,
            SUM(COALESCE(output_tokens, 0)) AS output_tokens,
            COUNT(*) AS legs
        FROM usage_ledger
        WHERE datetime(recorded_at) >= datetime('now', ?)
        GROUP BY model
        ORDER BY tokens DESC
        """,
        (f"-{days} days",),
    )
    rows = [dict(r) for r in cur.fetchall()]
    totals = {"tokens": sum(r["tokens"] or 0 for r in rows), "days": days}
    return rows, totals


def run_safe_select(conn: sqlite3.Connection, sql: str, *, params: tuple = ()) -> list[dict]:
    cur = conn.execute(sql, params)
    cols = [d[0] for d in cur.description] if cur.description else []
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def observability_preset_failed_steps(conn: sqlite3.Connection, limit: int = 50) -> list[dict]:
    if not table_exists(conn, "workflow_steps"):
        return []
    lim = max(10, min(200, limit))
    cur = conn.execute(
        """
        SELECT ws.id, ws.workflow_id, ws.step_index, ws.step_type, ws.status, ws.error,
               w.kind AS workflow_kind
        FROM workflow_steps ws
        JOIN workflows w ON w.id = ws.workflow_id
        WHERE ws.status = 'failed'
        ORDER BY ws.id DESC
        LIMIT ?
        """,
        (lim,),
    )
    return [dict(r) for r in cur.fetchall()]


def observability_action_recent(
    conn: sqlite3.Connection,
    *,
    kinds_like: str | None,
    mission_slug: str | None,
    limit: int = 80,
) -> list[dict]:
    lim = max(10, min(300, limit))
    params: list = []
    clauses = []

    ms = mission_slug.strip() if mission_slug else ""

    if kinds_like:
        clauses.append("a.kind LIKE ?")
        params.append(f"%{kinds_like}%")

    if ms and table_exists(conn, "missions"):
        clauses.append(
            """(t.mission_id IN (SELECT id FROM missions WHERE slug = ?))"""
        )
        params.append(ms)

    where = ""
    if clauses:
        where = "WHERE " + " AND ".join(clauses)

    if table_exists(conn, "missions"):
        join_mission = "LEFT JOIN missions m ON m.id = t.mission_id"
        mission_col = "m.slug AS mission_slug"
    else:
        join_mission = ""
        mission_col = "CAST(NULL AS TEXT) AS mission_slug"

    cur = conn.execute(
        f"""
        SELECT a.id, a.created_at, a.kind, a.session_id, a.payload_json,
               t.goal AS task_goal_preview, {mission_col}
        FROM action_log a
        LEFT JOIN tasks t ON t.id = a.session_id
        {join_mission}
        {where}
        ORDER BY a.id DESC
        LIMIT ?
        """,
        tuple(params + [lim]),
    )
    return [dict(r) for r in cur.fetchall()]
