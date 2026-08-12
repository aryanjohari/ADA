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
from ada.io.paths import BodyFault, get_paths
from ada.tools.body_tools import run_body_doctor

router = APIRouter(prefix="/api")

ModeName = Literal["observe", "agent", "plan"]


class LoginBody(BaseModel):
    password: str = Field(min_length=1)


class ChatBody(BaseModel):
    message: str = Field(min_length=1)
    mode: ModeName = "observe"


def _chat_service(request: Request):
    return request.app.state.chat


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
    try:
        paths = get_paths()
        if identity_mod.identity_exists(paths):
            card = identity_mod.load_identity(paths)
            identity = card.model_dump()
            born_at = card.born_at
        last_wake = lifecycle_mod.last_of_type("wake", paths)
        last_fault = lifecycle_mod.last_of_type("fault", paths)
    except BodyFault:
        pass
    return {
        "born_at": born_at,
        "identity": identity,
        "last_wake": last_wake.model_dump() if last_wake else None,
        "last_fault": last_fault.model_dump() if last_fault else None,
        "last_dream_at": None,
        "last_dream_status": "n/a",
        "push": "skipped",
    }


@router.get("/doctor")
def api_doctor() -> dict[str, Any]:
    return run_body_doctor()


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
