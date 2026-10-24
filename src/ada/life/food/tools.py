"""life_food_* / life_meal_* / life_nutrition_* / barcode / draft / preset handlers."""

from __future__ import annotations

import json
from typing import Any

from ada.harness.resolve_gate import macros_all_null
from ada.logs import food as food_mod
from ada.logs import meals as meals_mod
from ada.logs.receipts import write_life_crumb


def _write(tool: str, receipt_id: str, outcome: dict[str, Any]) -> dict[str, Any]:
    if receipt_id and outcome.get("ok"):
        write_life_crumb(receipt_id=receipt_id, tool=tool, outcome=outcome)
    return outcome


def _scale_line_nutrients(
    per_100g: dict[str, Any], grams: float | None
) -> dict[str, float | None]:
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


def _line_energy_kcal(line: dict[str, Any]) -> float | None:
    """Honest energy from line nutrients or snapshot — None is not zero."""
    for blob in (line.get("nutrients"), None):
        if isinstance(blob, dict) and blob.get("energy_kcal") is not None:
            try:
                return float(blob["energy_kcal"])
            except (TypeError, ValueError):
                return None
    snap = line.get("snapshot_json")
    if isinstance(snap, dict):
        sn = snap.get("nutrients") if isinstance(snap.get("nutrients"), dict) else {}
        if isinstance(sn, dict) and sn.get("energy_kcal") is not None:
            try:
                return float(sn["energy_kcal"])
            except (TypeError, ValueError):
                return None
    return None


def _line_macros_present(line: dict[str, Any]) -> bool:
    """Write-ready when CORE macros include energy_kcal (null energy ≠ kcal 0)."""
    nutrients = line.get("nutrients")
    if (
        isinstance(nutrients, dict)
        and nutrients.get("energy_kcal") is not None
        and not macros_all_null({"nutrients": nutrients})
    ):
        return True
    snap = line.get("snapshot_json")
    if isinstance(snap, dict):
        sn = snap.get("nutrients") if isinstance(snap.get("nutrients"), dict) else {}
        if (
            isinstance(sn, dict)
            and sn.get("energy_kcal") is not None
            and not macros_all_null({"nutrients": sn})
        ):
            return True
    return False


def _enrich_meal_line_from_ref(line: dict[str, Any]) -> dict[str, Any]:
    """Fill nutrients/snapshot from food cache when cortex passes ref_id only (F-M25-7)."""
    if _line_macros_present(line):
        return line
    ref_id = str(line.get("ref_id") or "").strip()
    if not ref_id:
        return line
    row = food_mod.get_food(ref_id)
    if not row:
        return line
    per_100g = json.loads(row.get("nutrients_per_100g_json") or "{}")
    if macros_all_null({"nutrients": per_100g}):
        return line
    serving_grams = line.get("serving_grams")
    if serving_grams is None:
        qty = float(line.get("serving_qty") or 1.0)
        unit = str(line.get("serving_unit") or "serving").lower()
        if unit in {"g", "gram", "grams", "ml"}:
            serving_grams = qty
    nutrients = _scale_line_nutrients(per_100g, serving_grams)
    provider = str(row.get("source") or "manual")
    enriched = dict(line)
    enriched.setdefault("display_name", row.get("name"))
    enriched["nutrients"] = nutrients
    enriched["snapshot_json"] = {
        "schema_version": 1,
        "nutrients": nutrients,
        "source": {
            "provider": provider,
            "external_id": row.get("external_id"),
            "fetched_at": row.get("imported_at"),
        },
    }
    enriched.setdefault("provenance", "api" if provider == "usda_fdc" else provider)
    return enriched


def _resolve_candidate_for_line(
    line: dict[str, Any], resolve: dict[str, Any] | None
) -> dict[str, Any] | None:
    """Find resolve-row candidate matching line ref_id (Confirm preview handoff)."""
    if not resolve:
        return None
    ref_id = str(line.get("ref_id") or "").strip()
    if not ref_id:
        return None
    pools: list[dict[str, Any]] = []
    for row in resolve.get("rows") or []:
        if isinstance(row, dict):
            pools.extend(c for c in (row.get("candidates") or []) if isinstance(c, dict))
    pools.extend(c for c in (resolve.get("candidates") or []) if isinstance(c, dict))
    for cand in pools:
        if str(cand.get("ref_id") or "") == ref_id:
            return cand
    return None


