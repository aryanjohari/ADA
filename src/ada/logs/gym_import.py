"""Seed exercise catalog into life_logs.db (M19a)."""

from __future__ import annotations

import json
import uuid
from importlib.resources import files
from pathlib import Path
from typing import Any

from ada.io.paths import DataPaths
from ada.logs.connection import open_life_db


def _seed_path(name: str = "exercise_seed_min.json") -> Path:
    pkg = files("ada.logs.data")
    return Path(str(pkg / name))


def _movement_from_category(category: str | None) -> str | None:
    if not category:
        return None
    needle = category.lower()
    if "push" in needle:
        return "push"
    if "pull" in needle:
        return "pull"
    if "squat" in needle or "legs" in needle:
        return "squat"
    if "hinge" in needle or "deadlift" in needle:
        return "hinge"
    return "other"


def _normalize_external_item(item: dict[str, Any]) -> dict[str, Any] | None:
    """Map bundled seed, wger, or exercisedb-shaped JSON to catalog row."""
    if not isinstance(item, dict):
        return None
    if item.get("canonical_name"):
        return {
            "exercise_id": item.get("exercise_id"),
            "canonical_name": str(item["canonical_name"]),
            "aliases": item.get("aliases") or [],
            "body_parts": item.get("body_parts") or [],
            "equipment": item.get("equipment") or [],
            "movement": item.get("movement"),
            "source": item.get("source") or "seed",
            "external_id": item.get("external_id"),
        }
    name = item.get("name") or item.get("exercise_name")
    if not name:
        return None
    aliases: list[str] = []
    for key in ("aliases", "alias"):
        raw = item.get(key)
        if isinstance(raw, list):
            aliases.extend(str(a) for a in raw if a)
        elif isinstance(raw, str) and raw.strip():
            aliases.append(raw.strip())
    body_parts: list[str] = []
    for key in ("body_parts", "muscles", "primaryMuscles", "targetMuscles"):
        raw = item.get(key)
        if isinstance(raw, list):
            body_parts.extend(str(x) for x in raw if x)
        elif isinstance(raw, str) and raw.strip():
            body_parts.append(raw.strip())
    equipment: list[str] = []
    for key in ("equipment", "equipments"):
        raw = item.get(key)
        if isinstance(raw, list):
            equipment.extend(str(x) for x in raw if x)
        elif isinstance(raw, str) and raw.strip():
            equipment.append(raw.strip())
    category = item.get("category") or item.get("force") or item.get("mechanic")
    movement = _movement_from_category(str(category) if category else None)
    external_id = item.get("external_id") or item.get("id")
    return {
        "exercise_id": item.get("exercise_id"),
        "canonical_name": str(name),
        "aliases": aliases,
        "body_parts": body_parts,
        "equipment": equipment,
        "movement": movement,
        "source": item.get("source") or "import",
        "external_id": str(external_id) if external_id is not None else None,
    }


def _load_exercise_items(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, list):
        return [x for x in raw if isinstance(x, dict)]
    if isinstance(raw, dict):
        for key in ("exercises", "results", "data"):
            nested = raw.get(key)
            if isinstance(nested, list):
                return [x for x in nested if isinstance(x, dict)]
    return []


def import_exercise_seed(
    *,
    path: Path | None = None,
    paths: DataPaths | None = None,
    seed_name: str = "exercise_seed.json",
) -> dict[str, Any]:
    src = path or _seed_path(seed_name)
    raw = json.loads(src.read_text(encoding="utf-8"))
    items = _load_exercise_items(raw)
    imported = 0
    skipped = 0
    with open_life_db(paths=paths) as conn:
        for item in items:
            norm = _normalize_external_item(item)
            if not norm:
                skipped += 1
                continue
            ex_id = norm.get("exercise_id") or uuid.uuid4().hex
            conn.execute(
                """
                INSERT OR IGNORE INTO exercise_catalog (
                  exercise_id, canonical_name, aliases_json, body_parts_json,
                  equipment_json, movement, source, external_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ex_id,
                    norm["canonical_name"],
                    json.dumps(norm.get("aliases") or []),
                    json.dumps(norm.get("body_parts") or []),
                    json.dumps(norm.get("equipment") or []),
                    norm.get("movement"),
                    norm.get("source") or "seed",
                    norm.get("external_id"),
                ),
            )
            imported += 1
    return {"ok": True, "imported": imported, "skipped": skipped, "path": str(src)}
