"""Dream FACT candidate staging queue (never auto-merge non-whitelist)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
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


def _staging_path(sid: str, *, paths: DataPaths) -> Path:
    return paths.memory_staging / f"{sid}.json"


def get_staged(staging_id: str, *, paths: DataPaths | None = None) -> dict[str, Any]:
    p = _require(paths)
    sid = str(staging_id).strip()
    path = _staging_path(sid, paths=p)
    if not path.is_file():
        return {"ok": False, "error": f"staging id not found: {sid}"}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": f"staging unreadable: {exc}"}
    return {"ok": True, "staged": payload, "path": str(path)}


def _write_status(
    path: Path,
    payload: dict[str, Any],
    *,
    status: str,
    resolution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = dict(payload)
    payload["status"] = status
    payload["resolved_at"] = utc_now_iso()
    if resolution is not None:
        payload["resolution"] = resolution
    atomic_write_text(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    return payload


def confirm_staged(
    staging_id: str,
    *,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    """Operator confirm-once for a pending staging item (M11-B / M06).

    - ``dream_open_loop_proposal`` → ``upsert_loop`` with confirmed=True
      (gated done still goes through open_loops confirm policy).
    - FACT-like candidates → ``append_fact`` / ``propose_edit`` with confirm.
    Never auto-runs without this call.
    """
    p = _require(paths)
    got = get_staged(staging_id, paths=p)
    if not got.get("ok"):
        return got
    payload = got["staged"]
    path = Path(got["path"])
    if payload.get("status") != "pending":
        return {
            "ok": False,
            "error": f"staging not pending (status={payload.get('status')})",
            "id": staging_id,
        }

    reason = str(payload.get("reason") or "")
    cand = payload.get("candidate") if isinstance(payload.get("candidate"), dict) else {}

    if reason == "dream_open_loop_proposal":
        from ada.memory.open_loops import upsert_loop

        loop = cand.get("open_loop") if "open_loop" in cand else cand
        if not isinstance(loop, dict):
            loop = {"text": str(loop)}
        text = loop.get("text")
        if not text and not loop.get("id"):
            return {"ok": False, "error": "open_loop proposal missing text/id", "id": staging_id}
        result = upsert_loop(
            text=str(text) if text is not None else None,
            loop_id=str(loop["id"]) if loop.get("id") else None,
            status=str(loop["status"]) if loop.get("status") is not None else None,
            kind=str(loop["kind"]) if loop.get("kind") is not None else None,
            title=str(loop["title"]) if loop.get("title") is not None else None,
            confirmed=True,
            paths=p,
        )
        if result.get("needs_confirm"):
            # Still gated — keep pending with note; operator must supply receipt path later.
            return {
                "ok": False,
                "needs_confirm": True,
                "reason": result.get("reason"),
                "id": staging_id,
                "upsert": result,
            }
        if not result.get("ok"):
            return {"ok": False, "error": result.get("error") or "upsert failed", "id": staging_id}
        updated = _write_status(
            path, payload, status="confirmed", resolution={"upsert": result}
        )
        return {"ok": True, "outcome": "confirmed", "staged": updated, "upsert": result}

    # FACT / prefs style candidates
    from ada.memory.facts import propose_edit

    key = cand.get("key") or (
        f"prefs.{cand['field']}" if cand.get("field") else None
    )
    if not key:
        return {"ok": False, "error": "candidate missing key", "id": staging_id}
    value = cand.get("value")
    result = propose_edit(str(key), value, paths=p, confirmed=True)
    if not result.get("ok"):
        return {
            "ok": False,
            "error": result.get("reason") or result.get("error") or "fact confirm failed",
            "id": staging_id,
            "fact": result,
        }
    updated = _write_status(
        path, payload, status="confirmed", resolution={"fact": result}
    )
    return {"ok": True, "outcome": "confirmed", "staged": updated, "fact": result}


def reject_staged(
    staging_id: str,
    *,
    paths: DataPaths | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """Mark a pending staging item rejected (no FACT / open_loop mutation)."""
    p = _require(paths)
    got = get_staged(staging_id, paths=p)
    if not got.get("ok"):
        return got
    payload = got["staged"]
    path = Path(got["path"])
    if payload.get("status") != "pending":
        return {
            "ok": False,
            "error": f"staging not pending (status={payload.get('status')})",
            "id": staging_id,
        }
    updated = _write_status(
        path,
        payload,
        status="rejected",
        resolution={"reason": reason or "operator_reject"},
    )
    return {"ok": True, "outcome": "rejected", "staged": updated}
