"""GATE: fail-closed without DRAFT; pass does not require LLM in this module."""

from __future__ import annotations

import aiosqlite
from unittest import mock

import pytest

from ada.config import Settings
from ada.query_engine import TASK_KIND_GOAL, QueryEngine
from ada.workflow.runner import run_workflow_for_parent_task
from ada.workflow.templates import expand_workflow_template


def _wf_kwargs(settings: Settings) -> dict:
    return {
        "settings": settings,
        "system_instruction": "sys",
        "max_tool_rounds": 2,
        "shell_max_output_bytes": 4096,
        "shell_timeout_sec": 1.0,
        "stream_chunk_idle_timeout_sec": 1.0,
        "stream_leg_max_wall_sec": 1.0,
        "rewire_after_tombstone": False,
        "max_session_tokens": 2000,
        "debug_stream": False,
        "knowledge_feed_host_allowlist": frozenset(),
        "knowledge_embeddings_enabled": False,
        "knowledge_embedding_model": "e",
        "knowledge_embedding_dim": 8,
        "knowledge_embedding_min_cosine": 0.1,
        "knowledge_tool_max_results": 1,
        "knowledge_tool_excerpt_chars": 200,
    }


@pytest.mark.asyncio
async def test_gate_fails_closes_draft_not_called(
    tmp_path, schema_sql_path, monkeypatch
):
    monkeypatch.setenv("ADA_PUBLISH_MIN_UNIQUE_FACTS", "2")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    db = tmp_path / "g.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=2)
    await qe.connect()
    try:
        sub = await qe.upsert_entity(
            type="service", name="Orphan Svc", payload_json={}
        )
        eid = int(sub["entity_id"])
        tid = await qe.insert_task("gate test", status="pending", task_kind=TASK_KIND_GOAL)
        wf_id, _ = await qe.enqueue_workflow(
            kind="t_gate",
            goal_text="gate test",
            params_json={"entity_id": eid},
            parent_task_id=tid,
            idempotency_key=None,
            steps=[
                {"step_index": 0, "step_type": "ENRICH", "input_json": {"entity_id": eid}},
                {"step_index": 1, "step_type": "GATE", "input_json": {"entity_id": eid}},
                {"step_index": 2, "step_type": "DRAFT", "input_json": {"entity_id": eid, "project_id": "p", "campaign_id": "c", "niche": "n"}},
            ],
        )
        s = Settings.load()
        with mock.patch(
            "ada.workflow.publish_enrich_step.run_enrich_step",
            new=mock.AsyncMock(
                return_value={
                    "knowledge_item_ids": [],
                    "graph_edge_ids": [],
                    "last_enriched_at": "x",
                },
            ),
        ):
            with mock.patch("ada.workflow.runner.run_publish_draft", new=mock.AsyncMock(
                side_effect=AssertionError("DRAFT must not run when GATE fails")
            )):
                with pytest.raises(Exception, match="GATE|minimum"):
                    await run_workflow_for_parent_task(
                        qe, parent_task_id=tid, goal="gate test", **_wf_kwargs(s)
                    )
        w = await qe.get_workflow_by_id(wf_id)
        assert w and str(w.get("status")) == "failed"
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_gate_ok_with_sufficient_edges(tmp_path, schema_sql_path, monkeypatch):
    monkeypatch.setenv("ADA_PUBLISH_MIN_UNIQUE_FACTS", "1")
    db = tmp_path / "g2.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=2)
    await qe.connect()
    try:
        sub = await qe.upsert_entity(
            type="service", name="S", payload_json={}
        )
        dst = await qe.upsert_entity(
            type="regulation", name="R", payload_json={}
        )
        eid, did = int(sub["entity_id"]), int(dst["entity_id"])
        await qe.insert_graph_edge(
            src_entity_id=eid,
            dst_entity_id=did,
            edge_type="ref",
            confidence=0.5,
            source_url="https://u.test/1",
        )
        tid = await qe.insert_task("g2", status="pending", task_kind=TASK_KIND_GOAL)
        wf_id, _ = await qe.enqueue_workflow(
            kind="t_g2",
            goal_text="g2",
            params_json={"entity_id": eid},
            parent_task_id=tid,
            idempotency_key=None,
            steps=[
                {"step_index": 0, "step_type": "GATE", "input_json": {"entity_id": eid}},
            ],
        )
        s = Settings.load()
        await run_workflow_for_parent_task(
            qe, parent_task_id=tid, goal="g2", **_wf_kwargs(s)
        )
        w = await qe.get_workflow_by_id(wf_id)
        assert w and str(w.get("status")) == "completed"
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_draft_step_uses_explicit_keyword_cluster(tmp_path, schema_sql_path, monkeypatch):
    monkeypatch.setenv("ADA_PUBLISH_MIN_UNIQUE_FACTS", "0")
    db = tmp_path / "dkey.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=2)
    await qe.connect()
    try:
        sub = await qe.upsert_entity(type="service", name="S3", payload_json={})
        eid = int(sub["entity_id"])
        tid = await qe.insert_task("d3", status="pending", task_kind=TASK_KIND_GOAL)
        wf_id, _ = await qe.enqueue_workflow(
            kind="t_d3",
            goal_text="d3",
            params_json={
                "entity_id": eid,
                "target_keyword_cluster": "roof repair auckland",
                "keyword_source": {"kind": "gsc"},
            },
            parent_task_id=tid,
            idempotency_key=None,
            steps=[
                {"step_index": 0, "step_type": "DRAFT", "input_json": {"entity_id": eid}},
            ],
        )
        s = Settings.load()
        with mock.patch(
            "ada.workflow.runner.run_publish_draft",
            new=mock.AsyncMock(return_value={"page": {"slug": "x", "title": "t", "meta_description": "m", "content": "<h1>x</h1>", "lead_gen": {"type": "form", "cta": "c"}, "json_ld": {"@context": "https://schema.org", "@type": "WebPage"}, "og_image": "https://img.test/1.png"}}),
        ):
            await run_workflow_for_parent_task(
                qe, parent_task_id=tid, goal="d3", **_wf_kwargs(s)
            )
        st = await qe.list_workflow_steps(wf_id)
        out = st[0]["output_json"]
        assert out["keyword_cluster_used"] is True
        assert out["fallback_reason"] is None
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_draft_step_gsc_no_rows_fallback(tmp_path, schema_sql_path, monkeypatch):
    monkeypatch.setenv("ADA_PUBLISH_MIN_UNIQUE_FACTS", "0")
    db = tmp_path / "dkey2.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=2)
    await qe.connect()
    try:
        sub = await qe.upsert_entity(type="service", name="S4", payload_json={})
        eid = int(sub["entity_id"])
        tid = await qe.insert_task("d4", status="pending", task_kind=TASK_KIND_GOAL)
        wf_id, _ = await qe.enqueue_workflow(
            kind="t_d4",
            goal_text="d4",
            params_json={
                "entity_id": eid,
                "keyword_source": {
                    "kind": "gsc",
                    "site": "https://example.com/",
                    "start_date": "2026-01-01",
                    "end_date": "2026-01-31",
                },
            },
            parent_task_id=tid,
            idempotency_key=None,
            steps=[
                {"step_index": 0, "step_type": "DRAFT", "input_json": {"entity_id": eid}},
            ],
        )
        s = Settings.load()
        with mock.patch(
            "ada.workflow.runner.run_publish_draft",
            new=mock.AsyncMock(return_value={"page": {"slug": "x", "title": "t", "meta_description": "m", "content": "<h1>x</h1>", "lead_gen": {"type": "form", "cta": "c"}, "json_ld": {"@context": "https://schema.org", "@type": "WebPage"}, "og_image": "https://img.test/1.png"}}),
        ):
            await run_workflow_for_parent_task(
                qe, parent_task_id=tid, goal="d4", **_wf_kwargs(s)
            )
        st = await qe.list_workflow_steps(wf_id)
        out = st[0]["output_json"]
        assert out["keyword_cluster_used"] is False
        assert out["fallback_reason"] in ("gsc_no_rows", "gsc_table_missing")
        async with aiosqlite.connect(db) as raw:
            cur = await raw.execute(
                "SELECT kind, payload_json FROM action_log WHERE kind='publish_keyword_targeting'"
            )
            row = await cur.fetchone()
        assert row is not None
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_publish_keyword_v1_provisions_entity_and_draft_gets_id(
    tmp_path, schema_sql_path, monkeypatch
):
    monkeypatch.setenv("ADA_ENABLE_WEB_TOOLS", "0")
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    db = tmp_path / "pkw.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=2)
    await qe.connect()
    try:
        tid = await qe.insert_task("kw pub", status="pending", task_kind=TASK_KIND_GOAL)
        params = {
            "target_keyword_cluster": "roof repair auckland",
            "project_id": "p",
            "campaign_id": "c",
            "niche": "n",
        }
        steps = expand_workflow_template("publish_keyword_v1", params, max_steps=10)
        wf_id, _ = await qe.enqueue_workflow(
            kind="publish_keyword_v1",
            goal_text="kw pub",
            params_json={**params},
            parent_task_id=tid,
            idempotency_key="idem-kw-1",
            steps=steps,
        )
        s = Settings.load()
        draft = mock.AsyncMock(
            return_value={
                "page": {
                    "slug": "x",
                    "title": "t",
                    "meta_description": "m",
                    "content": "<h1>x</h1>",
                    "lead_gen": {
                        "form_fields": [],
                        "form_action_url": "https://example.com/contact",
                        "call_display_phone": "",
                        "call_tel_link": "tel:+1",
                    },
                    "json_ld": {
                        "@context": "https://schema.org",
                        "@type": "WebPage",
                    },
                    "og_image": "https://img.test/1.png",
                }
            }
        )
        with mock.patch(
            "ada.workflow.publish_enrich_step.run_enrich_step",
            new=mock.AsyncMock(
                return_value={
                    "knowledge_item_ids": [],
                    "graph_edge_ids": [],
                    "last_enriched_at": "x",
                }
            ),
        ):
            with mock.patch("ada.workflow.runner.run_publish_draft", new=draft):
                with mock.patch(
                    "ada.workflow.runner.asyncio.to_thread",
                    new=mock.AsyncMock(return_value={"ok": True}),
                ):
                    await run_workflow_for_parent_task(
                        qe, parent_task_id=tid, goal="kw pub", **_wf_kwargs(s)
                    )
        w = await qe.get_workflow_by_id(wf_id)
        pj = w.get("params_json") if isinstance(w.get("params_json"), dict) else {}
        eid = pj.get("entity_id")
        assert eid is not None
        assert pj.get("keyword_stub") is True
        ent = await qe.get_entity_by_id(int(eid))
        assert ent and str(ent.get("type")) == "keyword_landing"
        call_kw = draft.call_args[1]
        assert call_kw.get("params", {}).get("entity_id") == eid
        assert call_kw.get("params", {}).get("target_keyword_cluster")
    finally:
        await qe.close()
