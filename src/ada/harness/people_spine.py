"""Shim — people spine lives in ada.life.people.spine."""

from __future__ import annotations

from ada.life.people.spine import (
    build_birthday_args,
    build_capture_args,
    build_note_args,
    build_who_is_args,
    parse_note_utterance,
    resolve_mention_for_due,
)

__all__ = [
    "build_birthday_args",
    "build_capture_args",
    "build_note_args",
    "build_who_is_args",
    "parse_note_utterance",
    "resolve_mention_for_due",
]
