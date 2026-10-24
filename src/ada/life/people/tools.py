"""life_person_* / who_is / people_remind gateway handlers."""

from __future__ import annotations

from typing import Any

import ada.memory.people as people_mod
from ada.logs.receipts import write_life_crumb


def _write(tool: str, receipt_id: str, outcome: dict[str, Any]) -> dict[str, Any]:
    if receipt_id and outcome.get("ok"):
        write_life_crumb(receipt_id=receipt_id, tool=tool, outcome=outcome)
    return outcome


def run_life_person_capture(args: dict[str, Any]) -> dict[str, Any]:
    receipt_id = str(args.get("receipt_id") or "")
    outcome = people_mod.person_capture(
        utterance=args.get("utterance"),
        display_name=args.get("display_name"),
        note=args.get("note"),
        person_id=args.get("person_id"),
        confirmed=bool(args.get("confirmed", False)),
    )
    if outcome.get("needs_confirm"):
        outcome["ok"] = False
        return outcome
    return _write("life_person_capture", receipt_id, outcome)


def run_life_who_is(args: dict[str, Any]) -> dict[str, Any]:
    mention = str(args.get("mention") or "")
    return people_mod.who_is(mention=mention)


def run_life_person_note(args: dict[str, Any]) -> dict[str, Any]:
    receipt_id = str(args.get("receipt_id") or "")
    outcome = people_mod.person_note(
        person_id=args.get("person_id"),
        mention=args.get("mention"),
        text=str(args.get("text") or ""),
        confirmed=bool(args.get("confirmed", False)),
    )
    if outcome.get("needs_confirm"):
        outcome["ok"] = False
        return outcome
    return _write("life_person_note", receipt_id, outcome)


def run_life_birthday_set(args: dict[str, Any]) -> dict[str, Any]:
    receipt_id = str(args.get("receipt_id") or "")
    return _write(
        "life_birthday_set",
        receipt_id,
        people_mod.birthday_set(
            person_id=args.get("person_id"),
            mention=args.get("mention"),
            birthday=str(args.get("birthday") or ""),
        ),
    )


def run_life_people_remind(args: dict[str, Any]) -> dict[str, Any]:
    return people_mod.people_remind(
        horizon_days=int(args.get("horizon_days") or 14),
    )


def run_life_alias_set(args: dict[str, Any]) -> dict[str, Any]:
    receipt_id = str(args.get("receipt_id") or "")
    utterance = str(args.get("utterance") or args.get("alias") or "")
    alias = args.get("alias")
    person_id = args.get("person_id")
    mention = args.get("mention")
    if utterance and "→" in utterance:
        left, right = utterance.split("→", 1)
        alias = left.strip().removesuffix(":").strip()
        person_id = right.strip()
    elif utterance and "->" in utterance:
        left, right = utterance.split("->", 1)
        alias = left.strip().removesuffix(":").strip()
        person_id = right.strip()
    outcome = people_mod.alias_set(
        alias=str(alias or utterance),
        person_id=person_id,
        mention=mention,
        sense=str(args.get("sense") or "alias"),
        confirmed=bool(args.get("confirmed", False)),
    )
    if outcome.get("needs_confirm"):
        outcome["ok"] = False
    return _write("life_alias_set", receipt_id, outcome)


def run_life_person_update(args: dict[str, Any]) -> dict[str, Any]:
    receipt_id = str(args.get("receipt_id") or "")
    outcome = people_mod.person_update(
        person_id=str(args.get("person_id") or ""),
        fields=args.get("fields") if isinstance(args.get("fields"), dict) else {},
        confirmed=bool(args.get("confirmed", False)),
    )
    if outcome.get("needs_confirm"):
        outcome["ok"] = False
    return _write("life_person_update", receipt_id, outcome)


DISPATCH = {
    "life_person_capture": run_life_person_capture,
    "life_who_is": run_life_who_is,
    "life_person_note": run_life_person_note,
    "life_birthday_set": run_life_birthday_set,
    "life_people_remind": run_life_people_remind,
    "life_alias_set": run_life_alias_set,
    "life_person_update": run_life_person_update,
}
