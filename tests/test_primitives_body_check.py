"""J1: body_check structured JSON — read-only aggregate."""

from __future__ import annotations

import pytest

from ada.boot import _invalidate_kernel_cache, kernel_boot, warm_kernel_cache
from ada.primitives.handlers import execute_primitive
from ada.query_engine import TASK_KIND_GOAL, QueryEngine


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


async def _task_count(qe: QueryEngine) -> int:
    assert qe._store._conn is not None
    cur = await qe._store._conn.execute("SELECT COUNT(*) FROM tasks")
    row = await cur.fetchone()
    return int(row[0])


async def _knowledge_count(qe: QueryEngine) -> int:
    assert qe._store._conn is not None
    cur = await qe._store._conn.execute("SELECT COUNT(*) FROM knowledge_items")
    row = await cur.fetchone()
    return int(row[0])


@pytest.mark.asyncio
async def test_body_check_returns_structured_json(booted_qe) -> None:
    qe, settings, kernel = booted_qe
    await qe.insert_task(
        "background goal",
        status="pending",
        task_kind=TASK_KIND_GOAL,
        mission_id=kernel.ada_ops_id,
    )
    out = await execute_primitive(
        qe,
        settings,
        "body_check",
        {},
        kernel=kernel,
    )
    assert out["ok"] is True
    assert out["primitive"] == "body_check"
    assert out["kernel"]["base_ops_id"] == kernel.base_ops_id
    assert out["kernel"]["ada_ops_id"] == kernel.ada_ops_id
    assert out["kernel"]["memory_source_id"] == kernel.memory_source_id
    assert out["pending_goal_count"] >= 1
    assert out["ada_ops"]["slug"] == "ada_ops"
    assert out["ada_ops"]["id"] == kernel.ada_ops_id
    assert "tick_state" in out["ada_ops"]
    assert out["daemon"]["job_queue"]
    assert "gemini_configured" in out["daemon"]
    assert "memory_dir" in out["profile_paths"]
    assert "state_db_path" in out["profile_paths"]
    assert "last_brief" in out
    assert "path" in out["last_brief"]


@pytest.mark.asyncio
async def test_body_check_no_writes(booted_qe) -> None:
    qe, settings, kernel = booted_qe
    tasks_before = await _task_count(qe)
    items_before = await _knowledge_count(qe)
    await execute_primitive(
        qe,
        settings,
        "body_check",
        {},
        kernel=kernel,
    )
    assert await _task_count(qe) == tasks_before
    assert await _knowledge_count(qe) == items_before
