"""Mouth templates for time tools — mouth ⊆ receipt."""

from __future__ import annotations

from typing import Any


def speak_time_status(data: dict[str, Any]) -> str:
    active = data.get("active")
    if isinstance(active, dict):
        kind = active.get("kind") or "timer"
        return f"Running: {kind}."
    return "No timer running."


def speak_time_start(data: dict[str, Any]) -> str:
    """Ack from start receipt only — never invent duration_s."""
    if data.get("ok") is False:
        return "Could not start a timer."
    label = str(data.get("label") or "").strip()
    kind = str(data.get("kind") or "timer").replace("_", " ")
    name = label or kind
    return f"Started {name}."


def speak_time_stop(data: dict[str, Any]) -> str:
    """Ack from stop receipt. Miss-stop never claims minutes."""
    if data.get("ok") is False or data.get("reason") == "no_active_block":
        return "No timer running."
    kind = str(data.get("kind") or "timer").replace("_", " ")
    duration = data.get("duration_s")
    if duration is None:
        return f"Stopped {kind}."
    return f"Stopped {kind} ({duration}s)."


def speak_time_day(data: dict[str, Any]) -> str:
    date = data.get("date") or "that day"
    n = int(data.get("block_count") or 0)
    if n == 0:
        return str(data.get("message") or f"No time blocks logged for {date}.")
    bits = [f"{date}: {n} time block(s)"]
    duration = data.get("duration_s")
    if isinstance(duration, int) and duration > 0:
        bits.append(f"{duration}s")
    cite = data.get("cite")
    if cite:
        bits.append(str(cite))
    text = ". ".join(bits)
    if not text.endswith("."):
        text += "."
    return text


def speak_time_week(data: dict[str, Any]) -> str:
    if not data.get("days_logged"):
        return str(data.get("message") or "No time blocks logged in this window.")
    window = int(data.get("window_days") or 7)
    logged = int(data.get("days_logged") or 0)
    bits = [f"Last {window} days: {logged} day(s) with time blocks"]
    ag = data.get("aggregates") if isinstance(data.get("aggregates"), dict) else {}
    duration = ag.get("sum_duration_s")
    if isinstance(duration, int) and duration > 0:
        bits.append(f"{duration}s")
    days = data.get("days") if isinstance(data.get("days"), list) else []
    cites = [
        str(d.get("cite"))
        for d in days
        if isinstance(d, dict) and d.get("block_count", 0) > 0 and d.get("cite")
    ]
    if cites:
        bits.append(f"Logged: {', '.join(cites[:2])}")
    text = ". ".join(bits)
    if not text.endswith("."):
        text += "."
    return text
