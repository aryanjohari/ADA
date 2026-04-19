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
            ):
                cur = await raw.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (name,),
                )
                assert await cur.fetchone() is not None
            cur = await raw.execute("PRAGMA table_info(knowledge_items)")
            cols = {str(r[1]) for r in await cur.fetchall()}
            assert "tags_json" in cols and "content_hash" in cols
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
