"""Operator gym split FACT — teach-in-flow Confirm write (M22). No hardcoded PPL."""

from __future__ import annotations

from typing import Any

from ada.io.atomic import atomic_write_text
from ada.io.paths import BodyFault, DataPaths, ada_data_mounted, require_ada_data
from ada.memory.facts import _dump_yaml, _load_yaml, get_fact

_SPLIT_DOC = "gym_split"
_DAY_KEYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
# Invite real labels on Confirm — not baked biography (F-M22-6).
_LABEL_HINT = "Fill day labels (e.g. Push / Pull / Legs / Rest) — empty shell rejected"


def _require(paths: DataPaths | None = None) -> DataPaths:
    p = paths or require_ada_data()
    if not ada_data_mounted(p.root):
        raise BodyFault("ADA data not mounted", code=2)
    p.ensure_memory_dirs()
    return p


def split_path(*, paths: DataPaths | None = None):
    return _require(paths).facts / f"{_SPLIT_DOC}.yaml"


def has_gym_split(*, paths: DataPaths | None = None) -> bool:
    hit = get_fact(_SPLIT_DOC, paths=paths or require_ada_data())
    if not hit.get("found"):
        return False
    value = hit.get("value")
    if not isinstance(value, dict):
        return False
    days = value.get("days")
    return isinstance(days, dict)


def empty_day_slots() -> dict[str, dict[str, Any]]:
    """Schema-shaped weekday slots only — no Push/Pull/Legs biography."""
    return {d: {"label": "", "body_parts": []} for d in _DAY_KEYS}


def _normalize_days(raw: Any) -> dict[str, dict[str, Any]] | None:
    if not isinstance(raw, dict):
        return None
    out: dict[str, dict[str, Any]] = {}
    for key, row in raw.items():
        day = str(key or "").strip().lower()[:3]
        if day not in _DAY_KEYS:
            # Allow full names mon/monday → mon
            full = str(key or "").strip().lower()
            day = full[:3] if full[:3] in _DAY_KEYS else ""
            if not day:
                continue
        if not isinstance(row, dict):
            continue
        label = str(row.get("label") or "").strip()
        parts_raw = row.get("body_parts") or row.get("muscles") or []
        if isinstance(parts_raw, str):
            parts = [p.strip() for p in parts_raw.split(",") if p.strip()]
        elif isinstance(parts_raw, list):
            parts = [str(p).strip() for p in parts_raw if str(p).strip()]
        else:
            parts = []
        out[day] = {"label": label, "body_parts": parts}
    return out


def _has_labeled_day(days: dict[str, dict[str, Any]]) -> bool:
    return any(str((row or {}).get("label") or "").strip() for row in days.values())


def set_gym_split(
    *,
    days: dict[str, Any] | None = None,
    confirmed: bool = False,
    schema_version: int = 1,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    """Write gym_split FACT only after Confirm Yes (confirmed=true).

    Rejects all-empty label shells — do not sticky a useless FACT (phone H3).
    """
    normalized = _normalize_days(days if days is not None else {})
    if normalized is None:
        return {"ok": False, "reason": "days_must_be_object"}
    proposed = normalized if normalized else empty_day_slots()
    if not confirmed:
        return {
            "ok": False,
            "needs_confirm": True,
            "outcome": "needs_confirm",
            "reason": "gym_split_requires_confirm",
            "days": proposed,
            "label_hint": _LABEL_HINT,
            "schema_version": int(schema_version or 1),
        }
    if not _has_labeled_day(proposed):
        # Re-ask — never write empty mon–sun shell.
        return {
            "ok": False,
            "needs_confirm": True,
            "outcome": "needs_confirm",
            "reason": "empty_split_labels",
            "days": proposed if proposed else empty_day_slots(),
            "label_hint": _LABEL_HINT,
            "schema_version": int(schema_version or 1),
        }
    p = _require(paths)
    doc = {
        "schema_version": int(schema_version or 1),
        "days": proposed,
    }
    path = split_path(paths=p)
    atomic_write_text(path, _dump_yaml(doc))
    return {
        "ok": True,
        "path": str(path),
        "gym_split": doc,
        "schema_version": doc["schema_version"],
        "days": proposed,
    }
