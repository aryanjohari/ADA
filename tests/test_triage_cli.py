from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import ada
import pytest

from ada.config import Settings
from ada.query_engine import QueryEngine
from ada.triage.run import run_triage_cli


@pytest.mark.asyncio
async def test_triage_updates_score_and_enqueues_goal_when_high_impact(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("ADA_DATA_DIR", str(tmp_path))

    settings = Settings.load()
    settings.ensure_data_dir()
    schema_path = Path(ada.__path__[0]) / "db" / "schema.sql"
    qe = QueryEngine(
        settings.state_db_path,
        schema_path,
        debounce_ms=settings.persist_debounce_ms,
    )
    await qe.connect()
    try:
        sid = await qe.insert_knowledge_source("rss", label="t", base_url="https://ex.test/f")
        ins = await qe.insert_knowledge_item(
            sid,
            "hash-triage-test",
            content_excerpt="RBNZ signals shift affecting NZ mortgage rates.",
            payload={"title": "Policy note", "link": "https://ex.test/a"},
        )
        assert ins.inserted
        kid = ins.id
    finally:
        await qe.close()

    class _FakeResp:
        text = '{"impact_score": 8}'

    mock_client = MagicMock()

    async def _fake_generate(*_a, **_k):
        return _FakeResp()

    mock_client.aio.models.generate_content = AsyncMock(side_effect=_fake_generate)

    stats, code = await run_triage_cli(
        settings,
        limit=20,
        client_cls=lambda **kwargs: mock_client,
    )

    assert code == 0
    assert stats.processed == 1
    assert stats.scored == 1
    assert stats.skipped == 0
    assert stats.deep_dives_enqueued == 1

    qe2 = QueryEngine(
        settings.state_db_path,
        schema_path,
        debounce_ms=settings.persist_debounce_ms,
    )
    await qe2.connect()
    try:
        item = await qe2.get_knowledge_item(kid)
        assert item["impact_score"] == 8
        goals = await qe2.list_goal_tasks(limit=10)
        expected = (
            f"Perform deep-dive synthesis on high-impact knowledge item ID: {kid}"
        )
        assert any(g["goal"] == expected for g in goals)
    finally:
        await qe2.close()
