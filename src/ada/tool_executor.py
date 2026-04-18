"""StreamingToolExecutor — allowlisted shell + optional memory appends (claude_logic §7)."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ada.config import Settings
from ada.memory_io import append_markdown_block, format_master_section, format_soul_fragment
from ada.stream_types import CompletedFunctionCall
from ada.tools.file_sandbox import (
    list_directory_entries,
    resolve_workspace_path_guarded,
)
from ada.tools.shell_allowlist import command_to_argv
from ada.tools.web_runtime import fetch_url_text_batch, serper_search

log = logging.getLogger("ada.web")


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


@dataclass(frozen=True)
class FileToolConfig:
    """Paths resolved at startup; relative file paths use primary_root."""

    roots: tuple[Path, ...]
    primary_root: Path
    max_read_bytes: int
    max_write_bytes: int
    deny_prefixes: tuple[Path, ...] = ()
    deny_basenames_extra: frozenset[str] = frozenset()
    max_list_entries: int = 200


@dataclass(frozen=True)
class WebToolConfig:
    """Serper + fetch limits; optional search when serper_api_key is set."""

    serper_api_key: str | None
    web_search_max_results: int
    web_search_timeout_sec: float
    fetch_mode: str
    fetch_max_urls: int
    fetch_max_chars: int
    fetch_max_bytes: int
    fetch_timeout_sec: float
    fetch_host_allowlist: frozenset[str]
    jina_reader_base_url: str
    jina_api_key: str | None


def build_web_tool_config(settings: Settings) -> WebToolConfig | None:
    """Return config when ADA_ENABLE_WEB_TOOLS=1; search executes only if Serper key is set."""
    if not settings.enable_web_tools:
        return None
    key = settings.serper_api_key.strip() or None
    return WebToolConfig(
        serper_api_key=key,
        web_search_max_results=settings.web_search_max_results,
        web_search_timeout_sec=settings.web_search_timeout_sec,
        fetch_mode=settings.web_fetch_mode,
        fetch_max_urls=settings.web_fetch_max_urls,
        fetch_max_chars=settings.web_fetch_max_chars,
        fetch_max_bytes=settings.web_fetch_max_bytes,
        fetch_timeout_sec=settings.web_fetch_timeout_sec,
        fetch_host_allowlist=settings.web_fetch_host_allowlist,
        jina_reader_base_url=settings.jina_reader_base_url,
        jina_api_key=settings.jina_api_key.strip() or None,
    )


class StreamingToolExecutor:
    """
    Dispatches allowlisted shell, optional memory-append tools, optional plan_json hooks,
    optional read_goal_task_view (goal recall), and optional sandboxed workspace file read/write.
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
        token_usage: Callable[[], Awaitable[dict[str, Any]]] | None = None,
        file_config: FileToolConfig | None = None,
        web: WebToolConfig | None = None,
        web_sources_reader: Callable[[int], Awaitable[list[dict[str, Any]]]]
        | None = None,
        goal_recall_reader: Callable[[int], Awaitable[dict[str, Any]]]
        | None = None,
        on_file_guard_violation: Callable[[str, str, str], Awaitable[None]]
        | None = None,
    ) -> None:
        self._allowlist = allowlist_exact
        self._max_output_bytes = max_output_bytes
        self._timeout_sec = timeout_sec
        self._memory = memory
        self._plan_hooks = plan_hooks
        self._token_usage = token_usage
        self._file_config = file_config
        self._web = web
        self._web_sources_reader = web_sources_reader
        self._goal_recall_reader = goal_recall_reader
        self._on_file_guard_violation = on_file_guard_violation
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
        if call.name == "check_token_usage":
            return await self._check_token_usage()
        if call.name == "read_workspace_file":
            return await self._read_workspace_file(call)
        if call.name == "write_workspace_file":
            return await self._write_workspace_file(call)
        if call.name == "list_workspace_directory":
            return await self._list_workspace_directory(call)
        if call.name == "web_search":
            return await self._web_search(call)
        if call.name == "fetch_url_text":
            return await self._fetch_url_text(call)
        if call.name == "list_session_web_sources":
            return await self._list_session_web_sources(call)
        if call.name == "read_goal_task_view":
            return await self._read_goal_task_view(call)
        return {"error": f"unknown tool: {call.name}"}

    async def _list_session_web_sources(
        self, call: CompletedFunctionCall
    ) -> dict[str, Any]:
        if self._web_sources_reader is None:
            return {"error": "list_session_web_sources not configured"}
        raw = call.args.get("limit")
        limit = 50
        if raw is not None:
            try:
                limit = max(1, min(int(raw), 200))
            except (TypeError, ValueError):
                limit = 50
        try:
            rows = await self._web_sources_reader(limit)
            return {"sources": rows, "count": len(rows)}
        except Exception as e:
            log.warning("list_session_web_sources failed: %s", e)
            return {"error": str(e)}

    async def _web_search(self, call: CompletedFunctionCall) -> dict[str, Any]:
        if self._web is None:
            return {"error": "web tools not configured"}
        if not self._web.serper_api_key:
            return {"error": "web search not configured (missing Serper API key)"}
        q = str(call.args.get("query") or "").strip()
        raw_n = call.args.get("num_results")
        n = self._web.web_search_max_results
        if raw_n is not None:
            try:
                n = min(int(raw_n), self._web.web_search_max_results)
            except (TypeError, ValueError):
                pass
        n = max(1, n)
        try:
            return await serper_search(
                api_key=self._web.serper_api_key,
                query=q,
                max_results=n,
                timeout_sec=self._web.web_search_timeout_sec,
            )
        except Exception as e:
            log.warning("web_search failed: %s", e)
            return {"error": str(e)}

    async def _fetch_url_text(self, call: CompletedFunctionCall) -> dict[str, Any]:
        if self._web is None:
            return {"error": "web tools not configured"}
        raw = call.args.get("urls")
        if raw is None:
            return {"error": "missing urls"}
        if not isinstance(raw, list):
            return {"error": "urls must be a list"}
        urls = [str(u).strip() for u in raw if str(u).strip()]
        try:
            return await fetch_url_text_batch(
                urls,
                mode=self._web.fetch_mode,
                max_urls=self._web.fetch_max_urls,
                max_total_chars=self._web.fetch_max_chars,
                max_bytes_per_response=self._web.fetch_max_bytes,
                timeout_sec=self._web.fetch_timeout_sec,
                host_patterns=self._web.fetch_host_allowlist,
                jina_base_url=self._web.jina_reader_base_url,
                jina_api_key=self._web.jina_api_key,
            )
        except Exception as e:
            log.warning("fetch_url_text failed: %s", e)
            return {"error": str(e)}

    async def _check_token_usage(self) -> dict[str, Any]:
        if self._token_usage is None:
            return {"error": "token usage not configured"}
        try:
            return await self._token_usage()
        except Exception as e:
            return {"error": str(e)}

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

    async def _read_goal_task_view(self, call: CompletedFunctionCall) -> dict[str, Any]:
        if self._goal_recall_reader is None:
            return {"error": "read_goal_task_view not configured"}
        raw = call.args.get("task_id")
        if raw is None:
            return {"error": "task_id required"}
        try:
            task_id = int(raw)
        except (TypeError, ValueError):
            return {"error": "task_id must be an integer"}
        try:
            return await self._goal_recall_reader(task_id)
        except LookupError as e:
            return {"error": str(e)}
        except ValueError as e:
            return {"error": str(e)}

    async def _shell(self, call: CompletedFunctionCall) -> dict[str, Any]:
        cmd = (call.args.get("command") or "").strip()
        if cmd not in self._allowlist:
            return {"error": "Command not in allowlist", "command": cmd}
        try:
            argv = command_to_argv(cmd)
        except ValueError as e:
            return {"error": str(e), "command": cmd}
        try:
            proc = await asyncio.create_subprocess_exec(
                argv[0],
                *argv[1:],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
        except (FileNotFoundError, PermissionError, OSError) as e:
            return {"error": str(e), "command": cmd}
        try:
            raw, _ = await asyncio.wait_for(
                proc.communicate(), timeout=self._timeout_sec
            )
        except asyncio.TimeoutError:
            proc.kill()
            return {"error": "timeout", "command": cmd}
        except asyncio.CancelledError:
            proc.kill()
            raise
        except Exception as e:
            proc.kill()
            return {"error": str(e), "command": cmd}
        text = raw.decode("utf-8", errors="replace")
        if len(text) > self._max_output_bytes:
            text = text[: self._max_output_bytes] + "\n… [truncated]"
        return {
            "stdout": text,
            "exit_code": proc.returncode,
            "command": cmd,
        }

    async def _notify_file_guard(
        self, tool: str, attempted_path: str, reason: str
    ) -> None:
        if self._on_file_guard_violation is None:
            return
        try:
            await self._on_file_guard_violation(tool, attempted_path, reason)
        except Exception:
            pass

    async def _read_workspace_file(self, call: CompletedFunctionCall) -> dict[str, Any]:
        if self._file_config is None:
            return {"error": "file tools not configured"}
        rel = call.args.get("path")
        if rel is None or not str(rel).strip():
            return {"error": "missing path"}
        rel_s = str(rel).strip()
        try:
            path = resolve_workspace_path_guarded(
                roots=self._file_config.roots,
                primary_root=self._file_config.primary_root,
                user_path=rel_s,
                deny_prefixes=self._file_config.deny_prefixes,
                deny_basenames_extra=self._file_config.deny_basenames_extra,
            )
        except ValueError as e:
            msg = str(e)
            await self._notify_file_guard("read_workspace_file", rel_s, msg)
            return {"error": msg, "path": rel_s}
        max_b = self._file_config.max_read_bytes

        def _read() -> dict[str, Any]:
            if not path.is_file():
                return {"error": "not a file or does not exist", "path": str(path)}
            data = path.read_bytes()
            total = len(data)
            truncated = total > max_b
            if truncated:
                data = data[:max_b]
            text = data.decode("utf-8", errors="replace")
            out: dict[str, Any] = {
                "path": str(path),
                "content": text,
                "truncated": truncated,
                "size_bytes": total,
            }
            return out

        try:
            return await asyncio.to_thread(_read)
        except OSError as e:
            return {"error": str(e), "path": str(path)}

    async def _write_workspace_file(self, call: CompletedFunctionCall) -> dict[str, Any]:
        if self._file_config is None:
            return {"error": "file tools not configured"}
        rel = call.args.get("path")
        if rel is None or not str(rel).strip():
            return {"error": "missing path"}
        raw_content = call.args.get("content")
        if raw_content is None:
            return {"error": "missing content"}
        content = str(raw_content)
        mode = str(call.args.get("mode") or "write").strip().lower()
        if mode not in ("write", "append"):
            return {"error": "mode must be 'write' or 'append'"}
        create_parents = bool(call.args.get("create_parents"))
        rel_s = str(rel).strip()
        try:
            path = resolve_workspace_path_guarded(
                roots=self._file_config.roots,
                primary_root=self._file_config.primary_root,
                user_path=rel_s,
                deny_prefixes=self._file_config.deny_prefixes,
                deny_basenames_extra=self._file_config.deny_basenames_extra,
            )
        except ValueError as e:
            msg = str(e)
            await self._notify_file_guard("write_workspace_file", rel_s, msg)
            return {"error": msg, "path": rel_s}
        encoded = content.encode("utf-8")
        if len(encoded) > self._file_config.max_write_bytes:
            return {
                "error": "content exceeds max_write_bytes",
                "max_write_bytes": self._file_config.max_write_bytes,
                "bytes": len(encoded),
            }

        def _write() -> dict[str, Any]:
            if create_parents:
                path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists() and path.is_dir():
                return {"error": "path is a directory", "path": str(path)}
            flag = "a" if mode == "append" else "w"
            with path.open(flag, encoding="utf-8", newline="") as f:
                f.write(content)
            return {
                "ok": True,
                "path": str(path),
                "mode": mode,
                "bytes_written": len(encoded),
            }

        try:
            return await asyncio.to_thread(_write)
        except OSError as e:
            return {"error": str(e), "path": str(path)}

    async def _list_workspace_directory(
        self, call: CompletedFunctionCall
    ) -> dict[str, Any]:
        if self._file_config is None:
            return {"error": "file tools not configured"}
        rel = call.args.get("path")
        if rel is None:
            rel_s = "."
        else:
            rel_s = str(rel).strip() or "."
        raw_max = call.args.get("max_entries")
        cap = self._file_config.max_list_entries
        try:
            if raw_max is not None:
                cap = min(int(raw_max), self._file_config.max_list_entries)
        except (TypeError, ValueError):
            cap = self._file_config.max_list_entries
        cap = max(1, cap)
        try:
            dir_path = resolve_workspace_path_guarded(
                roots=self._file_config.roots,
                primary_root=self._file_config.primary_root,
                user_path=rel_s,
                deny_prefixes=self._file_config.deny_prefixes,
                deny_basenames_extra=self._file_config.deny_basenames_extra,
            )
        except ValueError as e:
            msg = str(e)
            await self._notify_file_guard("list_workspace_directory", rel_s, msg)
            return {"error": msg, "path": rel_s}

        def _list() -> dict[str, Any]:
            return list_directory_entries(dir_path, max_entries=cap)

        try:
            return await asyncio.to_thread(_list)
        except OSError as e:
            return {"error": str(e), "path": str(dir_path)}

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
