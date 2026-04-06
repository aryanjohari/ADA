"""Gemini streaming (google-genai) — text + manual function calling."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from google import genai
from google.genai import types

from ada.query_engine import ROLE_ASSISTANT, ROLE_TOOL, ROLE_USER
from ada.stream_types import CompletedFunctionCall, StreamLegResult


def chain_rows_to_contents(rows: list[dict[str, Any]]) -> list[types.Content]:
    """Map persisted transcript rows to Gemini `contents` (§12)."""
    contents: list[types.Content] = []
    tool_batch: list[dict[str, Any]] = []

    def flush_tool_batch() -> None:
        nonlocal tool_batch
        if not tool_batch:
            return
        parts_out: list[types.Part] = []
        for p in tool_batch:
            name = p.get("name") or ""
            resp = p.get("response") or {}
            parts_out.append(
                types.Part.from_function_response(
                    name=name,
                    response=resp if isinstance(resp, dict) else {"result": resp},
                )
            )
        contents.append(types.Content(role="tool", parts=parts_out))
        tool_batch = []

    for row in rows:
        role = row.get("role", ROLE_USER)
        if role == ROLE_ASSISTANT:
            flush_tool_batch()
            role = "model"
        elif role == ROLE_TOOL:
            for p in row.get("parts", []):
                if p.get("type") == "function_response":
                    tool_batch.append(p)
            continue
        else:
            flush_tool_batch()

        parts_out: list[types.Part] = []
        for p in row.get("parts", []):
            if p.get("type") == "text":
                t = p.get("text") or ""
                if t or role == "model":
                    parts_out.append(types.Part.from_text(text=t))
            elif p.get("type") == "function_call":
                raw_args = p.get("args") or {}
                if not isinstance(raw_args, dict):
                    raw_args = {}
                parts_out.append(
                    types.Part(
                        function_call=types.FunctionCall(
                            name=p.get("name") or "",
                            args=raw_args,
                        )
                    )
                )
        if not parts_out and role == "user":
            parts_out.append(types.Part.from_text(text=""))
        contents.append(types.Content(role=role, parts=parts_out))

    flush_tool_batch()
    return contents


def _fc_to_completed(fc: types.FunctionCall) -> CompletedFunctionCall:
    args = fc.args
    if args is None:
        args_d: dict[str, Any] = {}
    elif isinstance(args, dict):
        args_d = args
    else:
        md = getattr(args, "model_dump", None)
        if callable(md):
            args_d = md()
        else:
            args_d = dict(args)
    return CompletedFunctionCall(
        name=fc.name or "",
        args=args_d,
        id=getattr(fc, "id", None) or None,
    )


def _remember_fc(
    bucket: dict[str, types.FunctionCall], order: list[str], fc: types.FunctionCall
) -> None:
    key = getattr(fc, "id", None) or f"_anon_{len(order)}"
    if key not in bucket:
        order.append(key)
    bucket[key] = fc


async def stream_one_model_leg(
    *,
    api_key: str,
    model: str,
    system_instruction: str,
    contents: list[types.Content],
    tool: types.Tool | None,
    on_text_delta: Callable[[str], Awaitable[None]] | None = None,
) -> StreamLegResult:
    """
    One generate_content_stream leg with optional tools; manual function calling.
    """
    client = genai.Client(api_key=api_key)
    cfg = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=[tool] if tool else None,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(mode="AUTO")
        )
        if tool
        else None,
    )
    stream = await client.aio.models.generate_content_stream(
        model=model,
        contents=contents,
        config=cfg,
    )

    seen_text = ""
    text_buf: list[str] = []
    fc_order: list[str] = []
    fc_bucket: dict[str, types.FunctionCall] = {}
    usage: dict[str, Any] = {}
    finish_reason: str | None = None

    async for chunk in stream:
        um = getattr(chunk, "usage_metadata", None)
        if um:
            pt = getattr(um, "prompt_token_count", None)
            ct = getattr(um, "candidates_token_count", None)
            if pt is not None:
                usage["input_tokens"] = pt
            if ct is not None:
                usage["output_tokens"] = ct

        chunk_level_text = getattr(chunk, "text", None)

        cands = getattr(chunk, "candidates", None) or []
        for cand in cands:
            fr = getattr(cand, "finish_reason", None)
            if fr is not None:
                finish_reason = str(fr)
            content = getattr(cand, "content", None)
            if not content or not content.parts:
                continue
            for part in content.parts:
                pfc = getattr(part, "function_call", None)
                if pfc is not None:
                    _remember_fc(fc_bucket, fc_order, pfc)
                if not chunk_level_text:
                    ptext = getattr(part, "text", None)
                    if ptext:
                        text_buf.append(ptext)
                        if on_text_delta:
                            await on_text_delta(ptext)

        if chunk_level_text:
            t = chunk_level_text
            if t.startswith(seen_text):
                delta = t[len(seen_text) :]
                seen_text = t
            else:
                delta = t
                seen_text += t
            if delta:
                text_buf.append(delta)
                if on_text_delta:
                    await on_text_delta(delta)

    text = "".join(text_buf)
    calls = [_fc_to_completed(fc_bucket[k]) for k in fc_order if k in fc_bucket]
    return StreamLegResult(
        text=text,
        function_calls=calls,
        usage=usage,
        finish_reason=finish_reason,
    )


async def stream_generate_text(
    *,
    api_key: str,
    model: str,
    system_instruction: str,
    contents: list[types.Content],
) -> AsyncIterator[str]:
    """Yield incremental text fragments from Gemini streaming (no tools)."""
    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
    )
    stream = await client.aio.models.generate_content_stream(
        model=model,
        contents=contents,
        config=config,
    )
    seen = ""
    async for chunk in stream:
        t = getattr(chunk, "text", None)
        if t:
            if t.startswith(seen):
                delta = t[len(seen) :]
                seen = t
            else:
                delta = t
                seen += t
            if delta:
                yield delta
            continue
        cands = getattr(chunk, "candidates", None) or []
        for cand in cands:
            content = getattr(cand, "content", None)
            if not content:
                continue
            for part in content.parts or []:
                pt = getattr(part, "text", None)
                if pt:
                    yield pt
