"""Phase 0: global UTC budgets, kill-switch gate helpers, usage_ledger sums."""

from __future__ import annotations

from pathlib import Path

import pytest

from ada.budget import (
    daemon_should_execute_goal,
    global_budget_blocks,
)
from ada.persistent.store import PersistentState


def test_global_budget_blocks_daily() -> None:
    blocked, scope = global_budget_blocks(
        day_total=100,
        month_total=50,
        daily_limit=100,
        monthly_limit=None,
    )
    assert blocked and scope == "daily"


def test_global_budget_blocks_monthly() -> None:
    blocked, scope = global_budget_blocks(
        day_total=10,
        month_total=500,
        daily_limit=None,
        monthly_limit=500,
    )
    assert blocked and scope == "monthly"


def test_global_budget_daily_checked_before_monthly() -> None:
    blocked, scope = global_budget_blocks(
        day_total=100,
        month_total=9999,
        daily_limit=100,
        monthly_limit=100,
    )
    assert blocked and scope == "daily"


def test_daemon_should_execute_goal_kill_switch() -> None:
    ok, reason = daemon_should_execute_goal(
        kill_switch=True,
        day_total=0,
        month_total=0,
        daily_limit=None,
        monthly_limit=None,
    )
    assert not ok and reason == "kill_switch"


def test_daemon_should_execute_goal_ok() -> None:
    ok, reason = daemon_should_execute_goal(
        kill_switch=False,
        day_total=10,
        month_total=20,
        daily_limit=100,
        monthly_limit=1000,
    )
    assert ok and reason is None


@pytest.mark.asyncio
async def test_get_global_usage_token_totals_utc(
    tmp_path: Path, schema_sql_path: Path
) -> None:
    db = tmp_path / "t.db"
    ps = PersistentState(db, schema_sql_path)
    await ps.connect()
    tid = await ps.insert_task("g", status="completed", task_kind="goal")
    await ps._conn.execute(
        """
        INSERT INTO usage_ledger (session_id, model, input_tokens, output_tokens, recorded_at)
        VALUES (?, 'm', 3, 7, datetime('now'))
        """,
        (tid,),
    )
    await ps._conn.commit()
    totals = await ps.get_global_usage_token_totals_utc()
    assert totals["day_total"] >= 10
    assert totals["month_total"] >= 10
    await ps.close()


@pytest.mark.asyncio
async def test_get_global_usage_token_totals_respects_recorded_at_day(
    tmp_path: Path, schema_sql_path: Path
) -> None:
    db = tmp_path / "t.db"
    ps = PersistentState(db, schema_sql_path)
    await ps.connect()
    tid = await ps.insert_task("g", status="completed", task_kind="goal")
    await ps._conn.execute(
        """
        INSERT INTO usage_ledger (session_id, model, input_tokens, output_tokens, recorded_at)
        VALUES (?, 'm', 100, 100, '2020-01-01T00:00:00')
        """,
        (tid,),
    )
    await ps._conn.commit()
    totals = await ps.get_global_usage_token_totals_utc()
    assert totals["day_total"] == 0
    assert totals["month_total"] == 0
    await ps.close()
