"""StreamingToolExecutor — allowlisted shell + optional memory appends (claude_logic §7)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ada.memory_io import append_markdown_block, format_master_section, format_soul_fragment
from ada.stream_types import CompletedFunctionCall
from ada.tools.shell_allowlist import command_to_argv


@dataclass
class ToolInvocationResult:
    call: CompletedFunctionCall
    response: dict[str, Any]


@dataclass(frozen=True)
class MemoryToolConfig:
    master_path: Path
    soul_path: Path
    backups_dir: Path
    memory_dir: Path
    max_append_bytes: int
    max_file_bytes: int


class StreamingToolExecutor:
    """
    Dispatches allowlisted shell and (optionally) memory-append tools.
    Single-writer memory I/O uses memory_io global lock.
    """

    def __init__(
        self,
        *,
        allowlist_exact: frozenset[str],
        max_output_bytes: int,
        timeout_sec: float,
        memory: MemoryToolConfig | None = None,
    ) -> None:
        self._allowlist = allowlist_exact
        self._max_output_bytes = max_output_bytes
        self._timeout_sec = timeout_sec
        self._memory = memory
        self.discarded = False

    def discard(self) -> None:
        self.discarded = True

    async def run_ordered(
        self, calls: list[CompletedFunctionCall]
    ) -> list[ToolInvocationResult]:
        out: list[ToolInvocationResult] = []
        for call in calls:
            if self.discarded:
                out.append(
                    ToolInvocationResult(
                        call=call,
                        response={"error": "executor discarded"},
                    )
                )
                continue
            out.append(
                ToolInvocationResult(call=call, response=await self._dispatch(call))
            )
        return out

    async def _dispatch(self, call: CompletedFunctionCall) -> dict[str, Any]:
        if call.name == "run_allowlisted_shell":
            return await self._shell(call)
        if call.name == "append_master_section":
            return await self._append_master(call)
        if call.name == "append_soul_fragment":
            return await self._append_soul(call)
        return {"error": f"unknown tool: {call.name}"}

    async def _shell(self, call: CompletedFunctionCall) -> dict[str, Any]:
        cmd = (call.args.get("command") or "").strip()
        if cmd not in self._allowlist:
            return {"error": f"command not allowlisted: {cmd!r}"}
        try:
            argv = command_to_argv(cmd)
        except ValueError as e:
            return {"error": str(e)}
        try:
            proc = await asyncio.create_subprocess_exec(
                argv[0],
                *argv[1:],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
        except FileNotFoundError:
            return {"error": f"executable not found: {argv[0]!r}"}
        try:
            raw, _ = await asyncio.wait_for(
                proc.communicate(), timeout=self._timeout_sec
            )
        except asyncio.TimeoutError:
            proc.kill()
            return {"error": "timeout", "command": cmd}
        text = raw.decode("utf-8", errors="replace")
        if len(text) > self._max_output_bytes:
            text = text[: self._max_output_bytes] + "\n… [truncated]"
        return {
            "stdout": text,
            "exit_code": proc.returncode,
            "command": cmd,
        }

    async def _append_master(self, call: CompletedFunctionCall) -> dict[str, Any]:
        if self._memory is None:
            return {"error": "memory tools disabled"}
        heading = str(call.args.get("heading") or "").strip()
        body = str(call.args.get("body") or "").strip()
        if not body:
            return {"error": "empty body"}
        try:
            block = format_master_section(heading, body)
            await append_markdown_block(
                self._memory.master_path,
                self._memory.backups_dir,
                block,
                memory_dir=self._memory.memory_dir,
                max_block_bytes=self._memory.max_append_bytes,
                max_file_bytes=self._memory.max_file_bytes,
            )
        except ValueError as e:
            return {"error": str(e)}
        return {"ok": True, "wrote": "master.md", "chars": len(block)}

    async def _append_soul(self, call: CompletedFunctionCall) -> dict[str, Any]:
        if self._memory is None:
            return {"error": "memory tools disabled"}
        text = str(call.args.get("text") or "").strip()
        if not text:
            return {"error": "empty text"}
        try:
            block = format_soul_fragment(text)
            await append_markdown_block(
                self._memory.soul_path,
                self._memory.backups_dir,
                block,
                memory_dir=self._memory.memory_dir,
                max_block_bytes=self._memory.max_append_bytes,
                max_file_bytes=self._memory.max_file_bytes,
            )
        except ValueError as e:
            return {"error": str(e)}
        return {"ok": True, "wrote": "soul.md", "chars": len(block)}
