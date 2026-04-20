from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import ada
import pytest
import json

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
        goal_rows = [g for g in goals if f"knowledge item ID: {kid}" in g["goal"]]
        assert len(goal_rows) == 1
        assert "[tier:macro]" in goal_rows[0]["goal"]
        plan = json.loads(goal_rows[0]["plan_json"])
        assert plan["tier"] == "macro"
        assert int(plan["knowledge_id"]) == kid
    finally:
        await qe2.close()


@pytest.mark.asyncio
async def test_triage_tier2_respects_daily_cap(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("ADA_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ADA_TRIAGE_LEAD_DAILY_CAP", "1")

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
        for i in range(2):
            ins = await qe.insert_knowledge_item(
                sid,
                f"hash-lead-{i}",
                content_excerpt="Local supplier issues are hurting businesses.",
                payload={"title": f"Lead {i}", "link": f"https://ex.test/l/{i}"},
            )
            assert ins.inserted
    finally:
        await qe.close()

    class _FakeResp:
        text = '{"impact_score": 6}'

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
    assert stats.processed == 2
    assert stats.scored == 2
    assert stats.deep_dives_enqueued == 1

    qe2 = QueryEngine(
        settings.state_db_path,
        schema_path,
        debounce_ms=settings.persist_debounce_ms,
    )
    await qe2.connect()
    try:
        goals = await qe2.list_goal_tasks(limit=20)
        lead_goals = [g for g in goals if "[tier:lead]" in g["goal"]]
        assert len(lead_goals) == 1
        plan = json.loads(lead_goals[0]["plan_json"])
        assert plan["tier"] == "lead"
    finally:
        await qe2.close()
