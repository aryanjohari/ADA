"""Utterance → kind/label for time blocks (M19a)."""

from __future__ import annotations

import re
from typing import Any

_SLEEP = re.compile(r"\b(going to sleep|going to bed|bedtime|goodnight)\b", re.I)
_WAKE = re.compile(r"\b(woke up|wake up|morning)\b", re.I)
_COOKING = re.compile(r"\b(breakfast|meal prep|cooking|lunch prep|dinner prep)\b", re.I)
_DEEP = re.compile(r"\b(deep work|phd|writing|focus block)\b", re.I)
_MAINT = re.compile(r"\b(admin chores|maintenance|email triage)\b", re.I)


def map_time_intent(utterance: str) -> dict[str, Any]:
    text = (utterance or "").strip()
    if _SLEEP.search(text):
        return {"kind": "sleep", "label": None}
    if _WAKE.search(text):
        return {"kind": "wake", "label": None}
    if _COOKING.search(text):
        return {"kind": "cooking", "label": text[:80]}
    if _DEEP.search(text):
        return {"kind": "focus_deep", "label": text[:80]}
    if _MAINT.search(text):
        return {"kind": "focus_maint", "label": text[:80]}
    return {"kind": "custom", "label": text[:80] or "activity"}
