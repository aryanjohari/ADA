"""Verb/chip → life tool routing (M19a)."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path
import re
from typing import Any

import yaml

from ada.harness.time_intent import map_time_intent

_DEFAULT_PACK = "life_p0.yaml"
_P1_PACK = "life_p1.yaml"
_MEAL_SLOT = re.compile(r"\b(?:to|for)\s+(breakfast|lunch|dinner|snack)\b", re.IGNORECASE)
_ADD_MEAL = re.compile(
    r"^(?:add|log)\s+(.+?)\s+(?:to|for)\s+(breakfast|lunch|dinner|snack)\b",
    re.IGNORECASE,
)
_LIFT_LINE = re.compile(r"\b(?:\d+(?:\.\d+)?)\s*(?:kg|kgs|lb|lbs)\s*x\s*\d+\b", re.IGNORECASE)

READ_PACK_VERBS = frozenset(
    {
        "nutrition_day",
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
            args["meal_slot"] = slot.group(1).lower()
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


def _route_aliases(
    raw: str,
    lower: str,
    *,
    config: dict[str, Any],
) -> dict[str, Any] | None:
    for alias in config.get("aliases") or []:
        if not isinstance(alias, dict):
            continue
        pattern = str(alias.get("pattern") or "").strip().lower()
        verb = str(alias.get("verb") or "").strip()
        if pattern and verb and pattern in lower:
            return _route_from_pack(verb, raw, raw, config=config)
    return None


def route_utterance(text: str, *, config: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Map utterance prefix, YAML alias, or structural parser to tool + args hint."""
    raw = (text or "").strip()
    lower = raw.lower()
    cfg = config or load_pack_config()
    packs = cfg.get("packs") or {}

    for verb, entry in packs.items():
        prefill = (entry.get("prefill") or "").lower()
        if prefill and lower.startswith(prefill):
            body = raw[len(prefill) :].strip()
            return _route_from_pack(verb, raw, body, config=cfg)

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
            routed["args"]["meal_slot"] = meal.group(2).lower()
        return routed

    if lower.startswith("log lift:") or _LIFT_LINE.search(raw):
        body = raw.split(":", 1)[1].strip() if ":" in raw else raw
        return _route_from_pack("lift_log", raw, body, config=cfg)

    return None
