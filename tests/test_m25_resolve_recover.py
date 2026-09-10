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
    recover_food_slot,
)
from ada.harness.resolve_gate import candidate_matches_query, decide_food_bind
from ada.harness.session import ChatSession
from ada.io.paths import get_paths
from ada.logs.connection import open_life_db
from ada.logs.favorites import set_favorite
from ada.logs.food import get_food, insert_food, update_food_nutrients


def _nested_fdc_nutrients(*pairs: tuple[int, float]) -> list[dict]:
    """Realistic USDA FDC detail foodNutrients (nested nutrient.id + amount)."""
    return [
        {"nutrient": {"id": nid, "name": "n", "unitName": "G"}, "amount": val}
        for nid, val in pairs
    ]


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
            "foodNutrients": _nested_fdc_nutrients(
                (1008, 155),
                (1003, 12.6),
                (1004, 10.6),
                (1005, 1.1),
            ),
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
    assert nutrients.get("protein_g") is not None
    row = get_food(candy["food_ref_id"], paths=paths)
    assert row is not None
    cached = json.loads(row.get("nutrients_per_100g_json") or "{}")
    assert cached.get("energy_kcal") == 155.0
    assert cached.get("protein_g") == 12.6


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

    import ada.logs.food as food_mod

    monkeypatch.setattr(food_mod, "fetch_usda_search", lambda *a, **k: None)

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


def test_alt_queries_no_double_modifier_or_bad_plural() -> None:
    alts = build_alt_queries("7 boiled eggs", "eggs")
    lowered = [a.lower() for a in alts]
    assert "boiled boiled" not in " ".join(lowered)
    assert "rices" not in lowered
    assert "boiled eggs" in lowered or "boiled egg" in lowered