def _preview_per_100g_from_cand(cand: dict[str, Any]) -> dict[str, Any] | None:
    nutrients = cand.get("nutrients")
    if isinstance(nutrients, dict) and not macros_all_null({"nutrients": nutrients}):
        return dict(nutrients)
    raw = cand.get("nutrients_per_100g")
    if isinstance(raw, dict) and not macros_all_null({"nutrients": raw}):
        return dict(raw)
    kcal = cand.get("kcal_per_100g")
    if kcal is not None:
        try:
            return {
                "energy_kcal": float(kcal),
                "protein_g": None,
                "fat_g": None,
                "carb_g": None,
            }
        except (TypeError, ValueError):
            return None
    return None


def _enrich_meal_line_from_resolve_preview(
    line: dict[str, Any], resolve: dict[str, Any] | None
) -> dict[str, Any]:
    """If DB enrich missed but Confirm picker had kcal → scale preview into line."""
    if _line_macros_present(line):
        return line
    cand = _resolve_candidate_for_line(line, resolve)
    if not cand:
        return line
    per_100g = _preview_per_100g_from_cand(cand)
    if not per_100g:
        return line
    # Accept kcal-only preview (energy set, other CORE null) — still honest partial.
    if macros_all_null({"nutrients": per_100g}) and per_100g.get("energy_kcal") is None:
        return line
    serving_grams = line.get("serving_grams")
    if serving_grams is None:
        qty = float(line.get("serving_qty") or 1.0)
        unit = str(line.get("serving_unit") or "serving").lower()
        if unit in {"g", "gram", "grams", "ml"}:
            serving_grams = qty
    nutrients = _scale_line_nutrients(per_100g, serving_grams)
    if nutrients.get("energy_kcal") is None and macros_all_null({"nutrients": nutrients}):
        return line
    enriched = dict(line)
    enriched["nutrients"] = nutrients
    snap = (
        dict(enriched.get("snapshot_json") or {})
        if isinstance(enriched.get("snapshot_json"), dict)
        else {}
    )
    snap.setdefault("schema_version", 1)
    snap["nutrients"] = nutrients
    src = (
        dict(snap.get("source") or {})
        if isinstance(snap.get("source"), dict)
        else {}
    )
    src.setdefault("provider", "confirm_preview")
    snap["source"] = src
    enriched["snapshot_json"] = snap
    if cand.get("label") or cand.get("name"):
        enriched.setdefault("display_name", cand.get("label") or cand.get("name"))
    return enriched


def _require_spine_resolve(args: dict[str, Any], *, confirmed: bool) -> dict[str, Any] | None:
    """Refuse cortex freestyle meal_log — bind authority is meal_spine only (M26 v1.8)."""
    if confirmed:
        return None
    resolve = args.get("resolve") if isinstance(args.get("resolve"), dict) else None
    if not resolve:
        return {
            "ok": False,
            "outcome": "error",
            "reason": "spine_required",
            "error": "spine_required",
            "lines": args.get("lines") or [],
        }
    if resolve.get("bind_authority") != "meal_spine":
        return {
            "ok": False,
            "outcome": "error",
            "reason": "spine_required",
            "error": "spine_required",
            "lines": args.get("lines") or [],
        }
    return None


def _resolve_needs_confirm_hold(resolve: dict[str, Any]) -> bool:
    """True when spine resolve must hold write until operator Confirm."""
    if resolve.get("needs_confirm") is False:
        return False
    reasons: list[str] = list(resolve.get("reasons") or [])
    for row in resolve.get("rows") or []:
        if isinstance(row, dict):
            reasons.extend(row.get("reasons") or [])
    silent_ok = not reasons or set(reasons) <= {"favorite_unique"}
    return not silent_ok


