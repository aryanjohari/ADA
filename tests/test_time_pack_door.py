"""M26 time v1.1 — pack door: start-shapes force time_start (gym analogue)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ada.harness.loop import _speak_time_stop, run_turn
from ada.harness.mouth import allowed_numeric_tokens, numeric_tokens
from ada.harness.pack_router import (
    is_gym_start_utterance,
    is_time_start_utterance,
    route_utterance,
)
from ada.harness.session import ChatSession
from ada.io.paths import get_paths
from ada.logs.connection import open_life_db


class _ShouldNotRunAdapter:
    model = "fake"

    def generate(self, *, system, contents, tools=None):
        raise AssertionError("pack fast-path should finish before model generate")


class _QuietAdapter:
    model = "fake"

    def generate(self, *, system, contents, tools=None):
        from ada.cortex.adapter import CortexTurn

        return CortexTurn(text="logged it", tool_calls=[])


def _running_count() -> int:
    with open_life_db(paths=get_paths()) as conn:
        return int(
            conn.execute(
                "SELECT COUNT(*) AS n FROM time_blocks WHERE status = 'running'"
            ).fetchone()["n"]
        )


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


# --- Router ---


@pytest.mark.parametrize(
    "text",
    [
        "start timer: morning cooking",
        "start focus: work",
    ],
)
def test_route_start_timer_focus_prefixes(text: str) -> None:
    assert is_time_start_utterance(text)
    r = route_utterance(text)
    assert r is not None, text
    assert r["verb"] == "time_start", text
    assert r["tool"] == "life_time_start", text


@pytest.mark.parametrize(
    "text",
    [
        "I'm starting gym commute",
        "I started shower and skincare",
        "I'm hanging clothes",
        "starting gym commute",
    ],
)
def test_route_time_start_shapes(text: str) -> None:
    assert is_time_start_utterance(text), text
    assert not is_gym_start_utterance(text), text
    r = route_utterance(text)
    assert r is not None, text
    assert r["verb"] == "time_start", text
    assert r["tool"] == "life_time_start", text


@pytest.mark.parametrize("text", ["morning cooking", "gym commute"])
def test_bare_spine_label_is_not_time_start(text: str) -> None:
    assert not is_time_start_utterance(text), text
    r = route_utterance(text)
    if r is not None:
        assert r["verb"] != "time_start", text


def test_im_at_the_gym_is_gym_not_time() -> None:
    text = "I'm at the gym"
    assert is_gym_start_utterance(text)
    assert not is_time_start_utterance(text)
    r = route_utterance(text)
    assert r is not None
    assert r["verb"] == "gym_start"
    assert r["tool"] == "life_gym_start"


@pytest.mark.parametrize(
    ("text", "verb", "tool"),
    [
        ("going to sleep", "time_start", "life_time_start"),
        ("stop timer", "time_stop", "life_time_stop"),
        ("what's running", "time_status", "life_time_status"),
    ],
)
def test_yaml_time_aliases_still_route(text: str, verb: str, tool: str) -> None:
    r = route_utterance(text)
    assert r is not None, text
    assert r["verb"] == verb, text
    assert r["tool"] == tool, text


# --- Resolve (kind + label; no catalog) ---


@pytest.mark.parametrize(
    ("text", "kind", "label"),
    [
        ("start timer: morning cooking", "cooking", "morning cooking"),
        ("start focus: work", "custom", "work"),
        ("I'm starting gym commute", "custom", "gym commute"),
        ("I started shower and skincare", "custom", "shower and skincare"),
        ("I'm hanging clothes", "custom", "hanging clothes"),
        ("starting gym commute", "custom", "gym commute"),
        ("going to sleep", "sleep", None),
        ("good morning", "wake", None),
    ],
)
def test_time_intent_kind_and_stripped_label(
    text: str, kind: str, label: str | None
) -> None:
    from ada.harness.time_intent import map_time_intent

    mapped = map_time_intent(text)
    assert mapped["kind"] == kind, text
    assert mapped.get("label") == label, text
    r = route_utterance(text)
    assert r is not None, text
    assert r["verb"] == "time_start", text
    assert r["args"]["kind"] == kind, text
    assert r["args"].get("label") == label, text


# --- Confirm sticky (none on start/stop; alias FACT is not a gate) ---


def test_time_packs_have_no_confirm_class() -> None:
    from ada.harness.pack_router import CONFIRM_BOUND_VERBS, load_pack_config
    from ada.tools.toolspec import SPECS_BY_NAME

    cfg = load_pack_config()
    packs = cfg.get("packs") or {}
    for verb in ("time_start", "time_stop"):
        entry = packs.get(verb) or {}
        assert not entry.get("confirm_class"), verb
        assert verb not in CONFIRM_BOUND_VERBS
    for tool in ("life_time_start", "life_time_stop"):
        spec = SPECS_BY_NAME[tool]
        params = (spec.schema or {}).get("parameters") or {}
        props = params.get("properties") or {}
        assert "confirmed" not in props, tool
        assert spec.side_effect != "confirm", tool


def test_start_without_kind_alias_fact_no_confirm(data_root: Path) -> None:
    from ada.io.paths import get_paths

    alias = get_paths().facts / "time_kind_aliases.yaml"
    assert not alias.exists()
    result = run_turn(
        ChatSession(mode="agent"), "I'm hanging clothes", _ShouldNotRunAdapter()
    )
    assert result.stop_reason == "pack_fast_path"
    start = next(r for r in result.tool_receipts if r.get("tool") == "life_time_start")
    assert start.get("ok") is True
    assert start.get("needs_confirm") is not True
    assert start.get("outcome") != "needs_confirm"
    assert _running_count() == 1
    stop = run_turn(ChatSession(mode="agent"), "stop timer", _ShouldNotRunAdapter())
    assert stop.stop_reason == "pack_fast_path"
    stopped = next(r for r in stop.tool_receipts if r.get("tool") == "life_time_stop")
    assert stopped.get("ok") is True
    assert stopped.get("needs_confirm") is not True


# --- Loop / HUD ---



@pytest.mark.parametrize(
    "text",
    [
        "start timer: morning cooking",
        "start focus: work",
        "I'm starting gym commute",
        "I started shower and skincare",
        "I'm hanging clothes",
    ],
)
def test_time_start_fast_path_no_generate(data_root: Path, text: str) -> None:
    session = ChatSession(mode="agent")
    result = run_turn(session, text, _ShouldNotRunAdapter())
    assert result.stop_reason == "pack_fast_path", text
    assert any(r.get("tool") == "life_time_start" for r in result.tool_receipts), text
    assert not any(r.get("tool") == "life_meal_log" for r in result.tool_receipts), text
    assert not any(r.get("tool") == "life_gym_start" for r in result.tool_receipts), text
    assert _running_count() == 1


def test_time_start_forces_without_pack_hint(
    data_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "ada.harness.pack_router.route_utterance",
        lambda text, **kwargs: None,
    )
    session = ChatSession(mode="agent")
    result = run_turn(session, "I'm hanging clothes", _ShouldNotRunAdapter())
    assert result.stop_reason == "pack_fast_path"
    assert any(r.get("tool") == "life_time_start" for r in result.tool_receipts)
    assert _running_count() == 1


def test_observe_structural_time_does_not_write(data_root: Path) -> None:
    session = ChatSession(mode="observe")
    result = run_turn(session, "I'm hanging clothes", _QuietAdapter())
    assert result.stop_reason != "pack_fast_path"
    assert not any(r.get("tool") == "life_time_start" for r in result.tool_receipts)
    assert _running_count() == 0


def test_im_at_the_gym_fast_path_stays_gym(data_root: Path) -> None:
    session = ChatSession(mode="agent")
    result = run_turn(session, "I'm at the gym", _ShouldNotRunAdapter())
    assert result.stop_reason == "pack_fast_path"
    assert any(r.get("tool") == "life_gym_start" for r in result.tool_receipts)
    assert not any(r.get("tool") == "life_time_start" for r in result.tool_receipts)


def test_yaml_sleep_and_status_still_fast_path(data_root: Path) -> None:
    sleep = run_turn(
        ChatSession(mode="agent"), "going to sleep", _ShouldNotRunAdapter()
    )
    assert sleep.stop_reason == "pack_fast_path"
    assert any(r.get("tool") == "life_time_start" for r in sleep.tool_receipts)
    status = run_turn(
        ChatSession(mode="observe"), "what's running", _ShouldNotRunAdapter()
    )
    assert status.stop_reason == "pack_fast_path"
    assert any(r.get("tool") == "life_time_status" for r in status.tool_receipts)
    stop = run_turn(
        ChatSession(mode="agent"), "stop timer", _ShouldNotRunAdapter()
    )
    assert stop.stop_reason == "pack_fast_path"
    assert any(r.get("tool") == "life_time_stop" for r in stop.tool_receipts)


# --- Mouth ⊆ receipt ---


_DURATION_CLAIM = ("minute", "minutes", "logged")


def test_speak_miss_stop_no_duration() -> None:
    spoken = _speak_time_stop({"ok": False, "reason": "no_active_block"})
    low = spoken.lower()
    assert "no_active_block" not in low
    for token in _DURATION_CLAIM:
        assert token not in low
    assert "0" not in spoken
    assert numeric_tokens(spoken) == []


def test_miss_stop_mouth_no_minutes(data_root: Path) -> None:
    result = run_turn(
        ChatSession(mode="agent"), "stop timer", _ShouldNotRunAdapter()
    )
    assert result.stop_reason == "pack_fast_path"
    stop = next(r for r in result.tool_receipts if r.get("tool") == "life_time_stop")
    data = stop.get("data") or {}
    assert data.get("ok") is False
    assert data.get("reason") == "no_active_block"
    assert data.get("duration_s") is None
    spoken = result.text or ""
    low = spoken.lower()
    for token in _DURATION_CLAIM:
        assert token not in low, spoken
    assert "logged" not in low
    _assert_mouth_subset(spoken, data)


def test_start_speak_from_receipt_no_duration(data_root: Path) -> None:
    result = run_turn(
        ChatSession(mode="agent"), "I'm hanging clothes", _ShouldNotRunAdapter()
    )
    start = next(r for r in result.tool_receipts if r.get("tool") == "life_time_start")
    data = start.get("data") or {}
    assert data.get("ok") is True
    assert data.get("kind") == "custom"
    assert data.get("label") == "hanging clothes"
    assert data.get("started_at")
    assert data.get("duration_s") is None
    spoken = result.text or ""
    assert "hanging clothes" in spoken.lower() or "custom" in spoken.lower()
    for token in _DURATION_CLAIM:
        assert token not in spoken.lower(), spoken
    _assert_mouth_subset(spoken, data)


def test_stop_after_start_duration_only_from_receipt(data_root: Path) -> None:
    run_turn(ChatSession(mode="agent"), "start focus: work", _ShouldNotRunAdapter())
    result = run_turn(
        ChatSession(mode="agent"), "stop timer", _ShouldNotRunAdapter()
    )
    stop = next(r for r in result.tool_receipts if r.get("tool") == "life_time_stop")
    data = stop.get("data") or {}
    assert data.get("ok") is True
    assert "duration_s" in data
    spoken = result.text or ""
    for token in _DURATION_CLAIM:
        assert token not in spoken.lower(), spoken
    _assert_mouth_subset(spoken, data)
