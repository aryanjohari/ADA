"""Life capture tool wrappers (M19a)."""

from __future__ import annotations

from typing import Any

from ada.logs import food as food_mod
from ada.logs import gym as gym_mod
from ada.logs import habits as habits_mod
from ada.logs import meals as meals_mod
from ada.logs import time as time_mod
from ada.logs.receipts import write_life_crumb
from ada.memory import people as people_mod


def _write(tool: str, receipt_id: str, outcome: dict[str, Any]) -> dict[str, Any]:
    if receipt_id and outcome.get("ok"):
        write_life_crumb(receipt_id=receipt_id, tool=tool, outcome=outcome)
    return outcome


def run_life_food_search(args: dict[str, Any]) -> dict[str, Any]:
    query = args.get("query") or args.get("q") or ""
    limit = int(args.get("limit") or 10)
    fetch_remote = bool(args.get("fetch_remote", True))
    candidates = food_mod.search_foods_resolved(
        str(query), limit=limit, fetch_remote=fetch_remote
    )
    return {"ok": True, "outcome": "ok", "candidates": candidates}


def run_life_barcode_lookup(args: dict[str, Any]) -> dict[str, Any]:
    barcode = args.get("barcode") or args.get("gtin") or ""
    fetch_remote = bool(args.get("fetch_remote", True))
    result = food_mod.barcode_lookup(str(barcode), fetch_remote=fetch_remote)
    if not result.get("ok"):
        return {"ok": False, "outcome": "ok", **result}
    return {"ok": True, "outcome": "ok", **result}


def run_life_meal_log(args: dict[str, Any]) -> dict[str, Any]:
    receipt_id = str(args.get("receipt_id") or "")
    lines = args.get("lines") or []
    if not lines:
        raise ValueError("lines required")
    return _write(
        "life_meal_log",
        receipt_id,
        meals_mod.meal_log(
            receipt_id=receipt_id,
            note=args.get("note"),
            meal_slot=args.get("meal_slot"),
            lines=lines,
        ),
    )


def run_life_meal_fix(args: dict[str, Any]) -> dict[str, Any]:
    receipt_id = str(args.get("receipt_id") or "")
    lines = args.get("lines") or []
    return _write(
        "life_meal_fix",
        receipt_id,
        meals_mod.meal_log(
            receipt_id=receipt_id,
            note=args.get("note"),
            meal_slot=args.get("meal_slot"),
            lines=lines,
        ),
    )


def run_life_nutrition_day(args: dict[str, Any]) -> dict[str, Any]:
    return meals_mod.nutrition_day(date=args.get("date"))


def run_life_gym_start(args: dict[str, Any]) -> dict[str, Any]:
    receipt_id = str(args.get("receipt_id") or "")
    return _write(
        "life_gym_start",
        receipt_id,
        gym_mod.gym_start(receipt_id=receipt_id, split_day=args.get("split_day")),
    )


def run_life_lift_log(args: dict[str, Any]) -> dict[str, Any]:
    receipt_id = str(args.get("receipt_id") or "")
    sets = args.get("sets") or []
    if not sets:
        raise ValueError("sets required")
    return _write(
        "life_lift_log",
        receipt_id,
        gym_mod.lift_log(
            receipt_id=receipt_id,
            sets=sets,
            session_id=args.get("session_id"),
        ),
    )


def run_life_gym_end(args: dict[str, Any]) -> dict[str, Any]:
    receipt_id = str(args.get("receipt_id") or "")
    return _write(
        "life_gym_end",
        receipt_id,
        gym_mod.gym_end(
            receipt_id=receipt_id,
            session_id=args.get("session_id"),
            notes=args.get("notes"),
        ),
    )


def run_life_time_start(args: dict[str, Any]) -> dict[str, Any]:
    receipt_id = str(args.get("receipt_id") or "")
    kind = args.get("kind")
    if not kind:
        raise ValueError("kind required")
    return _write(
        "life_time_start",
        receipt_id,
        time_mod.start_block(
            kind=str(kind),
            label=args.get("label"),
            receipt_id=receipt_id,
        ),
    )


def run_life_time_stop(args: dict[str, Any]) -> dict[str, Any]:
    receipt_id = str(args.get("receipt_id") or "")
    return _write(
        "life_time_stop",
        receipt_id,
        time_mod.stop_block(receipt_id=receipt_id, block_id=args.get("block_id")),
    )


def run_life_time_status(args: dict[str, Any]) -> dict[str, Any]:
    return time_mod.time_status()


def run_life_gym_status(args: dict[str, Any]) -> dict[str, Any]:
    return gym_mod.gym_status(date=args.get("date"))


def run_life_food_preset_save(args: dict[str, Any]) -> dict[str, Any]:
    from ada.memory import facts as facts_mod

    name = args.get("name") or args.get("preset_id")
    if not name:
        raise ValueError("name required")
    components = args.get("components") or []
    return facts_mod.append_fact(
        f"nutrition_presets.presets",
        {"id": name, "display_name": name, "components": components},
        confirmed=bool(args.get("confirmed", False)),
    )


