"""Structural people pack doors — met / who is / note / alias / birthday / remind."""

from __future__ import annotations

import re

from ada.life.utterance import strip_leading_filler

# People wrappers — name is a remainder slot, not a YAML row. Bare "Ravi" is not a door.
_MET_NL = re.compile(r"^met\s+(.+)$", re.IGNORECASE)
_WHO_IS_NL = re.compile(r"^who\s+is\s+(.+)$", re.IGNORECASE)
_NOTE_FOR_NL = re.compile(r"^note\s+for\s+(.+)$", re.IGNORECASE)
_ALIAS_SET_NL = re.compile(r"^alias\s+set:\s*(.+)$", re.IGNORECASE)
_BIRTHDAY_SET_NL = re.compile(r"^set\s+birthday:\s*(.+)$", re.IGNORECASE)


def _people_other_organ(raw: str) -> bool:
    """Meal / lift / gym / time / habit / due wrappers win over people."""
    from ada.harness.pack_router import (
        is_due_add_utterance,
        is_due_done_utterance,
        is_due_list_utterance,
        is_gym_end_utterance,
        is_gym_start_utterance,
        is_habit_do_utterance,
        is_habit_miss_utterance,
        is_lift_log_utterance,
        is_meal_log_utterance,
        is_remind_utterance,
        is_time_start_utterance,
    )

    return (
        is_habit_do_utterance(raw)
        or is_habit_miss_utterance(raw)
        or is_gym_start_utterance(raw)
        or is_gym_end_utterance(raw)
        or is_time_start_utterance(raw)
        or is_lift_log_utterance(raw)
        or is_meal_log_utterance(raw)
        or is_due_add_utterance(raw)
        or is_due_done_utterance(raw)
        or is_remind_utterance(raw)
        or is_due_list_utterance(raw)
    )


def _people_raw(text: str) -> str:
    return strip_leading_filler(text)


def is_person_capture_utterance(text: str) -> bool:
    """Wrapper pack door for person_capture — `met {name}`. Bare names are not a door."""
    raw = _people_raw(text)
    if not raw or _people_other_organ(raw):
        return False
    matched = _MET_NL.match(raw)
    return bool(matched and matched.group(1).strip())


def is_who_is_utterance(text: str) -> bool:
    """Wrapper pack door for who_is — `who is {name}`."""
    raw = _people_raw(text)
    if not raw or _people_other_organ(raw):
        return False
    matched = _WHO_IS_NL.match(raw)
    return bool(matched and matched.group(1).strip())


def is_person_note_utterance(text: str) -> bool:
    """Wrapper pack door for person_note — `note for {name}`."""
    raw = _people_raw(text)
    if not raw or _people_other_organ(raw):
        return False
    matched = _NOTE_FOR_NL.match(raw)
    return bool(matched and matched.group(1).strip())


def is_alias_set_utterance(text: str) -> bool:
    """Wrapper pack door for alias_set — `alias set:`."""
    raw = _people_raw(text)
    if not raw or _people_other_organ(raw):
        return False
    matched = _ALIAS_SET_NL.match(raw)
    return bool(matched and matched.group(1).strip())


def is_birthday_set_utterance(text: str) -> bool:
    """Wrapper pack door for birthday_set — `set birthday: {name} YYYY-MM-DD`."""
    raw = _people_raw(text)
    if not raw or _people_other_organ(raw):
        return False
    matched = _BIRTHDAY_SET_NL.match(raw)
    return bool(matched and matched.group(1).strip())


def is_people_remind_utterance(text: str) -> bool:
    """Read door for people_remind — not dues `remind me`."""
    raw = _people_raw(text)
    if not raw or _people_other_organ(raw):
        return False
    lower = raw.lower()
    if lower.startswith("people remind"):
        return True
    return "upcoming birthdays" in lower


def person_capture_body(text: str) -> str:
    raw = _people_raw(text)
    matched = _MET_NL.match(raw)
    return matched.group(1).strip() if matched else raw


def who_is_mention(text: str) -> str:
    raw = _people_raw(text)
    matched = _WHO_IS_NL.match(raw)
    return matched.group(1).strip() if matched else raw


def person_note_body(text: str) -> str:
    raw = _people_raw(text)
    matched = _NOTE_FOR_NL.match(raw)
    return matched.group(1).strip() if matched else raw


def alias_set_body(text: str) -> str:
    raw = _people_raw(text)
    matched = _ALIAS_SET_NL.match(raw)
    return matched.group(1).strip() if matched else raw


def birthday_set_body(text: str) -> str:
    raw = _people_raw(text)
    matched = _BIRTHDAY_SET_NL.match(raw)
    return matched.group(1).strip() if matched else raw
