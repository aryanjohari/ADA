"""Verb/chip → life tool routing (M19a)."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path
import re
from typing import Any

import yaml

from ada.life.food.date import (
    has_week_cue,
    local_today,
    parse_nutrition_date,
)
from ada.life.food.doors import (
    _ADD_MEAL,
    _MEAL_MULTI,
    _MEAL_MULTI_BARE,
    _MEAL_SINGLE,
    _MEAL_SLOT,
    _meal_body_from_raw,
    _normalize_meal_slot,
    is_meal_log_utterance,
    meal_log_fast_path_args,
    route_nutrition_read,
)
from ada.life.gym.date import parse_gym_date
from ada.life.gym.doors import (
    gym_read_takes_priority,
    is_gym_end_utterance,
    is_gym_start_utterance,
    is_incomplete_lift_utterance,
    is_lift_log_utterance,
    lift_log_fast_path_args,
    route_gym_read,
)
from ada.life.habits.date import parse_habit_date
from ada.life.habits.doors import (
    _HABIT_DONE_NL,
    _HABIT_MISS_NL,
    is_habit_do_utterance,
    is_habit_miss_utterance,
    route_habit_read,
)
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
from ada.life.time.date import parse_time_date
from ada.life.time.doors import is_time_start_utterance, route_time_read, route_time_start_focus
from ada.life.time.intent import map_time_intent
from ada.life.utterance import strip_leading_filler

_DEFAULT_PACK = "life_p0.yaml"
_P1_PACK = "life_p1.yaml"
_BRIEF_PREF_NL = re.compile(
    r"\b(?:don'?t|do\s+not|exclude|remove|hide|omit|add|include|put|show)\b.*\bbrief\b"
    r"|\bbrief\b.*\b(?:don'?t|do\s+not|exclude|remove|hide|omit|add|include|put|show)\b",
    re.IGNORECASE,
)

READ_PACK_VERBS = frozenset(
    {
        "nutrition_day",
        "nutrition_week",
        "time_status",
        "time_day",
        "time_week",
        "due_list",
        "gym_status",
        "gym_day",
        "gym_week",
        "habit_day",
        "habit_week",
        "life_status",
        "streak_show",
        "who_is",
        "people_remind",
    }
)
ADMIN_WRITE_VERBS = frozenset({"due_add", "remind", "due_done"})
CONFIRM_BOUND_VERBS = frozenset(
    {"alias_set", "person_update", "routine_edit", "kin_link"}
)
# Model must never self-Confirm — HUD Confirm Yes is the only confirmed=true path.
MODEL_STRIP_CONFIRMED = frozenset(
    {
        "life_habit_do",
        "life_habit_miss",
        "life_habit_create",
        "life_split_set",
        "life_meal_log",
        "life_meal_draft_add",
        "life_meal_draft_save",
        "life_meal_preset_log",
        "life_food_preset_save",
        "life_food_favorite_set",
        "life_person_capture",
        "memory_facts_propose_edit",
        "memory_facts_append",
    }
)


def _pack_path(name: str = _DEFAULT_PACK) -> Path:
    return Path(str(files("ada.harness.packs") / name))


def _merge_pack_configs(*configs: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {"packs": {}, "chips": {}, "aliases": []}
    for cfg in configs:
        merged["packs"] = {**merged["packs"], **(cfg.get("packs") or {})}
        merged["chips"] = {**merged["chips"], **(cfg.get("chips") or {})}
        merged["aliases"] = list(merged["aliases"]) + list(cfg.get("aliases") or [])
    return merged


def load_pack_config(path: Path | None = None) -> dict[str, Any]:
    if path is not None:
        if not path.is_file():
            return {"packs": {}, "chips": {}, "aliases": []}
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        loaded.setdefault("packs", {})
        loaded.setdefault("chips", {})
        loaded.setdefault("aliases", [])
        return loaded
    p0_path = _pack_path(_DEFAULT_PACK)
    p1_path = _pack_path(_P1_PACK)
    p0 = {"packs": {}, "chips": {}, "aliases": []}
    if p0_path.is_file():
        p0 = yaml.safe_load(p0_path.read_text(encoding="utf-8")) or p0
    p1 = {"packs": {}, "chips": {}, "aliases": []}
    if p1_path.is_file():
        p1 = yaml.safe_load(p1_path.read_text(encoding="utf-8")) or p1
    return _merge_pack_configs(p0, p1)


def resolve_pack(verb: str, *, config: dict[str, Any] | None = None) -> dict[str, Any] | None:
    cfg = config or load_pack_config()
    packs = cfg.get("packs") or {}
    entry = packs.get(verb)
    if not entry:
        return None
    tool = entry.get("tool")
    if entry.get("alias_of"):
        base = packs.get(entry["alias_of"]) or {}
        tool = base.get("tool") or tool
        entry = {**base, **entry}
    return {
        "verb": verb,
        "tool": tool,
        "prefill": entry.get("prefill"),
        "preferred_tools": list(entry.get("preferred_tools") or []),
        "spine": entry.get("spine"),
        "arg_hints": dict(entry.get("arg_hints") or {}),
    }


def _route_from_pack(
    verb: str,
    raw: str,
    body: str,
    *,
    config: dict[str, Any],
) -> dict[str, Any] | None:
    pack = resolve_pack(verb, config=config)
    if not pack:
        return None
    tool = str(pack.get("tool") or "")
    args = dict(pack.get("arg_hints") or {})
    if tool == "life_time_start":
        args.update(map_time_intent(body or raw))
    elif tool == "life_capture":
        args["text"] = body or raw
    elif tool == "life_meal_log":
        args["utterance"] = body
        slot = _MEAL_SLOT.search(body or raw)
        if slot:
            args["meal_slot"] = _normalize_meal_slot(slot.group(1))
    elif tool == "life_meal_draft_start":
        args["utterance"] = body or raw
    elif tool == "life_meal_draft_save":
        from ada.life.food.draft_spine import parse_save_as_name

        args["utterance"] = body or raw
        name = parse_save_as_name(raw) or parse_save_as_name(body or "")
        if name:
            args["name"] = name
    elif tool == "life_meal_draft_cancel":
        args["utterance"] = body or raw
    elif tool == "life_meal_preset_log":
        from ada.life.food.draft_spine import parse_log_preset_name

        args["utterance"] = body or raw
        name = parse_log_preset_name(raw) or (body or "").strip()
        name = re.sub(r"^my\s+", "", name, flags=re.I).strip()
        if name:
            args["name"] = name
        slot = _MEAL_SLOT.search(body or raw)
        if slot:
            args["meal_slot"] = _normalize_meal_slot(slot.group(1))
    elif tool == "life_barcode_lookup":
        from ada.life.food.draft_spine import parse_barcode_gtin

        gtin = parse_barcode_gtin(raw) or parse_barcode_gtin(body or "")
        if not gtin:
            # "barcode: 123…" body after prefill strip
            gtin = re.sub(r"\D", "", body or "")
        if gtin:
            args["barcode"] = gtin
    elif tool == "life_lift_log":
        args["utterance"] = body or raw
    elif tool == "memory_open_loops_upsert":
        args["utterance"] = body or raw
        args["text"] = body or raw
    elif tool == "memory_open_loops_list":
        args.setdefault("kind", "todo")
        args.setdefault("status", "open")
    elif tool in {"life_habit_do", "life_habit_miss", "life_routine_run"}:
        args["utterance"] = body or raw
        args["name"] = body or raw
    elif tool == "memory_facts_propose_edit" and verb == "brief_include":
        args["utterance"] = body or raw
    elif tool == "life_person_capture":
        args["utterance"] = body or raw
    elif tool == "life_who_is":
        mention = body or raw
        if str(mention).lower().startswith("who is "):
            mention = str(mention)[7:].strip()
        args["mention"] = mention
    elif tool == "life_birthday_set":
        args["body"] = body or raw
    elif tool == "life_person_note":
        args["text"] = body or raw
    elif tool == "life_alias_set":
        args["utterance"] = body or raw
    elif tool == "life_person_update":
        args["utterance"] = body or raw
    elif tool == "life_nutrition_week":
        args.setdefault("days", 7)
    elif tool == "life_nutrition_day":
        if not has_week_cue(raw):
            parsed = parse_nutrition_date(raw)
            if parsed:
                args["date"] = parsed
            elif verb == "nutrition_day":
                args.setdefault("date", local_today())
    elif tool == "life_gym_week":
        args.setdefault("days", 7)
    elif tool == "life_gym_day":
        if not has_week_cue(raw):
            parsed = parse_gym_date(raw)
            if parsed:
                args["date"] = parsed
            elif verb == "gym_day":
                args.setdefault("date", local_today())
    elif tool == "life_time_week":
        args.setdefault("days", 7)
    elif tool == "life_time_day":
        if not has_week_cue(raw):
            parsed = parse_time_date(raw)
            if parsed:
                args["date"] = parsed
            elif verb == "time_day":
                args.setdefault("date", local_today())
    elif tool == "life_habit_week":
        args.setdefault("days", 7)
    elif tool == "life_habit_day":
        if not has_week_cue(raw):
            parsed = parse_habit_date(raw)
            if parsed:
                args["date"] = parsed
            elif verb == "habit_day":
                args.setdefault("date", local_today())
    return {
        "verb": verb,
        "tool": tool,
        "args": args,
        "body": body,
        "preferred_tools": list(pack.get("preferred_tools") or []),
        "spine": pack.get("spine"),
    }


def resolve_chip(chip: str, *, config: dict[str, Any] | None = None) -> dict[str, Any] | None:
    cfg = config or load_pack_config()
    verb = (cfg.get("chips") or {}).get(chip)
    if not verb:
        return None
    return resolve_pack(verb, config=cfg)


def _route_nutrition_read(
    raw: str,
    *,
    config: dict[str, Any],
) -> dict[str, Any] | None:
    """Structural nutrition read: week window or explicit/relative day."""
    return route_nutrition_read(
        raw,
        route_from_pack=_route_from_pack,
        config=config,
    )


def _route_gym_read(
    raw: str,
    *,
    config: dict[str, Any],
) -> dict[str, Any] | None:
    """Structural gym read: week window or explicit/relative day. Not gym_status."""
    return route_gym_read(
        raw,
        route_from_pack=_route_from_pack,
        config=config,
    )


def _route_time_read(
    raw: str,
    *,
    config: dict[str, Any],
) -> dict[str, Any] | None:
    """Structural time day/week read. Not time_status / what's running."""
    return route_time_read(
        raw,
        has_week_cue=has_week_cue,
        route_from_pack=_route_from_pack,
        config=config,
    )


