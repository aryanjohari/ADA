"""Verb/chip → life tool routing (M19a)."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path
import re
from typing import Any

import yaml

from ada.harness.gym_date import is_gym_read_shape, parse_gym_date
from ada.harness.gym_spine import is_bare_nxm_without_unit, lift_utterance_body
from ada.harness.habit_date import is_habit_read_shape, parse_habit_date
from ada.harness.nutrition_date import (
    has_week_cue,
    is_nutrition_read_shape,
    local_today,
    parse_nutrition_date,
)
from ada.harness.time_date import is_time_read_shape, parse_time_date
from ada.harness.time_intent import map_time_intent

_DEFAULT_PACK = "life_p0.yaml"
_P1_PACK = "life_p1.yaml"
_MEAL_SLOT = re.compile(
    r"\b(?:to|for)\s+(?:an?\s+|the\s+)?(breakfast|lunch|dinner|snacks?)\b",
    re.IGNORECASE,
)
# STT often hears "Long meal" for "Log meal"; allow optional "meal" + article before slot.
_ADD_MEAL = re.compile(
    r"^(?:add|log|long)\s+(?:meal\s+)?(.+?)\s+(?:to|for)\s+(?:an?\s+|the\s+)?"
    r"(breakfast|lunch|dinner|snacks?)\b",
    re.IGNORECASE,
)
_LIFT_LINE = re.compile(r"\b(?:\d+(?:\.\d+)?)\s*(?:kg|kgs|lb|lbs)\s*x\s*\d+\b", re.IGNORECASE)
# Multi-set ladder without requiring "log lift:" (M24 pack preference).
_LIFT_LADDER = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:kg|kgs|lb|lbs)?\s*[x×]\s*\d+\s*"
    r"(?:reps?\s+)?(?:\d+(?:\.\d+)?\s*(?:kg|kgs|lb|lbs)?\s*[x×]\s*\d+)",
    re.IGNORECASE,
)
# "3x6 at 50kg" / "flat bench 3x6 @ 50" — sets×reps with load (M26 v1.2).
_LIFT_SETS_AT_LOAD = re.compile(
    r"\b\d+\s*[x×]\s*\d+\s*(?:at|@)\s*\d+(?:\.\d+)?\s*(?:kg|kgs|lb|lbs)?\b",
    re.IGNORECASE,
)
_GYM_START_SHAPE = re.compile(
    r"(?:"
    r"(?:i(?:['’]?m|\s+am)\s+)?at\s+(?:the\s+)?gym"
    r"|(?:i\s+)?start(?:ed|ing)?\s+(?:a\s+|the\s+)?gym"
    r")\.?\s*$",
    re.IGNORECASE,
)
# Time pack door — start-shapes only. Labels are slots, not YAML/regex per phrase.
# Ordered most-specific first so "I'm starting X" does not collapse to "I'm X".
_TIME_START_SHAPE = re.compile(
    r"^(?:"
    r"i\s+started\s+\S.*"
    r"|i(?:['’]?m|\s+am)\s+starting\s+\S.*"
    r"|starting\s+\S.*"
    r"|i(?:['’]?m|\s+am)\s+\S.*"
    r")",
    re.IGNORECASE,
)
_GYM_END_SHAPE = re.compile(
    r"(?:"
    r"\b(?:i\s+)?(?:finish(?:ed)?|done|end(?:ed)?|close[d]?)\s+"
    r"(?:the\s+|a\s+)?(?:gym|workout)\b"
    r"|\bgym\s+done\b"
    r")",
    re.IGNORECASE,
)
# Whole-utterance exercise name (catalog/custom fold) — not a sentence.
_NAME_ONLY_LIFT = re.compile(
    r"^[A-Za-z][A-Za-z'+-]*(?:\s+[A-Za-z][A-Za-z'+-]*){0,5}$"
)
_NAME_ONLY_CHAT = re.compile(
    r"^(?:i|i['’]m|im|we|what|how|did|do|why)\b",
    re.IGNORECASE,
)
_LIFT_PREFIX = re.compile(r"^(?:log\s+lift\b|lift\s*:)", re.IGNORECASE)
# Multi-item meal: log/add + qty cue + and/+ — slot optional (M26 path integrity).
_MEAL_MULTI = re.compile(
    r"\b(?:log|add|long)\b.+"
    r"(?:\d+(?:\.\d+)?\s*(?:g|grams?|kg|oz|ml|cups?|cup|tbsp|tsp)?|"
    r"(?:a|an|one|two|three|four|five|six|seven|eight|nine|ten)\s+)"
    r".+\b(?:and|\+)\b",
    re.IGNORECASE,
)
# Bare grams + and/+ + meal slot (no log verb) — still pack fence.
_MEAL_MULTI_BARE = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:g|grams?|kg|oz)?\b.+\b(?:and|\+)\b.+"
    r"\b(?:for|to)\s+(?:an?\s+|the\s+)?(?:breakfast|lunch|dinner|snacks?)\b",
    re.IGNORECASE,
)
# Phone NL: "Habit done skincare" / "habit done: skincare" — wrappers, name is a slot.
_HABIT_DONE_NL = re.compile(
    r"^(?:habit\s+)?(?:done|tick|logged)\s*:?\s*(.+)$",
    re.IGNORECASE,
)
_HABIT_MISS_NL = re.compile(
    r"^(?:habit\s+)?miss(?:ed)?\s*:?\s*(.+)$",
    re.IGNORECASE,
)
_BRIEF_PREF_NL = re.compile(
    r"\b(?:don'?t|do\s+not|exclude|remove|hide|omit|add|include|put|show)\b.*\bbrief\b"
    r"|\bbrief\b.*\b(?:don'?t|do\s+not|exclude|remove|hide|omit|add|include|put|show)\b",
    re.IGNORECASE,
)
_LEADING_FILLER = re.compile(r"^(?:okay|ok|yeah|yep|sure|please)[,.\s]+", re.I)
_MEAL_SINGLE = re.compile(
    r"^(?:add|log|long)\s+(?:meal\s+)?"
    r"(\d+(?:\.\d+)?\s*(?:g|grams?|kg|oz|ml|cups?)?\s*.+)$",
    re.I,
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
        from ada.harness.meal_draft_spine import parse_save_as_name

        args["utterance"] = body or raw
        name = parse_save_as_name(raw) or parse_save_as_name(body or "")
        if name:
            args["name"] = name
    elif tool == "life_meal_draft_cancel":
        args["utterance"] = body or raw
    elif tool == "life_meal_preset_log":
        from ada.harness.meal_draft_spine import parse_log_preset_name

        args["utterance"] = body or raw
        name = parse_log_preset_name(raw) or (body or "").strip()
        name = re.sub(r"^my\s+", "", name, flags=re.I).strip()
        if name:
            args["name"] = name
        slot = _MEAL_SLOT.search(body or raw)
        if slot:
            args["meal_slot"] = _normalize_meal_slot(slot.group(1))
    elif tool == "life_barcode_lookup":
        from ada.harness.meal_draft_spine import parse_barcode_gtin

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
    if not is_nutrition_read_shape(raw):
        return None
    if has_week_cue(raw):
        routed = _route_from_pack("nutrition_week", raw, raw, config=config)
        if routed is not None:
            routed["args"]["days"] = 7
        return routed
    parsed = parse_nutrition_date(raw)
    if parsed is None:
        return None
    routed = _route_from_pack("nutrition_day", raw, raw, config=config)
    if routed is not None:
        routed["args"]["date"] = parsed
    return routed


def _route_gym_read(
    raw: str,
    *,
    config: dict[str, Any],
) -> dict[str, Any] | None:
    """Structural gym read: week window or explicit/relative day. Not gym_status."""
    if not is_gym_read_shape(raw):
        return None
    if has_week_cue(raw):
        routed = _route_from_pack("gym_week", raw, raw, config=config)
        if routed is not None:
            routed["args"]["days"] = 7
        return routed
    parsed = parse_gym_date(raw)
    if parsed is None:
        return None
    routed = _route_from_pack("gym_day", raw, raw, config=config)
    if routed is not None:
        routed["args"]["date"] = parsed
    return routed


def _route_time_read(
    raw: str,
    *,
    config: dict[str, Any],
) -> dict[str, Any] | None:
    """Structural time day/week read. Not time_status / what's running."""
    if not is_time_read_shape(raw):
        return None
    if has_week_cue(raw):
        routed = _route_from_pack("time_week", raw, raw, config=config)
        if routed is not None:
            routed["args"]["days"] = 7
        return routed
    parsed = parse_time_date(raw)
    if parsed is None:
        return None
    routed = _route_from_pack("time_day", raw, raw, config=config)
    if routed is not None:
        routed["args"]["date"] = parsed
    return routed


