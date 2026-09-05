"""M26 v1.8/v1.9 — food path integrity: spine resolve required for meal_log writes."""

from __future__ import annotations

import pytest

from ada.cortex.adapter import CortexTurn, ProposedToolCall
from ada.harness.loop import _model_tool_blocked, run_turn
from ada.harness.meal_spine import build_meal_log_args
from ada.harness.pack_router import (
    is_meal_log_utterance,
    meal_log_fast_path_args,
    route_utterance,
)
from ada.harness.resolve_gate import candidate_matches_query, decide_food_bind, extract_food_stems
from ada.harness.session import ChatSession
from ada.io.paths import get_paths
from ada.logs.connection import open_life_db
from ada.logs.favorites import set_favorite
from ada.logs.food import insert_food
from ada.tools.life_tools import run_life_meal_log


class _ShouldNotRunAdapter:
    model = "fake"

    def generate(self, *, system, contents, tools=None):
        raise AssertionError("meal spine fast-path should finish before model generate")


def _spine_resolve(**extra: object) -> dict:
    base = {
        "bind_authority": "meal_spine",
        "needs_confirm": False,
        "reasons": [],
        "rows": [],
        "candidates": [],
    }
    base.update(extra)
    return base


def test_meal_log_without_resolve_refused(data_root) -> None:
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
    with open_life_db(paths=paths) as conn:
        before = int(conn.execute("SELECT COUNT(*) AS n FROM meals").fetchone()["n"])
    out = run_life_meal_log(
        {
            "receipt_id": "v18-refuse-freestyle",
            "lines": [{"ref_id": egg["food_ref_id"], "serving_grams": 100}],
        }
    )
    assert out.get("ok") is False
    assert out.get("reason") == "spine_required"
    assert out.get("error") == "spine_required"
    with open_life_db(paths=paths) as conn:
        after = int(conn.execute("SELECT COUNT(*) AS n FROM meals").fetchone()["n"])
        orphans = conn.execute(
            "SELECT COUNT(*) AS n FROM meals WHERE receipt_id = ?",
            ("v18-refuse-freestyle",),
        ).fetchone()["n"]
    assert after == before
    assert int(orphans) == 0


def test_meal_log_with_spine_resolve_silent_favorite(data_root) -> None:
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
    set_favorite(
        query="eggs",
        ref_id=egg["food_ref_id"],
        label=egg["name"],
        confirmed=True,
        paths=paths,
    )
    built = build_meal_log_args("5 eggs", fetch_remote=False, paths=paths)
    assert built.get("ok") is True
    assert built.get("needs_confirm") is False
    resolve = built.get("resolve") or {}
    assert resolve.get("bind_authority") == "meal_spine"

    with open_life_db(paths=paths) as conn:
        before = int(conn.execute("SELECT COUNT(*) AS n FROM meals").fetchone()["n"])
    out = run_life_meal_log(
        {
            "receipt_id": "v18-silent-fav",
            "lines": built["lines"],
            "resolve": resolve,
        }
    )
    assert out.get("ok") is True
    with open_life_db(paths=paths) as conn:
        after = int(conn.execute("SELECT COUNT(*) AS n FROM meals").fetchone()["n"])
    assert after == before + 1


def test_hud_confirmed_replay_still_writes(data_root) -> None:
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
    assert resolve.get("bind_authority") == "meal_spine"

    out = run_life_meal_log(
        {
            "receipt_id": "v18-hud-replay",
            "lines": built["lines"],
            "confirmed": True,
            "resolve": resolve,
            "save_favorite": True,
        }
    )
    assert out.get("ok") is True
    with open_life_db(paths=paths) as conn:
        row = conn.execute(
            "SELECT ref_id FROM meal_foods ORDER BY line_id DESC LIMIT 1"
        ).fetchone()
    assert row is not None
    assert str(row["ref_id"]) == egg["food_ref_id"]


def test_pack_route_okay_log_prefix() -> None:
    r = route_utterance("Okay log 100 grams cooked brown rice for snacks")
    assert r is not None
    assert r["tool"] == "life_meal_log"
    assert r["verb"] == "meal_log"
    assert r["args"].get("meal_slot") == "snack"
    assert "brown rice" in str(r["args"].get("utterance") or "").lower()


def test_pack_route_slotless_single() -> None:
    r = route_utterance("Log 250 grams cooked paneer")
    assert r is not None
    assert r["tool"] == "life_meal_log"
    assert r["args"].get("meal_slot") is None
    assert "paneer" in str(r["args"].get("utterance") or "").lower()


