"""Operator nutrition favorites — FACTS YAML, not Dream-whitelist (M21)."""

from __future__ import annotations

from typing import Any

from ada.body.vitals import utc_now_iso
from ada.harness.resolve_gate import normalize_query
from ada.io.atomic import atomic_write_text
from ada.io.paths import BodyFault, DataPaths, ada_data_mounted, require_ada_data
from ada.memory.facts import _dump_yaml, _load_yaml

_FAVORITES_DOC = "nutrition_favorites"


def _require(paths: DataPaths | None = None) -> DataPaths:
    p = paths or require_ada_data()
    if not ada_data_mounted(p.root):
        raise BodyFault("ADA data not mounted", code=2)
    p.ensure_memory_dirs()
    return p


def favorites_path(*, paths: DataPaths | None = None):
    return _require(paths).facts / f"{_FAVORITES_DOC}.yaml"


def load_favorites(*, paths: DataPaths | None = None) -> dict[str, Any]:
    path = favorites_path(paths=paths)
    raw = _load_yaml(path) if path.is_file() else {}
    doc = dict(raw or {})
    doc.setdefault("schema_version", 1)
    doc.setdefault("favorites", {})
    if not isinstance(doc["favorites"], dict):
        doc["favorites"] = {}
    return doc


def get_favorite(query: str, *, paths: DataPaths | None = None) -> dict[str, Any] | None:
    q = normalize_query(query)
    if not q:
        return None
    favs = load_favorites(paths=paths).get("favorites") or {}
    hit = favs.get(q)
    if isinstance(hit, dict) and hit.get("ref_id"):
        return {**hit, "query_norm": q}
    return None


def resolve_favorite_bind(
    query: str, *, paths: DataPaths | None = None
) -> tuple[dict[str, Any] | None, list[str]]:
    """Return sticky favorite for bind, or None if missing/broken after cache wipe.

    When FACTS points at a ref_id absent from food_reference.db, do **not** silent-
    bind — caller must Confirm + re-bind (M26 library harden).
    """
    fav = get_favorite(query, paths=paths)
    if not fav:
        return None, []
    rid = str(fav.get("ref_id") or "").strip()
    if not rid:
        return None, []
    from ada.logs import food as food_mod

    row = food_mod.get_food(rid, paths=paths)
    if not row:
        return None, ["favorite_ref_missing"]
    return {**fav, "ref_id": rid}, []


def set_favorite(
    *,
    query: str,
    ref_id: str,
    label: str | None = None,
    brand: str | None = None,
    confirmed: bool = False,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    """Write favorite only after Confirm Yes or explicit save (confirmed=true)."""
    q = normalize_query(query)
    rid = (ref_id or "").strip()
    if not q or not rid:
        return {"ok": False, "reason": "query_and_ref_id_required"}
    if not confirmed:
        return {
            "ok": False,
            "needs_confirm": True,
            "outcome": "needs_confirm",
            "reason": "favorite_requires_confirm",
            "query": query,
            "query_norm": q,
            "ref_id": rid,
            "label": label,
            "brand": brand,
        }
    p = _require(paths)
    doc = load_favorites(paths=p)
    entry = {
        "ref_id": rid,
        "label": label or q,
        "brand": brand,
        "source": "operator",
        "at": utc_now_iso(),
    }
    doc["favorites"][q] = entry
    path = favorites_path(paths=p)
    atomic_write_text(path, _dump_yaml(doc))
    return {"ok": True, "query_norm": q, "favorite": entry, "path": str(path)}


def delete_favorite(
    query: str,
    *,
    confirmed: bool = False,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    q = normalize_query(query)
    if not q:
        return {"ok": False, "reason": "query_required"}
    if not confirmed:
        return {
            "ok": False,
            "needs_confirm": True,
            "outcome": "needs_confirm",
            "reason": "favorite_delete_requires_confirm",
            "query_norm": q,
        }
    p = _require(paths)
    doc = load_favorites(paths=p)
    favs = doc.get("favorites") or {}
    removed = favs.pop(q, None)
    doc["favorites"] = favs
    path = favorites_path(paths=p)
    atomic_write_text(path, _dump_yaml(doc))
    return {"ok": True, "query_norm": q, "deleted": removed is not None, "path": str(path)}
