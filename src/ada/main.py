"""Async daemon: poll `pending` tasks and run one model turn per goal."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from ada.config import Settings, load_dotenv_if_present
from ada.orchestrator import orchestrate_turn
from ada.prompt import build_system_instruction, read_soul_text
from ada.query_engine import QueryEngine

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
    soul = read_soul_text(settings.soul_path)
    sys_instr = build_system_instruction(
        soul_text=soul,
        state_db_display_path=str(settings.state_db_path),
    )
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
