"""Agentic turn: stream legs + allowlisted tools (claude_logic §6–7)."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable, Coroutine
from typing import Any

from ada.adapters.gemini_stream import chain_rows_to_contents, stream_one_model_leg
from ada.stream_debug import is_stream_debug_on, log_stream
from ada.query_engine import QueryEngine
from ada.tool_executor import (
    FileToolConfig,
    MemoryToolConfig,
    PlanToolHooks,
    StreamingToolExecutor,
    WebToolConfig,
)
from ada.tools.registry import build_agent_tools


class StreamFailed(Exception):
    """Raised when the model stream ends without usable output."""


class SessionTokenLimitExceeded(Exception):
    """Raised when summed session usage_ledger tokens exceed ADA_MAX_SESSION_TOKENS."""


def file_guard_audit_hook(
    qe: QueryEngine,
    session_id: int,
    *,
    enabled: bool,
) -> Callable[[str, str, str], Coroutine[Any, Any, None]] | None:
    """Optional callback for StreamingToolExecutor when a path hits the file sandbox deny rules."""
    if not enabled:
        return None

    async def _cb(tool: str, path: str, reason: str) -> None:
        await qe.append_action_log(
            "file_access_denied",
            {"tool": tool, "path": path, "reason": reason},
            session_id=session_id,
        )

    return _cb


async def orchestrate_turn(
    qe: QueryEngine,
    *,
    session_id: int,
    user_text: str,
    system_instruction: str,
    api_key: str,
    model: str,
    on_delta: Callable[[str], Coroutine[Any, Any, None]] | None = None,
    max_retries: int = 1,
    shell_allowlist: frozenset[str] | None = None,
    max_tool_rounds: int = 12,
    shell_max_output_bytes: int = 65536,
    shell_timeout_sec: float = 60.0,
    stream_chunk_idle_timeout_sec: float | None = 120.0,
    stream_leg_max_wall_sec: float | None = 600.0,
    rewire_after_tombstone: bool = True,
    enable_memory_tools: bool = True,
    memory_config: MemoryToolConfig | None = None,
    include_plan_tools: bool = False,
    file_config: FileToolConfig | None = None,
    max_session_tokens: int = 50000,
    on_file_guard_violation: Callable[[str, str, str], Coroutine[Any, Any, None]]
    | None = None,
    web_config: WebToolConfig | None = None,
    enable_list_session_web_sources: bool = False,
    debug_stream: bool = False,
) -> str:
    """
    Persist user once, then run one or more model legs with optional tool rounds.
    Retries only if no tool results were persisted for this user turn.
    On retry: StreamingToolExecutor.discard() on the failed attempt's executor.
    """
    dbg = is_stream_debug_on(debug_stream)
    user_uuid = await qe.persist_user(session_id, user_text)
    allow = shell_allowlist or frozenset()
    gemini_tool = build_agent_tools(
        allowed_exact_commands=allow,
        include_memory_tools=enable_memory_tools,
        include_plan_tools=include_plan_tools,
        include_file_tools=file_config is not None,
        include_web_search=web_config is not None and bool(web_config.serper_api_key),
        include_web_fetch=web_config is not None,
        include_list_session_web_sources=enable_list_session_web_sources,
    )
    log_stream(
        dbg,
        "orchestrator",
        "turn_start",
        f"session_id={session_id}",
        f"include_web_search={web_config is not None and bool(web_config.serper_api_key)}",
        f"include_web_fetch={web_config is not None}",
        f"web_tools_enabled={web_config is not None}",
    )
    legs_cap = max(1, max_tool_rounds)
    memory = memory_config if enable_memory_tools else None

    async def _read_plan_bound() -> str:
        return await qe.get_task_plan_json(session_id)

    async def _write_plan_bound(text: str) -> None:
        await qe.set_task_plan_json(session_id, text)

    plan_hooks: PlanToolHooks | None = (
        PlanToolHooks(read_plan=_read_plan_bound, write_plan=_write_plan_bound)
        if include_plan_tools
        else None
    )

    last_err: Exception | None = None
    for attempt in range(max_retries + 1):
        tools_were_persisted = [False]

        async def _token_usage_bound() -> dict[str, Any]:
            return await qe.get_session_token_usage(session_id)

        async def _web_sources_list_bound(lim: int) -> list[dict[str, Any]]:
            return await qe.list_web_sources(session_id, limit=lim)

        executor = StreamingToolExecutor(
            allowlist_exact=allow,
            max_output_bytes=shell_max_output_bytes,
            timeout_sec=shell_timeout_sec,
            memory=memory,
            plan_hooks=plan_hooks,
            token_usage=_token_usage_bound,
            file_config=file_config,
            web=web_config,
            web_sources_reader=_web_sources_list_bound
            if enable_list_session_web_sources
            else None,
            on_file_guard_violation=on_file_guard_violation,
        )
        try:
            return await _agentic_loop(
                qe,
                session_id=session_id,
                user_parent_uuid=user_uuid,
                system_instruction=system_instruction,
                api_key=api_key,
                model=model,
                gemini_tool=gemini_tool,
                on_delta=on_delta,
                legs_cap=legs_cap,
                shell_allowlist=allow,
                executor=executor,
                tools_were_persisted=tools_were_persisted,
                stream_chunk_idle_timeout_sec=stream_chunk_idle_timeout_sec,
                stream_leg_max_wall_sec=stream_leg_max_wall_sec,
                rewire_after_tombstone=rewire_after_tombstone,
                plan_tools_configured=plan_hooks is not None,
                file_tools_configured=file_config is not None,
                web_search_configured=web_config is not None
                and bool(web_config.serper_api_key),
                web_fetch_configured=web_config is not None,
                web_sources_list_configured=enable_list_session_web_sources,
                max_session_tokens=max_session_tokens,
                debug_stream=dbg,
            )
        except SessionTokenLimitExceeded:
            executor.discard()
            raise
        except Exception as e:
            last_err = e
            executor.discard()
            await qe.state_set("turn.fallback_generation", str(attempt + 1))
            if tools_were_persisted[0]:
                break
            if attempt >= max_retries:
                break
            await asyncio.sleep(0.25 * (attempt + 1))
    assert last_err is not None
    raise last_err


async def _agentic_loop(
    qe: QueryEngine,
    *,
    session_id: int,
    user_parent_uuid: str,
    system_instruction: str,
    api_key: str,
    model: str,
    gemini_tool: Any,
    on_delta: Callable[[str], Coroutine[Any, Any, None]] | None,
    legs_cap: int,
    shell_allowlist: frozenset[str],
    executor: StreamingToolExecutor,
    tools_were_persisted: list[bool],
    stream_chunk_idle_timeout_sec: float | None,
    stream_leg_max_wall_sec: float | None,
    rewire_after_tombstone: bool,
    plan_tools_configured: bool,
    file_tools_configured: bool,
    web_search_configured: bool,
    web_fetch_configured: bool,
    web_sources_list_configured: bool,
    max_session_tokens: int,
    debug_stream: bool,
) -> str:
    parent = user_parent_uuid

    for _ in range(legs_cap):
        chain = await qe.load_chain_for_api(session_id)
        gemini_contents = chain_rows_to_contents(chain)
        assistant_uuid = await qe.persist_assistant_begin(session_id, parent)
        tool_rows_this_leg: list[str] = []

        async def _td(s: str) -> None:
            if on_delta:
                await on_delta(s)

        try:
            leg = await stream_one_model_leg(
                api_key=api_key,
                model=model,
                system_instruction=system_instruction,
                contents=gemini_contents,
                tool=gemini_tool,
                on_text_delta=_td if on_delta else None,
                chunk_idle_timeout_sec=stream_chunk_idle_timeout_sec,
                leg_max_wall_sec=stream_leg_max_wall_sec,
            )
            fc_payload = (
                [{"name": c.name, "args": c.args, "id": c.id} for c in leg.function_calls]
                if leg.function_calls
                else None
            )
            meta: dict[str, Any] = {
                "model": model,
                "finish_reason": leg.finish_reason,
                "usage": leg.usage,
            }
            await qe.persist_assistant_finalize(
                assistant_uuid,
                leg.text,
                meta,
                function_calls=fc_payload,
            )
            usage_extras = json.dumps(leg.usage, default=str) if leg.usage else None
            await qe.record_usage(
                session_id,
                model=model,
                input_tokens=leg.usage.get("input_tokens")
                if isinstance(leg.usage.get("input_tokens"), int)
                else None,
                output_tokens=leg.usage.get("output_tokens")
                if isinstance(leg.usage.get("output_tokens"), int)
                else None,
                usage_extras_json=usage_extras,
            )
            usage_totals = await qe.get_session_token_usage(session_id)
            if usage_totals["total"] > max_session_tokens:
                await qe.append_action_log(
                    "session_token_limit_exceeded",
                    {
                        "message": "Session token limit exceeded",
                        "input_tokens": usage_totals["input_tokens"],
                        "output_tokens": usage_totals["output_tokens"],
                        "total": usage_totals["total"],
                        "limit": max_session_tokens,
                    },
                    session_id=session_id,
                )
                await qe.update_task(session_id, status="failed")
                raise SessionTokenLimitExceeded("Session token limit exceeded")
        except asyncio.CancelledError:
            await qe.tombstone(
                [assistant_uuid, *tool_rows_this_leg],
                session_id,
                rewire_orphans=rewire_after_tombstone,
            )
            raise
        except SessionTokenLimitExceeded:
            raise
        except Exception:
            await qe.tombstone(
                [assistant_uuid, *tool_rows_this_leg],
                session_id,
                rewire_orphans=rewire_after_tombstone,
            )
            raise

        if not leg.function_calls:
            if not leg.text.strip():
                log_stream(
                    debug_stream,
                    "orchestrator",
                    "empty_model_output",
                    f"finish_reason={leg.finish_reason!r}",
                    f"usage={leg.usage!r}",
                    f"function_calls={leg.function_calls!r}",
                    f"text_len={len(leg.text)}",
                )
                raise StreamFailed("empty model output")
            await qe.state_set("session.active_model", model)
            if leg.finish_reason:
                await qe.state_set("session.last_finish_reason", leg.finish_reason)
            return leg.text

        needs_shell = any(
            c.name == "run_allowlisted_shell" for c in leg.function_calls
        )
        if needs_shell and not shell_allowlist:
            raise StreamFailed("model requested shell but allowlist is empty")

        needs_plan = any(
            c.name in ("read_task_plan", "write_task_plan")
            for c in leg.function_calls
        )
        if needs_plan and not plan_tools_configured:
            raise StreamFailed(
                "model requested plan tools but plan tools are not configured"
            )

        needs_file = any(
            c.name
            in (
                "read_workspace_file",
                "write_workspace_file",
                "list_workspace_directory",
            )
            for c in leg.function_calls
        )
        if needs_file and not file_tools_configured:
            raise StreamFailed(
                "model requested file tools but file tools are not configured"
            )

        needs_web_search = any(c.name == "web_search" for c in leg.function_calls)
        if needs_web_search and not web_search_configured:
            raise StreamFailed(
                "model requested web_search but web search is not configured"
            )

        needs_web_fetch = any(c.name == "fetch_url_text" for c in leg.function_calls)
        if needs_web_fetch and not web_fetch_configured:
            raise StreamFailed(
                "model requested fetch_url_text but web fetch is not configured"
            )

        needs_ws_list = any(
            c.name == "list_session_web_sources" for c in leg.function_calls
        )
        if needs_ws_list and not web_sources_list_configured:
            raise StreamFailed(
                "model requested list_session_web_sources but it is not configured"
            )

        results = await executor.run_ordered(leg.function_calls)
        for tr in results:
            tid = await qe.persist_tool_result(
                session_id,
                parent_assistant_uuid=assistant_uuid,
                name=tr.call.name,
                tool_call_id=tr.call.id,
                response=tr.response,
            )
            tool_rows_this_leg.append(tid)
            await qe.record_web_tool_artifacts(
                session_id,
                tr.call.name,
                tr.call.args,
                tr.response,
            )
        tools_were_persisted[0] = True

        head = await qe.chain_head_uuid(session_id)
        if not head:
            raise StreamFailed("chain head missing after tool results")
        parent = head

    raise StreamFailed("max tool/model legs exceeded")
