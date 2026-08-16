"""JSON APIs for vitals, lifecycle, doctor, mode, run tail, chat, auth."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from ada.body import identity as identity_mod
from ada.body import lifecycle as lifecycle_mod
from ada.body.vitals import collect_vitals, urgent_faults
from ada.dream.run import dream_status
from ada.hud.auth import (
    HudAuthError,
    clear_session_cookie,
    load_hud_secrets,
    mode_payload,
    passwords_match,
    require_agent_session,
    set_session_cookie,
)
from ada.hud.stream_bridge import run_with_bridge
from ada.hud.today import build_today
from ada.hud.xray import XrayError, list_entries, read_file
from ada.io.paths import BodyFault, DataPaths, get_paths
from ada.tools.body_tools import run_body_doctor

router = APIRouter(prefix="/api")

ModeName = Literal["observe", "agent", "plan"]


class LoginBody(BaseModel):
    password: str = Field(min_length=1)


class ChatBody(BaseModel):
    message: str = Field(min_length=1)
    mode: ModeName = "observe"


class ConfirmBody(BaseModel):
    tool: str = Field(min_length=1)
    args: dict[str, Any] = Field(default_factory=dict)
    pending_id: str | None = None


class PlanStepBody(BaseModel):
    text: str = Field(min_length=1)
    id: str | None = None


class PlanAcceptBody(BaseModel):
    plan_id: str | None = None
    steps: list[PlanStepBody] = Field(default_factory=list)
    raw_text: str | None = None


# Tools whose schemas accept confirmed=true (Consent Integrity re-drive).
_CONFIRMABLE_TOOLS = frozenset(
    {
        "memory_facts_propose_edit",
        "memory_facts_append",
        "memory_open_loops_upsert",
        "artifact_write",
    }
)


def _chat_service(request: Request):
    return request.app.state.chat


def _lifecycle_dream_fields(paths: DataPaths) -> dict[str, Any]:
    """HUD dream chips from dream_status — never invent S3 success."""
    status = dream_status(paths=paths)
    last_ok = status.get("last_dream_ok")
    last_fail = status.get("last_dream_fail")
    last_dream_at: str | None = None
    last_dream_status = "n/a"
    # Prefer latest by ts; ties / only-ok → dream_ok.
    if last_ok and last_fail:
        if str(last_ok.get("ts") or "") >= str(last_fail.get("ts") or ""):
            last_dream_at = last_ok.get("ts")
            last_dream_status = "dream_ok"
        else:
            last_dream_at = last_fail.get("ts")
            last_dream_status = "dream_fail"
    elif last_ok:
        last_dream_at = last_ok.get("ts")
        last_dream_status = "dream_ok"
    elif last_fail:
        last_dream_at = last_fail.get("ts")
        last_dream_status = "dream_fail"
    push = status.get("push") or "skipped"
    push_reason = None
    if isinstance(last_ok, dict):
        receipts = last_ok.get("receipts") or {}
        if isinstance(receipts, dict):
            push_reason = receipts.get("push_reason")
    out: dict[str, Any] = {
        "last_dream_at": last_dream_at,
        "last_dream_status": last_dream_status,
        "push": push,
    }
    if push_reason:
        out["push_reason"] = push_reason
    return out


@router.get("/vitals")
def api_vitals() -> dict[str, Any]:
    snap = collect_vitals()
    return {
        "vitals": snap.model_dump(),
        "urgent_faults": urgent_faults(snap),
    }


@router.get("/lifecycle")
def api_lifecycle() -> dict[str, Any]:
    identity = None
    last_wake = None
    last_fault = None
    born_at = None
    dream_fields: dict[str, Any] = {
        "last_dream_at": None,
        "last_dream_status": "n/a",
        "push": "skipped",
    }
    try:
        paths = get_paths()
        if identity_mod.identity_exists(paths):
            card = identity_mod.load_identity(paths)
            identity = card.model_dump()
            born_at = card.born_at
        last_wake = lifecycle_mod.last_of_type("wake", paths)
        last_fault = lifecycle_mod.last_of_type("fault", paths)
        dream_fields = _lifecycle_dream_fields(paths)
    except BodyFault:
        pass
    return {
        "born_at": born_at,
        "identity": identity,
        "last_wake": last_wake.model_dump() if last_wake else None,
        "last_fault": last_fault.model_dump() if last_fault else None,
        **dream_fields,
    }


@router.get("/doctor")
def api_doctor() -> dict[str, Any]:
    return run_body_doctor()


@router.get("/today")
def api_today(request: Request) -> dict[str, Any]:
    """Today strip — dues, reminds, pending Confirm/Plan, shelf heads (M16)."""
    chat = _chat_service(request)
    pending = [
        {
            "pending_id": pid,
            "tool": meta.get("tool"),
            "args_keys": sorted((meta.get("args") or {}).keys()),
        }
        for pid, meta in (chat.pending_confirms or {}).items()
    ]
    try:
        return build_today(
            pending_confirms=pending,
            last_plan=chat.last_plan,
        )
    except BodyFault as exc:
        return {
            "ok": False,
            "error": exc.message,
            "due_todos": [],
            "remind_soon": [],
            "pending_confirms": pending,
            "plan_sticky": None,
            "artifacts": [],
            "overnight": [],
            "continuity": None,
        }


@router.get("/mode")
def api_mode(request: Request) -> dict[str, Any]:
    chat = _chat_service(request)
    return mode_payload(
        request,
        mode=chat.current_mode(),
        last_denials=chat.last_denials,
    )


def _latest_run_path(explicit: Path | None = None) -> Path | None:
    if explicit is not None and explicit.is_file():
        return explicit
    runs_root = get_paths().runs
    if not runs_root.is_dir():
        return None
    candidates: list[Path] = []
    for day in sorted(runs_root.iterdir(), reverse=True):
        if not day.is_dir():
            continue
        for f in day.glob("*.jsonl"):
            candidates.append(f)
        if candidates:
            break
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _tail_jsonl(path: Path, n: int) -> list[dict[str, Any]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    out: list[dict[str, Any]] = []
    for line in lines[-n:]:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            out.append({"type": "parse_error", "raw": line[:500]})
    return out


@router.get("/run/tail")
def api_run_tail(request: Request, n: int = 80) -> dict[str, Any]:
    n = max(1, min(int(n), 500))
    chat = _chat_service(request)
    path = _latest_run_path(chat.run_path())
    if path is None:
        return {"path": None, "records": [], "n": n}
    return {"path": str(path), "records": _tail_jsonl(path, n), "n": n}


@router.post("/login", response_model=None)
def api_login(body: LoginBody) -> JSONResponse:
    try:
        cfg = load_hud_secrets()
    except HudAuthError as exc:
        return JSONResponse(
            status_code=503,
            content={"error": "secrets_missing", "message": exc.message},
        )
    if not passwords_match(cfg.password, body.password):
        return JSONResponse(
            status_code=401,
            content={"error": "bad_password", "message": "invalid password"},
        )
    resp = JSONResponse(content={"ok": True, "auth": "session"})
    set_session_cookie(resp, cfg.session_secret)
    return resp


@router.post("/logout", response_model=None)
def api_logout() -> JSONResponse:
    resp = JSONResponse(content={"ok": True, "auth": "mesh"})
    clear_session_cookie(resp)
    return resp


@router.get("/xray/list", response_model=None)
def api_xray_list(root: str = "memory", path: str = "") -> dict[str, Any] | JSONResponse:
    """Observe-only allowlisted directory list (M13 P2)."""
    try:
        return list_entries(root, path)
    except XrayError as exc:
        return JSONResponse(
            status_code=exc.status,
            content={"error": exc.code, "message": exc.message},
        )


@router.get("/xray/read", response_model=None)
def api_xray_read(
    root: str = "memory",
    path: str = "",
    max_bytes: int = 262144,
) -> dict[str, Any] | JSONResponse:
    """Observe-only allowlisted file read with size cap (M13 P2)."""
    try:
        return read_file(root, path, max_bytes=max_bytes)
    except XrayError as exc:
        return JSONResponse(
            status_code=exc.status,
            content={"error": exc.code, "message": exc.message},
        )


@router.post("/chat", response_model=None)
def api_chat(request: Request, body: ChatBody) -> StreamingResponse | JSONResponse:
    gate = require_agent_session(request, body.mode)
    if gate is not None:
        return gate

    chat = _chat_service(request)
    message = body.message.strip()
    mode = body.mode

    def worker(sink):
        return chat.run_user_turn(message, mode=mode, sink=sink)

    return StreamingResponse(
        run_with_bridge(worker),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/confirm", response_model=None)
def api_confirm(request: Request, body: ConfirmBody) -> JSONResponse:
    """Operator Confirm — re-execute gateway tool with confirmed=true (no cortex)."""
    gate = require_agent_session(request, "agent")
    if gate is not None:
        return gate

    tool = body.tool.strip()
    if tool not in _CONFIRMABLE_TOOLS:
        return JSONResponse(
            status_code=400,
            content={
                "error": "confirm_not_wired",
                "message": (
                    f"confirm path not wired for tool '{tool}' "
                    "(deny only; no fake success)"
                ),
                "tool": tool,
            },
        )

    chat = _chat_service(request)
    try:
        obs = chat.confirm_tool(
            tool,
            dict(body.args or {}),
            pending_id=body.pending_id,
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={"error": "confirm_bind_failed", "message": str(exc)},
        )
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            status_code=500,
            content={"error": "confirm_failed", "message": str(exc)},
        )
    return JSONResponse(content={"ok": True, "observation": obs})


@router.post("/plan/accept", response_model=None)
def api_plan_accept(request: Request, body: PlanAcceptBody) -> JSONResponse:
    """Accept a Plan artifact — upsert kind:todo steps (no cortex write tools)."""
    gate = require_agent_session(request, "agent")
    if gate is not None:
        return gate

    steps = [{"text": s.text, "id": s.id} for s in body.steps if s.text.strip()]
    if not steps and body.raw_text and body.raw_text.strip():
        steps = [{"text": body.raw_text.strip()}]
    if not steps:
        return JSONResponse(
            status_code=400,
            content={
                "error": "plan_empty",
                "message": "plan accept requires steps or raw_text",
            },
        )

    chat = _chat_service(request)
    try:
        result = chat.accept_plan(
            steps=steps,
            plan_id=body.plan_id,
            raw_text=body.raw_text,
        )
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            status_code=500,
            content={"error": "plan_accept_failed", "message": str(exc)},
        )
    return JSONResponse(content={"ok": True, **result})
