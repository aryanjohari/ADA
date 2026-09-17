"""Deterministic utterance -> lift_log sets helper (M19a P0.1 / M24 / M26 v1.2)."""

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
# "flat bench 3x6 at 50kg" / "flat bench 3x6 @ 50" / "flat bench 3x6 @ 50kg"
_SETS_AT_LOAD_NAMED = re.compile(
    r"^(.+?)\s+(\d+)\s*[x×]\s*(\d+)\s*(?:at|@)\s*"
    r"(\d+(?:\.\d+)?)\s*(kg|kgs|lb|lbs)?\s*$",
    re.IGNORECASE,
)
# "3x6 at 50kg flat bench"
_SETS_AT_LOAD_NAME_AFTER = re.compile(
    r"^(\d+)\s*[x×]\s*(\d+)\s*(?:at|@)\s*"
    r"(\d+(?:\.\d+)?)\s*(kg|kgs|lb|lbs)?\s+(.+)$",
    re.IGNORECASE,
)
# Bare follow-on: "3x6 at 50kg" / "3x6 @ 50"
_SETS_AT_LOAD_BARE = re.compile(
    r"^(\d+)\s*[x×]\s*(\d+)\s*(?:at|@)\s*"
    r"(\d+(?:\.\d+)?)\s*(kg|kgs|lb|lbs)?\s*$",
    re.IGNORECASE,
)
# Bare follow-on: "50kg x6" / "50 kg x 6"
_LOAD_X_REPS_BARE = re.compile(
    r"^(\d+(?:\.\d+)?)\s*(kg|kgs|lb|lbs)\s*[x×]\s*(\d+)\s*(?:reps?)?\s*$",
    re.IGNORECASE,
)
_LOAD_TOKEN = re.compile(
    r"^\d+(?:\.\d+)?\s*(?:kg|kgs|lb|lbs)$",
    re.IGNORECASE,
)

FOLLOW_ON_ASK = (
    "Need the exercise — log a named set in this open session first, "
    "then 3x6 at 50kg."
)
INCOMPLETE_ASK = (
    "Need load and reps for that lift — say it like 30kg x 12 "
    "(or 30×12/35×12/40×8)."
)
NEED_KG_ASK = "Need kg or lb for that lift — say it like 60kg x6."
# Bare "60x6" / "3 x 6" — sets×reps or load×reps with no unit (M26 v1.3).
_BARE_NXM = re.compile(
    r"^\d+(?:\.\d+)?\s*[x×]\s*\d+\s*$",
    re.IGNORECASE,
)


def lift_utterance_body(text: str) -> str:
    """Strip optional ``log lift:`` / ``lift:`` prefix."""
    return _LOG_PREFIX.sub("", (text or "").strip()).strip()


def is_bare_nxm_without_unit(text: str) -> bool:
    """Whole-utterance ``N x M`` / ``NxM`` with no kg/lb and no exercise name."""
    return bool(_BARE_NXM.match(lift_utterance_body(text)))


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


def _expand_loaded_sets(
    name: str, sets_n: int, reps: int, load: float, unit: str | None
) -> list[dict[str, Any]]:
    kg = _load_kg(load, unit)
    label = name.strip()
    return [
        {"exercise_name": label, "load_kg": kg, "reps": reps}
        for _ in range(sets_n)
    ]


def _is_nameless_follow_on(text: str) -> bool:
    raw = (text or "").strip()
    return bool(_SETS_AT_LOAD_BARE.match(raw) or _LOAD_X_REPS_BARE.match(raw))


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


def _parse_follow_on(text: str, name: str) -> list[dict[str, Any]]:
    label = (name or "").strip()
    if not label:
        return []
    m = _SETS_AT_LOAD_BARE.match(text)
    if m:
        return _expand_loaded_sets(
            label,
            int(m.group(1)),
            int(m.group(2)),
            float(m.group(3)),
            m.group(4),
        )
    m = _LOAD_X_REPS_BARE.match(text)
    if m:
        return [
            {
                "exercise_name": label,
                "load_kg": _load_kg(float(m.group(1)), m.group(2)),
                "reps": int(m.group(3)),
            }
        ]
    return []


