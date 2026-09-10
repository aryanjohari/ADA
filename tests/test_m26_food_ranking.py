"""M26 Phase 3 — food ranking, favorites sticky, Dream food slice + path integrity."""

from __future__ import annotations

import json

import pytest

from ada.cortex.adapter import CortexTurn, ProposedToolCall
from ada.harness.loop import run_turn
from ada.harness.meal_spine import build_meal_log_args
from ada.harness.pack_router import route_utterance
from ada.harness.resolve_gate import (
    candidate_matches_query,
    decide_food_bind,
    implausible_branded_junk,
    processed_food_mismatch,
)
from ada.harness.session import ChatSession
from ada.io.paths import get_paths
from ada.logs.connection import open_life_db
from ada.logs.favorites import get_favorite, load_favorites
from ada.logs.food import insert_food, search_foods_resolved
from ada.logs.meals import meal_log
from ada.tools.life_tools import run_life_meal_log


class _ShouldNotRunAdapter:
    model = "fake"

    def generate(self, *, system, contents, tools=None):
        raise AssertionError("pack fast-path should finish before model generate")


def test_parse_glued_qty_grams() -> None:
    """Phone NL 250g (no space) must strip qty from search query."""
    from ada.harness.meal_spine import _parse_piece

    q, qty, unit, grams = _parse_piece("250g cooked salmon")
    assert q == "cooked salmon"
    assert qty == 250.0
    assert unit == "g"
    assert grams == 250.0
    q2, _, _, g2 = _parse_piece("300 grams of cooked white rice")
    assert "rice" in q2 and "300" not in q2
    assert g2 == 300.0


def test_route_slotless_multi_meal_hits_pack() -> None:
    """Log salmon+rice without meal slot still routes meal_log (M26 pack fence)."""
    r = route_utterance(
        "Log 250 grams cooked salmon and 300 gram cooked white rice"
    )
    assert r is not None
    assert r["tool"] == "life_meal_log"
    assert r["verb"] == "meal_log"
    utt = str(r["args"].get("utterance") or "").lower()
    assert "salmon" in utt and "rice" in utt
    assert r["args"].get("meal_slot") is None


def test_route_snacks_plural_and_bare_multi() -> None:
    """snacks plural + bare grams+and+slot still pack-route."""
    snacks = route_utterance(
        "Log 50 grams of salmon and 100 grams of cooked white rice for snacks"
    )
    assert snacks is not None
    assert snacks["tool"] == "life_meal_log"
    assert snacks["args"].get("meal_slot") == "snack"

    bare = route_utterance(
        "250g cooked chicken breast and 300g cooked white rice for lunch"
    )
    assert bare is not None
    assert bare["tool"] == "life_meal_log"
    assert bare["args"].get("meal_slot") == "lunch"


def test_slotless_multi_uses_meal_spine_not_freestyle(data_root) -> None:
    """Pack fast-path owns slotless multi — cortex never freestyle name-only."""
    paths = get_paths()
    insert_food(
        name="Fish, salmon, Atlantic, farmed, cooked, dry heat",
        source="usda_fdc",
        nutrients_per_100g={
            "energy_kcal": 206,
            "protein_g": 22.1,
            "fat_g": 12.4,
            "carb_g": 0,
        },
        paths=paths,
    )
    insert_food(
        name="Rice, white, long-grain, cooked",
        source="usda_fdc",
        nutrients_per_100g={
            "energy_kcal": 130,
            "protein_g": 2.7,
            "fat_g": 0.3,
            "carb_g": 28.0,
        },
        paths=paths,
    )
    session = ChatSession(mode="agent")
    result = run_turn(
        session,
        "Log 250g cooked salmon and 300g cooked white rice",
        _ShouldNotRunAdapter(),
    )
    assert result.stop_reason in {"pack_fast_path", "missing_life_receipt"}
    meal_calls = [
        r for r in result.tool_receipts if str(r.get("tool") or "") == "life_meal_log"
    ]
    # Spine may Confirm or write — but never freestyle cortex path.
    assert result.stop_reason != "completed" or meal_calls


