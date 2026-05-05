"""Workflow enqueue mission tagging (session + slug resolution)."""

from __future__ import annotations

import pytest

from ada.query_engine import TASK_KIND_GOAL, QueryEngine
from ada.workflow.enqueue import enqueue_workflow_via_tool


@pytest.mark.asyncio
async def test_enqueue_inherits_source_task_mission(
    tmp_path, schema_sql_path
) -> None:
    db = tmp_path / "enqueue_m.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=2)
    await qe.connect()
    try:
        mid = await qe.create_mission("inherit-me", "T", defaults_json={})
        sid = await qe.insert_task(
            "parent goal",
            status="executing",
            task_kind=TASK_KIND_GOAL,
            mission_id=mid,
        )
        out = await enqueue_workflow_via_tool(
            qe,
            kind="rss_fetch_then_graph_then_synth",
            goal_text="child workflow goal",
            params_json='{"topic":"x"}',
            idempotency_key=None,
            max_steps=10,
            source_task_id=sid,
        )
        assert out.get("error") is None
        wf = await qe.get_workflow_by_id(int(out["workflow_id"]))
        assert wf is not None
        assert wf["mission_id"] == mid
        ctid = int(out["task_id"])
        t = await qe.get_goal_task(ctid)
        assert t["mission_id"] == mid
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_mission_slug_overrides_source_task_for_tag(
    tmp_path, schema_sql_path
) -> None:
    db = tmp_path / "enqueue_slug.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=2)
    await qe.connect()
    try:
        mid_a = await qe.create_mission("mission-a", "A", defaults_json={})
        mid_b = await qe.create_mission("mission-b", "B", defaults_json={})
        sid = await qe.insert_task(
            "parent",
            status="executing",
            task_kind=TASK_KIND_GOAL,
            mission_id=mid_a,
        )
        out = await enqueue_workflow_via_tool(
            qe,
            kind="rss_fetch_then_graph_then_synth",
            goal_text="tagged b",
            params_json='{"topic":"y"}',
            idempotency_key="slug-wins-1",
            max_steps=10,
            mission_slug="mission-b",
            source_task_id=sid,
        )
        assert out.get("error") is None
        wf = await qe.get_workflow_by_id(int(out["workflow_id"]))
        assert wf["mission_id"] == mid_b
    finally:
        await qe.close()
