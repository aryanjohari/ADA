"""Orchestrator harness appendix and chat session inject (Phase D)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from google.genai import types

from ada.adapters.gemini_stream import apply_turn_harness_appendix_to_contents
from ada.chat_ingress import ChatSurfaceMode
from ada.chat_session import ChatSession
from ada.chat_session import complete_chat_task_if_any
from ada.prompt import format_programme_digest_appendix
from ada.query_engine import QueryEngine, TASK_KIND_CHAT


def test_apply_turn_harness_appendix_prepends_to_last_user() -> None:
    contents = [
        types.Content(role="user", parts=[types.Part.from_text(text="hi")]),
        types.Content(role="model", parts=[types.Part.from_text(text="hello")]),
        types.Content(role="user", parts=[types.Part.from_text(text="status?")]),
    ]
    appendix = "[ProgrammeDigest]\n{}"
    out = apply_turn_harness_appendix_to_contents(contents, appendix)
    assert len(out) == 3
    last = out[-1]
    assert last.role == "user"
    assert appendix in last.parts[0].text
    assert "status?" in last.parts[0].text


def test_format_programme_digest_appendix_delimiters() -> None:
    text = format_programme_digest_appendix({"schema_version": 1, "mission_slug": "x"})
    assert "[ProgrammeDigest" in text
    assert "[/ProgrammeDigest]" in text


@pytest.mark.asyncio
async def test_chat_session_injects_appendix_first_turn(
    schema_sql_path, test_settings, monkeypatch
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "fake")
    monkeypatch.setenv("ADA_INJECT_PROGRAMME_DIGEST", "1")
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        schedule = {
            "version": 1,
            "jobs": [
                {
                    "id": "daily_brief",
                    "min_interval_hours": 24,
                    "action": {"type": "enqueue_goal", "goal_text": "brief"},
                }
            ],
        }
        await qe.create_mission(
            slug="inject-m",
            title="Inject",
            schedule_hint_json=schedule,
        )
        session = await ChatSession.open(
            test_settings,
            new_session=True,
            agent_mode=True,
            mission_slug="inject-m",
            apply_env_default=True,
        )
        try:
            assert session.surface == ChatSurfaceMode.AGENT
            assert session.effective_mission_id is not None
            captured: dict = {}

            async def _orch(**kwargs):
                captured.update(kwargs)
                return "ok"

            with patch(
                "ada.chat_session.orchestrate_turn",
                new_callable=AsyncMock,
                side_effect=_orch,
            ):
                await session.send_message("hello")
            assert captured.get("user_text") == "hello"
            appendix = captured.get("turn_harness_appendix")
            assert appendix is not None
            assert "daily_brief" in appendix
            assert "ProgrammeDigest" in appendix
        finally:
            await session.close()
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_complete_chat_task_if_any(schema_sql_path, test_settings) -> None:
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        tid = await qe.insert_task(
            "HUD chat",
            status="executing",
            task_kind=TASK_KIND_CHAT,
        )
        await complete_chat_task_if_any(
            test_settings, tid, schema_path=schema_sql_path
        )
        from ada.observability.queries import open_readonly_connection

        conn = open_readonly_connection(test_settings.state_db_path)
        try:
            cur = conn.execute("SELECT status FROM tasks WHERE id = ?", (tid,))
            row = cur.fetchone()
        finally:
            conn.close()
        assert row is not None
        assert row["status"] == "completed"
    finally:
        await qe.close()
