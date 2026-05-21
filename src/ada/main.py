"""Async daemon: poll `pending` tasks or run the ``system_jobs`` job plane."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from ada.budget import daemon_should_execute_goal, maybe_log_daemon_block
from ada.config import Settings, load_dotenv_if_present
from ada.daemon_goal import execute_goal_daemon_turn
from ada.orchestration_profile import INTERACTIVE_FAST
from ada.prompt import (
    build_system_instruction,
    format_allowlist_summary,
    format_file_tools_note,
    format_knowledge_tools_note,
    format_schema_digest_note,
    format_session_web_sources_list_note,
    format_web_tools_note,
    read_soul_text,
    read_text_file,
)
from ada.query_engine import PendingGoalTask, QueryEngine
from ada.profile_runtime import enforce_profile_identity
from ada.tool_executor import (
    FileToolConfig,
    MemoryToolConfig,
    build_web_tool_config,
)
from ada.tools.shell_allowlist import load_allowlist_exact_lines


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


log = logging.getLogger("ada.daemon")

POLL_INTERVAL_SEC = 2.0


def _interaction_profile(settings: Settings):
    if settings.ada_interaction_profile == "interactive_fast":
        return INTERACTIVE_FAST
    return None


async def run_daemon_loop(settings: Settings) -> None:
    settings.ensure_data_dir()
    schema_path = Path(__file__).resolve().parent / "db" / "schema.sql"
    qe = QueryEngine(
        settings.state_db_path,
        schema_path,
        debounce_ms=settings.persist_debounce_ms,
    )
    await qe.connect()
    await enforce_profile_identity(qe, settings)
    allow = load_allowlist_exact_lines(settings.allowlist_path)
    soul = read_soul_text(settings.soul_path)
    master = read_text_file(settings.master_path)
    file_note = (
        format_file_tools_note(settings)
        if settings.enable_file_tools
        else None
    )
    web_note = (
        format_web_tools_note(settings)
        if settings.enable_web_tools
        else None
    )
    digest_note = format_schema_digest_note(
        read_text_file(settings.memory_dir / "schema_digest.md")
    )
    ws_list_note = format_session_web_sources_list_note(settings)
    knowledge_note = format_knowledge_tools_note(settings)
    sys_instr = build_system_instruction(
        soul_text=soul,
        master_text=master,
        state_db_display_path=str(settings.state_db_path),
        allowlist_summary=format_allowlist_summary(allow),
        file_tools_note=file_note,
        web_tools_note=web_note,
        schema_digest_note=digest_note,
        session_web_sources_list_note=ws_list_note,
        knowledge_tools_note=knowledge_note,
        worker_mode=True,
    )
    file_cfg = _file_tool_config(settings)
    web_cfg = build_web_tool_config(settings)
    mem_cfg = _memory_tool_config(settings)
    if not settings.gemini_api_key:
        log.error("GEMINI_API_KEY not set; daemon idle")
    try:
        if settings.ada_job_queue == "system_jobs":
            from ada.jobs.worker import run_system_jobs_plane_loop

            await run_system_jobs_plane_loop(
                qe,
                settings,
                system_instruction=sys_instr,
                shell_allowlist=allow,
                file_cfg=file_cfg,
                web_cfg=web_cfg,
                memory_cfg=mem_cfg,
            )
            return
        while True:
            pending: PendingGoalTask | None = await qe.fetch_pending_task()
            if not pending:
                await asyncio.sleep(POLL_INTERVAL_SEC)
                continue
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
            await execute_goal_daemon_turn(
                qe,
                settings,
                pending,
                system_instruction=sys_instr,
                shell_allowlist=allow,
                file_cfg=file_cfg,
                web_cfg=web_cfg,
                memory_tool_config=mem_cfg,
                orchestration_profile=_interaction_profile(settings),
            )
    finally:
        await qe.close()


def main_daemon() -> None:
    load_dotenv_if_present()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    settings = Settings.load()
    asyncio.run(run_daemon_loop(settings))
