from __future__ import annotations

import pytest

from ada.knowledge_embeddings import float32_list_to_blob
from ada.knowledge_search import build_fts_match_query
from ada.query_engine import QueryEngine


def test_build_fts_match_query_basic():
    assert build_fts_match_query("foo bar") == "foo OR bar"
    assert build_fts_match_query("Hastings or Salvation") == "hastings OR salvation"
    assert build_fts_match_query("") == ""
    assert build_fts_match_query("   ") == ""


def test_reciprocal_rank_fusion_orders():
    from ada.knowledge_search import reciprocal_rank_fusion

    fused = reciprocal_rank_fusion([[1, 2, 3], [3, 1, 4]])
    assert fused[0] in (1, 3)
    assert set(fused) == {1, 2, 3, 4}


@pytest.mark.asyncio
async def test_insert_dedupe_content_hash_no_external_id(tmp_path, schema_sql_path):
    db = tmp_path / "k.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        sid = await qe.insert_knowledge_source("web")
        h = "hash-stable"
        x = await qe.insert_knowledge_item(
            sid, h, content_excerpt="first", external_id=None
        )
        y = await qe.insert_knowledge_item(
            sid, h, content_excerpt="second try", external_id=None
        )
        assert x.inserted and not y.inserted
        assert x.id == y.id
        row = await qe.get_knowledge_item(x.id)
        assert row["content_excerpt"] == "first"
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_list_knowledge_items_time_range(tmp_path, schema_sql_path):
    db = tmp_path / "k.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        import aiosqlite

        sid = await qe.insert_knowledge_source("rss")
        a = (await qe.insert_knowledge_item(sid, "h1", content_excerpt="a")).id
        b = (await qe.insert_knowledge_item(sid, "h2", content_excerpt="b")).id
        async with aiosqlite.connect(db) as raw:
            await raw.execute(
                "UPDATE knowledge_items SET ingested_at = ? WHERE id = ?",
                ("2026-01-10T12:00:00Z", a),
            )
            await raw.execute(
                "UPDATE knowledge_items SET ingested_at = ? WHERE id = ?",
                ("2026-02-10T12:00:00Z", b),
            )
            await raw.commit()
        mid = await qe.list_knowledge_items(
            source_id=sid,
            ingested_after="2026-01-15T00:00:00Z",
            ingested_before="2026-03-01T00:00:00Z",
            limit=50,
        )
        assert len(mid) == 1 and mid[0]["id"] == b
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_search_knowledge_items_corpus_fts(tmp_path, schema_sql_path):
    db = tmp_path / "k.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        sid = await qe.insert_knowledge_source("web")
        await qe.insert_knowledge_item(
            sid,
            "x1",
            tags=["housing"],
            content_excerpt="Auckland property market overview",
        )
        await qe.insert_knowledge_item(
            sid,
            "x2",
            tags=["sport"],
            content_excerpt="Rugby scores unrelated",
        )
        hits = await qe.search_knowledge_items("Auckland property", limit=10)
        assert len(hits) >= 1
        assert any("Auckland" in h["content_excerpt"] for h in hits)
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_search_knowledge_items_tag_filter(tmp_path, schema_sql_path):
    db = tmp_path / "k.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        sid = await qe.insert_knowledge_source("rss")
        await qe.insert_knowledge_item(
            sid, "a", tags=["keep"], content_excerpt="alpha beta shared token"
        )
        await qe.insert_knowledge_item(
            sid, "b", tags=["drop"], content_excerpt="alpha beta shared token"
        )
        hits = await qe.search_knowledge_items(
            "alpha", tag="keep", limit=10
        )
        assert len(hits) == 1
        assert hits[0]["tags"] == ["keep"]
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_search_knowledge_items_time_filter(tmp_path, schema_sql_path):
    db = tmp_path / "k.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        import aiosqlite

        sid = await qe.insert_knowledge_source("api")
        i1 = (
            await qe.insert_knowledge_item(sid, "z1", content_excerpt="omega particle")
        ).id
        i2 = (
            await qe.insert_knowledge_item(sid, "z2", content_excerpt="omega wave")
        ).id
        async with aiosqlite.connect(db) as raw:
            await raw.execute(
                "UPDATE knowledge_items SET ingested_at = ? WHERE id = ?",
                ("2026-01-05T00:00:00Z", i1),
            )
            await raw.execute(
                "UPDATE knowledge_items SET ingested_at = ? WHERE id = ?",
                ("2026-06-01T00:00:00Z", i2),
            )
            await raw.commit()
        hits = await qe.search_knowledge_items(
            "omega",
            ingested_after="2026-03-01T00:00:00Z",
            limit=10,
        )
        ids = {h["id"] for h in hits}
        assert i2 in ids and i1 not in ids
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_search_knowledge_items_limit_enforced(tmp_path, schema_sql_path):
    db = tmp_path / "k.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        sid = await qe.insert_knowledge_source("web")
        for n in range(8):
            await qe.insert_knowledge_item(
                sid, f"hh{n}", content_excerpt=f"keyword shared {n}"
            )
        hits = await qe.search_knowledge_items("keyword shared", limit=3)
        assert len(hits) == 3
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_search_knowledge_items_or_stopwords(tmp_path, schema_sql_path):
    """OR-token query matches when AND would require the word 'or' in the doc."""
    db = tmp_path / "k.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        sid = await qe.insert_knowledge_source("rss")
        await qe.insert_knowledge_item(
            sid,
            "h1",
            content_excerpt="Police incident in Hastings today",
        )
        hits = await qe.search_knowledge_items(
            "Hastings or Auckland", limit=10, search_mode="lexical"
        )
        assert len(hits) >= 1
        assert any("Hastings" in h["content_excerpt"] for h in hits)
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_search_knowledge_tool_payload_fields(tmp_path, schema_sql_path):
    db = tmp_path / "k.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        sid = await qe.insert_knowledge_source("rss")
        await qe.insert_knowledge_item(
            sid,
            "p1",
            content_excerpt="Hello",
            payload={
                "title": "T1",
                "link": "https://example.com/a",
                "feed_url": "https://feed",
            },
        )
        hits = await qe.search_knowledge_items("Hello", limit=5)
        assert len(hits) == 1
        assert hits[0]["payload"]["link"] == "https://example.com/a"
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_search_knowledge_semantic_mode(tmp_path, schema_sql_path):
    db = tmp_path / "k.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        sid = await qe.insert_knowledge_source("rss")
        ins = await qe.insert_knowledge_item(
            sid, "eh1", content_excerpt="alpha beta gamma"
        )
        model = "test-model"
        v = [1.0, 0.0, 0.0]
        await qe.upsert_knowledge_item_embedding(
            ins.id,
            model=model,
            dim=3,
            embedding=float32_list_to_blob(v),
            content_hash="eh1",
        )
        hits = await qe.search_knowledge_items(
            "ignored",
            limit=5,
            search_mode="semantic",
            query_embedding=[1.0, 0.0, 0.0],
            embedding_model=model,
            embedding_min_cosine=0.99,
        )
        assert len(hits) == 1
        assert hits[0]["id"] == ins.id
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_search_knowledge_semantic_respects_min_relevance(
    tmp_path, schema_sql_path
):
    db = tmp_path / "k.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        sid = await qe.insert_knowledge_source("rss")
        ins_low = await qe.insert_knowledge_item(
            sid, "low", content_excerpt="vec topic", relevance_score=0.1
        )
        ins_high = await qe.insert_knowledge_item(
            sid, "high", content_excerpt="vec topic", relevance_score=0.95
        )
        model = "test-model"
        v = [0.0, 1.0, 0.0]
        blob = float32_list_to_blob(v)
        await qe.upsert_knowledge_item_embedding(
            ins_low.id,
            model=model,
            dim=3,
            embedding=blob,
            content_hash="low",
        )
        await qe.upsert_knowledge_item_embedding(
            ins_high.id,
            model=model,
            dim=3,
            embedding=blob,
            content_hash="high",
        )
        hits = await qe.search_knowledge_items(
            "x",
            limit=10,
            search_mode="semantic",
            query_embedding=v,
            embedding_model=model,
            embedding_min_cosine=0.01,
            min_relevance_score=0.5,
        )
        ids = {h["id"] for h in hits}
        assert ins_low.id not in ids
        assert ins_high.id in ids
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_search_knowledge_min_relevance_and_expiry(tmp_path, schema_sql_path):
    db = tmp_path / "k.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        import aiosqlite

        sid = await qe.insert_knowledge_source("rss")
        low = (
            await qe.insert_knowledge_item(
                sid,
                "l1",
                content_excerpt="shared keyword low",
                relevance_score=0.2,
            )
        ).id
        high = (
            await qe.insert_knowledge_item(
                sid,
                "h1",
                content_excerpt="shared keyword high",
                relevance_score=0.9,
            )
        ).id
        legacy = (
            await qe.insert_knowledge_item(
                sid,
                "leg",
                content_excerpt="shared keyword legacy null score",
            )
        ).id
        hits = await qe.search_knowledge_items(
            "shared keyword",
            limit=10,
            search_mode="lexical",
            min_relevance_score=0.5,
        )
        ids = {h["id"] for h in hits}
        assert low not in ids
        assert high in ids
        assert legacy in ids

        async with aiosqlite.connect(db) as raw:
            await raw.execute(
                "UPDATE knowledge_items SET expires_at = ? WHERE id = ?",
                ("2020-01-01T00:00:00Z", high),
            )
            await raw.commit()
        hits2 = await qe.search_knowledge_items(
            "shared keyword",
            limit=10,
            search_mode="lexical",
            min_relevance_score=0.5,
            valid_at_now=True,
        )
        assert high not in {h["id"] for h in hits2}

        hits3 = await qe.search_knowledge_items(
            "shared keyword",
            limit=10,
            search_mode="lexical",
            min_relevance_score=0.5,
            valid_at_now=False,
        )
        assert high in {h["id"] for h in hits3}
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_search_knowledge_items_like_fallback(tmp_path, schema_sql_path):
    db = tmp_path / "k.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        sid = await qe.insert_knowledge_source("web")
        await qe.insert_knowledge_item(
            sid, "lb1", content_excerpt="unique like fallback phrase"
        )
        hits = await qe.search_knowledge_items(
            "fallback phrase", limit=5, prefer_fts=False
        )
        assert len(hits) == 1
    finally:
        await qe.close()
