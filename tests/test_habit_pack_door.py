"""M26 habits v1.0 — pack door: wrappers force habit_do/habit_miss (time analogue)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ada.harness.loop import _speak_habit_tick, run_turn
from ada.harness.mouth import allowed_numeric_tokens, numeric_tokens
from ada.harness.pack_router import (
    is_gym_start_utterance,
    is_habit_do_utterance,
    is_habit_miss_utterance,
    is_time_start_utterance,
    route_utterance,
)
from ada.harness.session import ChatSession
from ada.io.paths import get_paths
from ada.logs import habits as habits_mod
from ada.logs.connection import open_life_db
from ada.memory.facts import ensure_prefs


class _ShouldNotRunAdapter:
    model = "fake"

    def generate(self, *, system, contents, tools=None):
        raise AssertionError("pack fast-path should finish before model generate")


class _QuietAdapter:
    model = "fake"

    def generate(self, *, system, contents, tools=None):
        from ada.cortex.adapter import CortexTurn

        return CortexTurn(text="logged it", tool_calls=[])


def _event_count(*, kind: str | None = None) -> int:
    with open_life_db(paths=get_paths()) as conn:
        if kind:
            return int(
                conn.execute(
                    "SELECT COUNT(*) AS n FROM habit_events WHERE kind = ?",
                    (kind,),
                ).fetchone()["n"]
            )
        return int(conn.execute("SELECT COUNT(*) AS n FROM habit_events").fetchone()["n"])


@pytest.fixture
def seeded_habits(data_root: Path) -> Path:
    ensure_prefs(paths=get_paths())
    habits_mod.seed_default_habits()
    return data_root


# --- Router ---


@pytest.mark.parametrize(
    "text",
    [
        "habit done: skincare",
        "Habit done skincare",
        "tick laundry",
        "habit tick laundry",
    ],
)
def test_route_habit_do_wrappers(text: str) -> None:
    assert is_habit_do_utterance(text), text
    assert not is_habit_miss_utterance(text), text
    r = route_utterance(text)
    assert r is not None, text
    assert r["verb"] == "habit_do", text
    assert r["tool"] == "life_habit_do", text


def test_route_habit_miss_wrapper() -> None:
    text = "habit miss: skincare"
    assert is_habit_miss_utterance(text)
    assert not is_habit_do_utterance(text)
    r = route_utterance(text)
    assert r is not None
    assert r["verb"] == "habit_miss"
    assert r["tool"] == "life_habit_miss"


@pytest.mark.parametrize("text", ["skincare", "laundry"])
def test_bare_name_is_not_habit_door(text: str) -> None:
    assert not is_habit_do_utterance(text), text
    assert not is_habit_miss_utterance(text), text
    r = route_utterance(text)
    if r is not None:
        assert r["verb"] not in {"habit_do", "habit_miss"}, text


def test_im_starting_gym_commute_is_time_not_habit() -> None:
    text = "I'm starting gym commute"
    assert is_time_start_utterance(text)
    assert not is_gym_start_utterance(text)
    assert not is_habit_do_utterance(text)
    r = route_utterance(text)
    assert r is not None
    assert r["verb"] == "time_start"
    assert r["tool"] == "life_time_start"


def test_im_at_the_gym_is_gym_not_habit() -> None:
    text = "I'm at the gym"
    assert is_gym_start_utterance(text)
    assert not is_time_start_utterance(text)
    assert not is_habit_do_utterance(text)
    r = route_utterance(text)
    assert r is not None
    assert r["verb"] == "gym_start"
    assert r["tool"] == "life_gym_start"


# --- Loop / HUD ---


@pytest.mark.parametrize(
    "text",
    [
        "habit done: skincare",
        "Habit done skincare",
    ],
)
def test_habit_do_fast_path_no_generate(seeded_habits: Path, text: str) -> None:
    session = ChatSession(mode="agent")
    result = run_turn(session, text, _ShouldNotRunAdapter())
    assert result.stop_reason == "pack_fast_path", text
    assert any(r.get("tool") == "life_habit_do" for r in result.tool_receipts), text
    assert not any(r.get("tool") == "life_time_start" for r in result.tool_receipts), text
    assert not any(r.get("tool") == "life_gym_start" for r in result.tool_receipts), text
    assert _event_count(kind="done") == 1


def test_tick_laundry_routes_habit_do_before_cortex(seeded_habits: Path) -> None:
    session = ChatSession(mode="agent")
    result = run_turn(session, "tick laundry", _ShouldNotRunAdapter())
    assert result.stop_reason == "pack_fast_path"
    tools = [r.get("tool") for r in result.tool_receipts]
    assert "life_habit_do" in tools or "life_habit_create" in tools
    assert "life_gym_start" not in tools
    assert "life_time_start" not in tools


def test_habit_miss_fast_path_no_generate(seeded_habits: Path) -> None:
    session = ChatSession(mode="agent")
    result = run_turn(session, "habit miss: skincare", _ShouldNotRunAdapter())
    assert result.stop_reason == "pack_fast_path"
    assert any(r.get("tool") == "life_habit_miss" for r in result.tool_receipts)
    assert _event_count(kind="miss") == 1


def test_habit_do_forces_without_pack_hint(
    seeded_habits: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "ada.harness.pack_router.route_utterance",
        lambda text, **kwargs: None,
    )
    session = ChatSession(mode="agent")
    result = run_turn(session, "habit done: skincare", _ShouldNotRunAdapter())
    assert result.stop_reason == "pack_fast_path"
    assert any(r.get("tool") == "life_habit_do" for r in result.tool_receipts)
    assert _event_count(kind="done") == 1


def test_observe_structural_habit_does_not_write(seeded_habits: Path) -> None:
    session = ChatSession(mode="observe")
    result = run_turn(session, "habit done: skincare", _QuietAdapter())
    assert result.stop_reason != "pack_fast_path"
    assert not any(r.get("tool") == "life_habit_do" for r in result.tool_receipts)
    assert _event_count() == 0


def test_im_at_the_gym_fast_path_stays_gym(data_root: Path) -> None:
    session = ChatSession(mode="agent")
    result = run_turn(session, "I'm at the gym", _ShouldNotRunAdapter())
    assert result.stop_reason == "pack_fast_path"
    assert any(r.get("tool") == "life_gym_start" for r in result.tool_receipts)
    assert not any(r.get("tool") == "life_habit_do" for r in result.tool_receipts)
    assert not any(r.get("tool") == "life_time_start" for r in result.tool_receipts)


def test_im_starting_gym_commute_fast_path_stays_time(data_root: Path) -> None:
    session = ChatSession(mode="agent")
    result = run_turn(session, "I'm starting gym commute", _ShouldNotRunAdapter())
    assert result.stop_reason == "pack_fast_path"
    assert any(r.get("tool") == "life_time_start" for r in result.tool_receipts)
    assert not any(r.get("tool") == "life_habit_do" for r in result.tool_receipts)
    assert not any(r.get("tool") == "life_gym_start" for r in result.tool_receipts)


# --- Mouth ⊆ receipt ---


_TICK_LIE = ("logged", "streak broken")


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


def test_speak_already_done_no_logged() -> None:
    spoken = _speak_habit_tick(
        {"ok": False, "reason": "already_done", "habit_id": "habit_skincare"},
        verb="habit_do",
    )
    low = spoken.lower()
    for token in _TICK_LIE:
        assert token not in low, spoken
    assert "logged" not in low


def test_speak_unknown_miss_no_tick() -> None:
    spoken = _speak_habit_tick(
        {"ok": False, "reason": "missing_life_receipt"},
        verb="habit_miss",
    )
    low = spoken.lower()
    for token in _TICK_LIE:
        assert token not in low, spoken
    assert "habit logged" not in low


def test_already_done_mouth_no_logged(seeded_habits: Path) -> None:
    run_turn(ChatSession(mode="agent"), "habit done: skincare", _ShouldNotRunAdapter())
    result = run_turn(
        ChatSession(mode="agent"), "habit done: skincare", _ShouldNotRunAdapter()
    )
    assert result.stop_reason == "pack_fast_path"
    done = next(r for r in result.tool_receipts if r.get("tool") == "life_habit_do")
    data = done.get("data") or {}
    assert data.get("ok") is False
    assert data.get("reason") == "already_done"
    spoken = result.text or ""
    low = spoken.lower()
    for token in _TICK_LIE:
        assert token not in low, spoken
    _assert_mouth_subset(spoken, data)
    assert _event_count(kind="done") == 1


def test_unknown_miss_mouth_no_invented_tick(data_root: Path) -> None:
    result = run_turn(
        ChatSession(mode="agent"),
        "habit miss: flurmble glorp",
        _ShouldNotRunAdapter(),
    )
    assert result.stop_reason == "missing_life_receipt"
    spoken = result.text or ""
    low = spoken.lower()
    for token in _TICK_LIE:
        assert token not in low, spoken
    assert "habit logged" not in low
    assert _event_count() == 0


def test_miss_speak_from_receipt_no_logged(seeded_habits: Path) -> None:
    result = run_turn(
        ChatSession(mode="agent"), "habit miss: skincare", _ShouldNotRunAdapter()
    )
    miss = next(r for r in result.tool_receipts if r.get("tool") == "life_habit_miss")
    data = miss.get("data") or {}
    assert data.get("ok") is True
    assert data.get("kind") == "miss"
    spoken = result.text or ""
    low = spoken.lower()
    assert "logged" not in low
    assert "streak broken" not in low
    _assert_mouth_subset(spoken, data)
