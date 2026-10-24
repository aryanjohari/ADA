"""People domain organ — spine, doors, tools, fast-path."""

from __future__ import annotations

from ada.life.people.doors import (
    alias_set_body,
    birthday_set_body,
    is_alias_set_utterance,
    is_birthday_set_utterance,
    is_people_remind_utterance,
    is_person_capture_utterance,
    is_person_note_utterance,
    is_who_is_utterance,
    person_capture_body,
    person_note_body,
    who_is_mention,
)
from ada.life.people.spine import (
    build_birthday_args,
    build_capture_args,
    build_note_args,
    build_who_is_args,
    parse_note_utterance,
    resolve_mention_for_due,
)

__all__ = [
    "alias_set_body",
    "birthday_set_body",
    "build_birthday_args",
    "build_capture_args",
    "build_note_args",
    "build_who_is_args",
    "is_alias_set_utterance",
    "is_birthday_set_utterance",
    "is_people_remind_utterance",
    "is_person_capture_utterance",
    "is_person_note_utterance",
    "is_who_is_utterance",
    "parse_note_utterance",
    "person_capture_body",
    "person_note_body",
    "resolve_mention_for_due",
    "who_is_mention",
]
