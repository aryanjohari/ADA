"""M26 habits — SQL day/week reflection (time mirror). Not charts, not join."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

from ada.cortex.charter import build_system_charter
from ada.harness.habit_date import is_habit_read_shape, parse_habit_date
from ada.harness.loop import _speak_habit_day, _speak_habit_week, run_turn
from ada.harness.mouth import allowed_numeric_tokens, numeric_tokens
from ada.harness.nutrition_date import is_nutrition_read_shape
from ada.harness.pack_router import route_utterance
from ada.harness.session import ChatSession
from ada.harness.time_date import is_time_read_shape
from ada.io.paths import get_paths
from ada.logs import habits as habits_mod
from ada.logs.habit_reflection import habit_window
from ada.memory.facts import ensure_prefs
from ada.tools.gateway import Gateway
from ada.tools.toolspec import SPECS_BY_NAME, WRITE_TOOL_NAMES


class _ShouldNotRunAdapter:
    model = "fake"

    def generate(self, *, system, contents, tools=None):
        raise AssertionError("pack fast-path should finish before model generate")


def _canon_ok(tok: str, allowed: set[str]) -> bool:
    if tok in allowed:
        return True
    try:
        val = float(tok)
    except ValueError:
        return False
    if val == int(val) and abs(val) < 1e15 and str(int(val)) in allowed:
        return True
    return False


def _assert_mouth_subset(speech: str, receipt: dict) -> None:
    import json

    payload = json.dumps(receipt, default=str)
    allowed = allowed_numeric_tokens(payload)
    for tok in numeric_tokens(speech):
        assert _canon_ok(tok, allowed), (tok, speech, payload)


def _fixed_now(fixed: str):
    tz = ZoneInfo("Pacific/Auckland")
    fixed_date = datetime.strptime(fixed, "%Y-%m-%d").date()
    fixed_now = datetime(
        fixed_date.year, fixed_date.month, fixed_date.day, 10, 0, 0, tzinfo=tz
    )

    class _FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is not None:
                return fixed_now.astimezone(tz)
            return fixed_now.astimezone(timezone.utc)

    return _FixedDatetime


def _freeze_read_clock(fixed: str):
    dt = _fixed_now(fixed)
    return patch.multiple(
        "ada.harness.nutrition_date",
        datetime=dt,
    ), patch.multiple(
        "ada.logs.habit_reflection",
        datetime=dt,
    )


@pytest.fixture
def seeded_habits(data_root: Path) -> Path:
    ensure_prefs(paths=get_paths())
    habits_mod.seed_default_habits()
    return data_root


def _tick_on_day(gw: Gateway, *, name: str, local_day: str):
    with patch("ada.logs.habits.utc_to_local_day", return_value=local_day):
        return gw.execute("life_habit_do", {"name": name})


def test_habit_tools_observe_agent_not_writes() -> None:
    assert "life_habit_day" in SPECS_BY_NAME
    assert "life_habit_week" in SPECS_BY_NAME
    assert "life_habit_day" not in WRITE_TOOL_NAMES
    assert "life_habit_week" not in WRITE_TOOL_NAMES
    assert "life_habit_do" in WRITE_TOOL_NAMES


def test_observe_allows_habit_day_week_denies_do(seeded_habits: Path) -> None:
    obs = Gateway(mode="observe")
    assert obs.execute("life_habit_day", {}).ok
    assert obs.execute("life_habit_week", {"days": 7}).ok
    denied = obs.execute("life_habit_do", {"name": "skincare"})
    assert not denied.ok
    assert denied.outcome == "denied"


def test_nutrition_regex_does_not_steal_habit_reads() -> None:
    habit_utt = "what habits yesterday"
    assert is_habit_read_shape(habit_utt)
    assert not is_nutrition_read_shape(habit_utt)
    assert not is_time_read_shape(habit_utt)
    today = "habits today"
    assert not is_habit_read_shape(today)


def test_pack_routes_date_and_days_args(seeded_habits: Path) -> None:
    nutr, habit = _freeze_read_clock("2026-09-02")
    with nutr, habit:
        y = route_utterance("what habits yesterday")
        week = route_utterance("habits this week")
        status = route_utterance("habits today")
        assert parse_habit_date("what habits yesterday") == "2026-09-01"
    assert y is not None
    assert y["verb"] == "habit_day"
    assert y["tool"] == "life_habit_day"
    assert y["args"]["date"] == "2026-09-01"
    assert week is not None
    assert week["verb"] == "habit_week"
    assert week["tool"] == "life_habit_week"
    assert week["args"].get("days") == 7
    assert status is not None
    assert status["verb"] == "streak_show"
    assert status["tool"] == "life_habit_status"
    assert not (status.get("args") or {}).get("date")


def test_week_query_not_today_status(seeded_habits: Path) -> None:
    nutr, habit = _freeze_read_clock("2026-09-02")
    gw = Gateway(mode="agent")
    tick = _tick_on_day(gw, name="skincare", local_day="2026-09-01")
    assert tick.ok
    with nutr, habit:
        session = ChatSession(mode="observe")
        result = run_turn(session, "habits this week", _ShouldNotRunAdapter())
        status = route_utterance("habits today")
    assert result.stop_reason == "pack_fast_path"
    tools = [r.get("tool") for r in result.tool_receipts]
    assert "life_habit_week" in tools
    assert "life_habit_status" not in tools
    assert "life_habit_day" not in tools
    week = next(r for r in result.tool_receipts if r.get("tool") == "life_habit_week")
    assert week.get("ok") is True
    assert int(week.get("data", {}).get("window_days") or 0) == 7
    assert status is not None
    assert status["tool"] == "life_habit_status"


def test_habit_day_yesterday_fast_path(seeded_habits: Path) -> None:
    nutr, habit = _freeze_read_clock("2026-09-02")
    gw = Gateway(mode="agent")
    tick = _tick_on_day(gw, name="skincare", local_day="2026-09-01")
    assert tick.ok
    with nutr, habit:
        session = ChatSession(mode="observe")
        result = run_turn(
            session, "what habits yesterday", _ShouldNotRunAdapter()
        )
    assert result.stop_reason == "pack_fast_path"
    tools = [r.get("tool") for r in result.tool_receipts]
    assert tools == ["life_habit_day"]
    data = result.tool_receipts[0].get("data") or {}
    assert data.get("date") == "2026-09-01"
    assert data.get("cite") == "habit:day:2026-09-01"
    assert data.get("event_count") == 1
    assert data.get("done_count") == 1
    row = (data.get("events") or [{}])[0]
    assert row.get("kind") == "done"
    spoken = result.text or ""
    _assert_mouth_subset(spoken, data)
    assert "streak broken" not in spoken.lower()
    assert "2026-09-01" in spoken


def test_empty_day_is_honest_absence_not_invented_miss(seeded_habits: Path) -> None:
    day = Gateway(mode="observe").execute("life_habit_day", {"date": "2026-09-01"})
    assert day.ok
    data = day.data or {}
    assert data.get("event_count") == 0
    assert data.get("events") == []
    assert data.get("miss_count") == 0
    spoken = _speak_habit_day(data)
    assert "no habit ticks" in spoken.lower()
    _assert_mouth_subset(spoken, data)


def test_habit_window_days_cap(seeded_habits: Path) -> None:
    assert habit_window(days=99, paths=get_paths())["window_days"] == 31
    assert habit_window(days=0, paths=get_paths())["window_days"] == 1
    assert habit_window(days=7, paths=get_paths())["window_days"] == 7


def test_mouth_numbers_subset_week_receipt(seeded_habits: Path) -> None:
    nutr, habit = _freeze_read_clock("2026-09-02")
    gw = Gateway(mode="agent")
    _tick_on_day(gw, name="skincare", local_day="2026-09-01")
    with nutr, habit:
        week = Gateway(mode="observe").execute("life_habit_week", {"days": 7})
    assert week.ok
    spoken = _speak_habit_week(week.data or {})
    assert "streak broken" not in spoken.lower()
    _assert_mouth_subset(spoken, week.data or {})
    scratch = get_paths().scratch / "habit_reflection_latest.json"
    assert scratch.is_file()


def test_charter_does_not_substitute_habit_status_for_week() -> None:
    text = build_system_charter(
        mode="observe",
        include_worldview=False,
        pack_hint={"verb": "habit_week", "tool": "life_habit_week"},
    )
    assert "life_habit_week" in text
    assert "do not substitute" in text
    assert "life_habit_status" in text


def test_empty_week_days_not_filled_with_misses(seeded_habits: Path) -> None:
    nutr, habit = _freeze_read_clock("2026-09-02")
    gw = Gateway(mode="agent")
    _tick_on_day(gw, name="skincare", local_day="2026-09-01")
    with nutr, habit:
        week = habit_window(days=7, paths=get_paths())
    empty = week.get("empty_days") or []
    assert "2026-09-01" not in empty
    for day in week.get("days") or []:
        if day.get("empty"):
            assert day.get("miss_count") == 0
            assert day.get("event_count") == 0
