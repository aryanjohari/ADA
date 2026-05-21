"""run_skill via motor (B2)."""

from __future__ import annotations

import json

import pytest

from ada.motor.registry import clear_registry_cache
from ada.programme.propose import propose_packet
from ada.query_engine import QueryEngine
from ada.stream_types import CompletedFunctionCall


@pytest.mark.asyncio
async def test_propose_programme_tool_path(tmp_path, schema_sql_path) -> None:
    out = propose_packet(
        json.dumps({"mission_slug": "p", "title": "P", "defaults_json": {}})
    )
    assert "packet" in out
    assert out["packet"]["mission_slug"] == "p"


@pytest.mark.asyncio
async def test_run_skill_goal_via_orchestrator_handler(
    schema_sql_path, test_settings
) -> None:
    clear_registry_cache()
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path)
    await qe.connect()
    await qe.create_mission(slug="sk-test", title="SK", defaults_json={})
    settings = test_settings

    from ada.motor import MotorRequest, execute

    result = await execute(
        MotorRequest(
            layer="skill",
            id="weekly_research_goal",
            params={"goal_text": "test goal"},
            mission_slug="sk-test",
        ),
        settings=settings,
        qe=qe,
    )
    assert result.ok, result.error
    await qe.close()


@pytest.mark.asyncio
async def test_run_skill_respects_mission_skills_enabled(
    schema_sql_path, test_settings
) -> None:
    clear_registry_cache()
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path)
    await qe.connect()
    try:
        await qe.create_mission(
            slug="restricted-sk",
            title="Restricted",
            defaults_json={"skills_enabled": ["daily_brief"]},
        )
        from ada.motor import MotorRequest, execute

        blocked = await execute(
            MotorRequest(
                layer="skill",
                id="weekly_research_goal",
                params={"goal_text": "nope"},
                mission_slug="restricted-sk",
            ),
            settings=test_settings,
            qe=qe,
        )
        assert not blocked.ok
        assert "not enabled" in (blocked.error or "")

        allowed = await execute(
            MotorRequest(
                layer="skill",
                id="daily_brief",
                params={},
                mission_slug="restricted-sk",
            ),
            settings=test_settings,
            qe=qe,
        )
        assert allowed.ok, allowed.error
    finally:
        await qe.close()
