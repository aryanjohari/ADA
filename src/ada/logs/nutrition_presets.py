"""Named nutrition presets — FACTS YAML only (M19a / M22 / M26 library)."""

from __future__ import annotations

import re
from typing import Any

from ada.body.vitals import utc_now_iso
from ada.io.atomic import atomic_write_text
from ada.io.paths import BodyFault, DataPaths, ada_data_mounted, require_ada_data
from ada.memory.facts import _dump_yaml, _load_yaml

_DOC = "nutrition_presets"


def _require(paths: DataPaths | None = None) -> DataPaths:
    p = paths or require_ada_data()
    if not ada_data_mounted(p.root):
        raise BodyFault("ADA data not mounted", code=2)
    p.ensure_memory_dirs()
    return p


def presets_path(*, paths: DataPaths | None = None):
    return _require(paths).facts / f"{_DOC}.yaml"


def _norm_id(name: str) -> str:
    raw = re.sub(r"\s+", " ", (name or "").strip().lower())
    slug = re.sub(r"[^a-z0-9]+", "_", raw).strip("_")
    return slug or raw


def load_presets(*, paths: DataPaths | None = None) -> dict[str, Any]:
    path = presets_path(paths=paths)
    raw = _load_yaml(path) if path.is_file() else {}
    doc = dict(raw or {})
    doc.setdefault("schema_version", 1)
    presets = doc.get("presets")
    if isinstance(presets, list):
        # Normalize legacy list → id map.
        mapped: dict[str, Any] = {}
        for row in presets:
            if not isinstance(row, dict):
                continue
            pid = _norm_id(str(row.get("id") or row.get("display_name") or ""))
            if pid:
                mapped[pid] = row
        doc["presets"] = mapped
    elif not isinstance(presets, dict):
        doc["presets"] = {}
    return doc


def get_preset(name: str, *, paths: DataPaths | None = None) -> dict[str, Any] | None:
    pid = _norm_id(name)
    if not pid:
        return None
    presets = load_presets(paths=paths).get("presets") or {}
    hit = presets.get(pid)
    if isinstance(hit, dict):
        return {**hit, "id": pid}
    # Soft match display_name
    needle = re.sub(r"\s+", " ", (name or "").strip().lower())
    for key, row in presets.items():
        if not isinstance(row, dict):
            continue
        disp = str(row.get("display_name") or key).strip().lower()
        if disp == needle or key.replace("_", " ") == needle:
            return {**row, "id": key}
    return None


def save_preset(
    *,
    name: str,
    components: list[dict[str, Any]],
    provenance: str | None = None,
    confirmed: bool = False,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    """Write named preset to FACTS. Soft Confirm on name clash unless confirmed."""
    display = re.sub(r"\s+", " ", (name or "").strip())
    pid = _norm_id(display)
    if not pid:
        return {"ok": False, "reason": "name_required"}
    if not components:
        return {"ok": False, "reason": "components_required"}
    p = _require(paths)
    doc = load_presets(paths=p)
    presets = dict(doc.get("presets") or {})
    existing = presets.get(pid)
    if existing is not None and not confirmed:
        return {
            "ok": False,
            "needs_confirm": True,
            "outcome": "needs_confirm",
            "reason": "preset_name_clash",
            "name": display,
            "preset_id": pid,
            "existing": existing,
            "proposed": {
                "id": pid,
                "display_name": display,
                "components": components,
                "provenance": provenance,
            },
        }
    entry = {
        "id": pid,
        "display_name": display,
        "components": components,
        "provenance": provenance or "custom",
        "at": utc_now_iso(),
        "source": "operator",
    }
    presets[pid] = entry
    doc["presets"] = presets
    path = presets_path(paths=p)
    atomic_write_text(path, _dump_yaml(doc))
    return {"ok": True, "preset_id": pid, "preset": entry, "path": str(path)}


def expand_preset_lines(
    name: str, *, paths: DataPaths | None = None
) -> dict[str, Any]:
    """Expand preset → meal lines shaped for life_meal_log."""
    preset = get_preset(name, paths=paths)
    if not preset:
        return {
            "ok": False,
            "reason": "preset_unknown",
            "ask": f"I don't have a preset called {name!r} yet. Create a meal and save it?",
            "name": name,
        }
    lines: list[dict[str, Any]] = []
    for comp in preset.get("components") or []:
        if not isinstance(comp, dict):
            continue
        line = {
            "display_name": comp.get("display_name") or comp.get("label") or preset.get("display_name"),
            "ref_id": comp.get("ref_id"),
            "preset_id": preset.get("id"),
            "serving_qty": comp.get("serving_qty", 1),
            "serving_unit": comp.get("serving_unit") or "serving",
            "serving_grams": comp.get("serving_grams"),
            "provenance": comp.get("provenance")
            or preset.get("provenance")
            or "custom",
        }
        if comp.get("nutrients"):
            line["nutrients"] = comp["nutrients"]
        if comp.get("snapshot_json"):
            line["snapshot_json"] = comp["snapshot_json"]
        lines.append(line)
    if not lines:
        return {"ok": False, "reason": "preset_empty", "preset_id": preset.get("id")}
    return {
        "ok": True,
        "preset_id": preset.get("id"),
        "display_name": preset.get("display_name"),
        "lines": lines,
        "provenance": preset.get("provenance"),
    }
