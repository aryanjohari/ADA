"""record_edge: mandatory https source_url for fact edges (GATE provenance)."""

from __future__ import annotations

import aiosqlite
import pytest

import ada.orchestrator as orch
from ada.query_engine import TASK_KIND_CHAT, QueryEngine
from ada.stream_types import CompletedFunctionCall, StreamLegResult
from ada.tools.registry import KNOWLEDGE_TOOLS_EXTRACT


@pytest.mark.asyncio
async def test_record_edge_rejects_fact_without_source_url(
    tmp_path, schema_sql_path, monkeypatch
):
    db = tmp_path / "re.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        ea = await qe.upsert_entity(type="organization", name="A Co")
        eb = await qe.upsert_entity(type="organization", name="B Co")
        aid, bid = int(ea["entity_id"]), int(eb["entity_id"])
        sid = await qe.insert_knowledge_source("rss", label="L", base_url="https://feed.test/f")
        ins = await qe.insert_knowledge_item(
            sid, "h1", content_excerpt="evidence text", tags=[]
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
                                "src_entity_id": aid,
                                "dst_entity_id": bid,
                                "edge_type": "related_to",
                                "confidence": 0.75,
                                "evidence_item_ids": [kid],
                            },
                            id="e1",
                        )
                    ],
                    {},
                    None,
                )
            return StreamLegResult("Done.", [], {}, None)

        monkeypatch.setattr(orch, "stream_one_model_leg", leg)
        tid = await qe.insert_task("t", status="executing", task_kind=TASK_KIND_CHAT)
        await orch.orchestrate_turn(
            qe,
            session_id=tid,
            user_text="edge",
            system_instruction="sys",
            api_key="k",
            model="m",
            max_retries=0,
            enable_memory_tools=False,
            include_plan_tools=False,
            include_knowledge_tools=False,
            knowledge_tool_subset=KNOWLEDGE_TOOLS_EXTRACT,
            workflow_strict=True,
        )
        async with aiosqlite.connect(db) as raw:
            cur = await raw.execute("SELECT COUNT(*) FROM graph_edges")
            row = await cur.fetchone()
        assert row is not None and int(row[0]) == 0
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_record_edge_inserts_source_url_and_gate_count(
    tmp_path, schema_sql_path, monkeypatch
):
    db = tmp_path / "re2.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        ea = await qe.upsert_entity(type="organization", name="A Co")
        eb = await qe.upsert_entity(type="organization", name="B Co")
        aid, bid = int(ea["entity_id"]), int(eb["entity_id"])
        sid = await qe.insert_knowledge_source("rss", label="L", base_url="https://feed.test/f")
        ins = await qe.insert_knowledge_item(
            sid, "h2", content_excerpt="evidence text", tags=[]
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
                                "src_entity_id": aid,
                                "dst_entity_id": bid,
                                "edge_type": "related_to",
                                "confidence": 0.75,
                                "evidence_item_ids": [kid],
                                "source_url": "https://example.com/article",
                            },
                            id="e2",
                        )
                    ],
                    {},
                    None,
                )
            return StreamLegResult("Done.", [], {}, None)

        monkeypatch.setattr(orch, "stream_one_model_leg", leg)
        tid = await qe.insert_task("t", status="executing", task_kind=TASK_KIND_CHAT)
        await orch.orchestrate_turn(
            qe,
            session_id=tid,
            user_text="edge",
            system_instruction="sys",
            api_key="k",
            model="m",
            max_retries=0,
            enable_memory_tools=False,
            include_plan_tools=False,
            include_knowledge_tools=False,
            knowledge_tool_subset=KNOWLEDGE_TOOLS_EXTRACT,
            workflow_strict=True,
        )
        n = await qe.count_unique_local_facts(aid)
        assert n == 1
        async with aiosqlite.connect(db) as raw:
            cur = await raw.execute(
                "SELECT source_url FROM graph_edges WHERE src_entity_id = ?",
                (aid,),
            )
            row = await cur.fetchone()
        assert row and row[0] == "https://example.com/article"
    finally:
        await qe.close()
