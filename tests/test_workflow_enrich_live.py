"""ENRICH workflow step: live web path, graph sufficiency, graph-only refine."""

from __future__ import annotations

from unittest import mock

import aiosqlite
import pytest

import ada.orchestrator as orch
from ada.config import Settings
from ada.query_engine import TASK_KIND_CHAT, TASK_KIND_GOAL, QueryEngine
from ada.stream_types import CompletedFunctionCall, StreamLegResult
from ada.workflow.runner import run_workflow_for_parent_task
from ada.workflow.steps import KNOWLEDGE_TOOLS_ENRICH


def _wf_kwargs(settings: Settings) -> dict:
    return {
        "settings": settings,
        "system_instruction": "sys",
        "max_tool_rounds": 4,
        "shell_max_output_bytes": 4096,
        "shell_timeout_sec": 1.0,
        "stream_chunk_idle_timeout_sec": 1.0,
        "stream_leg_max_wall_sec": 1.0,
        "rewire_after_tombstone": False,
        "max_session_tokens": 8000,
        "debug_stream": False,
        "knowledge_feed_host_allowlist": frozenset(),
        "knowledge_embeddings_enabled": False,
        "knowledge_embedding_model": "e",
        "knowledge_embedding_dim": 8,
        "knowledge_embedding_min_cosine": 0.1,
        "knowledge_tool_max_results": 4,
        "knowledge_tool_excerpt_chars": 400,
    }


