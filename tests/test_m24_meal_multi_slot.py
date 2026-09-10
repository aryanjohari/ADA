"""M24 Slice 1 — meal multi-slot split + resolve Confirm + empty-macro guard."""

from __future__ import annotations

from pathlib import Path

import pytest

from ada.harness.loop import run_turn
from ada.harness.meal_spine import build_meal_log_args
from ada.harness.pack_router import MODEL_STRIP_CONFIRMED, route_utterance
from ada.harness.resolve_gate import brand_vs_query_fight, decide_food_bind
from ada.harness.session import ChatSession
from ada.hud.routes_api import _CONFIRMABLE_TOOLS
from ada.io.paths import get_paths
from ada.logs.connection import open_life_db
from ada.logs.favorites import set_favorite
from ada.logs.food import insert_food


class _ShouldNotRunAdapter:
    model = "fake"

    def generate(self, *, system, contents, tools=None):
        raise AssertionError("pack fast-path should finish before model generate")


def test_split_coffee_and_eggs() -> None:
    """Decompose multi-item meal NL into pieces (F-M24-1 prep)."""
    from ada.harness.meal_spine import _SPLIT, _parse_piece, _strip_meal_slot_words

    cleaned = _strip_meal_slot_words(
        "a cup of coffee and 7 boiled eggs", meal_slot="breakfast"
    )
    parts = [p.strip() for p in _SPLIT.split(cleaned) if p.strip()]
    assert len(parts) == 2
    q0, qty0, _, _ = _parse_piece(parts[0])
    q1, qty1, _, grams1 = _parse_piece(parts[1])
    assert "coffee" in q0.lower()
    assert qty0 == 1.0
    assert "egg" in q1.lower()
    assert qty1 == 7.0
    assert grams1 == 350.0


