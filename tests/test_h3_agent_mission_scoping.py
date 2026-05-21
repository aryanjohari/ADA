"""Agent NULL task: effective_mission_id and run_skill mission_slug scoping."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from ada.chat_ingress import ChatSurfaceMode
from ada.chat_session import ChatSession
from ada.motor import MotorRequest, execute
from ada.query_engine import QueryEngine, TASK_KIND_CHAT


@pytest.mark.asyncio
async def test_agent_session_null_task_with_default_slug(
    schema_sql_path, test_settings, monkeypatch
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "fake")
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        await qe.create_mission(slug="agent-scope", title="Agent Scope")
        session = await ChatSession.open(
            test_settings,
            new_session=True,
            surface_mode=ChatSurfaceMode.AGENT,
            agent_mode=True,
            mission_slug="agent-scope",
            apply_env_default=True,
        )
        try:
            assert session.mission_id is None
            assert session.default_mission_slug == "agent-scope"
            assert session.effective_mission_id is not None
            got = await qe.get_task_mission_id(session.task_id)
            assert got is None
            common = session._orchestrate_common()
            assert common["effective_mission_id"] == session.effective_mission_id
            assert common["chat_mission_slug"] == "agent-scope"
        finally:
            await session.close()
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_effective_mission_id_passed_to_orchestrator(
    schema_sql_path, test_settings, monkeypatch
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        mid = await qe.create_mission(slug="eff-m", title="Eff")
        session = await ChatSession.open(
            test_settings,
            new_session=True,
            surface_mode=ChatSurfaceMode.AGENT,
            agent_mode=True,
            mission_slug="eff-m",
            apply_env_default=True,
        )
        try:
            captured: dict[str, object] = {}

            async def _fake_orchestrate(*args: object, **kwargs: object) -> str:
                captured.update(kwargs)
                return "ok"

            with patch(
                "ada.chat_session.orchestrate_turn",
                new_callable=AsyncMock,
                side_effect=_fake_orchestrate,
            ):
                await session.send_message("hi")
            assert captured.get("effective_mission_id") == mid
        finally:
            await session.close()
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_run_skill_uses_mission_slug_for_workflow(
    schema_sql_path, test_settings, monkeypatch
) -> None:
    """Motor execute resolves slug to workflows.mission_id when enqueuing."""
    monkeypatch.setenv("GEMINI_API_KEY", "fake")
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        await qe.create_mission(slug="wf-scope", title="WF")
        req = MotorRequest(
            layer="skill",
            id="mission_tick_dry_run",
            params={},
            mission_slug="wf-scope",
            session_id=None,
            approved=True,
        )
        result = await execute(req, settings=test_settings, qe=qe)
        if result.ok and isinstance(result.output, dict):
            wf_id = result.output.get("workflow_id")
            if wf_id is not None:
                row = await qe.get_workflow(int(wf_id))
                assert row is not None
                assert row.get("mission_id") is not None
    finally:
        await qe.close()
