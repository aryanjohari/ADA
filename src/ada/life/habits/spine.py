"""Deterministic utterance → habit tick args (M19a P1 / M21 / M22)."""

from __future__ import annotations

import re
from typing import Any

from ada.harness.resolve_gate import decide_habit_bind
from ada.logs import habits as habits_mod

# Strip pack / NL wrappers so resolve sees the habit name only.
_HABIT_WRAPPER = re.compile(
    r"^(?:(?:create\s+new\s+habits?|new\s+habit|habit)\s+)?"
    r"(?:done|miss(?:ed)?|tick|logged)\s*:?\s+",
    re.IGNORECASE,
)
_CREATE_WRAPPER = re.compile(
    r"^(?:create\s+(?:new\s+)?habits?|new\s+habit)\s*:?\s+",
    re.IGNORECASE,
)


def clean_habit_name(utterance: str) -> str:
    """Normalize habit tick / create utterance to a display name."""
    name = (utterance or "").strip()
    if not name:
        return ""
    name = _HABIT_WRAPPER.sub("", name).strip()
    name = _CREATE_WRAPPER.sub("", name).strip()
    return name


def build_habit_tick_args(
    utterance: str,
    *,
    verb: str,
    paths=None,
) -> dict[str, Any]:
    """Parse habit_do / habit_miss / routine_run utterance (no write).

    Unique habit → bind habit_id. Many → needs_confirm + candidates (M21).
    Zero → Confirm-create via life_habit_create (M22 Slice 3b).
    """
    name = clean_habit_name(utterance)
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
    if resolved.get("ok"):
        return {
            "ok": True,
            "args": {"habit_id": resolved["habit_id"], "name": name},
            "habit_id": resolved["habit_id"],
        }
    matches = list(resolved.get("matches") or [])
    decision = decide_habit_bind(query=name, matches=matches)
    if decision.get("needs_confirm"):
        proposed = str(decision.get("proposed_habit_id") or "")
        resolve_blob = {
            "reason": "ambiguous",
            "reasons": list(decision.get("reasons") or ["many"]),
            "candidates": list(decision.get("candidates") or []),
            "proposed_habit_id": proposed,
            "query": name,
        }
        return {
            "ok": False,
            "needs_confirm": True,
            "reason": "ambiguous",
            "match_count": len(matches),
            "matches": matches,
            "candidates": resolve_blob["candidates"],
            "args": {
                "name": name,
                "habit_id": proposed or None,
                "confirmed": False,
                "resolve": resolve_blob,
                "candidates": resolve_blob["candidates"],
            },
        }
    # 0 matches — teach-in-flow Confirm-create (habit_do path ticks after Yes).
    if verb == "habit_do":
        return {
            "ok": False,
            "needs_confirm": True,
            "reason": "create_habit",
            "create": True,
            "confirm_tool": "life_habit_create",
            "match_count": 0,
            "matches": [],
            "args": {
                "display_name": name,
                "proposed_display_name": name,
                "confirmed": False,
                "tick_after": True,
            },
        }
    # habit_miss with unknown name — still honest miss (no silent create).
    return {
        "ok": False,
        "reason": "missing_life_receipt",
        "match_count": resolved.get("match_count", 0),
        "matches": matches,
    }
