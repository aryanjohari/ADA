"""Deterministic utterance → people capture/resolve args (M19a P1)."""

from __future__ import annotations

from typing import Any

from ada.memory import people as people_mod


def build_capture_args(utterance: str, *, paths=None) -> dict[str, Any]:
    parsed = people_mod.parse_capture_utterance(utterance)
    if not parsed.get("ok"):
        return {"ok": False, "reason": "missing_life_receipt", **parsed}
    name = str(parsed.get("display_name") or "").strip()
    note = parsed.get("note")
    resolved = people_mod.resolve_mention(name, paths=paths)
    if resolved.get("ok"):
        return {
            "ok": True,
            "args": {
                "utterance": utterance,
                "display_name": name,
                "note": note,
                "person_id": resolved["person_id"],
            },
            "person_id": resolved["person_id"],
        }
    candidates = [
        people_mod._people_candidate_row(c) for c in (resolved.get("candidates") or [])
    ]
    if len(candidates) > 1:
        proposed = str(candidates[0].get("person_id") or "")
        resolve_blob = {
            "reason": "ambiguous",
            "candidates": candidates,
            "proposed_person_id": proposed,
            "query": name,
        }
        return {
            "ok": False,
            "needs_confirm": True,
            "reason": "ambiguous",
            "confirm_tool": "life_person_capture",
            "match_count": len(candidates),
            "candidates": candidates,
            "args": {
                "utterance": utterance,
                "display_name": name,
                "note": note,
                "person_id": proposed or None,
                "confirmed": False,
                "resolve": resolve_blob,
                "candidates": candidates,
            },
        }
    return {
        "ok": False,
        "needs_confirm": True,
        "reason": "create_person",
        "create": True,
        "confirm_tool": "life_person_capture",
        "match_count": 0,
        "args": {
            "utterance": utterance,
            "display_name": name,
            "proposed_display_name": name,
            "note": note,
            "confirmed": False,
        },
    }


def build_who_is_args(utterance: str, *, body: str | None = None) -> dict[str, Any]:
    mention = (body or utterance or "").strip()
    lower = mention.lower()
    if lower.startswith("who is "):
        mention = mention[7:].strip()
    if not mention:
        return {"ok": False, "reason": "missing_mention"}
    return {"ok": True, "args": {"mention": mention}}


def parse_note_utterance(text: str) -> dict[str, Any]:
    """Parse 'note for {name}: {text}' — name is the remainder slot before the colon."""
    raw = (text or "").strip()
    lower = raw.lower()
    if lower.startswith("note for "):
        raw = raw[9:].strip()
    if not raw:
        return {"ok": False, "reason": "missing_mention"}
    mention = raw
    note = ""
    if ":" in raw:
        left, right = raw.split(":", 1)
        mention = left.strip()
        note = right.strip()
    if not mention:
        return {"ok": False, "reason": "missing_mention"}
    if not note:
        return {"ok": False, "reason": "missing_note", "mention": mention}
    return {"ok": True, "mention": mention, "text": note}


def build_note_args(utterance: str, *, paths=None) -> dict[str, Any]:
    parsed = parse_note_utterance(utterance)
    if not parsed.get("ok"):
        return {"ok": False, "reason": "missing_life_receipt", **parsed}
    resolved = people_mod.resolve_mention(parsed["mention"], paths=paths)
    if resolved.get("ok"):
        return {
            "ok": True,
            "args": {
                "person_id": resolved["person_id"],
                "mention": parsed["mention"],
                "text": parsed["text"],
            },
            "person_id": resolved["person_id"],
        }
    candidates = [
        people_mod._people_candidate_row(c) for c in (resolved.get("candidates") or [])
    ]
    if len(candidates) > 1:
        proposed = str(candidates[0].get("person_id") or "")
        resolve_blob = {
            "reason": "ambiguous",
            "candidates": candidates,
            "proposed_person_id": proposed,
            "query": parsed["mention"],
        }
        return {
            "ok": False,
            "needs_confirm": True,
            "reason": "ambiguous",
            "confirm_tool": "life_person_note",
            "match_count": len(candidates),
            "candidates": candidates,
            "args": {
                "mention": parsed["mention"],
                "text": parsed["text"],
                "person_id": proposed or None,
                "confirmed": False,
                "resolve": resolve_blob,
                "candidates": candidates,
            },
        }
    return {
        "ok": False,
        "reason": "missing_life_receipt",
        "match_count": resolved.get("match_count", 0),
        "candidates": candidates,
    }


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
        "person_id": resolved["person_id"],
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
