"""StreamingToolExecutor — allowlisted shell + optional memory appends (claude_logic §7)."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
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


@dataclass(frozen=True)
class PlanToolHooks:
    read_plan: Callable[[], Awaitable[str]]
    write_plan: Callable[[str], Awaitable[None]]


class StreamingToolExecutor:
    """
    Dispatches allowlisted shell, optional memory-append tools, and optional plan_json hooks.
    Single-writer memory I/O uses memory_io global lock.
    """

    def __init__(
        self,
        *,
        allowlist_exact: frozenset[str],
        max_output_bytes: int,
        timeout_sec: float,
        memory: MemoryToolConfig | None = None,
        plan_hooks: PlanToolHooks | None = None,
    ) -> None:
        self._allowlist = allowlist_exact
        self._max_output_bytes = max_output_bytes
        self._timeout_sec = timeout_sec
        self._memory = memory
        self._plan_hooks = plan_hooks
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
        if call.name == "read_task_plan":
            return await self._read_task_plan()
        if call.name == "write_task_plan":
            return await self._write_task_plan(call)
        return {"error": f"unknown tool: {call.name}"}

    async def _read_task_plan(self) -> dict[str, Any]:
        if self._plan_hooks is None:
            return {"error": "plan tools not configured"}
        try:
            text = await self._plan_hooks.read_plan()
            return {"plan_json": text}
        except (LookupError, ValueError) as e:
            return {"error": str(e)}

    async def _write_task_plan(self, call: CompletedFunctionCall) -> dict[str, Any]:
        if self._plan_hooks is None:
            return {"error": "plan tools not configured"}
        raw = call.args.get("plan_json")
        if raw is None:
            return {"error": "missing plan_json"}
        text = str(raw)
        if not text.strip():
            return {"error": "empty plan_json"}
        try:
            await self._plan_hooks.write_plan(text)
        except (LookupError, ValueError) as e:
            return {"error": str(e)}
        return {"ok": True, "chars": len(text)}

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
