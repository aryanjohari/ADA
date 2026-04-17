from __future__ import annotations

import pytest

from ada.goal_cli import async_main
from ada.query_engine import TASK_KIND_CHAT, TASK_KIND_GOAL, QueryEngine


@pytest.mark.asyncio
async def test_fetch_pending_skips_pending_chat_tasks(tmp_path, schema_sql_path):
    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        await qe.insert_task(
            "Interactive session",
            status="pending",
            task_kind=TASK_KIND_CHAT,
        )
        gid = await qe.insert_task(
            "background work", status="pending", task_kind=TASK_KIND_GOAL
        )
        p = await qe.fetch_pending_task()
        assert p is not None
        assert p[0] == gid
        assert p[1] == "background work"
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_get_goal_task_rejects_chat_task(tmp_path, schema_sql_path):
    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path)
    await qe.connect()
    try:
        cid = await qe.insert_task(
            "Interactive session", status="executing", task_kind=TASK_KIND_CHAT
        )
        with pytest.raises(ValueError, match="not a goal task"):
            await qe.get_goal_task(cid)
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_goal_cli_add_list_show(tmp_path, schema_sql_path, monkeypatch):
    monkeypatch.setenv("ADA_DATA_DIR", str(tmp_path))
    assert await async_main(["add", "hello", "world"]) == 0
    db_file = tmp_path / "state.db"
    assert db_file.is_file()

    qe = QueryEngine(db_file, schema_sql_path)
    await qe.connect()
    try:
        rows = await qe.list_goal_tasks(limit=10)
        assert len(rows) >= 1
        assert any(r["goal"] == "hello world" for r in rows)
        tid = next(r["id"] for r in rows if r["goal"] == "hello world")
        assert await async_main(["show", str(tid)]) == 0
        assert await async_main(["list", "--limit", "5"]) == 0
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_goal_cli_add_with_plan_json(tmp_path, schema_sql_path, monkeypatch):
    monkeypatch.setenv("ADA_DATA_DIR", str(tmp_path))
    rc = await async_main(
        ["add", "x", "--plan-json", '{"version":1,"steps":[]}']
    )
    assert rc == 0
    qe = QueryEngine(tmp_path / "state.db", schema_sql_path)
    await qe.connect()
    try:
        rows = await qe.list_goal_tasks(limit=1)
        assert rows[0]["plan_json"] == '{"version":1,"steps":[]}'
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_goal_cli_add_invalid_json(tmp_path, monkeypatch):
    monkeypatch.setenv("ADA_DATA_DIR", str(tmp_path))
    rc = await async_main(["add", "bad", "--plan-json", "not-json"])
    assert rc == 2
