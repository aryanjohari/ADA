"""Plan artifacts for M15 — structured steps from Plan-mode assistant text.

SSE + runs/ JSONL only (no YAML store in Tier A). Gateway still denies writes in Plan.
"""

from __future__ import annotations

import json
import re
import uuid
from typing import Any

_JSON_FENCE = re.compile(
    r"```(?:json)?\s*\n(\{.*?\})\s*\n```",
    re.DOTALL | re.IGNORECASE,
)
_NUMBERED = re.compile(
    r"^\s*(?:\d+[\.\)]\s+|[-*•]\s+)(.+\S)\s*$",
    re.MULTILINE,
)


def new_plan_id() -> str:
    return f"plan_{uuid.uuid4().hex[:12]}"


def _step(text: str, idx: int) -> dict[str, str]:
    return {"id": f"s{idx}", "text": text.strip()}


def _from_steps_list(raw_steps: list[Any], *, raw_text: str, source_run: str | None) -> dict[str, Any]:
    steps: list[dict[str, str]] = []
    for i, item in enumerate(raw_steps, start=1):
        if isinstance(item, str) and item.strip():
            steps.append(_step(item, i))
        elif isinstance(item, dict):
            t = str(item.get("text") or item.get("title") or "").strip()
            if t:
                steps.append(_step(t, i))
    if not steps:
        return _single_prose(raw_text, source_run=source_run)
    return {
        "plan_id": new_plan_id(),
        "status": "proposed",
        "source_run": source_run,
        "steps": steps,
        "raw_text": raw_text,
    }


def _single_prose(text: str, *, source_run: str | None) -> dict[str, Any] | None:
    cleaned = (text or "").strip()
    if not cleaned:
        return None
    return {
        "plan_id": new_plan_id(),
        "status": "proposed",
        "source_run": source_run,
        "steps": [_step(cleaned, 1)],
        "raw_text": cleaned,
    }


def parse_plan_from_assistant(
    text: str | None,
    *,
    source_run: str | None = None,
) -> dict[str, Any] | None:
    """Build a plan artifact from Plan-mode assistant text.

    Prefer fenced JSON ``{"steps":[...]}``; else numbered/bulleted lists (≥2);
    else a single step from the whole prose.
    """
    raw = (text or "").strip()
    if not raw:
        return None

    fence = _JSON_FENCE.search(raw)
    if fence:
        try:
            obj = json.loads(fence.group(1))
        except json.JSONDecodeError:
            obj = None
        if isinstance(obj, dict) and isinstance(obj.get("steps"), list):
            return _from_steps_list(obj["steps"], raw_text=raw, source_run=source_run)

    # Bare JSON object (no fence)
    if raw.startswith("{") and '"steps"' in raw:
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            obj = None
        if isinstance(obj, dict) and isinstance(obj.get("steps"), list):
            return _from_steps_list(obj["steps"], raw_text=raw, source_run=source_run)

    lines = _NUMBERED.findall(raw)
    if len(lines) >= 2:
        return _from_steps_list(lines, raw_text=raw, source_run=source_run)

    return _single_prose(raw, source_run=source_run)
