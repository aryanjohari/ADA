"""Relative/explicit date parsing for gym read routing.

Parallel to nutrition_date — not inside _NUTRITION_READ_SHAPE.
Reuses the same local-day / week-cue parsers so yesterday / this week
mean the same calendar window as food.
"""

from __future__ import annotations

import re

from ada.harness.nutrition_date import (  # noqa: F401 — re-export for gym callers
    has_week_cue,
    local_today,
    local_yesterday,
    parse_nutrition_date as parse_gym_date,
)

# Lift / gym / workout — not eat/ate/macros (those stay nutrition).
_GYM_READ_SHAPE = re.compile(
    r"\b(?:lifts?|lifted|gym|workouts?|tonnage)\b",
    re.IGNORECASE,
)


def is_gym_read_shape(utterance: str) -> bool:
    return bool(_GYM_READ_SHAPE.search(utterance or ""))
