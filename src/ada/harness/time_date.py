"""Relative/explicit date parsing for time day/week read routing.

Parallel to gym_date / nutrition_date. Reuses the same local-day / week-cue
parsers so yesterday / this week mean the same calendar window as food and gym.
"""

from __future__ import annotations

import re

from ada.harness.nutrition_date import (  # noqa: F401 — re-export for time callers
    has_week_cue,
    local_today,
    local_yesterday,
    parse_nutrition_date as parse_time_date,
)

# Named-block day/week reads — not "what's running" / start timer / gym / meals.
_TIME_READ_SHAPE = re.compile(
    r"\b(?:what\s+did\s+i\s+track|tracked|time\s+this\s+week)\b",
    re.IGNORECASE,
)


def is_time_read_shape(utterance: str) -> bool:
    return bool(_TIME_READ_SHAPE.search(utterance or ""))
