"""M25 — pack-fenced resolve recover after meal fast-spine miss."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ada.harness.loop import run_turn
from ada.harness.meal_spine import (
    build_alt_queries,
    build_meal_log_args,
    candidate_matches_query,
    recover_food_slot,
)
from ada.harness.resolve_gate import decide_food_bind
from ada.harness.session import ChatSession
from ada.io.paths import get_paths
from ada.logs.connection import open_life_db
from ada.logs.favorites import set_favorite
from ada.logs.food import get_food, insert_food, update_food_nutrients


class _ShouldNotRunAdapter:
    model = "fake"

    def generate(self, *, system, contents, tools=None):
        raise AssertionError("pack fast-path should finish before model generate")


def test_alt_queries_restore_boiled_egg() -> None:
    alts = build_alt_queries("7 boiled eggs", "eggs")
    joined = " ".join(alts).lower()
    assert "boiled eggs" in joined or "boiled egg" in joined
    assert "egg, whole, cooked" in joined
    assert "large egg" in joined


def test_candidate_matches_query_rejects_banana_for_eggs() -> None:
    """Off-query recover hit (Banana, raw via shared 'raw') must not bind."""
    banana = {
        "ref_id": "b1",
        "name": "Banana, raw",
        "score": 0.333,
        "nutrients": {
            "energy_kcal": 97.0,
            "protein_g": 0.74,
            "fat_g": 0.28,
            "carb_g": 22.71,
        },
    }
    egg = {
        "ref_id": "e1",
        "name": "Egg, whole, boiled or poached",
        "score": 1.0,
        "nutrients": {
            "energy_kcal": 155.0,
            "protein_g": 12.6,
            "fat_g": 10.6,
            "carb_g": 1.1,
        },
    }
    assert candidate_matches_query("eggs", banana) is False
    assert candidate_matches_query("eggs", egg) is True
    assert candidate_matches_query("egg", egg) is True


def test_recover_drops_off_query_banana(data_root: Path) -> None:
    """Recover pool must not accept Banana when slot query is eggs (phone dcce958)."""
    paths = get_paths()
    insert_food(
        name="eggs",
        source="custom",
        nutrients_per_100g={
            "energy_kcal": None,
            "protein_g": None,
            "fat_g": None,
            "carb_g": None,
        },
        paths=paths,
    )
    banana = insert_food(
        name="Banana, raw",
        source="usda_fdc",
        external_id="173944",
        nutrients_per_100g={
            "energy_kcal": 97.0,
            "protein_g": 0.74,
            "fat_g": 0.28,
            "carb_g": 22.71,
        },
        paths=paths,
    )

    import ada.logs.food as food_mod

    def fake_search(query, **kwargs):
        if "raw" in query.lower():
            return [
                {
                    "ref_id": banana["food_ref_id"],
                    "name": "Banana, raw",
                    "source": "usda_fdc",
                    "score": 0.333,
                    "nutrients": {
                        "energy_kcal": 97.0,
                        "protein_g": 0.74,
                        "fat_g": 0.28,
                        "carb_g": 22.71,
                    },
                }
            ]
        return []

    original = food_mod.search_foods_resolved
    food_mod.search_foods_resolved = fake_search
    try:
        recover = recover_food_slot(
            query="eggs",
            original_piece="7 eggs",
            qty=7.0,
            unit="serving",
            serving_grams=350.0,
            miss_reason="empty_macros",
            initial_candidates=[],
            fetch_remote=False,
            paths=paths,
        )
    finally:
        food_mod.search_foods_resolved = original

    assert recover.get("ok") is False
    assert recover.get("reason") == "recover_cap"
    line = recover.get("line")
    assert line is None or "banana" not in str(line.get("display_name") or "").lower()



def test_recover_detail_refresh_finds_honest_egg(data_root: Path) -> None:
    """Null-CORE candy row → detail refresh → honest bind (F-M25-1, F-M25-5)."""
    paths = get_paths()
    candy = insert_food(
        name="EGGS",
        source="usda_fdc",
        external_id="999001",
        brand="Mars Chocolate",
        nutrients_per_100g={
            "energy_kcal": None,
            "protein_g": None,
            "fat_g": None,
            "carb_g": None,
        },
        paths=paths,
    )

    def fake_get(url, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "fdcId": 999001,
            "description": "Egg, whole, cooked, hard-boiled",
            "foodNutrients": [
                {"nutrientId": 1008, "value": 155},
                {"nutrientId": 1003, "value": 12.6},
                {"nutrientId": 1004, "value": 10.6},
                {"nutrientId": 1005, "value": 1.1},
            ],
        }
        return resp

    recover = recover_food_slot(
        query="eggs",
        original_piece="7 boiled eggs",
        qty=7.0,
        unit="serving",
        serving_grams=350.0,
        miss_reason="empty_macros",
        initial_candidates=[
            {
                "ref_id": candy["food_ref_id"],
                "name": "EGGS",
                "brand": "Mars Chocolate",
                "source": "usda_fdc",
                "external_id": "999001",
                "score": 1.0,
                "nutrients": {
                    "energy_kcal": None,
                    "protein_g": None,
                    "fat_g": None,
                    "carb_g": None,
                },
            }
        ],
        fetch_remote=False,
        paths=paths,
        http_get=fake_get,
    )
    assert recover.get("ok") is True
    line = recover.get("line") or {}
    nutrients = line.get("nutrients") or {}
    assert nutrients.get("energy_kcal") is not None
    row = get_food(candy["food_ref_id"], paths=paths)
    assert row is not None
    cached = json.loads(row.get("nutrients_per_100g_json") or "{}")
    assert cached.get("energy_kcal") == 155.0


def test_recover_ambiguous_needs_confirm(data_root: Path) -> None:
    """Recover with multiple honest hits → Confirm, not silent bind (F-M25-2, F-M25-3)."""
    paths = get_paths()
    a = insert_food(
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
    b = insert_food(
        name="Egg, whole, raw",
        source="custom",
        nutrients_per_100g={
            "energy_kcal": 143,
            "protein_g": 12.6,
            "fat_g": 9.5,
            "carb_g": 0.7,
        },
        paths=paths,
    )

    def fake_search(query, **kwargs):
        if "cooked" in query.lower():
            return [
                {
                    "ref_id": a["food_ref_id"],
                    "name": "Egg, whole, cooked",
                    "score": 0.9,
                    "nutrients": {
                        "energy_kcal": 155,
                        "protein_g": 12.6,
                        "fat_g": 10.6,
                        "carb_g": 1.1,
                    },
                }
            ]
        if "raw" in query.lower():
            return [
                {
                    "ref_id": b["food_ref_id"],
                    "name": "Egg, whole, raw",
                    "score": 0.9,
                    "nutrients": {
                        "energy_kcal": 143,
                        "protein_g": 12.6,
                        "fat_g": 9.5,
                        "carb_g": 0.7,
                    },
                }
            ]
        return []

    import ada.logs.food as food_mod

    original = food_mod.search_foods_resolved
    calls: list[str] = []

    def patched_search(query, **kwargs):
        calls.append(query)
        return fake_search(query, **kwargs)

    food_mod.search_foods_resolved = patched_search
    try:
        built = build_meal_log_args(
            "7 boiled eggs",
            meal_slot="breakfast",
            fetch_remote=False,
            paths=paths,
        )
    finally:
        food_mod.search_foods_resolved = original

    assert any("boiled" in c.lower() or "cooked" in c.lower() for c in calls)
    assert built.get("ok") is True
    assert built.get("needs_confirm") is True
    assert built.get("lines")
    with open_life_db(paths=paths) as conn:
        n = conn.execute("SELECT COUNT(*) AS n FROM meals").fetchone()["n"]
    assert int(n) == 0


def test_recover_favorite_silent_bind(data_root: Path) -> None:
    """Unique sticky favorite after recover → silent bind (F-M25-2)."""
    paths = get_paths()
    egg = insert_food(
        name="Egg, whole, cooked, hard-boiled",
        source="custom",
        nutrients_per_100g={
            "energy_kcal": 155,
            "protein_g": 12.6,
            "fat_g": 10.6,
            "carb_g": 1.1,
        },
        paths=paths,
    )
    set_favorite(
        query="eggs",
        ref_id=egg["food_ref_id"],
        label="Egg, whole, cooked, hard-boiled",
        confirmed=True,
        paths=paths,
    )
    insert_food(
        name="eggs",
        source="custom",
        nutrients_per_100g={
            "energy_kcal": None,
            "protein_g": None,
            "fat_g": None,
            "carb_g": None,
        },
        paths=paths,
    )

    import ada.logs.food as food_mod

    def fake_search(query, **kwargs):
        if "cooked" in query.lower() or "boiled" in query.lower():
            return [
                {
                    "ref_id": egg["food_ref_id"],
                    "name": "Egg, whole, cooked, hard-boiled",
                    "score": 1.0,
                    "nutrients": {
                        "energy_kcal": 155,
                        "protein_g": 12.6,
                        "fat_g": 10.6,
                        "carb_g": 1.1,
                    },
                }
            ]
        return food_mod.search_foods(query, limit=5, paths=paths)

    original = food_mod.search_foods_resolved
    food_mod.search_foods_resolved = fake_search
    try:
        built = build_meal_log_args(
            "7 boiled eggs",
            meal_slot="breakfast",
            fetch_remote=False,
            paths=paths,
        )
    finally:
        food_mod.search_foods_resolved = original

    assert built.get("ok") is True
    assert built.get("needs_confirm") is False
    assert built["lines"][0]["ref_id"] == egg["food_ref_id"]


def test_recover_cap_hit_human_ask(
    data_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Caps → clear ask, not forever empty ack (F-M25-4, F-M25-5)."""
    paths = get_paths()
    insert_food(
        name="eggs",
        source="custom",
        nutrients_per_100g={
            "energy_kcal": None,
            "protein_g": None,
            "fat_g": None,
            "carb_g": None,
        },
        paths=paths,
    )
    monkeypatch.setattr(
        "ada.harness.meal_spine._RECOVER_SEARCHES",
        2,
    )

    built = build_meal_log_args(
        "7 boiled eggs",
        meal_slot="breakfast",
        fetch_remote=False,
        paths=paths,
    )
    assert built.get("ok") is False
    assert built.get("ask")
    assert len(built.get("searches") or []) >= 2

    session = ChatSession(mode="agent")
    result = run_turn(
        session,
        "log meal: 7 boiled eggs for breakfast",
        _ShouldNotRunAdapter(),
    )
    assert result.stop_reason == "missing_life_receipt"
    assert result.text
    assert "empty" not in result.text.lower() or "tries" in result.text.lower()
    meal_receipts = [
        r for r in result.tool_receipts if str(r.get("tool") or "") == "life_meal_log"
    ]
    assert not meal_receipts