def _route_habit_read(
    raw: str,
    *,
    config: dict[str, Any],
) -> dict[str, Any] | None:
    """Structural habit day/week read. Not undated habits today / streak_show."""
    return route_habit_read(
        raw,
        route_from_pack=_route_from_pack,
        config=config,
    )


def _route_aliases(
    raw: str,
    lower: str,
    *,
    config: dict[str, Any],
) -> dict[str, Any] | None:
    aliases = sorted(
        (a for a in (config.get("aliases") or []) if isinstance(a, dict)),
        key=lambda a: len(str(a.get("pattern") or "")),
        reverse=True,
    )
    for alias in aliases:
        pattern = str(alias.get("pattern") or "").strip().lower()
        verb = str(alias.get("verb") or "").strip()
        if pattern and verb and pattern in lower:
            # Substring "starting gym" must not steal "I'm starting gym commute".
            if verb == "gym_start" and not is_gym_start_utterance(raw):
                continue
            return _route_from_pack(verb, raw, raw, config=config)
    return None


_DUE_ADD_LEAD = re.compile(
    r"^(?:add\s+due:\s*|gotta(?:\s+finish)?\s+|i\s+need\s+to\s+finish\s+)",
    re.IGNORECASE,
)
_DUE_LIST_CUES = (
    "what's due",
    "whats due",
    "on my plate",
    "have to buy",
    "what to buy",
    "grocery",
    "shopping list",
)


