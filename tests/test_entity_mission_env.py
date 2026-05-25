"""ADA_CHAT_DEFAULT_MISSION applies only with explicit mission binding."""

from __future__ import annotations

import pytest

from ada.chat_ingress import ChatIngressMode, ChatSurfaceMode
from ada.chat_session import ChatSession, resolve_chat_mission_id
from ada.query_engine import QueryEngine


@pytest.mark.asyncio
async def test_plain_chat_ignores_default_mission_env(
    schema_sql_path, test_settings, monkeypatch
) -> None:
    monkeypatch.setenv("ADA_CHAT_DEFAULT_MISSION", "ada_ops")
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        await qe.create_mission(slug="ada_ops", title="Ops")
        mid = await resolve_chat_mission_id(
            qe, test_settings, None, apply_env_default=False
        )
        assert mid is None
        session = await ChatSession.open(
            test_settings,
            new_session=True,
            surface_mode=ChatSurfaceMode.CHAT,
            apply_env_default=False,
        )
        try:
            assert session.surface == ChatSurfaceMode.CHAT
            assert session.mission_id is None
        finally:
            await session.close()
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_chat_mission_flag_uses_explicit_slug(
    schema_sql_path, test_settings, monkeypatch
) -> None:
    monkeypatch.setenv("ADA_CHAT_DEFAULT_MISSION", "other-m")
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        await qe.create_mission(slug="explicit-m", title="Explicit")
        await qe.create_mission(slug="other-m", title="Other")
        session = await ChatSession.open(
            test_settings,
            new_session=True,
            agent_mode=True,
            mission_slug="explicit-m",
            apply_env_default=True,
        )
        try:
            assert session.surface == ChatSurfaceMode.AGENT
            row = await qe.get_mission_by_slug("explicit-m")
            assert session.mission_id is None
            assert session.effective_mission_id == int(row["id"])
            assert session.default_mission_slug == "explicit-m"
        finally:
            await session.close()
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_env_default_fills_empty_explicit_mission_slug(
    schema_sql_path, test_settings, monkeypatch
) -> None:
    monkeypatch.setenv("ADA_CHAT_DEFAULT_MISSION", "env-m")
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        await qe.create_mission(slug="env-m", title="Env")
        mid = await resolve_chat_mission_id(
            qe, test_settings, "", apply_env_default=True
        )
        row = await qe.get_mission_by_slug("env-m")
        assert mid == int(row["id"])
    finally:
        await qe.close()
