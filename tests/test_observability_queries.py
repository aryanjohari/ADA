"""Tests for ada.observability queries (no Streamlit import)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from ada.observability.paths import resolve_data_dir, resolve_state_db_path
from ada.observability.queries import (
    action_log_recent,
    open_readonly_connection,
    tasks_pending_failed,
    usage_rollup_by_utc_day,
    usage_today_month_totals,
    workflow_steps_recent,
    workflows_recent,
)
from ada.observability.sanitize import action_payload_safe, field_digest, truncate_error


def _schema_sql() -> str:
    root = Path(__file__).resolve().parents[1]
    return (root / "src" / "ada" / "db" / "schema.sql").read_text(encoding="utf-8")


@pytest.fixture()
def obs_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "state.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(_schema_sql())
        conn.execute(
            "INSERT INTO tasks (goal, status, task_kind) VALUES (?, 'pending', 'goal')",
            ("do-not-leak-this-goal-text",),
        )
        tid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            """
            INSERT INTO workflows (kind, goal_text, status, parent_task_id)
            VALUES ('publish_entity_v1', 'secret workflow goal', 'running', ?)
            """,
            (tid,),
        )
        wid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            """
            INSERT INTO workflow_steps (
                workflow_id, step_index, step_type, status, error, input_json, output_json
            ) VALUES (?, 0, 'FETCH', 'failed', 'boom with user pasted secret', '{}', '{}')
            """,
            (wid,),
        )
        conn.execute(
            """
            INSERT INTO usage_ledger (session_id, model, input_tokens, output_tokens, recorded_at)
            VALUES (?, 'm', 10, 20, datetime('now'))
            """,
            (tid,),
        )
        conn.execute(
            """
            INSERT INTO action_log (session_id, kind, payload_json)
            VALUES (NULL, 'global_budget_block', '{"scope":"daily","used":100,"limit":200}')
            """
        )
        conn.commit()
    finally:
        conn.close()
    return db_path


def test_tasks_pending_failed_no_raw_goal(obs_db: Path) -> None:
    conn = open_readonly_connection(obs_db)
    with conn:
        rows = tasks_pending_failed(conn, limit=10)
    assert len(rows) == 1
    r = rows[0]
    assert r["status"] == "pending"
    assert "do-not-leak" not in str(r)
    assert r["goal_digest"]["byte_len"] > 0
    assert "sha256_prefix" in r["goal_digest"]


def test_workflow_steps_error_truncated(obs_db: Path) -> None:
    conn = open_readonly_connection(obs_db)
    with conn:
        rows = workflow_steps_recent(conn, limit=10)
    assert len(rows) >= 1
    err = next(x["error_preview"] for x in rows if x["step_type"] == "FETCH")
    assert "boom" in err
    assert "secret" in err or len(err) <= 300


def test_workflows_goal_digest_only(obs_db: Path) -> None:
    conn = open_readonly_connection(obs_db)
    with conn:
        rows = workflows_recent(conn, limit=10)
    assert len(rows) == 1
    assert "secret workflow" not in str(rows[0])
    assert rows[0]["kind"] == "publish_entity_v1"
    assert rows[0]["goal_text_digest"]["byte_len"] > 0


def test_usage_rollup_and_totals(obs_db: Path) -> None:
    conn = open_readonly_connection(obs_db)
    with conn:
        days = usage_rollup_by_utc_day(conn, days=7)
        totals = usage_today_month_totals(conn)
    assert totals["day_total"] >= 30
    assert any(d.get("input_tokens", 0) >= 10 for d in days)


def test_action_log_sanitized(obs_db: Path) -> None:
    conn = open_readonly_connection(obs_db)
    with conn:
        rows = action_log_recent(conn, limit=5)
    assert rows[0]["kind"] == "global_budget_block"
    p = rows[0]["payload_safe"]
    assert p.get("used") == 100
    assert p.get("limit") == 200


def test_action_payload_safe_unknown_redacts() -> None:
    raw = '{"workflow_id":1,"secret":"nope"}'
    out = action_payload_safe("unknown_kind_xyz", raw)
    assert "nope" not in str(out)


def test_field_digest_stable_prefix() -> None:
    d = field_digest("hello")
    assert d["byte_len"] == 5
    assert len(str(d["sha256_prefix"])) == 12


def test_truncate_error() -> None:
    long = "x" * 500
    t = truncate_error(long, max_chars=100)
    assert len(t) <= 100


def test_resolve_state_db_path_default(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("ADA_PROFILE", raising=False)
    monkeypatch.delenv("ADA_PROFILE_DATA_ROOT", raising=False)
    monkeypatch.delenv("ADA_COMMERCIAL_DATA_DIR", raising=False)
    monkeypatch.setenv("ADA_DATA_DIR", str(tmp_path))
    p = resolve_state_db_path()
    assert p == tmp_path / "state.db"
    assert resolve_data_dir() == tmp_path.resolve()
