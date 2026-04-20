"""Terminal chat — one `tasks` row per session (claude_logic + system_arch)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from ada.config import Settings
from ada.dream.run import run_dream_job
from ada.orchestrator import (
    SessionTokenLimitExceeded,
    file_guard_audit_hook,
    orchestrate_turn,
)
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
from ada.query_engine import TASK_KIND_CHAT, QueryEngine
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
            task_id = await qe.insert_task(
                "Interactive session", status="executing", task_kind=TASK_KIND_CHAT
            )
        else:
            existing = await qe.latest_cli_session_task_id()
            if existing is not None:
                task_id = existing
                await qe.update_task(task_id, status="executing")
            else:
                task_id = await qe.insert_task(
                    "Interactive session",
                    status="executing",
                    task_kind=TASK_KIND_CHAT,
                )

        allow = load_allowlist_exact_lines(settings.allowlist_path)
        soul = read_soul_text(settings.soul_path)
        master = read_text_file(settings.master_path)
        wakeup = read_text_file(settings.wakeup_path)
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
            worker_mode=False,
        )
        file_cfg = _file_tool_config(settings)
        web_cfg = build_web_tool_config(settings)

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
                    include_goal_recall_tool=settings.enable_goal_recall_tool,
                    file_config=file_cfg,
                    max_session_tokens=settings.max_session_tokens,
                    on_file_guard_violation=file_guard_audit_hook(
                        qe,
                        task_id,
                        enabled=settings.file_audit_denials,
                    ),
                    web_config=web_cfg,
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
                )
                print(flush=True)
                await qe.state_set(_boot_state_key(task_id), "1")
            except SessionTokenLimitExceeded as e:
                print(f"\n[boot error] {e}", file=sys.stderr)
                await qe.update_task(task_id, status="failed", current_output=str(e))
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
                    include_goal_recall_tool=settings.enable_goal_recall_tool,
                    file_config=file_cfg,
                    max_session_tokens=settings.max_session_tokens,
                    on_file_guard_violation=file_guard_audit_hook(
                        qe,
                        task_id,
                        enabled=settings.file_audit_denials,
                    ),
                    web_config=web_cfg,
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
                )
                await qe.update_task(
                    task_id,
                    status="executing",
                    current_output=final,
                )
                print()
            except SessionTokenLimitExceeded as e:
                print(f"\n[error] {e}", file=sys.stderr)
                await qe.update_task(
                    task_id,
                    status="failed",
                    current_output=str(e),
                )
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
