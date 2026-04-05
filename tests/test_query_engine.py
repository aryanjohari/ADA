from __future__ import annotations

import pytest

from ada.query_engine import QueryEngine, ROLE_ASSISTANT, ROLE_USER


@pytest.mark.asyncio
async def test_user_assistant_chain_parent_and_api_load(
    tmp_path, schema_sql_path
):
    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        tid = await qe.insert_task("daemon goal", status="pending")
        u1 = await qe.persist_user(tid, "hi")
        head = await qe.chain_head_uuid(tid)
        assert head == u1
        a1 = await qe.persist_assistant_begin(tid, u1)
        await qe.persist_assistant_finalize(a1, "hello", {"model": "x"})
        chain = await qe.load_chain_for_api(tid)
        assert len(chain) == 2
        assert chain[0]["role"] == ROLE_USER
        assert chain[0]["parts"][0]["text"] == "hi"
        assert chain[1]["role"] == ROLE_ASSISTANT
        assert chain[1]["parts"][0]["text"] == "hello"
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_api_load_excludes_tombstone(tmp_path, schema_sql_path):
    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        tid = await qe.insert_task("t", status="pending")
        await qe.persist_user(tid, "u")
        a = await qe.persist_assistant_begin(tid, await qe.chain_head_uuid(tid))
        await qe.tombstone([a], tid)
        chain = await qe.load_chain_for_api(tid)
        assert len(chain) == 1
        assert chain[0]["role"] == ROLE_USER
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_state_kv(tmp_path, schema_sql_path):
    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path)
    await qe.connect()
    try:
        await qe.state_set("k", "v")
        assert await qe.state_get("k") == "v"
    finally:
        await qe.close()
