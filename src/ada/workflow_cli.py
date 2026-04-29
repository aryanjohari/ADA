"""`ada workflow` subcommands."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
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


async def run_workflow_retry_cli(
    settings: Settings,
    *,
    workflow_id: int,
    dry_run: bool,
    reason: str,
    duplicate_run: bool,
) -> int:
    """
    Reset a failed workflow for daemon resume (--dry-run previews only),
    or --duplicate-run: enqueue a new workflow clone (full re-run via idempotency key).
    """
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
        if duplicate_run:
            wf = await qe.get_workflow_by_id(workflow_id)
            if wf is None:
                print(f"no workflow with id={workflow_id}", file=sys.stderr)
                return 1
            pj = wf.get("params_json")
            params_json = (
                json.dumps(pj, ensure_ascii=False)
                if isinstance(pj, dict)
                else None
            )
            ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
            idem = f"wf-retry-{workflow_id}-{ts}"
            out = await enqueue_workflow_via_tool(
                qe,
                kind=str(wf.get("kind") or ""),
                goal_text=str(wf.get("goal_text") or ""),
                params_json=params_json,
                idempotency_key=idem,
                max_steps=settings.ada_max_task_steps,
                require_approval=settings.require_approval_for_enqueue,
            )
            if out.get("error"):
                print(out["error"], file=sys.stderr)
                return 1
            print(json.dumps(out, indent=2, default=str))
            return 0

        out = await qe.retry_failed_workflow(
            workflow_id,
            reason=reason.strip() if reason.strip() else "manual_retry",
            dry_run=dry_run,
        )
        if out.get("error"):
            print(out["error"], file=sys.stderr)
            return 1
        print(json.dumps(out, indent=2, default=str))
        return 0
    finally:
        await qe.close()
