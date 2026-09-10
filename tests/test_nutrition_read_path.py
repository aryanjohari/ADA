"""Nutrition read path — pack router date/window args + fast path."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

from ada.harness.loop import run_turn
from ada.harness.nutrition_date import local_today, local_yesterday, parse_nutrition_date
from ada.harness.pack_router import route_utterance
from ada.harness.session import ChatSession
from ada.io.atomic import atomic_write_text
from ada.io.paths import get_paths
from ada.logs.food import insert_food
from ada.logs.meals import meal_log
from ada.memory.facts import _dump_yaml, ensure_prefs


class _ShouldNotRunAdapter:
    model = "fake"

    def generate(self, *, system, contents, tools=None):
        raise AssertionError("pack fast-path should finish before model generate")


def _fixed_local_day(fixed: str):
    """Patch utc_to_local_day and now() so yesterday/today are deterministic."""

    def _utc_to_local_day(ts=None, *, paths=None):
        return fixed

    tz = ZoneInfo("Pacific/Auckland")
    fixed_date = datetime.strptime(fixed, "%Y-%m-%d").date()
    fixed_now = datetime(
        fixed_date.year,
        fixed_date.month,
        fixed_date.day,
        10,
        0,
        0,
        tzinfo=tz,
    )

    class _FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is not None:
                return fixed_now.astimezone(tz)
            return fixed_now.replace(tzinfo=timezone.utc)

    return patch.multiple(
        "ada.harness.nutrition_date",
        utc_to_local_day=_utc_to_local_day,
        datetime=_FixedDatetime,
    )


@pytest.fixture
def nutrition_paths(data_root, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ADA_DATA_ROOT", str(data_root))
    paths = get_paths()
    paths.ensure_memory_dirs()
    ensure_prefs(paths=paths)
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
    return paths, egg


def _seed_meal_on_day(paths, egg: dict, *, local_day: str, receipt_id: str) -> None:
    with patch("ada.logs.meals.utc_to_local_day", return_value=local_day):
        meal_log(
            receipt_id=receipt_id,
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


def test_parse_nutrition_date_yesterday(nutrition_paths) -> None:
    with _fixed_local_day("2026-09-02"):
        assert parse_nutrition_date("what did I eat yesterday?") == "2026-09-01"
        assert parse_nutrition_date("macros from last night") == "2026-09-01"


def test_parse_nutrition_date_explicit_sept(nutrition_paths) -> None:
    with _fixed_local_day("2026-09-02"):
        assert parse_nutrition_date("What did I eat on 1st sept?") == "2026-09-01"
        assert parse_nutrition_date("macros on 2026-09-01") == "2026-09-01"
        assert parse_nutrition_date("september 1st protein") == "2026-09-01"


def test_route_yesterday_sets_date(nutrition_paths) -> None:
    with _fixed_local_day("2026-09-02"):
        r = route_utterance("What did I eat yesterday?")
    assert r is not None
    assert r["verb"] == "nutrition_day"
    assert r["tool"] == "life_nutrition_day"
    assert r["args"]["date"] == "2026-09-01"


def test_route_on_first_sept_sets_date(nutrition_paths) -> None:
    with _fixed_local_day("2026-09-02"):
        r = route_utterance("What did I eat on 1st sept?")
    assert r is not None
    assert r["verb"] == "nutrition_day"
    assert r["args"]["date"] == "2026-09-01"


def test_route_tell_all_macros_this_week(nutrition_paths) -> None:
    r = route_utterance("Tell all macros this week")
    assert r is not None
    assert r["verb"] == "nutrition_week"
    assert r["tool"] == "life_nutrition_week"
    assert r["args"].get("days") == 7


def test_route_what_did_i_eat_defaults_today(nutrition_paths) -> None:
    with _fixed_local_day("2026-09-02"):
        r = route_utterance("what did i eat")
    assert r is not None
    assert r["verb"] == "nutrition_day"
    assert r["args"].get("date") == "2026-09-02"


def test_route_macros_yesterday(nutrition_paths) -> None:
    with _fixed_local_day("2026-09-02"):
        r = route_utterance("Macros from yesterday")
    assert r is not None
    assert r["verb"] == "nutrition_day"
    assert r["args"]["date"] == "2026-09-01"


def test_observe_run_turn_macros_yesterday_fast_path(nutrition_paths) -> None:
    paths, egg = nutrition_paths
    with _fixed_local_day("2026-09-02"):
        _seed_meal_on_day(paths, egg, local_day="2026-09-01", receipt_id="y-day")
        session = ChatSession(mode="observe")
        result = run_turn(session, "macros yesterday", _ShouldNotRunAdapter())
    assert result.stop_reason == "pack_fast_path"
    tools = [r.get("tool") for r in result.tool_receipts]
    assert tools == ["life_nutrition_day"]
    day_receipt = result.tool_receipts[0]
    assert day_receipt.get("ok") is True
    assert day_receipt.get("data", {}).get("date") == "2026-09-01"
    assert day_receipt.get("data", {}).get("totals", {}).get("protein_g") == pytest.approx(
        31.5
    )


def test_agent_run_turn_protein_this_week_not_day(nutrition_paths) -> None:
    paths, egg = nutrition_paths
    with _fixed_local_day("2026-09-02"):
        _seed_meal_on_day(paths, egg, local_day="2026-09-01", receipt_id="w-y")
        _seed_meal_on_day(paths, egg, local_day="2026-09-02", receipt_id="w-t")
        session = ChatSession(mode="agent")
        result = run_turn(session, "protein this week", _ShouldNotRunAdapter())
    assert result.stop_reason == "pack_fast_path"
    tools = [r.get("tool") for r in result.tool_receipts]
    assert "life_nutrition_week" in tools
    assert "life_nutrition_day" not in tools
    week = next(r for r in result.tool_receipts if r.get("tool") == "life_nutrition_week")
    assert week.get("ok") is True
    assert int(week.get("data", {}).get("days_logged") or 0) >= 2


def test_meal_capture_fast_path_unchanged(nutrition_paths, monkeypatch) -> None:
    paths, _egg = nutrition_paths
    monkeypatch.delenv("USDA_FDC_API_KEY", raising=False)
    secrets = paths.root / "secrets"
    secrets.mkdir(exist_ok=True)
    monkeypatch.setenv("ADA_SECRETS_DIR", str(secrets))
    from ada.logs.food import insert_food as _insert_food

    _insert_food(
        name="Banana",
        source="custom",
        nutrients_per_100g={
            "energy_kcal": 89,
            "protein_g": 1.1,
            "carb_g": 23,
            "fat_g": 0.3,
        },
        paths=paths,
    )
    session = ChatSession(mode="agent")
    result = run_turn(
        session,
        "Log 5 boiled eggs for breakfast",
        _ShouldNotRunAdapter(),
    )
    assert result.stop_reason == "pack_fast_path"
    tools = [r.get("tool") for r in result.tool_receipts]
    assert "life_meal_log" in tools
    assert "life_nutrition_day" not in tools


def test_local_yesterday_matches_today_minus_one(nutrition_paths) -> None:
    with _fixed_local_day("2026-09-02"):
        assert local_today() == "2026-09-02"
        assert local_yesterday() == "2026-09-01"