def _refuse_empty_macros(lines: list[dict[str, Any]]) -> dict[str, Any] | None:
    """F-M24-2 / F-M25-7 / M26: refuse write when macros missing or line unbound.

    Sibling guard: ``_require_spine_resolve`` blocks cortex ref_id commits without
    meal_spine ``resolve.bind_authority``. Freestyle name-only lines (no ref_id/
    preset_id, no honest nutrients) must not touch SQLite — fail closed before insert.
    Null ``energy_kcal`` with P/F/C present is also refuse (phone oats → kcal 0).
    """
    for line in lines:
        if _line_macros_present(line):
            continue
        has_ref = bool(str(line.get("ref_id") or "").strip())
        has_preset = bool(str(line.get("preset_id") or "").strip())
        nutrients = line.get("nutrients")
        snap = line.get("snapshot_json")
        explicit_empty = (
            isinstance(nutrients, dict) and macros_all_null({"nutrients": nutrients})
        ) or (
            isinstance(snap, dict)
            and isinstance(snap.get("nutrients"), dict)
            and macros_all_null({"nutrients": snap["nutrients"]})
        )
        # P/F/C without energy still not write-ready (would coerce to kcal 0).
        energy_missing = _line_energy_kcal(line) is None and (
            (
                isinstance(nutrients, dict)
                and any(
                    nutrients.get(k) is not None
                    for k in ("protein_g", "fat_g", "carb_g")
                )
            )
            or (
                isinstance(snap, dict)
                and isinstance(snap.get("nutrients"), dict)
                and any(
                    snap["nutrients"].get(k) is not None
                    for k in ("protein_g", "fat_g", "carb_g")
                )
            )
        )
        # Unbound display_name-only → empty_macros (no invent, no orphan meal row).
        if not has_ref and not has_preset:
            return {
                "ok": False,
                "outcome": "error",
                "reason": "empty_macros",
                "error": "empty_macros",
                "lines": lines,
            }
        if has_ref or explicit_empty or energy_missing:
            return {
                "ok": False,
                "outcome": "error",
                "reason": "empty_macros",
                "error": "empty_macros",
                "lines": lines,
            }
    return None

def run_life_food_search(args: dict[str, Any]) -> dict[str, Any]:
    query = args.get("query") or args.get("q") or ""
    limit = int(args.get("limit") or 10)
    fetch_remote = bool(args.get("fetch_remote", True))
    candidates = food_mod.search_foods_resolved(
        str(query), limit=limit, fetch_remote=fetch_remote
    )
    return {"ok": True, "outcome": "ok", "candidates": candidates}


def run_life_barcode_lookup(args: dict[str, Any]) -> dict[str, Any]:
    barcode = args.get("barcode") or args.get("gtin") or ""
    fetch_remote = bool(args.get("fetch_remote", True))
    result = food_mod.barcode_lookup(str(barcode), fetch_remote=fetch_remote)
    if not result.get("ok"):
        return {"ok": False, "outcome": "ok", **result}
    return {"ok": True, "outcome": "ok", **result}


def run_life_meal_log(args: dict[str, Any]) -> dict[str, Any]:
    receipt_id = str(args.get("receipt_id") or "")
    lines = args.get("lines") or []
    if not lines:
        raise ValueError("lines required")
    resolve = args.get("resolve") if isinstance(args.get("resolve"), dict) else None
    confirmed = bool(args.get("confirmed", False))
    refused = _require_spine_resolve(args, confirmed=confirmed)
    if refused:
        return refused
    # M21: ambiguous bind held at gateway — no write until confirmed=true.
    if resolve and not confirmed and _resolve_needs_confirm_hold(resolve):
        return {
            "ok": False,
            "needs_confirm": True,
            "outcome": "needs_confirm",
            "reason": (resolve.get("reasons") or ["ambiguous"])[0]
            if isinstance(resolve.get("reasons"), list)
            else resolve.get("reason") or "ambiguous",
            "reasons": list(resolve.get("reasons") or []),
            "candidates": list(resolve.get("candidates") or []),
            "resolve": resolve,
            "lines": lines,
            "meal_slot": args.get("meal_slot"),
            "note": args.get("note"),
            "save_favorite": bool(args.get("save_favorite", True)),
        }
    # Strip spine-private keys before durable write.
    clean_lines = []
    for line in lines:
        if not isinstance(line, dict):
            continue
        enriched = _enrich_meal_line_from_ref(line)
        # Confirm path: if DB thin/null but picker preview had kcal, scale that in
        # before empty_macros refuse (M26 v1.10 — run 55378c77…).
        if confirmed and not _line_macros_present(enriched):
            enriched = _enrich_meal_line_from_resolve_preview(enriched, resolve)
        clean = {k: v for k, v in enriched.items() if not str(k).startswith("_")}
        clean_lines.append(clean)
    refused = _refuse_empty_macros(clean_lines)
    if refused:
        return refused
    outcome = meals_mod.meal_log(
        receipt_id=receipt_id,
        note=args.get("note"),
        meal_slot=args.get("meal_slot"),
        lines=clean_lines,
    )
    written = _write("life_meal_log", receipt_id, outcome)
    if written.get("ok") and confirmed and bool(args.get("save_favorite", True)):
        resolve = resolve or {}
        from ada.logs import favorites as favorites_mod

        for row in resolve.get("rows") or []:
            # Prefer stable query_norm so wipe/re-bind sticks to the same key.
            q = str(row.get("query_norm") or row.get("query") or "").strip()
            ref = str(row.get("proposed_ref_id") or "").strip()
            if not q or not ref:
                continue
            preview = None
            for cand in row.get("candidates") or []:
                if str(cand.get("ref_id") or "") == ref:
                    preview = cand
                    break
            favorites_mod.set_favorite(
                query=q,
                ref_id=ref,
                label=(preview or {}).get("label"),
                brand=(preview or {}).get("brand"),
                confirmed=True,
            )
    return written


