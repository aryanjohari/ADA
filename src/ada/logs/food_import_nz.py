"""NZ FOODfiles offline import (M19a — minimal CSV stub)."""

from __future__ import annotations

import csv
import uuid
from pathlib import Path
from typing import Any

from ada.body.vitals import utc_now_iso
from ada.io.paths import DataPaths
from ada.logs.connection import open_food_db


def import_nz_foodfiles(
    path: Path,
    *,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    """Import CSV rows from NZ FOODfiles directory (stub column map)."""
    root = Path(path)
    if not root.is_dir():
        return {"ok": False, "error": f"path not found: {root}"}
    csv_files = list(root.glob("*.csv"))
    if not csv_files:
        return {"ok": False, "error": "no CSV files found"}
    imported = 0
    now = utc_now_iso()
    with open_food_db(paths=paths) as conn:
        for csv_path in csv_files:
            with csv_path.open(encoding="utf-8-sig", newline="") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    name = (
                        row.get("Food name")
                        or row.get("food_name")
                        or row.get("name")
                        or row.get("Description")
                    )
                    if not name:
                        continue
                    ext_id = row.get("FoodID") or row.get("id") or name
                    nutrients = {}
                    if row.get("Energy (kJ)"):
                        try:
                            kj = float(row["Energy (kJ)"])
                            nutrients["energy_kcal"] = round(kj / 4.184, 2)
                        except (TypeError, ValueError):
                            pass
                    for col, slot in (
                        ("Protein", "protein_g"),
                        ("Total fat", "fat_g"),
                        ("Available carbohydrate", "carb_g"),
                        ("Dietary fibre", "fiber_g"),
                    ):
                        if row.get(col):
                            try:
                                nutrients[slot] = float(row[col])
                            except (TypeError, ValueError):
                                pass
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO foods (
                          food_ref_id, source, external_id, barcode, name, brand,
                          default_serving_g, nutrients_per_100g_json, meta_json, imported_at
                        ) VALUES (?, 'nz_foodfiles', ?, NULL, ?, NULL, 100, ?, '{}', ?)
                        """,
                        (
                            uuid.uuid4().hex,
                            str(ext_id),
                            name.strip(),
                            __import__("json").dumps(nutrients),
                            now,
                        ),
                    )
                    imported += 1
    return {"ok": True, "imported": imported, "files": len(csv_files)}
