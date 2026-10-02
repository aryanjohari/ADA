"""Jinja page routes for the five-pane HUD shell + organ faces."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ada.hud.devices import (
    DEVICE_COOKIE,
    normalize_face,
    resolve_device_id,
    set_device_cookie,
    upsert_device,
)
from ada.io.paths import BodyFault

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter()


def _stamp_device(request: Request, *, face_hint: str | None) -> tuple[str, bool]:
    device_id, need_cookie = resolve_device_id(
        cookie=request.cookies.get(DEVICE_COOKIE),
        body=None,
    )
    if need_cookie:
        try:
            upsert_device(device_id, face_hint=face_hint, touch=True)
        except (BodyFault, OSError, ValueError):
            pass
    return device_id, need_cookie


@router.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    face = normalize_face(request.query_params.get("face"))
    device_id, need_cookie = _stamp_device(request, face_hint=face)
    resp = templates.TemplateResponse(
        request,
        "index.html",
        {"title": "ADA HUD", "face": face or ""},
    )
    if need_cookie or request.cookies.get(DEVICE_COOKIE) != device_id:
        set_device_cookie(resp, device_id)
    return resp
