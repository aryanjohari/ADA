"""Relative/explicit date parsing for nutrition read routing."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from ada.logs.tz_util import preferred_tz_name, utc_to_local_day

_MONTHS: dict[str, int] = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}

_WEEK_CUES = re.compile(
    r"\b(?:this\s+week|past\s+week|last\s+7\s+days|last\s+seven\s+days)\b",
    re.IGNORECASE,
)
_NUTRITION_READ_SHAPE = re.compile(
    r"\b(?:eat|ate|eating|macros?|nutrition|protein|kcal|calories?|food\s+log|micros?|nutrients?)\b",
    re.IGNORECASE,
)
_ISO_DATE = re.compile(
    r"\b(20\d{2})[-/](0[1-9]|1[0-2])[-/](0[1-9]|[12]\d|3[01])\b"
)
_DAY_MONTH = re.compile(
    r"\b(?:on\s+)?(\d{1,2})(?:st|nd|rd|th)?(?:\s+of)?\s+"
    r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|"
    r"dec(?:ember)?)\b",
    re.IGNORECASE,
)
_MONTH_DAY = re.compile(
    r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|"
    r"dec(?:ember)?)\s+(\d{1,2})(?:st|nd|rd|th)?\b",
    re.IGNORECASE,
)


def local_today(*, paths=None) -> str:
    return utc_to_local_day(paths=paths)


def local_yesterday(*, paths=None) -> str:
    tz = ZoneInfo(preferred_tz_name(paths=paths))
    today = datetime.now(timezone.utc).astimezone(tz).date()
    return (today - timedelta(days=1)).isoformat()


def has_week_cue(utterance: str) -> bool:
    return bool(_WEEK_CUES.search(utterance or ""))


def is_nutrition_read_shape(utterance: str) -> bool:
    return bool(_NUTRITION_READ_SHAPE.search(utterance or ""))


def _month_key(token: str) -> int | None:
    return _MONTHS.get((token or "").strip().lower())


def _resolve_year(month: int, day: int, *, paths=None) -> int:
    tz = ZoneInfo(preferred_tz_name(paths=paths))
    now = datetime.now(timezone.utc).astimezone(tz)
    year = now.year
    try:
        candidate = datetime(year, month, day, tzinfo=tz).date()
    except ValueError:
        return year
    if candidate > now.date():
        year -= 1
    return year


def _format_day(year: int, month: int, day: int) -> str | None:
    try:
        return datetime(year, month, day).strftime("%Y-%m-%d")
    except ValueError:
        return None


def parse_nutrition_date(utterance: str, *, paths=None) -> str | None:
    """Return YYYY-MM-DD local day from utterance, or None if no date cue."""
    text = utterance or ""
    lower = text.lower()

    if re.search(r"\b(?:yesterday|last\s+night)\b", lower):
        return local_yesterday(paths=paths)
    if re.search(r"\btoday\b", lower):
        return local_today(paths=paths)

    iso = _ISO_DATE.search(text)
    if iso:
        return f"{iso.group(1)}-{iso.group(2)}-{iso.group(3)}"

    day_month = _DAY_MONTH.search(text)
    if day_month:
        month = _month_key(day_month.group(2))
        if month is not None:
            day = int(day_month.group(1))
            year = _resolve_year(month, day, paths=paths)
            return _format_day(year, month, day)

    month_day = _MONTH_DAY.search(text)
    if month_day:
        month = _month_key(month_day.group(1))
        if month is not None:
            day = int(month_day.group(2))
            year = _resolve_year(month, day, paths=paths)
            return _format_day(year, month, day)

    return None