def run_life_food_favorite_set(args: dict[str, Any]) -> dict[str, Any]:
    from ada.logs import favorites as favorites_mod

    outcome = favorites_mod.set_favorite(
        query=str(args.get("query") or ""),
        ref_id=str(args.get("ref_id") or ""),
        label=args.get("label"),
        brand=args.get("brand"),
        confirmed=bool(args.get("confirmed", False)),
    )
    if outcome.get("needs_confirm"):
        outcome["ok"] = False
    return outcome

def run_life_meal_fix(args: dict[str, Any]) -> dict[str, Any]:
    receipt_id = str(args.get("receipt_id") or "")
    lines = args.get("lines") or []
    return _write(
        "life_meal_fix",
        receipt_id,
        meals_mod.meal_log(
            receipt_id=receipt_id,
            note=args.get("note"),
            meal_slot=args.get("meal_slot"),
            lines=lines,
        ),
    )


def run_life_nutrition_day(args: dict[str, Any]) -> dict[str, Any]:
    return meals_mod.nutrition_day(date=args.get("date"))


def run_life_nutrition_week(args: dict[str, Any]) -> dict[str, Any]:
    from ada.life.food.reflection import nutrition_window, write_food_reflection_scratch

    days = args.get("days", 7)
    try:
        days_n = int(days)
    except (TypeError, ValueError):
        days_n = 7
    result = nutrition_window(days=days_n)
    write_food_reflection_scratch(result)
    return result
def run_life_food_preset_save(args: dict[str, Any]) -> dict[str, Any]:
    from ada.logs import nutrition_presets as presets_mod

    name = args.get("name") or args.get("preset_id")
    if not name:
        raise ValueError("name required")
    components = args.get("components") or []
    outcome = presets_mod.save_preset(
        name=str(name),
        components=list(components) if isinstance(components, list) else [],
        provenance=args.get("provenance"),
        confirmed=bool(args.get("confirmed", False)),
    )
    if outcome.get("needs_confirm"):
        outcome["ok"] = False
    return outcome


def run_life_meal_draft_start(args: dict[str, Any]) -> dict[str, Any]:
    from ada.logs import meal_draft as draft_mod

    session_id = str(args.get("session_id") or "")
    if not session_id:
        return {"ok": False, "reason": "session_id_required"}
    return draft_mod.start_draft(session_id)


def run_life_meal_draft_add(args: dict[str, Any]) -> dict[str, Any]:
    """Confirm-gated append of one resolved line into the open meal draft."""
    from ada.logs import meal_draft as draft_mod
    from ada.logs import favorites as favorites_mod

    session_id = str(args.get("session_id") or "")
    lines = args.get("lines") or []
    if not session_id:
        return {"ok": False, "reason": "session_id_required"}
    if not lines:
        return {"ok": False, "reason": "lines_required"}
    resolve = args.get("resolve") if isinstance(args.get("resolve"), dict) else None
    confirmed = bool(args.get("confirmed", False))
    if resolve and not confirmed and _resolve_needs_confirm_hold(resolve):
        return {
            "ok": False,
            "needs_confirm": True,
            "outcome": "needs_confirm",
            "reason": (resolve.get("reasons") or ["ambiguous"])[0]
            if isinstance(resolve.get("reasons"), list)
            else resolve.get("reason") or "ambiguous",
            "reasons": list(resolve.get("reasons") or []),
            "candidates": list(resolve.get("candidates") or []),
            "resolve": resolve,
            "lines": lines,
            "session_id": session_id,
            "save_favorite": bool(args.get("save_favorite", True)),
            "draft_action": "add",
        }
    # Apply confirmed bind; sticky favorite on Yes (same as meal_log).
    clean_lines = []
    for line in lines:
        if not isinstance(line, dict):
            continue
        enriched = _enrich_meal_line_from_ref(line)
        if confirmed and not _line_macros_present(enriched):
            enriched = _enrich_meal_line_from_resolve_preview(enriched, resolve)
        clean = {k: v for k, v in enriched.items() if not str(k).startswith("_")}
        clean_lines.append(clean)
    refused = _refuse_empty_macros(clean_lines)
    if refused:
        return refused
    last = None
    for ln in clean_lines:
        last = draft_mod.append_draft_line(session_id, ln)
        if not last.get("ok"):
            return last
    if confirmed and bool(args.get("save_favorite", True)) and resolve:
        for row in resolve.get("rows") or []:
            q = str(row.get("query_norm") or row.get("query") or "").strip()
            ref = str(row.get("proposed_ref_id") or "").strip()
            if not q or not ref:
                continue
            preview = None
            for cand in row.get("candidates") or []:
                if str(cand.get("ref_id") or "") == ref:
                    preview = cand
                    break
            favorites_mod.set_favorite(
                query=q,
                ref_id=ref,
                label=(preview or {}).get("label"),
                brand=(preview or {}).get("brand"),
                confirmed=True,
            )
    return {
        "ok": True,
        **(last or {}),
        "added": len(clean_lines),
    }


