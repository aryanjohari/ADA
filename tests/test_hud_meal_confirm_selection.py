"""HUD meal Confirm — operator candidate selection (M26 v1.8)."""

from __future__ import annotations

import pytest

from ada.harness.meal_spine import build_meal_log_args
from ada.hud.chat_service import ChatService, _patch_meal_confirm_selection
from ada.io.paths import get_paths
from ada.logs.connection import open_life_db
from ada.logs.favorites import get_favorite
from ada.logs.food import insert_food


def _seed_three_eggs(data_root) -> tuple[dict, dict, dict]:
    paths = get_paths()
    egg = insert_food(
        name="Egg, whole, boiled or poached",
        source="usda_fdc",
        external_id="2707154",
        nutrients_per_100g={
            "energy_kcal": 155,
            "protein_g": 12.6,
            "fat_g": 10.6,
            "carb_g": 1.1,
        },
        paths=paths,
    )
    candy = insert_food(
        name="EGGS",
        source="usda_fdc",
        brand="Mars Chocolate",
        external_id="999999",
        nutrients_per_100g={
            "energy_kcal": 571,
            "protein_g": 3.6,
            "fat_g": 35,
            "carb_g": 58,
        },
        paths=paths,
    )
    duck = insert_food(
        name="Egg, duck, whole, fresh, raw",
        source="usda_fdc",
        external_id="173424",
        nutrients_per_100g={
            "energy_kcal": 185,
            "protein_g": 12.8,
            "fat_g": 13.8,
            "carb_g": 1.5,
        },
        paths=paths,
    )
    return egg, candy, duck


def _meal_pending_args(data_root) -> tuple[dict, str]:
    _seed_three_eggs(data_root)
    built = build_meal_log_args("5 eggs", fetch_remote=False, paths=get_paths())
    assert built.get("needs_confirm") is True
    resolve = built.get("resolve") or {}
    rows = resolve.get("rows") or []
    assert rows
    assert len(rows[0].get("candidates") or []) >= 2
    return {
        "lines": built["lines"],
        "meal_slot": built.get("meal_slot"),
        "resolve": resolve,
        "save_favorite": True,
        "confirmed": False,
    }, str(rows[0].get("query_norm") or rows[0].get("query") or "eggs")


def _meal_line_ref_id() -> str | None:
    with open_life_db(paths=get_paths()) as conn:
        row = conn.execute(
            "SELECT ref_id FROM meal_foods ORDER BY line_id DESC LIMIT 1"
        ).fetchone()
    return str(row[0]) if row else None


def test_meal_confirm_selected_ref_patches_line_and_favorite(data_root) -> None:
    """Operator picks non-default candidate → line ref_id + favorite match."""
    egg, candy, duck = _seed_three_eggs(data_root)
    stash, key = _meal_pending_args(data_root)
    rows = stash["resolve"]["rows"]
    candidates = rows[0]["candidates"]
    assert len(candidates) >= 2
    proposed = rows[0]["proposed_ref_id"]
    alt = next(
        c["ref_id"]
        for c in candidates
        if c["ref_id"] != proposed
    )

    svc = ChatService()
    svc._ensure_session("agent")
    svc.pending_confirms["rcpt_meal_pick"] = {
        "tool": "life_meal_log",
        "args": stash,
    }
    out = svc.confirm_tool(
        "life_meal_log",
        {"lines": [{"display_name": "FORGED"}]},
        pending_id="rcpt_meal_pick",
        selected_ref_ids={key: alt},
    )
    assert out.get("ok") is True
    assert _meal_line_ref_id() == alt
    fav = get_favorite(key, paths=get_paths())
    assert fav is not None
    assert fav["ref_id"] == alt


def test_meal_confirm_invalid_ref_fails_closed(data_root) -> None:
    stash, key = _meal_pending_args(data_root)
    svc = ChatService()
    svc._ensure_session("agent")
    svc.pending_confirms["rcpt_bad"] = {"tool": "life_meal_log", "args": stash}
    with pytest.raises(ValueError, match="invalid meal selection"):
        svc.confirm_tool(
            "life_meal_log",
            {},
            pending_id="rcpt_bad",
            selected_ref_ids={key: "fdc:not-in-pool"},
        )


def test_meal_confirm_no_selection_uses_proposed(data_root) -> None:
    """No selected_ref_ids → proposed_ref_id unchanged (current behavior)."""
    _seed_three_eggs(data_root)
    stash, key = _meal_pending_args(data_root)
    proposed = stash["resolve"]["rows"][0]["proposed_ref_id"]
    patched = _patch_meal_confirm_selection(stash, None)
    assert patched["lines"][0]["ref_id"] == proposed
    assert patched["resolve"]["rows"][0]["proposed_ref_id"] == proposed

    svc = ChatService()
    svc._ensure_session("agent")
    svc.pending_confirms["rcpt_default"] = {
        "tool": "life_meal_log",
        "args": stash,
    }
    out = svc.confirm_tool(
        "life_meal_log",
        {},
        pending_id="rcpt_default",
        selected_ref_ids=None,
    )
    assert out.get("ok") is True
    assert _meal_line_ref_id() == proposed


def test_patch_rejects_null_energy_pick_when_complete_exists() -> None:
    """Confirm pick of null-kcal oats remaps to proposed Oats, raw (d99da535…)."""
    raw = {
        "ref_id": "raw-oats",
        "label": "Oats, raw",
        "kcal_per_100g": 379.0,
        "macros_empty": False,
        "nutrients": {
            "energy_kcal": 379.0,
            "protein_g": 13.2,
            "fat_g": 6.5,
            "carb_g": 67.7,
        },
    }
    rolled = {
        "ref_id": "rolled-oats",
        "label": "Oats, whole grain, rolled, old fashioned",
        "kcal_per_100g": None,
        "macros_empty": True,
        "nutrients": {
            "energy_kcal": None,
            "protein_g": 13.5,
            "fat_g": 5.9,
            "carb_g": 68.7,
        },
    }
    stash = {
        "lines": [
            {
                "_query": "oats",
                "_query_norm": "oats",
                "display_name": "Oats, raw",
                "ref_id": "raw-oats",
                "serving_grams": 100.0,
            }
        ],
        "resolve": {
            "bind_authority": "meal_spine",
            "rows": [
                {
                    "query": "oats",
                    "query_norm": "oats",
                    "proposed_ref_id": "raw-oats",
                    "candidates": [raw, rolled],
                }
            ],
            "candidates": [raw, rolled],
        },
    }
    patched = _patch_meal_confirm_selection(stash, {"oats": "rolled-oats"})
    assert patched["lines"][0]["ref_id"] == "raw-oats"
    assert patched["lines"][0]["display_name"] == "Oats, raw"
    nuts = patched["lines"][0].get("nutrients") or {}
    assert nuts.get("energy_kcal") == 379.0