def test_pack_route_prose_not_meal_log() -> None:
    assert route_utterance("It's just paneer") is None


def test_black_gram_not_chickpeas() -> None:
    stems = extract_food_stems("cooked black gram")
    assert "black" in stems or "black_gram" in stems
    assert "gram" in stems or "black_gram" in stems
    chickpeas = {
        "ref_id": "fdc:chickpeas",
        "name": "Chickpeas (garbanzo beans, bengal gram), mature seeds, boiled",
        "nutrients": {
            "energy_kcal": 164,
            "protein_g": 8.9,
            "fat_g": 2.6,
            "carb_g": 27.4,
        },
    }
    black_gram = {
        "ref_id": "fdc:black-gram",
        "name": "Beans, black gram, mature seeds, cooked, boiled",
        "nutrients": {
            "energy_kcal": 132,
            "protein_g": 8.7,
            "fat_g": 0.5,
            "carb_g": 23.5,
        },
    }
    assert candidate_matches_query("black gram", chickpeas) is False
    assert candidate_matches_query("black gram", black_gram) is True
    glutinous = {
        "ref_id": "fdc:glutinous",
        "name": "Rice, white, glutinous, cooked",
        "nutrients": {
            "energy_kcal": 97,
            "protein_g": 2.0,
            "fat_g": 0.2,
            "carb_g": 21.1,
        },
    }
    brown = {
        "ref_id": "fdc:brown-rice",
        "name": "Rice, brown, long-grain, cooked",
        "nutrients": {
            "energy_kcal": 123,
            "protein_g": 2.7,
            "fat_g": 1.0,
            "carb_g": 25.6,
        },
    }
    assert candidate_matches_query("brown rice", glutinous) is False
    assert candidate_matches_query("brown rice", brown) is True


