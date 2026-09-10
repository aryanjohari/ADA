"""M26 food reflection — deterministic window compute (not Dream)."""

from __future__ import annotations

import json

import pytest

from ada.dream.delta import build_delta
from ada.dream.manage import manage_delta
from ada.harness.pack_router import route_utterance
from ada.io.atomic import atomic_write_text
from ada.io.paths import get_paths
from ada.logs.connection import open_life_db
from ada.logs.food import insert_food
from ada.logs.food_reflection import nutrition_window
from ada.logs.meals import meal_log
from ada.memory.facts import _dump_yaml
from ada.tools.gateway import Gateway


def test_nutrition_window_patterns(data_root) -> None:
    """7-day window with seeded rollups — target pattern counts use window denominator."""
    paths = get_paths()
    paths.ensure_memory_dirs()
    atomic_write_text(
        paths.facts / "nutrition_targets.yaml",
        _dump_yaml({"schema_version": 1, "targets": {"protein_g": 150, "energy_kcal": 2500}}),
    )
    egg = insert_food(
        name="Egg, whole, cooked",
        source="custom",
        nutrients_per_100g={
            "energy_kcal": 155,
            "protein_g": 12.6,
            "fat_g": 10.6,
            "carb_g": 1.1,
        },
        paths=paths,
    )
    meal_log(
        receipt_id="m1",
        meal_slot="breakfast",
        lines=[
            {
                "display_name": "eggs",
                "ref_id": egg["food_ref_id"],
                "serving_qty": 5,
                "serving_unit": "piece",
                "serving_grams": 250.0,
                "provenance": "api",
                "nutrients": {
                    "energy_kcal": 387.5,
                    "protein_g": 31.5,
                    "fat_g": 26.5,
                    "carb_g": 2.75,
                },
            }
        ],
        paths=paths,
    )
    with open_life_db(paths=paths) as conn:
        day = conn.execute(
            "SELECT local_day FROM nutrition_day_rollup ORDER BY local_day DESC LIMIT 1"
        ).fetchone()["local_day"]

    window = nutrition_window(paths=paths, days=7)
    assert window["ok"] is True
    assert window["days_logged"] == 1
    assert window["window_days"] == 7
    assert window["days"]
    logged = [d for d in window["days"] if d["meal_count"] > 0]
    assert logged[0]["cite"] == f"meal:day:{day}"
    assert logged[0]["totals"]["protein_g"] == pytest.approx(31.5)
    assert window["targets"]["protein_g"] == 150
    assert window["flags"]["protein_below_target"] == "7/7"
    assert any("protein below target 7/7" in p for p in window["patterns"])
    assert window["meal_slots"]["breakfast"] == 1
    assert len(window["summary_text"]) <= 2000


def test_nutrition_window_empty(data_root) -> None:
    paths = get_paths()
    window = nutrition_window(paths=paths, days=7)
    assert window["ok"] is True
    assert window["days_logged"] == 0
    assert window["days"] == []
    assert "No meals logged" in window["summary_text"]


def test_nutrition_window_honest_partial_no_invented_macros(data_root) -> None:
    paths = get_paths()
    paths.ensure_memory_dirs()
    atomic_write_text(
        paths.facts / "nutrition_targets.yaml",
        _dump_yaml({"schema_version": 1, "targets": {"protein_g": 100}}),
    )
    meal_log(
        receipt_id="partial-1",
        meal_slot="lunch",
        lines=[
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
                    "calcium_mg": None,
                },
            }
        ],
        paths=paths,
    )
    window = nutrition_window(paths=paths, days=3)
    logged = [d for d in window["days"] if d["meal_count"] > 0]
    assert logged[0]["honest_partial"] is True
    assert "calcium_mg" not in logged[0]["totals"]
    assert window["flags"].get("honest_partial_days") == 1


def test_delta_excludes_food_rollup(data_root) -> None:
    """Dream delta must not carry food rollup — reflection is tool-only."""
    paths = get_paths()
    from ada.body.identity import create_identity
    from ada.memory.facts import ensure_prefs

    create_identity(paths=paths)
    ensure_prefs(paths)
    delta = build_delta(paths=paths)
    assert "food_rollup_summary" not in delta
    assert "food_rollup" not in delta["summary_text"]


def test_manage_delta_without_food_block(data_root) -> None:
    paths = get_paths()
    from ada.body.identity import create_identity
    from ada.memory.facts import ensure_prefs

    create_identity(paths=paths)
    ensure_prefs(paths)
    delta = build_delta(paths=paths)

    class FakeManage:
        class models:
            @staticmethod
            def generate_content(**kwargs):
                class Resp:
                    text = json.dumps(
                        {
                            "digest": "Quiet night.",
                            "fact_candidates": [],
                            "worldview_notes": [],
                            "campaign_digests": [],
                            "open_loops": [],
                            "conflicts": [],
                        }
                    )

                return Resp()

    manage = manage_delta(delta, client=FakeManage(), api_key="fake")
    assert manage["ok"] is True


def test_route_protein_this_week() -> None:
    r = route_utterance("protein this week")
    assert r is not None
    assert r["verb"] == "nutrition_week"
    assert r["tool"] == "life_nutrition_week"
