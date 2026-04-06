"""Compact transcript lines for dream prompts."""

from __future__ import annotations

import json
from typing import Any


def compact_message_line(
    session_id: int, role: str, content_json: str, *, max_len: int = 450
) -> str:
    try:
        payload: dict[str, Any] = json.loads(content_json)
    except json.JSONDecodeError:
        return f"[sess={session_id} {role}] <invalid json>"
    parts = payload.get("parts") or []
    bits: list[str] = []
    for p in parts:
        pt = p.get("type")
        if pt == "text":
            bits.append((p.get("text") or "").strip())
        elif pt == "function_call":
            bits.append(f"[call {p.get('name')}]")
        elif pt == "function_response":
            bits.append(f"[result {p.get('name')}]")
    text = " ".join(x for x in bits if x).strip()
    text = " ".join(text.split())
    if len(text) > max_len:
        text = text[:max_len] + "…"
    return f"[sess={session_id} {role}] {text}"
