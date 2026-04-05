"""Terminal chat — one `tasks` row per session (claude_logic + system_arch)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from ada.config import Settings
from ada.orchestrator import orchestrate_turn
from ada.prompt import build_system_instruction, read_soul_text
from ada.query_engine import QueryEngine


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

        soul = read_soul_text(settings.soul_path)
        sys_instr = build_system_instruction(
            soul_text=soul,
            state_db_display_path=str(settings.state_db_path),
        )

        if not settings.gemini_api_key:
            print("Set GEMINI_API_KEY (see .env.example).", file=sys.stderr)
            return

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
