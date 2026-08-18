"""Seed exercise catalog into life_logs.db (M19a)."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import tempfile
import uuid
from importlib.resources import files
from pathlib import Path
from typing import Any, Callable

import httpx

from ada.io.paths import DataPaths
from ada.logs.connection import open_life_db

logger = logging.getLogger(__name__)

ENV_GYM_CATALOG_FETCH = "ADA_GYM_CATALOG_FETCH"
FREE_EXERCISE_DB_URL = (
    "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/dist/exercises.json"
)


def _seed_path(name: str = "exercise_seed_min.json") -> Path:
    pkg = files("ada.logs.data")
    return Path(str(pkg / name))


def catalog_is_empty(conn: sqlite3.Connection) -> bool:
    row = conn.execute("SELECT COUNT(*) FROM exercise_catalog").fetchone()
    return int(row[0]) == 0


def _fetch_enabled() -> bool:
    raw = os.environ.get(ENV_GYM_CATALOG_FETCH, "full").strip().lower()
    if raw in ("off", "0", "bundled", "false", "no"):
        return False
    return True


def fold_keys(name: str) -> frozenset[str]:
    """Alnum fold + light plural so pull-ups matches Pullups."""
    base = "".join(ch for ch in (name or "").lower() if ch.isalnum())
    if not base:
        return frozenset()
    keys = {base}
    if base.endswith("es") and len(base) > 4:
        keys.add(base[:-2])
    if base.endswith("s") and not base.endswith("ss") and len(base) > 3:
        keys.add(base[:-1])
    else:
        keys.add(base + "s")
    return frozenset(keys)


def names_fold_match(left: str, right: str) -> bool:
    return bool(fold_keys(left) & fold_keys(right))


def _uniq_aliases(canonical: str, aliases: list[str]) -> list[str]:
    seen = {canonical.strip().lower()}
    out: list[str] = []
    for raw in aliases:
        alias = str(raw).strip()
        if not alias:
            continue
        key = alias.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(alias)
    return out


def syntactic_aliases(name: str, external_id: str | None = None) -> list[str]:
    """Hyphen / space / plural variants from a catalog name or id."""
    seeds = [name]
    if external_id:
        pretty = str(external_id).replace("_", " ").replace("-", " ")
        if pretty.strip() and pretty.lower() != name.lower():
            seeds.append(pretty)
    variants: set[str] = set()
    for seed in seeds:
        s = str(seed).strip()
        if not s:
            continue
        variants.add(s)
        variants.add(s.replace("-", " "))
        variants.add(s.replace(" ", "-"))
        variants.add(s.replace("_", " "))
        variants.add(s.replace("_", "-"))
        compact = "".join(s.split())
        if compact != s:
            variants.add(compact)
        low = s.lower()
        glued = "-" not in s and " " not in s
        if glued and low.endswith("ups"):
            stem = s[:-3]
            variants.update(
                {
                    f"{stem}-ups",
                    f"{stem} ups",
                    f"{stem}-up",
                    f"{stem} up",
                    f"{stem}up",
                }
            )
        elif glued and low.endswith("up"):
            stem = s[:-2]
            variants.update(
                {f"{s}s", f"{stem}-up", f"{stem}-ups", f"{stem} ups", f"{stem}up"}
            )
    return _uniq_aliases(name, list(variants))


def fetch_free_exercise_db(
    *,
    dest: Path,
    url: str = FREE_EXERCISE_DB_URL,
    http_get: Callable[..., httpx.Response] | None = None,
) -> bool:
    """Download free-exercise-db JSON to *dest*. Returns False on any failure."""
    get = http_get or httpx.get
    try:
        resp = get(url, timeout=30.0, follow_redirects=True)
        if resp.status_code != 200:
            logger.warning("gym catalog fetch failed: HTTP %s", resp.status_code)
            return False
        dest.write_bytes(resp.content)
        return True
    except Exception as exc:
        logger.warning("gym catalog fetch failed: %s", exc)
        return False


_EQUIPMENT_MAP = {
    "body only": "bodyweight",
    "body": "bodyweight",
}


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


def _movement_from_item(item: dict[str, Any], name: str) -> str | None:
    force = item.get("force")
    if force:
        needle = str(force).lower()
        if needle in ("push", "pull"):
            return needle
        if needle == "static":
            return "other"
    low = name.lower()
    if "squat" in low:
        return "squat"
    if "deadlift" in low or "rdl" in low or "hinge" in low:
        return "hinge"
    category = item.get("category") or item.get("mechanic")
    return _movement_from_category(str(category) if category else None)


def _map_equipment(value: str) -> str:
    mapped = _EQUIPMENT_MAP.get(value.strip().lower())
    return mapped or value


def _collect_str_list(item: dict[str, Any], keys: tuple[str, ...]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for key in keys:
        raw = item.get(key)
        values: list[str] = []
        if isinstance(raw, list):
            values.extend(str(x) for x in raw if x)
        elif isinstance(raw, str) and raw.strip():
            values.append(raw.strip())
        for value in values:
            low = value.lower()
            if low in seen:
                continue
            seen.add(low)
            out.append(value)
    return out


def _normalize_external_item(item: dict[str, Any]) -> dict[str, Any] | None:
    """Map bundled seed, wger, or exercisedb-shaped JSON to catalog row."""
    if not isinstance(item, dict):
        return None
    if item.get("canonical_name"):
        name = str(item["canonical_name"])
        aliases = _uniq_aliases(
            name,
            list(item.get("aliases") or []) + syntactic_aliases(name, item.get("external_id")),
        )
        equipment = [_map_equipment(str(x)) for x in (item.get("equipment") or [])]
        return {
            "exercise_id": item.get("exercise_id"),
            "canonical_name": name,
            "aliases": aliases,
            "body_parts": list(item.get("body_parts") or []),
            "equipment": equipment,
            "movement": item.get("movement") or _movement_from_item(item, name),
            "source": item.get("source") or "seed",
            "external_id": item.get("external_id"),
        }
    name = item.get("name") or item.get("exercise_name")
    if not name:
        return None
    name = str(name)
    aliases = _collect_str_list(item, ("aliases", "alias"))
    external_id = item.get("external_id") or item.get("id")
    ext = str(external_id) if external_id is not None else None
    aliases = _uniq_aliases(name, aliases + syntactic_aliases(name, ext))
    body_parts = _collect_str_list(
        item,
        ("body_parts", "muscles", "primaryMuscles", "targetMuscles", "secondaryMuscles"),
    )
    equipment = [
        _map_equipment(x)
        for x in _collect_str_list(item, ("equipment", "equipments"))
    ]
    return {
        "exercise_id": item.get("exercise_id"),
        "canonical_name": name,
        "aliases": aliases,
        "body_parts": body_parts,
        "equipment": equipment,
        "movement": _movement_from_item(item, name),
        "source": item.get("source") or "import",
        "external_id": ext,
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


def _import_items_into_conn(
    conn: sqlite3.Connection,
    items: list[dict[str, Any]],
) -> dict[str, int]:
    imported = 0
    skipped = 0
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
    return {"imported": imported, "skipped": skipped}


def _import_from_file(conn: sqlite3.Connection, path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    items = _load_exercise_items(raw)
    counts = _import_items_into_conn(conn, items)
    return {"ok": True, "path": str(path), **counts}


def _merge_bundled_seed(conn: sqlite3.Connection) -> dict[str, int]:
    """Overlay bundled aliases onto fold-matches; insert unmatched seed rows."""
    items = _load_exercise_items(
        json.loads(_seed_path("exercise_seed.json").read_text(encoding="utf-8"))
    )
    existing = conn.execute("SELECT * FROM exercise_catalog").fetchall()
    index: list[tuple[frozenset[str], Any]] = []
    for row in existing:
        keys = fold_keys(row["canonical_name"])
        for alias in json.loads(row["aliases_json"] or "[]"):
            keys |= fold_keys(str(alias))
        index.append((keys, row))

    overlaid = 0
    inserted = 0
    for item in items:
        norm = _normalize_external_item(item)
        if not norm:
            continue
        keys = fold_keys(norm["canonical_name"])
        for alias in norm.get("aliases") or []:
            keys |= fold_keys(str(alias))
        match = None
        for existing_keys, row in index:
            if keys & existing_keys:
                match = row
                break
        if match is None:
            counts = _import_items_into_conn(conn, [item])
            inserted += counts["imported"]
            continue
        old_aliases = json.loads(match["aliases_json"] or "[]")
        merged = _uniq_aliases(
            match["canonical_name"],
            list(old_aliases)
            + [norm["canonical_name"]]
            + list(norm.get("aliases") or []),
        )
        movement = match["movement"]
        bundled_move = norm.get("movement")
        if (not movement or movement == "other") and bundled_move and bundled_move != "other":
            movement = bundled_move
        conn.execute(
            """
            UPDATE exercise_catalog
            SET aliases_json = ?, movement = ?
            WHERE exercise_id = ?
            """,
            (json.dumps(merged), movement, match["exercise_id"]),
        )
        overlaid += 1
    return {"overlaid": overlaid, "inserted": inserted}


def _import_bundled_seed(conn: sqlite3.Connection) -> dict[str, Any]:
    result = _import_from_file(conn, _seed_path("exercise_seed.json"))
    result["source"] = "bundled"
    return result


def ensure_exercise_catalog(
    conn: sqlite3.Connection,
    *,
    paths: DataPaths | None = None,
    http_get: Callable[..., httpx.Response] | None = None,
) -> dict[str, Any] | None:
    """Populate exercise_catalog when empty. Idempotent no-op if rows exist."""
    if not catalog_is_empty(conn):
        return None

    tmp_path: Path | None = None
    try:
        if _fetch_enabled() and paths is not None:
            paths.ensure_logs_dirs()
            fd, tmp_name = tempfile.mkstemp(
                suffix=".json",
                prefix="free-exercise-db-",
                dir=str(paths.logs),
            )
            os.close(fd)
            tmp_path = Path(tmp_name)
            if fetch_free_exercise_db(dest=tmp_path, http_get=http_get):
                try:
                    result = _import_from_file(conn, tmp_path)
                    if result["imported"] > 0:
                        result["source"] = "remote"
                        result["bundled_merge"] = _merge_bundled_seed(conn)
                        return result
                    logger.warning(
                        "gym catalog remote import produced no rows; using bundled seed"
                    )
                except Exception as exc:
                    logger.warning("gym catalog remote import failed: %s", exc)
            else:
                logger.info("gym catalog: fetch failed; falling back to bundled seed")

        return _import_bundled_seed(conn)
    finally:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def import_exercise_seed(
    *,
    path: Path | None = None,
    paths: DataPaths | None = None,
    seed_name: str = "exercise_seed.json",
) -> dict[str, Any]:
    src = path or _seed_path(seed_name)
    with open_life_db(paths=paths) as conn:
        result = _import_from_file(conn, src)
    return {"ok": True, **result}
