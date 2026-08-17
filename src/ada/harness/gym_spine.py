"""Deterministic utterance -> lift_log sets helper (M19a P0.1)."""

from __future__ import annotations

import re
from typing import Any

_LB_TO_KG = 0.453592
_SET = re.compile(
    r"^(.+?)\s+(\d+(?:\.\d+)?)\s*(kg|kgs|lb|lbs)\s*[x×]\s*(\d+)\s*$",
    re.IGNORECASE,
)
_MULTI = re.compile(
    r"^(\d+)\s*[x×]\s*(\d+)\s+(.+?)\s*$",
    re.IGNORECASE,
)
_REPS_ONLY = re.compile(
    r"^(.+?)\s+[x×]\s*(\d+)\s*$",
    re.IGNORECASE,
)
_REPS_FIRST = re.compile(
    r"^(\d+)\s+(.+?)\s*$",
    re.IGNORECASE,
)
_SPLIT = re.compile(r"\s*(?:,|/| and | then )\s*", re.IGNORECASE)


def _bodyweight_set(exercise_name: str, reps: int) -> dict[str, Any]:
    return {
        "exercise_name": exercise_name.strip(),
        "load_kg": None,
        "reps": reps,
    }


def _parse_set(part: str) -> list[dict[str, Any]]:
    text = (part or "").strip()
    if not text:
        return []
    m = _SET.match(text)
    if m:
        load = float(m.group(2))
        unit = m.group(3).lower()
        if unit.startswith("lb"):
            load = round(load * _LB_TO_KG, 2)
        return [
            {
                "exercise_name": m.group(1).strip(),
                "load_kg": load,
                "reps": int(m.group(4)),
            }
        ]
    m = _MULTI.match(text)
    if m:
        sets_n = int(m.group(1))
        reps = int(m.group(2))
        name = m.group(3).strip()
        return [_bodyweight_set(name, reps) for _ in range(sets_n)]
    m = _REPS_ONLY.match(text)
    if m:
        return [_bodyweight_set(m.group(1), int(m.group(2)))]
    m = _REPS_FIRST.match(text)
    if m:
        return [_bodyweight_set(m.group(2), int(m.group(1)))]
    return []


def build_lift_log_args(utterance: str) -> dict[str, Any]:
    raw = (utterance or "").strip()
    if not raw:
        return {"ok": False, "sets": [], "utterance": utterance}
    parts = [p.strip() for p in _SPLIT.split(raw) if p.strip()]
    sets: list[dict[str, Any]] = []
    for part in parts:
        sets.extend(_parse_set(part))
    return {"ok": bool(sets), "sets": sets, "utterance": utterance}
