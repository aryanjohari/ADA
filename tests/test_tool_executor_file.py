from __future__ import annotations

import pytest

from ada.stream_types import CompletedFunctionCall
from ada.tool_executor import FileToolConfig, StreamingToolExecutor


@pytest.mark.asyncio
async def test_write_then_read_workspace_file(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    rr = ws.resolve()
    cfg = FileToolConfig(
        roots=(rr,),
        primary_root=rr,
        max_read_bytes=4096,
        max_write_bytes=4096,
    )
    ex = StreamingToolExecutor(
        allowlist_exact=frozenset(),
        max_output_bytes=1024,
        timeout_sec=5.0,
        file_config=cfg,
    )
    w = await ex.run_ordered(
        [
            CompletedFunctionCall(
                name="write_workspace_file",
                args={"path": "sub/x.txt", "content": "hello", "mode": "write", "create_parents": True},
                id="1",
            )
        ]
    )
    assert w[0].response.get("ok") is True
    assert (ws / "sub" / "x.txt").read_text(encoding="utf-8") == "hello"

    r = await ex.run_ordered(
        [
            CompletedFunctionCall(
                name="read_workspace_file",
                args={"path": "sub/x.txt"},
                id="2",
            )
        ]
    )
    assert r[0].response.get("content") == "hello"


@pytest.mark.asyncio
async def test_file_tools_disabled_returns_error():
    ex = StreamingToolExecutor(
        allowlist_exact=frozenset(),
        max_output_bytes=1024,
        timeout_sec=5.0,
        file_config=None,
    )
    r = await ex.run_ordered(
        [
            CompletedFunctionCall(
                name="read_workspace_file",
                args={"path": "any"},
                id="1",
            )
        ]
    )
    assert r[0].response.get("error") == "file tools not configured"
