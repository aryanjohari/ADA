"""Phase B smoke: template dry-run + motor skill + programme propose."""

from __future__ import annotations

import json

import pytest

from ada.mission_cli import _load_mission_template
from ada.motor.registry import clear_registry_cache
from ada.programme.packet import ProgrammePacket
from ada.programme.propose import propose_packet


def test_template_load_research() -> None:
    data = _load_mission_template("research")
    assert data["mission_slug"] == "research"
    assert "weekly_research_goal" in data["skills_enabled"]


def test_propose_template_packet() -> None:
    data = _load_mission_template("research")
    out = propose_packet(data)
    assert "packet" in out
    packet = ProgrammePacket.model_validate(out["packet"])
    assert packet.mission_slug == "research"


@pytest.mark.asyncio
async def test_apply_template_dry_run_via_cli_logic(schema_sql_path, test_settings) -> None:
    from ada.mission_cli import _run_apply_template
    import argparse

    clear_registry_cache()
    from ada.query_engine import QueryEngine

    qe = QueryEngine(test_settings.state_db_path, schema_sql_path)
    await qe.connect()
    try:
        args = argparse.Namespace(name="research", dry_run=True, yes=False)
        code = await _run_apply_template(qe, test_settings, args)
        assert code == 0
    finally:
        await qe.close()
