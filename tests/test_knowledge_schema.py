from __future__ import annotations

from pathlib import Path

import aiosqlite
import pytest

from ada.query_engine import TASK_KIND_CHAT, QueryEngine


@pytest.mark.asyncio
async def test_fresh_db_has_knowledge_tables(tmp_path, schema_sql_path):
    db = tmp_path / "k.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        async with aiosqlite.connect(db) as raw:
            await raw.execute("PRAGMA foreign_keys = ON")
            cur = await raw.execute("PRAGMA foreign_keys")
            row = await cur.fetchone()
            assert row is not None and int(row[0]) == 1
            for name in (
                "knowledge_sources",
                "knowledge_items",
                "knowledge_synthesis",
                "market_metrics",
                "synthesis_edges",
            ):
                cur = await raw.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (name,),
                )
                assert await cur.fetchone() is not None
            cur = await raw.execute("PRAGMA table_info(knowledge_items)")
            cols = {str(r[1]) for r in await cur.fetchall()}
            assert "tags_json" in cols and "content_hash" in cols
            assert "relevance_score" in cols
            assert "impact_score" in cols
            assert "expires_at" in cols
            assert "tombstoned" in cols
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_knowledge_crud_roundtrip(tmp_path, schema_sql_path):
    db = tmp_path / "k.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        sid = await qe.insert_knowledge_source(
            "rss", label="NZ news", base_url="https://example.com/feed"
        )
        ins = await qe.insert_knowledge_item(
            sid,
            "sha256:abc",
            tags=["nz", "housing"],
            content_excerpt="Summary line",
            payload={"price": 100},
            external_id="entry-1",
            published_at="2026-01-01T00:00:00Z",
        )
        assert ins.inserted is True
        iid = ins.id
        tid = await qe.insert_task("g", status="executing", task_kind=TASK_KIND_CHAT)
        syn_id = await qe.insert_knowledge_synthesis(
            "Market looks tight.", [iid], task_id=tid
        )
        assert syn_id > 0
        item = await qe.get_knowledge_item(iid)
        assert item["tags"] == ["nz", "housing"]
        assert item["payload"] == {"price": 100}
        assert item["external_id"] == "entry-1"
        assert item["relevance_score"] is None
        assert item["impact_score"] is None
        assert item["tombstoned"] == 0
        listed = await qe.list_knowledge_items(source_id=sid, limit=10)
        assert len(listed) == 1 and listed[0]["id"] == iid
        syns = await qe.list_knowledge_synthesis_for_task(tid)
        assert len(syns) == 1
        assert syns[0]["ref_item_ids"] == [iid]
        assert "tight" in syns[0]["body"]
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_knowledge_items_dedupe_external_id(tmp_path, schema_sql_path):
    db = tmp_path / "k.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        sid = await qe.insert_knowledge_source("web")
        a = await qe.insert_knowledge_item(
            sid, "h1", tags=None, external_id="same", content_excerpt="a"
        )
        b = await qe.insert_knowledge_item(
            sid, "h2", tags=None, external_id="same", content_excerpt="b"
        )
        assert a.inserted and not b.inserted
        assert a.id == b.id
        row = await qe.get_knowledge_item(a.id)
        assert row["content_excerpt"] == "a"
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_knowledge_items_dedupe_payload_link_across_sources(
    tmp_path, schema_sql_path
):
    db = tmp_path / "k.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        s1 = await qe.insert_knowledge_source("rss", label="A", base_url="https://a.test/f")
        s2 = await qe.insert_knowledge_source("rss", label="B", base_url="https://b.test/f")
        link = "https://news.example.nz/story/one"
        a = await qe.insert_knowledge_item(
            s1,
            "hash-one",
            content_excerpt="first",
            payload={"title": "T", "link": link},
        )
        b = await qe.insert_knowledge_item(
            s2,
            "hash-two",
            content_excerpt="second",
            payload={"title": "T2", "link": link},
        )
        assert a.inserted and not b.inserted
        assert a.id == b.id
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_knowledge_items_cascade_on_source_delete(tmp_path, schema_sql_path):
    db = tmp_path / "k.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        sid = await qe.insert_knowledge_source("api")
        iid = (await qe.insert_knowledge_item(sid, "hx", content_excerpt="x")).id
        await qe.delete_knowledge_source(sid)
        with pytest.raises(LookupError):
            await qe.get_knowledge_item(iid)
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_knowledge_synthesis_task_id_set_null_on_task_delete(
    tmp_path, schema_sql_path
):
    db = tmp_path / "k.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        sid = await qe.insert_knowledge_source("rss")
        iid = (await qe.insert_knowledge_item(sid, "hz", content_excerpt="z")).id
        tid = await qe.insert_task("t", status="completed", task_kind=TASK_KIND_CHAT)
        syn_id = await qe.insert_knowledge_synthesis("note", [iid], task_id=tid)
    finally:
        await qe.close()

    async with aiosqlite.connect(db) as raw:
        await raw.execute("PRAGMA foreign_keys = ON")
        await raw.execute("DELETE FROM tasks WHERE id = ?", (tid,))
        await raw.commit()

    async with aiosqlite.connect(db) as raw:
        cur = await raw.execute(
            "SELECT task_id FROM knowledge_synthesis WHERE id = ?",
            (syn_id,),
        )
        row = await cur.fetchone()
        assert row is not None and row[0] is None


