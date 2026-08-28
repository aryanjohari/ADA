"""Deterministic utterance -> lift_log sets helper (M19a P0.1 / M24 multi-set)."""

from __future__ import annotations

import re
from typing import Any

_LB_TO_KG = 0.453592
_LOG_PREFIX = re.compile(r"^(?:log\s+(?:lift\s+)?:?\s*|lift\s*:?\s*)", re.IGNORECASE)
# name + load×reps (optional "reps" word)
_SET = re.compile(
    r"^(.+?)\s+(\d+(?:\.\d+)?)\s*(kg|kgs|lb|lbs)\s*[x×]\s*(\d+)\s*(?:reps?)?\s*$",
    re.IGNORECASE,
)
_MULTI = re.compile(
    r"^(\d+)\s*[x×]\s*(\d+)\s+(.+?)\s*$",
    re.IGNORECASE,
)
_REPS_ONLY = re.compile(
    r"^(.+?)\s+[x×]\s*(\d+)\s*(?:reps?)?\s*$",
    re.IGNORECASE,
)
_REPS_FIRST = re.compile(
    r"^(\d+)\s+(.+?)\s*$",
    re.IGNORECASE,
)
# Same-exercise ladder: "lat pulldown 30kg x 12 reps 35kg x12 reps 40kg x 8"
_LADDER = re.compile(
    r"^(.+?)\s+((?:\d+(?:\.\d+)?\s*(?:kg|kgs|lb|lbs)\s*[x×]\s*\d+\s*(?:reps?)?\s*)+)$",
    re.IGNORECASE,
)
_LADDER_STEP = re.compile(
    r"(\d+(?:\.\d+)?)\s*(kg|kgs|lb|lbs)\s*[x×]\s*(\d+)\s*(?:reps?)?",
    re.IGNORECASE,
)
# Slash ladder after name: "lat pulldown 30×12/35×12/40×8" or "30kg x12/35kg x12"
_SLASH_LADDER = re.compile(
    r"^(.+?)\s+((?:\d+(?:\.\d+)?\s*(?:kg|kgs|lb|lbs)?\s*[x×]\s*\d+\s*)"
    r"(?:/\s*\d+(?:\.\d+)?\s*(?:kg|kgs|lb|lbs)?\s*[x×]\s*\d+\s*)+)$",
    re.IGNORECASE,
)
_SLASH_STEP = re.compile(
    r"(\d+(?:\.\d+)?)\s*(kg|kgs|lb|lbs)?\s*[x×]\s*(\d+)",
    re.IGNORECASE,
)
_SPLIT = re.compile(r"\s*(?:,|/| and | then )\s*", re.IGNORECASE)


def _bodyweight_set(exercise_name: str, reps: int) -> dict[str, Any]:
    return {
        "exercise_name": exercise_name.strip(),
        "load_kg": None,
        "reps": reps,
    }


def _load_kg(load: float, unit: str | None) -> float:
    u = (unit or "kg").lower()
    if u.startswith("lb"):
        return round(load * _LB_TO_KG, 2)
    return load


def _parse_ladder(text: str) -> list[dict[str, Any]]:
    """Same-exercise multi-set ladders (space-separated or slash)."""
    m = _LADDER.match(text)
    if m:
        name = m.group(1).strip()
        steps = list(_LADDER_STEP.finditer(m.group(2)))
        if len(steps) >= 2 and name:
            return [
                {
                    "exercise_name": name,
                    "load_kg": _load_kg(float(s.group(1)), s.group(2)),
                    "reps": int(s.group(3)),
                }
                for s in steps
            ]

    m = _SLASH_LADDER.match(text)
    if m:
        name = m.group(1).strip()
        steps = list(_SLASH_STEP.finditer(m.group(2)))
        if len(steps) >= 2 and name:
            default_unit = "kg"
            out: list[dict[str, Any]] = []
            for s in steps:
                unit = s.group(2) or default_unit
                if s.group(2):
                    default_unit = s.group(2)
                out.append(
                    {
                        "exercise_name": name,
                        "load_kg": _load_kg(float(s.group(1)), unit),
                        "reps": int(s.group(3)),
                    }
                )
            return out
    return []


def _parse_set(part: str) -> list[dict[str, Any]]:
    text = (part or "").strip()
    if not text:
        return []
    ladder = _parse_ladder(text)
    if ladder:
        return ladder
    m = _SET.match(text)
    if m:
        return [
            {
                "exercise_name": m.group(1).strip(),
                "load_kg": _load_kg(float(m.group(2)), m.group(3)),
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
    """Parse lift NL into complete sets[] — fail closed if incomplete (M24)."""
    raw = _LOG_PREFIX.sub("", (utterance or "").strip()).strip()
    if not raw:
        return {
            "ok": False,
            "sets": [],
            "utterance": utterance,
            "reason": "empty",
            "ask": "Need the lift — say it like lat pulldown 30kg x 12.",
        }

    # Prefer whole-utterance ladder before comma/slash multi-exercise split.
    ladder = _parse_ladder(raw)
    if ladder:
        return {"ok": True, "sets": ladder, "utterance": utterance}

    parts = [p.strip() for p in _SPLIT.split(raw) if p.strip()]
    sets: list[dict[str, Any]] = []
    incomplete: list[str] = []
    for part in parts:
        parsed = _parse_set(part)
        if not parsed:
            incomplete.append(part)
            continue
        sets.extend(parsed)

    if incomplete or not sets:
        ask = (
            "Need load and reps for that lift — say it like 30kg x 12 "
            "(or 30×12/35×12/40×8)."
        )
        return {
            "ok": False,
            "sets": [],
            "utterance": utterance,
            "reason": "incomplete_parse",
            "incomplete": incomplete,
            "ask": ask,
        }
    return {"ok": True, "sets": sets, "utterance": utterance}