def _due_other_organ(raw: str) -> bool:
    """Meal / lift / gym / time / habit wrappers win over due."""
    return (
        is_habit_do_utterance(raw)
        or is_habit_miss_utterance(raw)
        or is_gym_start_utterance(raw)
        or is_gym_end_utterance(raw)
        or is_time_start_utterance(raw)
        or is_lift_log_utterance(raw)
        or is_meal_log_utterance(raw)
    )


def is_due_add_utterance(text: str) -> bool:
    """Wrapper pack door for due_add — title is a slot, not a YAML row.

    Hint optional: wrappers force the verb even if pack_hint is missing.
    Bare titles (thesis) without a wrapper are not a door.
    """
    raw = strip_leading_filler(text)
    if not raw or _due_other_organ(raw):
        return False
    lower = raw.lower()
    if _DUE_ADD_LEAD.match(raw):
        return True
    return "due by" in lower


def is_remind_utterance(text: str) -> bool:
    """Wrapper pack door for remind — `remind:` / `remind me`. Not people_remind."""
    raw = strip_leading_filler(text)
    if not raw or _due_other_organ(raw):
        return False
    lower = raw.lower()
    if lower.startswith("people remind"):
        return False
    if lower.startswith("remind:"):
        return True
    return "remind me" in lower


def is_due_done_utterance(text: str) -> bool:
    """Wrapper pack door for due_done — `done:` only. Not habit done / gym end."""
    raw = strip_leading_filler(text)
    if not raw:
        return False
    lower = raw.lower()
    if not lower.startswith("done:"):
        return False
    if is_habit_do_utterance(raw) or is_gym_end_utterance(raw):
        return False
    return True


def is_due_list_utterance(text: str) -> bool:
    """Read door for due_list — grocery/shopping aliases stay this organ."""
    raw = strip_leading_filler(text)
    if not raw or _due_other_organ(raw):
        return False
    lower = raw.lower()
    return any(cue in lower for cue in _DUE_LIST_CUES)


