"""Food reference cache — search, barcode, nutrients (M19a)."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any, Callable

import httpx

from ada.body.vitals import utc_now_iso
from ada.io.paths import DataPaths
from ada.logs.connection import open_food_db
from ada.secrets.usda import load_usda_fdc_api_key

# DRI-relevant slots — honest_partial when any CORE slot is null on a line.
CORE_NUTRIENT_IDS = (
    "energy_kcal",
    "protein_g",
    "fat_g",
    "carb_g",
    "fiber_g",
    "sugar_g",
    "saturated_fat_g",
    "cholesterol_mg",
    "sodium_mg",
    "potassium_mg",
    "calcium_mg",
    "iron_mg",
    "magnesium_mg",
    "phosphorus_mg",
    "zinc_mg",
    "copper_mg",
    "manganese_mg",
    "selenium_ug",
    "iodine_ug",
    "chloride_mg",
    "vitamin_a_rae_ug",
    "vitamin_c_mg",
    "vitamin_d_ug",
    "vitamin_e_mg",
    "vitamin_k_ug",
    "thiamin_mg",
    "riboflavin_mg",
    "niacin_mg",
    "pantothenic_mg",
    "vitamin_b6_mg",
    "folate_ug",
    "vitamin_b12_ug",
)
# Additional §5 slots cached when FDC returns them (not required for honest_partial).
EXTENDED_NUTRIENT_IDS = (
    "water_g",
    "alcohol_g",
    "ash_g",
    "added_sugar_g",
    "starch_g",
    "monounsaturated_fat_g",
    "polyunsaturated_fat_g",
    "trans_fat_g",
    "omega3_g",
    "omega6_g",
    "caffeine_mg",
    "retinol_ug",
    "beta_carotene_ug",
)
TRACKED_NUTRIENT_IDS = tuple(dict.fromkeys(CORE_NUTRIENT_IDS + EXTENDED_NUTRIENT_IDS))
_MACRO_IDS = ("energy_kcal", "protein_g", "fat_g", "carb_g")
_CORE_MICRO_IDS = (
    "calcium_mg",
    "iron_mg",
    "magnesium_mg",
    "phosphorus_mg",
    "potassium_mg",
    "zinc_mg",
    "vitamin_c_mg",
    "vitamin_d_ug",
    "vitamin_a_rae_ug",
    "folate_ug",
    "vitamin_b12_ug",
)
# USDA FDC nutrient.id → internal slot (M19a §5).
FDC_NUTRIENT_MAP: dict[int, str] = {
    1008: "energy_kcal",
    1003: "protein_g",
    1004: "fat_g",
    1005: "carb_g",
    1079: "fiber_g",
    1051: "water_g",
    1018: "alcohol_g",
    1007: "ash_g",
    2000: "sugar_g",
    1235: "added_sugar_g",
    1009: "starch_g",
    1258: "saturated_fat_g",
    1292: "monounsaturated_fat_g",
    1293: "polyunsaturated_fat_g",
    1257: "trans_fat_g",
    1253: "cholesterol_mg",
    1404: "omega3_g",
    1406: "omega6_g",
    1057: "caffeine_mg",
    1087: "calcium_mg",
    1089: "iron_mg",
    1090: "magnesium_mg",
    1091: "phosphorus_mg",
    1092: "potassium_mg",
    1093: "sodium_mg",
    1095: "zinc_mg",
    1098: "copper_mg",
    1101: "manganese_mg",
    1103: "selenium_ug",
    1100: "iodine_ug",
    1088: "chloride_mg",
    1106: "vitamin_a_rae_ug",
    1105: "retinol_ug",
    1107: "beta_carotene_ug",
    1162: "vitamin_c_mg",
    1114: "vitamin_d_ug",
    1109: "vitamin_e_mg",
    1185: "vitamin_k_ug",
    1165: "thiamin_mg",
    1166: "riboflavin_mg",
    1167: "niacin_mg",
    1170: "pantothenic_mg",
    1175: "vitamin_b6_mg",
    1177: "folate_ug",
    1178: "vitamin_b12_ug",
}
_PROTECTED_FOOD_SOURCES = frozenset({"usda_fdc", "off", "nz_foodfiles"})

OFF_PRODUCT_URL = "https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
USDA_SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
USDA_FOOD_URL = "https://api.nal.usda.gov/fdc/v1/food/{fdc_id}"


def core_nutrients_partial(nutrients: dict[str, Any]) -> bool:
    """True when any CORE slot is missing or null."""
    return any(nutrients.get(k) is None for k in CORE_NUTRIENT_IDS)


def _normalize_nutrients(raw: dict[str, Any]) -> dict[str, float | None]:
    out: dict[str, float | None] = {k: None for k in TRACKED_NUTRIENT_IDS}
    for key, val in raw.items():
        if key in out and val is not None:
            try:
                out[key] = float(val)
            except (TypeError, ValueError):
                out[key] = None
    return out


def insert_food(
    *,
    name: str,
    source: str,
    external_id: str | None = None,
    barcode: str | None = None,
    brand: str | None = None,
    nutrients_per_100g: dict[str, Any] | None = None,
    default_serving_g: float | None = None,
    meta: dict[str, Any] | None = None,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    food_ref_id = uuid.uuid4().hex
    now = utc_now_iso()
    nutrients_json = json.dumps(
        _normalize_nutrients(nutrients_per_100g or {}),
        separators=(",", ":"),
    )
    with open_food_db(paths=paths) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO foods (
              food_ref_id, source, external_id, barcode, name, brand,
              default_serving_g, nutrients_per_100g_json, meta_json, imported_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                food_ref_id,
                source,
                external_id,
                barcode,
                name,
                brand,
                default_serving_g,
                nutrients_json,
                json.dumps(meta or {}, separators=(",", ":")),
                now,
            ),
        )
    return {"food_ref_id": food_ref_id, "name": name, "source": source}


def search_foods(
    query: str,
    *,
    limit: int = 10,
    paths: DataPaths | None = None,
) -> list[dict[str, Any]]:
    q = (query or "").strip()
    if not q:
        return []
    tokens = [t for t in re.split(r"\W+", q.lower()) if t]
    if not tokens:
        return []
    with open_food_db(paths=paths) as conn:
        rows = conn.execute(
            "SELECT food_ref_id, name, brand, source, barcode, nutrients_per_100g_json FROM foods"
        ).fetchall()
    scored: list[tuple[float, dict[str, Any]]] = []
    for row in rows:
        hay = f"{row['name']} {row['brand'] or ''}".lower()
        score = sum(1 for t in tokens if t in hay) / len(tokens)
        if score > 0:
            nutrients = json.loads(row["nutrients_per_100g_json"] or "{}")
            scored.append(
                (
                    score,
                    {
                        "ref_id": row["food_ref_id"],
                        "name": row["name"],
                        "brand": row["brand"],
                        "source": row["source"],
                        "barcode": row["barcode"],
                        "score": round(score, 3),
                        "nutrients": nutrients,
                    },
                )
            )
    scored.sort(key=lambda x: (-x[0], x[1]["name"]))
    return [item for _, item in scored[:limit]]


def get_by_barcode(
    barcode: str,
    *,
    paths: DataPaths | None = None,
) -> dict[str, Any] | None:
    with open_food_db(paths=paths) as conn:
        row = conn.execute(
            "SELECT * FROM foods WHERE barcode = ?",
            (barcode.strip(),),
        ).fetchone()
    return dict(row) if row else None


def get_food(ref_id: str, *, paths: DataPaths | None = None) -> dict[str, Any] | None:
    with open_food_db(paths=paths) as conn:
        row = conn.execute("SELECT * FROM foods WHERE food_ref_id = ?", (ref_id.strip(),)).fetchone()
    return dict(row) if row else None


def _nutrients_of(row: dict[str, Any]) -> dict[str, Any]:
    if isinstance(row.get("nutrients"), dict):
        return row["nutrients"]
    raw = row.get("nutrients_per_100g_json")
    if isinstance(raw, str):
        return json.loads(raw or "{}")
    if isinstance(raw, dict):
        return raw
    return {}


def is_thin_custom_food(row: dict[str, Any]) -> bool:
    """True when source=custom and CORE slots are missing (macros-only stubs)."""
    if str(row.get("source") or "") != "custom":
        return False
    nutrients = _nutrients_of(row)
    missing_core = any(nutrients.get(k) is None for k in CORE_NUTRIENT_IDS)
    has_macro = any(nutrients.get(k) is not None for k in _MACRO_IDS)
    missing_micros = all(nutrients.get(k) is None for k in _CORE_MICRO_IDS)
    return missing_core or (has_macro and missing_micros)


def delete_food(ref_id: str, *, paths: DataPaths | None = None) -> dict[str, Any]:
    """Delete one food row by ref_id (any source)."""
    rid = (ref_id or "").strip()
    if not rid:
        return {"ok": False, "deleted": 0, "reason": "ref_id_required"}
    with open_food_db(paths=paths) as conn:
        row = conn.execute(
            "SELECT food_ref_id, name, source FROM foods WHERE food_ref_id = ?",
            (rid,),
        ).fetchone()
        if row is None:
            return {"ok": False, "deleted": 0, "reason": "not_found", "ref_id": rid}
        conn.execute("DELETE FROM foods WHERE food_ref_id = ?", (rid,))
    return {
        "ok": True,
        "deleted": 1,
        "ref_id": row["food_ref_id"],
        "name": row["name"],
        "source": row["source"],
    }


def forget_foods(
    name: str,
    *,
    source: str = "custom",
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    """Delete local cache rows by name match. Custom only — never usda_fdc/off by name."""
    query = (name or "").strip()
    src = (source or "custom").strip()
    if src != "custom":
        return {
            "ok": False,
            "deleted": 0,
            "reason": "source_not_custom",
            "query": query,
        }
    if not query:
        return {"ok": False, "deleted": 0, "reason": "name_required"}
    hits = search_foods(query, paths=paths)
    deleted: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for hit in hits:
        hit_source = str(hit.get("source") or "")
        if hit_source in _PROTECTED_FOOD_SOURCES or hit_source != "custom":
            skipped.append(
                {
                    "ref_id": hit.get("ref_id"),
                    "name": hit.get("name"),
                    "source": hit_source,
                    "reason": "name_match_protected",
                }
            )
            continue
        result = delete_food(str(hit.get("ref_id") or ""), paths=paths)
        if result.get("ok"):
            deleted.append(result)
    return {
        "ok": True,
        "deleted": len(deleted),
        "rows": deleted,
        "skipped": skipped,
        "query": query,
        "source": "custom",
    }


def search_foods_resolved(
    query: str,
    *,
    limit: int = 10,
    fetch_remote: bool = True,
    paths: DataPaths | None = None,
    http_get: Callable[..., httpx.Response] | None = None,
) -> list[dict[str, Any]]:
    """Local search; thin custom-only hits count as a miss for USDA when key present."""
    candidates = search_foods(query, limit=limit, paths=paths)
    only_thin_custom = bool(candidates) and all(is_thin_custom_food(c) for c in candidates)
    if fetch_remote and str(query or "").strip() and (not candidates or only_thin_custom):
        hit = fetch_usda_search(str(query), http_get=http_get)
        if hit:
            inserted = insert_food(
                name=hit["name"],
                source=hit["source"],
                external_id=hit.get("external_id"),
                brand=hit.get("brand"),
                nutrients_per_100g=hit.get("nutrients_per_100g"),
                paths=paths,
            )
            usda = {
                "ref_id": inserted["food_ref_id"],
                "name": inserted["name"],
                "source": inserted["source"],
                "score": 1.0,
                "nutrients": hit.get("nutrients_per_100g") or {},
            }
            kept = [c for c in candidates if not is_thin_custom_food(c)]
            candidates = [usda] + kept
    candidates.sort(
        key=lambda c: (
            1 if is_thin_custom_food(c) else 0,
            -float(c.get("score") or 0),
            str(c.get("name") or ""),
        )
    )
    return candidates[:limit]


def build_snapshot_from_food(row: dict[str, Any], *, provider: str) -> dict[str, Any]:
    nutrients = json.loads(row.get("nutrients_per_100g_json") or "{}")
    return {
        "schema_version": 1,
        "nutrients": nutrients,
        "source": {
            "provider": provider,
            "external_id": row.get("external_id"),
            "fetched_at": utc_now_iso(),
        },
    }


def _parse_off_nutrients(product: dict[str, Any]) -> dict[str, float | None]:
    n = product.get("nutriments") or {}
    mapping = {
        "energy_kcal": n.get("energy-kcal_100g") or n.get("energy-kcal"),
        "protein_g": n.get("proteins_100g"),
        "fat_g": n.get("fat_100g"),
        "carb_g": n.get("carbohydrates_100g"),
        "fiber_g": n.get("fiber_100g"),
        "sugar_g": n.get("sugars_100g"),
        "sodium_mg": (n.get("sodium_100g") or 0) * 1000 if n.get("sodium_100g") else None,
    }
    return _normalize_nutrients(mapping)


def fetch_off_barcode(
    barcode: str,
    *,
    http_get: Callable[..., httpx.Response] | None = None,
) -> dict[str, Any] | None:
    url = OFF_PRODUCT_URL.format(barcode=barcode)
    get = http_get or httpx.get
    resp = get(url, timeout=10.0, headers={"User-Agent": "ADA/1.0"})
    if resp.status_code != 200:
        return None
    data = resp.json()
    if data.get("status") != 1:
        return None
    product = data.get("product") or {}
    name = product.get("product_name") or product.get("generic_name") or "unknown"
    nutrients = _parse_off_nutrients(product)
    return {
        "name": name,
        "brand": product.get("brands"),
        "source": "off",
        "external_id": barcode,
        "barcode": barcode,
        "nutrients_per_100g": nutrients,
        "provenance": "barcode",
    }


def _parse_fdc_food_nutrients(item: dict[str, Any]) -> dict[str, float | None]:
    nutrients: dict[str, float | None] = {k: None for k in TRACKED_NUTRIENT_IDS}
    for n in item.get("foodNutrients") or []:
        nid = n.get("nutrientId") or n.get("nutrientNumber")
        if nid is None:
            continue
        try:
            slot = FDC_NUTRIENT_MAP.get(int(nid))
        except (TypeError, ValueError):
            continue
        if not slot:
            continue
        try:
            nutrients[slot] = float(n.get("value") or n.get("amount") or 0)
        except (TypeError, ValueError):
            pass
    return nutrients


def fetch_usda_detail(
    fdc_id: str | int,
    *,
    api_key: str | None = None,
    http_get: Callable[..., httpx.Response] | None = None,
) -> dict[str, Any] | None:
    """Full FDC food payload — preferred for nutrient completeness."""
    key = api_key or load_usda_fdc_api_key(required=False)
    if not key:
        return None
    fid = str(fdc_id).strip()
    if not fid:
        return None
    get = http_get or httpx.get
    resp = get(
        USDA_FOOD_URL.format(fdc_id=fid),
        params={"api_key": key},
        timeout=15.0,
    )
    if resp.status_code != 200:
        return None
    item = resp.json()
    if not item or not item.get("fdcId"):
        return None
    nutrients = _parse_fdc_food_nutrients(item)
    return {
        "name": item.get("description") or fid,
        "brand": item.get("brandOwner"),
        "source": "usda_fdc",
        "external_id": str(item.get("fdcId") or fid),
        "barcode": None,
        "nutrients_per_100g": nutrients,
        "provenance": "api_detail",
    }


def fetch_usda_search(
    query: str,
    *,
    api_key: str | None = None,
    http_get: Callable[..., httpx.Response] | None = None,
) -> dict[str, Any] | None:
    """Search for discovery; prefer detail endpoint before cache insert."""
    key = api_key or load_usda_fdc_api_key(required=False)
    if not key:
        return None
    params = {"api_key": key, "query": query, "pageSize": 1}
    get = http_get or httpx.get
    resp = get(USDA_SEARCH_URL, params=params, timeout=15.0)
    if resp.status_code != 200:
        return None
    data = resp.json()
    foods = data.get("foods") or []
    if not foods:
        return None
    item = foods[0]
    fdc_id = item.get("fdcId")
    if fdc_id is not None:
        detail = fetch_usda_detail(fdc_id, api_key=key, http_get=get)
        if detail:
            return detail
    nutrients = _parse_fdc_food_nutrients(item)
    return {
        "name": item.get("description") or query,
        "brand": item.get("brandOwner"),
        "source": "usda_fdc",
        "external_id": str(fdc_id or ""),
        "barcode": None,
        "nutrients_per_100g": nutrients,
        "provenance": "api_search",
    }


def barcode_lookup(
    barcode: str,
    *,
    paths: DataPaths | None = None,
    fetch_remote: bool = True,
    http_get: Callable[..., httpx.Response] | None = None,
) -> dict[str, Any]:
    code = (barcode or "").strip()
    if not code:
        return {"ok": False, "reason": "barcode_required"}
    cached = get_by_barcode(code, paths=paths)
    if cached:
        return {
            "ok": True,
            "ref_id": cached["food_ref_id"],
            "name": cached["name"],
            "source": cached["source"],
            "from_cache": True,
            "nutrients_preview": json.loads(cached["nutrients_per_100g_json"] or "{}"),
            "provenance": "verified" if cached["source"] in {"off", "usda_fdc"} else cached["source"],
        }
    if not fetch_remote:
        return {"ok": False, "reason": "barcode_miss"}
    hit = fetch_off_barcode(code, http_get=http_get)
    provider = "open_food_facts"
    if not hit:
        hit = fetch_usda_search(code, http_get=http_get)
        provider = "usda_fdc"
    if not hit:
        return {"ok": False, "reason": "barcode_miss"}
    inserted = insert_food(
        name=hit["name"],
        source=hit["source"],
        external_id=hit.get("external_id"),
        barcode=code,
        brand=hit.get("brand"),
        nutrients_per_100g=hit.get("nutrients_per_100g"),
        paths=paths,
    )
    return {
        "ok": True,
        "ref_id": inserted["food_ref_id"],
        "name": inserted["name"],
        "source": inserted["source"],
        "from_cache": False,
        "nutrients_preview": hit.get("nutrients_per_100g") or {},
        "provenance": "verified" if provider in {"open_food_facts", "usda_fdc"} else hit.get("provenance"),
        "fetch_provider": provider,
    }