def test_decide_food_bind_never_sole_picks_null_core() -> None:
    """Code bind only — null CORE top hit skipped when viable exists (F-M25-7)."""
    decision = decide_food_bind(
        query="eggs",
        candidates=[
            {
                "ref_id": "null1",
                "name": "EGGS",
                "brand": "Mars",
                "score": 1.0,
                "nutrients": {
                    "energy_kcal": None,
                    "protein_g": None,
                    "fat_g": None,
                    "carb_g": None,
                },
            },
            {
                "ref_id": "good1",
                "name": "Egg, whole, cooked",
                "score": 0.8,
                "nutrients": {
                    "energy_kcal": 155,
                    "protein_g": 12.6,
                    "fat_g": 10.6,
                    "carb_g": 1.1,
                },
            },
        ],
        favorite=None,
    )
    assert decision.get("proposed_ref_id") == "good1"


def test_update_food_nutrients_writes_cache(data_root: Path) -> None:
    row = insert_food(
        name="EGGS",
        source="usda_fdc",
        external_id="123",
        nutrients_per_100g={
            "energy_kcal": None,
            "protein_g": None,
            "fat_g": None,
            "carb_g": None,
        },
        paths=get_paths(),
    )
    updated = update_food_nutrients(
        row["food_ref_id"],
        nutrients_per_100g={
            "energy_kcal": 155,
            "protein_g": 12.6,
            "fat_g": 10.6,
            "carb_g": 1.1,
        },
        name="Egg, whole, cooked",
        paths=get_paths(),
    )
    assert updated is not None
    nutrients = json.loads(updated.get("nutrients_per_100g_json") or "{}")
    assert nutrients.get("energy_kcal") == 155.0
