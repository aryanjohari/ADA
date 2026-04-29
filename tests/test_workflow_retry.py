"""Resume-safe workflow.retry_failed_workflow store + QueryEngine."""

from __future__ import annotations

import json

import aiosqlite
import pytest

from ada.query_engine import TASK_KIND_GOAL, QueryEngine
from ada.workflow.templates import expand_workflow_template


@pytest.mark.asyncio
async def test_retry_failed_workflow_resets_tail(tmp_path, schema_sql_path):
    db = tmp_path / "w.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=2)
    await qe.connect()
    try:
        tid = await qe.insert_task("goal x", status="failed", task_kind=TASK_KIND_GOAL)
        steps_tpl = expand_workflow_template(
            "rss_fetch_then_graph_then_synth",
            {"topic": "T"},
            max_steps=10,
        )
        wf_id, created = await qe.enqueue_workflow(
            kind="rss_fetch_then_graph_then_synth",
            goal_text="goal x",
            params_json={"topic": "T"},
            parent_task_id=tid,
            idempotency_key="retry-fixture-1",
            steps=steps_tpl,
        )
        assert created is True

        listed = await qe.list_workflow_steps(wf_id)
        assert len(listed) == 3
        s0_id, s1_id = int(listed[0]["id"]), int(listed[1]["id"])

        await qe.update_workflow_row(wf_id, status="failed")
        await qe.update_workflow_step_row(
            s0_id,
            status="completed",
            output_json={"feeds_attempted": 1},
            error="",
        )
        await qe.update_workflow_step_row(s1_id, status="failed", error="step failed")

        out = await qe.retry_failed_workflow(
            wf_id,
            reason="pytest",
            dry_run=False,
        )
        assert out.get("error") is None
        assert out.get("ok") is True

        wf = await qe.get_workflow_by_id(wf_id)
        assert wf is not None
        assert str(wf["status"]).lower() == "pending"

        task = await qe.get_goal_task(tid)
        assert task["status"] == "pending"
        assert task["current_output"] == ""

        listed_after = await qe.list_workflow_steps(wf_id)
        assert str(listed_after[0]["status"]).lower() == "completed"
        assert (listed_after[0].get("output_json") or {}).get("feeds_attempted") == 1
        assert str(listed_after[1]["status"]).lower() == "pending"
        assert listed_after[1].get("error") == ""
        assert str(listed_after[2]["status"]).lower() == "pending"

        async with aiosqlite.connect(db) as conn:
            cur = await conn.execute(
                """
                SELECT kind, payload_json FROM action_log
                WHERE kind = ?
                ORDER BY id DESC LIMIT 1
                """,
                ("workflow_retry_requested",),
            )
            row = await cur.fetchone()
        assert row is not None
        assert row[0] == "workflow_retry_requested"
        pl = json.loads(row[1])
        assert pl["workflow_id"] == wf_id
        assert pl["reason"] == "pytest"
        assert pl.get("dry_run") is False
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_retry_failed_workflow_dry_run_no_write(tmp_path, schema_sql_path):
    db = tmp_path / "w2.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=2)
    await qe.connect()
    try:
        tid = await qe.insert_task("g", status="failed", task_kind=TASK_KIND_GOAL)
        steps_tpl = expand_workflow_template(
            "rss_fetch_then_graph_then_synth",
            {"topic": "T"},
            max_steps=10,
        )
        wf_id, _ = await qe.enqueue_workflow(
            kind="rss_fetch_then_graph_then_synth",
            goal_text="g",
            params_json={"topic": "T"},
            parent_task_id=tid,
            idempotency_key="retry-dry-run",
            steps=steps_tpl,
        )
        await qe.update_workflow_row(wf_id, status="failed")
        listed = await qe.list_workflow_steps(wf_id)
        await qe.update_workflow_step_row(
            int(listed[0]["id"]),
            status="completed",
            output_json={"x": 1},
            error="",
        )
        await qe.update_workflow_step_row(
            int(listed[1]["id"]),
            status="failed",
            error="e",
        )

        wf_before = await qe.get_workflow_by_id(wf_id)
        task_before = await qe.get_goal_task(tid)
        steps_before = await qe.list_workflow_steps(wf_id)

        dry = await qe.retry_failed_workflow(wf_id, reason="dry", dry_run=True)
        assert dry.get("error") is None
        assert dry.get("dry_run") is True
        assert "plan" in dry

        wf_after = await qe.get_workflow_by_id(wf_id)
        task_after = await qe.get_goal_task(tid)
        steps_after = await qe.list_workflow_steps(wf_id)

        assert wf_after == wf_before
        assert task_after == task_before
        for a, b in zip(steps_after, steps_before, strict=True):
            assert a["status"] == b["status"] and a["error"] == b["error"]
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_retry_requires_failed_status(tmp_path, schema_sql_path):
    db = tmp_path / "w3.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=2)
    await qe.connect()
    try:
        tid = await qe.insert_task("g", status="pending", task_kind=TASK_KIND_GOAL)
        steps_tpl = expand_workflow_template(
            "rss_fetch_then_graph_then_synth",
            {"topic": "T"},
            max_steps=10,
        )
        wf_id, _ = await qe.enqueue_workflow(
            kind="rss_fetch_then_graph_then_synth",
            goal_text="g",
            params_json={"topic": "T"},
            parent_task_id=tid,
            idempotency_key="retry-notfailed",
            steps=steps_tpl,
        )

        bad = await qe.retry_failed_workflow(wf_id, dry_run=True)
        assert "error" in bad
        assert "failed" in bad["error"].lower()
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_retry_all_steps_completed_rejected(tmp_path, schema_sql_path):
    db = tmp_path / "w4.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=2)
    await qe.connect()
    try:
        tid = await qe.insert_task("g", status="failed", task_kind=TASK_KIND_GOAL)
        steps_tpl = expand_workflow_template(
            "rss_fetch_then_graph_then_synth",
            {"topic": "T"},
            max_steps=10,
        )
        wf_id, _ = await qe.enqueue_workflow(
            kind="rss_fetch_then_graph_then_synth",
            goal_text="g",
            params_json={"topic": "T"},
            parent_task_id=tid,
            idempotency_key="retry-all-done",
            steps=steps_tpl,
        )
        await qe.update_workflow_row(wf_id, status="failed")
        for st in await qe.list_workflow_steps(wf_id):
            await qe.update_workflow_step_row(
                int(st["id"]), status="completed", output_json={"done": True}, error=""
            )

        bad = await qe.retry_failed_workflow(wf_id)
        assert bad.get("error")
        assert "all steps completed" in bad["error"].lower()
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_retry_rejects_missing_parent_task(tmp_path, schema_sql_path):
    db = tmp_path / "w-no-parent.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=2)
    await qe.connect()
    try:
        store = qe._store
        cur = await store._conn.execute(  # noqa: SLF001
            """
            INSERT INTO workflows (kind, goal_text, params_json, idempotency_key, status, parent_task_id)
            VALUES (?, ?, '{}', NULL, 'failed', NULL)
            """,
            ("rss_fetch_then_graph_then_synth", "orphan"),
        )
        await store._conn.commit()  # noqa: SLF001
        wf_id = int(cur.lastrowid)
        bad = await qe.retry_failed_workflow(wf_id)
        assert bad.get("error")
        assert "parent_task_id" in bad["error"].lower()
    finally:
        await qe.close()
