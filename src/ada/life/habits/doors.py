"""Structural habit pack doors — do/miss NL + read routing helpers."""

from __future__ import annotations

import re
from typing import Any, Callable

from ada.life.habits.date import has_week_cue, is_habit_read_shape, parse_habit_date
from ada.life.utterance import strip_leading_filler

# Phone NL: "Habit done skincare" / "habit done: skincare" — wrappers, name is a slot.
_HABIT_DONE_NL = re.compile(
    r"^(?:habit\s+)?(?:done|tick|logged)\s*:?\s*(.+)$",
    re.IGNORECASE,
)
_HABIT_MISS_NL = re.compile(
    r"^(?:habit\s+)?miss(?:ed)?\s*:?\s*(.+)$",
    re.IGNORECASE,
)


def is_habit_do_utterance(text: str) -> bool:
    """Wrapper pack door for habit_do — name is a slot, not a YAML row.

    Hint optional: wrappers force the verb even if pack_hint is missing.
    Bare labels (skincare / laundry) without a wrapper are not a door.
    """
    raw = strip_leading_filler(text)
    if not raw:
        return False
    lower = raw.lower()
    matched = _HABIT_DONE_NL.match(raw)
    if not matched or not matched.group(1).strip():
        return False
    return (
        lower.startswith("habit ")
        or lower.startswith("habit\t")
        or lower.startswith("tick ")
        or "habit done" in lower
        or "habit tick" in lower
    )


def is_habit_miss_utterance(text: str) -> bool:
    """Wrapper pack door for habit_miss — habit in string, or starts with miss."""
    raw = strip_leading_filler(text)
    if not raw:
        return False
    lower = raw.lower()
    matched = _HABIT_MISS_NL.match(raw)
    if not matched or not matched.group(1).strip():
        return False
    return "habit" in lower or lower.startswith("miss")


def route_habit_read(
    raw: str,
    *,
    route_from_pack: Callable[..., dict[str, Any] | None],
    config: dict[str, Any],
) -> dict[str, Any] | None:
    """Structural habit day/week read. Not undated habits today / streak_show."""
    if not is_habit_read_shape(raw):
        return None
    if has_week_cue(raw):
        routed = route_from_pack("habit_week", raw, raw, config=config)
        if routed is not None:
            routed["args"]["days"] = 7
        return routed
    parsed = parse_habit_date(raw)
    if parsed is None:
        return None
    routed = route_from_pack("habit_day", raw, raw, config=config)
    if routed is not None:
        routed["args"]["date"] = parsed
    return routed
