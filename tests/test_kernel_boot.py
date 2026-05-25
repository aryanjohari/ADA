"""J0: kernel_boot idempotency, state keys, missions, memory source."""

from __future__ import annotations

import json

import pytest

from ada.boot import (
    ADA_OPS_SLUG,
    BASE_OPS_SLUG,
    KERNEL_MEMORY_SOURCE_KEY,
    KERNEL_MISSION_IDS_KEY,
    MEMORY_SOURCE_LABEL,
    MEMORY_SOURCE_URL,
    _invalidate_kernel_cache,
    get_kernel,
    kernel_boot,
)
from ada.programme.packet import ProgrammePacket
from ada.query_engine import QueryEngine


@pytest.mark.asyncio
async def test_kernel_boot_idempotent(schema_sql_path, test_settings) -> None:
    _invalidate_kernel_cache()
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        k1 = await kernel_boot(qe, test_settings)
        k2 = await kernel_boot(qe, test_settings)
        assert k1.base_ops_id == k2.base_ops_id
        assert k1.ada_ops_id == k2.ada_ops_id
        assert k1.memory_source_id == k2.memory_source_id

        base = await qe.get_mission_by_slug(BASE_OPS_SLUG)
        ada = await qe.get_mission_by_slug(ADA_OPS_SLUG)
        assert base is not None
        assert ada is not None
        assert int(base["id"]) == k1.base_ops_id
        assert int(ada["id"]) == k1.ada_ops_id

        raw_ids = await qe.state_get(KERNEL_MISSION_IDS_KEY)
        assert raw_ids is not None
        ids = json.loads(raw_ids)
        assert ids[BASE_OPS_SLUG] == k1.base_ops_id
        assert ids[ADA_OPS_SLUG] == k1.ada_ops_id

        mem_key = await qe.state_get(KERNEL_MEMORY_SOURCE_KEY)
        assert mem_key == str(k1.memory_source_id)

        src = await qe.list_knowledge_sources()
        mem_rows = [
            s
            for s in src
            if s.get("label") == MEMORY_SOURCE_LABEL
            and s.get("base_url") == MEMORY_SOURCE_URL
        ]
        assert len(mem_rows) == 1
        assert int(mem_rows[0]["id"]) == k1.memory_source_id
        assert mem_rows[0].get("mission_id") == k1.base_ops_id
    finally:
        await qe.close()
        _invalidate_kernel_cache()


@pytest.mark.asyncio
async def test_get_kernel_after_boot(schema_sql_path, test_settings) -> None:
    _invalidate_kernel_cache()
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        booted = await kernel_boot(qe, test_settings)
    finally:
        await qe.close()

    _invalidate_kernel_cache()
    loaded = await get_kernel(test_settings)
    assert loaded.base_ops_id == booted.base_ops_id
    assert loaded.ada_ops_id == booted.ada_ops_id
    assert loaded.memory_source_id == booted.memory_source_id
    _invalidate_kernel_cache()


@pytest.mark.asyncio
async def test_migrate_jarvis_ops_to_ada_ops(schema_sql_path, test_settings) -> None:
    _invalidate_kernel_cache()
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        legacy_id = await qe.create_mission(
            slug="jarvis-ops",
            title="Legacy ops",
            defaults_json={"pack": "core-ops"},
        )
        kernel = await kernel_boot(qe, test_settings)
        legacy = await qe.get_mission_by_slug("jarvis-ops")
        ada = await qe.get_mission_by_slug(ADA_OPS_SLUG)
        assert legacy is None
        assert ada is not None
        assert int(ada["id"]) == legacy_id == kernel.ada_ops_id
    finally:
        await qe.close()
        _invalidate_kernel_cache()


@pytest.mark.asyncio
async def test_base_ops_template_uses_personal_pack(
    schema_sql_path, test_settings
) -> None:
    from ada.mission_cli import load_mission_template

    data = load_mission_template("base_ops")
    packet = ProgrammePacket.model_validate(data)
    assert packet.defaults_json.get("pack") == "personal"
    assert packet.mission_slug == BASE_OPS_SLUG
