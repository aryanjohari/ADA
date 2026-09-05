"""Shared life-write resolve gate (M21/M22/M24/M27) — candidates in, bind / needs_confirm out.

Code owns id bind. Cortex may parse slots; never silently pick candidates[0].

M27 Step 2: food ranking policy lives in catalog_rank.py; this module keeps
backward-compatible wrappers and shared stem / brand / macro helpers.
"""

from __future__ import annotations

import re
from typing import Any

_TOKEN = re.compile(r"[a-z0-9]+")
_MACRO_IDS = ("energy_kcal", "protein_g", "fat_g", "carb_g")
_SCORE_HIGH = 0.85
_SCORE_MANY = 0.5
# Prep/cook/size words — not primary food nouns for name-match gate.
_MATCH_STOP = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "of",
        "for",
        "with",
        "to",
        "cup",
        "cups",
        "whole",
        "cooked",
        "raw",
        "boiled",
        "poached",
        "large",
        "small",
        "medium",
        "hard",
        "soft",
        "fresh",
        "frozen",
        "fried",
        "scrambled",
    }
)
# Color/cut modifiers — never sole-bind without the head noun (white rice, salmon fillet).
_FOOD_MODIFIER_STOP = frozenset(
    {
        "white",
        "brown",
        "black",
        "red",
        "yellow",
        "fillet",
        "fillets",
        "boneless",
        "skinless",
        "lean",
        "extra",
        "light",
        "dark",
        "sweet",
        "hot",
        "cold",
    }
)
# Protected bigrams — color/cut modifiers stay in stem set (black gram, brown rice).
_COMPOUND_HEADS = frozenset(
    {
        ("black", "gram"),
        ("brown", "rice"),
        ("white", "rice"),
        ("red", "lentil"),
        ("kidney", "bean"),
        ("black", "bean"),
    }
)


def normalize_query(query: str) -> str:
    """Normalize food/habit query keys for favorites lookup."""
    return re.sub(r"\s+", " ", (query or "").strip().lower())


def _tokens(text: str) -> set[str]:
    return set(_TOKEN.findall((text or "").lower()))


def _stem_token(token: str) -> str:
    t = (token or "").lower()
    if len(t) > 3 and t.endswith("s") and not t.endswith("ss"):
        return t[:-1]
    return t


def extract_food_stems(query: str) -> set[str]:
    """Head-noun stems from slot query — modifiers stripped, not qty/meal-slot."""
    tokens = _TOKEN.findall((query or "").lower())
    stems: set[str] = set()
    i = 0
    while i < len(tokens):
        if i + 1 < len(tokens) and (tokens[i], tokens[i + 1]) in _COMPOUND_HEADS:
            stems.add(f"{tokens[i]}_{tokens[i + 1]}")
            stems.add(_stem_token(tokens[i]))
            stems.add(_stem_token(tokens[i + 1]))
            i += 2
            continue
        t = tokens[i]
        if len(t) <= 1 or t in _MATCH_STOP or t in _FOOD_MODIFIER_STOP:
            i += 1
            continue
        stems.add(_stem_token(t))
        i += 1
    return stems


def _stems_satisfied(q_stems: set[str], name_stems: set[str]) -> bool:
    for stem in q_stems:
        if stem in name_stems:
            continue
        if "_" in stem:
            left, right = stem.split("_", 1)
            if left in name_stems and right in name_stems:
                continue
        return False
    return True


def candidate_matches_query(query: str, candidate: dict[str, Any]) -> bool:
    """True when every non-modifier food stem from the query appears in candidate name."""
    q_stems = extract_food_stems(query)
    if not q_stems:
        return True
    name = str(
        candidate.get("name")
        or candidate.get("label")
        or candidate.get("display_name")
        or ""
    )
    name_tokens = _TOKEN.findall(name.lower())
    name_stems = {_stem_token(t) for t in name_tokens}
    for j in range(len(name_tokens) - 1):
        pair = (name_tokens[j], name_tokens[j + 1])
        if pair in _COMPOUND_HEADS:
            name_stems.add(f"{pair[0]}_{pair[1]}")
            name_stems.add(_stem_token(pair[0]))
            name_stems.add(_stem_token(pair[1]))
    return _stems_satisfied(q_stems, name_stems)


def brand_vs_query_fight(query: str, candidate: dict[str, Any]) -> bool:
    """True when a branded row matches the query name but brand diverges (Gott Ice Cream COFFEE)."""
    q = _tokens(query)
    if not q:
        return False
    brand = str(candidate.get("brand") or "").strip()
    if not brand:
        return False
    name = str(candidate.get("name") or candidate.get("label") or "")
    name_toks = _tokens(name)
    brand_toks = _tokens(brand)
    # Brand mentions the query (e.g. "Coffee Brand Co") — not a fight.
    if q & brand_toks:
        return False
    # Query tokens hit the name while brand is unrelated.
    if q <= name_toks or name_toks <= q or bool(q & name_toks):
        return True
    return False


