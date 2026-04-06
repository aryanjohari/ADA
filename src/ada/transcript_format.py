"""Message JSON packing — shared by PersistentState and QueryEngine."""

from __future__ import annotations

import json
import uuid
from typing import Any

ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"
ROLE_TOOL = "tool"
ROLE_SYSTEM = "system"


def new_uuid() -> str:
    return str(uuid.uuid4())


def pack_user_text(text: str) -> str:
    payload = {"parts": [{"type": "text", "text": text}]}
    return json.dumps(payload, ensure_ascii=False)


def pack_assistant_text(text: str, extra: dict[str, Any] | None = None) -> str:
    base: dict[str, Any] = {"parts": [{"type": "text", "text": text}]}
    if extra:
        base.update(extra)
    return json.dumps(base, ensure_ascii=False)


def pack_assistant_full(
    *,
    text: str,
    function_calls: list[dict[str, Any]] | None,
    meta: dict[str, Any] | None,
) -> str:
    parts: list[dict[str, Any]] = []
    if text.strip():
        parts.append({"type": "text", "text": text})
    if function_calls:
        for fc in function_calls:
            parts.append(
                {
                    "type": "function_call",
                    "name": fc.get("name") or "",
                    "args": fc.get("args") or {},
                    "id": fc.get("id"),
                }
            )
    if not parts:
        parts.append({"type": "text", "text": ""})
    base: dict[str, Any] = {"parts": parts}
    if meta:
        base["meta"] = meta
    return json.dumps(base, ensure_ascii=False)