def _route_habit_read(
    raw: str,
    *,
    config: dict[str, Any],
) -> dict[str, Any] | None:
    """Structural habit day/week read. Not undated habits today / streak_show."""
    if not is_habit_read_shape(raw):
        return None
    if has_week_cue(raw):
        routed = _route_from_pack("habit_week", raw, raw, config=config)
        if routed is not None:
            routed["args"]["days"] = 7
        return routed
    parsed = parse_habit_date(raw)
    if parsed is None:
        return None
    routed = _route_from_pack("habit_day", raw, raw, config=config)
    if routed is not None:
        routed["args"]["date"] = parsed
    return routed


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


def gym_read_takes_priority(text: str) -> bool:
    """Week / relative-day gym reads win over start/end/lift writes."""
    raw = (text or "").strip()
    if not is_gym_read_shape(raw):
        return False
    if has_week_cue(raw):
        return True
    return parse_gym_date(raw) is not None


def is_gym_start_utterance(text: str) -> bool:
    """Structural gym-start NL — independent of pack_hint match."""
    raw = (text or "").strip()
    raw = _LEADING_FILLER.sub("", raw).strip()
    if not raw or gym_read_takes_priority(raw):
        return False
    return bool(_GYM_START_SHAPE.match(raw))


def is_time_start_utterance(text: str) -> bool:
    """Structural time-start NL — start-shapes only; hint optional.

    Inserted after meal / lift / gym start / gym end so those organs win.
    Bare spine labels without a start-shape are not a door.
    """
    raw = (text or "").strip()
    raw = _LEADING_FILLER.sub("", raw).strip()
    if not raw:
        return False
    if is_meal_log_utterance(raw) or is_lift_log_utterance(raw):
        return False
    if is_incomplete_lift_utterance(raw):
        return False
    if is_gym_start_utterance(raw) or is_gym_end_utterance(raw):
        return False
    lower = raw.lower()
    if lower.startswith("start focus") or lower.startswith("start timer"):
        return True
    return bool(_TIME_START_SHAPE.match(raw))


