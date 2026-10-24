"""Mouth templates for meal / nutrition tools — mouth ⊆ receipt."""

from __future__ import annotations

import re
from typing import Any

from ada.harness.mouth import CONFIRM_LINE

LIFE_SAVE_FAIL_ACK = "That didn't save — try once more."
MEAL_EMPTY_MACROS_ACK = (
    "Couldn't log that — nutrients came back empty. Try another food name."
)
_MEAL_LOGGED_CLAIM = re.compile(
    r"\b(?:logged|entries?\s+are\s+on\s+the\s+board|saved\s+(?:that|the)\s+meal)\b",
    re.IGNORECASE,
)


def meal_receipt_outcome(receipts: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Latest life_meal_log data blob, or None if no meal tool ran."""
    for row in reversed(receipts):
        if str(row.get("tool") or "") != "life_meal_log":
            continue
        data = row.get("data")
        if isinstance(data, dict):
            return data
        # Gateway sometimes surfaces needs_confirm on the observation itself.
        if row.get("needs_confirm") or row.get("ok") is False:
            return {
                "ok": bool(row.get("ok")),
                "needs_confirm": bool(row.get("needs_confirm")),
                "reason": row.get("reason") or row.get("denied_reason"),
            }
    return None


def honest_meal_mouth(text: str | None, receipts: list[dict[str, Any]]) -> str | None:
    """M23/M26: refuse lying 'Logged…' when meal tool failed or needs Confirm."""
    meal = meal_receipt_outcome(receipts)
    if meal is None or not text:
        return text
    failed = (
        meal.get("ok") is False
        or meal.get("needs_confirm")
        or str(meal.get("reason") or "") in {"empty_macros", "needs_confirm", "spine_required"}
        or str(meal.get("error") or "") in {"empty_macros", "spine_required"}
    )
    if not failed:
        return text
    if not _MEAL_LOGGED_CLAIM.search(text):
        return text
    if meal.get("needs_confirm"):
        return CONFIRM_LINE
    if str(meal.get("reason") or meal.get("error") or "") == "empty_macros":
        return MEAL_EMPTY_MACROS_ACK
    return LIFE_SAVE_FAIL_ACK


def speak_nutrition_day(data: dict[str, Any]) -> str:
    totals = data.get("totals") or {}
    date = data.get("date") or "today"
    kcal = totals.get("energy_kcal")
    protein = totals.get("protein_g")
    if not totals:
        text = f"No meals logged for {date}."
    else:
        bits = [f"{date}:"]
        if kcal is not None:
            bits.append(f"{kcal} kcal")
        if protein is not None:
            bits.append(f"{protein}g protein")
        text = " ".join(bits)
    mix = data.get("provenance_mix") or []
    if "estimate" in mix or data.get("has_estimate"):
        text += " Includes estimate lines — not lab-exact."
    if data.get("honest_partial"):
        text += " Partial micronutrients only — not inventing Ca/Fe/C/D."
    return text


def speak_nutrition_week(data: dict[str, Any]) -> str:
    if not data.get("days_logged"):
        return str(data.get("message") or "No meals logged in this window.")
    window = int(data.get("window_days") or 7)
    logged = int(data.get("days_logged") or 0)
    ag = data.get("aggregates") or {}
    bits = [f"Last {window} days: {logged} day(s) logged."]
    avg_p = ag.get("avg_protein_g")
    if avg_p is not None:
        bits.append(f"Avg {avg_p}g protein")
    avg_k = ag.get("avg_energy_kcal")
    if avg_k is not None:
        bits.append(f"avg {avg_k} kcal")
    days = data.get("days") if isinstance(data.get("days"), list) else []
    cites = [
        str(d.get("cite"))
        for d in days
        if isinstance(d, dict) and d.get("meal_count", 0) > 0 and d.get("cite")
    ]
    if cites:
        bits.append(f"Logged: {', '.join(cites[:2])}")
    for pat in data.get("patterns") or []:
        bits.append(pat)
    text = ". ".join(bits)
    if not text.endswith("."):
        text += "."
    return text
