"""Mouth templates for habit tools — mouth ⊆ receipt."""

from __future__ import annotations

from typing import Any

LIFE_SAVE_FAIL_ACK = "That didn't save — try once more."


def speak_habit_status(data: dict[str, Any]) -> str:
    habits = data.get("habits") or []
    if not habits:
        return "No habits seeded yet."
    rate = data.get("continuity_rate")
    done = sum(1 for h in habits if h.get("done_today"))
    text = f"Habits today: {done}/{len(habits)} done."
    if rate is not None:
        text += f" Continuity {int(float(rate) * 100)}% over {data.get('window_days', 7)} days."
    return text


def speak_habit_day(data: dict[str, Any]) -> str:
    date = data.get("date") or "that day"
    n = int(data.get("event_count") or 0)
    if n == 0:
        return str(data.get("message") or f"No habit ticks for {date}.")
    done = int(data.get("done_count") or 0)
    miss = int(data.get("miss_count") or 0)
    bits = [f"{date}: {done} done, {miss} miss"]
    cite = data.get("cite")
    if cite:
        bits.append(str(cite))
    text = ". ".join(bits)
    if not text.endswith("."):
        text += "."
    return text


def speak_habit_week(data: dict[str, Any]) -> str:
    if not data.get("days_logged"):
        return str(data.get("message") or "No habit ticks in this window.")
    window = int(data.get("window_days") or 7)
    logged = int(data.get("days_logged") or 0)
    bits = [f"Last {window} days: {logged} day(s) with habit ticks"]
    pct = data.get("continuity_pct")
    if pct is None:
        ag = data.get("aggregates") if isinstance(data.get("aggregates"), dict) else {}
        pct = ag.get("continuity_pct")
    if isinstance(pct, int):
        bits.append(f"Continuity {pct}%")
    days = data.get("days") if isinstance(data.get("days"), list) else []
    cites = [
        str(d.get("cite"))
        for d in days
        if isinstance(d, dict) and d.get("event_count", 0) > 0 and d.get("cite")
    ]
    if cites:
        bits.append(", ".join(cites[:2]))
    text = ". ".join(bits)
    if not text.endswith("."):
        text += "."
    return text


def speak_habit_tick(data: dict[str, Any], *, verb: str = "habit_do") -> str:
    """Ack from habit write receipt only — no invented tick, no shame copy."""
    if data.get("ok") is False:
        reason = str(data.get("reason") or "")
        if reason == "already_done":
            return "Already done today."
        return LIFE_SAVE_FAIL_ACK
    if verb == "habit_miss" or data.get("kind") == "miss":
        return "Habit miss."
    if verb == "routine_run":
        return "Routine logged."
    return "Habit logged."
