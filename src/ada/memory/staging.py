"""Dream FACT candidate staging queue (never auto-merge non-whitelist)."""

from __future__ import annotations

import json
import uuid
from typing import Any

from ada.body.vitals import utc_now_iso
from ada.io.atomic import atomic_write_text
from ada.io.paths import BodyFault, DataPaths, ada_data_mounted, require_ada_data


def _require(paths: DataPaths | None) -> DataPaths:
    p = paths or require_ada_data()
    if not ada_data_mounted(p.root):
        raise BodyFault(
            f"ada-data not mounted or missing at {p.root}; refusing durable writes"
        )
    return p


def stage_candidate(
    candidate: dict[str, Any],
    *,
    reason: str,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    """Write one staging JSON file under memory/staging/."""
    p = _require(paths)
    p.ensure_memory_dirs()
    sid = uuid.uuid4().hex[:12]
    payload = {
        "id": sid,
        "ts": utc_now_iso(),
        "reason": reason,
        "status": "pending",
        "candidate": candidate,
    }
    path = p.memory_staging / f"{sid}.json"
    atomic_write_text(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    return {"ok": True, "id": sid, "path": str(path), "reason": reason}


def list_staged(*, paths: DataPaths | None = None, limit: int = 50) -> list[dict[str, Any]]:
    p = paths or require_ada_data()
    if not p.memory_staging.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for path in sorted(p.memory_staging.glob("*.json"))[:limit]:
        try:
            out.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    return out
