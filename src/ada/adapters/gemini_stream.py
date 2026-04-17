"""Gemini streaming (google-genai) — text + manual function calling."""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from google import genai
from google.genai import types

from ada.stream_debug import is_stream_debug_on, log_stream
from ada.stream_types import CompletedFunctionCall, StreamLegResult
from ada.transcript_format import ROLE_ASSISTANT, ROLE_TOOL, ROLE_USER


class StreamTimeout(Exception):
    """No chunk within idle window, or entire leg exceeded wall-clock max."""



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


def _stable_fc_key(fc: types.FunctionCall) -> str:
    """Dedupe streamed calls: anonymous rounds no longer use list position (fragile)."""
    fid = getattr(fc, "id", None) or None
    if fid:
        return str(fid)
    name = fc.name or ""
    try:
        sig = json.dumps(fc.args or {}, sort_keys=True, default=str)
    except TypeError:
        sig = str(fc.args or {})
    return f"_noid_{name}|{sig}"


def _remember_fc(
    bucket: dict[str, types.FunctionCall], order: list[str], fc: types.FunctionCall
) -> None:
    key = _stable_fc_key(fc)
    if key not in bucket:
        order.append(key)
    bucket[key] = fc


def _tool_call_to_function_call(raw: object) -> types.FunctionCall | None:
    """Map genai 1.7+ ``Part.tool_call`` (server ToolCall) to executable FunctionCall names."""
    if raw is None:
        return None
    tool_call_cls = getattr(types, "ToolCall", None)
    if tool_call_cls is not None and isinstance(raw, tool_call_cls):
        ttype = raw.tool_type
        args = dict(raw.args or {})
        tid = raw.id
    elif isinstance(raw, dict):
        ttype = raw.get("tool_type") or raw.get("toolType")
        args = dict(raw.get("args") or {})
        tid = raw.get("id")
        if not ttype and not args and not tid:
            return None
    else:
        return None

    tsv = ""
    if ttype is not None:
        tsv = str(getattr(ttype, "value", None) or ttype)
    u = tsv.upper()

    name: str | None = None
    out_args: dict[str, Any] = args

    if "GOOGLE_SEARCH" in u and "WEB" in u:
        name = "web_search"
        if "query" not in out_args:
            for k in ("q", "search_query", "searchQuery"):
                if k in out_args:
                    out_args = {**out_args, "query": str(out_args[k])}
                    break
    elif "URL_CONTEXT" in u:
        name = "fetch_url_text"
        urls = out_args.get("urls")
        if not urls:
            uone = out_args.get("url") or out_args.get("URL")
            if isinstance(uone, str):
                urls = [uone]
        if urls:
            out_args = {
                "urls": [str(x) for x in urls]
                if isinstance(urls, (list, tuple))
                else [str(urls)]
            }
    if not name:
        return None
    return types.FunctionCall(id=tid, name=name, args=out_args)


def _fc_from_part(part: object) -> types.FunctionCall | None:
    """Extract a FunctionCall from a streamed part (Part, dict, or loose shapes).

    Some stream chunks expose tool calls only under alternate keys or in
    ``model_dump()`` while ``part.function_call`` is unset; the SDK still warns
    when reading ``chunk.text`` because ``function_call`` exists on the wire.
    """
    if part is None:
        return None
    pfc = getattr(part, "function_call", None)
    if isinstance(pfc, types.FunctionCall):
        return pfc
    if pfc is not None and isinstance(pfc, dict):
        return types.FunctionCall.model_validate(pfc)

    tm = _tool_call_to_function_call(getattr(part, "tool_call", None))
    if tm is not None:
        return tm

    if isinstance(part, dict):
        raw = part.get("function_call") or part.get("functionCall")
        if raw is not None:
            if isinstance(raw, types.FunctionCall):
                return raw
            if isinstance(raw, dict):
                return types.FunctionCall.model_validate(raw)
        raw_tc = part.get("tool_call") or part.get("toolCall")
        tm = _tool_call_to_function_call(raw_tc)
        if tm is not None:
            return tm
        return None
    md = getattr(part, "model_dump", None)
    if callable(md):
        try:
            d = md(mode="python", exclude_none=False)
        except TypeError:
            try:
                d = md()
            except Exception:
                d = None
        except Exception:
            d = None
        if isinstance(d, dict):
            raw = d.get("function_call") or d.get("functionCall")
            if raw is not None:
                if isinstance(raw, types.FunctionCall):
                    return raw
                if isinstance(raw, dict):
                    return types.FunctionCall.model_validate(raw)
            raw_tc = d.get("tool_call") or d.get("toolCall")
            tm = _tool_call_to_function_call(raw_tc)
            if tm is not None:
                return tm
    return None


def _part_text_delta(part: object) -> str | None:
    """Non-thought text from a single part, or None if absent."""
    if isinstance(part, dict):
        t = part.get("text")
        thought = part.get("thought")
    else:
        t = getattr(part, "text", None)
        thought = getattr(part, "thought", None)
    if isinstance(thought, bool) and thought:
        return None
    if isinstance(t, str) and t:
        return t
    return None


def _clip(s: str | None, n: int = 200) -> str:
    if s is None:
        return "None"
    t = s.replace("\n", "\\n")
    return t if len(t) <= n else t[:n] + "…"


def _describe_part(idx: int, part: object) -> str:
    bits: list[str] = [f"p{idx}"]
    fc = getattr(part, "function_call", None)
    if fc is not None:
        nm = getattr(fc, "name", None) or "?"
        bits.append(f"fc={nm!r}")
    tc = getattr(part, "tool_call", None)
    if tc is not None:
        tt = getattr(tc, "tool_type", None)
        tv = getattr(tt, "value", None) or tt
        bits.append(f"tool={tv!r}")
    tx = getattr(part, "text", None)
    if isinstance(tx, str) and tx:
        bits.append(f"text_len={len(tx)}")
    if getattr(part, "thought", None):
        bits.append("thought")
    if len(bits) == 1:
        bits.append("(no fc/tool/text)")
    return "[" + " ".join(bits) + "]"