def test_search_null_core_local_triggers_remote(
    data_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """All-null-CORE local cache must not block USDA fetch (Gap A)."""
    paths = get_paths()
    insert_food(
        name="EGGS",
        source="usda_fdc",
        external_id="junk001",
        brand="Mars Chocolate",
        nutrients_per_100g={
            "energy_kcal": None,
            "protein_g": None,
            "fat_g": None,
            "carb_g": None,
        },
        paths=paths,
    )
    remote_called: list[str] = []

    def fake_fetch(query, **kwargs):
        remote_called.append(query)
        return {
            "name": "Egg, whole, cooked, hard-boiled",
            "source": "usda_fdc",
            "external_id": "173424",
            "brand": None,
            "nutrients_per_100g": {
                "energy_kcal": 155.0,
                "protein_g": 12.6,
                "fat_g": 10.6,
                "carb_g": 1.1,
            },
            "data_type": "Foundation",
        }

    import ada.logs.food as food_mod

    monkeypatch.setattr(food_mod, "fetch_usda_search", fake_fetch)
    hits = food_mod.search_foods_resolved("eggs", limit=5, paths=paths)
    assert remote_called == ["eggs"]
    assert hits
    assert hits[0].get("nutrients", {}).get("energy_kcal") == 155.0


def test_freestyle_meal_log_ref_id_only_enriches(data_root: Path) -> None:
    """Spine resolve + ref_id line → enrich from cache, honest macros (Gap B)."""
    from ada.tools.life_tools import run_life_meal_log

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
    out = run_life_meal_log(
        {
            "receipt_id": "r1",
            "lines": [
                {
                    "ref_id": egg["food_ref_id"],
                    "serving_qty": 7,
                    "serving_unit": "serving",
                    "serving_grams": 350.0,
                }
            ],
            "resolve": {
                "bind_authority": "meal_spine",
                "needs_confirm": False,
                "reasons": ["favorite_unique"],
                "rows": [
                    {
                        "query": "eggs",
                        "proposed_ref_id": egg["food_ref_id"],
                        "reasons": ["favorite_unique"],
                    }
                ],
                "candidates": [],
            },
        }
    )
    assert out.get("ok") is True
    assert out.get("kcal") and float(out["kcal"]) > 0
    assert out.get("protein_g") and float(out["protein_g"]) > 0


def test_freestyle_meal_log_ref_id_only_refuses_null_core(data_root: Path) -> None:
    """ref_id without spine resolve → spine_required; null-CORE with resolve → empty_macros."""
    from ada.tools.life_tools import run_life_meal_log

    paths = get_paths()
    junk = insert_food(
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
    refused = run_life_meal_log(
        {
            "receipt_id": "r2",
            "lines": [{"ref_id": junk["food_ref_id"], "serving_qty": 7}],
        }
    )
    assert refused.get("ok") is False
    assert refused.get("reason") == "spine_required"
    out = run_life_meal_log(
        {
            "receipt_id": "r2b",
            "lines": [{"ref_id": junk["food_ref_id"], "serving_qty": 7}],
            "resolve": {
                "bind_authority": "meal_spine",
                "needs_confirm": False,
                "reasons": [],
                "rows": [
                    {
                        "query": "eggs",
                        "proposed_ref_id": junk["food_ref_id"],
                        "reasons": [],
                    }
                ],
                "candidates": [],
            },
        }
    )
    assert out.get("ok") is False
    assert out.get("reason") == "empty_macros"
    with open_life_db(paths=paths) as conn:
        n = conn.execute("SELECT COUNT(*) AS n FROM meals").fetchone()["n"]
    assert int(n) == 0


def test_fast_spine_detail_refresh_before_recover(data_root: Path) -> None:
    """Null-CORE FDC on fast spine → detail refresh → honest bind without recover cap."""
    paths = get_paths()
    candy = insert_food(
        name="EGGS",
        source="usda_fdc",
        external_id="999002",
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
            "fdcId": 999002,
            "description": "Egg, whole, cooked, hard-boiled",
            "foodNutrients": _nested_fdc_nutrients(
                (1008, 155),
                (1003, 12.6),
                (1004, 10.6),
                (1005, 1.1),
            ),
        }
        return resp

    built = build_meal_log_args(
        "7 boiled eggs",
        meal_slot="breakfast",
        fetch_remote=False,
        paths=paths,
        http_get=fake_get,
    )
    assert built.get("ok") is True
    line = (built.get("lines") or [{}])[0]
    nutrients = line.get("nutrients") or {}
    assert nutrients.get("energy_kcal") is not None
    assert nutrients.get("protein_g") is not None
    assert line.get("ref_id") == candy["food_ref_id"]
    row = get_food(candy["food_ref_id"], paths=paths)
    cached = json.loads(row.get("nutrients_per_100g_json") or "{}")
    assert cached.get("energy_kcal") == 155.0
    assert cached.get("protein_g") == 12.6


def test_seven_eggs_not_mars_candy(data_root: Path) -> None:
    """Poisoned Mars EGGS candy macros must not sole-bind; recover → real egg (F-M25-2)."""
    paths = get_paths()
    candy = insert_food(
        name="EGGS",
        source="usda_fdc",
        external_id="mars001",
        brand="Mars Chocolate North America LLC",
        nutrients_per_100g={
            "energy_kcal": 571.0,
            "protein_g": 3.57,
            "fat_g": 30.0,
            "carb_g": 57.14,
        },
        paths=paths,
    )
    egg = insert_food(
        name="Egg, whole, cooked, hard-boiled",
        source="custom",
        nutrients_per_100g={
            "energy_kcal": 155.0,
            "protein_g": 12.6,
            "fat_g": 10.6,
            "carb_g": 1.1,
        },
        paths=paths,
    )

    import ada.logs.food as food_mod

    def fake_search(query, **kwargs):
        ql = query.lower()
        if "boiled" in ql or "cooked" in ql or "whole" in ql:
            return [
                {
                    "ref_id": egg["food_ref_id"],
                    "name": "Egg, whole, cooked, hard-boiled",
                    "score": 0.95,
                    "nutrients": {
                        "energy_kcal": 155.0,
                        "protein_g": 12.6,
                        "fat_g": 10.6,
                        "carb_g": 1.1,
                    },
                }
            ]
        if ql.strip() in {"eggs", "egg"}:
            return [
                {
                    "ref_id": candy["food_ref_id"],
                    "name": "EGGS",
                    "brand": "Mars Chocolate North America LLC",
                    "source": "usda_fdc",
                    "external_id": "mars001",
                    "score": 1.0,
                    "nutrients": {
                        "energy_kcal": 571.0,
                        "protein_g": 3.57,
                        "fat_g": 30.0,
                        "carb_g": 57.14,
                    },
                }
            ]
        return []

    original = food_mod.search_foods_resolved
    food_mod.search_foods_resolved = fake_search
    try:
        built = build_meal_log_args(
            "7 eggs",
            meal_slot="breakfast",
            fetch_remote=False,
            paths=paths,
        )
    finally:
        food_mod.search_foods_resolved = original

    assert built.get("ok") is True
    line = (built.get("lines") or [{}])[0]
    nutrients = line.get("nutrients") or {}
    protein = float(nutrients.get("protein_g") or 0)
    assert protein >= 40.0
    assert "mars" not in str(line.get("display_name") or "").lower()
    assert line.get("ref_id") != candy["food_ref_id"]
    if built.get("needs_confirm"):
        labels = [
            str(c.get("label") or "")
            for c in (built.get("resolve") or {}).get("candidates") or []
        ]
        assert any(
            "egg" in lbl.lower() and "mars" not in lbl.lower() for lbl in labels
        )


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
