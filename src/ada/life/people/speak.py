"""Mouth templates for people tools — mouth ⊆ receipt."""

from __future__ import annotations

from typing import Any


def speak_who_is(data: dict[str, Any]) -> str:
    count = int(data.get("match_count") or len(data.get("candidates") or []))
    if count == 0:
        return "No person match — offer to capture a stub."
    if count == 1:
        cand = (data.get("candidates") or [{}])[0]
        name = cand.get("display_name") or data.get("person_id") or "person"
        return f"Matched {name}."
    return f"{count} matches — tap Confirm on the card."


def speak_people_remind(data: dict[str, Any]) -> str:
    upcoming = data.get("upcoming") or data.get("birthday_soon") or []
    if not upcoming:
        return "No upcoming kin events in horizon."
    names = ", ".join(str(x.get("display_name") or x.get("person_id")) for x in upcoming[:3])
    return f"Upcoming: {names}."
