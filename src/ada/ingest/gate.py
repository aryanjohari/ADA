"""Optional LLM gate for RSS ingest: score relevance from title + summary only."""

from __future__ import annotations

import json
import logging
from typing import Any

from google import genai
from google.genai import types

log = logging.getLogger("ada.ingest.gate")

_GATE_SYSTEM = """You evaluate RSS/Atom entries for a local knowledge base.
Return JSON only with keys:
- relevance_score: number from 0 to 1 (higher = more useful to keep indexed).
- tags: optional array of short topical tag strings (max 8 entries, each max 80 chars).

No other keys; no markdown or explanation outside JSON."""


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


async def score_feed_entry(
    api_key: str,
    *,
    title: str,
    summary: str,
    model: str,
    max_output_tokens: int | None = None,
) -> tuple[float, list[str]]:
    """
    Call Gemini with title + summary only. On any failure returns (1.0, []).
    """
    block = f"title: {title}\n\nsummary_or_description:\n{summary}".strip()
    if not block:
        return 1.0, []
    cfg_kw: dict[str, Any] = {
        "system_instruction": _GATE_SYSTEM,
        "response_mime_type": "application/json",
        "temperature": 0.2,
    }
    if max_output_tokens is not None:
        cfg_kw["max_output_tokens"] = max_output_tokens
    try:
        client = genai.Client(api_key=api_key)
        resp = await client.aio.models.generate_content(
            model=model,
            contents=[
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=block)],
                )
            ],
            config=types.GenerateContentConfig(**cfg_kw),
        )
        raw = (getattr(resp, "text", None) or "").strip()
        data = json.loads(raw)
    except Exception as e:
        log.warning("ingest gate failed: %s", e)
        return 1.0, []
    try:
        rs = float(data.get("relevance_score", 1.0))
    except (TypeError, ValueError):
        rs = 1.0
    rs = _clamp01(rs)
    extra_tags: list[str] = []
    raw_tags = data.get("tags")
    if isinstance(raw_tags, list):
        for t in raw_tags[:8]:
            s = str(t).strip()
            if s:
                extra_tags.append(s[:80])
    return rs, extra_tags
