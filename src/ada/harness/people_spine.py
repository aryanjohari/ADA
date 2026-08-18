"""Deterministic utterance → people capture/resolve args (M19a P1)."""

from __future__ import annotations

from typing import Any

from ada.memory import people as people_mod


def build_capture_args(utterance: str, *, paths=None) -> dict[str, Any]:
    parsed = people_mod.parse_capture_utterance(utterance)
    if not parsed.get("ok"):
        return {"ok": False, "reason": "missing_life_receipt", **parsed}
    return {
        "ok": True,
        "args": {"utterance": utterance, "display_name": parsed["display_name"], "note": parsed.get("note")},
    }


def build_who_is_args(utterance: str, *, body: str | None = None) -> dict[str, Any]:
    mention = (body or utterance or "").strip()
    lower = mention.lower()
    if lower.startswith("who is "):
        mention = mention[7:].strip()
    if not mention:
        return {"ok": False, "reason": "missing_mention"}
    return {"ok": True, "args": {"mention": mention}}


def build_birthday_args(body: str, *, paths=None) -> dict[str, Any]:
    parsed = people_mod.parse_birthday_utterance(body)
    if not parsed.get("ok"):
        return {"ok": False, "reason": "missing_life_receipt", **parsed}
    resolved = people_mod.resolve_mention(parsed["mention"], paths=paths)
    if not resolved.get("ok"):
        return {
            "ok": False,
            "reason": "missing_life_receipt",
            "match_count": resolved.get("match_count", 0),
            "candidates": resolved.get("candidates") or [],
        }
    return {
        "ok": True,
        "args": {
            "person_id": resolved["person_id"],
            "mention": parsed["mention"],
            "birthday": parsed["birthday"],
        },
    }


def resolve_mention_for_due(title: str, *, paths=None) -> dict[str, Any]:
    """Extract trailing capitalized name token for due/remind glue."""
    text = (title or "").strip()
    if not text:
        return {"ok": False, "reason": "empty"}
    tokens = text.replace(",", " ").split()
    if not tokens:
        return {"ok": False, "reason": "empty"}
    # Try last token as person mention (e.g. 'call Ravi Friday' → Ravi)
    for token in reversed(tokens):
        clean = token.strip(".")
        if clean and clean[0].isupper() and clean.lower() not in {
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
            "tomorrow",
        }:
            resolved = people_mod.resolve_mention(clean, paths=paths)
            if resolved.get("ok"):
                return {"ok": True, "person_id": resolved["person_id"], "mention": clean}
            if resolved.get("match_count", 0) > 1:
                return resolved
    return {"ok": False, "reason": "not_found", "match_count": 0}
