"""Verb/chip → life tool routing (M19a)."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path
import re
from typing import Any

import yaml

from ada.harness.nutrition_date import (
    has_week_cue,
    is_nutrition_read_shape,
    local_today,
    parse_nutrition_date,
)
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
# Phone NL: "Habit done skincare" (no colon) — still pack-route, not prose Confirm.
_HABIT_DONE_NL = re.compile(
    r"^(?:habit\s+)?(?:done|tick|logged)\s+:?\s*(.+)$",
    re.IGNORECASE,
)
_HABIT_MISS_NL = re.compile(
    r"^(?:habit\s+)?miss(?:ed)?\s+:?\s*(.+)$",
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
        "due_list",
        "gym_status",
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
            return _route_from_pack(verb, raw, raw, config=config)
    return None


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
        return {
            "utterance": meal.group(1).strip(),
            "meal_slot": _normalize_meal_slot(meal.group(2)),
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

    nutrition = _route_nutrition_read(raw, config=cfg)
    if nutrition is not None:
        return nutrition

    aliased = _route_aliases(raw, lower, config=cfg)
    if aliased is not None:
        return aliased

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

    # Habit NL before bare due — require "habit" / tick cue (not "done: thesis").
    habit_done = _HABIT_DONE_NL.match(raw)
    if habit_done and (
        lower.startswith("habit ")
        or lower.startswith("habit\t")
        or lower.startswith("tick ")
        or "habit done" in lower
        or "habit tick" in lower
    ):
        body = habit_done.group(1).strip()
        if body:
            return _route_from_pack("habit_do", raw, body, config=cfg)

    habit_miss = _HABIT_MISS_NL.match(raw)
    if habit_miss and ("habit" in lower or lower.startswith("miss")):
        body = habit_miss.group(1).strip()
        if body:
            return _route_from_pack("habit_miss", raw, body, config=cfg)

    if _BRIEF_PREF_NL.search(raw):
        return _route_from_pack("brief_include", raw, raw, config=cfg)

    if lower.startswith("log lift:") or _LIFT_LINE.search(raw) or _LIFT_LADDER.search(raw):
        body = raw.split(":", 1)[1].strip() if ":" in raw else raw
        return _route_from_pack("lift_log", raw, body, config=cfg)

    return None
