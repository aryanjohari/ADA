"""M26 time v1.1 — SQL day/week reflection (gym mirror). Not charts, not join."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

from ada.cortex.charter import build_system_charter
from ada.harness.loop import _speak_time_day, _speak_time_week, run_turn
from ada.harness.mouth import allowed_numeric_tokens, numeric_tokens
from ada.harness.nutrition_date import is_nutrition_read_shape
from ada.harness.pack_router import route_utterance
from ada.harness.session import ChatSession
from ada.harness.time_date import is_time_read_shape, parse_time_date
from ada.io.paths import get_paths
from ada.logs.time_reflection import time_day, time_window
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
    payload = json.dumps(receipt, default=str)
    allowed = allowed_numeric_tokens(payload)
    for tok in numeric_tokens(speech):
        assert _canon_ok(tok, allowed), (tok, speech, payload)


def _iso_for_local(local_day: str, hour: int, minute: int = 0) -> str:
    tz = ZoneInfo("Pacific/Auckland")
    dt = datetime.strptime(local_day, "%Y-%m-%d").replace(
        hour=hour, minute=minute, second=0, tzinfo=tz
    )
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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
        "ada.logs.time_reflection",
        datetime=dt,
    )


@pytest.fixture
def seeded_time(data_root: Path) -> Path:
    ensure_prefs(paths=get_paths())
    return data_root


def _start_block(gw: Gateway, *, kind: str, label: str | None, when: str):
    payload: dict = {"kind": kind}
    if label is not None:
        payload["label"] = label
    with patch("ada.logs.time._now_iso", return_value=when):
        return gw.execute("life_time_start", payload)


def _stop_block(gw: Gateway, *, when: str):
    with patch("ada.logs.time._now_iso", return_value=when):
        return gw.execute("life_time_stop", {})


def test_time_tools_observe_agent_not_writes() -> None:
    assert "life_time_day" in SPECS_BY_NAME
    assert "life_time_week" in SPECS_BY_NAME
    assert "life_time_day" not in WRITE_TOOL_NAMES
    assert "life_time_week" not in WRITE_TOOL_NAMES
    assert "life_time_start" in WRITE_TOOL_NAMES


def test_observe_allows_time_day_week_denies_start(seeded_time: Path) -> None:
    obs = Gateway(mode="observe")
    assert obs.execute("life_time_day", {}).ok
    assert obs.execute("life_time_week", {"days": 7}).ok
    denied = obs.execute("life_time_start", {"kind": "custom", "label": "x"})
    assert not denied.ok
    assert denied.outcome == "denied"


def test_nutrition_regex_does_not_steal_time_reads() -> None:
    time_utt = "what did i track yesterday"
    assert is_time_read_shape(time_utt)
    assert not is_nutrition_read_shape(time_utt)
    running = "what's running"
    assert not is_time_read_shape(running)


def test_pack_routes_date_and_days_args(seeded_time: Path) -> None:
    nutr, timed = _freeze_read_clock("2026-09-02")
    with nutr, timed:
        y = route_utterance("what did i track yesterday")
        week = route_utterance("time this week")
        status = route_utterance("what's running")
        assert parse_time_date("what did i track yesterday") == "2026-09-01"
    assert y is not None
    assert y["verb"] == "time_day"
    assert y["tool"] == "life_time_day"
    assert y["args"]["date"] == "2026-09-01"
    assert week is not None
    assert week["verb"] == "time_week"
    assert week["tool"] == "life_time_week"
    assert week["args"].get("days") == 7
    assert status is not None
    assert status["verb"] == "time_status"
    assert status["tool"] == "life_time_status"
    assert not (status.get("args") or {}).get("date")


def test_week_query_not_today_status(seeded_time: Path) -> None:
    nutr, timed = _freeze_read_clock("2026-09-02")
    gw = Gateway(mode="agent")
    start = _start_block(
        gw,
        kind="custom",
        label="hanging clothes",
        when=_iso_for_local("2026-09-01", 10),
    )
    assert start.ok
    stop = _stop_block(gw, when=_iso_for_local("2026-09-01", 11))
    assert stop.ok
    with nutr, timed:
        session = ChatSession(mode="observe")
        result = run_turn(session, "time this week", _ShouldNotRunAdapter())
        status = route_utterance("what's running")
    assert result.stop_reason == "pack_fast_path"
    tools = [r.get("tool") for r in result.tool_receipts]
    assert "life_time_week" in tools
    assert "life_time_status" not in tools
    assert "life_time_day" not in tools
    week = next(r for r in result.tool_receipts if r.get("tool") == "life_time_week")
    assert week.get("ok") is True
    assert int(week.get("data", {}).get("window_days") or 0) == 7
    assert status is not None
    assert status["tool"] == "life_time_status"


def test_time_day_yesterday_fast_path(seeded_time: Path) -> None:
    nutr, timed = _freeze_read_clock("2026-09-02")
    gw = Gateway(mode="agent")
    start = _start_block(
        gw,
        kind="custom",
        label="gym commute",
        when=_iso_for_local("2026-09-01", 10),
    )
    assert start.ok
    stop = _stop_block(gw, when=_iso_for_local("2026-09-01", 10, 30))
    assert stop.ok
    assert stop.data.get("duration_s") == 30 * 60
    with nutr, timed:
        session = ChatSession(mode="observe")
        result = run_turn(
            session, "what did i track yesterday", _ShouldNotRunAdapter()
        )
    assert result.stop_reason == "pack_fast_path"
    tools = [r.get("tool") for r in result.tool_receipts]
    assert tools == ["life_time_day"]
    data = result.tool_receipts[0].get("data") or {}
    assert data.get("date") == "2026-09-01"
    assert data.get("cite") == "time:day:2026-09-01"
    assert data.get("block_count") == 1
    assert data.get("duration_s") == 30 * 60
    row = (data.get("blocks") or [{}])[0]
    assert row.get("label") == "gym commute"
    assert row.get("duration_s") == 30 * 60
    spoken = result.text or ""
    _assert_mouth_subset(spoken, data)
    assert "Logged" not in spoken
    assert "2026-09-01" in spoken


def test_running_block_no_invented_duration(seeded_time: Path) -> None:
    gw = Gateway(mode="agent")
    started = _start_block(
        gw,
        kind="custom",
        label="work",
        when=_iso_for_local("2026-09-02", 9),
    )
    assert started.ok
    assert started.data.get("duration_s") is None
    day = Gateway(mode="observe").execute("life_time_day", {"date": "2026-09-02"})
    assert day.ok
    data = day.data or {}
    blocks = data.get("blocks") or []
    assert blocks
    assert blocks[0].get("duration_s") is None
    assert blocks[0].get("status") == "running"
    spoken = _speak_time_day(data)
    assert "minute" not in spoken.lower()
    _assert_mouth_subset(spoken, data)


def test_sleep_spanning_midnight_is_start_day(seeded_time: Path) -> None:
    gw = Gateway(mode="agent")
    start = _start_block(
        gw,
        kind="sleep",
        label=None,
        when=_iso_for_local("2026-09-01", 23),
    )
    assert start.ok
    stop = _stop_block(gw, when=_iso_for_local("2026-09-02", 7))
    assert stop.ok
    y = time_day(date="2026-09-01", paths=get_paths())
    t = time_day(date="2026-09-02", paths=get_paths())
    assert y["block_count"] == 1
    assert (y["blocks"] or [{}])[0]["kind"] == "sleep"
    assert (y["blocks"] or [{}])[0]["local_day"] == "2026-09-01"
    assert t["block_count"] == 0


def test_time_window_days_cap(seeded_time: Path) -> None:
    assert time_window(days=99, paths=get_paths())["window_days"] == 31
    assert time_window(days=0, paths=get_paths())["window_days"] == 1
    assert time_window(days=7, paths=get_paths())["window_days"] == 7


def test_mouth_numbers_subset_week_receipt(seeded_time: Path) -> None:
    nutr, timed = _freeze_read_clock("2026-09-02")
    gw = Gateway(mode="agent")
    _start_block(
        gw,
        kind="custom",
        label="hanging clothes",
        when=_iso_for_local("2026-09-01", 10),
    )
    _stop_block(gw, when=_iso_for_local("2026-09-01", 11))
    with nutr, timed:
        week = Gateway(mode="observe").execute("life_time_week", {"days": 7})
    assert week.ok
    spoken = _speak_time_week(week.data or {})
    _assert_mouth_subset(spoken, week.data or {})
    scratch = get_paths().scratch / "time_reflection_latest.json"
    assert scratch.is_file()


def test_charter_does_not_substitute_time_status_for_week() -> None:
    text = build_system_charter(
        mode="observe",
        include_worldview=False,
        pack_hint={"verb": "time_week", "tool": "life_time_week"},
    )
    assert "life_time_week" in text
    assert "do not substitute" in text
    assert "life_time_status" in text
