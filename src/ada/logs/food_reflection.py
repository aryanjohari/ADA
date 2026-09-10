"""Deterministic food reflection on structured logs (M26) — not Dream, not LLM."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from ada.io.paths import DataPaths, require_ada_data
from ada.logs.connection import open_life_db
from ada.logs.tz_util import preferred_tz_name
from ada.memory.facts import get_fact

MAX_SUMMARY_CHARS = 2_000
_CORE_TOTAL_KEYS = ("energy_kcal", "protein_g", "carb_g", "fat_g")
_MEAL_SLOTS = ("breakfast", "lunch", "dinner", "snack")


def _cap_days(days: int) -> int:
    return max(1, min(int(days), 31))


def _local_days_window(*, days: int, paths: DataPaths | None = None) -> list[str]:
    tz = ZoneInfo(preferred_tz_name(paths=paths))
    today = datetime.now(timezone.utc).astimezone(tz).date()
    return [(today - timedelta(days=i)).isoformat() for i in range(days)]


def _load_targets(paths: DataPaths) -> dict[str, Any]:
    targets_doc = get_fact("nutrition_targets", paths=paths)
    if not targets_doc.get("found"):
        return {}
    val = targets_doc.get("value")
    if not isinstance(val, dict):
        return {}
    raw = val.get("targets") or val
    return {
        k: float(v)
        for k, v in raw.items()
        if isinstance(v, (int, float))
    }


def _day_gaps(totals: dict[str, Any], targets: dict[str, float]) -> dict[str, float | None]:
    gaps: dict[str, float | None] = {}
    for key, target in targets.items():
        got = totals.get(key)
        if got is not None:
            gaps[key] = float(target) - float(got)
    return gaps


def _totals_subset(totals: dict[str, Any]) -> dict[str, float]:
    out: dict[str, float] = {}
    for key in _CORE_TOTAL_KEYS:
        val = totals.get(key)
        if val is not None:
            out[key] = float(val)
    return out


def nutrition_window(
    *,
    days: int = 7,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    """Last N local calendar days vs FACTS targets — SQL + rules only."""
    p = paths or require_ada_data()
    window_days = _cap_days(days)
    calendar_days = _local_days_window(days=window_days, paths=p)
    targets = _load_targets(p)

    rollup_by_day: dict[str, dict[str, Any]] = {}
    meal_slots: dict[str, int] = {slot: 0 for slot in _MEAL_SLOTS}
    try:
        with open_life_db(paths=p) as conn:
            placeholders = ",".join("?" for _ in calendar_days)
            rows = conn.execute(
                f"""
                SELECT local_day, totals_json, meal_count, honest_partial
                FROM nutrition_day_rollup
                WHERE local_day IN ({placeholders})
                """,
                calendar_days,
            ).fetchall()
            for row in rows:
                totals = json.loads(row["totals_json"] or "{}")
                rollup_by_day[row["local_day"]] = {
                    "totals": totals,
                    "meal_count": int(row["meal_count"] or 0),
                    "honest_partial": bool(row["honest_partial"]),
                }
            slot_rows = conn.execute(
                f"""
                SELECT meal_slot, COUNT(*) AS n
                FROM meals
                WHERE local_day IN ({placeholders})
                  AND meal_slot IS NOT NULL
                GROUP BY meal_slot
                """,
                calendar_days,
            ).fetchall()
            for row in slot_rows:
                slot = str(row["meal_slot"] or "").lower()
                if slot == "snacks":
                    slot = "snack"
                if slot in meal_slots:
                    meal_slots[slot] = int(row["n"] or 0)
    except Exception:  # noqa: BLE001 — reflection must not fail closed on reads
        rollup_by_day = {}
        meal_slots = {slot: 0 for slot in _MEAL_SLOTS}

    days_out: list[dict[str, Any]] = []
    days_logged = 0
    honest_partial_days = 0
    protein_vals: list[float] = []
    kcal_vals: list[float] = []

    for local_day in calendar_days:
        rolled = rollup_by_day.get(local_day)
        if rolled is None:
            day_entry = {
                "day": local_day,
                "cite": f"meal:day:{local_day}",
                "meal_count": 0,
                "honest_partial": False,
                "totals": {},
                "gaps": {},
            }
        else:
            totals = _totals_subset(rolled["totals"])
            if rolled["meal_count"] > 0:
                days_logged += 1
            if rolled["honest_partial"]:
                honest_partial_days += 1
            if totals.get("protein_g") is not None:
                protein_vals.append(float(totals["protein_g"]))
            if totals.get("energy_kcal") is not None:
                kcal_vals.append(float(totals["energy_kcal"]))
            day_entry = {
                "day": local_day,
                "cite": f"meal:day:{local_day}",
                "meal_count": rolled["meal_count"],
                "honest_partial": rolled["honest_partial"],
                "totals": totals,
                "gaps": _day_gaps(totals, targets),
            }
        days_out.append(day_entry)

    if days_logged == 0:
        return {
            "ok": True,
            "window_days": window_days,
            "days_logged": 0,
            "days": [],
            "targets": targets,
            "aggregates": {},
            "meal_slots": meal_slots,
            "patterns": [],
            "flags": {},
            "summary_text": f"No meals logged in the last {window_days} days.",
            "message": f"No meals logged in the last {window_days} days.",
        }

    aggregates: dict[str, float] = {}
    if protein_vals:
        aggregates["sum_protein_g"] = round(sum(protein_vals), 1)
        aggregates["avg_protein_g"] = round(sum(protein_vals) / len(protein_vals), 1)
    if kcal_vals:
        aggregates["sum_energy_kcal"] = round(sum(kcal_vals), 1)
        aggregates["avg_energy_kcal"] = round(sum(kcal_vals) / len(kcal_vals), 1)

    flags: dict[str, Any] = {}
    patterns: list[str] = []
    if targets.get("protein_g") is not None:
        protein_target = float(targets["protein_g"])
        below = sum(
            1
            for d in days_out
            if float(d["totals"].get("protein_g") or 0) < protein_target
        )
        flags["protein_below_target"] = f"{below}/{window_days}"
        if below:
            patterns.append(f"protein below target {below}/{window_days} days")
    if targets.get("energy_kcal") is not None:
        kcal_target = float(targets["energy_kcal"])
        below = sum(
            1
            for d in days_out
            if float(d["totals"].get("energy_kcal") or 0) < kcal_target
        )
        flags["kcal_below_target"] = f"{below}/{window_days}"
        if below:
            patterns.append(f"kcal below target {below}/{window_days} days")
    if honest_partial_days:
        flags["honest_partial_days"] = honest_partial_days
        patterns.append(f"honest_partial days: {honest_partial_days}")

    lines = [
        f"nutrition_window (last {window_days} local days, {days_logged} logged):",
    ]
    for d in days_out:
        if d["meal_count"] == 0:
            continue
        lines.append(
            f"  {d['cite']}: meals={d['meal_count']} "
            f"totals={json.dumps(d['totals'], ensure_ascii=False)} "
            f"partial={d['honest_partial']}"
        )
    if targets:
        lines.append(f"targets={json.dumps(targets, ensure_ascii=False)}")
    if aggregates:
        lines.append(f"aggregates={json.dumps(aggregates, ensure_ascii=False)}")
    if any(meal_slots.values()):
        lines.append(f"meal_slots={json.dumps(meal_slots, ensure_ascii=False)}")
    for pat in patterns:
        lines.append(f"pattern: {pat}")
    summary_text = "\n".join(lines)
    if len(summary_text) > MAX_SUMMARY_CHARS:
        summary_text = summary_text[: MAX_SUMMARY_CHARS - 1] + "…"

    return {
        "ok": True,
        "window_days": window_days,
        "days_logged": days_logged,
        "days": days_out,
        "targets": targets,
        "aggregates": aggregates,
        "meal_slots": meal_slots,
        "patterns": patterns,
        "flags": flags,
        "summary_text": summary_text,
    }


def write_food_reflection_scratch(
    payload: dict[str, Any],
    *,
    paths: DataPaths | None = None,
) -> None:
    """Overwrite scratch artifact for brief/HUD (not WORLDVIEW)."""
    from ada.io.atomic import atomic_write_text

    p = paths or require_ada_data()
    p.scratch.mkdir(parents=True, exist_ok=True)
    target = p.scratch / "food_reflection_latest.json"
    atomic_write_text(
        target,
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
    )
