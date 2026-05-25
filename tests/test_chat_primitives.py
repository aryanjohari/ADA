"""J2: CHAT surface exposes run_primitive, not run_skill; NULL task mission."""

from __future__ import annotations

import pytest

from ada.chat_capability import PRIMITIVE_ALLOWLIST, profile_chat
from ada.chat_ingress import ChatSurfaceMode
from ada.chat_session import ChatSession
from ada.config import Settings
from ada.query_engine import QueryEngine
from ada.tools.registry import build_agent_tools, frozen_tool_declaration_names


def test_chat_profile_includes_run_primitive_not_run_skill() -> None:
    p = profile_chat(Settings.load())
    assert p.include_run_primitive is True
    assert p.include_run_skill is False
    assert p.primitive_allowlist == PRIMITIVE_ALLOWLIST

    tool = build_agent_tools(
        allowed_exact_commands=frozenset(),
        include_memory_tools=False,
        include_mission_control_snapshot=True,
        include_run_skill=p.include_run_skill,
        include_run_primitive=p.include_run_primitive,
        include_propose_programme=p.include_propose_programme,
        knowledge_tool_subset=p.knowledge_tool_subset,
    )
    names = frozen_tool_declaration_names(tool)
    assert "run_primitive" in names
    assert "run_skill" not in names


@pytest.mark.asyncio
async def test_chat_session_null_mission_and_run_primitive(
    schema_sql_path, test_settings, monkeypatch
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "fake")
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        session = await ChatSession.open(
            test_settings,
            new_session=True,
            surface_mode=ChatSurfaceMode.CHAT,
            apply_env_default=False,
        )
        try:
            assert session.surface == ChatSurfaceMode.CHAT
            assert session.mission_id is None
            assert session.include_run_primitive is True
            assert session.include_run_skill is False
            mission_id = await qe.get_task_mission_id(session.task_id)
            assert mission_id is None
            flags = session._orchestrate_common()
            assert flags["include_run_primitive"] is True
            assert flags["include_run_skill"] is False
            assert flags["primitive_allowlist"] == PRIMITIVE_ALLOWLIST
        finally:
            await session.close()
    finally:
        await qe.close()
