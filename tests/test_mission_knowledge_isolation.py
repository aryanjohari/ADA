"""Mission-scoped knowledge_items reads, link dedupe, entities, and recent-id listing."""

from __future__ import annotations

from pathlib import Path

import pytest

from ada.query_engine import QueryEngine


@pytest.fixture
def schema_sql_path() -> Path:
    return Path(__file__).resolve().parents[1] / "src" / "ada" / "db" / "schema.sql"


@pytest.mark.asyncio
async def test_knowledge_search_and_list_mission_isolation(tmp_path, schema_sql_path):
    db = tmp_path / "m.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        mid_a = await qe.create_mission(
            slug="mission-a",
            title="A",
            niche=None,
            topic=None,
            brief_md="",
        )
        mid_b = await qe.create_mission(
            slug="mission-b",
            title="B",
            niche=None,
            topic=None,
            brief_md="",
        )
        sa = await qe.insert_knowledge_source(
            "rss",
            label="feed-a",
            base_url="https://a.example/feed.xml",
            mission_id=mid_a,
        )
        sb = await qe.insert_knowledge_source(
            "rss",
            label="feed-b",
            base_url="https://b.example/feed.xml",
            mission_id=mid_b,
        )
        await qe.insert_knowledge_item(
            sa,
            "h1",
            content_excerpt="unique alpha zebra mission a",
            payload={"title": "T1", "link": "https://a.example/p1"},
        )
        await qe.insert_knowledge_item(
            sb,
            "h2",
            content_excerpt="unique beta zebra mission b",
            payload={"title": "T2", "link": "https://b.example/p2"},
        )
        qa = await qe.search_knowledge_items(
            "zebra",
            limit=10,
            prefer_fts=True,
            search_mode="lexical",
            mission_scope=mid_a,
        )
        qb = await qe.search_knowledge_items(
            "zebra",
            limit=10,
            prefer_fts=False,
            search_mode="lexical",
            mission_scope=mid_b,
        )
        assert len(qa) == 1 and "alpha" in qa[0]["content_excerpt"]
        assert len(qb) == 1 and "beta" in qb[0]["content_excerpt"]
        la = await qe.list_knowledge_items(limit=10, mission_scope=mid_a)
        lb = await qe.list_knowledge_items(limit=10, mission_scope=mid_b)
        assert len(la) == 1 and la[0]["source_id"] == sa
        assert len(lb) == 1 and lb[0]["source_id"] == sb
        ra = await qe.list_recent_knowledge_item_ids(limit=5, mission_scope=mid_a)
        rb = await qe.list_recent_knowledge_item_ids(limit=5, mission_scope=mid_b)
        assert set(ra) == {la[0]["id"]}
        assert set(rb) == {lb[0]["id"]}
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_link_dedupe_respects_mission_pool(tmp_path, schema_sql_path):
    db = tmp_path / "d.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        mid_a = int(
            await qe.create_mission(
                slug="ma",
                title="Ma",
                niche=None,
                topic=None,
                brief_md="",
            )
        )
        mid_b = int(
            await qe.create_mission(
                slug="mb",
                title="Mb",
                niche=None,
                topic=None,
                brief_md="",
            )
        )
        share_link = "https://shared.example/news/1"
        sa = await qe.insert_knowledge_source(
            "rss", label="a", base_url="https://a.example/f", mission_id=mid_a
        )
        sb = await qe.insert_knowledge_source(
            "rss", label="b", base_url="https://b.example/f", mission_id=mid_b
        )
        p = {"title": "x", "link": share_link}
        r1 = await qe.insert_knowledge_item(sa, "x1", content_excerpt="c1", payload=p)
        assert r1.inserted is True
        r2 = await qe.insert_knowledge_item(sb, "x2", content_excerpt="c2", payload=p)
        assert r2.inserted is True
        assert r1.id != r2.id
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_entity_upsert_mission_scoped_uniqueness(tmp_path, schema_sql_path):
    db = tmp_path / "e.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        mid_a = int(
            await qe.create_mission(
                slug="em-a",
                title="Ea",
                niche=None,
                topic=None,
                brief_md="",
            )
        )
        mid_b = int(
            await qe.create_mission(
                slug="em-b",
                title="Eb",
                niche=None,
                topic=None,
                brief_md="",
            )
        )
        r_a1 = await qe.upsert_entity(type="organization", name="Acme", mission_id=mid_a)
        r_a2 = await qe.upsert_entity(type="organization", name="Acme", mission_id=mid_a)
        assert r_a2["entity_id"] == r_a1["entity_id"] and r_a2["inserted"] is False
        r_b = await qe.upsert_entity(type="organization", name="Acme", mission_id=mid_b)
        assert r_b["inserted"] is True
        assert r_b["entity_id"] != r_a1["entity_id"]
        ent_a = await qe.get_entity_by_id(r_a1["entity_id"])
        ent_b = await qe.get_entity_by_id(r_b["entity_id"])
        assert ent_a is not None and ent_a["mission_id"] == mid_a
        assert ent_b is not None and ent_b["mission_id"] == mid_b
    finally:
        await qe.close()