def test_freestyle_name_only_meal_refuses_no_db_row(data_root) -> None:
    """display_name-only life_meal_log → empty_macros, zero new meal rows."""
    paths = get_paths()
    with open_life_db(paths=paths) as conn:
        before = int(conn.execute("SELECT COUNT(*) AS n FROM meals").fetchone()["n"])
    out = run_life_meal_log(
        {
            "receipt_id": "m26-refuse-name-only",
            "lines": [
                {"display_name": "cooked salmon", "serving_grams": 250},
                {"display_name": "cooked white rice", "serving_grams": 300},
            ],
        }
    )
    assert out.get("ok") is False
    assert out.get("reason") == "spine_required"
    with open_life_db(paths=paths) as conn:
        after = int(conn.execute("SELECT COUNT(*) AS n FROM meals").fetchone()["n"])
        orphans = conn.execute(
            "SELECT COUNT(*) AS n FROM meals WHERE receipt_id = ?",
            ("m26-refuse-name-only",),
        ).fetchone()["n"]
    assert after == before
    assert int(orphans) == 0


def test_mouth_refused_meal_does_not_claim_logged(data_root) -> None:
    """Freestyle empty_macros must not leave final text claiming Logged (M23)."""

    class _LiarAck:
        model = "fake"
        _n = 0

        def generate(self, *, system, contents, tools=None):
            self._n += 1
            if self._n == 1:
                return CortexTurn(
                    text=None,
                    tool_calls=[
                        ProposedToolCall(
                            name="life_meal_log",
                            args={
                                "lines": [
                                    {
                                        "display_name": "cooked salmon",
                                        "serving_grams": 250,
                                    }
                                ]
                            },
                            call_id="lie-meal",
                        )
                    ],
                )
            return CortexTurn(
                text="Logged the salmon. Entries are on the board.",
                tool_calls=[],
            )

    session = ChatSession(mode="agent")
    # Utterance that does not pack-route (no log+and / no slot) so freestyle runs.
    result = run_turn(session, "please record salmon somehow", _LiarAck())
    text = (result.text or "").lower()
    assert "logged" not in text
    assert "on the board" not in text
    assert "couldn't log" in text or "didn't save" in text or "empty" in text or "spine" in text


def test_salmon_query_rejects_emu_without_salmon_stem() -> None:
    """Token overlap must not bind emu when query asks for salmon."""
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


def test_processed_food_mismatch_demotes_breaded_tenders() -> None:
    """Plain cooked query must not prefer breaded tenders when plain breast exists."""
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


def test_search_resolved_prefers_plain_breast_over_breaded(data_root) -> None:
    """search_foods_resolved pool sort — plain breast ranks above breaded tenders."""
    paths = get_paths()
    insert_food(
        name="Chicken breast tenders, breaded, cooked, microwaved",
        source="usda_fdc",
        external_id="171514",
        nutrients_per_100g={
            "energy_kcal": 250,
            "protein_g": 23,
            "fat_g": 12,
            "carb_g": 14,
        },
        paths=paths,
    )
    plain = insert_food(
        name="Chicken, broilers or fryers, breast, meat only, cooked, roasted",
        source="usda_fdc",
        external_id="05064",
        nutrients_per_100g={
            "energy_kcal": 165,
            "protein_g": 31,
            "fat_g": 3.6,
            "carb_g": 0,
        },
        paths=paths,
    )
    hits = search_foods_resolved(
        "cooked chicken breast",
        limit=5,
        fetch_remote=False,
        paths=paths,
    )
    assert hits
    assert hits[0]["ref_id"] == plain["food_ref_id"]


