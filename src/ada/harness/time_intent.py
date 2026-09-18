"""Utterance → kind/label for time blocks (M19a)."""

from __future__ import annotations

import re
from typing import Any

_SLEEP = re.compile(r"\b(going to sleep|going to bed|bedtime|goodnight)\b", re.I)
_WAKE = re.compile(r"\b(woke up|wake up|morning)\b", re.I)
_COOKING = re.compile(r"\b(breakfast|meal prep|cooking|lunch prep|dinner prep)\b", re.I)
_DEEP = re.compile(r"\b(deep work|phd|writing|focus block)\b", re.I)
_MAINT = re.compile(r"\b(admin chores|maintenance|email triage)\b", re.I)
# Most-specific first — "I'm starting X" must not become label "starting X".
_START_SHAPE_PREFIXES = (
    re.compile(r"^start\s+(?:focus|timer)\s*:?\s*", re.I),
    re.compile(r"^i\s+started\s+", re.I),
    re.compile(r"^i(?:['’]?m|\s+am)\s+starting\s+", re.I),
    re.compile(r"^starting\s+", re.I),
    re.compile(r"^i(?:['’]?m|\s+am)\s+", re.I),
)


def strip_time_start_shape(utterance: str) -> str:
    """Drop start-shape prefixes so label is the named thing, not the door."""
    text = (utterance or "").strip()
    for pat in _START_SHAPE_PREFIXES:
        stripped = pat.sub("", text, count=1).strip()
        if stripped != text:
            return stripped or text
    return text


def map_time_intent(utterance: str) -> dict[str, Any]:
    raw = (utterance or "").strip()
    text = strip_time_start_shape(raw)
    if _SLEEP.search(text) or _SLEEP.search(raw):
        return {"kind": "sleep", "label": None}
    if _COOKING.search(text):
        return {"kind": "cooking", "label": text[:80]}
    if _DEEP.search(text):
        return {"kind": "focus_deep", "label": text[:80]}
    if _MAINT.search(text):
        return {"kind": "focus_maint", "label": text[:80]}
    if _WAKE.search(text) or _WAKE.search(raw):
        return {"kind": "wake", "label": None}
    return {"kind": "custom", "label": text[:80] or "activity"}
