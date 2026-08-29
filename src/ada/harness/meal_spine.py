"""Deterministic utterance -> meal_log lines helper (M19a P0.1 / M24 multi-slot / M25 recover)."""

from __future__ import annotations

import json
import re
import time
from typing import Any, Callable

import httpx

from ada.harness.resolve_gate import (
    brand_vs_query_fight,
    decide_food_bind,
    implausible_branded_junk,
    macros_all_null,
    normalize_query,
)
from ada.logs import favorites as favorites_mod
from ada.logs import food as food_mod

_SPLIT = re.compile(r"\s+(?:and|\+)\s+|,\s*")
_TOKEN = re.compile(r"[a-z0-9]+")
_MEAL_SLOT_TAIL = re.compile(
    r"\s+(?:to|for)\s+(breakfast|lunch|dinner|snack)\b.*$",
    re.IGNORECASE,
)
# Ignore cook/size words when checking candidate ↔ original query relevance.
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
_STOPWORDS = {
    "a",
    "an",
    "the",
    "my",
    "for",
    "with",
    "to",
    "of",
    "cup",
    "cups",
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
    "egg": 50.0,
    "eggs": 50.0,
}
_STRIPPED_MODIFIERS = frozenset({"small", "medium", "large", "boiled"})
_RECOVER_ROUNDS = 3
_RECOVER_SEARCHES = 5
_RECOVER_WALL_SEC = 8.0
_RECOVER_ASK = (
    "Couldn't pin down nutrition for that after a few tries — "
    "try a clearer name like egg, whole, cooked."
)


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
    while i < len(words) and words[i].lower() in _STRIPPED_MODIFIERS:
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


def _line_from_ref(
    *,
    query: str,
    ref_id: str,
    qty: float,
    unit: str,
    serving_grams: float | None,
    display_name: str | None = None,
    paths=None,
) -> dict[str, Any] | None:
    row = food_mod.get_food(ref_id, paths=paths)
    if not row:
        return None
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
    return {
        "display_name": display_name or row.get("name") or query,
        "ref_id": row.get("food_ref_id"),
        "serving_qty": qty,
        "serving_unit": unit,
        "serving_grams": serving_grams,
        "provenance": "api" if provider == "usda_fdc" else provider,
        "snapshot_json": snapshot,
        "nutrients": nutrients,
        "_query": query,
        "_query_norm": normalize_query(query),
    }


def _candidate_as_row(cand: dict[str, Any]) -> dict[str, Any]:
    """Normalize search hit so decide_food_bind / macros see nutrients."""
    out = dict(cand)
    if not isinstance(out.get("nutrients"), dict):
        raw = out.get("nutrients_per_100g")
        if isinstance(raw, dict):
            out["nutrients"] = raw
    return out


def _extract_stripped_modifiers(piece: str) -> list[str]:
    mods: list[str] = []
    for w in (piece or "").split():
        wl = w.lower()
        if wl in _STRIPPED_MODIFIERS and wl not in mods:
            mods.append(wl)
    return mods


def build_alt_queries(original_piece: str, parsed_query: str) -> list[str]:
    """Deterministic alt-query table for recover (M25 OPEN #1 OFF — no cortex assist)."""
    alts: list[str] = []
    seen: set[str] = set()
    base = (parsed_query or "").strip()
    parsed_lower = base.lower()

    def add(q: str) -> None:
        q = re.sub(r"\s+", " ", (q or "").strip())
        key = q.lower()
        if q and key not in seen and key != parsed_lower:
            seen.add(key)
            alts.append(q)

    base_tokens = set(parsed_lower.split())

    for mod in _extract_stripped_modifiers(original_piece):
        if mod in base_tokens or parsed_lower.startswith(f"{mod} "):
            continue
        add(f"{mod} {base}")
        if base.endswith("s") and len(base) > 1:
            add(f"{mod} {base[:-1]}")

    if base.endswith("s") and len(base) > 1:
        add(base[:-1])
    elif base and not base.endswith("s") and not base.endswith("e"):
        add(f"{base}s")

    if "egg" in parsed_lower:
        add("boiled egg")
        add("boiled eggs")
        add("egg, whole, cooked")
        add("egg, whole, raw")
        add("large egg")
        add("eggs, whole, cooked")
        add("egg, whole, cooked, hard-boiled")

    return alts


def _fdc_external_id(cand: dict[str, Any], *, paths=None) -> str | None:
    ext = cand.get("external_id")
    if ext:
        return str(ext)
    ref_id = str(cand.get("ref_id") or cand.get("food_ref_id") or "").strip()
    if not ref_id:
        return None
    row = food_mod.get_food(ref_id, paths=paths)
    if row and row.get("external_id"):
        return str(row["external_id"])
    return None


