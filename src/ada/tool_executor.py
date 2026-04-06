"""StreamingToolExecutor — allowlisted shell only (claude_logic §7 subset)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from ada.stream_types import CompletedFunctionCall
from ada.tools.shell_allowlist import command_to_argv


@dataclass
class ToolInvocationResult:
    call: CompletedFunctionCall
    response: dict[str, Any]


class StreamingToolExecutor:
    """
    Single-tool MVP: `run_allowlisted_shell`.
    Ordered completion in submission order; parallel optional later.
    """

    def __init__(
        self,
        *,
        allowlist_exact: frozenset[str],
        max_output_bytes: int,
        timeout_sec: float,
    ) -> None:
        self._allowlist = allowlist_exact
        self._max_output_bytes = max_output_bytes
        self._timeout_sec = timeout_sec
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
        if call.name != "run_allowlisted_shell":
            return {"error": f"unknown tool: {call.name}"}
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