def route_utterance(text: str, *, config: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Map utterance prefix, YAML alias, or structural parser to tool + args hint."""
    raw = strip_leading_filler(text)
    lower = raw.lower()
    cfg = config or load_pack_config()
    packs = cfg.get("packs") or {}

    for verb, entry in packs.items():
        prefill = (entry.get("prefill") or "").lower()
        if prefill and lower.startswith(prefill):
            body = raw[len(prefill) :].strip()
            return _route_from_pack(verb, raw, body, config=cfg)

    gym = _route_gym_read(raw, config=cfg)
    if gym is not None:
        return gym

    nutrition = _route_nutrition_read(raw, config=cfg)
    if nutrition is not None:
        return nutrition

    timed = _route_time_read(raw, config=cfg)
    if timed is not None:
        return timed

    habit_read = _route_habit_read(raw, config=cfg)
    if habit_read is not None:
        return habit_read

    # Lift writes before YAML aliases so "at the gym" cannot steal kg×reps NL.
    if is_lift_log_utterance(raw):
        lift_args = lift_log_fast_path_args(raw) or {}
        body = str(lift_args.get("utterance") or raw)
        return _route_from_pack("lift_log", raw, body, config=cfg)

    aliased = _route_aliases(raw, lower, config=cfg)
    if aliased is not None:
        return aliased

    # Structural create-meal draft (make / wanna make / add a meal) before meal_log.
    from ada.life.food.draft_spine import is_meal_draft_start

    if is_meal_draft_start(raw):
        return _route_from_pack("meal_draft_start", raw, raw, config=cfg)

    if lower.startswith("start focus") or lower.startswith("start timer"):
        return route_time_start_focus(raw, resolve_pack=resolve_pack, config=cfg)

    meal = _ADD_MEAL.match(raw)
    if meal:
        routed = _route_from_pack("meal_log", raw, meal.group(1).strip(), config=cfg)
        if routed is not None:
            routed["args"]["meal_slot"] = _normalize_meal_slot(meal.group(2))
        return routed

    meal_single = _MEAL_SINGLE.match(raw)
    if meal_single:
        body = meal_single.group(1).strip()
        routed = _route_from_pack("meal_log", raw, body, config=cfg)
        if routed is not None:
            routed["args"]["meal_slot"] = None
        return routed

    # Multi-item meal NL → always meal spine (slot optional; M26 pack fence).
    if _MEAL_MULTI.search(raw) or _MEAL_MULTI_BARE.search(raw):
        slot_m = _MEAL_SLOT.search(raw)
        slot = _normalize_meal_slot(slot_m.group(1)) if slot_m else None
        body = _meal_body_from_raw(raw, slot=slot_m.group(1) if slot_m else None)
        routed = _route_from_pack("meal_log", raw, body, config=cfg)
        if routed is not None and slot:
            routed["args"]["meal_slot"] = slot
        return routed

    # Habit NL before bare due — wrappers only (not "done: thesis" / bare skincare).
    if is_habit_do_utterance(raw):
        done_m = _HABIT_DONE_NL.match(raw)
        body = (done_m.group(1) if done_m else "").strip()
        if body:
            return _route_from_pack("habit_do", raw, body, config=cfg)

    if is_habit_miss_utterance(raw):
        miss_m = _HABIT_MISS_NL.match(raw)
        body = (miss_m.group(1) if miss_m else "").strip()
        if body:
            return _route_from_pack("habit_miss", raw, body, config=cfg)

    if _BRIEF_PREF_NL.search(raw):
        return _route_from_pack("brief_include", raw, raw, config=cfg)

    if is_gym_start_utterance(raw):
        return _route_from_pack("gym_start", raw, raw, config=cfg)

    if is_gym_end_utterance(raw):
        return _route_from_pack("gym_end", raw, raw, config=cfg)

    # After meal / lift / gym start / gym end — start-shapes only, hint optional.
    if is_time_start_utterance(raw):
        return _route_from_pack("time_start", raw, raw, config=cfg)

    # After meal / lift / gym / time / habit — people wrappers (prefill usually wins first).
    if is_person_capture_utterance(raw):
        return _route_from_pack("person_capture", raw, raw, config=cfg)
    if is_who_is_utterance(raw):
        return _route_from_pack("who_is", raw, who_is_mention(raw), config=cfg)
    if is_person_note_utterance(raw):
        return _route_from_pack("person_note", raw, person_note_body(raw), config=cfg)
    if is_alias_set_utterance(raw):
        return _route_from_pack("alias_set", raw, alias_set_body(raw), config=cfg)
    if is_birthday_set_utterance(raw):
        return _route_from_pack("birthday_set", raw, birthday_set_body(raw), config=cfg)
    if is_people_remind_utterance(raw):
        return _route_from_pack("people_remind", raw, raw, config=cfg)

    return None
