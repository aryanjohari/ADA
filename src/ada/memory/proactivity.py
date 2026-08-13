"""Proactivity suppress helpers — quiet hours + mute (M06 check/nudge path).

Boot heads still load (truth for STATUS). Only user-facing nudges / campaign check
payloads consult this. Chill is session-scoped in the harness, not here.
"""

from __future__ import annotations

from datetime import datetime, time
from typing import Any
from zoneinfo import ZoneInfo

from ada.io.paths import DataPaths, require_ada_data
from ada.memory.facts import DEFAULT_PREFS, ensure_prefs, load_prefs

NZ_TZ = ZoneInfo("Pacific/Auckland")


def _parse_hhmm(value: str | None, fallback: str) -> time:
    raw = (value or fallback or "").strip()
    try:
        hour_s, min_s = raw.split(":", 1)
        return time(hour=int(hour_s), minute=int(min_s))
    except (ValueError, TypeError):
        fb_h, fb_m = fallback.split(":")
        return time(hour=int(fb_h), minute=int(fb_m))


def _now_local(now: datetime | None, tz: ZoneInfo) -> datetime:
    if now is None:
        return datetime.now(tz)
    if now.tzinfo is None:
        return now.replace(tzinfo=tz)
    return now.astimezone(tz)


def in_quiet_hours(
    *,
    now: datetime | None = None,
    quiet_start: str | None = None,
    quiet_end: str | None = None,
    tz: ZoneInfo | None = None,
) -> bool:
    """True if local time is inside quiet window (default 23:00–05:30 NZST)."""
    zone = tz or NZ_TZ
    local = _now_local(now, zone)
    start = _parse_hhmm(quiet_start, str(DEFAULT_PREFS["quiet_hours_start"]))
    end = _parse_hhmm(quiet_end, str(DEFAULT_PREFS["quiet_hours_end"]))
    t = local.time().replace(second=0, microsecond=0)
    if start <= end:
        return start <= t < end
    # Wraps midnight: quiet if t >= start OR t < end
    return t >= start or t < end


def proactivity_suppressed(
    *,
    paths: DataPaths | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Whether campaign check / nudges should stay quiet.

    Returns {suppressed, reasons[], mute_proactivity, in_quiet_hours, ...}.
    """
    p = paths or require_ada_data()
    try:
        prefs = load_prefs(p) if p.prefs_yaml.is_file() else dict(DEFAULT_PREFS)
    except Exception:
        try:
            prefs = ensure_prefs(p)
        except Exception:
            prefs = dict(DEFAULT_PREFS)

    mute = bool(prefs.get("mute_proactivity", False))
    q_start = str(prefs.get("quiet_hours_start") or DEFAULT_PREFS["quiet_hours_start"])
    q_end = str(prefs.get("quiet_hours_end") or DEFAULT_PREFS["quiet_hours_end"])
    tz_name = str(prefs.get("preferred_tz") or "Pacific/Auckland")
    try:
        zone = ZoneInfo(tz_name)
    except Exception:
        zone = NZ_TZ

    quiet = in_quiet_hours(
        now=now, quiet_start=q_start, quiet_end=q_end, tz=zone
    )
    reasons: list[str] = []
    if mute:
        reasons.append("mute_proactivity")
    if quiet:
        reasons.append("quiet_hours")
    return {
        "suppressed": bool(reasons),
        "reasons": reasons,
        "mute_proactivity": mute,
        "in_quiet_hours": quiet,
        "quiet_hours_start": q_start,
        "quiet_hours_end": q_end,
        "tz": tz_name,
    }