def _refresh_fdc_detail(
    cand: dict[str, Any],
    *,
    paths=None,
    http_get: Callable[..., httpx.Response] | None = None,
) -> dict[str, Any]:
    """Force detail fetch for FDC rows with null CORE; write honest cache (OPEN #4)."""
    row = _candidate_as_row(cand)
    if str(row.get("source") or "") != "usda_fdc" and not _fdc_external_id(row, paths=paths):
        return row
    if not macros_all_null(row):
        return row
    ext_id = _fdc_external_id(row, paths=paths)
    if not ext_id:
        return row
    detail = food_mod.fetch_usda_detail(ext_id, http_get=http_get)
    if not detail:
        return row
    nutrients = detail.get("nutrients_per_100g") or {}
    if macros_all_null({"nutrients": nutrients}):
        return row
    ref_id = str(row.get("ref_id") or row.get("food_ref_id") or "").strip()
    if ref_id:
        food_mod.update_food_nutrients(
            ref_id,
            nutrients_per_100g=nutrients,
            name=detail.get("name"),
            brand=detail.get("brand"),
            paths=paths,
        )
    else:
        inserted = food_mod.insert_food(
            name=detail["name"],
            source=detail["source"],
            external_id=detail.get("external_id"),
            brand=detail.get("brand"),
            nutrients_per_100g=nutrients,
            paths=paths,
        )
        ref_id = inserted["food_ref_id"]
    refreshed = dict(row)
    refreshed["ref_id"] = ref_id
    refreshed["name"] = detail.get("name") or row.get("name")
    refreshed["brand"] = detail.get("brand")
    refreshed["source"] = "usda_fdc"
    refreshed["nutrients"] = nutrients
    return refreshed


def _stem_token(token: str) -> str:
    t = (token or "").lower()
    if len(t) > 3 and t.endswith("s") and not t.endswith("ss"):
        return t[:-1]
    return t