@pytest.mark.asyncio
async def test_migration_adds_business_kernel_schema(tmp_path, schema_sql_path):
    before = (
        Path(__file__).resolve().parent
        / "fixtures"
        / "schema_before_business_kernel.sql"
    )
    db = tmp_path / "pre_kernel.db"
    async with aiosqlite.connect(db) as raw:
        await raw.execute("PRAGMA foreign_keys = ON")
        await raw.executescript(before.read_text(encoding="utf-8"))
        await raw.commit()
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        async with aiosqlite.connect(db) as raw:
            cur = await raw.execute("PRAGMA table_info(knowledge_items)")
            cols = {str(r[1]) for r in await cur.fetchall()}
            assert "impact_score" in cols
            for name in ("market_metrics", "synthesis_edges"):
                cur = await raw.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (name,),
                )
                assert await cur.fetchone() is not None
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_impact_score_check_constraint(tmp_path, schema_sql_path):
    db = tmp_path / "k.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        sid = await qe.insert_knowledge_source("web")
        iid = (await qe.insert_knowledge_item(sid, "hc", content_excerpt="c")).id
        async with aiosqlite.connect(db) as raw:
            await raw.execute("PRAGMA foreign_keys = ON")
            with pytest.raises(Exception):
                await raw.execute(
                    "UPDATE knowledge_items SET impact_score = ? WHERE id = ?",
                    (11, iid),
                )
                await raw.commit()
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_update_impact_score_validates_range(tmp_path, schema_sql_path):
    db = tmp_path / "k.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        sid = await qe.insert_knowledge_source("rss")
        iid = (await qe.insert_knowledge_item(sid, "hv", content_excerpt="v")).id
        with pytest.raises(ValueError):
            await qe.update_impact_score(iid, 0)
        with pytest.raises(ValueError):
            await qe.update_impact_score(iid, 11)
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_business_kernel_metrics_edges_roundtrip_and_cascade(
    tmp_path, schema_sql_path
):
    db = tmp_path / "k.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        sid = await qe.insert_knowledge_source("api")
        iid = (await qe.insert_knowledge_item(sid, "hk", content_excerpt="k")).id
        unscored = await qe.list_unscored_knowledge(limit=20)
        assert any(x["id"] == iid for x in unscored)
        mid = await qe.insert_market_metric("cpi", 3.14, api_source="nz")
        assert mid > 0
        eid = await qe.insert_synthesis_edge(iid, mid, causality_notes="link")
        assert eid > 0
        await qe.update_impact_score(iid, 5)
        assert not any(
            x["id"] == iid for x in await qe.list_unscored_knowledge(limit=20)
        )
        assert (await qe.get_knowledge_item(iid))["impact_score"] == 5
        async with aiosqlite.connect(db) as raw:
            await raw.execute("PRAGMA foreign_keys = ON")
            await raw.execute("DELETE FROM knowledge_items WHERE id = ?", (iid,))
            await raw.commit()
        async with aiosqlite.connect(db) as raw:
            cur = await raw.execute(
                "SELECT COUNT(*) FROM synthesis_edges WHERE id = ?", (eid,)
            )
            row = await cur.fetchone()
            assert row is not None and int(row[0]) == 0
        iid2 = (await qe.insert_knowledge_item(sid, "hk2", content_excerpt="k2")).id
        eid2 = await qe.insert_synthesis_edge(iid2, mid, causality_notes="e2")
        async with aiosqlite.connect(db) as raw:
            await raw.execute("PRAGMA foreign_keys = ON")
            await raw.execute("DELETE FROM market_metrics WHERE id = ?", (mid,))
            await raw.commit()
        async with aiosqlite.connect(db) as raw:
            cur = await raw.execute(
                "SELECT COUNT(*) FROM synthesis_edges WHERE id = ?", (eid2,)
            )
            row = await cur.fetchone()
            assert row is not None and int(row[0]) == 0
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_migration_adds_knowledge_tables(tmp_path):
    legacy = (
        Path(__file__).resolve().parent
        / "fixtures"
        / "schema_legacy_before_knowledge.sql"
    )
    db = tmp_path / "legacy.db"
    qe = QueryEngine(db, legacy, debounce_ms=5)
    await qe.connect()
    try:
        async with aiosqlite.connect(db) as raw:
            for name in (
                "knowledge_sources",
                "knowledge_items",
                "knowledge_synthesis",
            ):
                cur = await raw.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (name,),
                )
                assert await cur.fetchone() is not None
    finally:
        await qe.close()
