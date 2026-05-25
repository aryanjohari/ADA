"""Orchestrator fallback when post-run_primitive model stream is empty."""

from __future__ import annotations

import pytest

import ada.orchestrator as orch
from ada.boot import _invalidate_kernel_cache, kernel_boot, warm_kernel_cache
from ada.primitives.handlers import execute_primitive
from ada.query_engine import TASK_KIND_CHAT, QueryEngine
from ada.stream_types import CompletedFunctionCall, StreamLegResult


@pytest.fixture
async def booted_qe(schema_sql_path, test_settings):
    _invalidate_kernel_cache()
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path, debounce_ms=1)
    await qe.connect()
    kernel = await kernel_boot(qe, test_settings)
    warm_kernel_cache(kernel)
    yield qe, test_settings
    await qe.close()
    _invalidate_kernel_cache()


@pytest.mark.asyncio
async def test_orchestrator_empty_leg_after_run_primitive_returns_summary(
    booted_qe, monkeypatch
) -> None:
    """Leg 2 empty after successful log_memory must not raise StreamFailed."""
    qe, settings = booted_qe
    calls = {"n": 0}

    async def run_then_empty(**kwargs: object) -> StreamLegResult:
        calls["n"] += 1
        if calls["n"] == 1:
            return StreamLegResult(
                "",
                [
                    CompletedFunctionCall(
                        name="run_primitive",
                        args={
                            "primitive_id": "log_memory",
                            "args_json": '{"content": "SEO report for Ben"}',
                        },
                        id="rp1",
                    )
                ],
                {},
                "STOP",
            )
        return StreamLegResult("", [], {}, "STOP")

    monkeypatch.setattr(orch, "stream_one_model_leg", run_then_empty)

    tid = await qe.insert_task(
        "Interactive", status="executing", task_kind=TASK_KIND_CHAT
    )
    out = await orch.orchestrate_turn(
        qe,
        session_id=tid,
        user_text="remember I need an SEO report for Ben",
        system_instruction="sys",
        api_key="k",
        model="gemini-2.5-flash-lite",
        max_retries=0,
        enable_memory_tools=False,
        include_plan_tools=False,
        include_run_primitive=True,
        motor_settings=settings,
    )
    assert out == "Memory logged."
    assert calls["n"] >= 4  # leg1 + 3 empty retries on leg2
    chain = await qe.load_chain_for_api(tid)
    assistant_texts = [
        p.get("text")
        for row in chain
        if row["role"] == "assistant"
        for p in row.get("parts", [])
        if p.get("type") == "text"
    ]
    assert "Memory logged." in assistant_texts


@pytest.mark.asyncio
async def test_orchestrator_empty_leg_after_run_primitive_error_shows_error(
    booted_qe, monkeypatch
) -> None:
    qe, settings = booted_qe
    calls = {"n": 0}

    async def run_then_empty(**kwargs: object) -> StreamLegResult:
        calls["n"] += 1
        if calls["n"] == 1:
            return StreamLegResult(
                "",
                [
                    CompletedFunctionCall(
                        name="run_primitive",
                        args={"primitive_id": "add_task", "args_json": "{}"},
                        id="rp1",
                    )
                ],
                {},
                "STOP",
            )
        return StreamLegResult("", [], {}, "STOP")

    monkeypatch.setattr(orch, "stream_one_model_leg", run_then_empty)

    tid = await qe.insert_task(
        "Interactive", status="executing", task_kind=TASK_KIND_CHAT
    )
    out = await orch.orchestrate_turn(
        qe,
        session_id=tid,
        user_text="add a todo",
        system_instruction="sys",
        api_key="k",
        model="m",
        max_retries=0,
        enable_memory_tools=False,
        include_plan_tools=False,
        include_run_primitive=True,
        motor_settings=settings,
    )
    assert "Could not complete that:" in out
    assert "goal" in out.lower()


@pytest.mark.asyncio
async def test_orchestrator_stream_error_after_run_primitive_returns_summary(
    booted_qe, monkeypatch
) -> None:
    """Leg 2 API/stream failure after recall_memory must fall back, not fail silently."""
    qe, settings = booted_qe
    await execute_primitive(
        qe,
        settings,
        "log_memory",
        {"content": "About me: favorite color is blue"},
    )
    calls = {"n": 0}

    async def tool_then_stream_error(**kwargs: object) -> StreamLegResult:
        calls["n"] += 1
        if calls["n"] == 1:
            return StreamLegResult(
                "",
                [
                    CompletedFunctionCall(
                        name="run_primitive",
                        args={
                            "primitive_id": "recall_memory",
                            "args_json": '{"query": "about me"}',
                        },
                        id="rp1",
                    )
                ],
                {},
                "STOP",
            )
        raise RuntimeError("gemini stream exhausted")

    monkeypatch.setattr(orch, "stream_one_model_leg", tool_then_stream_error)

    deltas: list[str] = []

    async def on_delta(chunk: str) -> None:
        deltas.append(chunk)

    tid = await qe.insert_task(
        "Interactive", status="executing", task_kind=TASK_KIND_CHAT
    )
    out = await orch.orchestrate_turn(
        qe,
        session_id=tid,
        user_text="what do you remember about me?",
        system_instruction="sys",
        api_key="k",
        model="gemini-2.5-flash-lite",
        max_retries=0,
        enable_memory_tools=False,
        include_plan_tools=False,
        include_run_primitive=True,
        motor_settings=settings,
        on_delta=on_delta,
    )
    assert "remember" in out.lower()
    assert "blue" in out.lower()
    assert any("blue" in d for d in deltas)


@pytest.mark.asyncio
async def test_orchestrator_empty_leg_without_run_primitive_still_fails(
    tmp_path, schema_sql_path, monkeypatch
) -> None:
    calls = {"n": 0}

    async def always_empty(**kwargs: object) -> StreamLegResult:
        calls["n"] += 1
        return StreamLegResult("", [], {}, "STOP")

    monkeypatch.setattr(orch, "stream_one_model_leg", always_empty)

    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        tid = await qe.insert_task(
            "Interactive", status="executing", task_kind=TASK_KIND_CHAT
        )
        with pytest.raises(orch.StreamFailed, match="empty model output"):
            await orch.orchestrate_turn(
                qe,
                session_id=tid,
                user_text="hi",
                system_instruction="sys",
                api_key="k",
                model="m",
                max_retries=0,
                enable_memory_tools=False,
                include_plan_tools=False,
            )
    finally:
        await qe.close()
