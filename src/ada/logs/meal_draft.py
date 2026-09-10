"""Short-lived create-meal draft — scratch stash, not Dream (M26 library)."""

from __future__ import annotations

import json
import re
from typing import Any

from ada.body.vitals import utc_now_iso
from ada.io.atomic import atomic_write_text
from ada.io.paths import BodyFault, DataPaths, ada_data_mounted, require_ada_data

_ASK_START = "Type a food or paste a barcode (GTIN)?"
_ASK_NEXT = "Add another, or say done / save this meal?"
_ASK_NAME = "What should I call this meal?"


def _require(paths: DataPaths | None = None) -> DataPaths:
    p = paths or require_ada_data()
    if not ada_data_mounted(p.root):
        raise BodyFault("ADA data not mounted", code=2)
    p.scratch.mkdir(parents=True, exist_ok=True)
    return p


def draft_path(session_id: str, *, paths: DataPaths | None = None):
    sid = re.sub(r"[^a-zA-Z0-9_-]", "", (session_id or "").strip()) or "anon"
    return _require(paths).scratch / f"meal_draft_{sid}.json"


def load_draft(
    session_id: str, *, paths: DataPaths | None = None
) -> dict[str, Any] | None:
    path = draft_path(session_id, paths=paths)
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    if str(raw.get("status") or "") != "open":
        return None
    return raw


def _write_draft(
    session_id: str, draft: dict[str, Any], *, paths: DataPaths | None = None
) -> dict[str, Any]:
    path = draft_path(session_id, paths=paths)
    atomic_write_text(path, json.dumps(draft, indent=2, sort_keys=True) + "\n")
    return {**draft, "path": str(path)}


def clear_draft(session_id: str, *, paths: DataPaths | None = None) -> dict[str, Any]:
    path = draft_path(session_id, paths=paths)
    existed = path.is_file()
    if existed:
        path.unlink(missing_ok=True)
    return {"ok": True, "cleared": existed, "status": "closed"}


def start_draft(session_id: str, *, paths: DataPaths | None = None) -> dict[str, Any]:
    draft = {
        "schema_version": 1,
        "status": "open",
        "lines": [],
        "name": None,
        "opened_at": utc_now_iso(),
    }
    out = _write_draft(session_id, draft, paths=paths)
    return {
        "ok": True,
        "status": "open",
        "lines": [],
        "ask": _ASK_START,
        "path": out.get("path"),
    }


def append_draft_line(
    session_id: str,
    line: dict[str, Any],
    *,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    draft = load_draft(session_id, paths=paths)
    if not draft:
        return {"ok": False, "reason": "no_open_draft", "ask": "Say add a meal first."}
    lines = list(draft.get("lines") or [])
    clean = {
        k: v
        for k, v in line.items()
        if not str(k).startswith("_") and k in {
            "display_name",
            "ref_id",
            "preset_id",
            "serving_qty",
            "serving_unit",
            "serving_grams",
            "provenance",
            "nutrients",
            "snapshot_json",
            "barcode",
        }
    }
    if not clean.get("ref_id") and not clean.get("display_name"):
        return {"ok": False, "reason": "line_required"}
    lines.append(clean)
    draft["lines"] = lines
    draft["updated_at"] = utc_now_iso()
    out = _write_draft(session_id, draft, paths=paths)
    return {
        "ok": True,
        "status": "open",
        "line_count": len(lines),
        "lines": lines,
        "ask": _ASK_NEXT,
        "path": out.get("path"),
    }


def set_draft_name(
    session_id: str,
    name: str,
    *,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    draft = load_draft(session_id, paths=paths)
    if not draft:
        return {"ok": False, "reason": "no_open_draft"}
    draft["name"] = str(name or "").strip() or None
    out = _write_draft(session_id, draft, paths=paths)
    return {"ok": True, "name": draft["name"], "path": out.get("path")}


ASK_START = _ASK_START
ASK_NEXT = _ASK_NEXT
ASK_NAME = _ASK_NAME
