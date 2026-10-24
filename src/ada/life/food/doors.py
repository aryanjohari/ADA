"""Structural meal / nutrition pack doors — NL capture + read routing helpers."""

from __future__ import annotations

import re
from typing import Any, Callable

from ada.life.food.date import has_week_cue, is_nutrition_read_shape, parse_nutrition_date
from ada.life.utterance import strip_leading_filler

_MEAL_SLOT = re.compile(
    r"\b(?:to|for)\s+(?:an?\s+|the\s+)?(breakfast|lunch|dinner|snacks?)\b",
    re.IGNORECASE,
)
# STT often hears "Long meal" for "Log meal"; allow optional "meal" + article before slot.
_ADD_MEAL = re.compile(
    r"^(?:add|log|long)\s+(?:meal\s+)?(.+?)\s+(?:to|for)\s+(?:an?\s+|the\s+)?"
    r"(breakfast|lunch|dinner|snacks?)\b",
    re.IGNORECASE,
)
# Multi-item meal: log/add + qty cue + and/+ — slot optional (M26 path integrity).
_MEAL_MULTI = re.compile(
    r"\b(?:log|add|long)\b.+"
    r"(?:\d+(?:\.\d+)?\s*(?:g|grams?|kg|oz|ml|cups?|cup|tbsp|tsp)?|"
    r"(?:a|an|one|two|three|four|five|six|seven|eight|nine|ten)\s+)"
    r".+\b(?:and|\+)\b",
    re.IGNORECASE,
)
# Bare grams + and/+ + meal slot (no log verb) — still pack fence.
_MEAL_MULTI_BARE = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:g|grams?|kg|oz)?\b.+\b(?:and|\+)\b.+"
    r"\b(?:for|to)\s+(?:an?\s+|the\s+)?(?:breakfast|lunch|dinner|snacks?)\b",
    re.IGNORECASE,
)
_MEAL_SINGLE = re.compile(
    r"^(?:add|log|long)\s+(?:meal\s+)?"
    r"(\d+(?:\.\d+)?\s*(?:g|grams?|kg|oz|ml|cups?)?\s*.+)$",
    re.I,
)


def _normalize_meal_slot(raw_slot: str) -> str:
    slot = (raw_slot or "").strip().lower()
    if slot == "snacks":
        return "snack"
    return slot


def is_meal_log_utterance(text: str) -> bool:
    """Structural meal capture — independent of pack_hint match."""
    raw = strip_leading_filler(text)
    if not raw:
        return False
    if _ADD_MEAL.match(raw):
        return True
    if _MEAL_SINGLE.match(raw):
        return True
    if _MEAL_MULTI.search(raw) or _MEAL_MULTI_BARE.search(raw):
        return True
    return False


def meal_log_fast_path_args(text: str) -> dict[str, Any] | None:
    """Return {utterance, meal_slot} for build_meal_log_args, or None."""
    raw = strip_leading_filler(text)
    if not raw:
        return None

    meal = _ADD_MEAL.match(raw)
    if meal:
        slot_raw = meal.group(2)
        body = _meal_body_from_raw(raw, slot=slot_raw)
        return {
            "utterance": body or meal.group(1).strip(),
            "meal_slot": _normalize_meal_slot(slot_raw),
        }

    meal_single = _MEAL_SINGLE.match(raw)
    if meal_single:
        return {
            "utterance": meal_single.group(1).strip(),
            "meal_slot": None,
        }

    if _MEAL_MULTI.search(raw) or _MEAL_MULTI_BARE.search(raw):
        slot_m = _MEAL_SLOT.search(raw)
        slot = _normalize_meal_slot(slot_m.group(1)) if slot_m else None
        body = _meal_body_from_raw(raw, slot=slot_m.group(1) if slot_m else None)
        return {"utterance": body, "meal_slot": slot}

    return None


def _meal_body_from_raw(raw: str, *, slot: str | None = None) -> str:
    """Strip log/add prefix and trailing meal-slot clause from meal NL."""
    body = raw
    for prefix in ("log meal:", "long meal:", "log meal", "long meal", "log ", "add ", "long "):
        if body.lower().startswith(prefix):
            body = body[len(prefix) :].strip()
            break
    if slot:
        body = re.sub(
            r"\s+(?:to|for)\s+(?:an?\s+|the\s+)?"
            + re.escape(slot)
            + r"s?\b.*$",
            "",
            body,
            flags=re.IGNORECASE,
        ).strip()
    return body


def route_nutrition_read(
    raw: str,
    *,
    route_from_pack: Callable[..., dict[str, Any] | None],
    config: dict[str, Any],
) -> dict[str, Any] | None:
    """Structural nutrition read: week window or explicit/relative day."""
    if not is_nutrition_read_shape(raw):
        return None
    if has_week_cue(raw):
        routed = route_from_pack("nutrition_week", raw, raw, config=config)
        if routed is not None:
            routed["args"]["days"] = 7
        return routed
    parsed = parse_nutrition_date(raw)
    if parsed is None:
        return None
    routed = route_from_pack("nutrition_day", raw, raw, config=config)
    if routed is not None:
        routed["args"]["date"] = parsed
    return routed
