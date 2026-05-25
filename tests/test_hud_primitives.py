"""J3: HUD primitive chips — hud_run_primitive without chat task."""

from __future__ import annotations

import pytest

from ada.boot import _invalidate_kernel_cache, kernel_boot, warm_kernel_cache
from ada.observability.hud_actions import hud_kernel_summary, hud_run_primitive
from ada.observability.queries import open_readonly_connection
from ada.query_engine import TASK_KIND_CHAT, TASK_KIND_SYSTEM, QueryEngine


def _count_tasks_by_kind(db_path, task_kind: str) -> int:
    conn = open_readonly_connection(db_path)
    try:
        cur = conn.execute(
            "SELECT COUNT(*) AS c FROM tasks WHERE task_kind = ?",
            (task_kind,),
        )
        row = cur.fetchone()
        return int(row["c"] if row else 0)
    finally:
        conn.close()


@pytest.fixture
async def booted_settings(schema_sql_path, test_settings):
    _invalidate_kernel_cache()
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        kernel = await kernel_boot(qe, test_settings)
        warm_kernel_cache(kernel)
    finally:
        await qe.close()
    yield test_settings, schema_sql_path
    _invalidate_kernel_cache()


@pytest.mark.asyncio
async def test_hud_kernel_summary(booted_settings) -> None:
    settings, _schema = booted_settings
    out = await hud_kernel_summary(settings)
    assert out.get("ok") is True
    assert isinstance(out.get("base_ops_id"), int)
    assert isinstance(out.get("ada_ops_id"), int)
    assert isinstance(out.get("memory_source_id"), int)


@pytest.mark.asyncio
async def test_hud_run_primitive_log_memory_no_chat_task(booted_settings) -> None:
    settings, _schema = booted_settings
    chat_before = _count_tasks_by_kind(settings.state_db_path, TASK_KIND_CHAT)

    out = await hud_run_primitive(
        settings,
        primitive_id="log_memory",
        args={"content": "hud chip memory note"},
    )
    assert out.get("ok") is True
    assert out.get("primitive") == "log_memory"
    assert out.get("inserted") is True

    chat_after = _count_tasks_by_kind(settings.state_db_path, TASK_KIND_CHAT)
    assert chat_after == chat_before


@pytest.mark.asyncio
async def test_hud_run_primitive_add_task_system_hat(booted_settings) -> None:
    settings, schema_sql_path = booted_settings
    out = await hud_run_primitive(
        settings,
        primitive_id="add_task",
        args={"goal": "from hud chip"},
    )
    assert out.get("ok") is True
    assert out.get("task_id")

    qe = QueryEngine(settings.state_db_path, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        row = await qe.get_system_task(int(out["task_id"]))
        assert row["task_kind"] == TASK_KIND_SYSTEM
        ksum = await hud_kernel_summary(settings)
        assert row["mission_id"] == ksum["base_ops_id"]
        pending = await qe.fetch_pending_task()
        assert pending is None or pending.task_id != int(out["task_id"])
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_hud_run_primitive_body_check(booted_settings) -> None:
    settings, _schema = booted_settings
    out = await hud_run_primitive(
        settings,
        primitive_id="body_check",
        args={},
    )
    assert out.get("ok") is True
    assert out.get("primitive") == "body_check"
    assert "kernel" in out
    assert "pending_goal_count" in out
    assert "ada_ops" in out


@pytest.mark.asyncio
async def test_hud_run_primitive_unknown_id(booted_settings) -> None:
    settings, _schema = booted_settings
    out = await hud_run_primitive(
        settings,
        primitive_id="publish_keyword_v1",
        args={},
    )
    assert out.get("ok") is False
    assert "unknown primitive" in out.get("error", "")


@pytest.mark.asyncio
async def test_hud_run_primitive_validation_error(booted_settings) -> None:
    settings, _schema = booted_settings
    out = await hud_run_primitive(
        settings,
        primitive_id="log_memory",
        args={},
    )
    assert out.get("ok") is False
    assert "content" in out.get("error", "").lower()
