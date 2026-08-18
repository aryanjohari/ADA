"""M19a P1.1 — habit falsifiers F-P1.1a–d."""

from __future__ import annotations

from pathlib import Path

import pytest

from ada.harness.habit_spine import build_habit_tick_args
from ada.harness.loop import run_turn
from ada.harness.session import ChatSession
from ada.logs import habits as habits_mod
from ada.logs.connection import open_life_db
from ada.memory.facts import ensure_prefs
from ada.tools.gateway import Gateway


class _ShouldNotRunAdapter:
    model = "fake"

    def generate(self, *, system, contents, tools=None):
        raise AssertionError("pack fast-path should finish before model generate")


class _CapturingSink:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    def emit(self, event: str, payload: dict) -> None:
        self.events.append((event, payload))


@pytest.fixture
def p1_habits_root(data_root: Path) -> Path:
    ensure_prefs()
    habits_mod.seed_default_habits()
    return data_root


def test_f_p1_1b_habit_do_sqlite_row(p1_habits_root: Path) -> None:
    gw = Gateway(mode="agent")
    obs = gw.execute("life_habit_do", {"name": "skincare"})
    assert obs.ok
    with open_life_db() as conn:
        row = conn.execute(
            "SELECT habit_id FROM habit_events WHERE kind = 'done'"
        ).fetchone()
    assert row is not None
    assert row["habit_id"] == "habit_skincare"


def test_f_p1_1d_already_done_unique(p1_habits_root: Path) -> None:
    gw = Gateway(mode="agent")
    first = gw.execute("life_habit_do", {"name": "skincare"})
    assert first.ok
    second = gw.execute("life_habit_do", {"name": "skincare"})
    assert not second.ok
    assert second.data.get("reason") == "already_done"
    with open_life_db() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM habit_events WHERE habit_id = ? AND kind = 'done'",
            ("habit_skincare",),
        ).fetchone()[0]
    assert count == 1


def test_f_p1_1a_status_requires_sql_read(p1_habits_root: Path) -> None:
    gw = Gateway(mode="agent")
    gw.execute("life_habit_do", {"name": "skincare"})
    obs = Gateway(mode="observe").execute("life_habit_status", {})
    assert obs.ok
    assert obs.data.get("habits")
    assert obs.data.get("continuity_rate") is not None


def test_f_p1_1c_no_shame_streak_copy(p1_habits_root: Path) -> None:
    session = ChatSession(mode="observe")
    session.gateway = Gateway(mode="observe")
    sink = _CapturingSink()
    result = run_turn(
        session,
        "habits today",
        _ShouldNotRunAdapter(),
        sink=sink,
    )
    assert result.stop_reason == "pack_fast_path"
    text = (result.text or "").lower()
    assert "streak broken" not in text
    assert "guilt" not in text
    assert "continuity" in text or "done" in text


def test_habit_spine_unknown_misses(p1_habits_root: Path) -> None:
    parsed = build_habit_tick_args("flurmble glorp", verb="habit_do")
    assert not parsed.get("ok")
    assert parsed.get("reason") == "missing_life_receipt"


def test_habit_fast_path_agent(p1_habits_root: Path) -> None:
    session = ChatSession(mode="agent")
    session.gateway = Gateway(mode="agent")
    sink = _CapturingSink()
    result = run_turn(
        session,
        "habit done: skincare",
        _ShouldNotRunAdapter(),
        sink=sink,
    )
    assert result.stop_reason == "pack_fast_path"
    tools = [r.get("tool") for r in result.tool_receipts]
    assert "life_habit_do" in tools
    assert "life_habit_status" in tools
    deltas = [p for ev, p in sink.events if ev == "token_delta"]
    assert deltas and "Habit logged" in deltas[-1].get("text", "")


def test_habit_unknown_fast_path_missing_receipt(p1_habits_root: Path) -> None:
    session = ChatSession(mode="agent")
    session.gateway = Gateway(mode="agent")
    result = run_turn(
        session,
        "habit done: flurmble glorp",
        _ShouldNotRunAdapter(),
    )
    assert result.stop_reason == "missing_life_receipt"
    with open_life_db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM habit_events").fetchone()[0]
    assert count == 0


def test_routine_run_row(p1_habits_root: Path) -> None:
    gw = Gateway(mode="agent")
    obs = gw.execute("life_routine_run", {"name": "evening"})
    assert obs.ok
    with open_life_db() as conn:
        row = conn.execute("SELECT routine_id FROM routine_runs").fetchone()
    assert row is not None
