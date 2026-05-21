"""WORK ingress tool flags unchanged after Entity slice."""

from __future__ import annotations

from dataclasses import replace

import pytest

from ada.chat_ingress import ChatSurfaceMode
from ada.chat_capability import ENTITY_KNOWLEDGE_TOOLS
from ada.chat_session import ChatSession
from ada.query_engine import QueryEngine


@pytest.mark.asyncio
async def test_work_session_tool_flags(schema_sql_path, test_settings, monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "fake")
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        await qe.create_mission(slug="work-reg", title="Work Reg")
        session = await ChatSession.open(
            test_settings,
            new_session=True,
            mission_slug="work-reg",
            legacy_work=True,
            apply_env_default=True,
        )
        try:
            golden = {
                "surface": ChatSurfaceMode.AGENT,
                "include_run_skill": True,
                "include_propose": False,
                "entity_mode": False,
                "knowledge_tool_subset": None,
            }
            assert session.surface == golden["surface"]
            assert session.mission_id is not None
            assert session.include_run_skill == golden["include_run_skill"]
            assert session.include_propose == golden["include_propose"]
            assert session.entity_mode == golden["entity_mode"]
            assert session.knowledge_tool_subset == golden["knowledge_tool_subset"]
            common = session._orchestrate_common()
            assert common["include_run_skill"] is True
            assert common["include_propose_programme"] is False
            assert common["include_workflow_tools"] == test_settings.enable_workflow_tools
            assert common["include_plan_tools"] == test_settings.enable_plan_tools
        finally:
            await session.close()
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_entity_session_tool_flags(schema_sql_path, test_settings, monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "fake")
    settings = replace(test_settings, enable_knowledge_tools=True)
    qe = QueryEngine(settings.state_db_path, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        session = await ChatSession.open(
            settings,
            new_session=True,
            surface_mode=ChatSurfaceMode.CHAT,
            apply_env_default=False,
        )
        try:
            assert session.surface == ChatSurfaceMode.CHAT
            assert session.include_run_skill is False
            assert session.include_propose is True
            assert session.knowledge_tool_subset == ENTITY_KNOWLEDGE_TOOLS
            common = session._orchestrate_common()
            assert common["include_run_skill"] is False
            assert common["include_propose_programme"] is True
            assert common["include_workflow_tools"] is False
            assert common["include_plan_tools"] is False
        finally:
            await session.close()
    finally:
        await qe.close()
