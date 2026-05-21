"""Tests for system_jobs claim semantics and goal enqueue."""

from __future__ import annotations

from pathlib import Path

import pytest

from ada.persistent.store import PersistentState, TASK_KIND_GOAL
from ada.query_engine import QueryEngine


async def _mk_qe(tmp_path: Path) -> QueryEngine:
    schema = Path(__file__).resolve().parents[1] / "src" / "ada" / "db" / "schema.sql"
    db = tmp_path / "state.db"
    q = QueryEngine(db, schema, debounce_ms=1)
    await q.connect()
    await q.create_mission(slug="t1", title="T1")
    return q


@pytest.mark.asyncio
async def test_claim_next_system_job_single_winner(tmp_path: Path) -> None:
    qe = await _mk_qe(tmp_path)
    try:
        jid = await qe.insert_system_job(
            kind="noop.ping",
            payload_json={"x": 1},
            idempotency_key="test-claim-1",
        )
        assert jid >= 1
        j1 = await qe.claim_next_system_job("w-a", lease_seconds=60)
        j2 = await qe.claim_next_system_job("w-b", lease_seconds=60)
        assert j1 is not None and j1["id"] == jid
        assert j2 is None
        ok = await qe.complete_system_job(jid, "w-a")
        assert ok is True
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_try_enqueue_goal_run_turn_idempotent(tmp_path: Path) -> None:
    qe = await _mk_qe(tmp_path)
    try:
        tid = await qe.insert_task(
            "hello", status="pending", task_kind=TASK_KIND_GOAL, mission_id=1
        )
        a = await qe.try_enqueue_goal_run_turn(tid)
        b = await qe.try_enqueue_goal_run_turn(tid)
        assert a is not None
        assert b is None
        row = await qe.get_system_job(a)
        assert row is not None
        assert row["kind"] == "goal.run_turn"
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_reclaim_expired_lease_makes_pending(tmp_path: Path) -> None:
    qe = await _mk_qe(tmp_path)
    try:
        store = qe._store
        assert isinstance(store, PersistentState)
        jid = await qe.insert_system_job(
            kind="noop.ping",
            payload_json={},
            idempotency_key="lease-reclaim-test",
            max_attempts=3,
        )
        await store._conn.execute(  # noqa: SLF001
            """
            UPDATE system_jobs SET status='running', lease_owner='x',
            lease_expires_at=datetime('now', '-1 seconds')
            WHERE id=?
            """,
            (jid,),
        )
        await store._conn.commit()  # noqa: SLF001
        n = await qe.reclaim_expired_system_jobs()
        assert n >= 1
        row = await qe.get_system_job(jid)
        assert row is not None
        assert row["status"] in ("pending", "dead")
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_try_enqueue_ingest_run_dedupes_inflight(tmp_path: Path) -> None:
    qe = await _mk_qe(tmp_path)
    try:
        iid = await qe.create_ingest_job(
            "gsc_search_analytics_v1",
            {
                "site_url": "https://example.test/",
                "start_date": "2026-01-01",
                "end_date": "2026-01-02",
            },
            idempotency_key="test-ingest-enq-1",
        )
        a = await qe.try_enqueue_ingest_run(iid, mission_id=1)
        b = await qe.try_enqueue_ingest_run(iid, mission_id=1)
        assert a is not None
        assert b is None
        row = await qe.get_system_job(a)
        assert row is not None
        assert row["kind"] == "ingest.run"
        assert row["mission_id"] == 1
        assert (row.get("payload_json") or {}).get("ingest_job_id") == iid
    finally:
        await qe.close()
