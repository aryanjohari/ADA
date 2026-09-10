"""Create-meal draft utterance spine (M26 library) — code binds ids, cortex asks."""

from __future__ import annotations

import re
from typing import Any, Callable

import httpx

from ada.harness.meal_spine import build_meal_log_args
from ada.logs import meal_draft as draft_mod
from ada.logs import nutrition_presets as presets_mod

_START = re.compile(
    r"^(?:ada[, ]+)?(?:please\s+)?"
    r"(?:add|create|start|begin|new)\s+(?:a\s+)?meal\b"
    r"|^(?:ada[, ]+)?meal\s+draft\b",
    re.I,
)
_CANCEL = re.compile(
    r"^(?:ada[, ]+)?(?:cancel(?:\s+meal)?|never\s+mind|forget\s+(?:it|the\s+meal)|abort(?:\s+meal)?)\s*$",
    re.I,
)
_DONE = re.compile(
    r"^(?:ada[, ]+)?(?:done|finish(?:ed)?|that's\s+(?:it|all)|save\s+this\s+meal)\s*$",
    re.I,
)
_SAVE_AS = re.compile(
    r"^(?:ada[, ]+)?"
    r"(?:save\s+(?:this\s+)?(?:as|as\s+my)\s+|make\s+this\s+(?:my\s+)?)"
    r"(.+?)\s*$",
    re.I,
)
_LOG_NOW = re.compile(
    r"^(?:ada[, ]+)?(?:log\s+it(?:\s+now)?|log\s+this\s+meal(?:\s+now)?)\s*$",
    re.I,
)
_LOG_PRESET = re.compile(
    r"^(?:ada[, ]+)?(?:log|add)\s+(?:my\s+)?(.+?)\s*$",
    re.I,
)
_BARCODE = re.compile(
    r"^(?:ada[, ]+)?(?:barcode|gtin|scan)\s*:?\s*(\d{8,14})\s*$"
    r"|^(?:ada[, ]+)?(\d{8,14})\s*$",
    re.I,
)
_ESTIMATE = re.compile(r"\bestimate\b|\(.*estimate.*\)", re.I)


def is_meal_draft_start(text: str) -> bool:
    return bool(_START.search((text or "").strip()))


def is_meal_draft_cancel(text: str) -> bool:
    return bool(_CANCEL.match((text or "").strip()))


def parse_save_as_name(text: str) -> str | None:
    m = _SAVE_AS.match((text or "").strip())
    if not m:
        return None
    return re.sub(r"\s+", " ", m.group(1).strip().rstrip("."))


def is_draft_done(text: str) -> bool:
    return bool(_DONE.match((text or "").strip()))


def is_draft_log_now(text: str) -> bool:
    return bool(_LOG_NOW.match((text or "").strip()))


def parse_barcode_gtin(text: str) -> str | None:
    m = _BARCODE.match((text or "").strip())
    if not m:
        return None
    return (m.group(1) or m.group(2) or "").strip() or None


def parse_log_preset_name(text: str) -> str | None:
    """Return preset name for 'log my breakfast' / 'log omelette breakfast'."""
    raw = (text or "").strip()
    if is_meal_draft_start(raw) or is_meal_draft_cancel(raw):
        return None
    if parse_barcode_gtin(raw):
        return None
    # Avoid stealing plain meal logs: "log 5 eggs", "log 100g chicken"
    if re.match(
        r"^(?:ada[, ]+)?(?:log|add)\s+\d",
        raw,
        re.I,
    ):
        return None
    if re.match(
        r"^(?:ada[, ]+)?(?:log|add)\s+(?:\d+(?:\.\d+)?\s*(?:g|grams?|kg))",
        raw,
        re.I,
    ):
        return None
    m = _LOG_PRESET.match(raw)
    if not m:
        return None
    name = re.sub(r"\s+", " ", m.group(1).strip().rstrip("."))
    # Strip leading "my "
    name = re.sub(r"^my\s+", "", name, flags=re.I).strip()
    if not name or name.lower() in {"meal", "food", "it", "this", "that"}:
        return None
    # Require "my" cue OR multi-word named dish (not bare "log eggs")
    if not re.search(r"\bmy\b", raw, re.I) and " " not in name and name.lower() in {
        "eggs",
        "coffee",
        "rice",
        "chicken",
        "salmon",
    }:
        return None
    if not re.search(r"\bmy\b", raw, re.I) and len(name.split()) < 2:
        # Single token without "my" → meal log, not preset
        return None
    return name


