"""Programme apply closed mutations (B7)."""

from __future__ import annotations

import json

import pytest

from ada.programme.apply import apply_packet, confirm_and_apply
from ada.programme.packet import ProgrammePacket
from ada.programme.propose import propose_packet
from ada.query_engine import QueryEngine


@pytest.mark.asyncio
async def test_propose_does_not_write_missions(tmp_path, schema_sql_path) -> None:
    db = tmp_path / "state.db"
    qe = QueryEngine(db, schema_sql_path)
    await qe.connect()
    try:
        out = propose_packet(
            {
                "mission_slug": "prog-test",
                "title": "T",
                "defaults_json": {"a": 1},
            }
        )
        assert "packet" in out
        row = await qe.get_mission_by_slug("prog-test")
        assert row is None
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_apply_denied_no_side_effects(schema_sql_path, test_settings) -> None:
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path)
    await qe.connect()
    settings = test_settings
    packet = ProgrammePacket(
        mission_slug="denied-test",
        title="Denied",
    )
    try:
        out = await confirm_and_apply(
            qe, settings, packet, approved=False, session_id=None
        )
        assert out.get("denied")
        assert await qe.get_mission_by_slug("denied-test") is None
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_apply_approved_creates_mission(schema_sql_path, test_settings) -> None:
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path)
    await qe.connect()
    settings = test_settings
    packet = ProgrammePacket(
        mission_slug="apply-test",
        title="Apply Test",
        defaults_json={"project_id": "p1"},
        knowledge_sources=[{"url": "https://example.com/feed.xml", "kind": "rss"}],
        recommended_cron=[{"comment": "tick", "line": "0 6 * * 0 ada mission tick"}],
        skills_enabled=["weekly_research_goal"],
    )
    try:
        out = await apply_packet(qe, settings, packet, session_id=None)
        assert out.get("ok")
        row = await qe.get_mission_by_slug("apply-test")
        assert row is not None
        assert row["title"] == "Apply Test"
        assert row["defaults_json"].get("skills_enabled") == ["weekly_research_goal"]
        cron_file = test_settings.data_dir / "artifacts" / "cron" / "apply-test.snippet"
        assert cron_file.is_file()
        assert "ada mission tick" in cron_file.read_text()
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_apply_rejects_pack_skill_mismatch(schema_sql_path, test_settings) -> None:
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path)
    await qe.connect()
    settings = test_settings
    packet = ProgrammePacket(
        mission_slug="pack-mismatch",
        title="Mismatch",
        defaults_json={"pack": "core-ops"},
        skills_enabled=["publish_entity_v1"],
    )
    try:
        out = await apply_packet(qe, settings, packet, session_id=None)
        assert not out.get("ok")
        assert out.get("error")
        assert await qe.get_mission_by_slug("pack-mismatch") is None
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_packet_rejects_unknown_keys() -> None:
    with pytest.raises(Exception):
        ProgrammePacket.model_validate(
            {"mission_slug": "x", "title": "t", "extra_field": 1}
        )
