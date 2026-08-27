"""Deterministic utterance → prefs.brief_include propose_edit args (M22)."""

from __future__ import annotations

import re
from typing import Any

from ada.memory.facts import BRIEF_INCLUDE_DEFAULT, BRIEF_INCLUDE_SECTIONS, load_prefs
from ada.io.paths import require_ada_data

# Spoken section aliases → brief_include section id.
_SECTION_ALIASES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b(?:open\s+)?gym(?:\s+session)?\b|\bworkout\b", re.I), "open_gym"),
    (re.compile(r"\bhabits?\b|\bstreaks?\b", re.I), "habits_due"),
    (re.compile(r"\bdues?\b|\btodos?\b|\bto-?dos?\b", re.I), "dues"),
    (re.compile(r"\bovernight\b|\bheal\b", re.I), "overnight"),
    (re.compile(r"\bmeal\s*gaps?\b|\bmeals?\b", re.I), "meal_gap"),
    (re.compile(r"\bnutrition\b|\bmacros?\b", re.I), "nutrition_headline"),
    (re.compile(r"\bcontinuity\b", re.I), "continuity"),
)

_EXCLUDE = re.compile(
    r"\b(?:don'?t|do\s+not|exclude|remove|hide|omit|without)\b",
    re.I,
)
_INCLUDE = re.compile(
    r"\b(?:add|include|put|show|keep)\b",
    re.I,
)
_BRIEF_CUE = re.compile(r"\bbrief\b|\btoday\s+(?:strip|card)\b", re.I)


def _current_include(*, paths=None) -> list[str]:
    prefs = load_prefs(paths or require_ada_data())
    raw = prefs.get("brief_include")
    if isinstance(raw, list) and raw:
        allowed = set(BRIEF_INCLUDE_SECTIONS)
        out = [str(x) for x in raw if str(x) in allowed]
        return out or list(BRIEF_INCLUDE_DEFAULT)
    return list(BRIEF_INCLUDE_DEFAULT)


def _mentioned_sections(text: str) -> list[str]:
    found: list[str] = []
    for pat, section in _SECTION_ALIASES:
        if pat.search(text) and section not in found:
            found.append(section)
    return found


def build_brief_include_args(utterance: str, *, paths=None) -> dict[str, Any]:
    """Parse teach-in-flow brief section prefs → propose_edit args (no write).

    Maps e.g. \"don't put gym in my morning brief\" → remove open_gym from include list.
    """
    raw = (utterance or "").strip()
    if not raw:
        return {"ok": False, "reason": "missing_utterance"}
    if not _BRIEF_CUE.search(raw):
        return {"ok": False, "reason": "not_brief_pref"}
    sections = _mentioned_sections(raw)
    if not sections:
        return {"ok": False, "reason": "no_section_mentioned"}

    current = _current_include(paths=paths)
    exclude = bool(_EXCLUDE.search(raw))
    include = bool(_INCLUDE.search(raw)) and not exclude
    if not exclude and not include:
        # Default teach posture for \"gym in brief\" talk: exclude when negated cue
        # already handled; bare mention without verb → no-op fail.
        return {"ok": False, "reason": "ambiguous_brief_pref", "sections": sections}

    proposed = list(current)
    if exclude:
        proposed = [s for s in proposed if s not in sections]
    else:
        for s in sections:
            if s not in proposed:
                proposed.append(s)

    return {
        "ok": True,
        "args": {
            "key": "prefs.brief_include",
            "value": proposed,
            "confirmed": False,
        },
        "proposed": proposed,
        "removed": sections if exclude else [],
        "added": sections if include else [],
        "existing": current,
    }
