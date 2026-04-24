"""Phase 3: workflows, tool subsets, enqueue idempotency."""

from __future__ import annotations

import pytest

from ada.query_engine import TASK_KIND_GOAL, QueryEngine
from ada.stream_types import CompletedFunctionCall
from ada.tool_executor import StreamingToolExecutor
from ada.tools.registry import (
    KNOWLEDGE_TOOLS_EXTRACT,
    KNOWLEDGE_TOOLS_SYNTHESIZE,
    build_agent_tools,
    frozen_tool_declaration_names,
    knowledge_function_declarations_subset,
)
from ada.workflow.steps import ENRICH_STRICT_TOOL_NAMES, KNOWLEDGE_TOOLS_ENRICH
from ada.workflow.templates import (
    WORKFLOW_KINDS,
    expand_workflow_template,
    validate_workflow_step_dependencies,
)


def test_knowledge_subset_extract_excludes_search():
    decls = knowledge_function_declarations_subset(KNOWLEDGE_TOOLS_EXTRACT)
    names = {d.name for d in decls}
    assert names == KNOWLEDGE_TOOLS_EXTRACT
    assert "search_knowledge" not in names


def test_knowledge_subset_synthesize_excludes_graph():
    decls = knowledge_function_declarations_subset(KNOWLEDGE_TOOLS_SYNTHESIZE)
    names = {d.name for d in decls}
    assert names == KNOWLEDGE_TOOLS_SYNTHESIZE
    assert "record_entity" not in names


def test_build_agent_tools_workflow_strict_subset():
    t = build_agent_tools(
        allowed_exact_commands=frozenset(),
        include_memory_tools=False,
        include_plan_tools=False,
        include_file_tools=False,
        include_web_search=False,
        include_web_fetch=False,
        include_knowledge_tools=False,
        knowledge_tool_subset=KNOWLEDGE_TOOLS_SYNTHESIZE,
        include_workflow_tools=False,
    )
    names = frozen_tool_declaration_names(t)
    assert "search_knowledge" in names
    assert "record_entity" not in names
    assert "check_token_usage" in names


def test_enrich_live_strict_tool_names_match_build():
    t = build_agent_tools(
        allowed_exact_commands=frozenset(),
        include_memory_tools=False,
        include_plan_tools=False,
        include_file_tools=False,
        include_web_search=True,
        include_web_fetch=True,
        include_knowledge_tools=False,
        knowledge_tool_subset=KNOWLEDGE_TOOLS_ENRICH,
        include_workflow_tools=False,
    )
    assert frozen_tool_declaration_names(t) == ENRICH_STRICT_TOOL_NAMES


@pytest.mark.asyncio
async def test_workflow_schema_and_idempotent_enqueue(tmp_path, schema_sql_path):
    db = tmp_path / "w.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=2)
    await qe.connect()
    try:
        tid = await qe.insert_task("goal text", status="pending", task_kind=TASK_KIND_GOAL)
        steps = expand_workflow_template(
            "rss_fetch_then_graph_then_synth",
            {"topic": "Test topic"},
            max_steps=10,
        )
        wf_id, created = await qe.enqueue_workflow(
            kind="rss_fetch_then_graph_then_synth",
            goal_text="goal text",
            params_json={"topic": "Test topic"},
            parent_task_id=tid,
            idempotency_key="idem-1",
            steps=steps,
        )
        assert created is True
        wf_id2, created2 = await qe.enqueue_workflow(
            kind="rss_fetch_then_graph_then_synth",
            goal_text="other",
            params_json={},
            parent_task_id=tid,
            idempotency_key="idem-1",
            steps=steps,
        )
        assert created2 is False
        assert wf_id2 == wf_id
        listed = await qe.list_workflow_steps(wf_id)
        assert len(listed) == 3
        assert [s["step_type"] for s in listed] == ["FETCH", "EXTRACT", "SYNTHESIZE"]
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_expand_respects_max_task_steps():
    with pytest.raises(ValueError, match="ADA_MAX_TASK_STEPS"):
        expand_workflow_template(
            "rss_fetch_then_graph_then_synth",
            {},
            max_steps=2,
        )


def test_expand_publish_entity_v1_merges_params():
    st = expand_workflow_template(
        "publish_entity_v1",
        {
            "entity_id": 42,
            "project_id": "proj",
            "campaign_id": "camp",
            "niche": "widgets",
        },
        max_steps=10,
    )
    assert [x["step_type"] for x in st] == ["ENRICH", "GATE", "DRAFT", "DEPLOY"]
    for step in st:
        inp = step.get("input_json") or {}
        assert inp.get("entity_id") == 42
        assert inp.get("project_id") == "proj"
        assert inp.get("niche") == "widgets"


def test_validate_dependency_rejects_forward_ref():
    steps = [
        {
            "step_index": 1,
            "step_type": "FETCH",
            "input_json": {"depends_on_step_index": 1},
        },
    ]
    with pytest.raises(ValueError, match="depends_on_step_index"):
        validate_workflow_step_dependencies(steps)


@pytest.mark.asyncio
async def test_executor_dispatch_allowlist_blocks_unknown():
    async def _search(_call: CompletedFunctionCall) -> dict:
        return {"items": [], "count": 0, "returned_count": 0, "truncated": False}

    ex = StreamingToolExecutor(
        allowlist_exact=frozenset(),
        max_output_bytes=1024,
        timeout_sec=5.0,
        memory=None,
        plan_hooks=None,
        token_usage=None,
        file_config=None,
        web=None,
        dispatch_allowlist=frozenset({"check_token_usage", "search_knowledge"}),
        knowledge_search=_search,
    )
    call = CompletedFunctionCall(
        name="record_entity",
        args={"name": "X", "type": "organization"},
        id="1",
    )
    out = await ex._dispatch(call)
    assert out.get("error") == "tool_not_allowed_in_workflow_step"


def test_workflow_kinds_contains_builtin():
    assert "rss_fetch_then_graph_then_synth" in WORKFLOW_KINDS
    assert "publish_entity_v1" in WORKFLOW_KINDS