def run_life_meal_draft_save(args: dict[str, Any]) -> dict[str, Any]:
    from ada.logs import meal_draft as draft_mod
    from ada.logs import nutrition_presets as presets_mod
    from ada.life.food.draft_spine import build_draft_save_args

    session_id = str(args.get("session_id") or "")
    name = args.get("name")
    built = build_draft_save_args(
        session_id,
        name=str(name) if name else None,
        confirmed=bool(args.get("confirmed", False)),
    )
    if not built.get("ok"):
        return built
    outcome = presets_mod.save_preset(
        name=str(built["name"]),
        components=list(built["components"]),
        provenance=built.get("provenance"),
        confirmed=bool(args.get("confirmed", False)),
    )
    if outcome.get("needs_confirm"):
        outcome["ok"] = False
        outcome["session_id"] = session_id
        return outcome
    if outcome.get("ok"):
        draft_mod.clear_draft(session_id)
        outcome["draft_cleared"] = True
        outcome["ask"] = "Saved. Log it now?"
    return outcome


def run_life_meal_draft_cancel(args: dict[str, Any]) -> dict[str, Any]:
    from ada.logs import meal_draft as draft_mod

    session_id = str(args.get("session_id") or "")
    if not session_id:
        return {"ok": False, "reason": "session_id_required"}
    out = draft_mod.clear_draft(session_id)
    out["ask"] = "Cancelled — meal draft cleared."
    return out


def run_life_meal_preset_log(args: dict[str, Any]) -> dict[str, Any]:
    """Expand named preset → life_meal_log (Confirm on first use)."""
    from ada.life.food.draft_spine import expand_preset_log_args

    name = str(args.get("name") or args.get("preset_id") or "").strip()
    if not name:
        return {"ok": False, "reason": "name_required", "ask": "Which preset should I log?"}
    if args.get("lines") and args.get("resolve"):
        # Confirm redrive — write meal.
        log_args = {
            "lines": args["lines"],
            "resolve": args["resolve"],
            "meal_slot": args.get("meal_slot"),
            "confirmed": bool(args.get("confirmed", False)),
            "save_favorite": bool(args.get("save_favorite", False)),
            "receipt_id": args.get("receipt_id"),
        }
        # Ensure spine authority on resolve.
        resolve = dict(log_args["resolve"])
        resolve["bind_authority"] = "meal_spine"
        log_args["resolve"] = resolve
        return run_life_meal_log(log_args)

    built = expand_preset_log_args(name, meal_slot=args.get("meal_slot"))
    if not built.get("ok"):
        return built
    resolve = dict(built.get("resolve") or {})
    resolve["bind_authority"] = "meal_spine"
    resolve["needs_confirm"] = True
    return run_life_meal_log(
        {
            "lines": built["lines"],
            "resolve": resolve,
            "meal_slot": built.get("meal_slot"),
            "confirmed": bool(args.get("confirmed", False)),
            "save_favorite": False,
            "receipt_id": args.get("receipt_id"),
        }
    )


DISPATCH = {
    "life_food_search": run_life_food_search,
    "life_barcode_lookup": run_life_barcode_lookup,
    "life_meal_log": run_life_meal_log,
    "life_meal_fix": run_life_meal_fix,
    "life_nutrition_day": run_life_nutrition_day,
    "life_nutrition_week": run_life_nutrition_week,
    "life_food_preset_save": run_life_food_preset_save,
    "life_food_favorite_set": run_life_food_favorite_set,
    "life_meal_draft_start": run_life_meal_draft_start,
    "life_meal_draft_add": run_life_meal_draft_add,
    "life_meal_draft_save": run_life_meal_draft_save,
    "life_meal_draft_cancel": run_life_meal_draft_cancel,
    "life_meal_preset_log": run_life_meal_preset_log,
}
