"""Workflow runner injects mission brief_md into step prompts."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from ada.config import Settings
from ada.programme.mission_brief import load_mission_brief_for_workflow
from ada.query_engine import TASK_KIND_GOAL, QueryEngine
from ada.workflow.runner import _build_extract_user_text, run_workflow_for_parent_task


def test_build_extract_user_text_includes_programme_brief() -> None:
    text = _build_extract_user_text(
        goal_text="goal",
        item_ids=[1, 2],
        params={},
        programme_brief="NZ ISR pages for operators.",
    )
    assert "[PROGRAMME_BRIEF]" in text
    assert "NZ ISR pages" in text
    assert "[WORKFLOW_STEP:EXTRACT]" in text


@pytest.mark.asyncio
async def test_load_mission_brief_for_workflow(schema_sql_path, test_settings) -> None:
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        mid = await qe.create_mission(
            slug="wf-brief-load",
            title="T",
            brief_md="Stored mission brief text.",
        )
        brief = await load_mission_brief_for_workflow(qe, mid)
        assert "Stored mission brief" in brief
        assert await load_mission_brief_for_workflow(qe, None) == ""
    finally:
        await qe.close()


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
async def test_runner_extract_includes_mission_brief(
    tmp_path, schema_sql_path, monkeypatch
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    db = tmp_path / "brief_wf.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=2)
    await qe.connect()
    try:
        mid = await qe.create_mission(
            slug="wf-brief-run",
            title="T",
            brief_md="NZ ISR operator intent for EXTRACT.",
        )
        tid = await qe.insert_task("extract brief", status="pending", task_kind=TASK_KIND_GOAL)
        await qe.enqueue_workflow(
            kind="rss_fetch_then_graph_then_synth",
            goal_text="extract brief",
            params_json={"topic": "t"},
            parent_task_id=tid,
            idempotency_key="brief-extract-1",
            steps=[
                {"step_index": 0, "step_type": "EXTRACT", "input_json": {}},
            ],
            mission_id=mid,
        )
        captured: dict = {}

        async def _orch(*_args, **kwargs):
            captured.update(kwargs)
            return "ok"

        s = Settings.load()
        with patch(
            "ada.workflow.runner.orchestrate_turn",
            new=AsyncMock(side_effect=_orch),
        ):
            await run_workflow_for_parent_task(
                qe, parent_task_id=tid, goal="extract brief", **_wf_kwargs(s)
            )
        assert "[PROGRAMME_BRIEF]" in captured.get("user_text", "")
        assert "NZ ISR operator intent" in captured.get("user_text", "")
    finally:
        await qe.close()