def is_habit_do_utterance(text: str) -> bool:
    """Wrapper pack door for habit_do — name is a slot, not a YAML row.

    Hint optional: wrappers force the verb even if pack_hint is missing.
    Bare labels (skincare / laundry) without a wrapper are not a door.
    """
    raw = (text or "").strip()
    raw = _LEADING_FILLER.sub("", raw).strip()
    if not raw:
        return False
    lower = raw.lower()
    matched = _HABIT_DONE_NL.match(raw)
    if not matched or not matched.group(1).strip():
        return False
    return (
        lower.startswith("habit ")
        or lower.startswith("habit\t")
        or lower.startswith("tick ")
        or "habit done" in lower
        or "habit tick" in lower
    )


def is_habit_miss_utterance(text: str) -> bool:
    """Wrapper pack door for habit_miss — habit in string, or starts with miss."""
    raw = (text or "").strip()
    raw = _LEADING_FILLER.sub("", raw).strip()
    if not raw:
        return False
    lower = raw.lower()
    matched = _HABIT_MISS_NL.match(raw)
    if not matched or not matched.group(1).strip():
        return False
    return "habit" in lower or lower.startswith("miss")


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
    raw = (text or "").strip()
    raw = _LEADING_FILLER.sub("", raw).strip()
    if not raw or _due_other_organ(raw):
        return False
    lower = raw.lower()
    if _DUE_ADD_LEAD.match(raw):
        return True
    return "due by" in lower


