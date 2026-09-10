"""M27 falsifiers — unified catalog ranking policy."""

from __future__ import annotations

import pytest

from ada.harness.catalog_rank import (
    catalog_form_mismatch,
    macro_implausible,
    rank_catalog_bind,
    rank_catalog_candidates,
)
from ada.harness.resolve_gate import (
    candidate_matches_query,
    decide_food_bind,
    implausible_branded_junk,
    processed_food_mismatch,
)
from ada.io.paths import get_paths
from ada.logs.food import insert_food, search_foods_resolved


def _thigh_macros() -> dict:
    return {
        "energy_kcal": 180,
        "protein_g": 24,
        "fat_g": 9,
        "carb_g": 0,
    }


def test_skin_on_braised_thigh_demoted_for_plain_query() -> None:
    """F-M27-1: chicken thigh must not silent-bind skin-on braised row."""
    skin_on = {
        "ref_id": "fdc:skin-thigh",
        "name": "Chicken thigh, skin-on, braised",
        "score": 1.0,
        "nutrients": _thigh_macros(),
    }
    plain = {
        "ref_id": "fdc:plain-thigh",
        "name": "Chicken, broiler, thigh, meat only, cooked, roasted",
        "score": 0.95,
        "nutrients": _thigh_macros(),
    }
    assert catalog_form_mismatch("chicken thigh", skin_on, domain="food") is True
    assert catalog_form_mismatch("chicken thigh", plain, domain="food") is False

    ranked = rank_catalog_candidates("chicken thigh", [skin_on, plain], domain="food")
    assert ranked[0]["ref_id"] == "fdc:plain-thigh"

    decision = decide_food_bind(
        query="chicken thigh",
        candidates=[skin_on, plain],
        favorite=None,
    )
    assert decision.get("proposed_ref_id") == "fdc:plain-thigh"
    assert decision.get("needs_confirm") is True


def test_mars_eggs_still_demoted() -> None:
    """F-M27 regression: Mars EGGS candy must not sole-bind generic egg query."""
    candy = {
        "ref_id": "mars-eggs",
        "name": "EGGS",
        "brand": "Mars Chocolate",
        "score": 1.0,
        "nutrients": {
            "energy_kcal": 571,
            "protein_g": 3.6,
            "fat_g": 35,
            "carb_g": 58,
        },
    }
    assert macro_implausible("eggs", candy) is True
    assert implausible_branded_junk("eggs", candy) is True

    decision = decide_food_bind(query="eggs", candidates=[candy], favorite=None)
    assert decision.get("needs_confirm") is True
    assert "no_favorite" in (decision.get("reasons") or [])


def test_breaded_tenders_demoted_for_plain_breast() -> None:
    """Regression: plain breast ranks above breaded tenders."""
    breaded = {
        "ref_id": "fdc:171514",
        "name": "Chicken breast tenders, breaded, cooked, microwaved",
        "score": 1.0,
        "nutrients": {
            "energy_kcal": 250,
            "protein_g": 23,
            "fat_g": 12,
            "carb_g": 14,
        },
    }
    plain = {
        "ref_id": "fdc:plain-breast",
        "name": "Chicken, broilers or fryers, breast, meat only, cooked, roasted",
        "score": 0.9,
        "nutrients": {
            "energy_kcal": 165,
            "protein_g": 31,
            "fat_g": 3.6,
            "carb_g": 0,
        },
    }
    assert processed_food_mismatch("cooked chicken breast", breaded) is True
    assert processed_food_mismatch("cooked chicken breast", plain) is False

    decision = decide_food_bind(
        query="cooked chicken breast",
        candidates=[breaded, plain],
        favorite=None,
    )
    assert decision.get("proposed_ref_id") == "fdc:plain-breast"


def test_breaded_not_proposed_when_plain_in_pool() -> None:
    """F-M27 / 1c509c18…: propose-pool must not default breaded when plain exists."""
    breaded = {
        "ref_id": "fdc:171514",
        "name": "Chicken breast tenders, breaded, cooked, microwaved",
        "score": 1.0,
        "nutrients": {
            "energy_kcal": 250,
            "protein_g": 23,
            "fat_g": 12,
            "carb_g": 14,
        },
    }
    plain = {
        "ref_id": "fdc:171477",
        "name": "Chicken, broilers or fryers, breast, meat only, cooked, roasted",
        "score": 0.5,
        "nutrients": {
            "energy_kcal": 165,
            "protein_g": 31,
            "fat_g": 3.6,
            "carb_g": 0,
        },
    }
    decision = rank_catalog_bind(
        "cooked chicken breast",
        [breaded, plain],
        domain="food",
        favorite=None,
    )
    assert decision.get("proposed_ref_id") == "fdc:171477"
    assert "form_mismatch" not in (decision.get("reasons") or [])


