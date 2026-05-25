"""Streamlit/operator HUD actions — apply programme and run skills outside chat turns."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ada.boot import kernel_boot
from ada.config import Settings
from ada.motor.execute import execute
from ada.primitives.catalog import PRIMITIVE_IDS
from ada.primitives.handlers import execute_primitive
from ada.motor.types import MotorRequest, MotorResult
from ada.motor.registry import SkillSpec, load_skill_registry
from ada.programme.apply import confirm_and_apply
from ada.programme.packet import ProgrammePacket
from ada.programme.packs import (
    PACK_SKILL_ALLOWLIST,
    normalize_skill_ids,
    resolve_pack,
)
from ada.query_engine import QueryEngine


def _schema_path() -> Path:
    import ada

    return Path(ada.__path__[0]) / "db" / "schema.sql"


def _motor_result_to_dict(result: MotorResult) -> dict[str, Any]:
    out: dict[str, Any] = {
        "ok": result.ok,
        "pending_approval": result.pending_approval,
    }
    if result.error:
        out["error"] = result.error
    if result.action_log_id is not None:
        out["action_log_id"] = result.action_log_id
    if result.output:
        out["output"] = result.output
    return out


async def hud_apply_programme(
    settings: Settings,
    packet_dict: dict[str, Any],
    *,
    approved: bool,
) -> dict[str, Any]:
    """Wrap programme.confirm_and_apply — Streamlit/CLI HUD only."""
    try:
        packet = ProgrammePacket.model_validate(packet_dict)
    except Exception as e:
        return {"ok": False, "error": f"invalid packet: {e}"}
    qe = QueryEngine(
        settings.state_db_path,
        _schema_path(),
        debounce_ms=settings.persist_debounce_ms,
    )
    await qe.connect()
    try:
        return await confirm_and_apply(
            qe, settings, packet, approved=approved, session_id=None
        )
    finally:
        await qe.close()


async def hud_kernel_summary(settings: Settings) -> dict[str, Any]:
    """Connect, kernel_boot, return mission hat ids — HUD sidebar (J3)."""
    qe = QueryEngine(
        settings.state_db_path,
        _schema_path(),
        debounce_ms=settings.persist_debounce_ms,
    )
    await qe.connect()
    try:
        kernel = await kernel_boot(qe, settings)
        return {"ok": True, **kernel.as_summary()}
    finally:
        await qe.close()


async def hud_run_primitive(
    settings: Settings,
    *,
    primitive_id: str,
    args: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Open QueryEngine, kernel_boot, execute_primitive — no chat task required (J3)."""
    pid = str(primitive_id or "").strip()
    if not pid:
        return {"ok": False, "error": "primitive_id required"}
    if pid not in PRIMITIVE_IDS:
        known = sorted(PRIMITIVE_IDS)
        return {
            "ok": False,
            "error": f"unknown primitive {pid!r}; known: {known}",
        }
    raw_args = args if isinstance(args, dict) else {}
    qe = QueryEngine(
        settings.state_db_path,
        _schema_path(),
        debounce_ms=settings.persist_debounce_ms,
    )
    await qe.connect()
    try:
        kernel = await kernel_boot(qe, settings)
        return await execute_primitive(
            qe, settings, pid, raw_args, kernel=kernel
        )
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    finally:
        await qe.close()


async def hud_run_skill(
    settings: Settings,
    *,
    skill_id: str,
    mission_slug: str,
    params: dict[str, Any] | None = None,
    approved: bool = False,
) -> dict[str, Any]:
    """Open QueryEngine, motor.execute layer=skill — no chat task required."""
    sid = str(skill_id or "").strip()
    slug = str(mission_slug or "").strip()
    if not sid:
        return {"ok": False, "error": "skill_id required"}
    if not slug:
        return {"ok": False, "error": "mission_slug required"}
    raw_params = params if isinstance(params, dict) else {}
    qe = QueryEngine(
        settings.state_db_path,
        _schema_path(),
        debounce_ms=settings.persist_debounce_ms,
    )
    await qe.connect()
    try:
        req = MotorRequest(
            layer="skill",
            id=sid,
            params=raw_params,
            mission_slug=slug,
            session_id=None,
            approved=approved,
        )
        result = await execute(req, settings=settings, qe=qe)
        return _motor_result_to_dict(result)
    finally:
        await qe.close()


def skills_for_mission_defaults(defaults: dict[str, Any]) -> list[SkillSpec]:
    """Skills selectable in Agent HUD for a mission (H5 pack + skills_enabled)."""
    registry = load_skill_registry()
    enabled = normalize_skill_ids(defaults.get("skills_enabled"))
    pack = resolve_pack(defaults)
    if enabled:
        ids = set(enabled)
        if pack and pack in PACK_SKILL_ALLOWLIST:
            ids &= PACK_SKILL_ALLOWLIST[pack]
        return [registry[sid] for sid in sorted(ids) if sid in registry]
    if pack and pack in PACK_SKILL_ALLOWLIST:
        return [
            registry[sid]
            for sid in sorted(PACK_SKILL_ALLOWLIST[pack])
            if sid in registry
        ]
    return [registry[sid] for sid in sorted(registry.keys())]


def parse_params_json(text: str) -> tuple[dict[str, Any] | None, str | None]:
    """Parse optional HUD params JSON; returns (params, error)."""
    raw = (text or "").strip()
    if not raw:
        return {}, None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        return None, str(e)
    if not isinstance(parsed, dict):
        return None, "params must be a JSON object"
    return parsed, None
