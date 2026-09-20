"""M26 dues v1.0 — pack door: wrappers force due_add/remind/due_done/due_list."""

from __future__ import annotations

from pathlib import Path

import pytest

from ada.harness.loop import run_turn
from ada.harness.pack_router import (
    is_due_add_utterance,
    is_due_done_utterance,
    is_due_list_utterance,
    is_gym_start_utterance,
    is_habit_do_utterance,
    is_meal_log_utterance,
    is_remind_utterance,
    is_time_start_utterance,
    route_utterance,
)
from ada.harness.session import ChatSession
from ada.io.paths import get_paths
from ada.memory.facts import ensure_prefs
from ada.memory.open_loops import list_loops


class _ShouldNotRunAdapter:
    model = "fake"

    def generate(self, *, system, contents, tools=None):
        raise AssertionError("pack fast-path should finish before model generate")


class _QuietAdapter:
    model = "fake"

    def generate(self, *, system, contents, tools=None):
        from ada.cortex.adapter import CortexTurn

        return CortexTurn(text="logged it", tool_calls=[])


def _open_todos() -> list[dict]:
    return list_loops(kind="todo", status="open", paths=get_paths())


@pytest.fixture
def dues_root(data_root: Path) -> Path:
    ensure_prefs(paths=get_paths())
    return data_root


# --- Router ---


@pytest.mark.parametrize(
    "text,verb",
    [
        ("add due: finish thesis by Friday", "due_add"),
        ("gotta finish lab report by Thursday", "due_add"),
        ("i need to finish the slides", "due_add"),
        ("lab report due by Friday", "due_add"),
        ("remind: stretch at 7pm", "remind"),
        ("remind me to stretch at 7pm", "remind"),
        ("done: thesis", "due_done"),
        ("what's due", "due_list"),
    ],
)
def test_route_due_wrappers_hit_four_verbs(text: str, verb: str) -> None:
    r = route_utterance(text)
    assert r is not None, text
    assert r["verb"] == verb, text
    if verb in {"due_add", "remind", "due_done"}:
        assert r["tool"] == "memory_open_loops_upsert", text
    else:
        assert r["tool"] == "memory_open_loops_list", text


def test_chip_due_prefills_add_due() -> None:
    from ada.harness.pack_router import resolve_chip

    c = resolve_chip("due")
    assert c is not None
    assert c["verb"] == "due_add"
    assert c["prefill"] == "add due: "


@pytest.mark.parametrize(
    "text",
    [
        "grocery list",
        "What's on my grocery list?",
        "shopping list",
        "on my plate",
        "What all did I have to buy?",
    ],
)
def test_grocery_shopping_on_my_plate_are_due_list(text: str) -> None:
    assert is_due_list_utterance(text), text
    assert not is_due_add_utterance(text), text
    r = route_utterance(text)
    assert r is not None, text
    assert r["verb"] == "due_list", text
    assert r["tool"] == "memory_open_loops_list", text
    assert (r.get("args") or {}).get("kind") == "todo"
    assert (r.get("args") or {}).get("status") == "open"


def test_bare_thesis_is_not_due_door() -> None:
    text = "thesis"
    assert not is_due_add_utterance(text)
    assert not is_due_done_utterance(text)
    assert not is_remind_utterance(text)
    r = route_utterance(text)
    if r is not None:
        assert r["verb"] not in {"due_add", "due_done", "remind", "due_list"}


def test_habit_done_skincare_is_not_due_add() -> None:
    text = "habit done skincare"
    assert is_habit_do_utterance(text)
    assert not is_due_add_utterance(text)
    assert not is_due_done_utterance(text)
    r = route_utterance(text)
    assert r is not None
    assert r["verb"] == "habit_do"
    assert r["tool"] == "life_habit_do"


def test_im_at_the_gym_is_not_due_add() -> None:
    text = "I'm at the gym"
    assert is_gym_start_utterance(text)
    assert not is_due_add_utterance(text)
    r = route_utterance(text)
    assert r is not None
    assert r["verb"] == "gym_start"
    assert r["tool"] == "life_gym_start"


