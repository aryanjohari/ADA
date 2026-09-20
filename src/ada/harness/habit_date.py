"""Relative/explicit date parsing for habit day/week read routing.

Parallel to time_date / gym_date. Reuses the same local-day / week-cue
parsers so yesterday / this week mean the same calendar window as food.
"""

from __future__ import annotations

import re

from ada.harness.nutrition_date import (  # noqa: F401 — re-export for habit callers
    has_week_cue,
    local_today,
    local_yesterday,
    parse_nutrition_date as parse_habit_date,
)

# Named habit day/week reads — not undated "habits today" / streak_show.
_HABIT_READ_SHAPE = re.compile(
    r"\b(?:what\s+habits|habits\s+this\s+week|habit\s+this\s+week)\b",
    re.IGNORECASE,
)


def is_habit_read_shape(utterance: str) -> bool:
    return bool(_HABIT_READ_SHAPE.search(utterance or ""))
