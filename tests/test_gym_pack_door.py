"""M26 gym v1.2 — pack door parity with food (structural NL → spine)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ada.cortex.adapter import CortexTurn, ProposedToolCall
from ada.harness.gym_spine import FOLLOW_ON_ASK, NEED_KG_ASK, build_lift_log_args
from ada.harness.loop import _model_tool_blocked, run_turn
from ada.harness.pack_router import (
    is_gym_end_utterance,
    is_gym_start_utterance,
    is_incomplete_lift_utterance,
    is_lift_log_utterance,
    lift_log_fast_path_args,
    route_utterance,
)
from ada.harness.session import ChatSession
from ada.io.paths import get_paths
from ada.logs import gym as gym_mod
from ada.logs.connection import open_life_db
from ada.logs.gym_import import import_exercise_seed
from ada.tools.gateway import Gateway


class _ShouldNotRunAdapter:
    model = "fake"

    def generate(self, *, system, contents, tools=None):
        raise AssertionError("pack fast-path should finish before model generate")


class _QuietAdapter:
    model = "fake"

    def generate(self, *, system, contents, tools=None):
        return CortexTurn(text="logged it", tool_calls=[])


def _set_count() -> int:
    with open_life_db(paths=get_paths()) as conn:
        return int(conn.execute("SELECT COUNT(*) AS n FROM gym_sets").fetchone()["n"])


def _session_count() -> int:
    with open_life_db(paths=get_paths()) as conn:
        return int(
            conn.execute("SELECT COUNT(*) AS n FROM gym_sessions").fetchone()["n"]
        )


def _last_sets(n: int) -> list:
    with open_life_db(paths=get_paths()) as conn:
        return conn.execute(
            """
            SELECT exercise_name_raw, load_kg, reps
            FROM gym_sets
            ORDER BY sort_order ASC, logged_at ASC
            """
        ).fetchall()[-n:]


# --- Router ---


@pytest.mark.parametrize(
    "text",
    [
        "start gym",
        "I started gym",
        "I started a gym",
        "started gym",
        "starting gym",
        "I'm at the gym",
        "at the gym",
    ],
)
def test_route_gym_start_shapes(text: str) -> None:
    assert is_gym_start_utterance(text)
    r = route_utterance(text)
    assert r is not None, text
    assert r["verb"] == "gym_start", text
    assert r["tool"] == "life_gym_start", text


@pytest.mark.parametrize(
    "text",
    [
        "end gym",
        "close gym",
        "end workout",
        "I finished gym",
        "done gym",
        "gym done",
        "finished workout",
    ],
)
def test_route_gym_end_shapes(text: str) -> None:
    assert is_gym_end_utterance(text)
    r = route_utterance(text)
    assert r is not None, text
    assert r["verb"] == "gym_end", text
    assert r["tool"] == "life_gym_end", text


def test_done_colon_not_gym_end() -> None:
    assert not is_gym_end_utterance("done: thesis")
    r = route_utterance("done: thesis")
    assert r is not None
    assert r["verb"] == "due_done"


@pytest.mark.parametrize(
    "text",
    [
        "gym this week",
        "lifts this week",
        "what did i lift yesterday",
    ],
)
def test_gym_reads_not_stolen_by_start_or_lift(text: str) -> None:
    assert not is_gym_start_utterance(text)
    assert not is_lift_log_utterance(text)
    r = route_utterance(text)
    assert r is not None, text
    assert r["verb"] in {"gym_week", "gym_day"}, text
    if r["verb"] == "gym_week":
        assert r["args"].get("days") == 7
    else:
        assert r["args"].get("date")


@pytest.mark.parametrize(
    "text",
    [
        "flat bench 3x6 at 50kg",
        "flat bench 3x6 @ 50",
        "flat bench 3x6 @ 50kg",
        "3x6 at 50kg flat bench",
        "flat bench 50kg x 6",
        "3x6 at 50kg",
        "50kg x6",
        "log lift: flat bench 50kg x6",
    ],
)
def test_route_lift_write_shapes(text: str) -> None:
    assert is_lift_log_utterance(text), text
    r = route_utterance(text)
    assert r is not None, text
    assert r["verb"] == "lift_log", text
    assert r["tool"] == "life_lift_log", text


def test_what_did_i_lift_at_the_gym_is_status_not_start() -> None:
    text = "what did i lift at the gym"
    assert not is_gym_start_utterance(text)
    r = route_utterance(text)
    assert r is not None
    assert r["verb"] == "gym_status"
    assert r["tool"] == "life_gym_status"
    assert not is_lift_log_utterance("I had a good session")
    assert not is_lift_log_utterance("flat bench")
    assert not is_incomplete_lift_utterance("I like bench")
    assert not is_incomplete_lift_utterance("what did i lift")
    assert route_utterance("I had a good session") is None


@pytest.mark.parametrize("text", ["60x6", "3x6", "60 x 6", "3 x 6"])
def test_bare_nxm_without_unit_is_incomplete_not_write(text: str) -> None:
    assert is_incomplete_lift_utterance(text), text
    assert not is_lift_log_utterance(text), text
    assert not is_gym_start_utterance(text), text
    assert route_utterance(text) is None, text
    built = build_lift_log_args(text)
    assert built["ok"] is False
    assert built.get("sets") == []
    assert built.get("reason") == "missing_load_unit"
    assert NEED_KG_ASK in str(built.get("ask") or "")


@pytest.mark.parametrize(
    "text",
    ["60kg x6", "3x6 at 50kg", "log lift: flat bench 50kg x6"],
)
def test_complete_lift_shapes_not_incomplete(text: str) -> None:
    assert is_lift_log_utterance(text), text
    assert not is_incomplete_lift_utterance(text), text


def test_name_only_catalog_is_incomplete(data_root: Path) -> None:
    import_exercise_seed(paths=get_paths())
    for text in ("Incline bench", "incline bench", "flat bench"):
        assert is_incomplete_lift_utterance(text), text
        assert not is_lift_log_utterance(text), text
        assert route_utterance(text) is None, text
    assert not is_incomplete_lift_utterance("I like bench")
    assert not is_incomplete_lift_utterance("what did i lift")


def test_name_only_custom_exercise_is_incomplete(data_root: Path) -> None:
    from ada.logs.gym_custom import save_custom_exercise

    save_custom_exercise(display_name="My cable fly", paths=get_paths())
    assert is_incomplete_lift_utterance("My cable fly")
    assert not is_lift_log_utterance("My cable fly")
    result = run_turn(
        ChatSession(mode="agent"), "My cable fly", _ShouldNotRunAdapter()
    )
    assert result.stop_reason == "missing_life_receipt"
    assert "Logged" not in (result.text or "")
    assert _set_count() == 0
    assert _session_count() == 0


def test_lift_log_fast_path_args_strips_prefix() -> None:
    args = lift_log_fast_path_args("log lift: flat bench 3x6 at 50kg")
    assert args is not None
    assert "flat bench" in args["utterance"].lower()


# --- Spine ---


def test_spine_expands_sets_x_reps_at_load() -> None:
    for utterance in (
        "flat bench 3x6 at 50kg",
        "flat bench 3x6 @ 50",
        "flat bench 3x6 @ 50kg",
        "3x6 at 50kg flat bench",
    ):
        built = build_lift_log_args(utterance)
        assert built["ok"] is True, utterance
        assert len(built["sets"]) == 3, utterance
        assert all(s["exercise_name"] == "flat bench" for s in built["sets"]), utterance
        assert all(s["load_kg"] == 50.0 for s in built["sets"]), utterance
        assert all(s["reps"] == 6 for s in built["sets"]), utterance


def test_spine_bodyweight_stays_null() -> None:
    built = build_lift_log_args("pull-ups x8")
    assert built["ok"] is True
    assert built["sets"][0]["load_kg"] is None
    assert built["sets"][0]["reps"] == 8


def test_spine_incomplete_fail_closed() -> None:
    for utterance in ("flat bench", "lat pulldown somehow heavy"):
        built = build_lift_log_args(utterance)
        assert built["ok"] is False, utterance
        assert built.get("sets") == []
        assert built.get("ask")


def test_spine_follow_on_with_name() -> None:
    for utterance in ("3x6 at 50kg", "50kg x6"):
        built = build_lift_log_args(utterance, follow_on_name="flat bench")
        assert built["ok"] is True, utterance
        assert built["sets"][0]["exercise_name"] == "flat bench"
        assert built["sets"][0]["load_kg"] == 50.0
        if utterance.startswith("3x"):
            assert len(built["sets"]) == 3
            assert all(s["reps"] == 6 for s in built["sets"])
        else:
            assert len(built["sets"]) == 1
            assert built["sets"][0]["reps"] == 6


def test_spine_follow_on_without_name_asks() -> None:
    for utterance in ("3x6 at 50kg", "50kg x6"):
        built = build_lift_log_args(utterance)
        assert built["ok"] is False, utterance
        assert built.get("sets") == []
        assert built.get("reason") == "follow_on_no_open"
        assert FOLLOW_ON_ASK in str(built.get("ask") or "")


# --- Loop / HUD ---


def test_structural_lift_nl_fast_path_without_prefix(data_root: Path) -> None:
    import_exercise_seed(paths=get_paths())
    session = ChatSession(mode="agent")
    result = run_turn(session, "flat bench 3x6 at 50kg", _ShouldNotRunAdapter())
    assert result.stop_reason == "pack_fast_path"
    assert any(r.get("tool") == "life_lift_log" for r in result.tool_receipts)
    spoken = result.text or ""
    assert "Logged" in spoken
    assert "50" in spoken
    assert "6" in spoken
    rows = _last_sets(3)
    assert len(rows) == 3
    assert all(float(r["load_kg"]) == 50.0 for r in rows)
    assert all(int(r["reps"]) == 6 for r in rows)


def test_lift_intent_forces_spine_without_pack_hint(
    data_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import_exercise_seed(paths=get_paths())
    monkeypatch.setattr(
        "ada.harness.pack_router.route_utterance",
        lambda text, **kwargs: None,
    )
    session = ChatSession(mode="agent")
    result = run_turn(session, "flat bench 3x6 at 50kg", _ShouldNotRunAdapter())
    assert result.stop_reason == "pack_fast_path"
    assert any(r.get("tool") == "life_lift_log" for r in result.tool_receipts)
    assert _set_count() == 3


def test_observe_structural_lift_does_not_write(data_root: Path) -> None:
    import_exercise_seed(paths=get_paths())
    session = ChatSession(mode="observe")
    result = run_turn(session, "flat bench 3x6 at 50kg", _QuietAdapter())
    assert result.stop_reason != "pack_fast_path"
    assert not any(r.get("tool") == "life_lift_log" for r in result.tool_receipts)
    assert _set_count() == 0


def test_follow_on_binds_open_session_last_exercise(data_root: Path) -> None:
    import_exercise_seed(paths=get_paths())
    session = ChatSession(mode="agent")
    first = run_turn(session, "log lift: flat bench 50kg x6", _ShouldNotRunAdapter())
    assert first.stop_reason == "pack_fast_path"
    follow = run_turn(
        ChatSession(mode="agent"), "3x6 at 50kg", _ShouldNotRunAdapter()
    )
    assert follow.stop_reason == "pack_fast_path"
    assert any(r.get("tool") == "life_lift_log" for r in follow.tool_receipts)
    rows = _last_sets(4)
    assert len(rows) == 4
    follow_rows = rows[-3:]
    assert all("bench" in str(r["exercise_name_raw"]).lower() for r in follow_rows)
    assert all(float(r["load_kg"]) == 50.0 for r in follow_rows)


def test_follow_on_without_open_session_asks(data_root: Path) -> None:
    import_exercise_seed(paths=get_paths())
    session = ChatSession(mode="agent")
    result = run_turn(session, "3x6 at 50kg", _ShouldNotRunAdapter())
    assert result.stop_reason == "missing_life_receipt"
    assert not any(r.get("tool") == "life_lift_log" for r in result.tool_receipts)
    assert "Logged" not in (result.text or "")
    assert _set_count() == 0


def test_follow_on_empty_open_session_asks(data_root: Path) -> None:
    import_exercise_seed(paths=get_paths())
    start = run_turn(ChatSession(mode="agent"), "start gym", _ShouldNotRunAdapter())
    assert start.stop_reason == "pack_fast_path"
    result = run_turn(ChatSession(mode="agent"), "50kg x6", _ShouldNotRunAdapter())
    assert result.stop_reason == "missing_life_receipt"
    assert not any(r.get("tool") == "life_lift_log" for r in result.tool_receipts)
    assert _set_count() == 0
    assert gym_mod.last_open_session_exercise_name() is None


def test_follow_on_ignores_last_closed_bout(data_root: Path) -> None:
    import_exercise_seed(paths=get_paths())
    gw = Gateway(mode="agent")
    logged = gw.execute(
        "life_lift_log",
        {"sets": [{"exercise_name": "flat bench", "load_kg": 50, "reps": 6}]},
    )
    assert logged.ok
    ended = gw.execute("life_gym_end", {})
    assert ended.ok
    assert gym_mod.last_open_session_exercise_name() is None
    result = run_turn(ChatSession(mode="agent"), "3x6 at 50kg", _ShouldNotRunAdapter())
    assert result.stop_reason == "missing_life_receipt"
    assert not any(r.get("tool") == "life_lift_log" for r in result.tool_receipts)
    assert _set_count() == 1


def test_incomplete_name_only_no_logged_mouth(data_root: Path) -> None:
    session = ChatSession(mode="agent")
    result = run_turn(session, "log lift: flat bench", _ShouldNotRunAdapter())
    assert result.stop_reason == "missing_life_receipt"
    assert "Logged" not in (result.text or "")
    assert _set_count() == 0


def test_start_structural_nl_fast_path(data_root: Path) -> None:
    session = ChatSession(mode="agent")
    result = run_turn(session, "I'm at the gym", _ShouldNotRunAdapter())
    assert result.stop_reason == "pack_fast_path"
    assert any(r.get("tool") == "life_gym_start" for r in result.tool_receipts)


def test_cortex_lift_log_denied_on_lift_turn(data_root: Path) -> None:
    class _CortexLift:
        model = "fake"
        _n = 0

        def generate(self, *, system, contents, tools=None):
            self._n += 1
            if self._n == 1:
                return CortexTurn(
                    text=None,
                    tool_calls=[
                        ProposedToolCall(
                            name="life_lift_log",
                            args={
                                "sets": [
                                    {
                                        "exercise_name": "bench",
                                        "load_kg": 99,
                                        "reps": 1,
                                    }
                                ]
                            },
                            call_id="cortex-lift",
                        )
                    ],
                )
            return CortexTurn(text="ok", tool_calls=[])

    session = ChatSession(mode="agent")
    session.gateway = Gateway(mode="agent")
    session.gateway.turn_user_text = "flat bench 50kg x6"
    assert _model_tool_blocked(session, "life_lift_log") is not None

    import_exercise_seed(paths=get_paths())
    # Skip structural + pack fast-path so the model step runs.
    from unittest.mock import patch

    with (
        patch("ada.harness.loop._maybe_gym_write_fast_path", return_value=(None, None)),
        patch("ada.harness.loop._maybe_pack_fast_path", return_value=(None, None)),
    ):
        result = run_turn(
            ChatSession(mode="agent"),
            "flat bench 50kg x6",
            _CortexLift(),
        )
    denied = [
        r
        for r in result.tool_receipts
        if r.get("tool") == "life_lift_log" and r.get("outcome") == "denied"
    ]
    assert denied
    assert "gym_spine" in str(denied[0].get("denied_reason") or "")
    assert _set_count() == 0


def test_bare_nxm_after_close_asks_no_write_no_generate(data_root: Path) -> None:
    import_exercise_seed(paths=get_paths())
    gw = Gateway(mode="agent")
    logged = gw.execute(
        "life_lift_log",
        {"sets": [{"exercise_name": "flat bench", "load_kg": 50, "reps": 6}]},
    )
    assert logged.ok
    ended = gw.execute("life_gym_end", {})
    assert ended.ok
    sessions_before = _session_count()
    sets_before = _set_count()
    for text in ("60x6", "3x6"):
        result = run_turn(ChatSession(mode="agent"), text, _ShouldNotRunAdapter())
        assert result.stop_reason == "missing_life_receipt", text
        spoken = result.text or ""
        assert "Logged" not in spoken
        assert "session started" not in spoken.lower()
        assert NEED_KG_ASK.split("—")[0].strip() in spoken or "kg" in spoken.lower()
        assert not any(r.get("tool") == "life_lift_log" for r in result.tool_receipts)
        assert not any(r.get("tool") == "life_gym_start" for r in result.tool_receipts)
        assert _session_count() == sessions_before
        assert _set_count() == sets_before


def test_name_only_after_close_asks_no_write_no_generate(data_root: Path) -> None:
    import_exercise_seed(paths=get_paths())
    gw = Gateway(mode="agent")
    logged = gw.execute(
        "life_lift_log",
        {"sets": [{"exercise_name": "flat bench", "load_kg": 50, "reps": 6}]},
    )
    assert logged.ok
    ended = gw.execute("life_gym_end", {})
    assert ended.ok
    sessions_before = _session_count()
    sets_before = _set_count()
    for text in ("Incline bench", "flat bench"):
        result = run_turn(ChatSession(mode="agent"), text, _ShouldNotRunAdapter())
        assert result.stop_reason == "missing_life_receipt", text
        spoken = result.text or ""
        assert "Logged" not in spoken
        assert "session started" not in spoken.lower()
        assert "load" in spoken.lower() or "reps" in spoken.lower()
        assert not any(r.get("tool") == "life_lift_log" for r in result.tool_receipts)
        assert not any(r.get("tool") == "life_gym_start" for r in result.tool_receipts)
        assert _session_count() == sessions_before
        assert _set_count() == sets_before


def test_open_session_60kg_x6_follow_on_bench(data_root: Path) -> None:
    import_exercise_seed(paths=get_paths())
    first = run_turn(
        ChatSession(mode="agent"),
        "log lift: flat bench 50kg x6",
        _ShouldNotRunAdapter(),
    )
    assert first.stop_reason == "pack_fast_path"
    follow = run_turn(
        ChatSession(mode="agent"), "60kg x6", _ShouldNotRunAdapter()
    )
    assert follow.stop_reason == "pack_fast_path"
    assert any(r.get("tool") == "life_lift_log" for r in follow.tool_receipts)
    rows = _last_sets(2)
    assert "bench" in str(rows[-1]["exercise_name_raw"]).lower()
    assert float(rows[-1]["load_kg"]) == 60.0
    assert int(rows[-1]["reps"]) == 6


def test_observe_incomplete_lift_does_not_write(data_root: Path) -> None:
    import_exercise_seed(paths=get_paths())
    for text in ("60x6", "Incline bench"):
        result = run_turn(ChatSession(mode="observe"), text, _QuietAdapter())
        assert result.stop_reason != "pack_fast_path", text
        assert not any(r.get("tool") == "life_lift_log" for r in result.tool_receipts)
        assert not any(r.get("tool") == "life_gym_start" for r in result.tool_receipts)
        assert _set_count() == 0
        assert _session_count() == 0


def test_cortex_denied_start_and_log_on_incomplete_60x6(data_root: Path) -> None:
    class _CortexInvent:
        model = "fake"
        _n = 0

        def generate(self, *, system, contents, tools=None):
            self._n += 1
            if self._n == 1:
                return CortexTurn(
                    text=None,
                    tool_calls=[
                        ProposedToolCall(
                            name="life_gym_start",
                            args={},
                            call_id="cortex-start",
                        )
                    ],
                )
            if self._n == 2:
                return CortexTurn(
                    text=None,
                    tool_calls=[
                        ProposedToolCall(
                            name="life_lift_log",
                            args={
                                "sets": [
                                    {
                                        "exercise_name": "Incline bench",
                                        "load_kg": 60,
                                        "reps": 6,
                                    }
                                ]
                            },
                            call_id="cortex-lift",
                        )
                    ],
                )
            return CortexTurn(text="ok", tool_calls=[])

    session = ChatSession(mode="agent")
    session.gateway = Gateway(mode="agent")
    session.gateway.turn_user_text = "60x6"
    assert _model_tool_blocked(session, "life_gym_start") is not None
    assert _model_tool_blocked(session, "life_lift_log") is not None

    from unittest.mock import patch

    with (
        patch("ada.harness.loop._maybe_gym_write_fast_path", return_value=(None, None)),
        patch("ada.harness.loop._maybe_pack_fast_path", return_value=(None, None)),
    ):
        result = run_turn(
            ChatSession(mode="agent"),
            "60x6",
            _CortexInvent(),
        )
    denied_tools = {
        r.get("tool")
        for r in result.tool_receipts
        if r.get("outcome") == "denied"
    }
    assert "life_gym_start" in denied_tools
    assert "life_lift_log" in denied_tools
    assert _session_count() == 0
    assert _set_count() == 0
    assert "Logged" not in (result.text or "")


def test_gym_reads_still_status_day_week(data_root: Path) -> None:
    import_exercise_seed(paths=get_paths())
    session = ChatSession(mode="agent")
    status = run_turn(session, "what did i lift", _ShouldNotRunAdapter())
    assert any(r.get("tool") == "life_gym_status" for r in status.tool_receipts)
    yesterday = run_turn(
        ChatSession(mode="agent"),
        "what did i lift yesterday",
        _ShouldNotRunAdapter(),
    )
    assert any(r.get("tool") == "life_gym_day" for r in yesterday.tool_receipts)
    week = run_turn(
        ChatSession(mode="agent"), "gym this week", _ShouldNotRunAdapter()
    )
    assert any(r.get("tool") == "life_gym_week" for r in week.tool_receipts)
    assert _set_count() == 0
    assert _session_count() == 0
