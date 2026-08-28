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
    resolve = args.get("resolve") if isinstance(args.get("resolve"), dict) else None
    confirmed = bool(args.get("confirmed", False))
    # M21: ambiguous bind held at gateway — no write until confirmed=true.
    if resolve and not confirmed:
        return {
            "ok": False,
            "needs_confirm": True,
            "outcome": "needs_confirm",
            "reason": (resolve.get("reasons") or ["ambiguous"])[0]
            if isinstance(resolve.get("reasons"), list)
            else resolve.get("reason") or "ambiguous",
            "reasons": list(resolve.get("reasons") or []),
            "candidates": list(resolve.get("candidates") or []),
            "resolve": resolve,
            "lines": lines,
            "meal_slot": args.get("meal_slot"),
            "note": args.get("note"),
            "save_favorite": bool(args.get("save_favorite", True)),
        }
    # Strip spine-private keys before durable write.
    clean_lines = []
    for line in lines:
        if not isinstance(line, dict):
            continue
        clean = {k: v for k, v in line.items() if not str(k).startswith("_")}
        # F-M24-2: refuse empty-macro durable write even after Confirm Yes.
        nutrients = clean.get("nutrients")
        if isinstance(nutrients, dict):
            macros = ("energy_kcal", "protein_g", "fat_g", "carb_g")
            if all(nutrients.get(k) is None for k in macros):
                return {
                    "ok": False,
                    "outcome": "error",
                    "reason": "empty_macros",
                    "error": "empty_macros",
                    "lines": lines,
                }
        snap = clean.get("snapshot_json")
        if isinstance(snap, dict):
            sn = snap.get("nutrients") if isinstance(snap.get("nutrients"), dict) else {}
            macros = ("energy_kcal", "protein_g", "fat_g", "carb_g")
            if sn and all(sn.get(k) is None for k in macros):
                return {
                    "ok": False,
                    "outcome": "error",
                    "reason": "empty_macros",
                    "error": "empty_macros",
                    "lines": lines,
                }
        clean_lines.append(clean)
    outcome = meals_mod.meal_log(
        receipt_id=receipt_id,
        note=args.get("note"),
        meal_slot=args.get("meal_slot"),
        lines=clean_lines,
    )
    written = _write("life_meal_log", receipt_id, outcome)
    if (
        written.get("ok")
        and confirmed
        and bool(args.get("save_favorite", False))
        and resolve
    ):
        from ada.logs import favorites as favorites_mod

        for row in resolve.get("rows") or []:
            q = str(row.get("query") or row.get("query_norm") or "").strip()
            ref = str(row.get("proposed_ref_id") or "").strip()
            if not q or not ref:
                continue
            preview = None
            for cand in row.get("candidates") or []:
                if str(cand.get("ref_id") or "") == ref:
                    preview = cand
                    break
            favorites_mod.set_favorite(
                query=q,
                ref_id=ref,
                label=(preview or {}).get("label"),
                brand=(preview or {}).get("brand"),
                confirmed=True,
            )
    return written


def run_life_food_favorite_set(args: dict[str, Any]) -> dict[str, Any]:
    from ada.logs import favorites as favorites_mod

    outcome = favorites_mod.set_favorite(
        query=str(args.get("query") or ""),
        ref_id=str(args.get("ref_id") or ""),
        label=args.get("label"),
        brand=args.get("brand"),
        confirmed=bool(args.get("confirmed", False)),
    )
    if outcome.get("needs_confirm"):
        outcome["ok"] = False
    return outcome


def run_life_split_set(args: dict[str, Any]) -> dict[str, Any]:
    """Sticky gym_split FACT after Confirm Yes (M22 teach-in-flow)."""
    from ada.logs import gym_split as split_mod

    days = args.get("days")
    if days is None and isinstance(args.get("gym_split"), dict):
        days = (args.get("gym_split") or {}).get("days")
    outcome = split_mod.set_gym_split(
        days=days if isinstance(days, dict) else {},
        confirmed=bool(args.get("confirmed", False)),
        schema_version=int(args.get("schema_version") or 1),
    )
    if outcome.get("needs_confirm"):
        outcome["ok"] = False
    return outcome


def run_life_habit_create(args: dict[str, Any]) -> dict[str, Any]:
    """Confirm-create habit definition (teach-in-flow); optional same-turn tick."""
    receipt_id = str(args.get("receipt_id") or "")
    display_name = str(
        args.get("display_name") or args.get("proposed_display_name") or args.get("name") or ""
    ).strip()
    outcome = habits_mod.create_habit(
        display_name=display_name,
        aliases=args.get("aliases") if isinstance(args.get("aliases"), list) else None,
        schedule=args.get("schedule") if isinstance(args.get("schedule"), dict) else None,
        confirmed=bool(args.get("confirmed", False)),
        tick_after=bool(args.get("tick_after", False)),
        note=args.get("note"),
        receipt_id=receipt_id or None,
    )
    if outcome.get("needs_confirm"):
        outcome["ok"] = False
        return outcome
    return _write("life_habit_create", receipt_id, outcome)

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


