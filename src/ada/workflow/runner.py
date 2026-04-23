"""Run Phase 3 workflows for a parent goal task (daemon)."""

from __future__ import annotations

import json
import logging
from typing import Any

from ada.config import Settings
from ada.ingest.rss import ingest_rss_feeds
from ada.orchestrator import orchestrate_turn
from ada.query_engine import QueryEngine
from ada.tools.registry import KNOWLEDGE_TOOLS_EXTRACT, KNOWLEDGE_TOOLS_SYNTHESIZE

log = logging.getLogger("ada.workflow.runner")


def _build_extract_user_text(
    *,
    goal_text: str,
    item_ids: list[int],
    params: dict[str, Any],
) -> str:
    lines = [
        "[WORKFLOW_STEP:EXTRACT]",
        f"Parent goal: {goal_text}",
        "Extract graph-lite entities and edges grounded in the following knowledge_items ids.",
        f"item_ids: {json.dumps(item_ids)}",
        "Use only record_entity, record_edge, and link_evidence. Cite evidence_item_ids from these items.",
        f"Extra params: {json.dumps(params, ensure_ascii=False)}",
    ]
    return "\n".join(lines)


def _build_synthesize_user_text(
    *,
    goal_text: str,
    params: dict[str, Any],
    prior_summary: str,
) -> str:
    topic = str(params.get("topic") or "Summarize recent ingested knowledge.").strip()
    lines = [
        "[WORKFLOW_STEP:SYNTHESIZE]",
        f"Parent goal: {goal_text}",
        f"Topic: {topic}",
        "Use search_knowledge then record_synthesis with ref_item_ids from search results.",
        f"Prior step summary: {prior_summary}",
    ]
    return "\n".join(lines)


