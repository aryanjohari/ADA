"""Apply-time pack and skills_enabled validation (Hands H5)."""

from __future__ import annotations

import pytest

from ada.programme.apply import apply_packet
from ada.programme.packet import ProgrammePacket
from ada.query_engine import QueryEngine


@pytest.mark.asyncio
async def test_apply_rejects_publish_on_core_ops_pack(
    schema_sql_path, test_settings
) -> None:
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path)
    await qe.connect()
    try:
        packet = ProgrammePacket(
            mission_slug="bad-ops",
            title="Bad Ops",
            defaults_json={"pack": "core-ops"},
            skills_enabled=["publish_keyword_v1"],
        )
        out = await apply_packet(qe, test_settings, packet)
        assert not out.get("ok")
        assert out.get("error")
        assert await qe.get_mission_by_slug("bad-ops") is None
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_apply_accepts_valid_isr_publish_packet(
    schema_sql_path, test_settings
) -> None:
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path)
    await qe.connect()
    try:
        packet = ProgrammePacket(
            mission_slug="good-isr",
            title="ISR",
            defaults_json={"pack": "isr-publish"},
            skills_enabled=["publish_entity_v1", "publish_keyword_v1"],
        )
        out = await apply_packet(qe, test_settings, packet)
        assert out.get("ok"), out.get("error")
        row = await qe.get_mission_by_slug("good-isr")
        assert row is not None
        assert row["defaults_json"]["pack"] == "isr-publish"
        assert "publish_keyword_v1" in row["defaults_json"]["skills_enabled"]
    finally:
        await qe.close()
