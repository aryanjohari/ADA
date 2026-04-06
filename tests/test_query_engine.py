from __future__ import annotations

import aiosqlite
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


@pytest.mark.asyncio
async def test_persist_assistant_with_function_calls(tmp_path, schema_sql_path):
    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        tid = await qe.insert_task("t", status="pending")
        u = await qe.persist_user(tid, "hi")
        mid = await qe.persist_assistant_begin(tid, u)
        await qe.persist_assistant_finalize(
            mid,
            "thinking",
            {"model": "x"},
            function_calls=[
                {"name": "run_allowlisted_shell", "args": {"command": "uname -a"}, "id": "1"}
            ],
        )
        chain = await qe.load_chain_for_api(tid)
        parts = chain[-1]["parts"]
        types_ = [p["type"] for p in parts]
        assert "text" in types_
        assert "function_call" in types_
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_record_usage_ledger(tmp_path, schema_sql_path):
    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path)
    await qe.connect()
    try:
        tid = await qe.insert_task("t", status="pending")
        await qe.record_usage(tid, model="m", input_tokens=10, output_tokens=3)
        async with aiosqlite.connect(db) as raw:
            cur = await raw.execute(
                "SELECT count(*) FROM usage_ledger WHERE session_id = ?", (tid,)
            )
            row = await cur.fetchone()
        assert row[0] == 1
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_get_session_token_usage_sums_ledger(tmp_path, schema_sql_path):
    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path)
    await qe.connect()
    try:
        tid = await qe.insert_task("t", status="pending")
        await qe.record_usage(tid, model="m1", input_tokens=10, output_tokens=3)
        await qe.record_usage(tid, model="m2", input_tokens=7, output_tokens=None)
        await qe.record_usage(tid, model="m3", input_tokens=None, output_tokens=5)
        u = await qe.get_session_token_usage(tid)
        assert u["input_tokens"] == 17
        assert u["output_tokens"] == 8
        assert u["total"] == 25
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_tombstone_rewires_live_children(tmp_path, schema_sql_path):
    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        tid = await qe.insert_task("t", status="pending")
        u = await qe.persist_user(tid, "hi")
        a = await qe.persist_assistant_begin(tid, u)
        tid_tool = await qe.persist_tool_result(
            tid,
            parent_assistant_uuid=a,
            name="run_allowlisted_shell",
            tool_call_id="x",
            response={"stdout": "ok"},
        )
        await qe.tombstone([a], tid, rewire_orphans=True)
        async with aiosqlite.connect(db) as raw:
            cur = await raw.execute(
                "SELECT parent_uuid FROM messages WHERE uuid = ?", (tid_tool,)
            )
            row = await cur.fetchone()
        assert row is not None
        assert row[0] == u
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_append_action_log(tmp_path, schema_sql_path):
    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path)
    await qe.connect()
    try:
        tid = await qe.insert_task("t", status="pending")
        rid = await qe.append_action_log(
            "test_kind", {"a": 1}, session_id=tid
        )
        assert rid >= 1
        async with aiosqlite.connect(db) as raw:
            cur = await raw.execute(
                "SELECT kind, payload_json FROM action_log WHERE id = ?", (rid,)
            )
            row = await cur.fetchone()
        assert row[0] == "test_kind"
        assert '"a": 1' in row[1]
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_task_plan_json_roundtrip(tmp_path, schema_sql_path):
    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path)
    await qe.connect()
    try:
        tid = await qe.insert_task("t", status="pending")
        assert await qe.get_task_plan_json(tid) == "{}"
        await qe.set_task_plan_json(tid, '{"steps":["a"]}')
        assert await qe.get_task_plan_json(tid) == '{"steps":["a"]}'
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_set_task_plan_json_invalid_json_raises(tmp_path, schema_sql_path):
    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path)
    await qe.connect()
    try:
        tid = await qe.insert_task("t", status="pending")
        with pytest.raises(ValueError, match="valid JSON"):
            await qe.set_task_plan_json(tid, "not json")
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_task_plan_json_missing_task_raises(tmp_path, schema_sql_path):
    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path)
    await qe.connect()
    try:
        await qe.insert_task("t", status="pending")
        bad_id = 99999
        with pytest.raises(LookupError):
            await qe.get_task_plan_json(bad_id)
        with pytest.raises(LookupError):
            await qe.set_task_plan_json(bad_id, "{}")
    finally:
        await qe.close()