async def run_workflow_for_parent_task(
    qe: QueryEngine,
    *,
    settings: Settings,
    parent_task_id: int,
    goal: str,
    system_instruction: str,
    max_tool_rounds: int,
    shell_max_output_bytes: int,
    shell_timeout_sec: float,
    stream_chunk_idle_timeout_sec: float | None,
    stream_leg_max_wall_sec: float | None,
    rewire_after_tombstone: bool,
    max_session_tokens: int,
    debug_stream: bool,
    knowledge_feed_host_allowlist: frozenset[str],
    knowledge_embeddings_enabled: bool,
    knowledge_embedding_model: str,
    knowledge_embedding_dim: int,
    knowledge_embedding_min_cosine: float,
    knowledge_tool_max_results: int,
    knowledge_tool_excerpt_chars: int,
) -> str:
    """
    Execute workflow steps for workflows.parent_task_id == parent_task_id.
    Caller must verify a workflow row exists for this task.
    """
    wf = await qe.get_workflow_by_parent_task_id(parent_task_id)
    if wf is None:
        raise RuntimeError("run_workflow_for_parent_task called without workflow row")

    wf_id = int(wf["id"])
    await qe.update_workflow_row(wf_id, status="running")
    steps = await qe.list_workflow_steps(wf_id)
    params = wf.get("params_json") if isinstance(wf.get("params_json"), dict) else {}
    prior_bits: list[str] = []
    last_final = ""

    for st in steps:
        sid = int(st["id"])
        stype = str(st["step_type"]).upper()
        if str(st["status"]) == "completed":
            prior_bits.append(f"{stype}: skipped (already completed)")
            continue
        await qe.update_workflow_step_row(sid, status="running", increment_attempt=True)
        try:
            if stype == "FETCH":
                res = await ingest_rss_feeds(qe, settings=settings)
                out = {
                    "feeds_attempted": res.feeds_attempted,
                    "feeds_ok": res.feeds_ok,
                    "items_inserted": res.items_inserted,
                    "items_deduped": res.items_deduped,
                    "errors": res.errors[:12],
                }
                await qe.update_workflow_step_row(
                    sid, status="completed", output_json=out, error=""
                )
                prior_bits.append(f"FETCH: {out}")
            elif stype == "EXTRACT":
                inp = st.get("input_json") or {}
                lim = int(inp.get("recent_item_limit") or 40)
                item_ids = await qe.list_recent_knowledge_item_ids(limit=lim)
                user_txt = _build_extract_user_text(
                    goal_text=str(wf.get("goal_text") or goal),
                    item_ids=item_ids,
                    params=params,
                )
                final = await orchestrate_turn(
                    qe,
                    session_id=parent_task_id,
                    user_text=user_txt,
                    system_instruction=system_instruction,
                    api_key=settings.gemini_api_key,
                    model=settings.gemini_model,
                    shell_allowlist=frozenset(),
                    max_tool_rounds=max_tool_rounds,
                    shell_max_output_bytes=shell_max_output_bytes,
                    shell_timeout_sec=shell_timeout_sec,
                    stream_chunk_idle_timeout_sec=stream_chunk_idle_timeout_sec,
                    stream_leg_max_wall_sec=stream_leg_max_wall_sec,
                    rewire_after_tombstone=rewire_after_tombstone,
                    enable_memory_tools=False,
                    memory_config=None,
                    include_plan_tools=False,
                    include_goal_recall_tool=False,
                    file_config=None,
                    max_session_tokens=max_session_tokens,
                    on_file_guard_violation=None,
                    web_config=None,
                    enable_list_session_web_sources=False,
                    debug_stream=debug_stream,
                    include_knowledge_tools=False,
                    knowledge_feed_host_allowlist=knowledge_feed_host_allowlist,
                    knowledge_embeddings_enabled=knowledge_embeddings_enabled,
                    knowledge_embedding_model=knowledge_embedding_model,
                    knowledge_embedding_dim=knowledge_embedding_dim,
                    knowledge_embedding_min_cosine=knowledge_embedding_min_cosine,
                    knowledge_tool_max_results=knowledge_tool_max_results,
                    knowledge_tool_excerpt_chars=knowledge_tool_excerpt_chars,
                    knowledge_tool_subset=KNOWLEDGE_TOOLS_EXTRACT,
                    workflow_strict=True,
                    include_workflow_tools=False,
                    workflow_max_steps=None,
                )
                await qe.update_workflow_step_row(
                    sid,
                    status="completed",
                    output_json={"assistant_excerpt": final[:4000]},
                    error="",
                )
                prior_bits.append(f"EXTRACT: model completed ({len(final)} chars)")
                last_final = final
            elif stype == "SYNTHESIZE":
                user_txt = _build_synthesize_user_text(
                    goal_text=str(wf.get("goal_text") or goal),
                    params=params,
                    prior_summary="; ".join(prior_bits)[-6000:],
                )
                final = await orchestrate_turn(
                    qe,
                    session_id=parent_task_id,
                    user_text=user_txt,
                    system_instruction=system_instruction,
                    api_key=settings.gemini_api_key,
                    model=settings.gemini_model,
                    shell_allowlist=frozenset(),
                    max_tool_rounds=max_tool_rounds,
                    shell_max_output_bytes=shell_max_output_bytes,
                    shell_timeout_sec=shell_timeout_sec,
                    stream_chunk_idle_timeout_sec=stream_chunk_idle_timeout_sec,
                    stream_leg_max_wall_sec=stream_leg_max_wall_sec,
                    rewire_after_tombstone=rewire_after_tombstone,
                    enable_memory_tools=False,
                    memory_config=None,
                    include_plan_tools=False,
                    include_goal_recall_tool=False,
                    file_config=None,
                    max_session_tokens=max_session_tokens,
                    on_file_guard_violation=None,
                    web_config=None,
                    enable_list_session_web_sources=False,
                    debug_stream=debug_stream,
                    include_knowledge_tools=False,
                    knowledge_feed_host_allowlist=knowledge_feed_host_allowlist,
                    knowledge_embeddings_enabled=knowledge_embeddings_enabled,
                    knowledge_embedding_model=knowledge_embedding_model,
                    knowledge_embedding_dim=knowledge_embedding_dim,
                    knowledge_embedding_min_cosine=knowledge_embedding_min_cosine,
                    knowledge_tool_max_results=knowledge_tool_max_results,
                    knowledge_tool_excerpt_chars=knowledge_tool_excerpt_chars,
                    knowledge_tool_subset=KNOWLEDGE_TOOLS_SYNTHESIZE,
                    workflow_strict=True,
                    include_workflow_tools=False,
                    workflow_max_steps=None,
                )
                await qe.update_workflow_step_row(
                    sid,
                    status="completed",
                    output_json={"assistant_excerpt": final[:4000]},
                    error="",
                )
                prior_bits.append(f"SYNTHESIZE: model completed ({len(final)} chars)")
                last_final = final
            else:
                raise RuntimeError(f"unsupported step_type {stype!r}")
        except Exception as e:
            log.exception("workflow step failed wf=%s step=%s", wf_id, sid)
            await qe.update_workflow_step_row(
                sid, status="failed", error=str(e)[:2000]
            )
            await qe.update_workflow_row(wf_id, status="failed")
            raise

    await qe.update_workflow_row(wf_id, status="completed")
    return last_final if last_final else "\n".join(prior_bits)
