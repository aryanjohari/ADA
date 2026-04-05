"""Gemini streaming (google-genai) — MVP text deltas only."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from google import genai
from google.genai import types

from ada.query_engine import ROLE_ASSISTANT, ROLE_USER


def chain_rows_to_contents(rows: list[dict[str, Any]]) -> list[types.Content]:
    """Map persisted transcript rows to Gemini `contents`."""
    contents: list[types.Content] = []
    for row in rows:
        role = row.get("role", ROLE_USER)
        if role == ROLE_ASSISTANT:
            role = "model"  # Gemini API role name
        parts_out: list[types.Part] = []
        for p in row.get("parts", []):
            if p.get("type") == "text":
                t = p.get("text") or ""
                if t or role == "model":
                    parts_out.append(types.Part.from_text(text=t))
            # function_call / function_response: Phase 2
        if not parts_out and role == "user":
            parts_out.append(types.Part.from_text(text=""))
        contents.append(types.Content(role=role, parts=parts_out))
    return contents


async def stream_generate_text(
    *,
    api_key: str,
    model: str,
    system_instruction: str,
    contents: list[types.Content],
) -> AsyncIterator[str]:
    """
    Yield incremental text fragments from Gemini streaming.
    MVP: no tools / function calls.
    """
    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
    )
    stream = await client.aio.models.generate_content_stream(
        model=model,
        contents=contents,
        config=config,
    )
    # Chunks may expose cumulative `text` or small increments; normalize to deltas.
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
        # Fallback: walk candidates/parts (treat part texts as deltas)
        cands = getattr(chunk, "candidates", None) or []
        for cand in cands:
            content = getattr(cand, "content", None)
            if not content:
                continue
            for part in content.parts or []:
                pt = getattr(part, "text", None)
                if pt:
                    yield pt