def test_im_starting_gym_commute_is_not_due_add() -> None:
    text = "I'm starting gym commute"
    assert is_time_start_utterance(text)
    assert not is_due_add_utterance(text)
    r = route_utterance(text)
    assert r is not None
    assert r["verb"] == "time_start"
    assert r["tool"] == "life_time_start"


def test_meal_nl_is_not_due_add() -> None:
    text = "add one banana to breakfast"
    assert is_meal_log_utterance(text)
    assert not is_due_add_utterance(text)
    r = route_utterance(text)
    assert r is not None
    assert r["verb"] == "meal_log"
    assert r["tool"] == "life_meal_log"


def test_done_colon_thesis_is_due_done_not_gym_end() -> None:
    from ada.harness.pack_router import is_gym_end_utterance

    text = "done: thesis"
    assert is_due_done_utterance(text)
    assert not is_gym_end_utterance(text)
    r = route_utterance(text)
    assert r is not None
    assert r["verb"] == "due_done"
    assert r["tool"] == "memory_open_loops_upsert"


# --- Loop / HUD ---


@pytest.mark.parametrize(
    "text,verb",
    [
        ("add due: finish thesis by Friday", "due_add"),
        ("gotta finish lab report by Thursday", "due_add"),
        ("remind me to stretch at 7pm", "remind"),
        ("remind: stretch at 7pm", "remind"),
    ],
)
def test_due_write_fast_path_no_generate(dues_root: Path, text: str, verb: str) -> None:
    session = ChatSession(mode="agent")
    result = run_turn(session, text, _ShouldNotRunAdapter())
    assert result.stop_reason == "pack_fast_path", text
    tools = [r.get("tool") for r in result.tool_receipts]
    assert "memory_open_loops_upsert" in tools, text
    assert "life_habit_do" not in tools, text
    assert "life_gym_start" not in tools, text
    assert "life_time_start" not in tools, text
    assert "life_meal_log" not in tools, text
    assert _open_todos()


def test_whats_due_fast_path_observe_and_agent(dues_root: Path) -> None:
    agent = run_turn(ChatSession(mode="agent"), "what's due", _ShouldNotRunAdapter())
    assert agent.stop_reason == "pack_fast_path"
    assert any(r.get("tool") == "memory_open_loops_list" for r in agent.tool_receipts)
    observed = run_turn(
        ChatSession(mode="observe"), "what's due", _ShouldNotRunAdapter()
    )
    assert observed.stop_reason == "pack_fast_path"
    assert any(
        r.get("tool") == "memory_open_loops_list" for r in observed.tool_receipts
    )


def test_due_add_forces_without_pack_hint(
    dues_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "ada.harness.pack_router.route_utterance",
        lambda text, **kwargs: None,
    )
    session = ChatSession(mode="agent")
    result = run_turn(session, "add due: finish thesis by Friday", _ShouldNotRunAdapter())
    assert result.stop_reason == "pack_fast_path"
    assert any(
        r.get("tool") == "memory_open_loops_upsert" for r in result.tool_receipts
    )
    assert any("thesis" in str(t.get("text") or "").lower() for t in _open_todos())


def test_observe_due_add_does_not_write(dues_root: Path) -> None:
    session = ChatSession(mode="observe")
    result = run_turn(session, "add due: buy milk", _QuietAdapter())
    assert result.stop_reason != "pack_fast_path"
    assert not any(
        r.get("tool") == "memory_open_loops_upsert" for r in result.tool_receipts
    )
    assert _open_todos() == []


def test_habit_done_fast_path_stays_habit(dues_root: Path) -> None:
    from ada.logs import habits as habits_mod

    habits_mod.seed_default_habits()
    result = run_turn(
        ChatSession(mode="agent"), "habit done skincare", _ShouldNotRunAdapter()
    )
    assert result.stop_reason == "pack_fast_path"
    assert any(r.get("tool") == "life_habit_do" for r in result.tool_receipts)
    assert not any(
        r.get("tool") == "memory_open_loops_upsert" for r in result.tool_receipts
    )


