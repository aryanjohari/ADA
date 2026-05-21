"""ChatSession one-turn test (no Streamlit import)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from ada.chat_session import ChatSession
from ada.query_engine import QueryEngine


@pytest.mark.asyncio
async def test_chat_session_send_message_binds_mission(
    schema_sql_path, test_settings, monkeypatch
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key-for-test")
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        mid = await qe.create_mission(slug="chat-s", title="Chat S")
        session = await ChatSession.open(
            test_settings,
            new_session=True,
            agent_mode=True,
            mission_slug="chat-s",
            apply_env_default=True,
        )
        try:
            assert session.mission_id is None
            assert session.effective_mission_id == mid
            with patch(
                "ada.chat_session.orchestrate_turn",
                new_callable=AsyncMock,
                return_value="ok reply",
            ):
                out = await session.send_message("hello")
            assert out == "ok reply"
            got = await qe.get_task_mission_id(session.task_id)
            assert got is None
        finally:
            await session.close()
    finally:
        await qe.close()