def is_remind_utterance(text: str) -> bool:
    """Wrapper pack door for remind — `remind:` / `remind me`. Not people_remind."""
    raw = (text or "").strip()
    raw = _LEADING_FILLER.sub("", raw).strip()
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
    raw = (text or "").strip()
    raw = _LEADING_FILLER.sub("", raw).strip()
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
    raw = (text or "").strip()
    raw = _LEADING_FILLER.sub("", raw).strip()
    if not raw or _due_other_organ(raw):
        return False
    lower = raw.lower()
    return any(cue in lower for cue in _DUE_LIST_CUES)


# People wrappers — name is a remainder slot, not a YAML row. Bare "Ravi" is not a door.
_MET_NL = re.compile(r"^met\s+(.+)$", re.IGNORECASE)
_WHO_IS_NL = re.compile(r"^who\s+is\s+(.+)$", re.IGNORECASE)
_NOTE_FOR_NL = re.compile(r"^note\s+for\s+(.+)$", re.IGNORECASE)
_ALIAS_SET_NL = re.compile(r"^alias\s+set:\s*(.+)$", re.IGNORECASE)
_BIRTHDAY_SET_NL = re.compile(r"^set\s+birthday:\s*(.+)$", re.IGNORECASE)


def _people_other_organ(raw: str) -> bool:
    """Meal / lift / gym / time / habit / due wrappers win over people."""
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
    raw = (text or "").strip()
    return _LEADING_FILLER.sub("", raw).strip()


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
    return (matched.group(1).strip() if matched else raw)


def who_is_mention(text: str) -> str:
    raw = _people_raw(text)
    matched = _WHO_IS_NL.match(raw)
    return (matched.group(1).strip() if matched else raw)


def person_note_body(text: str) -> str:
    raw = _people_raw(text)
    matched = _NOTE_FOR_NL.match(raw)
    return (matched.group(1).strip() if matched else raw)


def alias_set_body(text: str) -> str:
    raw = _people_raw(text)
    matched = _ALIAS_SET_NL.match(raw)
    return (matched.group(1).strip() if matched else raw)


def birthday_set_body(text: str) -> str:
    raw = _people_raw(text)
    matched = _BIRTHDAY_SET_NL.match(raw)
    return (matched.group(1).strip() if matched else raw)


def is_gym_end_utterance(text: str) -> bool:
    """Structural gym-end NL — does not steal habit `done:` / due `done:`."""
    raw = (text or "").strip()
    raw = _LEADING_FILLER.sub("", raw).strip()
    if not raw or gym_read_takes_priority(raw):
        return False
    lower = raw.lower()
    if lower.startswith("done:") or lower.startswith("habit "):
        return False
    return bool(_GYM_END_SHAPE.match(raw))


def is_lift_log_utterance(text: str) -> bool:
    """Structural lift capture — independent of pack_hint match."""
    raw = (text or "").strip()
    raw = _LEADING_FILLER.sub("", raw).strip()
    if not raw or gym_read_takes_priority(raw):
        return False
    if _LIFT_PREFIX.match(raw):
        return True
    if _LIFT_LINE.search(raw) or _LIFT_LADDER.search(raw) or _LIFT_SETS_AT_LOAD.search(raw):
        return True
    return False


def _is_complete_lift_shape(body: str) -> bool:
    return bool(
        _LIFT_LINE.search(body)
        or _LIFT_LADDER.search(body)
        or _LIFT_SETS_AT_LOAD.search(body)
    )


def is_incomplete_lift_utterance(text: str) -> bool:
    """Miss-path lift: ask, no session, no row. Not a write. Not gym_start.

    Matches bare ``60x6`` / ``3x6`` (no kg/lb) and name-only catalog/custom
    folds. Does not steal gym reads, start/end, complete kg×reps, or chat
    that is not an exercise bind (``I like bench``).
    """
    raw = (text or "").strip()
    raw = _LEADING_FILLER.sub("", raw).strip()
    if not raw or gym_read_takes_priority(raw):
        return False
    if is_gym_start_utterance(raw) or is_gym_end_utterance(raw):
        return False
    body = lift_utterance_body(raw)
    if not body:
        return False
    if _is_complete_lift_shape(body):
        return False
    if is_bare_nxm_without_unit(body):
        return True
    if _NAME_ONLY_CHAT.match(body):
        return False
    if not _NAME_ONLY_LIFT.match(body):
        return False
    from ada.logs.gym import exercise_name_known

    return exercise_name_known(body)