def _habit_id_exists(habit_id: str | None) -> bool:
    hid = str(habit_id or "").strip()
    if not hid:
        return False
    return any(h.get("habit_id") == hid for h in habits_mod.list_habit_definitions())


def _habit_create_confirm(name: str, *, tick_after: bool = True) -> dict[str, Any]:
    """0-match → Confirm-create payload (HUD remaps to life_habit_create)."""
    return habits_mod.create_habit(
        display_name=name,
        confirmed=False,
        tick_after=tick_after,
    )


def _habit_ambiguous_confirm(
    *,
    name: str,
    matches: list[dict[str, Any]],
    resolve: dict[str, Any] | None = None,
    candidates: list[Any] | None = None,
    habit_id: Any = None,
) -> dict[str, Any]:
    from ada.harness.resolve_gate import decide_habit_bind

    if resolve and (candidates or resolve.get("candidates")):
        cands = list(candidates or resolve.get("candidates") or [])
        return {
            "ok": False,
            "needs_confirm": True,
            "outcome": "needs_confirm",
            "reason": resolve.get("reason") or "ambiguous",
            "reasons": list(resolve.get("reasons") or ["many"]),
            "candidates": cands,
            "resolve": resolve,
            "name": name,
            "habit_id": habit_id or resolve.get("proposed_habit_id"),
        }
    decision = decide_habit_bind(query=name, matches=matches)
    return {
        "ok": False,
        "needs_confirm": True,
        "outcome": "needs_confirm",
        "reason": "ambiguous",
        "reasons": list(decision.get("reasons") or ["many"]),
        "candidates": list(decision.get("candidates") or []),
        "resolve": {
            "reason": "ambiguous",
            "candidates": list(decision.get("candidates") or []),
            "proposed_habit_id": decision.get("proposed_habit_id"),
            "query": name,
        },
        "name": name,
        "habit_id": decision.get("proposed_habit_id"),
    }


def _gate_habit_tick(args: dict[str, Any], *, allow_create: bool) -> dict[str, Any] | None:
    """Return needs_confirm / create payload, or None to proceed with bound habit_id.

    Never silent-create. Never write a stale/invented habit_id (FK class).
    Chat Yes alone is not Confirm — cortex confirmed=true still re-resolves.
    """
    from ada.harness.habit_spine import clean_habit_name

    confirmed = bool(args.get("confirmed", False))
    resolve = args.get("resolve") if isinstance(args.get("resolve"), dict) else None
    candidates = list(args.get("candidates") or [])
    if resolve and not candidates:
        candidates = list(resolve.get("candidates") or [])
    name = clean_habit_name(
        str(args.get("name") or args.get("utterance") or args.get("display_name") or "")
    )
    habit_id = str(args.get("habit_id") or "").strip() or None

    # Stale / model-invented id — drop and re-resolve (Consent Integrity).
    if habit_id and not _habit_id_exists(habit_id):
        habit_id = None

    if (resolve or (len(candidates) > 1)) and not confirmed:
        return _habit_ambiguous_confirm(
            name=name,
            matches=[],
            resolve=resolve,
            candidates=candidates,
            habit_id=habit_id or args.get("habit_id"),
        )

    if habit_id:
        # Real id after Confirm or unique bind — proceed.
        args["habit_id"] = habit_id
        if name:
            args["name"] = name
        return None

    if not name:
        return {"ok": False, "reason": "missing_name", "outcome": "error"}

    resolved = habits_mod.resolve_habit(name)
    if resolved.get("ok"):
        args["habit_id"] = resolved["habit_id"]
        args["name"] = name
        return None

    matches = list(resolved.get("matches") or [])
    if len(matches) > 1:
        return _habit_ambiguous_confirm(name=name, matches=matches)

    if allow_create:
        # 0-match — Confirm-create (no silent SQL; no FK).
        return _habit_create_confirm(name, tick_after=True)

    return {
        "ok": False,
        "reason": "missing_life_receipt",
        "match_count": 0,
        "matches": [],
        "name": name,
    }


def run_life_habit_do(args: dict[str, Any]) -> dict[str, Any]:
    receipt_id = str(args.get("receipt_id") or "")
    gated = _gate_habit_tick(args, allow_create=True)
    if gated is not None:
        return gated
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
    gated = _gate_habit_tick(args, allow_create=False)
    if gated is not None:
        return gated
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
    "life_food_favorite_set": run_life_food_favorite_set,
    "life_split_set": run_life_split_set,
    "life_habit_create": run_life_habit_create,
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
