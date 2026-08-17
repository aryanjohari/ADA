"""Deterministic utterance -> meal_log lines helper (M19a P0.1)."""

from __future__ import annotations

import json
import re
from typing import Any

from ada.logs import food as food_mod

_SPLIT = re.compile(r"\s+(?:and|\+)\s+|,\s*")
_MEAL_SLOT_TAIL = re.compile(
    r"\s+(?:to|for)\s+(breakfast|lunch|dinner|snack)\b.*$",
    re.IGNORECASE,
)
_STOPWORDS = {
    "a",
    "an",
    "the",
    "my",
    "for",
    "with",
    "to",
    "of",
}
_NUMBER_WORDS = {
    "a": 1.0,
    "an": 1.0,
    "one": 1.0,
    "two": 2.0,
    "three": 3.0,
}
_DEFAULT_SERVING_G = {
    "banana": 118.0,
    "milk": 240.0,
    "coffee": 240.0,
    "nescafe": 2.0,
}


def _parse_piece(part: str) -> tuple[str, float, str, float | None]:
    text = (part or "").strip()
    if not text:
        return "", 1.0, "serving", None
    words = text.split()
    qty = 1.0
    unit = "serving"
    i = 0
    if words:
        first = words[0].lower()
        if first in _NUMBER_WORDS:
            qty = _NUMBER_WORDS[first]
            i = 1
        else:
            try:
                qty = float(first)
                i = 1
            except ValueError:
                pass
    if i < len(words) and words[i].lower() in {"g", "gram", "grams", "ml"}:
        unit = "g" if words[i].lower().startswith("g") else "ml"
        i += 1
    elif i < len(words) and words[i].lower() in {"piece", "pieces", "banana", "bananas"}:
        unit = "piece"
        if words[i].lower() in {"banana", "bananas"}:
            i -= 0
        else:
            i += 1
    while i < len(words) and words[i].lower() in {"small", "medium", "large"}:
        i += 1
    query_tokens = [w for w in words[i:] if w.lower() not in _STOPWORDS]
    query = " ".join(query_tokens).strip()
    serving_grams = None
    if unit == "g":
        serving_grams = qty
    elif unit == "ml":
        serving_grams = qty
    else:
        for key, grams in _DEFAULT_SERVING_G.items():
            if key in query.lower():
                serving_grams = qty * grams
                break
    return query or text, qty, unit, serving_grams


def _scale_nutrients(per_100g: dict[str, Any], grams: float | None) -> dict[str, float | None]:
    nutrients: dict[str, float | None] = {}
    factor = (grams / 100.0) if grams not in (None, 0) else 1.0
    for key, value in per_100g.items():
        if value is None:
            nutrients[key] = None
            continue
        try:
            nutrients[key] = round(float(value) * factor, 3)
        except (TypeError, ValueError):
            nutrients[key] = None
    return nutrients


def _strip_meal_slot_words(utterance: str, meal_slot: str | None = None) -> str:
    """Drop trailing 'for/to breakfast' so search is the food, not the slot."""
    text = (utterance or "").strip()
    text = _MEAL_SLOT_TAIL.sub("", text)
    if meal_slot:
        text = re.sub(
            rf"\b(?:to|for)\s+{re.escape(str(meal_slot))}\b",
            " ",
            text,
            flags=re.IGNORECASE,
        )
    return re.sub(r"\s+", " ", text).strip()


def build_meal_log_args(
    utterance: str,
    *,
    meal_slot: str | None = None,
    fetch_remote: bool = True,
) -> dict[str, Any]:
    cleaned = _strip_meal_slot_words(utterance, meal_slot)
    parts = [p.strip() for p in _SPLIT.split(cleaned) if p.strip()]
    lines: list[dict[str, Any]] = []
    misses: list[dict[str, Any]] = []
    searches: list[dict[str, Any]] = []
    for part in parts:
        query, qty, unit, serving_grams = _parse_piece(part)
        candidates = food_mod.search_foods_resolved(
            query, limit=5, fetch_remote=fetch_remote
        )
        searches.append({"query": query, "count": len(candidates)})
        if not candidates:
            misses.append({"query": query, "reason": "food_search_miss"})
            continue
        ref_id = str(candidates[0].get("ref_id") or candidates[0].get("food_ref_id") or "")
        row = food_mod.get_food(ref_id)
        if not row:
            misses.append({"query": query, "reason": "food_ref_missing"})
            continue
        per_100g = json.loads(row.get("nutrients_per_100g_json") or "{}")
        nutrients = _scale_nutrients(per_100g, serving_grams)
        provider = str(row.get("source") or "manual")
        snapshot = {
            "schema_version": 1,
            "nutrients": nutrients,
            "source": {
                "provider": provider,
                "external_id": row.get("external_id"),
                "fetched_at": row.get("imported_at"),
            },
        }
        lines.append(
            {
                "display_name": row.get("name") or query,
                "ref_id": row.get("food_ref_id"),
                "serving_qty": qty,
                "serving_unit": unit,
                "serving_grams": serving_grams,
                "provenance": "api" if provider == "usda_fdc" else provider,
                "snapshot_json": snapshot,
                "nutrients": nutrients,
            }
        )
    return {
        "ok": bool(lines),
        "meal_slot": meal_slot,
        "lines": lines,
        "misses": misses,
        "searches": searches,
        "utterance": utterance,
    }
