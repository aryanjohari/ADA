"""Deterministic utterance → habit tick args (M19a P1)."""

from __future__ import annotations

from typing import Any

from ada.logs import habits as habits_mod


def build_habit_tick_args(
    utterance: str,
    *,
    verb: str,
    paths=None,
) -> dict[str, Any]:
    """Parse habit_do / habit_miss / routine_run utterance (no write)."""
    name = (utterance or "").strip()
    if not name:
        return {"ok": False, "reason": "missing_name"}
    if verb == "routine_run":
        resolved = habits_mod.resolve_routine(name, paths=paths)
        if not resolved.get("ok"):
            return {
                "ok": False,
                "reason": "missing_life_receipt",
                "match_count": resolved.get("match_count", 0),
                "matches": resolved.get("matches") or [],
            }
        return {
            "ok": True,
            "args": {"routine_id": resolved["routine_id"], "name": name},
            "routine_id": resolved["routine_id"],
        }
    resolved = habits_mod.resolve_habit(name, paths=paths)
    if not resolved.get("ok"):
        return {
            "ok": False,
            "reason": "missing_life_receipt",
            "match_count": resolved.get("match_count", 0),
            "matches": resolved.get("matches") or [],
        }
    return {
        "ok": True,
        "args": {"habit_id": resolved["habit_id"], "name": name},
        "habit_id": resolved["habit_id"],
    }
