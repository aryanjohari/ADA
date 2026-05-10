"""Tests for completed goal output queries (no Streamlit import)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from ada.observability.goal_outputs import completed_goal_outputs_recent
from ada.observability.queries import open_readonly_connection


def _schema_sql() -> str:
    root = Path(__file__).resolve().parents[1]
    return (root / "src" / "ada" / "db" / "schema.sql").read_text(encoding="utf-8")


def _legacy_schema_sql() -> str:
    root = Path(__file__).resolve().parents[1]
    return (root / "tests" / "fixtures" / "schema_before_missions.sql").read_text(encoding="utf-8")


def _db_with_missions(tmp_path: Path) -> Path:
    db_path = tmp_path / "state.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(_schema_sql())
        conn.execute(
            "INSERT INTO missions (slug, title) VALUES ('alpha', 'A'), ('beta', 'B')"
        )
        conn.execute(
            """
            INSERT INTO tasks (goal, status, current_output, task_kind, mission_id, updated_at)
            VALUES ('g1', 'completed', 'out one', 'goal', 1, '2026-01-02T00:00:00')
            """
        )
        conn.execute(
            """
            INSERT INTO tasks (goal, status, current_output, task_kind, mission_id, updated_at)
            VALUES ('g2', 'completed', 'out two', 'goal', 2, '2026-01-03T00:00:00')
            """
        )
        conn.execute(
            """
            INSERT INTO tasks (goal, status, current_output, task_kind, mission_id, updated_at)
            VALUES ('g3 empty', 'completed', '   ', 'goal', 1, '2026-01-04T00:00:00')
            """
        )
        conn.execute(
            """
            INSERT INTO tasks (goal, status, current_output, task_kind, mission_id, updated_at)
            VALUES ('g4 pending', 'pending', 'has text', 'goal', 1, '2026-01-05T00:00:00')
            """
        )
        conn.commit()
    finally:
        conn.close()
    return db_path


def test_completed_goal_outputs_newest_first_and_excludes_empty(tmp_path: Path) -> None:
    db_path = _db_with_missions(tmp_path)
    conn = open_readonly_connection(db_path)
    with conn:
        rows = completed_goal_outputs_recent(conn, limit=10, mission_slug=None)
    assert len(rows) == 2
    assert rows[0]["goal"] == "g2"
    assert rows[0]["current_output"] == "out two"
    assert rows[1]["goal"] == "g1"
    assert rows[1]["mission_slug"] is None


def test_completed_goal_outputs_mission_slug_filter(tmp_path: Path) -> None:
    db_path = _db_with_missions(tmp_path)
    conn = open_readonly_connection(db_path)
    with conn:
        rows = completed_goal_outputs_recent(conn, limit=10, mission_slug="alpha")
    assert len(rows) == 1
    assert rows[0]["goal"] == "g1"
    assert rows[0]["mission_slug"] == "alpha"


def test_completed_goal_outputs_whitespace_slug_means_no_filter(tmp_path: Path) -> None:
    db_path = _db_with_missions(tmp_path)
    conn = open_readonly_connection(db_path)
    with conn:
        rows = completed_goal_outputs_recent(conn, limit=10, mission_slug="  \t  ")
    assert len(rows) == 2


def test_legacy_db_no_missions_unfiltered_ok_mission_filter_empty(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(_legacy_schema_sql())
        conn.execute(
            """
            INSERT INTO tasks (goal, status, current_output, task_kind, updated_at)
            VALUES ('legacy goal', 'completed', 'legacy out', 'goal', '2026-02-01T00:00:00')
            """
        )
        conn.commit()
    finally:
        conn.close()

    ro = open_readonly_connection(db_path)
    with ro:
        rows = completed_goal_outputs_recent(ro, limit=10, mission_slug=None)
    assert len(rows) == 1
    assert rows[0]["current_output"] == "legacy out"

    ro2 = open_readonly_connection(db_path)
    with ro2:
        filtered = completed_goal_outputs_recent(ro2, limit=10, mission_slug="any")
    assert filtered == []


def test_limit_clamped(tmp_path: Path) -> None:
    db_path = _db_with_missions(tmp_path)
    conn = open_readonly_connection(db_path)
    with conn:
        assert len(completed_goal_outputs_recent(conn, limit=1, mission_slug=None)) == 1