def test_remote_multi_hit_prefers_plain_breast_over_breaded_top1(data_root, monkeypatch) -> None:
    """1c509c18…: USDA pageSize>1 must surface plain roasted when top-1 is breaded."""
    from ada.logs import food as food_mod

    paths = get_paths()
    insert_food(
        name="Chicken breast tenders, breaded, cooked, microwaved",
        source="usda_fdc",
        external_id="171514",
        nutrients_per_100g={
            "energy_kcal": 250,
            "protein_g": 23,
            "fat_g": 12,
            "carb_g": 14,
        },
        paths=paths,
    )

    def _fake_hits(query, *, page_size=8, api_key=None, http_get=None):
        return [
            {
                "name": "Chicken breast tenders, breaded, cooked, microwaved",
                "brand": None,
                "source": "usda_fdc",
                "external_id": "171514",
                "nutrients_per_100g": {
                    "energy_kcal": 250,
                    "protein_g": 23,
                    "fat_g": 12,
                    "carb_g": 14,
                },
                "data_type": "SR Legacy",
            },
            {
                "name": "Chicken, broilers or fryers, breast, meat only, cooked, roasted",
                "brand": None,
                "source": "usda_fdc",
                "external_id": "171477",
                "nutrients_per_100g": {
                    "energy_kcal": 165,
                    "protein_g": 31,
                    "fat_g": 3.6,
                    "carb_g": 0,
                },
                "data_type": "SR Legacy",
            },
        ]

    monkeypatch.setattr(food_mod, "fetch_usda_search_hits", _fake_hits)
    monkeypatch.setenv("ADA_DATA_ROOT", str(paths.root))

    hits = search_foods_resolved(
        "cooked chicken breast",
        limit=5,
        fetch_remote=True,
        paths=paths,
    )
    assert hits
    assert "breaded" not in (hits[0].get("name") or "").lower()
    assert "breast" in (hits[0].get("name") or "").lower()
    assert "meat only" in (hits[0].get("name") or "").lower()

    from ada.harness.meal_spine import build_meal_log_args

    built = build_meal_log_args(
        "100 grams cooked chicken breast",
        fetch_remote=True,
        paths=paths,
    )
    assert built.get("ok") is True
    assert built.get("lines")
    name = str(built["lines"][0].get("display_name") or "").lower()
    assert "breaded" not in name
    assert "tenders" not in name
    prop = (built.get("resolve") or {}).get("rows") or []
    if prop:
        assert "breaded" not in str(prop[0].get("proposed_ref_id") or "")
        # proposed display via line already checked; also candidates may include breaded
        proposed_label = ""
        for c in prop[0].get("candidates") or []:
            if c.get("ref_id") == prop[0].get("proposed_ref_id"):
                proposed_label = str(c.get("label") or "")
                break
        if proposed_label:
            assert "breaded" not in proposed_label.lower()


def test_implausible_branded_junk_mars_eggs_still_dead() -> None:
    """Mars EGGS candy regression — must not sole-bind generic egg query."""
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
    assert implausible_branded_junk("eggs", candy) is True
    decision = decide_food_bind(
        query="eggs",
        candidates=[candy],
        favorite=None,
    )
    assert decision.get("needs_confirm") is True
    assert "no_favorite" in (decision.get("reasons") or [])


def test_confirm_yes_writes_favorite_then_silent_bind(data_root) -> None:
    """First Confirm Yes → nutrition_favorites; second identical query silent-binds."""
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
    insert_food(
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

    first = build_meal_log_args(
        "5 eggs",
        meal_slot="breakfast",
        fetch_remote=False,
        paths=paths,
    )
    assert first.get("ok") is True
    assert first.get("needs_confirm") is True
    resolve = first.get("resolve") or {}
    assert resolve.get("rows")

    out = run_life_meal_log(
        {
            "receipt_id": "r-fav-1",
            "lines": first["lines"],
            "meal_slot": "breakfast",
            "confirmed": True,
            "save_favorite": True,
            "resolve": resolve,
        }
    )
    assert out.get("ok") is True
    fav = get_favorite("eggs", paths=paths)
    assert fav is not None
    assert fav["ref_id"] == egg["food_ref_id"]

    second = build_meal_log_args(
        "5 eggs",
        meal_slot="breakfast",
        fetch_remote=False,
        paths=paths,
    )
    assert second.get("needs_confirm") is False
    assert second["lines"][0]["ref_id"] == egg["food_ref_id"]
    reasons = (second.get("resolve") or {}).get("reasons") or []
    assert "favorite_miss" not in reasons


def test_save_favorite_defaults_true_on_confirm(data_root) -> None:
    """Confirm replay without explicit save_favorite still writes favorite when resolve present."""
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
    built = build_meal_log_args("5 eggs", fetch_remote=False, paths=paths)
    resolve = built.get("resolve") or {}
    run_life_meal_log(
        {
            "receipt_id": "r-fav-2",
            "lines": built["lines"],
            "confirmed": True,
            "resolve": resolve,
        }
    )
    fav = load_favorites(paths=paths)["favorites"].get("eggs")
    assert fav is not None
    assert fav["ref_id"] == egg["food_ref_id"]