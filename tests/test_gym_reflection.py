"""M26 gym v1.0 implement — capture receipt honesty + gym day/week retrieve."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

from ada.cortex.charter import build_system_charter
from ada.dream.delta import build_delta
from ada.dream.merge import apply_manage_result
from ada.harness.gym_date import is_gym_read_shape, parse_gym_date
from ada.harness.loop import (
    _speak_gym_day,
    _speak_gym_week,
    _speak_lift_log,
    run_turn,
)
from ada.harness.mouth import allowed_numeric_tokens, numeric_tokens
from ada.harness.nutrition_date import is_nutrition_read_shape
from ada.harness.pack_router import route_utterance
from ada.harness.session import ChatSession
from ada.io.paths import get_paths
from ada.logs import gym as gym_mod
from ada.logs.connection import open_life_db
from ada.logs.gym_import import import_exercise_seed
from ada.logs.gym_reflection import gym_day, gym_window
from ada.logs.gym_split import set_gym_split
from ada.memory.facts import ensure_prefs
from ada.memory.staging import list_staged
from ada.tools.gateway import Gateway
from ada.tools.toolspec import SPECS_BY_NAME, WRITE_TOOL_NAMES
from ada.body.identity import create_identity


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


def _iso_for_local_day(local_day: str, hour: int = 10) -> str:
    tz = ZoneInfo("Pacific/Auckland")
    dt = datetime.strptime(local_day, "%Y-%m-%d").replace(
        hour=hour, minute=0, second=0, tzinfo=tz
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
        "ada.logs.gym_reflection",
        datetime=dt,
    )


@pytest.fixture
def seeded_gym(data_root: Path) -> Path:
    ensure_prefs(paths=get_paths())
    import_exercise_seed(paths=get_paths())
    return data_root


def _log_set(gw: Gateway, *, name: str, load_kg, reps: int, when: str | None = None):
    payload = {"sets": [{"exercise_name": name, "load_kg": load_kg, "reps": reps}]}
    if when:
        with patch("ada.logs.gym.utc_now_iso", return_value=when):
            return gw.execute("life_lift_log", payload)
    return gw.execute("life_lift_log", payload)


# --- Slice A: capture sanitization ---


def test_lift_receipt_and_speak_include_load_reps(seeded_gym: Path) -> None:
    session = ChatSession(mode="agent")
    result = run_turn(
        session, "log lift: flat bench 50kg x6", _ShouldNotRunAdapter()
    )
    assert result.stop_reason == "pack_fast_path"
    lift = next(r for r in result.tool_receipts if r.get("tool") == "life_lift_log")
    assert lift.get("ok") is True
    data = lift.get("data") or {}
    row = (data.get("resolved") or [{}])[0]
    assert row.get("load_kg") == 50.0
    assert row.get("reps") == 6
    written = (data.get("sets") or [{}])[0]
    assert written.get("load_kg") == 50.0
    assert written.get("reps") == 6
    spoken = result.text or ""
    assert "50" in spoken
    assert "6" in spoken
    assert "Logged" in spoken
    _assert_mouth_subset(spoken, data)
    with open_life_db(paths=get_paths()) as conn:
        db = conn.execute(
            "SELECT load_kg, reps FROM gym_sets ORDER BY logged_at DESC LIMIT 1"
        ).fetchone()
    assert db["load_kg"] == 50.0
    assert db["reps"] == 6


def test_bodyweight_receipt_null_load_no_zero_kg(seeded_gym: Path) -> None:
    session = ChatSession(mode="agent")
    result = run_turn(session, "log lift: pull-ups x8", _ShouldNotRunAdapter())
    assert result.stop_reason == "pack_fast_path"
    lift = next(r for r in result.tool_receipts if r.get("tool") == "life_lift_log")
    data = lift.get("data") or {}
    row = (data.get("resolved") or [{}])[0]
    assert row.get("load_kg") is None
    assert row.get("reps") == 8
    spoken = result.text or ""
    assert "8" in spoken
    assert "0 kg" not in spoken.lower()
    assert " 0 " not in f" {spoken} "
    _assert_mouth_subset(spoken, data)
    with open_life_db(paths=get_paths()) as conn:
        db = conn.execute(
            "SELECT load_kg, reps FROM gym_sets ORDER BY logged_at DESC LIMIT 1"
        ).fetchone()
    assert db["load_kg"] is None
    assert db["reps"] == 8


def test_incomplete_name_only_no_write(seeded_gym: Path) -> None:
    session = ChatSession(mode="agent")
    result = run_turn(session, "log lift: flat bench", _ShouldNotRunAdapter())
    assert result.stop_reason == "missing_life_receipt"
    assert not any(r.get("tool") == "life_lift_log" for r in result.tool_receipts)
    assert "Logged" not in (result.text or "")
    with open_life_db(paths=get_paths()) as conn:
        n = conn.execute("SELECT COUNT(*) FROM gym_sets").fetchone()[0]
    assert int(n) == 0


def test_speak_lift_ok_false_no_logged() -> None:
    spoken = _speak_lift_log(
        {"ok": False, "resolved": [{"exercise_name": "bench", "load_kg": 50, "reps": 6}]}
    )
    assert "Logged" not in spoken
    assert "50" not in spoken


def test_last_closed_ignores_open_bout(seeded_gym: Path) -> None:
    gw = Gateway(mode="agent")
    a = _log_set(gw, name="bench press", load_kg=60, reps=5)
    assert a.ok
    eid = (a.data.get("resolved") or [{}])[0].get("exercise_id")
    ended = gw.execute("life_gym_end", {})
    assert ended.ok
    open_log = _log_set(gw, name="bench press", load_kg=999, reps=1)
    assert open_log.ok
    prior = gym_mod.last_closed_receipt_fields(str(eid))
    assert prior is not None
    assert prior["last_load_kg"] == 60
    assert prior["last_reps"] == 5
    assert prior["last_load_kg"] != 999
    assert open_log.data.get("last_load_kg") == 60


# --- Slice B: gym retrieve ---


def test_gym_tools_observe_agent_not_writes() -> None:
    assert "life_gym_day" in SPECS_BY_NAME
    assert "life_gym_week" in SPECS_BY_NAME
    assert "life_gym_day" not in WRITE_TOOL_NAMES
    assert "life_gym_week" not in WRITE_TOOL_NAMES
    assert "life_lift_log" in WRITE_TOOL_NAMES


def test_observe_allows_gym_day_week_denies_lift(seeded_gym: Path) -> None:
    obs = Gateway(mode="observe")
    assert obs.execute("life_gym_day", {}).ok
    assert obs.execute("life_gym_week", {"days": 7}).ok
    denied = obs.execute(
        "life_lift_log",
        {"sets": [{"exercise_name": "bench", "load_kg": 50, "reps": 6}]},
    )
    assert not denied.ok
    assert denied.outcome == "denied"


def test_nutrition_regex_does_not_steal_gym_reads() -> None:
    gym_utt = "what did i lift yesterday"
    assert is_gym_read_shape(gym_utt)
    assert not is_nutrition_read_shape(gym_utt)
    eat_utt = "what did i eat yesterday"
    assert is_nutrition_read_shape(eat_utt)
    assert not is_gym_read_shape(eat_utt)


def test_pack_routes_date_and_days_args(seeded_gym: Path) -> None:
    nutr, gym = _freeze_read_clock("2026-09-02")
    with nutr, gym:
        y = route_utterance("what did i lift yesterday")
        week = route_utterance("lifts this week")
        gym_week = route_utterance("gym this week")
        today_status = route_utterance("what did i lift")
        eat = route_utterance("what did i eat yesterday")
        assert parse_gym_date("what did i lift yesterday") == "2026-09-01"
    assert y is not None
    assert y["verb"] == "gym_day"
    assert y["tool"] == "life_gym_day"
    assert y["args"]["date"] == "2026-09-01"
    assert week is not None
    assert week["verb"] == "gym_week"
    assert week["tool"] == "life_gym_week"
    assert week["args"].get("days") == 7
    assert gym_week is not None
    assert gym_week["tool"] == "life_gym_week"
    assert today_status is not None
    assert today_status["verb"] == "gym_status"
    assert today_status["tool"] == "life_gym_status"
    assert not (today_status.get("args") or {}).get("date")
    assert eat is not None
    assert eat["tool"] == "life_nutrition_day"
    assert eat["args"]["date"] == "2026-09-01"


def test_week_query_not_today_status(seeded_gym: Path) -> None:
    nutr, gym = _freeze_read_clock("2026-09-02")
    gw = Gateway(mode="agent")
    _log_set(
        gw,
        name="flat bench",
        load_kg=50,
        reps=6,
        when=_iso_for_local_day("2026-09-01"),
    )
    with nutr, gym:
        session = ChatSession(mode="observe")
        result = run_turn(session, "lifts this week", _ShouldNotRunAdapter())
        status = route_utterance("what did i lift")
    assert result.stop_reason == "pack_fast_path"
    tools = [r.get("tool") for r in result.tool_receipts]
    assert "life_gym_week" in tools
    assert "life_gym_status" not in tools
    assert "life_gym_day" not in tools
    week = next(r for r in result.tool_receipts if r.get("tool") == "life_gym_week")
    assert week.get("ok") is True
    assert int(week.get("data", {}).get("window_days") or 0) == 7
    assert status is not None
    assert status["tool"] == "life_gym_status"


def test_gym_day_yesterday_fast_path(seeded_gym: Path) -> None:
    nutr, gym = _freeze_read_clock("2026-09-02")
    gw = Gateway(mode="agent")
    logged = _log_set(
        gw,
        name="flat bench",
        load_kg=50,
        reps=6,
        when=_iso_for_local_day("2026-09-01"),
    )
    assert logged.ok
    with nutr, gym:
        session = ChatSession(mode="observe")
        result = run_turn(
            session, "what did i lift yesterday", _ShouldNotRunAdapter()
        )
    assert result.stop_reason == "pack_fast_path"
    tools = [r.get("tool") for r in result.tool_receipts]
    assert tools == ["life_gym_day"]
    data = result.tool_receipts[0].get("data") or {}
    assert data.get("date") == "2026-09-01"
    assert data.get("cite") == "gym:day:2026-09-01"
    assert data.get("set_count") == 1
    assert data.get("tonnage_kg") == pytest.approx(300.0)
    assert (data.get("sets") or [{}])[0].get("load_kg") == 50.0
    spoken = result.text or ""
    _assert_mouth_subset(spoken, data)
    assert "Logged" not in spoken


def test_rest_day_gap(seeded_gym: Path) -> None:
    nutr, gym = _freeze_read_clock("2026-09-02")
    gw = Gateway(mode="agent")
    _log_set(
        gw,
        name="flat bench",
        load_kg=50,
        reps=6,
        when=_iso_for_local_day("2026-08-31"),
    )
    _log_set(
        gw,
        name="flat bench",
        load_kg=55,
        reps=5,
        when=_iso_for_local_day("2026-09-02"),
    )
    with nutr, gym:
        window = gym_window(days=3, paths=get_paths())
    assert window["ok"] is True
    assert window["days_logged"] == 2
    by_day = {d["day"]: d for d in window["days"]}
    assert by_day["2026-09-01"]["set_count"] == 0
    assert by_day["2026-09-01"]["rest"] is True
    assert "2026-09-01" in window["rest_days"]
    assert by_day["2026-08-31"]["cite"] == "gym:day:2026-08-31"
    assert by_day["2026-09-02"]["set_count"] == 1


def test_bodyweight_null_on_gym_day(seeded_gym: Path) -> None:
    gw = Gateway(mode="agent")
    logged = gw.execute(
        "life_lift_log",
        {"sets": [{"exercise_name": "pull-ups", "load_kg": None, "reps": 8}]},
    )
    assert logged.ok
    assert (logged.data.get("resolved") or [{}])[0].get("load_kg") is None
    day = Gateway(mode="observe").execute("life_gym_day", {})
    assert day.ok
    sets = (day.data or {}).get("sets") or []
    assert sets
    assert sets[0].get("load_kg") is None
    assert sets[0].get("reps") == 8
    spoken = _speak_gym_day(day.data or {})
    assert "0 kg" not in spoken.lower()
    _assert_mouth_subset(spoken, day.data or {})


def test_gym_window_days_cap(seeded_gym: Path) -> None:
    assert gym_window(days=99, paths=get_paths())["window_days"] == 31
    assert gym_window(days=0, paths=get_paths())["window_days"] == 1
    assert gym_window(days=7, paths=get_paths())["window_days"] == 7


def test_coverage_vs_split_pattern(seeded_gym: Path) -> None:
    set_gym_split(
        days={
            "mon": {"label": "Push", "body_parts": ["chest"]},
            "tue": {"label": "Rest", "body_parts": []},
            "wed": {"label": "Pull", "body_parts": ["lats"]},
        },
        confirmed=True,
        paths=get_paths(),
    )
    nutr, gym = _freeze_read_clock("2026-08-31")  # Monday
    gw = Gateway(mode="agent")
    # Monday Push logged as pull-ups — chest miss if catalog says back.
    _log_set(
        gw,
        name="pull-ups",
        load_kg=None,
        reps=8,
        when=_iso_for_local_day("2026-08-31"),
    )
    with nutr, gym:
        window = gym_window(days=1, paths=get_paths())
        day = gym_day(date="2026-08-31", paths=get_paths())
    assert window["coverage"]["has_split"] is True
    assert day.get("split_label") == "Push"
    assert any("coverage miss" in p for p in window["patterns"]) or any(
        d.get("missing_body_parts") for d in window["coverage"]["days"]
    )


def test_mouth_numbers_subset_week_receipt(seeded_gym: Path) -> None:
    nutr, gym = _freeze_read_clock("2026-09-02")
    gw = Gateway(mode="agent")
    _log_set(
        gw,
        name="flat bench",
        load_kg=50,
        reps=6,
        when=_iso_for_local_day("2026-09-01"),
    )
    with nutr, gym:
        week = Gateway(mode="observe").execute("life_gym_week", {"days": 7})
    assert week.ok
    spoken = _speak_gym_week(week.data or {})
    _assert_mouth_subset(spoken, week.data or {})
    scratch = get_paths().scratch / "gym_reflection_latest.json"
    assert scratch.is_file()


def test_charter_does_not_substitute_gym_status_for_week() -> None:
    text = build_system_charter(
        mode="observe",
        include_worldview=False,
        pack_hint={"verb": "gym_week", "tool": "life_gym_week"},
    )
    assert "life_gym_week" in text
    assert "do not substitute" in text
    assert "life_gym_status" in text


def test_dream_does_not_auto_merge_gym_split(data_root: Path) -> None:
    paths = get_paths()
    create_identity(paths=paths)
    ensure_prefs(paths)
    delta = build_delta(paths=paths)
    assert "gym_window" not in delta
    assert "gym_reflection" not in delta
    assert "life_gym_day/week" in delta["summary_text"] or "life_gym_week" in delta["summary_text"]
    info = apply_manage_result(
        {
            "digest": "",
            "fact_candidates": [
                {
                    "key": "gym_split",
                    "value": {"days": {"mon": {"label": "Push", "body_parts": ["chest"]}}},
                }
            ],
            "worldview_notes": [],
            "open_loops": [],
            "conflicts": [],
        },
        paths=paths,
        dream_id="gym-stage",
    )
    assert not any(m.get("key") == "prefs.gym_split" for m in info["merged"])
    staged = list_staged(paths=paths)
    reasons = {s.get("reason") for s in staged}
    assert "gym_split_always_stage" in reasons
    assert not (paths.facts / "gym_split.yaml").is_file()
