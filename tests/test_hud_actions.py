"""HUD apply programme and run_skill (H7)."""

from __future__ import annotations

import pytest

from ada.motor.registry import clear_registry_cache
from ada.observability.hud_actions import hud_apply_programme, hud_run_skill
from ada.programme.packet import ProgrammePacket
from ada.query_engine import QueryEngine


@pytest.mark.asyncio
async def test_hud_apply_programme_approved_creates_mission(
    schema_sql_path, test_settings
) -> None:
    packet = ProgrammePacket(
        mission_slug="hud-apply-m",
        title="HUD Apply",
        brief_md="Applied from HUD.",
        knowledge_sources=[],
    )
    out = await hud_apply_programme(
        test_settings,
        packet.model_dump(mode="json"),
        approved=True,
    )
    assert out.get("ok") is True
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        row = await qe.get_mission_by_slug("hud-apply-m")
        assert row is not None
        assert row["brief_md"] == "Applied from HUD."
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_hud_apply_programme_denied(schema_sql_path, test_settings) -> None:
    packet = ProgrammePacket(mission_slug="hud-deny", title="Deny")
    out = await hud_apply_programme(
        test_settings,
        packet.model_dump(mode="json"),
        approved=False,
    )
    assert out.get("denied") is True
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        assert await qe.get_mission_by_slug("hud-deny") is None
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_hud_run_skill_blocks_ops_publish(
    schema_sql_path, test_settings
) -> None:
    clear_registry_cache()
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        await qe.create_mission(
            slug="hud-ops",
            title="HUD Ops",
            defaults_json={
                "pack": "core-ops",
                "skills_enabled": ["daily_brief", "mission_tick_dry_run"],
            },
        )
    finally:
        await qe.close()
    out = await hud_run_skill(
        test_settings,
        skill_id="publish_keyword_v1",
        mission_slug="hud-ops",
        params={
            "goal_text": "test",
            "project_id": "p1",
            "campaign_id": "c1",
            "niche": "test",
            "target_keyword_cluster": "kw",
        },
        approved=True,
    )
    assert out.get("ok") is False
    assert out.get("error")
    assert "not enabled" in out["error"] or "not allowed" in out["error"]
