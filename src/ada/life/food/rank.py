"""M27 unified catalog ranking policy — food now, gym stub later."""

from __future__ import annotations

import re
from typing import Any, Literal

from ada.harness.resolve_gate import (
    brand_vs_query_fight,
    candidate_matches_query,
    candidate_preview,
    macros_all_null,
    normalize_query,
)

_TOKEN = re.compile(r"[a-z0-9]+")
_MACRO_IDS = ("energy_kcal", "protein_g", "fat_g", "carb_g")
_SCORE_HIGH = 0.85
_SCORE_MANY = 0.5

# Processed / variant-form markers — demote when query asks for plain cooked protein/grain.
_FORM_MARKERS = frozenset(
    {
        "breaded",
        "tender",
        "tenders",
        "fried",
        "microwaved",
        "nugget",
        "nuggets",
        "strip",
        "strips",
        "skin",
        "braised",
        "candied",
        "glutinous",
    }
)


def _tokens(text: str) -> set[str]:
    return set(_TOKEN.findall((text or "").lower()))


def _candidate_macros(candidate: dict[str, Any]) -> dict[str, Any]:
    nutrients = candidate.get("nutrients")
    if isinstance(nutrients, dict):
        return nutrients
    raw = candidate.get("nutrients_per_100g")
    if isinstance(raw, dict):
        return raw
    return {}


def _macro_float(nutrients: dict[str, Any], key: str) -> float | None:
    val = nutrients.get(key)
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _is_branded_food(row: dict[str, Any]) -> bool:
    return bool(str(row.get("brand") or "").strip())


def _ice_cream_demote(row: dict[str, Any]) -> int:
    """Demote ice-cream brands for generic queries (Gott COFFEE)."""
    hay = f"{row.get('name') or ''} {row.get('brand') or ''}".lower()
    if "ice cream" in hay or "icecream" in hay:
        return 1
    return 0


def _dry_when_cooked_demote(query: str, candidate: dict[str, Any]) -> int:
    """Query asks cooked/boiled — demote dry/raw rows when query omits those words."""
    q = (query or "").lower()
    cooked_cues = ("cooked", "boiled", "steamed", "roasted", "baked", "poached")
    if not any(w in q for w in cooked_cues):
        return 0
    name = str(candidate.get("name") or candidate.get("label") or "").lower()
    if "dry" in q or "raw" in q:
        return 0
    if "dry" in name or ", raw" in name or name.endswith(" raw"):
        return 1
    return 0


def _null_macro_tier(candidate: dict[str, Any]) -> int:
    """Branded null-CORE demoted below generic null-CORE and macro rows."""
    if not macros_all_null(candidate):
        return 0
    if _is_branded_food(candidate):
        return 2
    return 1


def foundation_boost(row: dict[str, Any]) -> int:
    """Prefer Foundation / SR Legacy / raw-generic over branded."""
    name = str(row.get("name") or "").lower()
    source = str(row.get("source") or "").lower()
    data_type = str(row.get("data_type") or "").lower()
    if "foundation" in data_type or "sr legacy" in data_type:
        return 0
    if source == "usda_fdc" and (", raw" in name or name.endswith(" raw")):
        return 0
    if _is_branded_food(row):
        return 2
    return 1


def catalog_form_mismatch(
    query: str,
    candidate: dict[str, Any],
    *,
    domain: Literal["food", "gym"] = "food",
) -> bool:
    """True when candidate form/equipment diverges from query-implied plain intent."""
    if domain != "food":
        return False
    q_toks = _tokens(query)
    name = str(candidate.get("name") or candidate.get("label") or "")
    name_toks = _tokens(name)
    mismatch = _FORM_MARKERS - q_toks
    if not mismatch:
        return False
    return bool(name_toks & mismatch)


def macro_implausible(query: str, candidate: dict[str, Any]) -> bool:
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


def _food_search_extras(candidate: dict[str, Any]) -> tuple[int, int]:
    """Thin-custom and null-CORE demotion for search_foods_resolved."""
    from ada.logs.food import is_null_core_food, is_thin_custom_food

    return (
        1 if is_thin_custom_food(candidate) else 0,
        1 if is_null_core_food(candidate) else 0,
    )