@pytest.mark.asyncio
async def test_enrich_live_calls_orchestrate_with_strict_web(
    tmp_path, schema_sql_path, monkeypatch
):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini")
    monkeypatch.setenv("ADA_ENABLE_WEB_TOOLS", "1")
    monkeypatch.setenv("ADA_SERPER_API_KEY", "fake-serper")
    db = tmp_path / "el.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=2)
    await qe.connect()
    try:
        ent = await qe.upsert_entity(type="service", name="Live Svc", payload_json={})
        eid = int(ent["entity_id"])
        tid = await qe.insert_task("enrich live", status="pending", task_kind=TASK_KIND_GOAL)
        await qe.enqueue_workflow(
            kind="t_enrich_live",
            goal_text="enrich live",
            params_json={"entity_id": eid},
            parent_task_id=tid,
            idempotency_key=None,
            steps=[
                {"step_index": 0, "step_type": "ENRICH", "input_json": {"entity_id": eid}},
            ],
        )
        settings = Settings.load()
        with mock.patch(
            "ada.workflow.publish_enrich_step.enrich_postcondition_met",
            return_value=True,
        ):
            with mock.patch(
                "ada.workflow.publish_enrich_step.orchestrate_turn",
                new=mock.AsyncMock(return_value="model final"),
            ) as ot:
                with mock.patch(
                    "ada.workflow.publish_enrich_step.run_enrich_step",
                    new=mock.AsyncMock(
                        side_effect=AssertionError("reference enrich must not run")
                    ),
                ):
                    await run_workflow_for_parent_task(
                        qe, parent_task_id=tid, goal="enrich live", **_wf_kwargs(settings)
                    )
        assert ot.await_count == 1
        kwa = ot.await_args_list[0].kwargs
        assert kwa.get("workflow_strict") is True
        assert kwa.get("workflow_strict_allow_web") is True
        assert kwa.get("web_config") is not None
        assert kwa.get("knowledge_tool_subset") is not None
        assert kwa.get("enrich_subject_entity_id") == eid
        ut = str(kwa.get("user_text") or "")
        assert "EXISTING_SUBGRAPH" in ut
        got = await qe.get_entity_by_id(eid)
        assert got and got.get("last_enriched_at")
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_enrich_live_retries_graph_only_then_fails(tmp_path, schema_sql_path, monkeypatch):
    """When postcondition never passes, runner issues graph-only retry then raises."""
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini")
    monkeypatch.setenv("ADA_ENABLE_WEB_TOOLS", "1")
    monkeypatch.setenv("ADA_SERPER_API_KEY", "fake-serper")
    db = tmp_path / "el2.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=2)
    await qe.connect()
    try:
        ent = await qe.upsert_entity(type="service", name="S2", payload_json={})
        eid = int(ent["entity_id"])
        tid = await qe.insert_task("enrich live", status="pending", task_kind=TASK_KIND_GOAL)
        await qe.enqueue_workflow(
            kind="t_enrich_live2",
            goal_text="enrich live",
            params_json={"entity_id": eid},
            parent_task_id=tid,
            idempotency_key=None,
            steps=[
                {"step_index": 0, "step_type": "ENRICH", "input_json": {"entity_id": eid}},
            ],
        )
        settings = Settings.load()
        with mock.patch(
            "ada.workflow.publish_enrich_step.enrich_postcondition_met",
            return_value=False,
        ):
            with mock.patch(
                "ada.workflow.publish_enrich_step.orchestrate_turn",
                new=mock.AsyncMock(return_value="x"),
            ) as ot:
                with mock.patch(
                    "ada.workflow.publish_enrich_step.run_enrich_step",
                    new=mock.AsyncMock(),
                ):
                    with pytest.raises(ValueError, match="ENRICH live"):
                        await run_workflow_for_parent_task(
                            qe, parent_task_id=tid, goal="enrich live", **_wf_kwargs(settings)
                        )
        assert ot.await_count == 2
        kwa0 = ot.await_args_list[0].kwargs
        kwa1 = ot.await_args_list[1].kwargs
        assert kwa0.get("web_config") is not None
        assert kwa1.get("web_config") is None
        assert kwa1.get("workflow_strict_allow_web") is False
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_enrich_rejects_record_edge_mismatched_src_entity_id(
    tmp_path, schema_sql_path, monkeypatch
):
    """ENRICH (enrich_subject_entity_id set): record_edge must use subject as src."""
    db = tmp_path / "enrich_re.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        subject = await qe.upsert_entity(type="service", name="Subj", payload_json={})
        other = await qe.upsert_entity(type="organization", name="Other", payload_json={})
        e_subject = int(subject["entity_id"])
        e_other = int(other["entity_id"])
        assert e_subject != e_other
        sid = await qe.insert_knowledge_source("rss", label="L", base_url="https://feed.test/f")
        ins = await qe.insert_knowledge_item(
            sid, "h1", content_excerpt="evidence", tags=[]
        )
        kid = int(ins.id)
        calls = {"n": 0}

        async def leg(**kwargs: object) -> StreamLegResult:
            calls["n"] += 1
            if calls["n"] == 1:
                return StreamLegResult(
                    "",
                    [
                        CompletedFunctionCall(
                            name="record_edge",
                            args={
                                "src_entity_id": e_other,
                                "dst_entity_id": e_subject,
                                "edge_type": "related_to",
                                "confidence": 0.75,
                                "evidence_item_ids": [kid],
                                "source_url": "https://example.com/page",
                            },
                            id="e1",
                        )
                    ],
                    {},
                    None,
                )
            return StreamLegResult("ok", [], {}, None)

        monkeypatch.setattr(orch, "stream_one_model_leg", leg)
        tid = await qe.insert_task("t", status="executing", task_kind=TASK_KIND_CHAT)
        await orch.orchestrate_turn(
            qe,
            session_id=tid,
            user_text="enrich",
            system_instruction="sys",
            api_key="k",
            model="m",
            max_retries=0,
            enable_memory_tools=False,
            include_plan_tools=False,
            include_knowledge_tools=False,
            knowledge_tool_subset=KNOWLEDGE_TOOLS_ENRICH,
            workflow_strict=True,
            workflow_strict_allow_web=False,
            enrich_subject_entity_id=e_subject,
        )
        async with aiosqlite.connect(db) as raw:
            cur = await raw.execute("SELECT COUNT(*) FROM graph_edges")
            row = await cur.fetchone()
        assert row is not None and int(row[0]) == 0
        chain = await qe.load_chain_for_api(tid)
        err_parts = [
            p.get("response")
            for r in chain
            if r.get("role") == "tool"
            for p in r.get("parts", [])
            if p.get("type") == "function_response" and p.get("name") == "record_edge"
        ]
        assert any(
            isinstance(x, dict) and x.get("error") == "src_entity_id must match enrich subject"
            for x in err_parts
        )
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_enrich_graph_sufficient_skips_orchestrate_and_serper(
    tmp_path, schema_sql_path, monkeypatch
):
    """Over graph thresholds, ENRICH completes with graph_sufficient without web or model turn."""
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini")
    monkeypatch.setenv("ADA_ENABLE_WEB_TOOLS", "1")
    monkeypatch.setenv("ADA_SERPER_API_KEY", "fake-serper")
    monkeypatch.setenv("ADA_PUBLISH_MIN_UNIQUE_FACTS", "3")
    db = tmp_path / "suff.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=2)
    await qe.connect()
    serper_n = {"n": 0}

    async def _no_serper(**_: object) -> dict:
        serper_n["n"] += 1
        return {"error": "should not call serper"}

    try:
        a = await qe.upsert_entity(type="service", name="Dense Svc", payload_json={})
        b = await qe.upsert_entity(type="regulation", name="R1", payload_json={})
        e1 = int(a["entity_id"])
        b1 = int(b["entity_id"])
        for i in range(3):
            await qe.insert_graph_edge(
                src_entity_id=e1,
                dst_entity_id=b1,
                edge_type="cites",
                confidence=0.9,
                source_url=f"https://dense.test/doc/{i}",
            )
        assert await qe.count_unique_local_facts(e1) == 3

        tid = await qe.insert_task("suff", status="pending", task_kind=TASK_KIND_GOAL)
        await qe.enqueue_workflow(
            kind="t_suff",
            goal_text="suff",
            params_json={"entity_id": e1},
            parent_task_id=tid,
            idempotency_key=None,
            steps=[
                {"step_index": 0, "step_type": "ENRICH", "input_json": {"entity_id": e1}},
            ],
        )
        settings = Settings.load()
        with mock.patch("ada.tools.web_runtime.serper_search", new=mock.AsyncMock(side_effect=_no_serper)):
            with mock.patch(
                "ada.workflow.publish_enrich_step.orchestrate_turn",
                new=mock.AsyncMock(
                    side_effect=AssertionError(
                        "orchestrate must not run when graph sufficient"
                    )
                ),
            ) as ot:
                with mock.patch(
                    "ada.workflow.publish_enrich_step.run_enrich_step",
                    new=mock.AsyncMock(),
                ):
                    await run_workflow_for_parent_task(
                        qe, parent_task_id=tid, goal="suff", **_wf_kwargs(settings)
                    )
        assert ot.await_count == 0
        assert serper_n["n"] == 0
        wrow = await qe.get_workflow_by_parent_task_id(tid)
        assert wrow is not None
        st = await qe.list_workflow_steps(int(wrow["id"]))
        oj = st[0].get("output_json") or {}
        assert oj.get("path") == "graph_sufficient"
        assert oj.get("metrics", {}).get("unique_local_facts") == 3
    finally:
        await qe.close()
