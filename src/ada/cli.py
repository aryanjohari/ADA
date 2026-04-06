"""Terminal chat — one `tasks` row per session (claude_logic + system_arch)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from ada.config import Settings
from ada.dream.run import run_dream_job
from ada.orchestrator import orchestrate_turn
from ada.prompt import (
    build_system_instruction,
    format_allowlist_summary,
    read_soul_text,
    read_text_file,
)
from ada.query_engine import QueryEngine
from ada.tool_executor import MemoryToolConfig
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


def _boot_state_key(task_id: int) -> str:
    return f"session.{task_id}.boot_complete"


async def run_chat(settings: Settings, *, new_session: bool) -> None:
    settings.ensure_data_dir()
    schema_path = Path(__file__).resolve().parent / "db" / "schema.sql"
    qe = QueryEngine(
        settings.state_db_path,
        schema_path,
        debounce_ms=settings.persist_debounce_ms,
    )
    await qe.connect()
    try:
        if new_session:
            task_id = await qe.insert_task("Interactive session", status="executing")
        else:
            existing = await qe.latest_cli_session_task_id()
            if existing is not None:
                task_id = existing
                await qe.update_task(task_id, status="executing")
            else:
                task_id = await qe.insert_task(
                    "Interactive session", status="executing"
                )

        allow = load_allowlist_exact_lines(settings.allowlist_path)
        soul = read_soul_text(settings.soul_path)
        master = read_text_file(settings.master_path)
        wakeup = read_text_file(settings.wakeup_path)
        sys_instr = build_system_instruction(
            soul_text=soul,
            master_text=master,
            state_db_display_path=str(settings.state_db_path),
            allowlist_summary=format_allowlist_summary(allow),
        )

        if not settings.gemini_api_key:
            print("Set GEMINI_API_KEY (see .env.example).", file=sys.stderr)
            return

        if await qe.state_get(_boot_state_key(task_id)) is None and wakeup.strip():
            print("Boot: running wakeup prompt once for this session…", flush=True)
            try:

                async def boot_on_delta(chunk: str) -> None:
                    print(chunk, end="", flush=True)

                await orchestrate_turn(
                    qe,
                    session_id=task_id,
                    user_text=wakeup.strip(),
                    system_instruction=sys_instr,
                    api_key=settings.gemini_api_key,
                    model=settings.gemini_model,
                    on_delta=boot_on_delta,
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
                )
                print(flush=True)
                await qe.state_set(_boot_state_key(task_id), "1")
            except Exception as e:
                print(f"\n[boot error] {e}", file=sys.stderr)

        print("ADA chat — empty line or Ctrl-D to exit.", flush=True)
        while True:
            try:
                line = input("you> ").strip()
            except EOFError:
                print()
                break
            if not line:
                break

            async def on_delta(chunk: str) -> None:
                print(chunk, end="", flush=True)

            try:
                final = await orchestrate_turn(
                    qe,
                    session_id=task_id,
                    user_text=line,
                    system_instruction=sys_instr,
                    api_key=settings.gemini_api_key,
                    model=settings.gemini_model,
                    on_delta=on_delta,
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
                )
                await qe.update_task(
                    task_id,
                    status="executing",
                    current_output=final,
                )
                print()
            except Exception as e:
                print(f"\n[error] {e}", file=sys.stderr)
                await qe.update_task(
                    task_id,
                    status="executing",
                    current_output=f"Error: {e}",
                )
    finally:
        await qe.close()


async def run_dream_cli(
    settings: Settings,
    *,
    session_id: int | None,
    dry_run: bool,
    max_messages: int,
) -> None:
    """Manual dream compression (invoke `ada dream`; schedule cron separately)."""
    settings.ensure_data_dir()
    schema_path = Path(__file__).resolve().parent / "db" / "schema.sql"
    qe = QueryEngine(
        settings.state_db_path,
        schema_path,
        debounce_ms=settings.persist_debounce_ms,
    )
    await qe.connect()
    try:
        out = await run_dream_job(
            qe,
            settings,
            session_id=session_id,
            dry_run=dry_run,
            max_messages=max_messages,
        )
        print(out)
    finally:
        await qe.close()