def _parse_set(part: str, *, default_name: str | None = None) -> list[dict[str, Any]]:
    text = (part or "").strip()
    if not text:
        return []
    ladder = _parse_ladder(text)
    if ladder:
        return ladder
    m = _SETS_AT_LOAD_NAMED.match(text)
    if m:
        name = m.group(1).strip()
        if name and not _LOAD_TOKEN.match(name):
            return _expand_loaded_sets(
                name,
                int(m.group(2)),
                int(m.group(3)),
                float(m.group(4)),
                m.group(5),
            )
    m = _SETS_AT_LOAD_NAME_AFTER.match(text)
    if m:
        name = m.group(5).strip()
        if name and not _LOAD_TOKEN.match(name):
            return _expand_loaded_sets(
                name,
                int(m.group(1)),
                int(m.group(2)),
                float(m.group(3)),
                m.group(4),
            )
    m = _SET.match(text)
    if m:
        name = m.group(1).strip()
        if name and not _LOAD_TOKEN.match(name):
            return [
                {
                    "exercise_name": name,
                    "load_kg": _load_kg(float(m.group(2)), m.group(3)),
                    "reps": int(m.group(4)),
                }
            ]
    if _is_nameless_follow_on(text):
        return _parse_follow_on(text, default_name or "")
    m = _MULTI.match(text)
    if m:
        name = m.group(3).strip()
        if name and not _LOAD_TOKEN.match(name) and not name.lower().startswith("at "):
            sets_n = int(m.group(1))
            reps = int(m.group(2))
            return [_bodyweight_set(name, reps) for _ in range(sets_n)]
    m = _REPS_ONLY.match(text)
    if m:
        name = m.group(1).strip()
        if _LOAD_TOKEN.match(name):
            if default_name:
                return _parse_follow_on(text, default_name)
            return []
        return [_bodyweight_set(name, int(m.group(2)))]
    m = _REPS_FIRST.match(text)
    if m:
        name = m.group(2).strip()
        if name and not _LOAD_TOKEN.match(name):
            return [_bodyweight_set(name, int(m.group(1)))]
    return []


def build_lift_log_args(
    utterance: str,
    *,
    follow_on_name: str | None = None,
) -> dict[str, Any]:
    """Parse lift NL into complete sets[] — fail closed if incomplete (M24).

    Nameless ``3x6 at 50kg`` / ``50kg x6`` bind to *follow_on_name* (last
    exercise in the currently OPEN session). No name and no follow-on → ask,
    no invented kg, no guessed exercise.
    """
    raw = lift_utterance_body(utterance)
    inherited = (follow_on_name or "").strip() or None
    if not raw:
        return {
            "ok": False,
            "sets": [],
            "utterance": utterance,
            "reason": "empty",
            "ask": "Need the lift — say it like lat pulldown 30kg x 12.",
        }

    # Bare 60x6 / 3x6 — never bodyweight name "60", never invent kg.
    if is_bare_nxm_without_unit(raw):
        return {
            "ok": False,
            "sets": [],
            "utterance": utterance,
            "reason": "missing_load_unit",
            "ask": NEED_KG_ASK,
        }

    # Prefer whole-utterance ladder before comma/slash multi-exercise split.
    ladder = _parse_ladder(raw)
    if ladder:
        return {"ok": True, "sets": ladder, "utterance": utterance}

    if _is_nameless_follow_on(raw) and not inherited:
        return {
            "ok": False,
            "sets": [],
            "utterance": utterance,
            "reason": "follow_on_no_open",
            "ask": FOLLOW_ON_ASK,
        }

    parts = [p.strip() for p in _SPLIT.split(raw) if p.strip()]
    sets: list[dict[str, Any]] = []
    incomplete: list[str] = []
    current_name = inherited
    follow_on_miss = False
    for part in parts:
        parsed = _parse_set(part, default_name=current_name)
        if not parsed:
            if _is_nameless_follow_on(part) and not current_name:
                follow_on_miss = True
            incomplete.append(part)
            continue
        sets.extend(parsed)
        last_name = str(parsed[-1].get("exercise_name") or "").strip()
        if last_name:
            current_name = last_name

    if incomplete or not sets:
        if follow_on_miss and not sets:
            ask = FOLLOW_ON_ASK
            reason = "follow_on_no_open"
        else:
            ask = INCOMPLETE_ASK
            reason = "incomplete_parse"
        return {
            "ok": False,
            "sets": [],
            "utterance": utterance,
            "reason": reason,
            "incomplete": incomplete,
            "ask": ask,
        }
    return {"ok": True, "sets": sets, "utterance": utterance}
