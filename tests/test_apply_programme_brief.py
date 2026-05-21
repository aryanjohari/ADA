"""apply_packet persists and replaces brief_md."""

from __future__ import annotations

import pytest

from ada.programme.apply import apply_packet
from ada.programme.packet import ProgrammePacket
from ada.query_engine import QueryEngine


@pytest.mark.asyncio
async def test_apply_creates_mission_with_brief(
    schema_sql_path, test_settings
) -> None:
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        packet = ProgrammePacket(
            mission_slug="brief-create",
            title="Brief Create",
            brief_md="First programme intent.",
        )
        out = await apply_packet(qe, test_settings, packet)
        assert out.get("ok")
        row = await qe.get_mission_by_slug("brief-create")
        assert row is not None
        assert row["brief_md"] == "First programme intent."
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_apply_reapply_replaces_brief(schema_sql_path, test_settings) -> None:
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        p1 = ProgrammePacket(
            mission_slug="brief-replace",
            title="T",
            brief_md="Version one.",
        )
        await apply_packet(qe, test_settings, p1)
        p2 = ProgrammePacket(
            mission_slug="brief-replace",
            title="T",
            brief_md="Version two.",
        )
        await apply_packet(qe, test_settings, p2)
        row = await qe.get_mission_by_slug("brief-replace")
        assert row is not None
        assert row["brief_md"] == "Version two."
    finally:
        await qe.close()
