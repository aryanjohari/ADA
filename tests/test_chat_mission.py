"""ada chat --mission binds task.mission_id for knowledge scope."""

from __future__ import annotations

import pytest

from ada.query_engine import TASK_KIND_CHAT, QueryEngine


@pytest.mark.asyncio
async def test_insert_chat_task_with_mission_id(tmp_path, schema_sql_path) -> None:
    db = tmp_path / "chat_mission.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        mid = await qe.create_mission(slug="ops", title="Ops")
        tid = await qe.insert_task(
            "Interactive session",
            status="executing",
            task_kind=TASK_KIND_CHAT,
            mission_id=mid,
        )
        got = await qe.get_task_mission_id(tid)
        assert got == mid
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_attach_task_to_mission(tmp_path, schema_sql_path) -> None:
    db = tmp_path / "attach_mission.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        mid = await qe.create_mission(slug="b", title="B")
        tid = await qe.insert_task(
            "Interactive session",
            status="executing",
            task_kind=TASK_KIND_CHAT,
        )
        assert await qe.get_task_mission_id(tid) is None
        await qe.attach_task_to_mission(tid, mid)
        assert await qe.get_task_mission_id(tid) == mid
    finally:
        await qe.close()
