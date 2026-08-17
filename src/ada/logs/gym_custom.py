"""FACTS custom gym exercises (M19a)."""

from __future__ import annotations

import json
from typing import Any

import yaml

from ada.body.vitals import utc_now_iso
from ada.io.atomic import atomic_write_text
from ada.io.paths import DataPaths, require_ada_data
from ada.memory.facts import _doc_path, _dump_yaml, _load_yaml, _require_mounted


def _custom_path(paths: DataPaths | None = None) -> Any:
    p = _require_mounted(paths or require_ada_data())
    p.ensure_memory_dirs()
    return _doc_path(p, "gym_custom_exercises")


def load_custom_exercises(*, paths: DataPaths | None = None) -> list[dict[str, Any]]:
    path = _custom_path(paths)
    if not path.is_file():
        return []
    data = _load_yaml(path)
    exercises = data.get("exercises") or []
    return exercises if isinstance(exercises, list) else []


def find_custom_exercise(name: str, *, paths: DataPaths | None = None) -> dict[str, Any] | None:
    needle = name.strip().lower()
    for ex in load_custom_exercises(paths=paths):
        display = str(ex.get("display_name") or ex.get("id") or "").lower()
        if needle == display or needle == str(ex.get("id") or "").lower():
            return ex
    return None


def save_custom_exercise(
    *,
    display_name: str,
    body_parts: list[str] | None = None,
    equipment: list[str] | None = None,
    movement: str | None = None,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    p = _require_mounted(paths or require_ada_data())
    path = _custom_path(p)
    data = _load_yaml(path) if path.is_file() else {"schema_version": 1, "exercises": []}
    exercises = list(data.get("exercises") or [])
    ex_id = "custom_" + display_name.lower().replace(" ", "_")[:40]
    entry = {
        "id": ex_id,
        "display_name": display_name,
        "body_parts": body_parts or [],
        "equipment": equipment or [],
        "movement": movement,
        "provenance": {"source": "operator", "at": utc_now_iso()},
    }
    exercises.append(entry)
    data["exercises"] = exercises
    atomic_write_text(path, _dump_yaml(data))
    return entry
