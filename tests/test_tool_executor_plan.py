from __future__ import annotations

import pytest

from ada.stream_types import CompletedFunctionCall
from ada.tool_executor import PlanToolHooks, StreamingToolExecutor


@pytest.mark.asyncio
async def test_read_write_task_plan_via_hooks():
    state = {"plan": "{}"}

    async def read_plan() -> str:
        return state["plan"]

    async def write_plan(text: str) -> None:
        state["plan"] = text

    hooks = PlanToolHooks(read_plan=read_plan, write_plan=write_plan)
    ex = StreamingToolExecutor(
        allowlist_exact=frozenset(),
        max_output_bytes=1024,
        timeout_sec=5.0,
        plan_hooks=hooks,
    )
    r1 = await ex.run_ordered(
        [CompletedFunctionCall(name="read_task_plan", args={}, id="1")]
    )
    assert r1[0].response == {"plan_json": "{}"}

    r2 = await ex.run_ordered(
        [
            CompletedFunctionCall(
                name="write_task_plan",
                args={"plan_json": '{"x":1}'},
                id="2",
            )
        ]
    )
    assert r2[0].response.get("ok") is True

    r3 = await ex.run_ordered(
        [CompletedFunctionCall(name="read_task_plan", args={}, id="3")]
    )
    assert r3[0].response == {"plan_json": '{"x":1}'}


@pytest.mark.asyncio
async def test_plan_tools_not_configured_returns_error():
    ex = StreamingToolExecutor(
        allowlist_exact=frozenset(),
        max_output_bytes=1024,
        timeout_sec=5.0,
    )
    r = await ex.run_ordered(
        [CompletedFunctionCall(name="read_task_plan", args={}, id="1")]
    )
    assert r[0].response == {"error": "plan tools not configured"}


@pytest.mark.asyncio
async def test_write_task_plan_empty_string_error():
    async def read_plan() -> str:
        return "{}"

    async def write_plan(_: str) -> None:
        pass

    ex = StreamingToolExecutor(
        allowlist_exact=frozenset(),
        max_output_bytes=1024,
        timeout_sec=5.0,
        plan_hooks=PlanToolHooks(read_plan=read_plan, write_plan=write_plan),
    )
    r = await ex.run_ordered(
        [
            CompletedFunctionCall(
                name="write_task_plan",
                args={"plan_json": "   "},
                id="1",
            )
        ]
    )
    assert r[0].response.get("error") == "empty plan_json"


@pytest.mark.asyncio
async def test_write_task_plan_hook_value_error_surfaces():
    async def read_plan() -> str:
        return "{}"

    async def write_plan(_: str) -> None:
        raise ValueError("bad json")

    ex = StreamingToolExecutor(
        allowlist_exact=frozenset(),
        max_output_bytes=1024,
        timeout_sec=5.0,
        plan_hooks=PlanToolHooks(read_plan=read_plan, write_plan=write_plan),
    )
    r = await ex.run_ordered(
        [
            CompletedFunctionCall(
                name="write_task_plan",
                args={"plan_json": "{}"},
                id="1",
            )
        ]
    )
    assert r[0].response == {"error": "bad json"}
