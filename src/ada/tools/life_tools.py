"""Life capture tool wrappers (M19a)."""

from __future__ import annotations

from typing import Any

# Re-export food helpers tests still import from this module.
from ada.life.food.tools import _refuse_empty_macros  # noqa: F401


def run_life_food_search(args: dict[str, Any]) -> dict[str, Any]:
    from ada.life.food.tools import run_life_food_search as _run

    return _run(args)


def run_life_barcode_lookup(args: dict[str, Any]) -> dict[str, Any]:
    from ada.life.food.tools import run_life_barcode_lookup as _run

    return _run(args)


def run_life_meal_log(args: dict[str, Any]) -> dict[str, Any]:
    from ada.life.food.tools import run_life_meal_log as _run

    return _run(args)


def run_life_food_favorite_set(args: dict[str, Any]) -> dict[str, Any]:
    from ada.life.food.tools import run_life_food_favorite_set as _run

    return _run(args)


def run_life_split_set(args: dict[str, Any]) -> dict[str, Any]:
    from ada.life.gym.tools import run_life_split_set as _run

    return _run(args)


def run_life_habit_create(args: dict[str, Any]) -> dict[str, Any]:
    from ada.life.habits.tools import run_life_habit_create as _run

    return _run(args)


def run_life_meal_fix(args: dict[str, Any]) -> dict[str, Any]:
    from ada.life.food.tools import run_life_meal_fix as _run

    return _run(args)


def run_life_nutrition_day(args: dict[str, Any]) -> dict[str, Any]:
    from ada.life.food.tools import run_life_nutrition_day as _run

    return _run(args)


def run_life_nutrition_week(args: dict[str, Any]) -> dict[str, Any]:
    from ada.life.food.tools import run_life_nutrition_week as _run

    return _run(args)


def run_life_gym_start(args: dict[str, Any]) -> dict[str, Any]:
    from ada.life.gym.tools import run_life_gym_start as _run

    return _run(args)


def run_life_lift_log(args: dict[str, Any]) -> dict[str, Any]:
    from ada.life.gym.tools import run_life_lift_log as _run

    return _run(args)


def run_life_gym_end(args: dict[str, Any]) -> dict[str, Any]:
    from ada.life.gym.tools import run_life_gym_end as _run

    return _run(args)


def run_life_time_start(args: dict[str, Any]) -> dict[str, Any]:
    from ada.life.time.tools import run_life_time_start as _run

    return _run(args)


def run_life_time_stop(args: dict[str, Any]) -> dict[str, Any]:
    from ada.life.time.tools import run_life_time_stop as _run

    return _run(args)


def run_life_time_status(args: dict[str, Any]) -> dict[str, Any]:
    from ada.life.time.tools import run_life_time_status as _run

    return _run(args)


def run_life_time_day(args: dict[str, Any]) -> dict[str, Any]:
    from ada.life.time.tools import run_life_time_day as _run

    return _run(args)


def run_life_time_week(args: dict[str, Any]) -> dict[str, Any]:
    from ada.life.time.tools import run_life_time_week as _run

    return _run(args)


def run_life_gym_status(args: dict[str, Any]) -> dict[str, Any]:
    from ada.life.gym.tools import run_life_gym_status as _run

    return _run(args)


def run_life_gym_day(args: dict[str, Any]) -> dict[str, Any]:
    from ada.life.gym.tools import run_life_gym_day as _run

    return _run(args)


def run_life_gym_week(args: dict[str, Any]) -> dict[str, Any]:
    from ada.life.gym.tools import run_life_gym_week as _run

    return _run(args)


def run_life_food_preset_save(args: dict[str, Any]) -> dict[str, Any]:
    from ada.life.food.tools import run_life_food_preset_save as _run

    return _run(args)


def run_life_meal_draft_start(args: dict[str, Any]) -> dict[str, Any]:
    from ada.life.food.tools import run_life_meal_draft_start as _run

    return _run(args)


def run_life_meal_draft_add(args: dict[str, Any]) -> dict[str, Any]:
    from ada.life.food.tools import run_life_meal_draft_add as _run

    return _run(args)


def run_life_meal_draft_save(args: dict[str, Any]) -> dict[str, Any]:
    from ada.life.food.tools import run_life_meal_draft_save as _run

    return _run(args)


