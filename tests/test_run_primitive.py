"""J2: run_primitive tool executor dispatch."""

from __future__ import annotations

import pytest

from ada.boot import _invalidate_kernel_cache, kernel_boot, warm_kernel_cache
from ada.primitives.handlers import (
    _coerce_run_primitive_args,
    execute_primitive,
)
from ada.query_engine import QueryEngine
from ada.stream_types import CompletedFunctionCall
from ada.tool_executor import StreamingToolExecutor


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
async def test_run_primitive_dispatch_configured(booted_qe) -> None:
    qe, settings = booted_qe

    async def handler(call: CompletedFunctionCall) -> dict:
        raw = call.args.get("args_json")
        args = {}
        if raw:
            import json

            args = json.loads(raw) if isinstance(raw, str) else raw
        pid = call.args.get("primitive_id")
        return await execute_primitive(qe, settings, str(pid), args)

    ex = StreamingToolExecutor(
        allowlist_exact=frozenset(),
        max_output_bytes=1024,
        timeout_sec=1.0,
        run_primitive_handler=handler,
    )
    call = CompletedFunctionCall(
        name="run_primitive",
        args={"primitive_id": "add_task", "args_json": '{"goal": "test"}'},
        id="1",
    )
    results = await ex.run_ordered([call])
    assert results[0].response.get("ok") is True
    assert results[0].response.get("task_id") is not None


@pytest.mark.asyncio
async def test_run_primitive_dispatch_missing_handler() -> None:
    ex = StreamingToolExecutor(
        allowlist_exact=frozenset(),
        max_output_bytes=1024,
        timeout_sec=1.0,
    )
    call = CompletedFunctionCall(name="run_primitive", args={"primitive_id": "add_task"}, id="1")
    results = await ex.run_ordered([call])
    assert results[0].response.get("error") == "run_primitive not configured"


@pytest.mark.asyncio
async def test_run_primitive_coerces_log_memory_text_alias(booted_qe) -> None:
    qe, settings = booted_qe
    out = await execute_primitive(
        qe, settings, "log_memory", {"text": "operator note via alias"}
    )
    assert out.get("ok") is True
    assert out.get("item_id") is not None


@pytest.mark.asyncio
async def test_run_primitive_coerces_add_task_title_alias(booted_qe) -> None:
    qe, settings = booted_qe
    out = await execute_primitive(
        qe, settings, "add_task", {"title": "buy milk via alias"}
    )
    assert out.get("ok") is True
    assert out.get("goal") == "buy milk via alias"
    assert out.get("task_id") is not None


@pytest.mark.asyncio
async def test_run_primitive_coerces_recall_memory_question_alias(booted_qe) -> None:
    qe, settings = booted_qe
    await execute_primitive(
        qe, settings, "log_memory", {"content": "favorite color is blue"}
    )
    out = await execute_primitive(
        qe, settings, "recall_memory", {"question": "blue"}
    )
    assert out.get("ok") is True
    assert out.get("count", 0) >= 1
    assert any("blue" in (i.get("content_excerpt") or "") for i in out.get("items", []))


@pytest.mark.asyncio
async def test_coerce_run_primitive_args_flat_text_alias(booted_qe) -> None:
    qe, settings = booted_qe
    pid, args = _coerce_run_primitive_args(
        {
            "primitive_id": "log_memory",
            "text": "flat operator note",
        }
    )
    assert pid == "log_memory"
    assert args.get("content") == "flat operator note"
    out = await execute_primitive(qe, settings, pid, args)
    assert out.get("ok") is True


@pytest.mark.asyncio
async def test_coerce_run_primitive_args_flat_task_alias(booted_qe) -> None:
    qe, settings = booted_qe
    pid, args = _coerce_run_primitive_args(
        {
            "primitive_id": "add_task",
            "task": "buy milk flat",
        }
    )
    assert pid == "add_task"
    assert args.get("goal") == "buy milk flat"
    out = await execute_primitive(qe, settings, pid, args)
    assert out.get("ok") is True
    assert out.get("goal") == "buy milk flat"


@pytest.mark.asyncio
async def test_coerce_run_primitive_args_primitive_id_with_args_json(booted_qe) -> None:
    qe, settings = booted_qe
    pid, args = _coerce_run_primitive_args(
        {
            "primitive_id": "log_memory",
            "args_json": '{"content": "via args_json"}',
        }
    )
    assert pid == "log_memory"
    assert args.get("content") == "via args_json"
    out = await execute_primitive(qe, settings, pid, args)
    assert out.get("ok") is True


@pytest.mark.asyncio
async def test_orchestrator_allowlist_rejects_unknown_primitive(booted_qe) -> None:
    qe, settings = booted_qe
    from ada.chat_capability import PRIMITIVE_ALLOWLIST

    async def handler(call: CompletedFunctionCall) -> dict:
        pid = str(call.args.get("primitive_id") or "")
        if pid not in PRIMITIVE_ALLOWLIST:
            return {"error": f"primitive {pid!r} not in chat allowlist"}
        return await execute_primitive(qe, settings, pid, {})

    ex = StreamingToolExecutor(
        allowlist_exact=frozenset(),
        max_output_bytes=1024,
        timeout_sec=1.0,
        run_primitive_handler=handler,
    )
    call = CompletedFunctionCall(name="run_primitive", args={"primitive_id": "publish"}, id="1")
    results = await ex.run_ordered([call])
    assert "not in chat allowlist" in results[0].response.get("error", "")
