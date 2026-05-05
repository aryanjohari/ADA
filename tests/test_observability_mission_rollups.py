"""Mission-scoped observability query helpers."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from ada.observability.queries import (
    open_readonly_connection,
    pending_task_counts_by_mission,
    pending_workflow_counts_by_mission,
    task_status_counts,
    task_status_counts_by_mission,
    tasks_pending_failed,
    workflow_status_counts,
    workflow_status_counts_by_mission,
    workflows_recent,
)


def _schema_sql() -> str:
    root = Path(__file__).resolve().parents[1]
    return (root / "src" / "ada" / "db" / "schema.sql").read_text(encoding="utf-8")


def test_mission_filters_and_rollups(tmp_path: Path) -> None:
    db_path = tmp_path / "m.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(_schema_sql())
        conn.execute(
            """
            INSERT INTO missions (slug, title, defaults_json)
            VALUES ('alpha', 'A', '{}')
            """
        )
        mid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            """
            INSERT INTO tasks (goal, status, task_kind, mission_id)
            VALUES ('g1', 'pending', 'goal', ?)
            """,
            (mid,),
        )
        conn.execute(
            """
            INSERT INTO tasks (goal, status, task_kind, mission_id)
            VALUES ('g2', 'completed', 'goal', ?)
            """,
            (mid,),
        )
        tid = conn.execute("SELECT id FROM tasks WHERE goal='g1'").fetchone()[0]
        conn.execute(
            """
            INSERT INTO workflows (kind, goal_text, status, parent_task_id, mission_id)
            VALUES ('publish_entity_v1', 'x', 'pending', ?, ?)
            """,
            (tid, mid),
        )
        conn.execute(
            """
            INSERT INTO workflows (kind, goal_text, status, parent_task_id, mission_id)
            VALUES ('publish_entity_v1', 'y', 'running', ?, NULL)
            """,
            (tid,),
        )
        conn.commit()
    finally:
        conn.close()

    ro = open_readonly_connection(db_path)
    with ro:
        assert task_status_counts(ro, mission_id=int(mid)) == {"pending": 1, "completed": 1}
        assert task_status_counts(ro, mission_id=None)["pending"] >= 1
        assert workflow_status_counts(ro, mission_id=int(mid)) == {"pending": 1}

        tbm = task_status_counts_by_mission(ro)
        assert sum(r["n"] for r in tbm if r["mission_id"] == int(mid)) == 2

        wbm = workflow_status_counts_by_mission(ro)
        assert len(wbm) >= 2

        ptask = pending_task_counts_by_mission(ro)
        assert any(
            r["mission_id"] == int(mid) and r["n"] == 1 for r in ptask
        )

        pwf = pending_workflow_counts_by_mission(ro)
        assert sum(r["n"] for r in pwf if r["mission_id"] == int(mid)) == 1

        rows = tasks_pending_failed(ro, mission_id=int(mid), limit=20)
        assert len(rows) == 1
        assert rows[0]["mission_id"] == int(mid)

        wfrows = workflows_recent(ro, mission_id=int(mid), limit=20)
        assert len(wfrows) == 1
        assert wfrows[0]["mission_id"] == int(mid)