def run_life_capture(args: dict[str, Any]) -> dict[str, Any]:
    from ada.logs.capture import classify_capture
    from ada.memory import artifacts as art_mod
    from ada.memory import facts as facts_mod
    from ada.memory import open_loops as loops_mod
    from ada.tools import artifact_tools, memory_tools

    text = str(args.get("text") or args.get("body") or "")
    kind_hint = args.get("kind")
    classified = classify_capture(text, kind_hint=str(kind_hint) if kind_hint else None)
    kind = classified["kind"]
    receipt_id = str(args.get("receipt_id") or "")

    if kind in {"todo", "remind"}:
        loop_args: dict[str, Any] = {
            "kind": "todo",
            "text": text,
            "status": "open",
        }
        if kind == "remind":
            loop_args["remind_at"] = args.get("remind_at")
        result = memory_tools.run_memory_open_loops_upsert(loop_args)
        return {
            "ok": True,
            "kind": kind,
            "open_loop_id": (result.get("loop") or {}).get("id"),
            "receipt_id": receipt_id,
            **result,
        }

    if kind == "fact":
        key = args.get("key") or "capture.notes"
        value = args.get("value") or text
        hit = facts_mod.get_fact(key)
        if hit.get("found") and not args.get("confirmed"):
            result = facts_mod.propose_edit(
                key, value, confirmed=bool(args.get("confirmed", False))
            )
        else:
            result = facts_mod.append_fact(
                key, value, confirmed=bool(args.get("confirmed", False))
            )
        out = {"ok": True, "kind": kind, "receipt_id": receipt_id, **result}
        if result.get("needs_confirm"):
            out["needs_confirm"] = True
            out["ok"] = False
        return out

    if kind in {"note", "letter_doc", "receipt_stub", "unknown"}:
        title = args.get("title") or kind
        result = artifact_tools.run_artifact_write(
            {"title": title, "body": text, "format": "md"}
        )
        return {
            "ok": True,
            "kind": kind,
            "path": result.get("path"),
            "receipt_id": receipt_id,
            **result,
        }

    return {"ok": False, "kind": kind, "reason": "unrouted"}


def run_life_habit_do(args: dict[str, Any]) -> dict[str, Any]:
    receipt_id = str(args.get("receipt_id") or "")
    return _write(
        "life_habit_do",
        receipt_id,
        habits_mod.habit_do(
            habit_id=args.get("habit_id"),
            name=args.get("name"),
            note=args.get("note"),
            receipt_id=receipt_id,
        ),
    )


def run_life_habit_miss(args: dict[str, Any]) -> dict[str, Any]:
    receipt_id = str(args.get("receipt_id") or "")
    return _write(
        "life_habit_miss",
        receipt_id,
        habits_mod.habit_miss(
            habit_id=args.get("habit_id"),
            name=args.get("name"),
            note=args.get("note"),
            receipt_id=receipt_id,
        ),
    )


def run_life_routine_run(args: dict[str, Any]) -> dict[str, Any]:
    receipt_id = str(args.get("receipt_id") or "")
    return _write(
        "life_routine_run",
        receipt_id,
        habits_mod.routine_run(
            routine_id=args.get("routine_id"),
            name=args.get("name"),
            steps=args.get("steps"),
            receipt_id=receipt_id,
        ),
    )


def run_life_habit_status(args: dict[str, Any]) -> dict[str, Any]:
    return habits_mod.habit_status(
        habit_id=args.get("habit_id"),
        date=args.get("date"),
        window_days=int(args.get("window_days") or 7),
    )


def run_life_person_capture(args: dict[str, Any]) -> dict[str, Any]:
    receipt_id = str(args.get("receipt_id") or "")
    outcome = people_mod.person_capture(
        utterance=args.get("utterance"),
        display_name=args.get("display_name"),
        note=args.get("note"),
    )
    if outcome.get("needs_confirm"):
        outcome["ok"] = False
    return _write("life_person_capture", receipt_id, outcome)


def run_life_who_is(args: dict[str, Any]) -> dict[str, Any]:
    mention = str(args.get("mention") or "")
    return people_mod.who_is(mention=mention)


def run_life_person_note(args: dict[str, Any]) -> dict[str, Any]:
    receipt_id = str(args.get("receipt_id") or "")
    return _write(
        "life_person_note",
        receipt_id,
        people_mod.person_note(
            person_id=args.get("person_id"),
            mention=args.get("mention"),
            text=str(args.get("text") or ""),
        ),
    )


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
    "life_food_search": run_life_food_search,
    "life_barcode_lookup": run_life_barcode_lookup,
    "life_meal_log": run_life_meal_log,
    "life_meal_fix": run_life_meal_fix,
    "life_nutrition_day": run_life_nutrition_day,
    "life_gym_start": run_life_gym_start,
    "life_lift_log": run_life_lift_log,
    "life_gym_end": run_life_gym_end,
    "life_time_start": run_life_time_start,
    "life_time_stop": run_life_time_stop,
    "life_time_status": run_life_time_status,
    "life_gym_status": run_life_gym_status,
    "life_food_preset_save": run_life_food_preset_save,
    "life_capture": run_life_capture,
    "life_habit_do": run_life_habit_do,
    "life_habit_miss": run_life_habit_miss,
    "life_routine_run": run_life_routine_run,
    "life_habit_status": run_life_habit_status,
    "life_person_capture": run_life_person_capture,
    "life_who_is": run_life_who_is,
    "life_person_note": run_life_person_note,
    "life_birthday_set": run_life_birthday_set,
    "life_people_remind": run_life_people_remind,
    "life_alias_set": run_life_alias_set,
    "life_person_update": run_life_person_update,
}