def test_form_mismatch_reason_when_only_breaded() -> None:
    """Only processed hits → Confirm with form_mismatch reason."""
    breaded = {
        "ref_id": "fdc:171514",
        "name": "Chicken breast tenders, breaded, cooked, microwaved",
        "score": 1.0,
        "nutrients": {
            "energy_kcal": 250,
            "protein_g": 23,
            "fat_g": 12,
            "carb_g": 14,
        },
    }
    decision = rank_catalog_bind(
        "cooked chicken breast",
        [breaded],
        domain="food",
        favorite=None,
    )
    assert decision.get("needs_confirm") is True
    assert "form_mismatch" in (decision.get("reasons") or [])
    assert decision.get("proposed_ref_id") == "fdc:171514"


def test_salmon_vs_emu_head_noun_gate() -> None:
    """Regression: head-noun gate rejects emu for salmon query."""
    emu = {
        "ref_id": "fdc:emu",
        "name": "Emu, full rump, raw",
        "score": 1.0,
        "nutrients": {
            "energy_kcal": 108,
            "protein_g": 22.5,
            "fat_g": 1.6,
            "carb_g": 0,
        },
    }
    salmon = {
        "ref_id": "fdc:salmon",
        "name": "Fish, salmon, Atlantic, farmed, cooked, dry heat",
        "score": 0.9,
        "nutrients": {
            "energy_kcal": 206,
            "protein_g": 22.1,
            "fat_g": 12.4,
            "carb_g": 0,
        },
    }
    assert candidate_matches_query("cooked salmon fillet", emu) is False
    assert candidate_matches_query("cooked salmon fillet", salmon) is True

    decision = decide_food_bind(
        query="cooked salmon fillet",
        candidates=[emu, salmon],
        favorite=None,
    )
    assert decision.get("proposed_ref_id") == "fdc:salmon"


def test_glutinous_rice_demoted_for_white_rice_query() -> None:
    """F-M27: glutinous rice demoted below plain white rice."""
    glutinous = {
        "ref_id": "fdc:glutinous",
        "name": "Rice, glutinous, cooked",
        "score": 1.0,
        "nutrients": {
            "energy_kcal": 97,
            "protein_g": 2.0,
            "fat_g": 0.2,
            "carb_g": 21.0,
        },
    }
    white = {
        "ref_id": "fdc:white",
        "name": "Rice, white, long-grain, cooked",
        "score": 0.95,
        "nutrients": {
            "energy_kcal": 130,
            "protein_g": 2.7,
            "fat_g": 0.3,
            "carb_g": 28.0,
        },
    }
    assert catalog_form_mismatch("white rice", glutinous, domain="food") is True
    assert catalog_form_mismatch("white rice", white, domain="food") is False

    ranked = rank_catalog_candidates("white rice", [glutinous, white], domain="food")
    assert ranked[0]["ref_id"] == "fdc:white"


def test_chickpeas_generic_ranks_above_branded(data_root) -> None:
    """Generic boiled chickpeas rank above branded Lowe's when query is chickpeas."""
    paths = get_paths()
    branded = insert_food(
        name="Chickpeas",
        source="usda_fdc",
        brand="Lowe's",
        external_id="brand-chick",
        nutrients_per_100g={
            "energy_kcal": 120,
            "protein_g": 5,
            "fat_g": 2,
            "carb_g": 18,
        },
        paths=paths,
    )
    generic = insert_food(
        name="Chickpeas, boiled, cooked, drained",
        source="usda_fdc",
        external_id="gen-chick",
        nutrients_per_100g={
            "energy_kcal": 164,
            "protein_g": 8.9,
            "fat_g": 2.6,
            "carb_g": 27.4,
        },
        paths=paths,
    )
    hits = search_foods_resolved("chickpeas", limit=5, fetch_remote=False, paths=paths)
    assert hits
    assert hits[0]["ref_id"] == generic["food_ref_id"]
    assert hits[0]["ref_id"] != branded["food_ref_id"]