def wants_estimate(text: str) -> bool:
    return bool(_ESTIMATE.search(text or ""))


def build_draft_add_from_utterance(
    utterance: str,
    *,
    session_id: str,
    fetch_remote: bool = True,
    paths=None,
    http_get: Callable[..., httpx.Response] | None = None,
) -> dict[str, Any]:
    """Resolve one food utterance into a draft-add payload (Confirm when needed)."""
    estimate = wants_estimate(utterance)
    cleaned = re.sub(r"\s*\(.*estimate.*\)\s*", " ", utterance or "", flags=re.I)
    cleaned = re.sub(r"\bestimate\b", " ", cleaned, flags=re.I)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    built = build_meal_log_args(
        cleaned,
        fetch_remote=fetch_remote,
        paths=paths,
        http_get=http_get,
    )
    if not built.get("ok") or not built.get("lines"):
        return {
            "ok": False,
            "reason": (built.get("misses") or [{}])[0].get("reason")
            if built.get("misses")
            else "food_search_miss",
            "ask": built.get("ask")
            or "I couldn't bind that food. Try another name or a barcode.",
            "searches": built.get("searches") or [],
            "session_id": session_id,
        }
    lines = list(built["lines"])
    if estimate:
        for ln in lines:
            ln["provenance"] = "estimate"
    return {
        "ok": True,
        "session_id": session_id,
        "lines": lines,
        "resolve": built.get("resolve"),
        "needs_confirm": bool(built.get("needs_confirm")),
        "searches": built.get("searches") or [],
        "save_favorite": True,
        "estimate": estimate,
    }


def build_draft_save_args(
    session_id: str,
    *,
    name: str | None,
    confirmed: bool = False,
    paths=None,
) -> dict[str, Any]:
    draft = draft_mod.load_draft(session_id, paths=paths)
    if not draft:
        return {"ok": False, "reason": "no_open_draft", "ask": "No open meal draft."}
    lines = list(draft.get("lines") or [])
    if not lines:
        return {
            "ok": False,
            "reason": "draft_empty",
            "ask": "Add at least one food before saving.",
        }
    label = (name or draft.get("name") or "").strip()
    if not label:
        return {
            "ok": False,
            "reason": "name_required",
            "ask": draft_mod.ASK_NAME,
            "needs_name": True,
            "session_id": session_id,
        }
    components = []
    for ln in lines:
        components.append(
            {
                "ref_id": ln.get("ref_id"),
                "display_name": ln.get("display_name"),
                "serving_qty": ln.get("serving_qty", 1),
                "serving_unit": ln.get("serving_unit") or "serving",
                "serving_grams": ln.get("serving_grams"),
                "provenance": ln.get("provenance") or "custom",
                "nutrients": ln.get("nutrients"),
            }
        )
    mix = {str(c.get("provenance") or "custom") for c in components}
    provenance = "estimate" if "estimate" in mix else ("custom" if len(mix) == 1 else "custom")
    return {
        "ok": True,
        "session_id": session_id,
        "name": label,
        "components": components,
        "provenance": provenance,
        "confirmed": confirmed,
        "line_count": len(components),
    }


def expand_preset_log_args(
    name: str,
    *,
    meal_slot: str | None = None,
    paths=None,
) -> dict[str, Any]:
    expanded = presets_mod.expand_preset_lines(name, paths=paths)
    if not expanded.get("ok"):
        return expanded
    lines = expanded["lines"]
    # Always Confirm first log of a named preset unless every line has sticky ref
    # (policy: Confirm when any line unbound macros / no favorite — keep simple Confirm).
    return {
        "ok": True,
        "preset_id": expanded.get("preset_id"),
        "display_name": expanded.get("display_name"),
        "lines": lines,
        "meal_slot": meal_slot,
        "needs_confirm": True,
        "resolve": {
            "bind_authority": "meal_spine",
            "needs_confirm": True,
            "reasons": ["preset_log"],
            "rows": [
                {
                    "query": expanded.get("display_name") or name,
                    "query_norm": (expanded.get("preset_id") or name),
                    "reasons": ["preset_log"],
                    "proposed_ref_id": ln.get("ref_id"),
                    "candidates": [
                        {
                            "ref_id": ln.get("ref_id"),
                            "label": ln.get("display_name"),
                            "nutrients": ln.get("nutrients") or {},
                        }
                    ]
                    if ln.get("ref_id")
                    else [],
                }
                for ln in lines
            ],
        },
        "save_favorite": False,
    }
