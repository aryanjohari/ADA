"""Motor plane unit tests (B0/B1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ada.motor import MotorRequest, execute, get_skill, load_skill_registry
from ada.motor.registry import clear_registry_cache
from ada.query_engine import QueryEngine


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_load_seed_skills(project_root: Path) -> None:
    clear_registry_cache()
    reg = load_skill_registry(project_root)
    for sid in (
        "weekly_research_goal",
        "ingest_rss_mission",
        "publish_entity_v1",
        "publish_keyword_v1",
        "mission_tick_dry_run",
    ):
        assert sid in reg, f"missing {sid}"


def test_unknown_skill_rejected(project_root: Path) -> None:
    assert get_skill("nonexistent_skill_xyz", project_root) is None


@pytest.mark.asyncio
async def test_execute_unknown_skill_logs(
    tmp_path: Path, schema_sql_path: Path, test_settings
) -> None:
    db = test_settings.state_db_path
    qe = QueryEngine(db, schema_sql_path)
    await qe.connect()
    settings = test_settings
    req = MotorRequest(layer="skill", id="nonexistent_skill_xyz", session_id=None)
    result = await execute(req, settings=settings, qe=qe)
    assert not result.ok
    assert result.error
    await qe.close()


@pytest.mark.asyncio
async def test_execute_goal_add_skill(
    schema_sql_path: Path, project_root: Path, test_settings
) -> None:
    clear_registry_cache()
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path)
    await qe.connect()
    await qe.create_mission(
        slug="test-ops",
        title="Test",
        defaults_json={},
    )
    settings = test_settings
    req = MotorRequest(
        layer="skill",
        id="weekly_research_goal",
        params={"goal_text": "Summarize weekly research"},
        mission_slug="test-ops",
        session_id=None,
    )
    result = await execute(req, settings=settings, qe=qe)
    assert result.ok, result.error
    assert isinstance(result.output, dict)
    assert "task_id" in result.output
    assert result.action_log_id is not None
    await qe.close()


@pytest.mark.asyncio
async def test_high_risk_skill_requires_approval(
    schema_sql_path: Path, project_root: Path, test_settings
) -> None:
    clear_registry_cache()
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path)
    await qe.connect()
    await qe.create_mission(slug="pub", title="Pub", defaults_json={})
    settings = test_settings
    req = MotorRequest(
        layer="skill",
        id="publish_entity_v1",
        params={
            "entity_id": "ent-1",
            "project_id": "p",
            "campaign_id": "c",
            "niche": "n",
        },
        mission_slug="pub",
        approved=False,
    )
    result = await execute(req, settings=settings, qe=qe)
    assert result.pending_approval
    assert not result.ok
    await qe.close()
