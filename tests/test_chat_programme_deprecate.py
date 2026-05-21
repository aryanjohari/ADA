"""Deprecated ada chat --programme maps to Entity with propose."""

from __future__ import annotations

import pytest

from ada.chat_ingress import ChatSurfaceMode
from ada.chat_session import ChatSession
from ada.query_engine import QueryEngine


@pytest.mark.asyncio
async def test_programme_flag_opens_entity_with_propose(
    schema_sql_path, test_settings, monkeypatch, capsys
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "fake")
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        session = await ChatSession.open(
            test_settings,
            new_session=True,
            programme_mode=True,
            apply_env_default=False,
        )
        try:
            err = capsys.readouterr().err
            assert "deprecated" in err.lower()
            assert session.surface == ChatSurfaceMode.PLAN
            assert session.include_propose is True
            assert session.include_run_skill is False
            prof = session.profile
            assert prof.include_apply_programme is True
        finally:
            await session.close()
    finally:
        await qe.close()
