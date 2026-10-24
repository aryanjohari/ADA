"""Structural time pack doors — start-shape NL + read routing helpers."""

from __future__ import annotations

import re
from typing import Any, Callable

from ada.life.time.date import is_time_read_shape, parse_time_date
from ada.life.time.intent import map_time_intent
from ada.life.utterance import strip_leading_filler

_TIME_START_SHAPE = re.compile(
    r"^(?:"
    r"i\s+started\s+\S.*"
    r"|i(?:['’]?m|\s+am)\s+starting\s+\S.*"
    r"|starting\s+\S.*"
    r"|i(?:['’]?m|\s+am)\s+\S.*"
    r")",
    re.IGNORECASE,
)


def is_time_start_utterance(text: str) -> bool:
    """Structural time-start NL — start-shapes only; hint optional.

    Inserted after meal / lift / gym start / gym end so those organs win.
    Bare spine labels without a start-shape are not a door.
    """
    raw = strip_leading_filler(text)
    if not raw:
        return False
    # Cross-domain fences — lazy so life.time can load before food/gym extract.
    from ada.harness.pack_router import (
        is_gym_end_utterance,
        is_gym_start_utterance,
        is_incomplete_lift_utterance,
        is_lift_log_utterance,
        is_meal_log_utterance,
    )

    if is_meal_log_utterance(raw) or is_lift_log_utterance(raw):
        return False
    if is_incomplete_lift_utterance(raw):
        return False
    if is_gym_start_utterance(raw) or is_gym_end_utterance(raw):
        return False
    lower = raw.lower()
    if lower.startswith("start focus") or lower.startswith("start timer"):
        return True
    return bool(_TIME_START_SHAPE.match(raw))


def route_time_read(
    raw: str,
    *,
    has_week_cue: Callable[[str], bool],
    route_from_pack: Callable[..., dict[str, Any] | None],
    config: dict[str, Any],
) -> dict[str, Any] | None:
    """Structural time day/week read. Not time_status / what's running."""
    if not is_time_read_shape(raw):
        return None
    if has_week_cue(raw):
        routed = route_from_pack("time_week", raw, raw, config=config)
        if routed is not None:
            routed["args"]["days"] = 7
        return routed
    parsed = parse_time_date(raw)
    if parsed is None:
        return None
    routed = route_from_pack("time_day", raw, raw, config=config)
    if routed is not None:
        routed["args"]["date"] = parsed
    return routed


def route_time_start_focus(
    raw: str,
    *,
    resolve_pack: Callable[..., dict[str, Any] | None],
    config: dict[str, Any],
) -> dict[str, Any]:
    """start focus / start timer YAML-independent branch."""
    mapped = map_time_intent(raw)
    pack = resolve_pack("time_start", config=config) or {}
    return {
        "verb": "time_start",
        "tool": "life_time_start",
        "args": mapped,
        "preferred_tools": list(pack.get("preferred_tools") or []),
        "spine": pack.get("spine"),
    }
