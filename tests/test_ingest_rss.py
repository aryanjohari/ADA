from __future__ import annotations

from pathlib import Path

import pytest

from types import SimpleNamespace

from ada.ingest.rss import ingest_rss_feeds
from ada.query_engine import QueryEngine


FIXTURE_XML = (
    Path(__file__).resolve().parent / "fixtures" / "sample_rss.xml"
).read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_ingest_rss_inserts_items(tmp_path, schema_sql_path):
    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        sid = await qe.insert_knowledge_source(
            "rss", label="Test", base_url="https://example.com/feed.xml"
        )

        async def fake_fetch(url: str) -> str:
            assert "example.com" in url
            return FIXTURE_XML

        res = await ingest_rss_feeds(
            qe,
            max_items_per_feed=10,
            fetch_text=fake_fetch,
        )
        assert res.feeds_attempted == 1
        assert res.feeds_ok == 1
        assert res.items_inserted == 2
        assert res.items_deduped == 0
        items = await qe.list_knowledge_items(source_id=sid, limit=20)
        assert len(items) == 2
        titles = {i["content_excerpt"] for i in items}
        assert any("First headline" in t for t in titles)
        assert any("Second headline" in t for t in titles)
        for i in items:
            assert i["relevance_score"] == 1.0
            assert i["expires_at"] is None
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_ingest_rss_dedupe_second_run(tmp_path, schema_sql_path):
    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        await qe.insert_knowledge_source(
            "rss", label="Test", base_url="https://example.com/feed.xml"
        )

        async def fake_fetch(url: str) -> str:
            return FIXTURE_XML

        r1 = await ingest_rss_feeds(qe, max_items_per_feed=10, fetch_text=fake_fetch)
        r2 = await ingest_rss_feeds(qe, max_items_per_feed=10, fetch_text=fake_fetch)
        assert r1.items_inserted == 2
        assert r2.items_inserted == 0
        assert r2.items_deduped == 2
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_ingest_rss_dedupes_same_story_link_across_feeds(
    tmp_path, schema_sql_path
):
    """Two RSS sources returning the same entries (same article URLs) → one row per story."""
    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        await qe.insert_knowledge_source(
            "rss", label="FeedA", base_url="https://example.com/a.xml"
        )
        await qe.insert_knowledge_source(
            "rss", label="FeedB", base_url="https://example.com/b.xml"
        )

        async def fake_fetch(url: str) -> str:
            return FIXTURE_XML

        res = await ingest_rss_feeds(
            qe,
            max_items_per_feed=10,
            fetch_text=fake_fetch,
        )
        assert res.feeds_attempted == 2
        assert res.feeds_ok == 2
        assert res.items_inserted == 2
        assert res.items_deduped == 2
        all_items = await qe.list_knowledge_items(limit=20)
        assert len(all_items) == 2
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_ingest_rss_sets_expires_when_retention_configured(
    tmp_path, schema_sql_path
):
    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        sid = await qe.insert_knowledge_source(
            "rss", label="Test", base_url="https://example.com/feed.xml"
        )
        settings = SimpleNamespace(
            ingest_gatekeeper=False,
            gemini_api_key="",
            ingest_gate_model="gemini-2.5-flash-lite",
            ingest_gate_max_output_tokens=None,
            knowledge_default_retention_days=7,
            enable_knowledge_embeddings=False,
            knowledge_embedding_model="m",
            knowledge_embedding_dim=768,
        )

        async def fake_fetch(url: str) -> str:
            return FIXTURE_XML

        await ingest_rss_feeds(
            qe,
            settings=settings,
            max_items_per_feed=10,
            fetch_text=fake_fetch,
        )
        items = await qe.list_knowledge_items(source_id=sid, limit=20)
        assert len(items) == 2
        for i in items:
            assert i["expires_at"] is not None
            assert "T" in (i["expires_at"] or "")
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_ingest_gate_mocked_scores_items(tmp_path, schema_sql_path, monkeypatch):
    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        await qe.insert_knowledge_source(
            "rss", label="Test", base_url="https://example.com/feed.xml"
        )
        settings = SimpleNamespace(
            ingest_gatekeeper=True,
            gemini_api_key="fake-key",
            ingest_gate_model="gemini-2.5-flash-lite",
            ingest_gate_max_output_tokens=256,
            knowledge_default_retention_days=None,
            enable_knowledge_embeddings=False,
            knowledge_embedding_model="m",
            knowledge_embedding_dim=768,
        )

        async def fake_gate(*_a, **_k):
            return (0.35, ["gate-tag"])

        monkeypatch.setattr("ada.ingest.rss.score_feed_entry", fake_gate)

        async def fake_fetch(url: str) -> str:
            return FIXTURE_XML

        await ingest_rss_feeds(
            qe,
            settings=settings,
            max_items_per_feed=10,
            fetch_text=fake_fetch,
        )
        items = await qe.list_knowledge_items(limit=20)
        assert len(items) == 2
        for i in items:
            assert i["relevance_score"] == 0.35
            assert "gate-tag" in i["tags"]
    finally:
        await qe.close()
