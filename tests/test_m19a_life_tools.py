"""M19a Slice 2 — life tools gateway and write tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ada.io.paths import get_paths
from ada.logs.connection import open_life_db
from ada.logs.gym_import import import_exercise_seed
from ada.tools.gateway import Gateway
from ada.tools.toolspec import SPECS_BY_NAME, WRITE_TOOL_NAMES, function_declarations


@pytest.fixture
def seeded_gym(data_root: Path) -> None:
    import_exercise_seed(paths=get_paths())


def test_observe_denies_meal_log(data_root: Path) -> None:
    gw = Gateway(mode="observe")
    obs = gw.execute("life_meal_log", {"lines": [{"display_name": "x"}]})
    assert not obs.ok
    assert obs.outcome == "denied"


def test_observe_allows_nutrition_day(data_root: Path) -> None:
    gw = Gateway(mode="observe")
    obs = gw.execute("life_nutrition_day", {})
    assert obs.ok


def test_meal_log_receipt_and_snapshot(data_root: Path) -> None:
    gw = Gateway(mode="agent")
    lines = [
        {
            "display_name": "banana",
            "serving_qty": 1,
            "serving_unit": "piece",
            "provenance": "manual",
            "nutrients": {
                "energy_kcal": 105,
                "protein_g": 1.3,
                "carb_g": 27,
                "fat_g": 0.4,
            },
        }
    ]
    obs = gw.execute("life_meal_log", {"lines": lines})
    assert obs.ok
    assert obs.receipt_id
    assert obs.data["kcal"] == 105.0
    paths = get_paths()
    with open_life_db(paths=paths) as conn:
        row = conn.execute(
            "SELECT receipt_id FROM meals WHERE meal_id = ?",
            (obs.data["meal_id"],),
        ).fetchone()
    assert row["receipt_id"] == obs.receipt_id
    crumb = paths.runs
    crumbs = list(crumb.rglob("life_*.json"))
    assert crumbs


def test_time_auto_stop(data_root: Path) -> None:
    gw = Gateway(mode="agent")
    r1 = gw.execute("life_time_start", {"kind": "focus_deep"})
    r2 = gw.execute("life_time_start", {"kind": "cooking"})
    assert r1.ok and r2.ok
    assert r2.data.get("auto_stopped_prior") == r1.data["block_id"]


def test_gym_auto_session(seeded_gym: None, data_root: Path) -> None:
    gw = Gateway(mode="agent")
    obs = gw.execute(
        "life_lift_log",
        {"sets": [{"exercise_name": "flat bench press", "load_kg": 60, "reps": 5}]},
    )
    assert obs.ok
    assert obs.data.get("auto_session") is True
    assert obs.data["volume_kg"] == 300.0


def test_nutrition_day_after_meal(data_root: Path) -> None:
    gw = Gateway(mode="agent")
    gw.execute(
        "life_meal_log",
        {
            "lines": [
                {
                    "display_name": "oats",
                    "provenance": "manual",
                    "nutrients": {"energy_kcal": 300, "protein_g": 10},
                }
            ]
        },
    )
    obs = gw.execute("life_nutrition_day", {})
    assert obs.ok
    assert obs.data["totals"].get("energy_kcal") == 300


def test_flat_bench_catalog_match(seeded_gym: None, data_root: Path) -> None:
    gw = Gateway(mode="agent")
    obs = gw.execute(
        "life_lift_log",
        {"sets": [{"exercise_name": "flat bench", "load_kg": 80, "reps": 3}]},
    )
    assert obs.ok
    paths = get_paths()
    with open_life_db(paths=paths) as conn:
        row = conn.execute(
            "SELECT exercise_id FROM gym_sets ORDER BY logged_at DESC LIMIT 1"
        ).fetchone()
        cat = conn.execute(
            "SELECT body_parts_json FROM exercise_catalog WHERE exercise_id = ?",
            (row["exercise_id"],),
        ).fetchone()
    assert cat is not None
    parts = json.loads(cat["body_parts_json"])
    assert "chest" in parts


def test_unknown_exercise_creates_custom(data_root: Path) -> None:
    gw = Gateway(mode="agent")
    obs = gw.execute(
        "life_lift_log",
        {"sets": [{"exercise_name": "Zercher squat variant", "load_kg": 50, "reps": 5}]},
    )
    assert obs.ok
    from ada.logs.gym_custom import find_custom_exercise

    assert find_custom_exercise("Zercher squat variant", paths=get_paths()) is not None


def test_life_write_tools_in_write_set() -> None:
    assert "life_meal_log" in WRITE_TOOL_NAMES
    assert "life_nutrition_day" not in WRITE_TOOL_NAMES
    assert "life_gym_status" not in WRITE_TOOL_NAMES
    assert "life_gym_status" in SPECS_BY_NAME
    assert "life_meal_log" in SPECS_BY_NAME


def test_observe_allows_gym_status(data_root: Path) -> None:
    gw = Gateway(mode="observe")
    obs = gw.execute("life_gym_status", {})
    assert obs.ok
    assert "sets_today" in (obs.data or {})


def _iter_array_schemas(node: object, path: str):
    if not isinstance(node, dict):
        return
    if node.get("type") == "array":
        yield path, node
        items = node.get("items")
        if isinstance(items, dict):
            yield from _iter_array_schemas(items, path + ".items")
    props = node.get("properties")
    if isinstance(props, dict):
        for key, val in props.items():
            child = f"{path}.{key}" if path else key
            yield from _iter_array_schemas(val, child)


def test_function_declaration_arrays_have_items() -> None:
    missing: list[str] = []
    for decl in function_declarations():
        name = str(decl.get("name") or "?")
        params = decl.get("parameters") or {}
        for path, schema in _iter_array_schemas(params, name):
            if "items" not in schema:
                missing.append(path)
    assert missing == []


def test_life_array_item_schemas_match_organs() -> None:
    """Honest/minimal items — fields the organ reads; no fake required."""
    meal_lines = SPECS_BY_NAME["life_meal_log"].schema["parameters"]["properties"]["lines"]
    assert meal_lines["items"]["type"] == "object"
    assert "required" not in meal_lines["items"]
    assert "display_name" in meal_lines["items"]["properties"]
    fix_lines = SPECS_BY_NAME["life_meal_fix"].schema["parameters"]["properties"]["lines"]
    assert fix_lines["items"]["type"] == "object"
    assert "required" not in fix_lines["items"]
    sets = SPECS_BY_NAME["life_lift_log"].schema["parameters"]["properties"]["sets"]
    assert sets["items"]["type"] == "object"
    assert "exercise_name" in sets["items"]["properties"]
    assert "required" not in sets["items"]
    components = SPECS_BY_NAME["life_food_preset_save"].schema["parameters"]["properties"][
        "components"
    ]
    assert components["items"]["type"] == "object"
    assert "required" not in components["items"]
    steps = SPECS_BY_NAME["life_routine_run"].schema["parameters"]["properties"]["steps"]
    assert steps["items"]["type"] == "string"