def test_run_turn_freestyle_meal_refused(data_root) -> None:
    paths = get_paths()
    insert_food(
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

    class _FreestyleRef:
        model = "fake"
        _n = 0

        def generate(self, *, system, contents, tools=None):
            self._n += 1
            if self._n == 1:
                row = insert_food(
                    name="Egg, whole, boiled or poached",
                    source="usda_fdc",
                    external_id="2707154b",
                    nutrients_per_100g={
                        "energy_kcal": 155,
                        "protein_g": 12.6,
                        "fat_g": 10.6,
                        "carb_g": 1.1,
                    },
                    paths=paths,
                )
                return CortexTurn(
                    text=None,
                    tool_calls=[
                        ProposedToolCall(
                            name="life_meal_log",
                            args={
                                "lines": [
                                    {
                                        "ref_id": row["food_ref_id"],
                                        "serving_grams": 250,
                                    }
                                ]
                            },
                            call_id="freestyle-ref",
                        )
                    ],
                )
            return CortexTurn(
                text="Logged that meal. Entries are on the board.",
                tool_calls=[],
            )

    with open_life_db(paths=paths) as conn:
        before = int(conn.execute("SELECT COUNT(*) AS n FROM meals").fetchone()["n"])
    session = ChatSession(mode="agent")
    result = run_turn(session, "please record salmon somehow", _FreestyleRef())
    text = (result.text or "").lower()
    assert "logged" not in text
    assert "on the board" not in text
    meal_obs = [
        r
        for r in result.tool_receipts
        if str(r.get("tool") or "") == "life_meal_log"
    ]
    assert meal_obs
    denied = [r for r in meal_obs if r.get("outcome") == "denied"]
    if denied:
        assert "meal_spine" in str(denied[0].get("denied_reason") or "")
    else:
        data = meal_obs[-1].get("data") or {}
        assert data.get("reason") == "spine_required" or data.get("error") == "spine_required"
    with open_life_db(paths=paths) as conn:
        after = int(conn.execute("SELECT COUNT(*) AS n FROM meals").fetchone()["n"])
    assert after == before


def test_meal_intent_forces_spine_without_pack_hint(
    data_root, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Meal NL always hits spine even when pack router returns None."""
    paths = get_paths()
    insert_food(
        name="Potato, mashed, NFS",
        source="usda_fdc",
        external_id="mashed-nfs",
        nutrients_per_100g={
            "energy_kcal": 106,
            "protein_g": 1.9,
            "fat_g": 4.2,
            "carb_g": 14.3,
        },
        paths=paths,
    )
    monkeypatch.setattr(
        "ada.harness.pack_router.route_utterance",
        lambda text, **kwargs: None,
    )
    _orig_build = build_meal_log_args

    def _local_build(utterance, **kwargs):
        return _orig_build(utterance, fetch_remote=False, paths=paths, **kwargs)

    monkeypatch.setattr("ada.harness.meal_spine.build_meal_log_args", _local_build)
    assert is_meal_log_utterance("Log 100 grams mashed potato")
    assert meal_log_fast_path_args("Log 100 grams mashed potato") is not None

    session = ChatSession(mode="agent")
    result = run_turn(
        session,
        "Log 100 grams mashed potato",
        _ShouldNotRunAdapter(),
    )
    assert result.stop_reason in {"pack_fast_path", "missing_life_receipt"}
    meal_obs = [
        r for r in result.tool_receipts if str(r.get("tool") or "") == "life_meal_log"
    ]
    assert meal_obs
    search_obs = [
        r for r in result.tool_receipts if str(r.get("tool") or "") == "life_food_search"
    ]
    assert search_obs


def test_cortex_meal_log_denied_on_meal_turn(data_root) -> None:
    """Model life_meal_log on meal utterance → tool_denied (spine owns writes)."""

    class _CortexMealLog:
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
                            args={"lines": [{"display_name": "eggs", "serving_grams": 50}]},
                            call_id="cortex-meal",
                        )
                    ],
                )
            return CortexTurn(text="ok", tool_calls=[])

    session = ChatSession(mode="agent")
    result = run_turn(session, "log something vague", _CortexMealLog())
    denied = [
        r
        for r in result.tool_receipts
        if r.get("tool") == "life_meal_log" and r.get("outcome") == "denied"
    ]
    assert denied
    assert "meal_spine" in str(denied[0].get("denied_reason") or "")


def test_cortex_food_search_denied_on_meal_turn(
    data_root, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Model life_food_search on meal log turn → denied; spine searched instead."""
    monkeypatch.setattr(
        "ada.harness.loop._fast_path_meal",
        lambda *args, **kwargs: (None, None),
    )

    class _CortexSearch:
        model = "fake"
        _n = 0

        def generate(self, *, system, contents, tools=None):
            self._n += 1
            if self._n == 1:
                return CortexTurn(
                    text=None,
                    tool_calls=[
                        ProposedToolCall(
                            name="life_food_search",
                            args={"query": "mashed potatoes"},
                            call_id="cortex-search",
                        )
                    ],
                )
            return CortexTurn(text="found some", tool_calls=[])

    paths = get_paths()
    insert_food(
        name="Potato, mashed, NFS",
        source="usda_fdc",
        external_id="mashed-nfs-2",
        nutrients_per_100g={
            "energy_kcal": 106,
            "protein_g": 1.9,
            "fat_g": 4.2,
            "carb_g": 14.3,
        },
        paths=paths,
    )
    session = ChatSession(mode="agent")
    result = run_turn(
        session,
        "Log 100 grams mashed potatoes",
        _CortexSearch(),
    )
    denied = [
        r
        for r in result.tool_receipts
        if r.get("tool") == "life_food_search" and r.get("outcome") == "denied"
    ]
    assert denied
    assert "meal_spine" in str(denied[0].get("denied_reason") or "")


def test_non_favorite_always_needs_confirm(data_root) -> None:
    """Brown rice and almond without favorite → needs_confirm with ranked picker rows."""
    paths = get_paths()
    brown = insert_food(
        name="Rice, brown, long-grain, cooked",
        source="usda_fdc",
        external_id="brown-rice",
        nutrients_per_100g={
            "energy_kcal": 123,
            "protein_g": 2.7,
            "fat_g": 1.0,
            "carb_g": 25.6,
        },
        paths=paths,
    )
    insert_food(
        name="Rice, brown, medium-grain, cooked",
        source="usda_fdc",
        external_id="brown-rice-med",
        nutrients_per_100g={
            "energy_kcal": 112,
            "protein_g": 2.3,
            "fat_g": 0.8,
            "carb_g": 23.5,
        },
        paths=paths,
    )
    insert_food(
        name="Rice, white, long-grain, cooked",
        source="usda_fdc",
        external_id="white-rice",
        nutrients_per_100g={
            "energy_kcal": 130,
            "protein_g": 2.7,
            "fat_g": 0.3,
            "carb_g": 28.0,
        },
        paths=paths,
    )
    insert_food(
        name="Nuts, almonds",
        source="usda_fdc",
        external_id="almonds",
        nutrients_per_100g={
            "energy_kcal": 579,
            "protein_g": 21.2,
            "fat_g": 49.9,
            "carb_g": 21.6,
        },
        paths=paths,
    )
    insert_food(
        name="Nuts, almond butter, plain, without salt added",
        source="usda_fdc",
        external_id="almond-butter",
        nutrients_per_100g={
            "energy_kcal": 614,
            "protein_g": 20.9,
            "fat_g": 55.5,
            "carb_g": 18.8,
        },
        paths=paths,
    )
    rice_built = build_meal_log_args(
        "100 grams cooked brown rice for snacks",
        fetch_remote=False,
        paths=paths,
    )
    assert rice_built.get("ok") is True
    assert rice_built.get("needs_confirm") is True
    rows = (rice_built.get("resolve") or {}).get("rows") or []
    assert len(rows) >= 1
    assert len(rows[0].get("candidates") or []) >= 2
    assert brown["food_ref_id"] in {
        str(c.get("ref_id")) for c in (rows[0].get("candidates") or [])
    }

    almond_built = build_meal_log_args(
        "10 grams almond for snacks",
        fetch_remote=False,
        paths=paths,
    )
    assert almond_built.get("ok") is True
    assert almond_built.get("needs_confirm") is True
    a_rows = (almond_built.get("resolve") or {}).get("rows") or []
    assert len(a_rows[0].get("candidates") or []) >= 2


def test_mashed_potato_null_macro_not_sole_propose(data_root) -> None:
    """Branded null-CORE mashed potatoes demoted; NFS/generic with macros preferred."""
    paths = get_paths()
    branded_null = insert_food(
        name="MASHED POTATOES",
        source="custom",
        brand="Some Brand",
        external_id="branded-mash",
        nutrients_per_100g={
            "energy_kcal": None,
            "protein_g": None,
            "fat_g": None,
            "carb_g": None,
        },
        paths=paths,
    )
    nfs = insert_food(
        name="Potato, mashed, NFS",
        source="usda_fdc",
        external_id="nfs-mash",
        nutrients_per_100g={
            "energy_kcal": 106,
            "protein_g": 1.9,
            "fat_g": 4.2,
            "carb_g": 14.3,
        },
        paths=paths,
    )
    decision = decide_food_bind(
        query="mashed potato",
        candidates=[
            {
                "ref_id": branded_null["food_ref_id"],
                "name": "MASHED POTATOES",
                "brand": "Some Brand",
                "score": 1.0,
                "nutrients": {
                    "energy_kcal": None,
                    "protein_g": None,
                    "fat_g": None,
                    "carb_g": None,
                },
            },
            {
                "ref_id": nfs["food_ref_id"],
                "name": "Potato, mashed, NFS",
                "score": 0.9,
                "nutrients": {
                    "energy_kcal": 106,
                    "protein_g": 1.9,
                    "fat_g": 4.2,
                    "carb_g": 14.3,
                },
            },
        ],
        favorite=None,
    )
    assert decision.get("proposed_ref_id") == nfs["food_ref_id"]
    assert decision.get("needs_confirm") is True
    assert not (decision.get("bind") or {}).get("macros_empty", False)

    built = build_meal_log_args(
        "100 grams mashed potato",
        fetch_remote=False,
        paths=paths,
    )
    assert built.get("ok") is True
    assert built.get("needs_confirm") is True
    rows = (built.get("resolve") or {}).get("rows") or []
    assert rows[0].get("proposed_ref_id") == nfs["food_ref_id"]


def test_confirm_preview_macros_write_when_db_thin(data_root) -> None:
    """Confirm Yes with picker preview kcal must write even if DB rehydrate is null.

    Root cause (55378c77…): Confirm cleared line nutrients then rehydrated from
    food_reference.db; thin/null CORE → empty_macros despite picker showing kcal.
    """
    from ada.hud.chat_service import _patch_meal_confirm_selection
    from ada.logs.food import update_food_nutrients

    paths = get_paths()
    brown = insert_food(
        name="Rice, brown, long-grain, cooked",
        source="usda_fdc",
        external_id="brown-rice-thin",
        nutrients_per_100g={
            "energy_kcal": 123,
            "protein_g": 2.7,
            "fat_g": 1.0,
            "carb_g": 25.6,
        },
        paths=paths,
    )
    insert_food(
        name="Rice, brown, medium-grain, cooked",
        source="usda_fdc",
        external_id="brown-rice-med-thin",
        nutrients_per_100g={
            "energy_kcal": 112,
            "protein_g": 2.3,
            "fat_g": 0.8,
            "carb_g": 23.5,
        },
        paths=paths,
    )
    built = build_meal_log_args(
        "100 grams cooked brown rice for snacks",
        fetch_remote=False,
        paths=paths,
    )
    assert built.get("needs_confirm") is True
    resolve = built.get("resolve") or {}
    rows = resolve.get("rows") or []
    assert rows
    proposed = str(rows[0].get("proposed_ref_id") or "")
    assert proposed
    # Simulate thin/null DB after spine built the line (Confirm rehydrate miss).
    update_food_nutrients(
        proposed,
        nutrients_per_100g={
            "energy_kcal": None,
            "protein_g": None,
            "fat_g": None,
            "carb_g": None,
        },
        paths=paths,
    )
    # Ensure resolve candidates carry preview macros (picker had kcal).
    cands = list(rows[0].get("candidates") or [])
    assert cands
    for c in cands:
        if str(c.get("ref_id")) == proposed and not c.get("nutrients"):
            c["nutrients"] = {
                "energy_kcal": 123,
                "protein_g": 2.7,
                "fat_g": 1.0,
                "carb_g": 25.6,
            }
            c["kcal_per_100g"] = 123
            c["macros_empty"] = False
    rows[0]["candidates"] = cands
    resolve["rows"] = rows

    stash = {
        "lines": built["lines"],
        "meal_slot": built.get("meal_slot"),
        "resolve": resolve,
        "save_favorite": False,
        "confirmed": False,
    }
    patched = _patch_meal_confirm_selection(stash, None)
    assert patched["lines"][0].get("ref_id") == proposed
    # Preview handoff should have restored nutrients on the line.
    assert (patched["lines"][0].get("nutrients") or {}).get("energy_kcal") is not None

    out = run_life_meal_log(
        {
            "receipt_id": "v110-confirm-preview",
            "lines": patched["lines"],
            "confirmed": True,
            "resolve": patched["resolve"],
            "save_favorite": False,
        }
    )
    assert out.get("ok") is True, out
    assert out.get("reason") != "empty_macros"


def test_eggs_favorite_silent_unchanged(data_root) -> None:
    """Eggs sticky favorite still silent-binds (no Confirm regression)."""
    paths = get_paths()
    egg = insert_food(
        name="Egg, whole, boiled or poached",
        source="usda_fdc",
        external_id="2707154-v110",
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
        label=egg["name"],
        confirmed=True,
        paths=paths,
    )
    built = build_meal_log_args("5 eggs", fetch_remote=False, paths=paths)
    assert built.get("ok") is True
    assert built.get("needs_confirm") is False
    out = run_life_meal_log(
        {
            "receipt_id": "v110-eggs-silent",
            "lines": built["lines"],
            "resolve": built.get("resolve"),
        }
    )
    assert out.get("ok") is True


def test_black_gram_not_chickpeas_bind(data_root) -> None:
    """Black gram query must not default to chickpeas/bengal gram."""
    paths = get_paths()
    chickpeas = insert_food(
        name="Chickpeas (garbanzo beans, bengal gram), mature seeds, boiled",
        source="usda_fdc",
        external_id="chickpeas",
        nutrients_per_100g={
            "energy_kcal": 164,
            "protein_g": 8.9,
            "fat_g": 2.6,
            "carb_g": 27.4,
        },
        paths=paths,
    )
    black = insert_food(
        name="Beans, black gram, mature seeds, cooked, boiled",
        source="usda_fdc",
        external_id="black-gram",
        nutrients_per_100g={
            "energy_kcal": 132,
            "protein_g": 8.7,
            "fat_g": 0.5,
            "carb_g": 23.5,
        },
        paths=paths,
    )
    decision = decide_food_bind(
        query="black gram",
        candidates=[
            {
                "ref_id": chickpeas["food_ref_id"],
                "name": chickpeas["name"],
                "score": 1.0,
                "nutrients": {
                    "energy_kcal": 164,
                    "protein_g": 8.9,
                    "fat_g": 2.6,
                    "carb_g": 27.4,
                },
            },
            {
                "ref_id": black["food_ref_id"],
                "name": black["name"],
                "score": 0.95,
                "nutrients": {
                    "energy_kcal": 132,
                    "protein_g": 8.7,
                    "fat_g": 0.5,
                    "carb_g": 23.5,
                },
            },
        ],
        favorite=None,
    )
    assert decision.get("proposed_ref_id") == black["food_ref_id"]
    assert candidate_matches_query("black gram", {"name": chickpeas["name"]}) is False

    built = build_meal_log_args(
        "100 grams black gram for lunch",
        fetch_remote=False,
        paths=paths,
    )
    assert built.get("ok") is True
    assert built.get("needs_confirm") is True
    rows = (built.get("resolve") or {}).get("rows") or []
    assert rows[0].get("proposed_ref_id") == black["food_ref_id"]
