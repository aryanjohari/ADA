"""Async daemon: poll `pending` tasks and run one model turn per goal."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from ada.config import Settings, load_dotenv_if_present
from ada.orchestrator import file_guard_audit_hook, orchestrate_turn
from ada.prompt import (
    build_system_instruction,
    format_allowlist_summary,
    format_file_tools_note,
    read_soul_text,
    read_text_file,
)
from ada.query_engine import QueryEngine
from ada.tool_executor import FileToolConfig, MemoryToolConfig
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


async def run_daemon_loop(settings: Settings) -> None:
    settings.ensure_data_dir()
    schema_path = Path(__file__).resolve().parent / "db" / "schema.sql"
    qe = QueryEngine(
        settings.state_db_path,
        schema_path,
        debounce_ms=settings.persist_debounce_ms,
    )
    await qe.connect()
    allow = load_allowlist_exact_lines(settings.allowlist_path)
    soul = read_soul_text(settings.soul_path)
    master = read_text_file(settings.master_path)
    file_note = (
        format_file_tools_note(settings)
        if settings.enable_file_tools
        else None
    )
    sys_instr = build_system_instruction(
        soul_text=soul,
        master_text=master,
        state_db_display_path=str(settings.state_db_path),
        allowlist_summary=format_allowlist_summary(allow),
        file_tools_note=file_note,
        worker_mode=True,
    )
    file_cfg = _file_tool_config(settings)
    if not settings.gemini_api_key:
        log.error("GEMINI_API_KEY not set; daemon idle")
    try:
        while True:
            pending = await qe.fetch_pending_task()
            if not pending:
                await asyncio.sleep(POLL_INTERVAL_SEC)
                continue
            task_id, goal = pending
            if not settings.gemini_api_key:
                await asyncio.sleep(POLL_INTERVAL_SEC)
                continue
            await qe.update_task(task_id, status="executing")
            try:
                final = await orchestrate_turn(
                    qe,
                    session_id=task_id,
                    user_text=goal,
                    system_instruction=sys_instr,
                    api_key=settings.gemini_api_key,
                    model=settings.gemini_model,
                    on_delta=None,
                    shell_allowlist=allow,
                    max_tool_rounds=settings.max_tool_rounds,
                    shell_max_output_bytes=settings.shell_max_output_bytes,
                    shell_timeout_sec=settings.shell_timeout_sec,
                    stream_chunk_idle_timeout_sec=settings.stream_chunk_idle_timeout_sec,
                    stream_leg_max_wall_sec=settings.stream_leg_max_wall_sec,
                    rewire_after_tombstone=settings.rewire_after_tombstone,
                    enable_memory_tools=settings.enable_memory_tools,
                    memory_config=_memory_tool_config(settings),
                    include_plan_tools=settings.enable_plan_tools,
                    file_config=file_cfg,
                    max_session_tokens=settings.max_session_tokens,
                    on_file_guard_violation=file_guard_audit_hook(
                        qe,
                        task_id,
                        enabled=settings.file_audit_denials,
                    ),
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
