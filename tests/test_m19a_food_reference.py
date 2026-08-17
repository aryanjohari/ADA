"""M19a Slice 1 — food reference cache and lookup tests."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from ada.io.paths import get_paths
from ada.logs.food import (
    barcode_lookup,
    forget_foods,
    insert_food,
    search_foods,
    search_foods_resolved,
    fetch_usda_detail,
    fetch_usda_search,
)
from ada.logs.gym_import import import_exercise_seed
from ada.tools.gateway import Gateway
from ada.tools.toolspec import SPECS_BY_NAME


def test_local_cache_hit(data_root: Path) -> None:
    insert_food(
        name="Oats rolled",
        source="custom",
        nutrients_per_100g={"energy_kcal": 389, "protein_g": 17},
        paths=get_paths(),
    )
    hits = search_foods("oats", paths=get_paths())
    assert len(hits) >= 1
    assert "oats" in hits[0]["name"].lower()


def test_barcode_miss_honest(data_root: Path) -> None:
    result = barcode_lookup("0000000000000", fetch_remote=False, paths=get_paths())
    assert result["ok"] is False
    assert result["reason"] == "barcode_miss"


def test_barcode_cache_hit(data_root: Path) -> None:
    paths = get_paths()
    insert_food(
        name="Test Bar",
        source="off",
        barcode="1234567890123",
        nutrients_per_100g={"energy_kcal": 200},
        paths=paths,
    )
    result = barcode_lookup("1234567890123", fetch_remote=False, paths=paths)
    assert result["ok"] is True
    assert result["from_cache"] is True
    assert result["provenance"] == "verified"


def test_barcode_off_fetch_mock(data_root: Path, monkeypatch) -> None:
    paths = get_paths()

    def fake_get(url, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "status": 1,
            "product": {
                "product_name": "Mock Cereal",
                "brands": "TestCo",
                "nutriments": {
                    "energy-kcal_100g": 350,
                    "proteins_100g": 8,
                    "fat_100g": 2,
                    "carbohydrates_100g": 70,
                },
            },
        }
        return resp

    result = barcode_lookup(
        "9998887776665",
        fetch_remote=True,
        paths=paths,
        http_get=fake_get,
    )
    assert result["ok"] is True
    assert result["from_cache"] is False
    assert result["name"] == "Mock Cereal"
    assert result["fetch_provider"] == "open_food_facts"


def test_gateway_life_food_search(data_root: Path) -> None:
    insert_food(name="Banana", source="manual", paths=get_paths())
    gw = Gateway(mode="observe")
    obs = gw.execute("life_food_search", {"query": "banana", "fetch_remote": False})
    assert obs.ok
    assert obs.data["candidates"]


def test_life_tools_registered() -> None:
    assert "life_food_search" in SPECS_BY_NAME
    assert "life_barcode_lookup" in SPECS_BY_NAME
    assert "life_gym_status" in SPECS_BY_NAME


def test_forget_foods_custom_only(data_root: Path) -> None:
    paths = get_paths()
    custom = insert_food(
        name="Banana",
        source="custom",
        nutrients_per_100g={"energy_kcal": 89, "protein_g": 1.1, "carb_g": 22.8},
        paths=paths,
    )
    usda = insert_food(
        name="Bananas, raw",
        source="usda_fdc",
        external_id="173944",
        nutrients_per_100g={"energy_kcal": 89, "protein_g": 1.1},
        paths=paths,
    )
    result = forget_foods("banana", source="custom", paths=paths)
    assert result["ok"] is True
    assert result["deleted"] == 1
    assert result["rows"][0]["ref_id"] == custom["food_ref_id"]
    remaining = search_foods("banana", paths=paths)
    ids = {row["ref_id"] for row in remaining}
    assert usda["food_ref_id"] in ids
    assert custom["food_ref_id"] not in ids


def test_thin_custom_treated_as_miss_when_usda_present(
    data_root: Path, monkeypatch
) -> None:
    paths = get_paths()
    insert_food(
        name="Banana",
        source="custom",
        nutrients_per_100g={"energy_kcal": 89, "protein_g": 1.1, "carb_g": 22.8},
        paths=paths,
    )

    def fake_usda(query, **kwargs):
        return {
            "name": "Bananas, raw",
            "brand": None,
            "source": "usda_fdc",
            "external_id": "173944",
            "barcode": None,
            "nutrients_per_100g": {
                "energy_kcal": 89.0,
                "protein_g": 1.1,
                "carb_g": 22.8,
            },
            "provenance": "api",
        }

    monkeypatch.setattr("ada.logs.food.fetch_usda_search", fake_usda)
    hits = search_foods_resolved("banana", fetch_remote=True, paths=paths)
    assert hits
    assert hits[0]["source"] == "usda_fdc"


def test_gym_import_wger_shape(data_root: Path, tmp_path: Path) -> None:
    wger = tmp_path / "wger.json"
    wger.write_text(
        json.dumps(
            [
                {
                    "id": 99,
                    "name": "Test push-up",
                    "muscles": ["Chest"],
                    "equipment": ["bodyweight"],
                    "category": "push",
                }
            ]
        ),
        encoding="utf-8",
    )
    result = import_exercise_seed(path=wger, paths=get_paths())
    assert result["ok"] is True
    assert result["imported"] == 1


def test_food_forget_cli_json(data_root: Path) -> None:
    from typer.testing import CliRunner

    from ada.cli.main import app

    insert_food(
        name="Banana",
        source="custom",
        nutrients_per_100g={"energy_kcal": 89},
        paths=get_paths(),
    )
    runner = CliRunner()
    result = runner.invoke(app, ["life", "food-forget", "--name", "banana", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["deleted"] == 1
    assert "/mnt/ada-data" not in result.output


def test_usda_detail_populates_calcium_iron(data_root: Path) -> None:
    paths = get_paths()

    def fake_get(url, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        if "foods/search" in str(url):
            resp.json.return_value = {
                "foods": [{"fdcId": 173944, "description": "Bananas, raw"}]
            }
        else:
            resp.json.return_value = {
                "fdcId": 173944,
                "description": "Bananas, raw",
                "foodNutrients": [
                    {"nutrientId": 1008, "value": 89},
                    {"nutrientId": 1003, "value": 1.1},
                    {"nutrientId": 1087, "value": 5.0},
                    {"nutrientId": 1089, "value": 0.26},
                    {"nutrientId": 1162, "value": 8.7},
                ],
            }
        return resp

    hit = fetch_usda_search("banana", api_key="test-key", http_get=fake_get)
    assert hit is not None
    nutrients = hit["nutrients_per_100g"]
    assert nutrients.get("calcium_mg") == 5.0
    assert nutrients.get("iron_mg") == 0.26
    assert nutrients.get("vitamin_c_mg") == 8.7
    assert hit["provenance"] == "api_detail"

    detail = fetch_usda_detail(173944, api_key="test-key", http_get=fake_get)
    assert detail is not None
    assert detail["nutrients_per_100g"]["calcium_mg"] == 5.0


def test_meal_snapshot_unchanged_after_cache_update(data_root: Path) -> None:
    from ada.logs.connection import open_life_db
    from ada.tools.gateway import Gateway

    paths = get_paths()
    thin = insert_food(
        name="Bananas, raw",
        source="usda_fdc",
        external_id="173944",
        nutrients_per_100g={
            "energy_kcal": 89.0,
            "protein_g": 1.1,
            "calcium_mg": None,
            "iron_mg": None,
        },
        paths=paths,
    )
    gw = Gateway(mode="agent")
    gw.execute(
        "life_meal_log",
        {
            "lines": [
                {
                    "display_name": "Bananas, raw",
                    "ref_id": thin["food_ref_id"],
                    "provenance": "usda_fdc",
                    "serving_grams": 100,
                    "nutrients": {
                        "energy_kcal": 89.0,
                        "protein_g": 1.1,
                        "calcium_mg": None,
                        "iron_mg": None,
                    },
                }
            ]
        },
    )
    with open_life_db(paths=paths) as conn:
        before = conn.execute(
            "SELECT snapshot_json FROM meal_foods ORDER BY line_id LIMIT 1"
        ).fetchone()
    before_snap = json.loads(before["snapshot_json"])

    insert_food(
        name="Bananas, raw",
        source="usda_fdc",
        external_id="173944",
        nutrients_per_100g={
            "energy_kcal": 89.0,
            "protein_g": 1.1,
            "calcium_mg": 5.0,
            "iron_mg": 0.26,
        },
        paths=paths,
    )
    with open_life_db(paths=paths) as conn:
        after = conn.execute(
            "SELECT snapshot_json FROM meal_foods ORDER BY line_id LIMIT 1"
        ).fetchone()
    after_snap = json.loads(after["snapshot_json"])
    assert before_snap == after_snap
    assert before_snap["nutrients"].get("calcium_mg") is None

