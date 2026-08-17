"""Capture classification stub (M19a)."""

from __future__ import annotations

import re
from typing import Any

_REMIND_RE = re.compile(r"\b(remind|reminder|ping me)\b", re.I)
_TODO_RE = re.compile(r"\b(todo|buy|pick up|call|email)\b", re.I)
_FACT_RE = re.compile(r"\b(remember that|fact:|my .+ is)\b", re.I)


def classify_capture(text: str, *, kind_hint: str | None = None) -> dict[str, Any]:
    text = (text or "").strip()
    if kind_hint and kind_hint != "unknown":
        return {"kind": kind_hint, "confidence": 0.9}
    if _REMIND_RE.search(text):
        return {"kind": "remind", "confidence": 0.75}
    if _FACT_RE.search(text):
        return {"kind": "fact", "confidence": 0.7}
    if _TODO_RE.search(text):
        return {"kind": "todo", "confidence": 0.7}
    if len(text) < 4:
        return {"kind": "unknown", "confidence": 0.3}
    return {"kind": "note", "confidence": 0.5}
