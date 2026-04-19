from __future__ import annotations

import pytest

import ada.orchestrator as orch
from ada.query_engine import TASK_KIND_CHAT, QueryEngine
from ada.stream_types import CompletedFunctionCall, StreamLegResult


@pytest.mark.asyncio
async def test_orchestrator_knowledge_search_and_synthesis_mock(
    tmp_path, schema_sql_path, monkeypatch
):
    """Offline: mocked model calls search_knowledge then record_synthesis; DB reflects synthesis."""
    calls = {"n": 0}

    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        sid = await qe.insert_knowledge_source("rss", label="L", base_url="https://x.test/feed")
        ins = await qe.insert_knowledge_item(
            sid,
            "hh1",
            content_excerpt="market crisis analysis",
            tags=["test"],
        )
        item_id = ins.id

        async def three_leg(**kwargs: object) -> StreamLegResult:
            calls["n"] += 1
            n = calls["n"]
            if n == 1:
                return StreamLegResult(
                    "",
                    [
                        CompletedFunctionCall(
                            name="search_knowledge",
                            args={"query": "crisis", "limit": 10},
                            id="k1",
                        )
                    ],
                    {},
                    None,
                )
            if n == 2:
                return StreamLegResult(
                    "",
                    [
                        CompletedFunctionCall(
                            name="record_synthesis",
                            args={
                                "body": "Crisis noted in stored feed.",
                                "ref_item_ids": [item_id],
                            },
                            id="k2",
                        )
                    ],
                    {},
                    None,
                )
            return StreamLegResult("Complete.", [], {}, None)

        monkeypatch.setattr(orch, "stream_one_model_leg", three_leg)

        tid = await qe.insert_task(
            "Interactive", status="executing", task_kind=TASK_KIND_CHAT
        )
        out = await orch.orchestrate_turn(
            qe,
            session_id=tid,
            user_text="use knowledge",
            system_instruction="sys",
            api_key="k",
            model="m",
            max_retries=0,
            enable_memory_tools=False,
            include_plan_tools=False,
            include_knowledge_tools=True,
            knowledge_feed_host_allowlist=frozenset(),
        )
        assert out == "Complete."
        syns = await qe.list_knowledge_synthesis_for_task(tid)
        assert len(syns) == 1
        assert item_id in syns[0]["ref_item_ids"]
        chain = await qe.load_chain_for_api(tid)
        tool_names = [
            p.get("name")
            for row in chain
            if row["role"] == "tool"
            for p in row.get("parts", [])
            if p.get("type") == "function_response"
        ]
        assert "search_knowledge" in tool_names
        assert "record_synthesis" in tool_names
    finally:
        await qe.close()
