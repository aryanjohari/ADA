"""M19a P0 falsifiers F1–F10 (M19a §13)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ada.cortex.charter import build_system_charter
from ada.harness.gym_spine import build_lift_log_args
from ada.harness.loop import run_turn
from ada.harness.session import ChatSession
from ada.harness.meal_spine import build_meal_log_args
from ada.hud.today import build_today
from ada.io.paths import get_paths
from ada.logs.connection import open_life_db
from ada.logs.food import barcode_lookup, insert_food
from ada.logs.gym_import import import_exercise_seed
from ada.memory.facts import ensure_prefs, save_prefs
from ada.tools.gateway import Gateway
from ada.tools.toolspec import WRITE_TOOL_NAMES


class _ShouldNotRunAdapter:
    model = "fake"

    def generate(self, *, system, contents, tools=None):
        raise AssertionError("meal fast-path should finish before model generate")


@pytest.mark.tier_a
def test_f1_observe_allows_nutrition_day_denies_meal_log(data_root: Path) -> None:
    """F1: macros require life_nutrition_day read path; writes denied in Observe."""
    ensure_prefs(get_paths())
    obs = Gateway(mode="observe")
    assert obs.execute("life_nutrition_day", {}).ok
    denied = obs.execute("life_meal_log", {"lines": [{"display_name": "x"}]})
    assert not denied.ok
    charter = build_system_charter(mode="agent")
    assert "life_nutrition_day" in charter


def test_f_p01a_charter_pack_hint_addendum() -> None:
    charter = build_system_charter(
        mode="agent",
        pack_hint={
            "verb": "meal_log",
            "tool": "life_meal_log",
            "args": {"utterance": "one banana", "meal_slot": "breakfast"},
            "preferred_tools": [
                "life_food_search",
                "life_meal_log",
                "life_nutrition_day",
            ],
        },
    )
    assert "Pack hint (this turn only):" in charter
    assert "life_meal_log" in charter
    assert "life_food_search -> life_meal_log -> life_nutrition_day" in charter
    cold = build_system_charter(mode="agent")
    assert "Pack hint (this turn only):" not in cold


@pytest.mark.tier_a
def test_f2_snapshot_immutable_after_refetch(data_root: Path) -> None:
    """F2: historical meal nutrients unchanged when cache updates."""
    paths = get_paths()
    insert_food(
        name="Old Food",
        source="custom",
        barcode="1112223334445",
        nutrients_per_100g={"energy_kcal": 100},
        paths=paths,
    )
    gw = Gateway(mode="agent")
    obs = gw.execute(
        "life_meal_log",
        {
            "lines": [
                {
                    "display_name": "Old Food",
                    "ref_id": "x",
                    "provenance": "barcode",
                    "nutrients": {"energy_kcal": 100},
                }
            ]
        },
    )
    meal_id = obs.data["meal_id"]
    insert_food(
        name="New Food",
        source="custom",
        barcode="1112223334445",
        nutrients_per_100g={"energy_kcal": 999},
        paths=paths,
    )
    with open_life_db(paths=paths) as conn:
        snap = conn.execute(
            "SELECT snapshot_json FROM meal_foods mf JOIN meals m ON m.meal_id = mf.meal_id WHERE m.meal_id = ?",
            (meal_id,),
        ).fetchone()["snapshot_json"]
    assert json.loads(snap)["nutrients"]["energy_kcal"] == 100


@pytest.mark.tier_a
def test_f3_no_parallel_running_timers(data_root: Path) -> None:
    """F3: only one running time block."""
    gw = Gateway(mode="agent")
    gw.execute("life_time_start", {"kind": "custom", "label": "a"})
    gw.execute("life_time_start", {"kind": "custom", "label": "b"})
    with open_life_db(paths=get_paths()) as conn:
        n = conn.execute(
            "SELECT COUNT(*) FROM time_blocks WHERE status = 'running'"
        ).fetchone()[0]
    assert n == 1


def test_f4_catalog_resolves_bench(data_root: Path) -> None:
    """F4: catalog match for known exercise."""
    import_exercise_seed(paths=get_paths())
    obs = Gateway(mode="agent").execute(
        "life_lift_log",
        {"sets": [{"exercise_name": "flat bench", "load_kg": 60, "reps": 5}]},
    )
    assert obs.ok


def test_f5_barcode_provenance_honest(data_root: Path) -> None:
    """F5: verified only with fetch provider."""
    paths = get_paths()

    def fake_get(url, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "status": 1,
            "product": {
                "product_name": "Honest Bar",
                "nutriments": {"energy-kcal_100g": 120},
            },
        }
        return resp

    r = barcode_lookup("5556667778889", paths=paths, http_get=fake_get)
    assert r["ok"]
    assert r.get("fetch_provider") == "open_food_facts"


@pytest.mark.tier_a
def test_f6_meal_write_has_receipt_id(data_root: Path) -> None:
    """F6: every meal write carries receipt_id."""
    obs = Gateway(mode="agent").execute(
        "life_meal_log",
        {"lines": [{"display_name": "egg", "provenance": "manual", "nutrients": {"energy_kcal": 70}}]},
    )
    assert obs.receipt_id
    with open_life_db(paths=get_paths()) as conn:
        row = conn.execute(
            "SELECT receipt_id FROM meals WHERE meal_id = ?",
            (obs.data["meal_id"],),
        ).fetchone()
    assert row["receipt_id"] == obs.receipt_id


@pytest.mark.tier_a
def test_f7_today_nutrition_from_rollup(data_root: Path) -> None:
    """F7: Today headline from SQL rollup only."""
    ensure_prefs(get_paths())
    Gateway(mode="agent").execute(
        "life_meal_log",
        {"lines": [{"display_name": "toast", "provenance": "manual", "nutrients": {"energy_kcal": 80}}]},
    )
    payload = build_today(paths=get_paths())
    assert payload["nutrition_headline"]["kcal"] == 80


@pytest.mark.tier_a
def test_f8_fact_overwrite_needs_confirm(data_root: Path) -> None:
    """F8: capture FACT overwrite triggers confirm."""
    paths = get_paths()
    ensure_prefs(paths)
    save_prefs({**ensure_prefs(paths), "brief_time": "06:00"}, paths=paths)
    obs = Gateway(mode="agent").execute(
        "life_capture",
        {"text": "x", "kind": "fact", "key": "prefs.brief_time", "value": "07:00"},
    )
    assert obs.needs_confirm or obs.data.get("needs_confirm")


def test_f9_no_api_key_in_observation(data_root: Path, monkeypatch) -> None:
    """F9: secrets not echoed in tool observations."""
    monkeypatch.setenv("USDA_FDC_API_KEY", "secret-test-key-xyz")
    obs = Gateway(mode="agent").execute(
        "life_food_search", {"query": "nothing", "fetch_remote": False}
    )
    blob = json.dumps(obs.as_observation())
    assert "secret-test-key" not in blob


@pytest.mark.tier_a
def test_f10_honest_partial_surfaced(data_root: Path) -> None:
    """F10: partial micros flagged."""
    Gateway(mode="agent").execute(
        "life_meal_log",
        {
            "lines": [
                {
                    "display_name": "mystery",
                    "provenance": "estimate",
                    "nutrients": {"energy_kcal": 50, "vitamin_d_ug": None},
                }
            ]
        },
    )
    day = Gateway(mode="observe").execute("life_nutrition_day", {})
    assert day.data.get("honest_partial") is True
    payload = build_today(paths=get_paths())
    if payload.get("nutrition_headline"):
        assert payload["nutrition_headline"].get("partial") is True


def test_meal_spine_builds_lines_from_local_food(data_root: Path) -> None:
    insert_food(
        name="Banana",
        source="custom",
        nutrients_per_100g={"energy_kcal": 89, "protein_g": 1.1, "carb_g": 22.8},
        default_serving_g=118,
        paths=get_paths(),
    )
    built = build_meal_log_args("one medium banana", meal_slot="breakfast", fetch_remote=False)
    assert built["ok"] is True
    assert built["meal_slot"] == "breakfast"
    assert built["lines"]
    assert built["lines"][0]["display_name"] == "Banana"
    assert built["lines"][0]["serving_grams"] == 118.0


def test_f_p01b_meal_fast_path_writes_receipts(data_root: Path) -> None:
    insert_food(
        name="Banana",
        source="custom",
        nutrients_per_100g={"energy_kcal": 89, "protein_g": 1.1, "carb_g": 22.8},
        default_serving_g=118,
        paths=get_paths(),
    )
    session = ChatSession(mode="agent")
    result = run_turn(
        session,
        "log meal: one medium banana for breakfast",
        _ShouldNotRunAdapter(),
    )
    assert result.stop_reason == "pack_fast_path"
    tools = [r.get("tool") for r in result.tool_receipts]
    assert "life_food_search" in tools
    assert "life_meal_log" in tools
    assert "life_nutrition_day" in tools
    with open_life_db(paths=get_paths()) as conn:
        row = conn.execute("SELECT meal_slot FROM meals ORDER BY created_at DESC LIMIT 1").fetchone()
    assert row["meal_slot"] == "breakfast"


def test_f_p01c_unknown_meal_stays_honest(data_root: Path) -> None:
    session = ChatSession(mode="agent")
    result = run_turn(
        session,
        "log meal: flurmble glorp for breakfast",
        _ShouldNotRunAdapter(),
    )
    assert result.stop_reason == "missing_life_receipt"
    tools = [r.get("tool") for r in result.tool_receipts]
    assert tools == ["life_food_search"]


def test_sleep_fast_path_writes_time_block(data_root: Path) -> None:
    session = ChatSession(mode="agent")
    result = run_turn(session, "going to sleep.", _ShouldNotRunAdapter())
    assert result.stop_reason == "pack_fast_path"
    tools = [r.get("tool") for r in result.tool_receipts]
    assert "life_time_start" in tools
    assert "life_time_status" in tools
    with open_life_db(paths=get_paths()) as conn:
        row = conn.execute(
            "SELECT kind, status FROM time_blocks ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
    assert row["kind"] == "sleep"
    assert row["status"] == "running"


def test_lift_fast_path_writes_set(data_root: Path) -> None:
    import_exercise_seed(paths=get_paths())
    session = ChatSession(mode="agent")
    result = run_turn(
        session,
        "log lift: flat bench 50kg x6",
        _ShouldNotRunAdapter(),
    )
    assert result.stop_reason == "pack_fast_path"
    assert any(r.get("tool") == "life_lift_log" for r in result.tool_receipts)
    with open_life_db(paths=get_paths()) as conn:
        row = conn.execute(
            "SELECT load_kg, reps FROM gym_sets ORDER BY logged_at DESC LIMIT 1"
        ).fetchone()
    assert row["load_kg"] == 50.0
    assert row["reps"] == 6


def test_gym_spine_parses_bench_set() -> None:
    built = build_lift_log_args("flat bench 50kg x6")
    assert built["ok"] is True
    assert built["sets"][0]["exercise_name"] == "flat bench"
    assert built["sets"][0]["load_kg"] == 50.0


def test_gym_spine_parses_bodyweight_reps() -> None:
    for utterance, name, reps in (
        ("pull-ups x8", "pull-ups", 8),
        ("10 pull-ups", "pull-ups", 10),
    ):
        built = build_lift_log_args(utterance)
        assert built["ok"] is True, utterance
        assert len(built["sets"]) == 1, utterance
        assert built["sets"][0]["exercise_name"] == name
        assert built["sets"][0]["reps"] == reps
        assert built["sets"][0]["load_kg"] is None


def test_gym_spine_parses_multi_set_bodyweight() -> None:
    built = build_lift_log_args("3x10 pull-ups")
    assert built["ok"] is True
    assert len(built["sets"]) == 3
    assert all(s["reps"] == 10 and s["load_kg"] is None for s in built["sets"])
    assert built["sets"][0]["exercise_name"] == "pull-ups"


def test_memory_facts_blocked_when_life_pack_hint() -> None:
    from ada.harness.loop import _model_tool_blocked

    session = ChatSession(mode="agent")
    session.pack_hint = {"tool": "life_lift_log", "args": {"utterance": "bench 50kg x6"}}
    assert _model_tool_blocked(session, "memory_facts_append") is not None
    assert _model_tool_blocked(session, "life_lift_log") is None


def test_life_writes_in_write_tool_names() -> None:
    assert "life_meal_log" in WRITE_TOOL_NAMES
    assert "life_nutrition_day" not in WRITE_TOOL_NAMES