def lift_log_fast_path_args(text: str) -> dict[str, Any] | None:
    """Return {utterance} for build_lift_log_args, or None."""
    raw = (text or "").strip()
    raw = _LEADING_FILLER.sub("", raw).strip()
    if not raw or not is_lift_log_utterance(raw):
        return None
    lower = raw.lower()
    if lower.startswith("log lift:") or lower.startswith("lift:"):
        body = raw.split(":", 1)[1].strip() if ":" in raw else raw
        return {"utterance": body or raw}
    return {"utterance": raw}


def _normalize_meal_slot(raw_slot: str) -> str:
    slot = (raw_slot or "").strip().lower()
    if slot == "snacks":
        return "snack"
    return slot


def is_meal_log_utterance(text: str) -> bool:
    """Structural meal capture — independent of pack_hint match."""
    raw = (text or "").strip()
    raw = _LEADING_FILLER.sub("", raw).strip()
    if not raw:
        return False
    if _ADD_MEAL.match(raw):
        return True
    if _MEAL_SINGLE.match(raw):
        return True
    if _MEAL_MULTI.search(raw) or _MEAL_MULTI_BARE.search(raw):
        return True
    return False


def meal_log_fast_path_args(text: str) -> dict[str, Any] | None:
    """Return {utterance, meal_slot} for build_meal_log_args, or None."""
    raw = (text or "").strip()
    raw = _LEADING_FILLER.sub("", raw).strip()
    if not raw:
        return None

    meal = _ADD_MEAL.match(raw)
    if meal:
        slot_raw = meal.group(2)
        body = _meal_body_from_raw(raw, slot=slot_raw)
        return {
            "utterance": body or meal.group(1).strip(),
            "meal_slot": _normalize_meal_slot(slot_raw),
        }

    meal_single = _MEAL_SINGLE.match(raw)
    if meal_single:
        return {
            "utterance": meal_single.group(1).strip(),
            "meal_slot": None,
        }

    if _MEAL_MULTI.search(raw) or _MEAL_MULTI_BARE.search(raw):
        slot_m = _MEAL_SLOT.search(raw)
        slot = _normalize_meal_slot(slot_m.group(1)) if slot_m else None
        body = _meal_body_from_raw(raw, slot=slot_m.group(1) if slot_m else None)
        return {"utterance": body, "meal_slot": slot}

    return None


def _meal_body_from_raw(raw: str, *, slot: str | None = None) -> str:
    """Strip log/add prefix and trailing meal-slot clause from meal NL."""
    body = raw
    for prefix in ("log meal:", "long meal:", "log meal", "long meal", "log ", "add ", "long "):
        if body.lower().startswith(prefix):
            body = body[len(prefix) :].strip()
            break
    if slot:
        body = re.sub(
            r"\s+(?:to|for)\s+(?:an?\s+|the\s+)?"
            + re.escape(slot)
            + r"s?\b.*$",
            "",
            body,
            flags=re.IGNORECASE,
        ).strip()
    return body


def route_utterance(text: str, *, config: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Map utterance prefix, YAML alias, or structural parser to tool + args hint."""
    raw = (text or "").strip()
    raw = _LEADING_FILLER.sub("", raw).strip()
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
    from ada.harness.meal_draft_spine import is_meal_draft_start

    if is_meal_draft_start(raw):
        return _route_from_pack("meal_draft_start", raw, raw, config=cfg)

    if lower.startswith("start focus") or lower.startswith("start timer"):
        mapped = map_time_intent(raw)
        pack = resolve_pack("time_start", config=cfg) or {}
        return {
            "verb": "time_start",
            "tool": "life_time_start",
            "args": mapped,
            "preferred_tools": list(pack.get("preferred_tools") or []),
            "spine": pack.get("spine"),
        }

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
