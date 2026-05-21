"""Unit tests for mission_control deterministic flags (fixture DB, fake secrets)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ada.mission_control.flags import collect_flags
from ada.mission_control.snapshot import build_mission_control_snapshot
from ada.observability.queries import open_readonly_connection
from ada.persistent.store import TASK_KIND_CHAT, TASK_KIND_GOAL
from ada.query_engine import QueryEngine


def _conn(db: Path):
    return open_readonly_connection(db)


@pytest.mark.asyncio
async def test_system_jobs_dead_flag(tmp_path, schema_sql_path) -> None:
    db = tmp_path / "flags_dead.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        jid = await qe.insert_system_job(
            kind="noop.ping",
            payload_json={"fake_token": "not-a-real-key"},
            idempotency_key="flag-dead-1",
        )
        store = qe._store
        await store._conn.execute(  # noqa: SLF001
            "UPDATE system_jobs SET status='dead', error='test_dead' WHERE id=?",
            (jid,),
        )
        await store._conn.commit()  # noqa: SLF001
    finally:
        await qe.close()
    with _conn(db) as conn:
        flags = collect_flags(conn, profile_scope=True)
    dead = [f for f in flags if f.id == "system_jobs_dead"]
    assert len(dead) == 1
    assert dead[0].source_table == "system_jobs"
    assert dead[0].source_id == str(jid)


@pytest.mark.asyncio
async def test_chat_task_missing_mission_flag(tmp_path, schema_sql_path) -> None:
    db = tmp_path / "flags_chat.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        await qe.insert_task(
            "Interactive session",
            status="executing",
            task_kind=TASK_KIND_CHAT,
            mission_id=None,
        )
    finally:
        await qe.close()
    with _conn(db) as conn:
        flags = collect_flags(conn, profile_scope=True)
    chat_flags = [f for f in flags if f.id == "chat_task_missing_mission"]
    assert len(chat_flags) == 1
    assert chat_flags[0].severity == "warn"


@pytest.mark.asyncio
async def test_mission_tick_never_ran_flag(tmp_path, schema_sql_path) -> None:
    db = tmp_path / "flags_tick.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        sched = json.dumps(
            {
                "version": 1,
                "jobs": [
                    {
                        "id": "daily_gsc",
                        "min_interval_hours": 24,
                        "action": {"type": "gsc_keyword_publish"},
                    }
                ],
            }
        )
        mid = await qe.create_mission(
            slug="pub",
            title="Pub",
            schedule_hint_json=json.loads(sched),
        )
    finally:
        await qe.close()
    with _conn(db) as conn:
        flags = collect_flags(
            conn,
            mission_id=mid,
            mission_slug="pub",
            profile_scope=False,
        )
    never = [f for f in flags if f.id == "mission_tick_never_ran"]
    assert len(never) >= 1
    assert never[0].mission_id == mid


@pytest.mark.asyncio
async def test_mission_tick_overdue_flag(tmp_path, schema_sql_path) -> None:
    db = tmp_path / "flags_overdue.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        sched = json.dumps(
            {
                "version": 1,
                "jobs": [{"id": "j1", "min_interval_hours": 9999, "action": {"type": "x"}}],
            }
        )
        mid = await qe.create_mission(
            slug="o",
            title="O",
            schedule_hint_json=json.loads(sched),
        )
        await qe.state_set("mission.tick.o.j1", "2020-01-01T00:00:00Z")
    finally:
        await qe.close()
    with _conn(db) as conn:
        flags = collect_flags(
            conn,
            mission_id=mid,
            mission_slug="o",
            profile_scope=False,
        )
    overdue = [f for f in flags if f.id == "mission_tick_job_overdue"]
    assert len(overdue) >= 1


@pytest.mark.asyncio
async def test_mission_pending_goals_info_flag(tmp_path, schema_sql_path) -> None:
    db = tmp_path / "flags_goals.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        mid = await qe.create_mission(slug="g", title="G")
        await qe.insert_task(
            "goal one",
            status="pending",
            task_kind=TASK_KIND_GOAL,
            mission_id=mid,
        )
    finally:
        await qe.close()
    with _conn(db) as conn:
        flags = collect_flags(
            conn,
            mission_id=mid,
            mission_slug="g",
            profile_scope=False,
        )
    pg = [f for f in flags if f.id == "mission_pending_goals"]
    assert len(pg) == 1
    assert pg[0].severity == "info"


@pytest.mark.asyncio
async def test_workflow_step_failed_flag(tmp_path, schema_sql_path) -> None:
    db = tmp_path / "wf_fail.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        mid = await qe.create_mission(slug="w", title="W")
        tid = await qe.insert_task(
            "g", status="pending", task_kind=TASK_KIND_GOAL, mission_id=mid
        )
        store = qe._store
        await store._conn.execute(  # noqa: SLF001
            """
            INSERT INTO workflows (kind, goal_text, status, parent_task_id, mission_id)
            VALUES ('publish_entity_v1', 'g', 'running', ?, ?)
            """,
            (tid, mid),
        )
        cur = await store._conn.execute("SELECT last_insert_rowid()")  # noqa: SLF001
        wf_row = await cur.fetchone()
        wf_id = int(wf_row[0])
        await store._conn.execute(  # noqa: SLF001
            """
            INSERT INTO workflow_steps (workflow_id, step_index, step_type, status, error)
            VALUES (?, 0, 'GATE', 'failed', 'GATE: test')
            """,
            (wf_id,),
        )
        await store._conn.commit()  # noqa: SLF001
    finally:
        await qe.close()
    with _conn(db) as conn:
        flags = collect_flags(conn, mission_id=mid, profile_scope=False)
    failed = [f for f in flags if f.id == "workflow_step_failed"]
    assert len(failed) >= 1


@pytest.mark.asyncio
async def test_snapshot_schema_version(tmp_path, schema_sql_path) -> None:
    db = tmp_path / "snap.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        mid = await qe.create_mission(slug="s", title="S")
    finally:
        await qe.close()
    with _conn(db) as conn:
        snap = build_mission_control_snapshot(
            conn,
            mission_id=mid,
            mission_slug="s",
            profile_scope=False,
        )
    assert snap["schema_version"] == 1
    assert snap["mission_id"] == mid
    assert "flags" in snap
