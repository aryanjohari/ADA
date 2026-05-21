"""Streamlit chat ingress resolution (no Streamlit runtime)."""

from __future__ import annotations

import pytest

from ada.chat_ingress import ChatSurfaceMode, resolve_chat_surface_mode
from ada.chat_session import resolve_chat_mission_id
from ada.query_engine import QueryEngine


def test_empty_slug_resolves_chat() -> None:
    mode = resolve_chat_surface_mode()
    assert mode == ChatSurfaceMode.CHAT


@pytest.mark.asyncio
async def test_agent_surface_with_slug(schema_sql_path, test_settings) -> None:
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        await qe.create_mission(slug="hud-w", title="HUD W")
        mode = resolve_chat_surface_mode(agent_mode=True)
        assert mode == ChatSurfaceMode.AGENT
        mid = await resolve_chat_mission_id(
            qe, test_settings, "hud-w", apply_env_default=True
        )
        assert mid is not None
    finally:
        await qe.close()
