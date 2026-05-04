"""Matrix planner enqueue path with mocked Gemini JSON."""

from __future__ import annotations

from unittest import mock

import pytest

from ada.config import Settings
from ada.publish.matrix_planner import run_matrix_plan_and_enqueue
from ada.query_engine import QueryEngine


@pytest.mark.asyncio
async def test_planner_enqueues_with_mock_llm(tmp_path, schema_sql_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key-for-test")
    monkeypatch.delenv("ADA_MATRIX_PLANNER_MODEL", raising=False)

    db = tmp_path / "planner.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=2)
    await qe.connect()
    try:
        await qe.ensure_triage_category_entities()
        cat = await qe.upsert_entity(
            type="category", name="labour_workforce", payload_json={}
        )
        sub = await qe.upsert_entity(type="service", name="Svc", payload_json={})
        await qe.insert_graph_edge(
            src_entity_id=int(sub["entity_id"]),
            dst_entity_id=int(cat["entity_id"]),
            edge_type="classified_as",
            confidence=1.0,
            source_url="https://planner.test/1",
        )
        sid = int(sub["entity_id"])

        async def fake_propose(**kwargs):
            return {"entity_ids": [sid]}, None

        with mock.patch(
            "ada.publish.matrix_planner.propose_entity_ids_via_planner_llm",
            new=fake_propose,
        ):
            n = 0
            from ada.workflow.enqueue import enqueue_workflow_via_tool as real_enqueue

            async def wrap(*a, **k):
                nonlocal n
                n += 1
                return await real_enqueue(*a, **k)

            with mock.patch("ada.publish.matrix.enqueue_workflow_via_tool", new=wrap):
                out = await run_matrix_plan_and_enqueue(
                    qe,
                    Settings.load(),
                    project_id="p1",
                    campaign_id="c1",
                )
        assert out.get("mode") == "matrix_planner"
        assert n >= 1
        assert sid in (out.get("planned_ids") or [])
    finally:
        await qe.close()
