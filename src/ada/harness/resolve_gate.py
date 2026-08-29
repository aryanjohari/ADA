"""Shared life-write resolve gate (M21/M22/M24) — candidates in, bind / needs_confirm out.

Code owns id bind. Cortex may parse slots; never silently pick candidates[0].
"""

from __future__ import annotations

import re
from typing import Any

_TOKEN = re.compile(r"[a-z0-9]+")
_SCORE_HIGH = 0.85
_SCORE_MANY = 0.5
_MACRO_IDS = ("energy_kcal", "protein_g", "fat_g", "carb_g")


def normalize_query(query: str) -> str:
    """Normalize food/habit query keys for favorites lookup."""
    return re.sub(r"\s+", " ", (query or "").strip().lower())


def _tokens(text: str) -> set[str]:
    return set(_TOKEN.findall((text or "").lower()))


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


def _macro_float(nutrients: dict[str, Any], key: str) -> float | None:
    val = nutrients.get(key)
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def implausible_branded_junk(query: str, candidate: dict[str, Any]) -> bool:
    """Branded row with candy-like macros for a generic whole-food query (Mars EGGS)."""
    if not str(candidate.get("brand") or "").strip():
        return False
    q = normalize_query(query)
    nutrients = _candidate_macros(candidate)
    carb = _macro_float(nutrients, "carb_g")
    protein = _macro_float(nutrients, "protein_g")
    kcal = _macro_float(nutrients, "energy_kcal")
    if "egg" in q:
        if carb is not None and carb > 30:
            return True
        if kcal is not None and kcal > 400:
            return True
        if (
            protein is not None
            and protein < 5
            and carb is not None
            and carb > 15
        ):
            return True
    return False


def has_viable_local_candidate(query: str, candidates: list[dict[str, Any]]) -> bool:
    """True when pool has a non-null, non-junk candidate matching the slot query."""
    for cand in candidates:
        if macros_all_null(cand):
            continue
        if brand_vs_query_fight(query, cand):
            continue
        if implausible_branded_junk(query, cand):
            continue
        name = str(cand.get("name") or cand.get("label") or "")
        q_stems = {
            t[:-1] if len(t) > 3 and t.endswith("s") and not t.endswith("ss") else t
            for t in _tokens(query)
            if len(t) > 1
        }
        name_stems = {
            t[:-1] if len(t) > 3 and t.endswith("s") and not t.endswith("ss") else t
            for t in _tokens(name)
        }
        if q_stems and not q_stems <= name_stems:
            continue
        return True
    return False


def candidate_preview(candidate: dict[str, Any], *, query: str | None = None) -> dict[str, Any]:
    """Gateway-visible candidate row (label, brand, kcal, ref_id, fight)."""
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
    """Decide silent bind vs needs_confirm for one food resolve.

    Silent OK only when unique favorite hit + no brand fight + macros present.
    Never sole-pick candidates[0] on brand_fight / many / empty macros.
    """
    q_norm = normalize_query(query)
    previews = [candidate_preview(c, query=query) for c in candidates]
    reasons: list[str] = []

    if not candidates:
        return {
            "ok": False,
            "needs_confirm": False,
            "reason": "no_candidates",
            "reasons": ["no_candidates"],
            "query": query,
            "query_norm": q_norm,
            "candidates": [],
            "bind": None,
            "proposed_ref_id": None,
        }

    scored = sorted(
        enumerate(candidates),
        key=lambda ic: (
            1 if macros_all_null(ic[1]) else 0,
            -float(ic[1].get("score") or 0),
            ic[0],  # preserve search rank (Foundation/raw preference)
        ),
    )
    scored = [c for _, c in scored]

    fav_ref = str((favorite or {}).get("ref_id") or "").strip() if favorite else ""
    if fav_ref:
        for c in scored:
            rid = str(c.get("ref_id") or c.get("food_ref_id") or "")
            if rid == fav_ref:
                scored = [c] + [x for x in scored if x is not c]
                break

    viable = [c for c in scored if not macros_all_null(c)]
    propose_pool = viable if viable else scored
    top = propose_pool[0]
    if macros_all_null(scored[0]) and viable:
        reasons.append("empty_macros_skipped")
        top = viable[0]

    top_score = float(top.get("score") or 0)
    above = [c for c in scored if float(c.get("score") or 0) >= score_many]
    if len(above) > 1:
        reasons.append("many")

    if brand_vs_query_fight(query, top):
        reasons.append("brand_fight")

    second = propose_pool[1] if len(propose_pool) > 1 else None
    second_score = float(second.get("score") or 0) if second else None
    if top_score < score_high:
        reasons.append("low_score")
    elif (
        second is not None
        and second_score is not None
        and abs(top_score - second_score) < 0.05
        and second_score >= score_many
    ):
        if "many" not in reasons:
            reasons.append("tied_score")

    top_ref = str(top.get("ref_id") or top.get("food_ref_id") or "")
    favorite_hit = bool(fav_ref) and fav_ref == top_ref
    if not fav_ref:
        reasons.append("no_favorite")
    elif not favorite_hit:
        reasons.append("favorite_miss")

    if macros_all_null(top):
        reasons.append("empty_macros")

    silent_ok = (
        favorite_hit
        and "brand_fight" not in reasons
        and "favorite_miss" not in reasons
        and "empty_macros" not in reasons
    )

    bind_preview = candidate_preview(top, query=query)
    if silent_ok:
        return {
            "ok": True,
            "needs_confirm": False,
            "reason": "favorite_unique",
            "reasons": [],
            "query": query,
            "query_norm": q_norm,
            "candidates": previews,
            "bind": top,
            "bind_preview": bind_preview,
            "favorite": favorite,
            "proposed_ref_id": top_ref,
        }

    if not reasons:
        reasons.append("ambiguous")

    return {
        "ok": False,
        "needs_confirm": True,
        "reason": reasons[0],
        "reasons": reasons,
        "query": query,
        "query_norm": q_norm,
        "candidates": previews,
        "bind": top,
        "bind_preview": bind_preview,
        "favorite": favorite,
        "proposed_ref_id": top_ref,
    }


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
