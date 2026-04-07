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


@pytest.mark.asyncio
async def test_list_workspace_directory(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "a.txt").write_text("x", encoding="utf-8")
    (ws / "sub").mkdir()
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
    r = await ex.run_ordered(
        [
            CompletedFunctionCall(
                name="list_workspace_directory",
                args={"path": "."},
                id="1",
            )
        ]
    )
    names = {e["name"] for e in r[0].response.get("entries", [])}
    assert "a.txt" in names
    assert "sub" in names


@pytest.mark.asyncio
async def test_list_workspace_directory_denied_triggers_audit(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    vault = ws / "vault"
    vault.mkdir()
    rr = ws.resolve()
    cfg = FileToolConfig(
        roots=(rr,),
        primary_root=rr,
        max_read_bytes=4096,
        max_write_bytes=4096,
        deny_prefixes=(vault.resolve(),),
    )
    audit: list[tuple[str, str, str]] = []

    async def on_v(tool: str, path: str, reason: str) -> None:
        audit.append((tool, path, reason))

    ex = StreamingToolExecutor(
        allowlist_exact=frozenset(),
        max_output_bytes=1024,
        timeout_sec=5.0,
        file_config=cfg,
        on_file_guard_violation=on_v,
    )
    r = await ex.run_ordered(
        [
            CompletedFunctionCall(
                name="list_workspace_directory",
                args={"path": "vault"},
                id="1",
            )
        ]
    )
    assert r[0].response.get("error")
    assert len(audit) == 1
    assert audit[0][0] == "list_workspace_directory"
