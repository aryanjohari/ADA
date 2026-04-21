from __future__ import annotations

import pytest

from ada.extract.graph_lite import run_graph_lite_extraction
from ada.query_engine import QueryEngine


@pytest.mark.asyncio
async def test_graph_lite_pipeline_fetch_extract_validate_store(tmp_path, schema_sql_path):
    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        sid = await qe.insert_knowledge_source(
            "rss", label="src", base_url="https://example.test/feed"
        )
        ins1 = await qe.insert_knowledge_item(
            sid,
            "h1",
            content_excerpt="Acme supplies industrial pumps to dairy processors in NZ.",
        )
        ins2 = await qe.insert_knowledge_item(
            sid,
            "h2",
            content_excerpt="Policy note references equipment demand and logistics constraints.",
        )

        async def fake_extractor(_docs):
            return {
                "entities": [
                    {"type": "company", "name": "Acme Pumps"},
                    {"type": "niche", "name": "Dairy Processing"},
                ],
                "edges": [
                    {
                        "src_key": "company:acme pumps",
                        "dst_key": "niche:dairy processing",
                        "edge_type": "supplies",
                        "confidence": 0.72,
                        "evidence_item_ids": [ins1.id, ins2.id],
                    }
                ],
            }

        stats = await run_graph_lite_extraction(
            qe,
            limit=10,
            token_cap=4000,
            extractor=fake_extractor,
            seed_triage_categories=False,
        )
        assert stats.processed_docs >= 2
        assert stats.edges_created == 1
        evidence = await qe.list_edge_evidence(1)
        assert len(evidence) == 2
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_graph_lite_pipeline_rejects_low_confidence(tmp_path, schema_sql_path):
    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        sid = await qe.insert_knowledge_source(
            "rss", label="src", base_url="https://example.test/feed"
        )
        ins = await qe.insert_knowledge_item(
            sid,
            "h3",
            content_excerpt="Possible weak signal from one source.",
        )

        async def fake_extractor(_docs):
            return {
                "entities": [
                    {"type": "company", "name": "SignalCo"},
                    {"type": "region", "name": "New Zealand"},
                ],
                "edges": [
                    {
                        "src_key": "company:signalco",
                        "dst_key": "region:new zealand",
                        "edge_type": "needs",
                        "confidence": 0.30,
                        "evidence_item_ids": [ins.id],
                    }
                ],
            }

        stats = await run_graph_lite_extraction(
            qe,
            limit=10,
            token_cap=4000,
            extractor=fake_extractor,
            seed_triage_categories=False,
        )
        assert stats.edges_created == 0
        assert stats.rejected >= 1
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_graph_lite_extractor_payload_ignores_schema_rationale(tmp_path, schema_sql_path):
    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        sid = await qe.insert_knowledge_source(
            "rss", label="src", base_url="https://example.test/feed"
        )
        await qe.insert_knowledge_item(
            sid,
            "h-rat",
            content_excerpt="Test excerpt for rationale strip.",
        )

        async def fake_extractor(_docs):
            return {
                "entities": [{"type": "company", "name": "RationaleCo"}],
                "edges": [],
                "schema_rationale": "debug only",
            }

        stats = await run_graph_lite_extraction(
            qe,
            limit=10,
            token_cap=4000,
            extractor=fake_extractor,
            seed_triage_categories=False,
        )
        assert stats.processed_docs >= 1
        assert stats.entities_upserted >= 1
    finally:
        await qe.close()