def _merge_usage_metadata(into: dict[str, Any], um: object) -> None:
    if um is None:
        return
    dump = getattr(um, "model_dump", None)
    if callable(dump):
        try:
            d = dump()
            if isinstance(d, dict):
                into["usage_metadata"] = d
                return
        except Exception:
            pass
    for attr in (
        "prompt_token_count",
        "candidates_token_count",
        "total_token_count",
        "cached_content_token_count",
        "thoughts_token_count",
        "tool_use_prompt_token_count",
    ):
        v = getattr(um, attr, None)
        if v is not None:
            into[attr] = v


async def stream_one_model_leg(
    *,
    api_key: str,
    model: str,
    system_instruction: str,
    contents: list[types.Content],
    tool: types.Tool | None,
    on_text_delta: Callable[[str], Awaitable[None]] | None = None,
    chunk_idle_timeout_sec: float | None = 120.0,
    leg_max_wall_sec: float | None = 600.0,
    debug_stream: bool = False,
) -> StreamLegResult:
    """
    One generate_content_stream leg with optional tools; manual function calling.
    """
    dbg = is_stream_debug_on(debug_stream)
    decl_n = 0
    if tool and getattr(tool, "function_declarations", None):
        decl_n = len(tool.function_declarations or [])
    log_stream(
        dbg,
        "stream",
        "leg_start",
        f"model={model!r}",
        f"contents_messages={len(contents)}",
        f"tool_function_declarations={decl_n}",
    )

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

    aiter = stream.__aiter__()
    loop_start = time.monotonic()
    chunk_idx = 0

    async def _next_chunk() -> object:
        if chunk_idle_timeout_sec is not None and chunk_idle_timeout_sec > 0:
            return await asyncio.wait_for(aiter.__anext__(), timeout=chunk_idle_timeout_sec)
        return await aiter.__anext__()

    while True:
        if leg_max_wall_sec is not None and leg_max_wall_sec > 0:
            if time.monotonic() - loop_start > leg_max_wall_sec:
                raise StreamTimeout("stream leg exceeded wall-clock limit")
        try:
            chunk = await _next_chunk()
        except StopAsyncIteration:
            break
        except asyncio.TimeoutError:
            raise StreamTimeout("no stream chunk within idle timeout") from None

        chunk_idx += 1
        fc_before = len(fc_order)

        um = getattr(chunk, "usage_metadata", None)
        if um:
            _merge_usage_metadata(usage, um)
            pt = getattr(um, "prompt_token_count", None)
            ct = getattr(um, "candidates_token_count", None)
            if pt is not None:
                usage["input_tokens"] = pt
            if ct is not None:
                usage["output_tokens"] = ct

        chunk_level_text = getattr(chunk, "text", None)

        cands = getattr(chunk, "candidates", None) or []
        if dbg:
            cand_summaries: list[str] = []
            for ci, cand in enumerate(cands):
                content = getattr(cand, "content", None)
                if not content:
                    cand_summaries.append(f"c{ci}:no_content")
                    continue
                parts = getattr(content, "parts", None) or []
                if not parts:
                    cand_summaries.append(f"c{ci}:empty_parts")
                    continue
                part_lines = [_describe_part(pi, p) for pi, p in enumerate(parts)]
                cand_summaries.append(f"c{ci}:" + " ".join(part_lines))
            sdk_fc = getattr(chunk, "function_calls", None)
            sdk_fc_n = len(sdk_fc) if sdk_fc else 0
            log_stream(
                dbg,
                "stream",
                f"chunk={chunk_idx}",
                f"candidates={len(cands)}",
                f"chunk.text={_clip(chunk_level_text)!r}",
                f"sdk_function_calls={sdk_fc_n}",
                "parts:",
                *cand_summaries,
            )

        for cand in cands:
            fr = getattr(cand, "finish_reason", None)
            if fr is not None:
                finish_reason = str(fr)
            content = getattr(cand, "content", None)
            if not content or not content.parts:
                continue
            for part in content.parts:
                pfc = _fc_from_part(part)
                if pfc is not None:
                    _remember_fc(fc_bucket, fc_order, pfc)
                if not chunk_level_text:
                    ptext = _part_text_delta(part)
                    if ptext:
                        text_buf.append(ptext)
                        if on_text_delta:
                            await on_text_delta(ptext)

        # First-candidate helper; stable keys dedupe against the parts walk above.
        extra_fcs = getattr(chunk, "function_calls", None) or []
        for pfc in extra_fcs:
            if pfc is not None:
                _remember_fc(fc_bucket, fc_order, pfc)

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

        if dbg:
            added_fc = len(fc_order) - fc_before
            keys = list(fc_order)
            log_stream(
                dbg,
                "stream",
                f"chunk={chunk_idx}_done",
                f"new_fc_this_chunk={added_fc}",
                f"fc_keys_total={keys}",
            )

    text = "".join(text_buf)
    calls = [_fc_to_completed(fc_bucket[k]) for k in fc_order if k in fc_bucket]
    log_stream(
        dbg,
        "stream",
        "leg_end",
        f"text_len={len(text)}",
        f"text_preview={_clip(text) if text else repr(text)}",
        f"function_calls_n={len(calls)}",
        f"names={[c.name for c in calls]}",
        f"finish_reason={finish_reason!r}",
        f"usage_keys={list(usage.keys())}",
    )
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
                pt = _part_text_delta(part)
                if pt:
                    yield pt