def test_silent_bind_requires_favorite_not_high_score() -> None:
    """Silent bind only on favorite hit; high score alone → Confirm."""
    egg = {
        "ref_id": "fdc:egg",
        "name": "Egg, whole, boiled or poached",
        "score": 1.0,
        "nutrients": {
            "energy_kcal": 155,
            "protein_g": 12.6,
            "fat_g": 10.6,
            "carb_g": 1.1,
        },
    }
    favorite = {"ref_id": "fdc:egg", "label": "Egg, whole, boiled or poached"}

    silent = rank_catalog_bind(
        "eggs",
        [egg],
        domain="food",
        favorite=favorite,
    )
    assert silent.get("ok") is True
    assert silent.get("needs_confirm") is False

    # High score without favorite → Confirm
    confirm = rank_catalog_bind("eggs", [egg], domain="food", favorite=None)
    assert confirm.get("needs_confirm") is True
    assert "no_favorite" in (confirm.get("reasons") or [])


def test_no_silent_bind_when_head_noun_absent() -> None:
    """F-M27-4: no silent bind when head noun absent from candidate name."""
    banana = {
        "ref_id": "fdc:banana",
        "name": "Banana, raw",
        "score": 1.0,
        "nutrients": {
            "energy_kcal": 89,
            "protein_g": 1.1,
            "fat_g": 0.3,
            "carb_g": 23,
        },
    }
    favorite = {"ref_id": "fdc:banana", "label": "Banana, raw"}

    decision = rank_catalog_bind(
        "eggs",
        [banana],
        domain="food",
        favorite=favorite,
    )
    assert decision.get("ok") is False
    assert decision.get("reason") == "no_name_match"
    assert decision.get("proposed_ref_id") is None


def test_gym_form_mismatch_stub() -> None:
    """Gym domain form mismatch is a no-op stub in Step 2."""
    assert catalog_form_mismatch("barbell squat", {"name": "Cable squat"}, domain="gym") is False


def test_gym_bind_raises_not_implemented() -> None:
    """Gym bind not implemented in Step 2."""
    with pytest.raises(NotImplementedError):
        rank_catalog_bind("squat", [], domain="gym")


def test_null_macro_branded_demoted_below_generic_with_macros() -> None:
    """Branded null-CORE ranks below NFS/generic rows with honest macros."""
    branded_null = {
        "ref_id": "fdc:branded-mash",
        "name": "MASHED POTATOES",
        "brand": "Acme",
        "score": 1.0,
        "nutrients": {
            "energy_kcal": None,
            "protein_g": None,
            "fat_g": None,
            "carb_g": None,
        },
    }
    nfs = {
        "ref_id": "fdc:nfs-mash",
        "name": "Potato, mashed, NFS",
        "score": 0.9,
        "nutrients": {
            "energy_kcal": 106,
            "protein_g": 1.9,
            "fat_g": 4.2,
            "carb_g": 14.3,
        },
    }
    ranked = rank_catalog_candidates("mashed potato", [branded_null, nfs], domain="food")
    assert ranked[0]["ref_id"] == "fdc:nfs-mash"


def test_dry_legume_demoted_when_query_says_cooked() -> None:
    """Cooked/boiled query demotes dry/raw candidate names."""
    dry = {
        "ref_id": "fdc:dry-gram",
        "name": "Beans, black gram, mature seeds, dry, raw",
        "score": 1.0,
        "nutrients": {
            "energy_kcal": 341,
            "protein_g": 25.2,
            "fat_g": 1.6,
            "carb_g": 58.9,
        },
    }
    cooked = {
        "ref_id": "fdc:cooked-gram",
        "name": "Beans, black gram, mature seeds, cooked, boiled",
        "score": 0.95,
        "nutrients": {
            "energy_kcal": 132,
            "protein_g": 8.7,
            "fat_g": 0.5,
            "carb_g": 23.5,
        },
    }
    ranked = rank_catalog_candidates(
        "cooked black gram", [dry, cooked], domain="food"
    )
    assert ranked[0]["ref_id"] == "fdc:cooked-gram"
