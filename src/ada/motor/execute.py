"""Unified motor execute — routes shell, motor_ada argv, and skills."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from ada.config import Settings, _find_project_root
from ada.motor.argv import build_op_argv
from ada.motor.registry import get_skill, load_shell_allowlist
from ada.motor.types import MotorRequest, MotorResult
from ada.motor.validate import validate_skill_for_mission, validate_skill_params
from ada.observability.operator_subprocess import run_ada
from ada.query_engine import TASK_KIND_GOAL, QueryEngine
from ada.tools.shell_allowlist import command_to_argv
from ada.workflow.enqueue import enqueue_workflow_via_tool

log = logging.getLogger("ada.motor")


async def execute(
    request: MotorRequest,
    *,
    settings: Settings,
    qe: QueryEngine,
) -> MotorResult:
    """Single motor ingress; logs action_log on success/failure."""
    try:
        if request.layer == "shell":
            result = await _execute_shell(request, settings=settings)
            kind = "motor_shell"
        elif request.layer == "motor_ada":
            result = _execute_motor_ada(request, settings=settings)
            kind = "motor_ada_argv"
        elif request.layer == "skill":
            result = await _execute_skill(request, settings=settings, qe=qe)
            kind = "motor_skill_run"
        else:
            return MotorResult(ok=False, error=f"unsupported layer {request.layer!r}")
    except ValueError as e:
        result = MotorResult(ok=False, error=str(e))
        kind = "motor_error"
    except Exception as e:
        log.exception("motor execute failed")
        result = MotorResult(ok=False, error=str(e))
        kind = "motor_error"

    log_id: int | None = None
    if not result.pending_approval:
        payload: dict[str, Any] = {
            "layer": request.layer,
            "id": request.id,
            "ok": result.ok,
        }
        if result.error:
            payload["error"] = result.error[:500]
        if isinstance(result.output, dict):
            payload["output_keys"] = list(result.output.keys())[:20]
        try:
            log_id = await qe.append_action_log(kind, payload, session_id=request.session_id)
        except Exception:
            log.warning("action_log append failed for motor", exc_info=True)
        result.action_log_id = log_id

    return result


async def _execute_shell(request: MotorRequest, *, settings: Settings) -> MotorResult:
    line = (request.shell_line or request.id or "").strip()
    allowlist = load_shell_allowlist(settings.memory_dir)
    if line not in allowlist:
        return MotorResult(ok=False, error="command not in shell allowlist")
    try:
        argv = command_to_argv(line)
    except ValueError as e:
        return MotorResult(ok=False, error=str(e))
    try:
        proc = await asyncio.create_subprocess_exec(
            argv[0],
            *argv[1:],
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        raw, _ = await asyncio.wait_for(proc.communicate(), timeout=60.0)
        text = raw.decode("utf-8", errors="replace")
        if len(text) > 64_000:
            text = text[:64_000] + "\n… truncated"
        return MotorResult(
            ok=proc.returncode == 0,
            output={"stdout": text, "exit_code": proc.returncode, "command": line},
            error=None if proc.returncode == 0 else f"exit {proc.returncode}",
        )
    except asyncio.TimeoutError:
        proc.kill()
        return MotorResult(ok=False, error="timeout")
    except Exception as e:
        return MotorResult(ok=False, error=str(e))


def _execute_motor_ada(request: MotorRequest, *, settings: Settings) -> MotorResult:
    cmd_id = request.id.strip()
    if cmd_id not in (
        "help",
        "mission_list",
        "mission_show",
        "goal_list",
        "workflow_status",
        "gate_failures",
        "mission_tick_dry_run",
        "matrix_scan_dry_run",
        "mission_init",
        "mission_migrate_env_dry",
    ):
        return MotorResult(ok=False, error=f"unknown motor_ada command {cmd_id!r}")
    ada_bin = (request.ada_bin or "ada").strip()
    kwargs = dict(request.argv_kwargs)
    kwargs.setdefault("mission_slug", request.mission_slug)
    try:
        argv = build_op_argv(ada_bin, command_id=cmd_id, **kwargs)  # type: ignore[arg-type]
    except ValueError as e:
        return MotorResult(ok=False, error=str(e))
    root = _find_project_root()
    run = run_ada(argv, cwd=root, timeout_sec=120.0)
    return MotorResult(
        ok=run.returncode == 0,
        output={
            "argv": argv,
            "returncode": run.returncode,
            "stdout": run.stdout,
            "stderr": run.stderr,
        },
        error=None if run.returncode == 0 else f"exit {run.returncode}",
    )


async def _execute_skill(
    request: MotorRequest,
    *,
    settings: Settings,
    qe: QueryEngine,
) -> MotorResult:
    spec = get_skill(request.id)
    if spec is None:
        return MotorResult(ok=False, error=f"unknown skill {request.id!r}")
    params = dict(request.params or {})
    err = validate_skill_params(spec, params, mission_slug=request.mission_slug)
    if err:
        return MotorResult(ok=False, error=err)
    err = await validate_skill_for_mission(qe, spec, request.mission_slug)
    if err:
        return MotorResult(ok=False, error=err)
    if spec.require_approval and not request.approved:
        return MotorResult(
            ok=False,
            pending_approval=True,
            error=f"skill {spec.id!r} requires operator approval",
            output={"skill_id": spec.id, "risk_tier": spec.risk_tier},
        )
    if spec.risk_tier == "high" and not request.approved:
        return MotorResult(
            ok=False,
            pending_approval=True,
            error=f"high-risk skill {spec.id!r} requires approved=true",
            output={"skill_id": spec.id},
        )

    slug = (request.mission_slug or "").strip() or None

    if spec.motor_type == "goal_add":
        goal_text = str(params.get("goal_text") or "").strip()
        if not goal_text and spec.id == "daily_brief":
            from ada.mission_control.digest import (
                goal_text_for_daily_brief,
                render_brief_from_settings,
            )

            goal_text = goal_text_for_daily_brief(
                render_brief_from_settings(settings, mission_slug=slug)
            )
        if not goal_text:
            return MotorResult(ok=False, error="goal_text required")
        mission_id: int | None = None
        if slug:
            row = await qe.get_mission_by_slug(slug)
            if row is None:
                return MotorResult(ok=False, error=f"no mission with slug {slug!r}")
            mission_id = int(row["id"])
        tid = await qe.insert_task(
            goal_text,
            status="pending",
            task_kind=TASK_KIND_GOAL,
            mission_id=mission_id,
        )
        return MotorResult(ok=True, output={"task_id": tid, "skill_id": spec.id})

    if spec.motor_type == "workflow_enqueue":
        playbook_id = spec.playbook_id
        wf_kind = spec.workflow_kind
        goal_text = str(params.get("goal_text") or f"skill:{spec.id}").strip()
        params_json = params.get("params_json")
        if isinstance(params_json, dict):
            params_json = json.dumps(params_json)
        elif params_json is not None:
            params_json = str(params_json)
        else:
            extra = {k: v for k, v in params.items() if k not in ("goal_text",)}
            params_json = json.dumps(extra) if extra else None
        out = await enqueue_workflow_via_tool(
            qe,
            kind=wf_kind or "",
            goal_text=goal_text,
            params_json=params_json,
            idempotency_key=str(params.get("idempotency_key") or "") or None,
            max_steps=settings.max_task_steps,
            require_approval=bool(params.get("require_approval", False)),
            playbook_id=playbook_id,
            mission_slug=slug,
        )
        if out.get("error"):
            return MotorResult(ok=False, error=str(out["error"]))
        return MotorResult(ok=True, output={**out, "skill_id": spec.id})

    if spec.motor_type == "ada_argv":
        op_id = spec.op_command_id or spec.id
        ada_bin = (request.ada_bin or "ada").strip()
        argv_kwargs: dict[str, Any] = dict(request.argv_kwargs)
        if slug:
            argv_kwargs.setdefault("mission_slug", slug)
        for k, v in params.items():
            argv_kwargs.setdefault(k, v)
        try:
            argv = build_op_argv(ada_bin, command_id=op_id, **argv_kwargs)  # type: ignore[arg-type]
        except ValueError as e:
            return MotorResult(ok=False, error=str(e))
        root = _find_project_root()
        run = run_ada(argv, cwd=root, timeout_sec=120.0)
        return MotorResult(
            ok=run.returncode == 0,
            output={"argv": argv, "returncode": run.returncode, "skill_id": spec.id},
            error=None if run.returncode == 0 else f"exit {run.returncode}",
        )

    return MotorResult(
        ok=False,
        error=f"skill {spec.id!r} motor_type {spec.motor_type!r} not implemented",
    )
