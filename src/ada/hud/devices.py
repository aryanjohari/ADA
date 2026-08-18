"""Thin HUD device registry — names + provenance, not a login (M19b v1.6).

One source of truth: facts/hud_devices.yaml (HUD-local write). Keep out of
Dream WHITELIST_KEYS. Cookie ada_hud_device is non-HttpOnly and is not the
HttpOnly ada_hud_session write-gate.
"""

from __future__ import annotations

import threading
import uuid
from pathlib import Path
from typing import Any

import yaml
from fastapi import Request, Response

from ada.body.vitals import utc_now_iso
from ada.hud.auth import cookie_secure
from ada.io.atomic import atomic_write_text, cleanup_orphan_tmps
from ada.io.paths import BodyFault, DataPaths, get_paths, require_ada_data

DEVICE_COOKIE = "ada_hud_device"
DEVICE_COOKIE_MAX_AGE = 60 * 60 * 24 * 400  # ~13 months
FACES = frozenset({"phone", "mac", "display"})
FACE_ALIASES = {
    "mac-chat": "mac",
    "mac-companion": "mac",
}
INPUT_KINDS = frozenset({"typed", "stt"})
_NAME_MAX = 64

_lock = threading.Lock()


def normalize_face(raw: str | None) -> str | None:
    """Return phone|mac|display, aliasing retired Mac face names. Else None."""
    if raw is None:
        return None
    v = str(raw).strip().lower()
    if not v:
        return None
    if v in FACE_ALIASES:
        return FACE_ALIASES[v]
    if v in FACES:
        return v
    return None


def normalize_input_kind(raw: str | None) -> str:
    v = (raw or "typed").strip().lower()
    if v in INPUT_KINDS:
        return v
    return "typed"


def parse_device_id(raw: str | None) -> str | None:
    if not raw:
        return None
    try:
        return str(uuid.UUID(str(raw).strip()))
    except (ValueError, AttributeError, TypeError):
        return None


def mint_device_id() -> str:
    return str(uuid.uuid4())


def resolve_device_id(*, cookie: str | None, body: str | None) -> tuple[str, bool]:
    """Cookie wins if both present and disagree. Returns (id, need_set_cookie)."""
    cid = parse_device_id(cookie)
    bid = parse_device_id(body)
    if cid:
        return cid, False
    if bid:
        return bid, True
    return mint_device_id(), True


def sanitize_device_name(raw: str | None) -> str | None:
    if raw is None:
        return None
    name = " ".join(str(raw).strip().split())
    if not name:
        return None
    name = "".join(ch for ch in name if ch.isprintable())
    name = name[:_NAME_MAX].strip() or None
    return name


def hud_devices_path(paths: DataPaths | None = None) -> Path:
    p = paths or get_paths()
    return p.hud_devices_yaml


def _empty_registry() -> dict[str, Any]:
    return {"schema_version": 1, "devices": []}


def load_registry(paths: DataPaths | None = None) -> dict[str, Any]:
    p = paths or get_paths()
    path = p.hud_devices_yaml
    cleanup_orphan_tmps(p.facts, "hud_devices.yaml")
    if not path.is_file():
        return _empty_registry()
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError:
        return _empty_registry()
    if not isinstance(raw, dict):
        return _empty_registry()
    devices = raw.get("devices")
    if not isinstance(devices, list):
        devices = []
    return {"schema_version": 1, "devices": devices}


def save_registry(data: dict[str, Any], paths: DataPaths | None = None) -> dict[str, Any]:
    p = require_ada_data(None if paths is None else paths.root)
    p.ensure_memory_dirs()
    cleanup_orphan_tmps(p.facts, "hud_devices.yaml")
    out = {
        "schema_version": 1,
        "devices": list(data.get("devices") or []),
    }
    atomic_write_text(
        p.hud_devices_yaml,
        yaml.safe_dump(out, sort_keys=False, allow_unicode=True, default_flow_style=False),
    )
    return out


def lookup_device(device_id: str, paths: DataPaths | None = None) -> dict[str, Any] | None:
    reg = load_registry(paths)
    for row in reg.get("devices") or []:
        if isinstance(row, dict) and str(row.get("id") or "") == device_id:
            return row
    return None


def upsert_device(
    device_id: str,
    *,
    name: str | None = None,
    face_hint: str | None = None,
    paths: DataPaths | None = None,
    touch: bool = True,
) -> dict[str, Any]:
    """Insert or update a named window. Unnamed ids still stamp. Names only."""
    did = parse_device_id(device_id)
    if not did:
        raise ValueError("device_id must be a uuid")
    face = normalize_face(face_hint)
    clean_name = sanitize_device_name(name)
    now = utc_now_iso()

    with _lock:
        p = paths or get_paths()
        require_ada_data(p.root)
        p.ensure_memory_dirs()
        reg = load_registry(p)
        devices = list(reg.get("devices") or [])
        found: dict[str, Any] | None = None
        for row in devices:
            if isinstance(row, dict) and str(row.get("id") or "") == did:
                found = row
                break
        if found is None:
            found = {"id": did, "created_at": now}
            devices.append(found)
        if clean_name is not None:
            found["name"] = clean_name
        if face is not None:
            found["face_hint"] = face
        if touch:
            found["last_seen_at"] = now
        reg["devices"] = devices
        save_registry(reg, p)
        return dict(found)


def set_device_cookie(response: Response, device_id: str) -> None:
    response.set_cookie(
        key=DEVICE_COOKIE,
        value=device_id,
        httponly=False,
        secure=cookie_secure(),
        samesite="lax",
        max_age=DEVICE_COOKIE_MAX_AGE,
        path="/",
    )


def read_device_cookie(request: Request) -> str | None:
    return parse_device_id(request.cookies.get(DEVICE_COOKIE))


def bind_device(
    request: Request,
    response: Response,
    *,
    body_id: str | None = None,
    name: str | None = None,
    face_hint: str | None = None,
    stamp: bool = True,
) -> dict[str, Any]:
    """Resolve cookie-over-body, optionally stamp FACT, Set-Cookie if needed."""
    device_id, need_cookie = resolve_device_id(
        cookie=request.cookies.get(DEVICE_COOKIE),
        body=body_id,
    )
    row: dict[str, Any] = {"id": device_id}
    if stamp:
        try:
            row = upsert_device(
                device_id,
                name=name,
                face_hint=face_hint,
                touch=True,
            )
        except (BodyFault, OSError, ValueError):
            row = lookup_device(device_id) or {"id": device_id}
    else:
        row = lookup_device(device_id) or {"id": device_id}
    if need_cookie or parse_device_id(request.cookies.get(DEVICE_COOKIE)) != device_id:
        set_device_cookie(response, device_id)
    return row
