"""M19a Slice 5 — Today strip life keys."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from ada.hud.today import build_today
from ada.io.paths import get_paths
from ada.logs.gym_import import import_exercise_seed
from ada.memory.facts import ensure_prefs
from ada.tools.gateway import Gateway


def test_today_life_keys_present(data_root: Path) -> None:
    ensure_prefs(get_paths())
    payload = build_today(paths=get_paths())
    assert "running_timer" in payload
    assert "nutrition_headline" in payload
    assert "meal_gap_nudge" in payload
    assert "columns" not in payload
    assert "widgets" not in payload


def test_today_running_timer_after_start(data_root: Path) -> None:
    ensure_prefs(get_paths())
    Gateway(mode="agent").execute("life_time_start", {"kind": "focus_deep", "label": "test"})
    payload = build_today(paths=get_paths())
    assert payload["running_timer"] is not None
    assert payload["running_timer"]["kind"] == "focus_deep"


def test_today_nutrition_from_rollup(data_root: Path) -> None:
    ensure_prefs(get_paths())
    gw = Gateway(mode="agent")
    gw.execute(
        "life_meal_log",
        {
            "lines": [
                {
                    "display_name": "rice",
                    "provenance": "manual",
                    "nutrients": {"energy_kcal": 200, "protein_g": 4},
                }
            ]
        },
    )
    payload = build_today(paths=get_paths())
    headline = payload.get("nutrition_headline")
    assert headline is not None
    assert headline.get("kcal") == 200


def test_today_p1_keys_present(data_root: Path) -> None:
    ensure_prefs(get_paths())
    payload = build_today(paths=get_paths())
    assert "habits_due" in payload
    assert "habits_done" in payload
    assert "habit_continuity" in payload
    assert "birthday_soon" in payload
    assert "people_remind" in payload
    assert "columns" not in payload
    assert "widgets" not in payload
