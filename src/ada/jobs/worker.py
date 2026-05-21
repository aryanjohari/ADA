"""Claim and run ``system_jobs`` (compare-and-set + lease)."""

from __future__ import annotations

import asyncio
import logging
import os
import socket
from typing import TYPE_CHECKING, Any

from ada.budget import daemon_should_execute_goal, maybe_log_daemon_block
from ada.daemon_goal import execute_goal_daemon_turn
from ada.persistent.store import PersistentState

if TYPE_CHECKING:
    from ada.config import Settings
    from ada.query_engine import QueryEngine

log = logging.getLogger("ada.jobs.worker")

POLL_INTERVAL_SEC = 2.0


def _default_worker_id() -> str:
    return f"{socket.gethostname()}:{os.getpid()}"


async def _handle_goal_run_turn(
    job: dict[str, Any],
    qe: QueryEngine,
    settings: Settings,
    *,
    worker_id: str,
    system_instruction: str,
    shell_allowlist: frozenset[str],
    file_cfg: Any,
    web_cfg: Any,
    memory_cfg: Any,
) -> None:
    payload = job.get("payload_json") or {}
    tid = int(payload.get("task_id") or 0)
    gen = int(payload.get("turn_generation") or 0)
    if tid <= 0 or gen <= 0:
        raise ValueError("goal.run_turn: invalid payload task_id/turn_generation")
    row = await qe.get_goal_task(tid)
    if str(row.get("status") or "") != "pending":
        log.info("goal.run_turn stale: task %s status=%s", tid, row.get("status"))
        return
    cur_gen = await qe.get_task_goal_dispatch_generation(tid)
    if cur_gen != gen:
        log.info(
            "goal.run_turn stale generation: task %s job_gen=%s task_gen=%s",
            tid,
            gen,
            cur_gen,
        )
        return
    from ada.query_engine import PendingGoalTask  # noqa: PLC0415

    pending = PendingGoalTask(
        task_id=tid,
        goal=str(row["goal"]),
        mission_id=row.get("mission_id"),
        mission_slug=row.get("mission_slug"),
    )
    await execute_goal_daemon_turn(
        qe,
        settings,
        pending,
        system_instruction=system_instruction,
        shell_allowlist=shell_allowlist,
        file_cfg=file_cfg,
        web_cfg=web_cfg,
        memory_tool_config=memory_cfg,
        action_log_kind="system_job_goal_run_turn",
    )


async def _handle_noop(job: dict[str, Any]) -> None:
    log.debug("noop job %s payload=%s", job.get("id"), job.get("payload_json"))


async def dispatch_system_job(
    job: dict[str, Any],
    qe: QueryEngine,
    settings: Settings,
    *,
    worker_id: str,
    system_instruction: str,
    shell_allowlist: frozenset[str],
    file_cfg: Any,
    web_cfg: Any,
    memory_cfg: Any,
) -> None:
    kind = str(job.get("kind") or "")
    if kind == PersistentState.SYSTEM_JOB_KIND_NOOP_PING:
        await _handle_noop(job)
        return
    if kind == PersistentState.SYSTEM_JOB_KIND_GOAL_RUN_TURN:
        await _handle_goal_run_turn(
            job,
            qe,
            settings,
            worker_id=worker_id,
            system_instruction=system_instruction,
            shell_allowlist=shell_allowlist,
            file_cfg=file_cfg,
            web_cfg=web_cfg,
            memory_cfg=memory_cfg,
        )
        return
    if kind == PersistentState.SYSTEM_JOB_KIND_WORKFLOW_START:
        from ada.jobs.handlers import handle_workflow_start  # noqa: PLC0415

        await handle_workflow_start(job, qe, settings, worker_id=worker_id)
        return
    if kind == PersistentState.SYSTEM_JOB_KIND_INGEST_RUN:
        from ada.jobs.handlers import handle_ingest_run  # noqa: PLC0415

        await handle_ingest_run(job, qe, settings, worker_id=worker_id)
        return
    if kind == PersistentState.SYSTEM_JOB_KIND_TICK_GSC_KEYWORD:
        from ada.jobs.handlers import handle_tick_gsc_keyword_publish  # noqa: PLC0415

        await handle_tick_gsc_keyword_publish(job, qe, settings, worker_id=worker_id)
        return
    if kind == PersistentState.SYSTEM_JOB_KIND_MATRIX_SCAN:
        from ada.jobs.handlers import handle_matrix_scan  # noqa: PLC0415

        await handle_matrix_scan(job, qe, settings, worker_id=worker_id)
        return
    raise ValueError(f"unknown system_jobs.kind: {kind!r}")


async def run_system_jobs_plane_loop(
    qe: QueryEngine,
    settings: Settings,
    *,
    system_instruction: str,
    shell_allowlist: frozenset[str],
    file_cfg: Any,
    web_cfg: Any,
    memory_cfg: Any,
) -> None:
    worker_id = _default_worker_id()
    lease = settings.system_job_lease_seconds
    if not settings.gemini_api_key:
        log.error("GEMINI_API_KEY not set; job plane idle")
    while True:
        if not settings.gemini_api_key:
            await asyncio.sleep(POLL_INTERVAL_SEC)
            continue
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
            await asyncio.sleep(POLL_INTERVAL_SEC)
            continue
        await qe.ensure_pending_goal_system_jobs()
        job = await qe.claim_next_system_job(worker_id, lease_seconds=lease)
        if job is None:
            await asyncio.sleep(POLL_INTERVAL_SEC)
            continue
        jid = int(job["id"])
        try:
            await dispatch_system_job(
                job,
                qe,
                settings,
                worker_id=worker_id,
                system_instruction=system_instruction,
                shell_allowlist=shell_allowlist,
                file_cfg=file_cfg,
                web_cfg=web_cfg,
                memory_cfg=memory_cfg,
            )
            await qe.complete_system_job(jid, worker_id)
        except Exception as e:
            log.exception("system_job %s failed", jid)
            await qe.fail_system_job(jid, worker_id, str(e), terminal=True)
