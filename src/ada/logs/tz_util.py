"""Timezone helpers for local_day bucketing (M19a)."""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from ada.memory.facts import DEFAULT_PREFS, load_prefs


def preferred_tz_name(*, paths=None) -> str:
    prefs = load_prefs(paths)
    return str(prefs.get("preferred_tz") or DEFAULT_PREFS["preferred_tz"])


def utc_to_local_day(ts: datetime | None = None, *, paths=None) -> str:
    """Return YYYY-MM-DD in operator TZ."""
    ts = ts or datetime.now(timezone.utc)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    tz = ZoneInfo(preferred_tz_name(paths=paths))
    return ts.astimezone(tz).strftime("%Y-%m-%d")
