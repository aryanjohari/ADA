"""Read-only queries for completed goal tasks with non-empty output (operator UI)."""

from __future__ import annotations

import sqlite3
from typing import Any


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


def completed_goal_outputs_recent(
    conn: sqlite3.Connection,
    *,
    limit: int = 30,
    mission_slug: str | None = None,
) -> list[dict[str, Any]]:
    """Completed goal tasks with non-empty current_output, newest first.

    When ``mission_slug`` is non-empty, requires ``missions`` table and ``tasks.mission_id``;
    otherwise returns no rows (cannot honor filter). Whitespace-only mission slug is treated
    as no filter.
    """
    lim = max(1, min(200, int(limit)))
    ms = (mission_slug or "").strip()

    if ms:
        if not _table_exists(conn, "missions") or not _column_exists(conn, "tasks", "mission_id"):
            return []
        cur = conn.execute(
            """
            SELECT t.id, t.updated_at, t.goal, t.current_output, m.slug AS mission_slug
            FROM tasks t
            JOIN missions m ON m.id = t.mission_id
            WHERE t.task_kind = 'goal'
              AND t.status = 'completed'
              AND length(trim(COALESCE(t.current_output, ''))) > 0
              AND m.slug = ?
            ORDER BY t.updated_at DESC
            LIMIT ?
            """,
            (ms, lim),
        )
    else:
        cur = conn.execute(
            """
            SELECT t.id, t.updated_at, t.goal, t.current_output
            FROM tasks t
            WHERE t.task_kind = 'goal'
              AND t.status = 'completed'
              AND length(trim(COALESCE(t.current_output, ''))) > 0
            ORDER BY t.updated_at DESC
            LIMIT ?
            """,
            (lim,),
        )

    rows: list[dict[str, Any]] = []
    for r in cur.fetchall():
        item: dict[str, Any] = {
            "id": r["id"],
            "updated_at": r["updated_at"],
            "goal": r["goal"] or "",
            "current_output": r["current_output"] or "",
        }
        if ms:
            item["mission_slug"] = r["mission_slug"]
        else:
            item["mission_slug"] = None
        rows.append(item)
    return rows
