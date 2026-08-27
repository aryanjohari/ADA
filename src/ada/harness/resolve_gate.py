"""Bind decision helpers for teach-in-flow Confirm (M21/M22)."""

from __future__ import annotations

import re
from typing import Any


def normalize_query(query: str) -> str:
    """Normalize food/habit query keys for favorites lookup."""
    return re.sub(r"\s+", " ", (query or "").strip().lower())


def _habit_candidate(habit: dict[str, Any]) -> dict[str, Any]:
    hid = str(habit.get("habit_id") or "")
    label = str(habit.get("display_name") or hid)
    return {
        "ref_id": hid,
        "habit_id": hid,
        "label": label,
        "display_name": label,
    }


def decide_habit_bind(*, query: str, matches: list[dict[str, Any]]) -> dict[str, Any]:
    """Many habit matches → Confirm candidates; unique → bind id."""
    _ = query  # reserved for future rank / preview
    cands = [_habit_candidate(m) for m in matches if isinstance(m, dict)]
    if len(cands) <= 1:
        proposed = cands[0]["habit_id"] if cands else None
        return {
            "needs_confirm": False,
            "candidates": cands,
            "proposed_habit_id": proposed,
            "reasons": [],
        }
    return {
        "needs_confirm": True,
        "candidates": cands,
        "proposed_habit_id": cands[0]["habit_id"],
        "reasons": ["many"],
    }
