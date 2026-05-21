"""Shared daemon path: one model turn for a pending goal (legacy poll or system_jobs worker)."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from ada.analytics.planner import build_gsc_campaign_plan_payload, default_window
from ada.budget import daemon_should_execute_goal, maybe_log_daemon_block
from ada.orchestrator import file_guard_audit_hook, orchestrate_turn
from ada.tool_executor import FileToolConfig, MemoryToolConfig, WebToolConfig
from ada.workflow.runner import run_workflow_for_parent_task

if TYPE_CHECKING:
    from ada.config import Settings
    from ada.orchestration_profile import OrchestrationProfile
    from ada.query_engine import PendingGoalTask, QueryEngine

log = logging.getLogger("ada.daemon_goal")


def _memory_tool_config(settings: Settings) -> MemoryToolConfig | None:
    if not settings.enable_memory_tools:
        return None
    return MemoryToolConfig(
        master_path=settings.master_path,
        soul_path=settings.soul_path,
        backups_dir=settings.memory_backups_dir,
        memory_dir=settings.memory_dir,
        max_append_bytes=settings.memory_max_append_bytes,
        max_file_bytes=settings.memory_max_file_bytes,
    )


def _file_tool_config(settings: Settings) -> FileToolConfig | None:
    if not settings.enable_file_tools:
        return None
    roots = settings.file_sandbox_roots
    return FileToolConfig(
        roots=roots,
        primary_root=roots[0],
        max_read_bytes=settings.file_max_read_bytes,
        max_write_bytes=settings.file_max_write_bytes,
        deny_prefixes=settings.file_deny_prefixes,
        deny_basenames_extra=settings.file_deny_basenames_extra,
        max_list_entries=settings.file_max_list_entries,
    )


async def maybe_generate_gsc_plan_for_goal(
    qe: QueryEngine, *, settings: Settings, task_id: int, goal: str
) -> None:
    if not settings.enable_gsc_read_tools:
        return
    site = settings.gsc_site_url.strip()
    if not site:
        return
    raw_plan = await qe.get_task_plan_json(task_id)
    try:
        existing = json.loads(raw_plan)
    except json.JSONDecodeError:
        existing = {}
    if isinstance(existing, dict) and (
        existing.get("top_opportunities")
        or existing.get("approval_status") == "pending"
    ):
        return
    window = default_window(
        site=site,
        lookback_days=settings.gsc_plan_default_lookback_days,
        limit=settings.gsc_plan_max_items,
    )
    payload = await build_gsc_campaign_plan_payload(
        qe,
        campaign_goal=goal,
        window=window,
        max_items=settings.gsc_plan_max_items,
    )
    await qe.set_task_plan_json(
        task_id, json.dumps(payload, ensure_ascii=False, sort_keys=True)
    )
    await qe.append_action_log(
        "gsc_plan_generated",
        {
            "task_id": task_id,
            "site": site,
            "start_date": window.start_date,
            "end_date": window.end_date,
            "max_items": settings.gsc_plan_max_items,
            "opportunities": len(payload.get("top_opportunities", [])),
        },
        session_id=task_id,
    )


async def execute_goal_daemon_turn(
    qe: QueryEngine,
    settings: Settings,
    pending: PendingGoalTask,
    *,
    system_instruction: str,
    shell_allowlist: frozenset[str],
    file_cfg: FileToolConfig | None,
    web_cfg: WebToolConfig,
    memory_tool_config: MemoryToolConfig | None,
    action_log_kind: str = "daemon_goal_dequeued",
    orchestration_profile: OrchestrationProfile | None = None,
) -> None:
    """Run budget check, GSC plan, workflow or orchestrate_turn, then terminal task status."""
    from ada.orchestration_profile import orchestrate_turn_kwargs

    task_id = pending.task_id
    goal = pending.goal
    totals = await qe.get_global_usage_token_totals_utc()
    allowed, block_reason = daemon_should_execute_goal(
        kill_switch=settings.ada_kill_switch,
        day_total=totals["day_total"],
        month_total=totals["month_total"],
        daily_limit=settings.ada_daily_token_budget,
        monthly_limit=settings.ada_monthly_token_budget,
    )
    if not allowed:
        await maybe_log_daemon_block(
            qe,
            block_reason=block_reason or "kill_switch",
            totals=totals,
            settings=settings,
        )
        return
    payload: dict[str, object] = {"task_id": task_id}
    if pending.mission_id is not None:
        payload["mission_id"] = pending.mission_id
    if pending.mission_slug:
        payload["mission_slug"] = pending.mission_slug
    await qe.append_action_log(action_log_kind, payload, session_id=task_id)
    await qe.update_task(task_id, status="executing")
    try:
        await maybe_generate_gsc_plan_for_goal(
            qe, settings=settings, task_id=task_id, goal=goal
        )
        wf_attached = await qe.get_workflow_by_parent_task_id(task_id)
        if wf_attached is not None:
            final = await run_workflow_for_parent_task(
                qe,
                settings=settings,
                parent_task_id=task_id,
                goal=goal,
                system_instruction=system_instruction,
                max_tool_rounds=settings.max_tool_rounds,
                shell_max_output_bytes=settings.shell_max_output_bytes,
                shell_timeout_sec=settings.shell_timeout_sec,
                stream_chunk_idle_timeout_sec=settings.stream_chunk_idle_timeout_sec,
                stream_leg_max_wall_sec=settings.stream_leg_max_wall_sec,
                rewire_after_tombstone=settings.rewire_after_tombstone,
                max_session_tokens=settings.max_session_tokens,
                debug_stream=settings.debug_stream,
                knowledge_feed_host_allowlist=settings.knowledge_feed_host_allowlist,
                knowledge_embeddings_enabled=settings.enable_knowledge_embeddings,
                knowledge_embedding_model=settings.knowledge_embedding_model,
                knowledge_embedding_dim=settings.knowledge_embedding_dim,
                knowledge_embedding_min_cosine=settings.knowledge_embedding_min_cosine,
                knowledge_tool_max_results=settings.knowledge_tool_max_results,
                knowledge_tool_excerpt_chars=settings.knowledge_tool_excerpt_chars,
            )
        else:
            ovr = orchestrate_turn_kwargs(
                orchestration_profile,
                base_max_tool_rounds=settings.max_tool_rounds,
                include_gsc_read_tools=settings.enable_gsc_read_tools,
                web_config=web_cfg,
            )
            eff_rounds = int(ovr.get("max_tool_rounds", settings.max_tool_rounds))
            eff_web = ovr.get("web_config", web_cfg)
            eff_gsc = bool(ovr.get("include_gsc_read_tools", settings.enable_gsc_read_tools))
            final = await orchestrate_turn(
                qe,
                session_id=task_id,
                user_text=goal,
                system_instruction=system_instruction,
                api_key=settings.gemini_api_key,
                model=settings.gemini_model,
                on_delta=None,
                shell_allowlist=shell_allowlist,
                max_tool_rounds=eff_rounds,
                shell_max_output_bytes=settings.shell_max_output_bytes,
                shell_timeout_sec=settings.shell_timeout_sec,
                stream_chunk_idle_timeout_sec=settings.stream_chunk_idle_timeout_sec,
                stream_leg_max_wall_sec=settings.stream_leg_max_wall_sec,
                rewire_after_tombstone=settings.rewire_after_tombstone,
                enable_memory_tools=settings.enable_memory_tools,
                memory_config=memory_tool_config or _memory_tool_config(settings),
                include_plan_tools=settings.enable_plan_tools,
                include_goal_recall_tool=settings.enable_goal_recall_tool,
                include_gsc_read_tools=eff_gsc,
                file_config=file_cfg or _file_tool_config(settings),
                max_session_tokens=settings.max_session_tokens,
                on_file_guard_violation=file_guard_audit_hook(
                    qe,
                    task_id,
                    enabled=settings.file_audit_denials,
                ),
                web_config=eff_web,
                enable_list_session_web_sources=settings.enable_web_sources_tool,
                include_knowledge_tools=settings.enable_knowledge_tools,
                knowledge_feed_host_allowlist=settings.knowledge_feed_host_allowlist,
                knowledge_embeddings_enabled=settings.enable_knowledge_embeddings,
                knowledge_embedding_model=settings.knowledge_embedding_model,
                knowledge_embedding_dim=settings.knowledge_embedding_dim,
                knowledge_embedding_min_cosine=settings.knowledge_embedding_min_cosine,
                knowledge_tool_max_results=settings.knowledge_tool_max_results,
                knowledge_tool_excerpt_chars=settings.knowledge_tool_excerpt_chars,
                debug_stream=settings.debug_stream,
                include_workflow_tools=settings.enable_workflow_tools,
                workflow_max_steps=settings.ada_max_task_steps,
                workflow_require_approval=settings.require_approval_for_enqueue,
            )
        await qe.update_task(
            task_id,
            status="completed",
            current_output=final,
        )
    except Exception as e:
        log.exception("task %s failed", task_id)
        await qe.update_task(
            task_id,
            status="failed",
            current_output=str(e),
        )
