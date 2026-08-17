"""Meal log — append, fix, day rollup (M19a)."""

from __future__ import annotations

import json
import uuid
from typing import Any

from ada.body.vitals import utc_now_iso
from ada.io.paths import DataPaths
from ada.logs.connection import open_life_db
from ada.logs.food import core_nutrients_partial
from ada.logs.tz_util import utc_to_local_day
from ada.memory.facts import get_fact


def _empty_snapshot(nutrients: dict[str, Any] | None = None, provider: str = "manual") -> str:
    payload = {
        "schema_version": 1,
        "nutrients": nutrients or {},
        "source": {
            "provider": provider,
            "external_id": None,
            "fetched_at": utc_now_iso(),
        },
    }
    return json.dumps(payload, separators=(",", ":"))


def _sum_nutrients(snapshots: list[dict[str, Any]]) -> tuple[dict[str, float], bool]:
    totals: dict[str, float] = {}
    partial = False
    for snap in snapshots:
        nutrients = snap.get("nutrients") or {}
        if core_nutrients_partial(nutrients):
            partial = True
        for key, val in nutrients.items():
            if val is None:
                continue
            try:
                totals[key] = totals.get(key, 0.0) + float(val)
            except (TypeError, ValueError):
                partial = True
    return totals, partial


def _rollup_day(conn, local_day: str, *, paths: DataPaths | None = None) -> dict[str, Any]:
    rows = conn.execute(
        """
        SELECT mf.snapshot_json FROM meal_foods mf
        JOIN meals m ON m.meal_id = mf.meal_id
        WHERE m.local_day = ?
        ORDER BY m.logged_at, mf.sort_order
        """,
        (local_day,),
    ).fetchall()
    snapshots = [json.loads(r["snapshot_json"]) for r in rows]
    totals, partial = _sum_nutrients(snapshots)
    meal_count = conn.execute(
        "SELECT COUNT(*) FROM meals WHERE local_day = ?", (local_day,)
    ).fetchone()[0]
    targets_doc = get_fact("nutrition_targets", paths=paths)
    targets = None
    if targets_doc.get("found"):
        val = targets_doc.get("value")
        if isinstance(val, dict):
            targets = val.get("targets") or val
    now = utc_now_iso()
    conn.execute(
        """
        INSERT OR REPLACE INTO nutrition_day_rollup (
          local_day, computed_at, totals_json, target_snapshot_json,
          meal_count, honest_partial
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            local_day,
            now,
            json.dumps(totals),
            json.dumps(targets) if targets else None,
            meal_count,
            1 if partial else 0,
        ),
    )
    return {
        "local_day": local_day,
        "totals": totals,
        "meal_count": meal_count,
        "honest_partial": partial,
    }


def append_meal(
    *,
    receipt_id: str,
    note: str | None = None,
    meal_slot: str | None = None,
    lines: list[dict[str, Any]] | None = None,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    """Backward-compatible minimal append (Slice 0 tests)."""
    return meal_log(
        receipt_id=receipt_id,
        note=note,
        meal_slot=meal_slot,
        lines=lines or [{"display_name": "placeholder", "provenance": "manual"}],
        paths=paths,
    )


def meal_log(
    *,
    receipt_id: str,
    note: str | None = None,
    meal_slot: str | None = None,
    lines: list[dict[str, Any]],
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    meal_id = uuid.uuid4().hex
    now = utc_now_iso()
    local_day = utc_to_local_day(paths=paths)
    provenance_mix: list[str] = []
    kcal = protein = carb = fat = 0.0
    partial_micros = False
    with open_life_db(paths=paths) as conn:
        conn.execute(
            """
            INSERT INTO meals (
              meal_id, local_day, logged_at, meal_slot, note, revision,
              source_verb, receipt_id, created_at
            ) VALUES (?, ?, ?, ?, ?, 1, 'meal_log', ?, ?)
            """,
            (meal_id, local_day, now, meal_slot, note, receipt_id, now),
        )
        for idx, line in enumerate(lines):
            snap_raw = line.get("snapshot_json")
            if isinstance(snap_raw, dict):
                snap = json.dumps(snap_raw, separators=(",", ":"))
            elif snap_raw:
                snap = str(snap_raw)
            else:
                nutrients = line.get("nutrients") or {}
                prov = str(line.get("provenance") or "manual")
                snap = _empty_snapshot(nutrients, provider=prov)
            snap_obj = json.loads(snap)
            nutrients = snap_obj.get("nutrients") or {}
            kcal += float(nutrients.get("energy_kcal") or 0)
            protein += float(nutrients.get("protein_g") or 0)
            carb += float(nutrients.get("carb_g") or 0)
            fat += float(nutrients.get("fat_g") or 0)
            if core_nutrients_partial(nutrients):
                partial_micros = True
            prov = str(line.get("provenance") or "manual")
            provenance_mix.append(prov)
            conn.execute(
                """
                INSERT INTO meal_foods (
                  line_id, meal_id, sort_order, display_name, ref_id, preset_id,
                  serving_qty, serving_unit, serving_grams, provenance, snapshot_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    uuid.uuid4().hex,
                    meal_id,
                    idx,
                    str(line.get("display_name") or "food"),
                    line.get("ref_id"),
                    line.get("preset_id"),
                    float(line.get("serving_qty") or 1.0),
                    str(line.get("serving_unit") or "serving"),
                    line.get("serving_grams"),
                    prov,
                    snap,
                ),
            )
        _rollup_day(conn, local_day, paths=paths)
    return {
        "ok": True,
        "receipt_id": receipt_id,
        "meal_id": meal_id,
        "day": local_day,
        "kcal": round(kcal, 1),
        "protein_g": round(protein, 1),
        "carb_g": round(carb, 1),
        "fat_g": round(fat, 1),
        "provenance_mix": provenance_mix,
        "partial_micros": partial_micros,
    }


def nutrition_day(
    *,
    date: str | None = None,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    local_day = date or utc_to_local_day(paths=paths)
    with open_life_db(paths=paths) as conn:
        rollup = conn.execute(
            "SELECT * FROM nutrition_day_rollup WHERE local_day = ?",
            (local_day,),
        ).fetchone()
        if rollup is None:
            rolled = _rollup_day(conn, local_day, paths=paths)
            totals = rolled["totals"]
            honest_partial = rolled["honest_partial"]
        else:
            totals = json.loads(rollup["totals_json"])
            honest_partial = bool(rollup["honest_partial"])
    targets_doc = get_fact("nutrition_targets", paths=paths)
    targets: dict[str, Any] = {}
    if targets_doc.get("found"):
        val = targets_doc.get("value")
        if isinstance(val, dict):
            targets = val.get("targets") or val
    gaps: dict[str, float | None] = {}
    for key, target in targets.items():
        if isinstance(target, (int, float)):
            got = totals.get(key)
            if got is not None:
                gaps[key] = float(target) - float(got)
    return {
        "ok": True,
        "date": local_day,
        "totals": totals,
        "targets": targets,
        "gaps": gaps,
        "honest_partial": honest_partial,
    }