def _filter_candidates(query: str, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop implausible branded junk before bind; keep null-CORE for detail refresh."""
    return [
        c
        for c in candidates
        if not implausible_branded_junk(query, c)
    ]


def _has_plausible_generic_candidate(
    query: str, candidates: list[dict[str, Any]]
) -> bool:
    for cand in candidates:
        row = _candidate_as_row(cand)
        if macros_all_null(row):
            continue
        if brand_vs_query_fight(query, row):
            continue
        if implausible_branded_junk(query, row):
            continue
        if candidate_matches_query(query, row):
            return True
    return False


def candidate_matches_query(query: str, candidate: dict[str, Any]) -> bool:
    """True when candidate name shares food stems with the original slot query.

    Blocks off-query recover binds (Banana, raw for eggs via shared 'raw').
    """
    q_stems = {
        _stem_token(t)
        for t in _TOKEN.findall((query or "").lower())
        if t not in _MATCH_STOP and len(t) > 1
    }
    if not q_stems:
        return True
    name = str(
        candidate.get("name")
        or candidate.get("label")
        or candidate.get("display_name")
        or ""
    )
    name_stems = {_stem_token(t) for t in _TOKEN.findall(name.lower())}
    # Every food stem from the slot query must appear in the candidate name.
    return q_stems <= name_stems


def _merge_candidate(
    pool: list[dict[str, Any]],
    cand: dict[str, Any],
    seen: set[str],
    *,
    query: str,
) -> None:
    row = _candidate_as_row(cand)
    ref_id = str(row.get("ref_id") or row.get("food_ref_id") or "").strip()
    if not ref_id or ref_id in seen or macros_all_null(row):
        return
    if implausible_branded_junk(query, row):
        return
    if not candidate_matches_query(query, row):
        return
    seen.add(ref_id)
    pool.append(row)


def _slot_from_decision(
    *,
    query: str,
    qty: float,
    unit: str,
    serving_grams: float | None,
    decision: dict[str, Any],
    paths=None,
) -> tuple[dict[str, Any] | None, bool, bool]:
    """Build meal line + (needs_confirm, recorded_resolve) from decide_food_bind output."""
    bind = decision.get("bind")
    if not bind:
        return None, False, False
    ref_id = str(
        decision.get("proposed_ref_id")
        or bind.get("ref_id")
        or bind.get("food_ref_id")
        or ""
    )
    if not ref_id:
        return None, False, False

    recorded_resolve = False
    slot_needs_confirm = bool(decision.get("needs_confirm"))
    if macros_all_null(bind):
        viable = [
            c
            for c in (decision.get("candidates") or [])
            if isinstance(c, dict) and not c.get("macros_empty")
        ]
        if not viable:
            return None, False, False
        slot_needs_confirm = True
        recorded_resolve = True
        ref_id = str(viable[0].get("ref_id") or ref_id)

    line = _line_from_ref(
        query=query,
        ref_id=ref_id,
        qty=qty,
        unit=unit,
        serving_grams=serving_grams,
        display_name=(decision.get("bind_preview") or {}).get("label"),
        paths=paths,
    )
    if not line:
        return None, False, False
    if macros_all_null({"nutrients": line.get("nutrients") or {}}):
        return None, False, False
    if decision.get("needs_confirm") and not recorded_resolve:
        slot_needs_confirm = True
    return line, slot_needs_confirm, recorded_resolve


def recover_food_slot(
    *,
    query: str,
    original_piece: str,
    qty: float,
    unit: str,
    serving_grams: float | None,
    miss_reason: str,
    initial_candidates: list[dict[str, Any]] | None = None,
    favorite: dict[str, Any] | None = None,
    fetch_remote: bool = True,
    paths=None,
    http_get: Callable[..., httpx.Response] | None = None,
) -> dict[str, Any]:
    """Bounded recover after empty_macros / food_search_miss (M25).

    Alt queries → search → detail refresh → drop null-CORE → decide_food_bind.
    Caps: 3 rounds · 5 searches · ~8s wall → human ask.
    """
    if miss_reason not in ("empty_macros", "food_search_miss", "brand_fight"):
        return {"ok": False, "reason": "not_recoverable"}

    start = time.monotonic()
    searches_done = 0
    recover_searches: list[dict[str, Any]] = []
    pool: list[dict[str, Any]] = []
    seen_refs: set[str] = set()

    for cand in initial_candidates or []:
        refreshed = _refresh_fdc_detail(cand, paths=paths, http_get=http_get)
        _merge_candidate(pool, refreshed, seen_refs, query=query)

    alt_queries = build_alt_queries(original_piece, query)

    for _round in range(_RECOVER_ROUNDS):
        if time.monotonic() - start >= _RECOVER_WALL_SEC:
            break
        for alt_q in alt_queries:
            if searches_done >= _RECOVER_SEARCHES:
                break
            if time.monotonic() - start >= _RECOVER_WALL_SEC:
                break
            hits = food_mod.search_foods_resolved(
                alt_q,
                limit=5,
                fetch_remote=fetch_remote,
                paths=paths,
                http_get=http_get,
            )
            searches_done += 1
            recover_searches.append({"query": alt_q, "count": len(hits), "recover": True})
            for hit in hits:
                refreshed = _refresh_fdc_detail(hit, paths=paths, http_get=http_get)
                _merge_candidate(pool, refreshed, seen_refs, query=query)

            if pool:
                pool = _filter_candidates(query, pool)
                if not pool:
                    continue
                decision = decide_food_bind(
                    query=query, candidates=pool, favorite=favorite
                )
                line, _, _ = _slot_from_decision(
                    query=query,
                    qty=qty,
                    unit=unit,
                    serving_grams=serving_grams,
                    decision=decision,
                    paths=paths,
                )
                if line:
                    return {
                        "ok": True,
                        "line": line,
                        "decision": decision,
                        "searches": recover_searches,
                    }

    return {
        "ok": False,
        "reason": "recover_cap",
        "ask": _RECOVER_ASK,
        "searches": recover_searches,
    }


def build_meal_log_args(
    utterance: str,
    *,
    meal_slot: str | None = None,
    fetch_remote: bool = True,
    paths=None,
    http_get: Callable[..., httpx.Response] | None = None,
) -> dict[str, Any]:
    """Decompose multi-item meal NL → N lines through resolve / Confirm gate (M24).

    Favorite sticky → silent bind. brand_fight / many / empty macros → Confirm.
    Hold whole meal if any line needs Confirm (OPEN #1). No partial silent write.
    M25: bounded recover on empty_macros / food_search_miss before fail-closed hold.
    """
    cleaned = _strip_meal_slot_words(utterance, meal_slot)
    parts = [p.strip() for p in _SPLIT.split(cleaned) if p.strip()]
    lines: list[dict[str, Any]] = []
    misses: list[dict[str, Any]] = []
    searches: list[dict[str, Any]] = []
    resolve_rows: list[dict[str, Any]] = []
    confirm_candidates: list[dict[str, Any]] = []
    reasons: list[str] = []
    needs_confirm = False
    meal_ask: str | None = None

    for part in parts:
        query, qty, unit, serving_grams = _parse_piece(part)
        if not query:
            misses.append({"query": part, "reason": "empty_piece"})
            continue

        favorite = favorites_mod.get_favorite(query, paths=paths)
        candidates = food_mod.search_foods_resolved(
            query, limit=5, fetch_remote=fetch_remote, paths=paths, http_get=http_get
        )
        searches.append({"query": query, "count": len(candidates)})
        candidates = [
            _refresh_fdc_detail(_candidate_as_row(c), paths=paths, http_get=http_get)
            for c in candidates
        ]
        candidates = _filter_candidates(query, candidates)

        # Favorite ref not in search hit list — still offer it as a candidate.
        if favorite and favorite.get("ref_id"):
            fav_id = str(favorite["ref_id"])
            if not any(
                str(c.get("ref_id") or c.get("food_ref_id") or "") == fav_id
                for c in candidates
            ):
                fav_row = food_mod.get_food(fav_id, paths=paths)
                if fav_row:
                    nutrients = json.loads(fav_row.get("nutrients_per_100g_json") or "{}")
                    candidates = [
                        {
                            "ref_id": fav_row.get("food_ref_id"),
                            "name": fav_row.get("name") or favorite.get("label") or query,
                            "brand": favorite.get("brand") or fav_row.get("brand"),
                            "source": fav_row.get("source"),
                            "score": 1.0,
                            "nutrients": nutrients,
                        }
                    ] + candidates

        if not candidates:
            recover = recover_food_slot(
                query=query,
                original_piece=part,
                qty=qty,
                unit=unit,
                serving_grams=serving_grams,
                miss_reason="food_search_miss",
                favorite=favorite,
                fetch_remote=fetch_remote,
                paths=paths,
                http_get=http_get,
            )
            searches.extend(recover.get("searches") or [])
            if recover.get("ok") and recover.get("line"):
                decision = recover.get("decision") or {}
                line = recover["line"]
                if decision.get("needs_confirm"):
                    needs_confirm = True
                    for r in decision.get("reasons") or []:
                        if r not in reasons:
                            reasons.append(r)
                    resolve_rows.append(decision)
                    confirm_candidates.extend(list(decision.get("candidates") or []))
                lines.append(line)
                continue
            misses.append({"query": query, "reason": "food_search_miss"})
            if recover.get("ask"):
                meal_ask = str(recover["ask"])
            continue

        decision = decide_food_bind(
            query=query, candidates=candidates, favorite=favorite
        )
        bind = decision.get("bind")
        if not bind:
            misses.append({"query": query, "reason": "no_bind"})
            continue

        ref_id = str(
            decision.get("proposed_ref_id")
            or bind.get("ref_id")
            or bind.get("food_ref_id")
            or ""
        )
        if not ref_id:
            misses.append({"query": query, "reason": "food_ref_missing"})
            continue

        # Empty-macro guard (F-M24-2): never durable-ok write all-null macros.
        recorded_resolve = False
        if macros_all_null(bind):
            viable = [
                c
                for c in (decision.get("candidates") or [])
                if isinstance(c, dict) and not c.get("macros_empty")
            ]
            if not viable:
                recover = recover_food_slot(
                    query=query,
                    original_piece=part,
                    qty=qty,
                    unit=unit,
                    serving_grams=serving_grams,
                    miss_reason="empty_macros",
                    initial_candidates=candidates,
                    favorite=favorite,
                    fetch_remote=fetch_remote,
                    paths=paths,
                    http_get=http_get,
                )
                searches.extend(recover.get("searches") or [])
                if recover.get("ok") and recover.get("line"):
                    decision = recover.get("decision") or {}
                    line = recover["line"]
                    if decision.get("needs_confirm"):
                        needs_confirm = True
                        if "empty_macros" not in reasons:
                            reasons.append("empty_macros")
                        for r in decision.get("reasons") or []:
                            if r not in reasons:
                                reasons.append(r)
                        resolve_rows.append(decision)
                        confirm_candidates.extend(list(decision.get("candidates") or []))
                    lines.append(line)
                    continue
                misses.append({"query": query, "reason": "empty_macros"})
                if recover.get("ask"):
                    meal_ask = str(recover["ask"])
                continue
            needs_confirm = True
            if "empty_macros" not in reasons:
                reasons.append("empty_macros")
            resolve_rows.append(decision)
            confirm_candidates.extend(list(decision.get("candidates") or []))
            recorded_resolve = True
            ref_id = str(viable[0].get("ref_id") or ref_id)

        line = _line_from_ref(
            query=query,
            ref_id=ref_id,
            qty=qty,
            unit=unit,
            serving_grams=serving_grams,
            display_name=(decision.get("bind_preview") or {}).get("label"),
            paths=paths,
        )
        if not line:
            misses.append({"query": query, "reason": "food_ref_missing"})
            continue
        if macros_all_null({"nutrients": line.get("nutrients") or {}}):
            recover = recover_food_slot(
                query=query,
                original_piece=part,
                qty=qty,
                unit=unit,
                serving_grams=serving_grams,
                miss_reason="empty_macros",
                initial_candidates=candidates,
                favorite=favorite,
                fetch_remote=fetch_remote,
                paths=paths,
                http_get=http_get,
            )
            searches.extend(recover.get("searches") or [])
            if recover.get("ok") and recover.get("line"):
                decision = recover.get("decision") or {}
                line = recover["line"]
                if decision.get("needs_confirm"):
                    needs_confirm = True
                    if "empty_macros" not in reasons:
                        reasons.append("empty_macros")
                    for r in decision.get("reasons") or []:
                        if r not in reasons:
                            reasons.append(r)
                    resolve_rows.append(decision)
                    confirm_candidates.extend(list(decision.get("candidates") or []))
                lines.append(line)
                continue
            misses.append({"query": query, "reason": "empty_macros"})
            if recover.get("ask"):
                meal_ask = str(recover["ask"])
            continue

        decision_reasons = list(decision.get("reasons") or [])
        if (
            decision.get("needs_confirm")
            and "brand_fight" in decision_reasons
            and not _has_plausible_generic_candidate(query, candidates)
        ):
            recover = recover_food_slot(
                query=query,
                original_piece=part,
                qty=qty,
                unit=unit,
                serving_grams=serving_grams,
                miss_reason="brand_fight",
                initial_candidates=candidates,
                favorite=favorite,
                fetch_remote=fetch_remote,
                paths=paths,
                http_get=http_get,
            )
            searches.extend(recover.get("searches") or [])
            if recover.get("ok") and recover.get("line"):
                decision = recover.get("decision") or {}
                line = recover["line"]
                if decision.get("needs_confirm"):
                    needs_confirm = True
                    if "brand_fight" not in reasons:
                        reasons.append("brand_fight")
                    for r in decision.get("reasons") or []:
                        if r not in reasons:
                            reasons.append(r)
                    resolve_rows.append(decision)
                    confirm_candidates.extend(list(decision.get("candidates") or []))
                lines.append(line)
                continue

        if decision.get("needs_confirm") and not recorded_resolve:
            needs_confirm = True
            for r in decision_reasons:
                if r not in reasons:
                    reasons.append(r)
            resolve_rows.append(decision)
            confirm_candidates.extend(list(decision.get("candidates") or []))

        lines.append(line)

    # OPEN #4: any miss → fail closed whole meal (no partial silent / Confirm-half).
    if misses:
        out: dict[str, Any] = {
            "ok": False,
            "needs_confirm": False,
            "meal_slot": meal_slot,
            "lines": [],
            "misses": misses,
            "searches": searches,
            "utterance": utterance,
            "reason": "partial_miss" if lines else (misses[0].get("reason") if misses else "miss"),
        }
        if meal_ask:
            out["ask"] = meal_ask
        return out

    # Hold whole meal if any line needs Confirm (OPEN #1).
    resolve_blob = None
    if needs_confirm and lines:
        resolve_blob = {
            "reasons": reasons or ["ambiguous"],
            "rows": [
                {
                    "query": r.get("query"),
                    "query_norm": r.get("query_norm"),
                    "reasons": r.get("reasons"),
                    "candidates": r.get("candidates"),
                    "proposed_ref_id": r.get("proposed_ref_id")
                    or (
                        (r.get("bind_preview") or {}).get("ref_id")
                        if isinstance(r.get("bind_preview"), dict)
                        else None
                    ),
                }
                for r in resolve_rows
            ],
            "candidates": confirm_candidates,
        }

    return {
        "ok": bool(lines),
        "needs_confirm": bool(needs_confirm and lines),
        "meal_slot": meal_slot,
        "lines": lines,
        "misses": misses,
        "searches": searches,
        "utterance": utterance,
        "resolve": resolve_blob,
        "save_favorite": True,
    }