def test_brand_fight_gott_coffee_needs_confirm(
    data_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Gott Ice Cream COFFEE vs query coffee → brand_fight Confirm (F-M24-1)."""
    monkeypatch.delenv("USDA_FDC_API_KEY", raising=False)
    secrets = data_root / "secrets"
    secrets.mkdir(exist_ok=True)
    monkeypatch.setenv("ADA_SECRETS_DIR", str(secrets))

    gott = insert_food(
        name="COFFEE",
        source="custom",
        brand="Gott Ice Cream, LLC",
        nutrients_per_100g={
            "energy_kcal": 310,
            "protein_g": 4,
            "fat_g": 18,
            "carb_g": 32,
        },
        paths=get_paths(),
    )
    cand = {
        "ref_id": gott["food_ref_id"],
        "name": "COFFEE",
        "brand": "Gott Ice Cream, LLC",
        "score": 1.0,
        "nutrients": {
            "energy_kcal": 310,
            "protein_g": 4,
            "fat_g": 18,
            "carb_g": 32,
        },
    }
    assert brand_vs_query_fight("coffee", cand) is True
    decision = decide_food_bind(query="coffee", candidates=[cand], favorite=None)
    assert decision["needs_confirm"] is True
    assert "brand_fight" in (decision.get("reasons") or [])

    banana = insert_food(
        name="Banana",
        source="custom",
        nutrients_per_100g={
            "energy_kcal": 89,
            "protein_g": 1.1,
            "fat_g": 0.3,
            "carb_g": 22.8,
        },
        default_serving_g=118,
        paths=get_paths(),
    )
    set_favorite(
        query="banana",
        ref_id=banana["food_ref_id"],
        label="Banana",
        confirmed=True,
        paths=get_paths(),
    )
    built = build_meal_log_args(
        "a cup of coffee and one banana",
        meal_slot="breakfast",
        fetch_remote=False,
    )
    assert built.get("needs_confirm") is True
    assert built.get("ok") is True
    reasons = (built.get("resolve") or {}).get("reasons") or []
    assert "brand_fight" in reasons
    session = ChatSession(mode="agent")
    result = run_turn(
        session,
        "log meal: a cup of coffee and one banana for breakfast",
        _ShouldNotRunAdapter(),
    )
    assert result.stop_reason == "pack_fast_path"
    meal_receipts = [
        r for r in result.tool_receipts if str(r.get("tool") or "") == "life_meal_log"
    ]
    assert meal_receipts
    assert meal_receipts[0].get("needs_confirm") or (
        meal_receipts[0].get("data") or {}
    ).get("needs_confirm")
    with open_life_db(paths=get_paths()) as conn:
        n = conn.execute("SELECT COUNT(*) AS n FROM meals").fetchone()["n"]
    assert int(n) == 0


def test_empty_macros_fail_closed(data_root: Path) -> None:
    """All-null CORE macros never durable-ok write (F-M24-2)."""
    insert_food(
        name="eggs",
        source="custom",
        nutrients_per_100g={
            "energy_kcal": None,
            "protein_g": None,
            "fat_g": None,
            "carb_g": None,
        },
        paths=get_paths(),
    )
    built = build_meal_log_args("7 boiled eggs", meal_slot="breakfast", fetch_remote=False)
    assert built.get("ok") is False
    assert any(
        str(m.get("reason") or "") == "empty_macros" for m in (built.get("misses") or [])
    )
    assert built.get("ask")


def test_coffee_eggs_hold_after_recover_fail(
    data_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """M24 hold whole meal when eggs recover fails — no partial write (F-M25-6)."""
    paths = get_paths()
    insert_food(
        name="COFFEE",
        source="custom",
        brand="Gott Ice Cream, LLC",
        nutrients_per_100g={
            "energy_kcal": 310,
            "protein_g": 4,
            "fat_g": 18,
            "carb_g": 32,
        },
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
    monkeypatch.setattr("ada.harness.meal_spine._RECOVER_SEARCHES", 1)

    built = build_meal_log_args(
        "a cup of coffee and 7 boiled eggs",
        meal_slot="breakfast",
        fetch_remote=False,
        paths=paths,
    )
    assert built.get("ok") is False
    assert built.get("lines") == []
    assert built.get("ask")
    with open_life_db(paths=paths) as conn:
        n = conn.execute("SELECT COUNT(*) AS n FROM meals").fetchone()["n"]
    assert int(n) == 0


def test_favorite_silent_bind(data_root: Path) -> None:
    """Sticky favorite → silent bind, needs_confirm False (M22 stores)."""
    inserted = insert_food(
        name="Banana",
        source="custom",
        nutrients_per_100g={
            "energy_kcal": 89,
            "protein_g": 1.1,
            "fat_g": 0.3,
            "carb_g": 22.8,
        },
        default_serving_g=118,
        paths=get_paths(),
    )
    set_favorite(
        query="banana",
        ref_id=inserted["food_ref_id"],
        label="Banana",
        confirmed=True,
        paths=get_paths(),
    )
    built = build_meal_log_args(
        "one medium banana", meal_slot="breakfast", fetch_remote=False
    )
    assert built["ok"] is True
    assert built.get("needs_confirm") is False
    assert built["lines"][0]["ref_id"] == inserted["food_ref_id"]


def test_route_coffee_eggs_pack_fence() -> None:
    r = route_utterance("Log a cup of coffee and 7 boiled eggs for breakfast")
    assert r is not None
    assert r["tool"] == "life_meal_log"
    assert r["args"].get("meal_slot") == "breakfast"
    assert "coffee" in str(r["args"].get("utterance") or "").lower()
    assert "egg" in str(r["args"].get("utterance") or "").lower()


def test_meal_confirm_allowlist() -> None:
    assert "life_meal_log" in _CONFIRMABLE_TOOLS
    assert "life_meal_log" in MODEL_STRIP_CONFIRMED


def test_chat_yes_does_not_bind_meal(data_root: Path) -> None:
    """MODEL_STRIP_CONFIRMED — cortex confirmed=true cannot bind (F-M24-4)."""
    from ada.cortex.adapter import CortexTurn, ProposedToolCall
    from ada.logs.food import insert_food as _ins

    gott = _ins(
        name="COFFEE",
        source="custom",
        brand="Gott Ice Cream, LLC",
        nutrients_per_100g={
            "energy_kcal": 310,
            "protein_g": 4,
            "fat_g": 18,
            "carb_g": 32,
        },
        paths=get_paths(),
    )

    class _ConfirmLiar:
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
                                        "display_name": "COFFEE",
                                        "ref_id": gott["food_ref_id"],
                                        "serving_qty": 1,
                                        "serving_unit": "serving",
                                        "nutrients": {
                                            "energy_kcal": 310,
                                            "protein_g": 4,
                                            "fat_g": 18,
                                            "carb_g": 32,
                                        },
                                    }
                                ],
                                "meal_slot": "breakfast",
                                "confirmed": True,
                                "resolve": {
                                    "reasons": ["brand_fight"],
                                    "candidates": [
                                        {
                                            "ref_id": gott["food_ref_id"],
                                            "label": "COFFEE",
                                            "brand": "Gott Ice Cream, LLC",
                                        }
                                    ],
                                },
                            },
                            call_id="liar",
                        )
                    ],
                )
            return CortexTurn(text="done", tool_calls=[])

    session = ChatSession(mode="agent")
    # No pack hint — freestyle model path; strip confirmed.
    result = run_turn(session, "yes", _ConfirmLiar())
    meal_receipts = [
        r for r in result.tool_receipts if str(r.get("tool") or "") == "life_meal_log"
    ]
    assert meal_receipts
    data = meal_receipts[0].get("data") or {}
    assert (
        meal_receipts[0].get("needs_confirm")
        or data.get("needs_confirm")
        or data.get("reason") == "spine_required"
    )
    with open_life_db(paths=get_paths()) as conn:
        n = conn.execute("SELECT COUNT(*) AS n FROM meals").fetchone()["n"]
    assert int(n) == 0
