"""Mocked graph-lite extraction: excluded-only docs yield empty entities/edges."""

from __future__ import annotations

import pytest

from ada.extract.graph_lite import run_graph_lite_extraction
from ada.query_engine import QueryEngine


@pytest.mark.asyncio
async def test_graph_lite_empty_output_weather_only_mocked(tmp_path, schema_sql_path):
    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        sid = await qe.insert_knowledge_source(
            "rss", label="src", base_url="https://example.test/feed"
        )
        await qe.insert_knowledge_item(
            sid,
            "h-weather",
            content_excerpt=(
                "Auckland today: fine spells, light winds, high 22°C. "
                "Coastal showers possible overnight."
            ),
            payload={"title": "Daily weather: Auckland", "link": "https://example.test/w"},
        )

        async def fake_extractor(_docs):
            return {
                "entities": [],
                "edges": [],
                "schema_rationale": "skipped: excluded content",
            }

        stats = await run_graph_lite_extraction(
            qe,
            limit=10,
            token_cap=4000,
            extractor=fake_extractor,
            seed_triage_categories=False,
        )
        assert stats.processed_docs >= 1
        assert stats.entities_upserted == 0
        assert stats.edges_created == 0
        assert stats.evidence_links_created == 0
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_graph_lite_empty_output_cartoons_only_mocked(tmp_path, schema_sql_path):
    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        sid = await qe.insert_knowledge_source(
            "rss", label="src", base_url="https://example.test/feed"
        )
        await qe.insert_knowledge_item(
            sid,
            "h-toon",
            content_excerpt=(
                "This week in the funny pages: a cat knocks over a vase. "
                "Readers share their favourite cartoon strips."
            ),
            payload={"title": "Cartoon roundup", "link": "https://example.test/c"},
        )

        async def fake_extractor(_docs):
            return {
                "entities": [],
                "edges": [],
                "schema_rationale": "skipped: excluded content",
            }

        stats = await run_graph_lite_extraction(
            qe,
            limit=10,
            token_cap=4000,
            extractor=fake_extractor,
            seed_triage_categories=False,
        )
        assert stats.processed_docs >= 1
        assert stats.entities_upserted == 0
        assert stats.edges_created == 0
        assert stats.evidence_links_created == 0
    finally:
        await qe.close()
