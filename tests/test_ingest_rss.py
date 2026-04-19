from __future__ import annotations

from pathlib import Path

import pytest

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
