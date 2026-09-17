"""Food personal library — favorites harden, meal draft, presets (M26 v1.11)."""

from __future__ import annotations

from ada.harness.meal_draft_spine import (
    build_draft_add_from_utterance,
    expand_preset_log_args,
    parse_log_preset_name,
    wants_estimate,
)
from ada.hud.chat_service import _patch_meal_confirm_selection
from ada.harness.meal_spine import build_meal_log_args
from ada.io.paths import get_paths
from ada.logs import meal_draft as draft_mod
from ada.logs.favorites import get_favorite, resolve_favorite_bind, set_favorite
from ada.logs.food import delete_food, insert_food
from ada.logs.nutrition_presets import expand_preset_lines, get_preset, save_preset
from ada.tools.life_tools import (
    run_life_meal_draft_add,
    run_life_meal_draft_cancel,
    run_life_meal_draft_save,
    run_life_meal_draft_start,
    run_life_meal_log,
    run_life_meal_preset_log,
)


def _egg(paths, *, external_id: str = "2707154", name: str = "Egg, whole, boiled or poached"):
    return insert_food(
        name=name,
        source="usda_fdc",
        external_id=external_id,
        nutrients_per_100g={
            "energy_kcal": 155,
            "protein_g": 12.6,
            "fat_g": 10.6,
            "carb_g": 1.1,
        },
        paths=paths,
    )


def _rice(paths):
    return insert_food(
        name="Rice, white, long-grain, cooked",
        source="usda_fdc",
        external_id="20045",
        nutrients_per_100g={
            "energy_kcal": 130,
            "protein_g": 2.7,
            "fat_g": 0.3,
            "carb_g": 28.0,
        },
        paths=paths,
    )


def test_favorite_hit_silent_bind(data_root) -> None:
    """Sticky favorite with live ref_id → silent bind (no Confirm)."""
    paths = get_paths()
    egg = _egg(paths)
    set_favorite(
        query="eggs",
        ref_id=egg["food_ref_id"],
        label=egg["name"],
        confirmed=True,
        paths=paths,
    )
    fav, reasons = resolve_favorite_bind("eggs", paths=paths)
    assert fav is not None
    assert reasons == []
    built = build_meal_log_args("5 eggs", fetch_remote=False, paths=paths)
    assert built.get("ok") is True
    assert built.get("needs_confirm") is False
    assert built["lines"][0]["ref_id"] == egg["food_ref_id"]


def test_favorite_missing_ref_forces_confirm_rebind(data_root) -> None:
    """Cache wipe deletes favorite ref → Confirm + re-bind, never silent broken."""
    paths = get_paths()
    egg = _egg(paths)
    set_favorite(
        query="eggs",
        ref_id=egg["food_ref_id"],
        label=egg["name"],
        confirmed=True,
        paths=paths,
    )
    delete_food(egg["food_ref_id"], paths=paths)
    _egg(paths, external_id="173424", name="Egg, whole, raw, fresh")
    fav, reasons = resolve_favorite_bind("eggs", paths=paths)
    assert fav is None
    assert "favorite_ref_missing" in reasons

    built = build_meal_log_args("5 eggs", fetch_remote=False, paths=paths)
    assert built.get("ok") is True
    assert built.get("needs_confirm") is True
    assert "favorite_ref_missing" in (built.get("resolve") or {}).get("reasons") or []
    resolve = built["resolve"]
    out = run_life_meal_log(
        {
            "lines": built["lines"],
            "resolve": resolve,
            "confirmed": True,
            "save_favorite": True,
        }
    )
    assert out.get("ok") is True
    rebound = get_favorite("eggs", paths=paths)
    assert rebound is not None
    assert rebound["ref_id"] == built["lines"][0]["ref_id"]


def test_meal_draft_start_add_save_clears(data_root) -> None:
    """start → add 2 lines (mock search) → save preset → draft cleared."""
    paths = get_paths()
    egg = _egg(paths)
    rice = _rice(paths)
    sid = "testsessiondraft01"
    start = run_life_meal_draft_start({"session_id": sid})
    assert start.get("ok") is True
    assert draft_mod.load_draft(sid, paths=paths) is not None

    set_favorite(
        query="eggs",
        ref_id=egg["food_ref_id"],
        label=egg["name"],
        confirmed=True,
        paths=paths,
    )
    set_favorite(
        query="cooked white rice",
        ref_id=rice["food_ref_id"],
        label=rice["name"],
        confirmed=True,
        paths=paths,
    )

    for utt in ("5 eggs", "100 grams cooked white rice"):
        built = build_draft_add_from_utterance(
            utt, session_id=sid, fetch_remote=False, paths=paths
        )
        assert built.get("ok") is True, built
        add = run_life_meal_draft_add(
            {
                "session_id": sid,
                "lines": built["lines"],
                "resolve": built.get("resolve"),
                "confirmed": True,
                "save_favorite": False,
            }
        )
        assert add.get("ok") is True, add

    draft = draft_mod.load_draft(sid, paths=paths)
    assert draft is not None
    assert len(draft.get("lines") or []) == 2

    saved = run_life_meal_draft_save(
        {"session_id": sid, "name": "my lunch", "confirmed": True}
    )
    assert saved.get("ok") is True, saved
    assert saved.get("draft_cleared") is True
    assert draft_mod.load_draft(sid, paths=paths) is None
    preset = get_preset("my lunch", paths=paths)
    assert preset is not None
    assert len(preset.get("components") or []) == 2


def test_meal_draft_cancel_clears(data_root) -> None:
    sid = "testsessioncancel02"
    run_life_meal_draft_start({"session_id": sid})
    assert draft_mod.load_draft(sid) is not None
    out = run_life_meal_draft_cancel({"session_id": sid})
    assert out.get("ok") is True
    assert draft_mod.load_draft(sid) is None


