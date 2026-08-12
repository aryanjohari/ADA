"""Open loops — projects / promises / TODOs (FACTS)."""

from __future__ import annotations

import uuid
from typing import Any

import yaml

from ada.body.vitals import utc_now_iso
from ada.io.atomic import atomic_write_text, cleanup_orphan_tmps
from ada.io.paths import BodyFault, DataPaths, ada_data_mounted, require_ada_data


def _dump(obj: dict[str, Any]) -> str:
    return yaml.safe_dump(
        obj, sort_keys=False, allow_unicode=True, default_flow_style=False
    )


def _require(paths: DataPaths | None) -> DataPaths:
    p = paths or require_ada_data()
    if not ada_data_mounted(p.root):
        raise BodyFault(
            f"ada-data not mounted or missing at {p.root}; refusing durable writes"
        )
    return p


def _load(paths: DataPaths) -> dict[str, Any]:
    cleanup_orphan_tmps(paths.facts, "open_loops.yaml")
    if not paths.open_loops_yaml.is_file():
        return {"schema_version": 1, "loops": []}
    raw = yaml.safe_load(paths.open_loops_yaml.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return {"schema_version": 1, "loops": []}
    raw.setdefault("schema_version", 1)
    raw.setdefault("loops", [])
    if not isinstance(raw["loops"], list):
        raw["loops"] = []
    return raw


def ensure_open_loops(paths: DataPaths | None = None) -> dict[str, Any]:
    p = _require(paths)
    p.ensure_memory_dirs()
    data = _load(p)
    if not p.open_loops_yaml.is_file():
        atomic_write_text(p.open_loops_yaml, _dump(data))
    return data


def list_loops(
    *,
    paths: DataPaths | None = None,
    status: str | None = "open",
    limit: int = 50,
) -> list[dict[str, Any]]:
    p = paths or require_ada_data()
    data = _load(p)
    loops = list(data.get("loops") or [])
    if status:
        loops = [x for x in loops if x.get("status") == status]
    return loops[: max(0, limit)]


def upsert_loop(
    *,
    text: str | None = None,
    loop_id: str | None = None,
    status: str = "open",
    delete: bool = False,
    confirmed: bool = False,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    """Create/update an open loop. Delete requires confirmed=True."""
    p = _require(paths)
    p.ensure_memory_dirs()
    data = ensure_open_loops(p)
    loops: list[dict[str, Any]] = list(data.get("loops") or [])

    if delete:
        if not loop_id:
            raise ValueError("delete requires loop_id")
        if not confirmed:
            return {
                "ok": False,
                "needs_confirm": True,
                "outcome": "needs_confirm",
                "reason": "delete open_loop requires confirmation",
                "id": loop_id,
            }
        before = len(loops)
        loops = [x for x in loops if x.get("id") != loop_id]
        data["loops"] = loops
        atomic_write_text(p.open_loops_yaml, _dump(data))
        return {
            "ok": True,
            "outcome": "ok",
            "deleted": before - len(loops),
            "id": loop_id,
        }

    if loop_id:
        for item in loops:
            if item.get("id") == loop_id:
                if text is not None:
                    item["text"] = text
                item["status"] = status
                item["updated_at"] = utc_now_iso()
                data["loops"] = loops
                atomic_write_text(p.open_loops_yaml, _dump(data))
                return {"ok": True, "outcome": "ok", "loop": item}
        return {
            "ok": False,
            "outcome": "error",
            "error": f"open_loop id not found: {loop_id}",
        }

    if not text or not str(text).strip():
        raise ValueError("text required to create open_loop")
    item = {
        "id": uuid.uuid4().hex[:12],
        "text": str(text).strip(),
        "status": status,
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso(),
    }
    loops.append(item)
    data["loops"] = loops
    atomic_write_text(p.open_loops_yaml, _dump(data))
    return {"ok": True, "outcome": "ok", "loop": item}
