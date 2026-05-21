"""ProfileDigest injection policy for Entity chat."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from ada.chat_ingress import ChatSurfaceMode
from ada.chat_session import ChatSession
from ada.mission_control.inject_policy import (
    should_inject_profile_digest,
    user_message_matches_profile_intent,
)
from ada.prompt import format_profile_digest_appendix
from ada.query_engine import QueryEngine


def test_user_message_matches_profile_intent() -> None:
    assert user_message_matches_profile_intent("what missions exist?")
    assert user_message_matches_profile_intent("weather in Auckland")
    assert not user_message_matches_profile_intent("hello there")


def test_should_inject_profile_digest_entity_turn_zero() -> None:
    assert should_inject_profile_digest(
        entity_mode=True,
        mission_id=None,
        user_turn_count_before=0,
        user_text="hi",
    )


def test_should_not_inject_profile_digest_work() -> None:
    assert not should_inject_profile_digest(
        entity_mode=False,
        mission_id=1,
        user_turn_count_before=0,
        user_text="hi",
    )


def test_format_profile_digest_appendix_delimiters() -> None:
    text = format_profile_digest_appendix({"schema_version": 1})
    assert "[ProfileDigest" in text
    assert "[/ProfileDigest]" in text


@pytest.mark.asyncio
async def test_chat_session_injects_profile_digest_entity(
    schema_sql_path, test_settings, monkeypatch
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "fake")
    monkeypatch.setenv("ADA_INJECT_PROFILE_DIGEST", "1")
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        await qe.create_mission(slug="entity-m", title="Entity M")
        session = await ChatSession.open(
            test_settings,
            new_session=True,
            mission_slug=None,
            apply_env_default=False,
        )
        try:
            assert session.surface == ChatSurfaceMode.CHAT
            assert session.entity_mode is True
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
            appendix = captured.get("turn_harness_appendix")
            assert appendix is not None
            assert "ProfileDigest" in appendix
            assert "entity-m" in appendix
        finally:
            await session.close()
    finally:
        await qe.close()