def test_im_at_the_gym_fast_path_stays_gym(dues_root: Path) -> None:
    result = run_turn(
        ChatSession(mode="agent"), "I'm at the gym", _ShouldNotRunAdapter()
    )
    assert result.stop_reason == "pack_fast_path"
    assert any(r.get("tool") == "life_gym_start" for r in result.tool_receipts)
    assert not any(
        r.get("tool") == "memory_open_loops_upsert" for r in result.tool_receipts
    )


def test_im_starting_gym_commute_fast_path_stays_time(dues_root: Path) -> None:
    result = run_turn(
        ChatSession(mode="agent"),
        "I'm starting gym commute",
        _ShouldNotRunAdapter(),
    )
    assert result.stop_reason == "pack_fast_path"
    assert any(r.get("tool") == "life_time_start" for r in result.tool_receipts)
    assert not any(
        r.get("tool") == "memory_open_loops_upsert" for r in result.tool_receipts
    )


# --- Confirm sticky (none on add / remind / unique done; 0/>1 = miss) ---


_CONFIRM_MARKERS = (
    "tap confirm",
    "confirm on the card",
    "which habit",
    "tap the right food",
)


def test_due_packs_have_no_confirm_class() -> None:
    from ada.harness.pack_router import ADMIN_WRITE_VERBS, CONFIRM_BOUND_VERBS, load_pack_config

    cfg = load_pack_config()
    packs = cfg.get("packs") or {}
    for verb in ("due_add", "remind", "due_done"):
        entry = packs.get(verb) or {}
        assert not entry.get("confirm_class"), verb
        assert verb in ADMIN_WRITE_VERBS
        assert verb not in CONFIRM_BOUND_VERBS


def test_due_add_and_remind_confirm_none(dues_root: Path) -> None:
    add = run_turn(
        ChatSession(mode="agent"),
        "add due: finish thesis by Friday",
        _ShouldNotRunAdapter(),
    )
    assert add.stop_reason == "pack_fast_path"
    upsert = next(
        r for r in add.tool_receipts if r.get("tool") == "memory_open_loops_upsert"
    )
    assert upsert.get("ok") is True
    assert upsert.get("needs_confirm") is not True
    assert upsert.get("outcome") != "needs_confirm"
    spoken = (add.text or "").lower()
    for marker in _CONFIRM_MARKERS:
        assert marker not in spoken, add.text

    remind = run_turn(
        ChatSession(mode="agent"),
        "remind me to stretch at 7pm",
        _ShouldNotRunAdapter(),
    )
    assert remind.stop_reason == "pack_fast_path"
    r_up = next(
        r for r in remind.tool_receipts if r.get("tool") == "memory_open_loops_upsert"
    )
    assert r_up.get("ok") is True
    assert r_up.get("needs_confirm") is not True


def test_unique_due_done_confirm_none(dues_root: Path) -> None:
    from ada.memory.open_loops import upsert_loop

    created = upsert_loop(text="finish thesis chapter", kind="todo", status="open")
    result = run_turn(
        ChatSession(mode="agent"), "done: thesis", _ShouldNotRunAdapter()
    )
    assert result.stop_reason == "pack_fast_path"
    upsert = next(
        r for r in result.tool_receipts if r.get("tool") == "memory_open_loops_upsert"
    )
    assert upsert.get("ok") is True
    assert upsert.get("needs_confirm") is not True
    assert (upsert.get("args") or {}).get("status") == "done"
    assert (upsert.get("args") or {}).get("id") == created["loop"]["id"]
    spoken = (result.text or "").lower()
    for marker in _CONFIRM_MARKERS:
        assert marker not in spoken, result.text
    remaining = _open_todos()
    assert not any(t.get("id") == created["loop"]["id"] for t in remaining)