def run_life_meal_draft_cancel(args: dict[str, Any]) -> dict[str, Any]:
    from ada.life.food.tools import run_life_meal_draft_cancel as _run

    return _run(args)


def run_life_meal_preset_log(args: dict[str, Any]) -> dict[str, Any]:
    from ada.life.food.tools import run_life_meal_preset_log as _run

    return _run(args)


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
    from ada.life.habits.tools import run_life_habit_do as _run

    return _run(args)


def run_life_habit_miss(args: dict[str, Any]) -> dict[str, Any]:
    from ada.life.habits.tools import run_life_habit_miss as _run

    return _run(args)


def run_life_routine_run(args: dict[str, Any]) -> dict[str, Any]:
    from ada.life.habits.tools import run_life_routine_run as _run

    return _run(args)


def run_life_habit_status(args: dict[str, Any]) -> dict[str, Any]:
    from ada.life.habits.tools import run_life_habit_status as _run

    return _run(args)


def run_life_habit_day(args: dict[str, Any]) -> dict[str, Any]:
    from ada.life.habits.tools import run_life_habit_day as _run

    return _run(args)


def run_life_habit_week(args: dict[str, Any]) -> dict[str, Any]:
    from ada.life.habits.tools import run_life_habit_week as _run

    return _run(args)


def run_life_person_capture(args: dict[str, Any]) -> dict[str, Any]:
    from ada.life.people.tools import run_life_person_capture as _run

    return _run(args)


def run_life_who_is(args: dict[str, Any]) -> dict[str, Any]:
    from ada.life.people.tools import run_life_who_is as _run

    return _run(args)


def run_life_person_note(args: dict[str, Any]) -> dict[str, Any]:
    from ada.life.people.tools import run_life_person_note as _run

    return _run(args)


def run_life_birthday_set(args: dict[str, Any]) -> dict[str, Any]:
    from ada.life.people.tools import run_life_birthday_set as _run

    return _run(args)


def run_life_people_remind(args: dict[str, Any]) -> dict[str, Any]:
    from ada.life.people.tools import run_life_people_remind as _run

    return _run(args)


def run_life_alias_set(args: dict[str, Any]) -> dict[str, Any]:
    from ada.life.people.tools import run_life_alias_set as _run

    return _run(args)


def run_life_person_update(args: dict[str, Any]) -> dict[str, Any]:
    from ada.life.people.tools import run_life_person_update as _run

    return _run(args)


DISPATCH = {
    "life_food_search": run_life_food_search,
    "life_barcode_lookup": run_life_barcode_lookup,
    "life_meal_log": run_life_meal_log,
    "life_meal_fix": run_life_meal_fix,
    "life_nutrition_day": run_life_nutrition_day,
    "life_nutrition_week": run_life_nutrition_week,
    "life_gym_start": run_life_gym_start,
    "life_lift_log": run_life_lift_log,
    "life_gym_end": run_life_gym_end,
    "life_time_start": run_life_time_start,
    "life_time_stop": run_life_time_stop,
    "life_time_status": run_life_time_status,
    "life_time_day": run_life_time_day,
    "life_time_week": run_life_time_week,
    "life_gym_status": run_life_gym_status,
    "life_gym_day": run_life_gym_day,
    "life_gym_week": run_life_gym_week,
    "life_food_preset_save": run_life_food_preset_save,
    "life_food_favorite_set": run_life_food_favorite_set,
    "life_meal_draft_start": run_life_meal_draft_start,
    "life_meal_draft_add": run_life_meal_draft_add,
    "life_meal_draft_save": run_life_meal_draft_save,
    "life_meal_draft_cancel": run_life_meal_draft_cancel,
    "life_meal_preset_log": run_life_meal_preset_log,
    "life_split_set": run_life_split_set,
    "life_habit_create": run_life_habit_create,
    "life_capture": run_life_capture,
    "life_habit_do": run_life_habit_do,
    "life_habit_miss": run_life_habit_miss,
    "life_routine_run": run_life_routine_run,
    "life_habit_status": run_life_habit_status,
    "life_habit_day": run_life_habit_day,
    "life_habit_week": run_life_habit_week,
    "life_person_capture": run_life_person_capture,
    "life_who_is": run_life_who_is,
    "life_person_note": run_life_person_note,
    "life_birthday_set": run_life_birthday_set,
    "life_people_remind": run_life_people_remind,
    "life_alias_set": run_life_alias_set,
    "life_person_update": run_life_person_update,
}
