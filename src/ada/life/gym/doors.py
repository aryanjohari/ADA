"""Structural gym pack doors — start/end/lift NL + read routing helpers."""

from __future__ import annotations

import re
from typing import Any, Callable

from ada.life.gym.date import has_week_cue, is_gym_read_shape, parse_gym_date
from ada.life.gym.spine import is_bare_nxm_without_unit, lift_utterance_body
from ada.life.utterance import strip_leading_filler

_LIFT_LINE = re.compile(r"\b(?:\d+(?:\.\d+)?)\s*(?:kg|kgs|lb|lbs)\s*x\s*\d+\b", re.IGNORECASE)
# Multi-set ladder without requiring "log lift:" (M24 pack preference).
_LIFT_LADDER = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:kg|kgs|lb|lbs)?\s*[x×]\s*\d+\s*"
    r"(?:reps?\s+)?(?:\d+(?:\.\d+)?\s*(?:kg|kgs|lb|lbs)?\s*[x×]\s*\d+)",
    re.IGNORECASE,
)
# "3x6 at 50kg" / "flat bench 3x6 @ 50" — sets×reps with load (M26 v1.2).
_LIFT_SETS_AT_LOAD = re.compile(
    r"\b\d+\s*[x×]\s*\d+\s*(?:at|@)\s*\d+(?:\.\d+)?\s*(?:kg|kgs|lb|lbs)?\b",
    re.IGNORECASE,
)
_GYM_START_SHAPE = re.compile(
    r"(?:"
    r"(?:i(?:['’]?m|\s+am)\s+)?at\s+(?:the\s+)?gym"
    r"|(?:i\s+)?start(?:ed|ing)?\s+(?:a\s+|the\s+)?gym"
    r")\.?\s*$",
    re.IGNORECASE,
)
_GYM_END_SHAPE = re.compile(
    r"(?:"
    r"\b(?:i\s+)?(?:finish(?:ed)?|done|end(?:ed)?|close[d]?)\s+"
    r"(?:the\s+|a\s+)?(?:gym|workout)\b"
    r"|\bgym\s+done\b"
    r")",
    re.IGNORECASE,
)
# Whole-utterance exercise name (catalog/custom fold) — not a sentence.
_NAME_ONLY_LIFT = re.compile(
    r"^[A-Za-z][A-Za-z'+-]*(?:\s+[A-Za-z][A-Za-z'+-]*){0,5}$"
)
_NAME_ONLY_CHAT = re.compile(
    r"^(?:i|i['’]m|im|we|what|how|did|do|why)\b",
    re.IGNORECASE,
)
_LIFT_PREFIX = re.compile(r"^(?:log\s+lift\b|lift\s*:)", re.IGNORECASE)


def gym_read_takes_priority(text: str) -> bool:
    """Week / relative-day gym reads win over start/end/lift writes."""
    raw = (text or "").strip()
    if not is_gym_read_shape(raw):
        return False
    if has_week_cue(raw):
        return True
    return parse_gym_date(raw) is not None


def is_gym_start_utterance(text: str) -> bool:
    """Structural gym-start NL — independent of pack_hint match."""
    raw = strip_leading_filler(text)
    if not raw or gym_read_takes_priority(raw):
        return False
    return bool(_GYM_START_SHAPE.match(raw))


def is_gym_end_utterance(text: str) -> bool:
    """Structural gym-end NL — does not steal habit `done:` / due `done:`."""
    raw = strip_leading_filler(text)
    if not raw or gym_read_takes_priority(raw):
        return False
    lower = raw.lower()
    if lower.startswith("done:") or lower.startswith("habit "):
        return False
    return bool(_GYM_END_SHAPE.match(raw))


def is_lift_log_utterance(text: str) -> bool:
    """Structural lift capture — independent of pack_hint match."""
    raw = strip_leading_filler(text)
    if not raw or gym_read_takes_priority(raw):
        return False
    if _LIFT_PREFIX.match(raw):
        return True
    if _LIFT_LINE.search(raw) or _LIFT_LADDER.search(raw) or _LIFT_SETS_AT_LOAD.search(raw):
        return True
    return False


def _is_complete_lift_shape(body: str) -> bool:
    return bool(
        _LIFT_LINE.search(body)
        or _LIFT_LADDER.search(body)
        or _LIFT_SETS_AT_LOAD.search(body)
    )


def is_incomplete_lift_utterance(text: str) -> bool:
    """Miss-path lift: ask, no session, no row. Not a write. Not gym_start.

    Matches bare ``60x6`` / ``3x6`` (no kg/lb) and name-only catalog/custom
    folds. Does not steal gym reads, start/end, complete kg×reps, or chat
    that is not an exercise bind (``I like bench``).
    """
    raw = strip_leading_filler(text)
    if not raw or gym_read_takes_priority(raw):
        return False
    if is_gym_start_utterance(raw) or is_gym_end_utterance(raw):
        return False
    body = lift_utterance_body(raw)
    if not body:
        return False
    if _is_complete_lift_shape(body):
        return False
    if is_bare_nxm_without_unit(body):
        return True
    if _NAME_ONLY_CHAT.match(body):
        return False
    if not _NAME_ONLY_LIFT.match(body):
        return False
    from ada.logs.gym import exercise_name_known

    return exercise_name_known(body)


def lift_log_fast_path_args(text: str) -> dict[str, Any] | None:
    """Return {utterance} for build_lift_log_args, or None."""
    raw = strip_leading_filler(text)
    if not raw or not is_lift_log_utterance(raw):
        return None
    lower = raw.lower()
    if lower.startswith("log lift:") or lower.startswith("lift:"):
        body = raw.split(":", 1)[1].strip() if ":" in raw else raw
        return {"utterance": body or raw}
    return {"utterance": raw}


def route_gym_read(
    raw: str,
    *,
    route_from_pack: Callable[..., dict[str, Any] | None],
    config: dict[str, Any],
) -> dict[str, Any] | None:
    """Structural gym read: week window or explicit/relative day. Not gym_status."""
    if not is_gym_read_shape(raw):
        return None
    if has_week_cue(raw):
        routed = route_from_pack("gym_week", raw, raw, config=config)
        if routed is not None:
            routed["args"]["days"] = 7
        return routed
    parsed = parse_gym_date(raw)
    if parsed is None:
        return None
    routed = route_from_pack("gym_day", raw, raw, config=config)
    if routed is not None:
        routed["args"]["date"] = parsed
    return routed