def test_ambiguous_due_done_is_miss_no_picker(dues_root: Path) -> None:
    from ada.memory.open_loops import upsert_loop

    upsert_loop(text="finish thesis chapter", kind="todo", status="open")
    upsert_loop(text="thesis bibliography", kind="todo", status="open")
    result = run_turn(
        ChatSession(mode="agent"), "done: thesis", _ShouldNotRunAdapter()
    )
    assert result.stop_reason == "missing_life_receipt"
    assert not any(
        r.get("tool") == "memory_open_loops_upsert" for r in result.tool_receipts
    )
    spoken = (result.text or "").lower()
    for marker in _CONFIRM_MARKERS:
        assert marker not in spoken, result.text
    assert len(_open_todos()) == 2


def test_zero_due_done_is_miss_no_guess(dues_root: Path) -> None:
    result = run_turn(
        ChatSession(mode="agent"), "done: flurmble glorp", _ShouldNotRunAdapter()
    )
    assert result.stop_reason == "missing_life_receipt"
    assert not any(
        r.get("tool") == "memory_open_loops_upsert" for r in result.tool_receipts
    )
    spoken = (result.text or "").lower()
    for marker in _CONFIRM_MARKERS:
        assert marker not in spoken, result.text
    assert "logged" not in spoken
    assert _open_todos() == []


# --- Mouth ⊆ receipt ---


def test_due_add_mouth_logged_after_upsert_ok(dues_root: Path) -> None:
    result = run_turn(
        ChatSession(mode="agent"),
        "add due: finish thesis by Friday",
        _ShouldNotRunAdapter(),
    )
    upsert = next(
        r for r in result.tool_receipts if r.get("tool") == "memory_open_loops_upsert"
    )
    assert upsert.get("ok") is True
    spoken = result.text or ""
    assert spoken.strip().lower() == "due add logged."
    from ada.harness.mouth import should_skip_register_pass

    assert should_skip_register_pass(spoken, result.tool_receipts) is True


def test_due_done_mouth_logged_after_upsert_ok(dues_root: Path) -> None:
    from ada.memory.open_loops import upsert_loop

    upsert_loop(text="finish thesis chapter", kind="todo", status="open")
    result = run_turn(
        ChatSession(mode="agent"), "done: thesis", _ShouldNotRunAdapter()
    )
    upsert = next(
        r for r in result.tool_receipts if r.get("tool") == "memory_open_loops_upsert"
    )
    assert upsert.get("ok") is True
    spoken = (result.text or "").strip().lower()
    assert spoken == "due done logged."


def test_due_done_miss_mouth_does_not_say_logged(dues_root: Path) -> None:
    result = run_turn(
        ChatSession(mode="agent"), "done: flurmble glorp", _ShouldNotRunAdapter()
    )
    assert result.stop_reason == "missing_life_receipt"
    spoken = (result.text or "").lower()
    assert "logged" not in spoken


def test_due_list_mouth_from_receipt_count(dues_root: Path) -> None:
    from ada.memory.open_loops import upsert_loop

    upsert_loop(text="finish thesis chapter", kind="todo", status="open")
    upsert_loop(text="lab report", kind="todo", status="open")
    result = run_turn(
        ChatSession(mode="agent"), "what's due", _ShouldNotRunAdapter()
    )
    listed = next(
        r for r in result.tool_receipts if r.get("tool") == "memory_open_loops_list"
    )
    data = listed.get("data") or {}
    n = int(data.get("count") if isinstance(data.get("count"), int) else len(data.get("loops") or []))
    spoken = (result.text or "").strip()
    assert spoken == f"{n} open due(s)."
    from ada.harness.mouth import should_skip_register_pass

    assert should_skip_register_pass(spoken, result.tool_receipts) is True


def test_due_canned_ack_skips_gemini_narrate() -> None:
    from ada.harness.mouth import should_skip_register_pass

    fake_ok = [{"ok": True, "tool": "memory_open_loops_upsert", "data": {"id": "loop_1"}}]
    assert should_skip_register_pass("due add logged.", fake_ok) is True
    assert should_skip_register_pass("due done logged.", fake_ok) is True
    assert should_skip_register_pass("remind logged.", fake_ok) is True
    assert should_skip_register_pass("2 open due(s).", fake_ok) is True