def test_preset_expand_and_log(data_root) -> None:
    paths = get_paths()
    egg = _egg(paths)
    save_preset(
        name="omelette breakfast",
        components=[
            {
                "ref_id": egg["food_ref_id"],
                "display_name": egg["name"],
                "serving_qty": 2,
                "serving_unit": "serving",
                "serving_grams": 100,
                "provenance": "custom",
                "nutrients": {
                    "energy_kcal": 155,
                    "protein_g": 12.6,
                    "fat_g": 10.6,
                    "carb_g": 1.1,
                },
            }
        ],
        confirmed=True,
        paths=paths,
    )
    expanded = expand_preset_lines("omelette breakfast", paths=paths)
    assert expanded.get("ok") is True
    assert expanded["lines"]
    assert parse_log_preset_name("log my omelette breakfast") == "omelette breakfast"
    built = expand_preset_log_args("omelette breakfast", paths=paths)
    assert built.get("ok") is True
    out = run_life_meal_preset_log(
        {
            "name": "omelette breakfast",
            "lines": built["lines"],
            "resolve": {**(built.get("resolve") or {}), "bind_authority": "meal_spine"},
            "confirmed": True,
        }
    )
    assert out.get("ok") is True


def test_unknown_preset_honest_miss(data_root) -> None:
    out = expand_preset_lines("no such feast", paths=get_paths())
    assert out.get("ok") is False
    assert out.get("reason") == "preset_unknown"
    assert "ask" in out


def test_log_my_x_finds_save_as_my_preset(data_root) -> None:
    """save as my lunch stores my_lunch; Log my lunch must still expand (edef2243)."""
    paths = get_paths()
    egg = _egg(paths)
    save_preset(
        name="my lunch",
        components=[
            {
                "ref_id": egg["food_ref_id"],
                "display_name": egg["name"],
                "serving_qty": 2,
                "serving_unit": "serving",
                "serving_grams": 100,
                "provenance": "custom",
                "nutrients": {
                    "energy_kcal": 155,
                    "protein_g": 12.6,
                    "fat_g": 10.6,
                    "carb_g": 1.1,
                },
            }
        ],
        confirmed=True,
        paths=paths,
    )
    assert parse_log_preset_name("Log my lunch") == "lunch"
    assert parse_log_preset_name("Yes log my lunch") == "lunch"
    hit = get_preset("lunch", paths=paths)
    assert hit is not None
    assert hit["id"] == "my_lunch"
    expanded = expand_preset_lines("lunch", paths=paths)
    assert expanded.get("ok") is True
    built = expand_preset_log_args("lunch", paths=paths)
    assert built.get("ok") is True
    out = run_life_meal_preset_log(
        {
            "name": "lunch",
            "lines": built["lines"],
            "resolve": {**(built.get("resolve") or {}), "bind_authority": "meal_spine"},
            "confirmed": True,
        }
    )
    assert out.get("ok") is True


def test_preset_confirm_rows_have_unique_keys(data_root) -> None:
    """Two-line preset must not share query_norm (HUD radio + Confirm pool)."""
    paths = get_paths()
    egg = _egg(paths)
    rice = _rice(paths)
    save_preset(
        name="my lunch",
        components=[
            {
                "ref_id": egg["food_ref_id"],
                "display_name": egg["name"],
                "serving_qty": 100,
                "serving_unit": "g",
                "serving_grams": 100,
                "provenance": "custom",
                "nutrients": {
                    "energy_kcal": 155,
                    "protein_g": 12.6,
                    "fat_g": 10.6,
                    "carb_g": 1.1,
                },
            },
            {
                "ref_id": rice["food_ref_id"],
                "display_name": rice["name"],
                "serving_qty": 100,
                "serving_unit": "g",
                "serving_grams": 100,
                "provenance": "custom",
                "nutrients": {
                    "energy_kcal": 130,
                    "protein_g": 2.7,
                    "fat_g": 0.3,
                    "carb_g": 28.0,
                },
            },
        ],
        confirmed=True,
        paths=paths,
    )
    built = expand_preset_log_args("lunch", paths=paths)
    rows = (built.get("resolve") or {}).get("rows") or []
    assert len(rows) == 2
    keys = [str(r.get("query_norm") or "") for r in rows]
    assert all(keys) and len(set(keys)) == 2
    selected = {str(r["query_norm"]): str(r["proposed_ref_id"]) for r in rows}
    patched = _patch_meal_confirm_selection(
        {"lines": built["lines"], "resolve": built["resolve"]},
        selected,
    )
    assert [ln["ref_id"] for ln in patched["lines"]] == [
        egg["food_ref_id"],
        rice["food_ref_id"],
    ]
    out = run_life_meal_preset_log(
        {
            "name": "lunch",
            "lines": patched["lines"],
            "resolve": {**(patched.get("resolve") or {}), "bind_authority": "meal_spine"},
            "confirmed": True,
        }
    )
    assert out.get("ok") is True


def test_estimate_tagged_on_draft_add(data_root) -> None:
    paths = get_paths()
    egg = _egg(paths)
    set_favorite(
        query="eggs",
        ref_id=egg["food_ref_id"],
        label=egg["name"],
        confirmed=True,
        paths=paths,
    )
    assert wants_estimate("log omelette (estimate)")
    sid = "testestimate03"
    run_life_meal_draft_start({"session_id": sid})
    built = build_draft_add_from_utterance(
        "5 eggs (estimate)",
        session_id=sid,
        fetch_remote=False,
        paths=paths,
    )
    assert built.get("ok") is True
    assert built.get("estimate") is True
    assert built["lines"][0].get("provenance") == "estimate"
