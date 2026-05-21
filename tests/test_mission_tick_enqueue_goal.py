"""mission_tick action.type enqueue_goal (B11)."""

from __future__ import annotations

import json

import pytest

from ada.config import Settings
from ada.mission_tick import parse_tick_schedule_v1, run_mission_tick
from ada.query_engine import QueryEngine


@pytest.mark.asyncio
async def test_tick_enqueue_goal_dry_run(schema_sql_path, test_settings, monkeypatch) -> None:
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path)
    await qe.connect()
    schedule = {
        "version": 1,
        "jobs": [
            {
                "id": "g1",
                "min_interval_hours": 0,
                "action": {"type": "enqueue_goal", "goal_text": "weekly synth"},
            }
        ],
    }
    await qe.create_mission(
        slug="tick-goal",
        title="Tick Goal",
        schedule_hint_json=schedule,
    )
    settings = test_settings
    code = await run_mission_tick(
        qe, settings, mission_slug="tick-goal", dry_run=True, force=True
    )
    assert code == 0
    row = await qe.get_mission_by_slug("tick-goal")
    tasks = await qe.list_goal_tasks(limit=10, mission_slug="tick-goal")
    assert len(tasks) == 0
    await qe.close()
