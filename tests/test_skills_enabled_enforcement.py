"""Motor enforcement of mission skills_enabled and pack (Hands H5)."""

from __future__ import annotations

import pytest

from ada.motor import MotorRequest, execute
from ada.motor.registry import clear_registry_cache
from ada.query_engine import QueryEngine


@pytest.mark.asyncio
async def test_ops_mission_blocks_publish_skill(schema_sql_path, test_settings) -> None:
    clear_registry_cache()
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path)
    await qe.connect()
    try:
        await qe.create_mission(
            slug="jarvis-ops-test",
            title="Ops",
            defaults_json={
                "pack": "core-ops",
                "skills_enabled": ["daily_brief", "mission_tick_dry_run"],
            },
        )
        result = await execute(
            MotorRequest(
                layer="skill",
                id="publish_keyword_v1",
                params={
                    "goal_text": "test",
                    "project_id": "p1",
                    "campaign_id": "c1",
                    "niche": "test",
                    "target_keyword_cluster": "kw",
                },
                mission_slug="jarvis-ops-test",
                approved=True,
            ),
            settings=test_settings,
            qe=qe,
        )
        assert not result.ok
        assert result.error
        assert "not enabled" in result.error or "not allowed" in result.error
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_isr_publish_mission_allows_publish_skill(
    schema_sql_path, test_settings
) -> None:
    clear_registry_cache()
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path)
    await qe.connect()
    try:
        await qe.create_mission(
            slug="isr-pub-test",
            title="ISR Publish",
            defaults_json={
                "pack": "isr-publish",
                "skills_enabled": ["publish_entity_v1", "publish_keyword_v1"],
            },
        )
        result = await execute(
            MotorRequest(
                layer="skill",
                id="publish_keyword_v1",
                params={
                    "goal_text": "test publish",
                    "project_id": "p1",
                    "campaign_id": "c1",
                    "niche": "test",
                    "target_keyword_cluster": "kw",
                },
                mission_slug="isr-pub-test",
                approved=True,
            ),
            settings=test_settings,
            qe=qe,
        )
        assert "not enabled" not in (result.error or "")
        assert "not allowed" not in (result.error or "")
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_empty_skills_enabled_no_motor_block(
    schema_sql_path, test_settings
) -> None:
    clear_registry_cache()
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path)
    await qe.connect()
    try:
        await qe.create_mission(
            slug="legacy-open",
            title="Legacy",
            defaults_json={"pack": "core-ops"},
        )
        result = await execute(
            MotorRequest(
                layer="skill",
                id="weekly_research_goal",
                params={"goal_text": "legacy goal"},
                mission_slug="legacy-open",
            ),
            settings=test_settings,
            qe=qe,
        )
        assert result.ok, result.error
    finally:
        await qe.close()
