from __future__ import annotations

import pytest

from ada.stream_types import CompletedFunctionCall
from ada.tool_executor import StreamingToolExecutor


@pytest.mark.asyncio
async def test_read_goal_task_view_via_reader():
    async def reader(tid: int) -> dict:
        return {"task_id": tid, "goal": "g", "status": "completed", "current_output": "x"}

    ex = StreamingToolExecutor(
        allowlist_exact=frozenset(),
        max_output_bytes=1024,
        timeout_sec=5.0,
        goal_recall_reader=reader,
    )
    r = await ex.run_ordered(
        [
            CompletedFunctionCall(
                name="read_goal_task_view",
                args={"task_id": 42},
                id="1",
            )
        ]
    )
    assert r[0].response["task_id"] == 42
    assert r[0].response["current_output"] == "x"


@pytest.mark.asyncio
async def test_read_goal_task_view_not_configured():
    ex = StreamingToolExecutor(
        allowlist_exact=frozenset(),
        max_output_bytes=1024,
        timeout_sec=5.0,
    )
    r = await ex.run_ordered(
        [
            CompletedFunctionCall(
                name="read_goal_task_view",
                args={"task_id": 1},
                id="1",
            )
        ]
    )
    assert r[0].response == {"error": "read_goal_task_view not configured"}


@pytest.mark.asyncio
async def test_read_goal_task_view_invalid_task_id():
    async def reader(_: int) -> dict:
        return {}

    ex = StreamingToolExecutor(
        allowlist_exact=frozenset(),
        max_output_bytes=1024,
        timeout_sec=5.0,
        goal_recall_reader=reader,
    )
    r = await ex.run_ordered(
        [
            CompletedFunctionCall(
                name="read_goal_task_view",
                args={"task_id": "nope"},
                id="1",
            )
        ]
    )
    assert r[0].response.get("error") == "task_id must be an integer"


@pytest.mark.asyncio
async def test_read_goal_task_view_lookup_error_from_reader():
    async def reader(_: int) -> dict:
        raise LookupError("no task with id=99")

    ex = StreamingToolExecutor(
        allowlist_exact=frozenset(),
        max_output_bytes=1024,
        timeout_sec=5.0,
        goal_recall_reader=reader,
    )
    r = await ex.run_ordered(
        [
            CompletedFunctionCall(
                name="read_goal_task_view",
                args={"task_id": 99},
                id="1",
            )
        ]
    )
    assert r[0].response == {"error": "no task with id=99"}
