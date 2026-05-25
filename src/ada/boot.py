"""Kernel boot: base_ops + ada_ops mission hats and memory source cache."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ada.config import Settings
from ada.mission_cli import load_mission_template
from ada.programme.apply import apply_packet
from ada.programme.packet import ProgrammePacket
from ada.query_engine import QueryEngine

KERNEL_MISSION_IDS_KEY = "ada.kernel.mission_ids_json"
KERNEL_MEMORY_SOURCE_KEY = "ada.kernel.memory_source.base_ops"
BASE_OPS_SLUG = "base_ops"
ADA_OPS_SLUG = "ada_ops"
LEGACY_OPS_SLUG = "jarvis-ops"
MEMORY_SOURCE_LABEL = "base_memory"
MEMORY_SOURCE_URL = "ada://memory/base"

_KERNEL_CACHE: MissionKernel | None = None


@dataclass(frozen=True)
class MissionKernel:
    base_ops_id: int
    ada_ops_id: int
    memory_source_id: int

    def as_summary(self) -> dict[str, Any]:
        return {
            "base_ops_id": self.base_ops_id,
            "ada_ops_id": self.ada_ops_id,
            "memory_source_id": self.memory_source_id,
        }


def _invalidate_kernel_cache() -> None:
    global _KERNEL_CACHE
    _KERNEL_CACHE = None


async def _migrate_jarvis_ops_slug(qe: QueryEngine) -> None:
    """Rename jarvis-ops → ada_ops when ada_ops row is absent (one-time greenfield path)."""
    legacy = await qe.get_mission_by_slug(LEGACY_OPS_SLUG)
    if legacy is None:
        return
    existing = await qe.get_mission_by_slug(ADA_OPS_SLUG)
    if existing is not None:
        return
    await qe.rename_mission_slug(LEGACY_OPS_SLUG, ADA_OPS_SLUG)


async def _ensure_mission_from_template(
    qe: QueryEngine,
    settings: Settings,
    template_name: str,
) -> int:
    data = load_mission_template(template_name)
    packet = ProgrammePacket.model_validate(data)
    out = await apply_packet(qe, settings, packet)
    if not out.get("ok"):
        raise RuntimeError(
            f"kernel_boot: apply {template_name!r} failed: {out.get('error')}"
        )
    return int(out["mission_id"])


async def kernel_boot(qe: QueryEngine, settings: Settings) -> MissionKernel:
    """
    Idempotent kernel ensure:
    - missions base_ops + ada_ops (from templates)
    - knowledge source ada://memory/base on base_ops
    - state cache keys for mission ids and memory source
    """
    _invalidate_kernel_cache()
    await _migrate_jarvis_ops_slug(qe)
    base_ops_id = await _ensure_mission_from_template(qe, settings, "base_ops")
    ada_ops_id = await _ensure_mission_from_template(qe, settings, "ada_ops")
    memory_source_id = await qe.ensure_knowledge_source(
        "web",
        label=MEMORY_SOURCE_LABEL,
        base_url=MEMORY_SOURCE_URL,
        mission_id=base_ops_id,
    )
    ids_payload = json.dumps(
        {BASE_OPS_SLUG: base_ops_id, ADA_OPS_SLUG: ada_ops_id},
        ensure_ascii=False,
    )
    await qe.state_set(KERNEL_MISSION_IDS_KEY, ids_payload)
    await qe.state_set(KERNEL_MEMORY_SOURCE_KEY, str(memory_source_id))
    kernel = MissionKernel(
        base_ops_id=base_ops_id,
        ada_ops_id=ada_ops_id,
        memory_source_id=memory_source_id,
    )
    global _KERNEL_CACHE
    _KERNEL_CACHE = kernel
    return kernel


def _default_schema_path() -> Path:
    import ada

    return Path(ada.__path__[0]) / "db" / "schema.sql"


async def get_kernel(settings: Settings) -> MissionKernel:
    """Process cache; cold-load from state when boot has run in this DB."""
    global _KERNEL_CACHE
    if _KERNEL_CACHE is not None:
        return _KERNEL_CACHE
    qe = QueryEngine(
        settings.state_db_path,
        _default_schema_path(),
        debounce_ms=settings.persist_debounce_ms,
    )
    await qe.connect()
    try:
        raw_ids = await qe.state_get(KERNEL_MISSION_IDS_KEY)
        raw_mem = await qe.state_get(KERNEL_MEMORY_SOURCE_KEY)
        if raw_ids is None or raw_mem is None:
            raise RuntimeError(
                "kernel not booted — run `ada boot` or call kernel_boot() first"
            )
        ids = json.loads(raw_ids)
        base_ops_id = int(ids[BASE_OPS_SLUG])
        ada_ops_id = int(ids[ADA_OPS_SLUG])
        memory_source_id = int(raw_mem)
        _KERNEL_CACHE = MissionKernel(
            base_ops_id=base_ops_id,
            ada_ops_id=ada_ops_id,
            memory_source_id=memory_source_id,
        )
        return _KERNEL_CACHE
    finally:
        await qe.close()


def warm_kernel_cache(kernel: MissionKernel) -> None:
    """Test helper: set process cache without opening a new connection."""
    global _KERNEL_CACHE
    _KERNEL_CACHE = kernel


async def run_boot_cli(settings: Settings) -> int:
    """CLI entry: connect, kernel_boot, print summary."""
    settings.ensure_data_dir()
    schema_path = _default_schema_path()
    qe = QueryEngine(
        settings.state_db_path,
        schema_path,
        debounce_ms=settings.persist_debounce_ms,
    )
    await qe.connect()
    try:
        from ada.profile_runtime import enforce_profile_identity

        await enforce_profile_identity(qe, settings)
        kernel = await kernel_boot(qe, settings)
        summary = kernel.as_summary()
        print(
            "kernel boot ok:"
            f" base_ops_id={summary['base_ops_id']}"
            f" ada_ops_id={summary['ada_ops_id']}"
            f" memory_source_id={summary['memory_source_id']}"
        )
        return 0
    finally:
        await qe.close()
