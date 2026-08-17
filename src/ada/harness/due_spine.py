"""Deterministic utterance → open_loop upsert args (M19a P0.2)."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from ada.logs.tz_util import preferred_tz_name
from ada.memory import open_loops as loops_mod

_WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}
_LEAD = re.compile(
    r"^(?:add\s+due:\s*|done:\s*|remind:\s*|"
    r"gotta(?:\s+finish)?\s+|"
    r"i\s+need\s+to\s+finish\s+|"
    r"remind\s+me(?:\s+to)?\s+)",
    re.IGNORECASE,
)
_BY_WEEKDAY = re.compile(
    r"\bby\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    re.IGNORECASE,
)
_TOMORROW = re.compile(r"\btomorrow\b", re.IGNORECASE)
_AT_TIME = re.compile(
    r"\bat\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b",
    re.IGNORECASE,
)
_ISO = re.compile(
    r"\b(\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)?)\b"
)


def _now_local(*, paths=None) -> datetime:
    tz = ZoneInfo(preferred_tz_name(paths=paths))
    return datetime.now(tz)


def _to_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _apply_time(day: datetime, hour: int, minute: int) -> datetime:
    return day.replace(hour=hour, minute=minute, second=0, microsecond=0)


def _end_of_day(day: datetime) -> datetime:
    return day.replace(hour=23, minute=59, second=0, microsecond=0)


def _parse_clock(match: re.Match[str]) -> tuple[int, int]:
    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    ampm = (match.group(3) or "").lower()
    if ampm == "pm" and hour < 12:
        hour += 12
    elif ampm == "am" and hour == 12:
        hour = 0
    hour = max(0, min(23, hour))
    minute = max(0, min(59, minute))
    return hour, minute


def _parse_when(text: str, *, paths=None) -> tuple[str | None, str]:
    """Return (iso_utc, remainder_without_time_phrases)."""
    now = _now_local(paths=paths)
    remainder = text
    iso_hit = _ISO.search(text)
    weekday_hit = _BY_WEEKDAY.search(text)
    tomorrow_hit = _TOMORROW.search(text)
    clock_hit = _AT_TIME.search(text)

    target: datetime | None = None
    if iso_hit:
        raw = iso_hit.group(1).replace(" ", "T")
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            parsed = None
        if parsed is not None:
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=now.tzinfo)
            target = parsed
            remainder = remainder.replace(iso_hit.group(0), " ")
    elif weekday_hit:
        want = _WEEKDAYS[weekday_hit.group(1).lower()]
        ahead = (want - now.weekday()) % 7
        target = now + timedelta(days=ahead)
        remainder = remainder.replace(weekday_hit.group(0), " ")
    elif tomorrow_hit:
        target = now + timedelta(days=1)
        remainder = remainder.replace(tomorrow_hit.group(0), " ")

    if clock_hit:
        hour, minute = _parse_clock(clock_hit)
        remainder = remainder.replace(clock_hit.group(0), " ")
        day = target or now
        stamped = _apply_time(day, hour, minute)
        if target is None and stamped <= now:
            stamped = stamped + timedelta(days=1)
        target = stamped
    elif target is not None and iso_hit is None:
        target = _end_of_day(target)

    iso = _to_iso(target) if target is not None else None
    cleaned = re.sub(r"\s+", " ", remainder).strip(" :-")
    return iso, cleaned


def _title_from(utterance: str, *, paths=None) -> tuple[str, str | None]:
    raw = (utterance or "").strip()
    stripped = _LEAD.sub("", raw, count=1).strip()
    when, title = _parse_when(stripped, paths=paths)
    title = re.sub(r"\s+", " ", title).strip(" :-")
    return title, when


def _open_todos(*, paths=None) -> list[dict[str, Any]]:
    return loops_mod.list_loops(kind="todo", status="open", paths=paths)


def _match_open_todos(needle: str, *, paths=None) -> list[dict[str, Any]]:
    q = (needle or "").strip().lower()
    if not q:
        return []
    hits: list[dict[str, Any]] = []
    for item in _open_todos(paths=paths):
        hay = f"{item.get('title') or ''} {item.get('text') or ''}".lower()
        if q in hay:
            hits.append(item)
    return hits


def build_due_upsert_args(
    utterance: str,
    *,
    verb: str,
    paths=None,
) -> dict[str, Any]:
    """Parse due/remind/done utterance into gateway upsert args (no write)."""
    title, when = _title_from(utterance, paths=paths)
    if verb == "due_done":
        if not title:
            return {"ok": False, "reason": "missing_title", "matches": []}
        matches = _match_open_todos(title, paths=paths)
        if len(matches) != 1:
            return {
                "ok": False,
                "reason": "missing_life_receipt",
                "match_count": len(matches),
                "matches": matches,
                "title": title,
            }
        hit = matches[0]
        return {
            "ok": True,
            "args": {
                "id": hit.get("id"),
                "kind": "todo",
                "status": "done",
                "text": hit.get("text") or title,
            },
            "title": title,
        }

    if not title:
        return {"ok": False, "reason": "missing_title"}

    args: dict[str, Any] = {
        "kind": "todo",
        "status": "open",
        "text": title,
        "title": title,
    }
    if verb == "remind":
        if when:
            args["remind_at"] = when
    elif when:
        args["due_at"] = when
    return {"ok": True, "args": args, "title": title, "when": when}