def _candidate_macros(candidate: dict[str, Any]) -> dict[str, Any]:
    nutrients = candidate.get("nutrients")
    if isinstance(nutrients, dict):
        return nutrients
    raw = candidate.get("nutrients_per_100g")
    if isinstance(raw, dict):
        return raw
    return {}


def macros_all_null(candidate: dict[str, Any]) -> bool:
    """True when energy/protein/fat/carb are all null — do not silent-bind."""
    n = _candidate_macros(candidate)
    return all(n.get(k) is None for k in _MACRO_IDS)


def processed_food_mismatch(query: str, candidate: dict[str, Any]) -> bool:
    """True when candidate form diverges from query-implied plain intent (M27 wrapper)."""
    from ada.harness.catalog_rank import catalog_form_mismatch

    return catalog_form_mismatch(query, candidate, domain="food")


def implausible_branded_junk(query: str, candidate: dict[str, Any]) -> bool:
    """Branded row with candy-like macros for a generic whole-food query (M27 wrapper)."""
    from ada.harness.catalog_rank import macro_implausible

    return macro_implausible(query, candidate)


def has_viable_local_candidate(query: str, candidates: list[dict[str, Any]]) -> bool:
    """True when pool has a non-null, non-junk, non-form-mismatch match."""
    from ada.harness.catalog_rank import has_viable_local_candidate as _has_viable

    return _has_viable(query, candidates, domain="food")


def candidate_preview(candidate: dict[str, Any], *, query: str | None = None) -> dict[str, Any]:
    """Gateway-visible candidate row (label, brand, kcal, ref_id, fight).

    Includes per-100g ``nutrients`` when present so Confirm→write can rehydrate
    the meal line if ``food_reference.db`` is thin/null for the same ref.
    """
    nutrients = _candidate_macros(candidate)
    kcal = nutrients.get("energy_kcal")
    ref_id = str(
        candidate.get("ref_id")
        or candidate.get("food_ref_id")
        or candidate.get("person_id")
        or candidate.get("id")
        or ""
    )
    label = str(
        candidate.get("label")
        or candidate.get("name")
        or candidate.get("display_name")
        or ref_id
    )
    row: dict[str, Any] = {
        "ref_id": ref_id,
        "label": label,
        "brand": candidate.get("brand"),
        "score": candidate.get("score"),
        "kcal_per_100g": kcal,
        "source": candidate.get("source"),
        "macros_empty": macros_all_null(candidate),
    }
    if nutrients:
        # Per-100g CORE — Confirm scales by serving_grams at write time.
        row["nutrients"] = {k: nutrients.get(k) for k in _MACRO_IDS}
    if query is not None:
        row["brand_fight"] = brand_vs_query_fight(query, candidate)
    return row


def decide_food_bind(
    *,
    query: str,
    candidates: list[dict[str, Any]],
    favorite: dict[str, Any] | None = None,
    score_high: float = _SCORE_HIGH,
    score_many: float = _SCORE_MANY,
) -> dict[str, Any]:
    """Decide silent bind vs needs_confirm for one food resolve (M27 wrapper)."""
    from ada.harness.catalog_rank import rank_catalog_bind

    return rank_catalog_bind(
        query,
        candidates,
        domain="food",
        favorite=favorite,
        score_high=score_high,
        score_many=score_many,
    )


def _habit_candidate(habit: dict[str, Any]) -> dict[str, Any]:
    hid = str(habit.get("habit_id") or "")
    label = str(habit.get("display_name") or hid)
    return {
        "ref_id": hid,
        "habit_id": hid,
        "label": label,
        "display_name": label,
    }


def decide_habit_bind(*, query: str, matches: list[dict[str, Any]]) -> dict[str, Any]:
    """Many habit matches → Confirm candidates; unique → bind id."""
    _ = query  # reserved for future rank / preview
    cands = [_habit_candidate(m) for m in matches if isinstance(m, dict)]
    if len(cands) <= 1:
        proposed = cands[0]["habit_id"] if cands else None
        return {
            "needs_confirm": False,
            "candidates": cands,
            "proposed_habit_id": proposed,
            "reasons": [],
        }
    return {
        "needs_confirm": True,
        "candidates": cands,
        "proposed_habit_id": cands[0]["habit_id"],
        "reasons": ["many"],
    }
