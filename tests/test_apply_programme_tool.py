"""apply_programme tool via confirm_and_apply."""

from __future__ import annotations

import pytest

from ada.programme.apply import confirm_and_apply
from ada.programme.packet import ProgrammePacket
from ada.query_engine import QueryEngine


@pytest.mark.asyncio
async def test_apply_denied_no_mission_row(tmp_path, schema_sql_path, test_settings) -> None:
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        packet = ProgrammePacket(mission_slug="deny-m", title="Deny")
        out = await confirm_and_apply(
            qe, test_settings, packet, approved=False, session_id=None
        )
        assert out.get("denied") is True
        assert await qe.get_mission_by_slug("deny-m") is None
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_apply_approved_creates_mission(tmp_path, schema_sql_path, test_settings) -> None:
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        packet = ProgrammePacket(
            mission_slug="apply-h3",
            title="Apply H3",
            brief_md="Tool apply brief intent.",
            knowledge_sources=[],
        )
        out = await confirm_and_apply(
            qe, test_settings, packet, approved=True, session_id=None
        )
        assert out.get("ok") is True
        row = await qe.get_mission_by_slug("apply-h3")
        assert row is not None
        assert row["brief_md"] == "Tool apply brief intent."
    finally:
        await qe.close()

