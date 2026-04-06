"""Agentic turn: stream legs + allowlisted tools (claude_logic §6–7)."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable, Coroutine
from typing import Any

from ada.adapters.gemini_stream import chain_rows_to_contents, stream_one_model_leg
from ada.query_engine import QueryEngine
from ada.tool_executor import MemoryToolConfig, StreamingToolExecutor
from ada.tools.registry import build_agent_tools


class StreamFailed(Exception):
    """Raised when the model stream ends without usable output."""


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
) -> str:
    """
    Persist user once, then run one or more model legs with optional tool rounds.
    Retries only if no tool results were persisted for this user turn.
    On retry: StreamingToolExecutor.discard() on the failed attempt's executor.
    """
    user_uuid = await qe.persist_user(session_id, user_text)
    allow = shell_allowlist or frozenset()
    gemini_tool = build_agent_tools(
        allowed_exact_commands=allow,
        include_memory_tools=enable_memory_tools,
    )
    legs_cap = max(1, max_tool_rounds)
    memory = memory_config if enable_memory_tools else None

    last_err: Exception | None = None
    for attempt in range(max_retries + 1):
        tools_were_persisted = [False]
        executor = StreamingToolExecutor(
            allowlist_exact=allow,
            max_output_bytes=shell_max_output_bytes,
            timeout_sec=shell_timeout_sec,
            memory=memory,
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
            )
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
        except asyncio.CancelledError:
            await qe.tombstone(
                [assistant_uuid, *tool_rows_this_leg],
                session_id,
                rewire_orphans=rewire_after_tombstone,
            )
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
        tools_were_persisted[0] = True

        head = await qe.chain_head_uuid(session_id)
        if not head:
            raise StreamFailed("chain head missing after tool results")
        parent = head

    raise StreamFailed("max tool/model legs exceeded")
