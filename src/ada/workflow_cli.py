"""`ada workflow` subcommands."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from ada.config import Settings
from ada.query_engine import QueryEngine
from ada.profile_runtime import enforce_profile_identity
from ada.workflow.enqueue import enqueue_workflow_via_tool, get_workflow_status_via_tool


async def run_workflow_enqueue_cli(
    settings: Settings,
    *,
    kind: str,
    goal: str,
    params_json: str | None,
    idempotency_key: str | None,
) -> int:
    settings.ensure_data_dir()
    schema_path = Path(__file__).resolve().parent / "db" / "schema.sql"
    qe = QueryEngine(
        settings.state_db_path,
        schema_path,
        debounce_ms=settings.persist_debounce_ms,
    )
    await qe.connect()
    await enforce_profile_identity(qe, settings)
    try:
        out = await enqueue_workflow_via_tool(
            qe,
            kind=kind,
            goal_text=goal,
            params_json=params_json,
            idempotency_key=idempotency_key,
            max_steps=settings.ada_max_task_steps,
            require_approval=settings.require_approval_for_enqueue,
        )
        if out.get("error"):
            print(out["error"], file=sys.stderr)
            return 1
        print(json.dumps(out, indent=2))
        return 0
    finally:
        await qe.close()


async def run_workflow_status_cli(settings: Settings, *, workflow_id: int) -> int:
    settings.ensure_data_dir()
    schema_path = Path(__file__).resolve().parent / "db" / "schema.sql"
    qe = QueryEngine(
        settings.state_db_path,
        schema_path,
        debounce_ms=settings.persist_debounce_ms,
    )
    await qe.connect()
    await enforce_profile_identity(qe, settings)
    try:
        out = await get_workflow_status_via_tool(qe, workflow_id=workflow_id)
        if out.get("error"):
            print(out["error"], file=sys.stderr)
            return 1
        print(json.dumps(out, indent=2, default=str))
        return 0
    finally:
        await qe.close()
