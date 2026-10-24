"""Mouth templates for gym tools — mouth ⊆ receipt."""

from __future__ import annotations

from typing import Any

LIFE_SAVE_FAIL_ACK = "That didn't save — try once more."


def speak_gym_end(data: dict[str, Any]) -> str:
    n = int(data.get("set_count") or 0)
    if n == 0:
        return "Closed the gym — no sets that session."
    muscles: list[str] = []
    for row in data.get("exercises") or []:
        if not isinstance(row, dict):
            continue
        for m in row.get("muscles") or []:
            token = str(m or "").strip()
            if token and token not in muscles:
                muscles.append(token)
    text = f"Closed the gym — {n} sets logged."
    if muscles:
        text += f" Hit {', '.join(muscles[:4])}."
    return text


def speak_lift_log(data: dict[str, Any]) -> str:
    if data.get("ok") is False:
        return LIFE_SAVE_FAIL_ACK
    resolved = data.get("resolved") or []
    row = resolved[0] if resolved and isinstance(resolved[0], dict) else {}
    name = (
        row.get("exercise_name")
        or row.get("canonical_name")
        or (data.get("exercise_names") or [None])[0]
        or "lift"
    )
    load = row.get("load_kg")
    reps = row.get("reps")
    bits = [f"Logged {name}"]
    if load is not None and reps is not None:
        bits.append(f"— {load} kg × {reps}")
    elif reps is not None:
        bits.append(f"— {reps} reps")
    last_load = data.get("last_load_kg")
    if last_load is None:
        last_load = row.get("last_load_kg")
    last_reps = data.get("last_reps")
    if last_reps is None:
        last_reps = row.get("last_reps")
    if last_load is not None and last_reps is not None:
        bits.append(f"Last closed was {last_load} × {last_reps}.")
    text = " ".join(bits)
    if not text.endswith("."):
        text += "."
    return text


def speak_gym_status(data: dict[str, Any]) -> str:
    if isinstance(data.get("exercises"), list):
        return speak_gym_end(data)
    n = len(data.get("sets_today") or [])
    exercises = data.get("exercises_today") or []
    if exercises and isinstance(exercises[0], dict):
        row = exercises[0]
        last_load = row.get("last_load_kg")
        last_reps = row.get("last_reps")
        if last_load is not None and last_reps is not None:
            name = row.get("canonical_name") or row.get("exercise_name") or "lift"
            prior = f"Last closed {name}: {last_load} × {last_reps}."
            if data.get("active_session"):
                if n == 0:
                    return f"Gym session's open — no sets yet. {prior}"
                return f"Gym session's open — {n} sets today. {prior}"
            if n == 0:
                return f"No gym sets logged today. {prior}"
            return f"{n} sets today. {prior}"
    if data.get("active_session"):
        if n == 0:
            return "Gym session's open — no sets yet."
        return f"Gym session's open — {n} sets today."
    if n == 0:
        return "No gym sets logged today."
    return f"{n} sets logged today."


def speak_gym_day(data: dict[str, Any]) -> str:
    date = data.get("date") or "that day"
    n = int(data.get("set_count") or 0)
    if n == 0:
        return str(data.get("message") or f"No gym sets logged for {date}.")
    bits = [f"{date}: {n} sets"]
    tonnage = data.get("tonnage_kg")
    if isinstance(tonnage, (int, float)) and float(tonnage) > 0:
        bits.append(f"{tonnage} kg tonnage")
    label = data.get("split_label")
    if label:
        bits.append(str(label))
    cite = data.get("cite")
    if cite:
        bits.append(str(cite))
    text = ". ".join(bits)
    if not text.endswith("."):
        text += "."
    return text


def speak_gym_week(data: dict[str, Any]) -> str:
    if not data.get("days_logged"):
        return str(data.get("message") or "No gym sets logged in this window.")
    window = int(data.get("window_days") or 7)
    logged = int(data.get("days_logged") or 0)
    bits = [f"Last {window} days: {logged} day(s) lifted"]
    ag = data.get("aggregates") if isinstance(data.get("aggregates"), dict) else {}
    tonnage = ag.get("sum_tonnage_kg")
    if isinstance(tonnage, (int, float)) and float(tonnage) > 0:
        bits.append(f"{tonnage} kg tonnage")
    rest_n = ag.get("rest_day_count")
    if isinstance(rest_n, int) and rest_n > 0:
        bits.append(f"{rest_n} rest day(s)")
    days = data.get("days") if isinstance(data.get("days"), list) else []
    cites = [
        str(d.get("cite"))
        for d in days
        if isinstance(d, dict) and d.get("set_count", 0) > 0 and d.get("cite")
    ]
    if cites:
        bits.append(f"Logged: {', '.join(cites[:2])}")
    for pat in data.get("patterns") or []:
        bits.append(str(pat))
    text = ". ".join(bits)
    if not text.endswith("."):
        text += "."
    return text
