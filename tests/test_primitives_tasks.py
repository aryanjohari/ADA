"""J1: system tasks on base_ops — not dequeued by goal daemon."""

from __future__ import annotations

import pytest

from ada.boot import _invalidate_kernel_cache, kernel_boot, warm_kernel_cache
from ada.primitives.handlers import execute_primitive
from ada.query_engine import TASK_KIND_GOAL, TASK_KIND_SYSTEM, QueryEngine


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
async def test_add_task_system_mission_not_dequeued(booted_qe) -> None:
    qe, settings, kernel = booted_qe
    out = await execute_primitive(
        qe,
        settings,
        "add_task",
        {"goal": "buy milk"},
        kernel=kernel,
    )
    assert out["ok"] is True
    tid = out["task_id"]

    row = await qe.get_system_task(tid)
    assert row["task_kind"] == TASK_KIND_SYSTEM
    assert row["mission_id"] == kernel.base_ops_id
    assert row["status"] == "pending"

    pending = await qe.fetch_pending_task()
    assert pending is None or pending.task_id != tid


@pytest.mark.asyncio
async def test_system_task_stays_pending_while_goal_dequeues(booted_qe) -> None:
    qe, settings, kernel = booted_qe
    sys_out = await execute_primitive(
        qe,
        settings,
        "add_task",
        {"goal": "personal todo"},
        kernel=kernel,
    )
    goal_id = await qe.insert_task(
        "daemon work",
        status="pending",
        task_kind=TASK_KIND_GOAL,
    )
    pending = await qe.fetch_pending_task()
    assert pending is not None
    assert pending.task_id == goal_id
    assert pending.task_id != sys_out["task_id"]


@pytest.mark.asyncio
async def test_list_and_complete_system_tasks(booted_qe) -> None:
    qe, settings, kernel = booted_qe
    added = await execute_primitive(
        qe,
        settings,
        "add_task",
        {"goal": "finish taxes"},
        kernel=kernel,
    )
    listed = await execute_primitive(
        qe,
        settings,
        "list_tasks",
        {"status": "pending"},
        kernel=kernel,
    )
    assert listed["count"] >= 1
    assert any(t["id"] == added["task_id"] for t in listed["tasks"])

    done = await execute_primitive(
        qe,
        settings,
        "complete_task",
        {"task_id": added["task_id"]},
        kernel=kernel,
    )
    assert done["status"] == "completed"

    listed_done = await execute_primitive(
        qe,
        settings,
        "list_tasks",
        {"status": "completed"},
        kernel=kernel,
    )
    assert any(t["id"] == added["task_id"] for t in listed_done["tasks"])


@pytest.mark.asyncio
async def test_complete_task_rejects_wrong_mission(booted_qe) -> None:
    qe, settings, kernel = booted_qe
    other_mid = await qe.create_mission(slug="other-hat", title="Other")
    foreign_id = await qe.insert_task(
        "foreign",
        task_kind=TASK_KIND_SYSTEM,
        mission_id=other_mid,
    )
    with pytest.raises(ValueError, match="does not belong to base_ops"):
        await execute_primitive(
            qe,
            settings,
            "complete_task",
            {"task_id": foreign_id},
            kernel=kernel,
        )
