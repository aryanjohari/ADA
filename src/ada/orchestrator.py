"""One-turn streaming orchestration (MVP: single leg, no tools)."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any

from ada.adapters.gemini_stream import chain_rows_to_contents, stream_generate_text
from ada.query_engine import QueryEngine


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
) -> str:
    """
    Persist user once, then stream assistant with retries (§8 light).
    Each retry tombstones the failed assistant shell only.
    """
    user_uuid = await qe.persist_user(session_id, user_text)
    last_err: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return await _stream_assistant_leg(
                qe,
                session_id=session_id,
                parent_user_uuid=user_uuid,
                system_instruction=system_instruction,
                api_key=api_key,
                model=model,
                on_delta=on_delta,
            )
        except Exception as e:
            last_err = e
            await qe.state_set("turn.fallback_generation", str(attempt + 1))
            if attempt >= max_retries:
                break
            await asyncio.sleep(0.25 * (attempt + 1))
    assert last_err is not None
    raise last_err


async def _stream_assistant_leg(
    qe: QueryEngine,
    *,
    session_id: int,
    parent_user_uuid: str,
    system_instruction: str,
    api_key: str,
    model: str,
    on_delta: Callable[[str], Coroutine[Any, Any, None]] | None,
) -> str:
    chain = await qe.load_chain_for_api(session_id)
    gemini_contents = chain_rows_to_contents(chain)
    assistant_uuid = await qe.persist_assistant_begin(
        session_id, parent_user_uuid
    )

    pieces: list[str] = []
    try:
        async for frag in stream_generate_text(
            api_key=api_key,
            model=model,
            system_instruction=system_instruction,
            contents=gemini_contents,
        ):
            pieces.append(frag)
            cur = "".join(pieces)
            qe.schedule_assistant_append(assistant_uuid, cur)
            if on_delta:
                await on_delta(frag)
        final = "".join(pieces)
        if not final.strip():
            raise StreamFailed("empty model output")
        meta = {"model": model}
        await qe.persist_assistant_finalize(assistant_uuid, final, meta)
        await qe.state_set("session.active_model", model)
        return final
    except asyncio.CancelledError:
        await qe.tombstone([assistant_uuid], session_id)
        raise
    except Exception:
        await qe.tombstone([assistant_uuid], session_id)
        raise
