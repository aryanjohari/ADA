"""J1: log_memory / recall_memory scoped to base_ops memory source."""

from __future__ import annotations

import pytest

from ada.boot import _invalidate_kernel_cache, kernel_boot, warm_kernel_cache
from ada.primitives.handlers import execute_primitive
from ada.query_engine import QueryEngine


@pytest.fixture
async def booted_qe(schema_sql_path, test_settings):
    _invalidate_kernel_cache()
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path, debounce_ms=1)
    await qe.connect()
    kernel = await kernel_boot(qe, test_settings)
    warm_kernel_cache(kernel)
    yield qe, test_settings, kernel
    await qe.close()
    _invalidate_kernel_cache()


@pytest.mark.asyncio
async def test_log_and_recall_memory_on_base_source(booted_qe) -> None:
    qe, settings, kernel = booted_qe
    logged = await execute_primitive(
        qe,
        settings,
        "log_memory",
        {"content": "operator prefers dark mode", "tags": ["preference"]},
        kernel=kernel,
    )
    assert logged["ok"] is True
    assert logged["inserted"] is True
    assert logged["source_id"] == kernel.memory_source_id

    recalled = await execute_primitive(
        qe,
        settings,
        "recall_memory",
        {"query": "dark mode"},
        kernel=kernel,
    )
    assert recalled["count"] == 1
    assert "dark mode" in recalled["items"][0]["content_excerpt"]


@pytest.mark.asyncio
async def test_log_memory_content_hash_dedupe(booted_qe) -> None:
    qe, settings, kernel = booted_qe
    first = await execute_primitive(
        qe,
        settings,
        "log_memory",
        {"content": "same note twice"},
        kernel=kernel,
    )
    second = await execute_primitive(
        qe,
        settings,
        "log_memory",
        {"content": "same note twice"},
        kernel=kernel,
    )
    assert first["inserted"] is True
    assert second["inserted"] is False
    assert second["item_id"] == first["item_id"]


@pytest.mark.asyncio
async def test_recall_memory_not_in_global_null_pool(booted_qe) -> None:
    qe, settings, kernel = booted_qe
    global_src = await qe.insert_knowledge_source(
        "web",
        label="global_pool",
        base_url="https://global.example/mem",
        mission_id=None,
    )
    await qe.insert_knowledge_item(
        global_src,
        "globalhash",
        content_excerpt="global secret zebra",
    )
    await execute_primitive(
        qe,
        settings,
        "log_memory",
        {"content": "personal zebra note"},
        kernel=kernel,
    )

    recalled = await execute_primitive(
        qe,
        settings,
        "recall_memory",
        {"query": "zebra"},
        kernel=kernel,
    )
    assert recalled["count"] == 1
    assert "personal" in recalled["items"][0]["content_excerpt"]
    assert "global secret" not in recalled["items"][0]["content_excerpt"]

    global_items = await qe.list_knowledge_items(
        source_id=global_src,
        mission_scope=None,
    )
    assert len(global_items) == 1
    assert "global secret" in global_items[0]["content_excerpt"]