def _candidate_sort_key(
    query: str,
    candidate: dict[str, Any],
    *,
    domain: Literal["food", "gym"],
    index: int,
    for_search: bool = False,
) -> tuple[Any, ...]:
    """Ordered sort layers from M27 §7."""
    if domain != "food":
        return (-float(candidate.get("score") or 0), index)

    extras = _food_search_extras(candidate) if for_search else (0, 0)
    return (
        0 if candidate_matches_query(query, candidate) else 1,
        extras[0],
        extras[1],
        _ice_cream_demote(candidate),
        _dry_when_cooked_demote(query, candidate),
        1 if catalog_form_mismatch(query, candidate, domain="food") else 0,
        1 if macro_implausible(query, candidate) else 0,
        foundation_boost(candidate),
        _null_macro_tier(candidate),
        -float(candidate.get("score") or 0),
        index,
    )


def _hoist_favorite(
    candidates: list[dict[str, Any]],
    favorite: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    fav_ref = str((favorite or {}).get("ref_id") or "").strip() if favorite else ""
    if not fav_ref:
        return candidates
    for i, c in enumerate(candidates):
        rid = str(c.get("ref_id") or c.get("food_ref_id") or "")
        if rid == fav_ref:
            return [c] + [x for x in candidates if x is not c]
    return candidates


def rank_catalog_candidates(
    query: str,
    candidates: list[dict[str, Any]],
    *,
    domain: Literal["food", "gym"] = "food",
    favorite: dict[str, Any] | None = None,
    for_search: bool = False,
) -> list[dict[str, Any]]:
    """Score and sort catalog candidates through the unified M27 pipeline."""
    if not candidates:
        return []
    indexed = list(enumerate(candidates))
    sorted_pairs = sorted(
        indexed,
        key=lambda ic: _candidate_sort_key(
            query, ic[1], domain=domain, index=ic[0], for_search=for_search
        ),
    )
    ranked = [c for _, c in sorted_pairs]
    return _hoist_favorite(ranked, favorite)


def _is_viable_food_candidate(query: str, candidate: dict[str, Any]) -> bool:
    if macros_all_null(candidate):
        return False
    if brand_vs_query_fight(query, candidate):
        return False
    if macro_implausible(query, candidate):
        return False
    if not candidate_matches_query(query, candidate):
        return False
    if catalog_form_mismatch(query, candidate, domain="food"):
        return False
    return True


def has_viable_local_candidate(
    query: str,
    candidates: list[dict[str, Any]],
    *,
    domain: Literal["food", "gym"] = "food",
) -> bool:
    """True when pool has a viable local hit — skip remote fetch."""
    if domain != "food":
        return bool(candidates)
    ranked = rank_catalog_candidates(query, candidates, domain="food")
    return any(_is_viable_food_candidate(query, c) for c in ranked)


def rank_catalog_bind(
    query: str,
    candidates: list[dict[str, Any]],
    *,
    domain: Literal["food", "gym"] = "food",
    favorite: dict[str, Any] | None = None,
    score_high: float = _SCORE_HIGH,
    score_many: float = _SCORE_MANY,
) -> dict[str, Any]:
    """Decide silent bind vs needs_confirm for one catalog resolve."""
    if domain == "gym":
        raise NotImplementedError("gym catalog bind not implemented in M27 Step 2")

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

    name_matched = [c for c in candidates if candidate_matches_query(query, c)]
    pool_in = name_matched if name_matched else []
    if not pool_in:
        return {
            "ok": False,
            "needs_confirm": False,
            "reason": "no_name_match",
            "reasons": ["no_name_match"],
            "query": query,
            "query_norm": q_norm,
            "candidates": previews,
            "bind": None,
            "proposed_ref_id": None,
        }

    scored = rank_catalog_candidates(query, pool_in, domain="food", favorite=favorite)

    # Propose-pool rule: honest null-CORE may stay in the ranked list for
    # visibility, but never become proposed_ref_id when any macro-complete
    # candidate exists (Confirm Yes must not hand off a null bind).
    # Form rule (M26 v1.11 / 1c509c18…): never propose breaded/tenders/etc.
    # when a form-matched plain candidate exists.
    form_ok = [
        c for c in scored if not catalog_form_mismatch(query, c, domain="food")
    ]
    if form_ok:
        scored_for_propose = form_ok
    else:
        scored_for_propose = scored
        reasons.append("form_mismatch")

    viable = [c for c in scored_for_propose if not macros_all_null(c)]
    propose_pool = viable if viable else scored_for_propose
    top = propose_pool[0]
    if viable and (macros_all_null(top) or macros_all_null(scored_for_propose[0])):
        reasons.append("empty_macros_skipped")
        top = viable[0]

    top_score = float(top.get("score") or 0)
    above = [c for c in scored_for_propose if float(c.get("score") or 0) >= score_many]
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
    fav_ref = str((favorite or {}).get("ref_id") or "").strip() if favorite else ""
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
