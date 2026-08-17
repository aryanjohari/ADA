"""M19a P0.1g HUD edge-case smoke — same path as HUD chat (`run_turn`).

Utterance table (test-local; not a pack YAML):

| id            | utterance                                      | expect                |
|---------------|------------------------------------------------|-----------------------|
| meal_prefix   | log meal: one medium banana for breakfast      | pack_fast_path        |
| meal_nl       | add one banana to breakfast                    | pack_fast_path        |
| wake          | I woke up                                      | pack_fast_path        |
| sleep         | going to sleep                                 | pack_fast_path        |
| sleep_period  | going to sleep.                                | pack_fast_path        |
| stop          | stop focus                                     | pack_fast_path        |
| lift          | log lift: flat bench 50kg x6                   | pack_fast_path        |
| lift_bw       | log lift: pull-ups x8                          | pack_fast_path        |
| capture       | capture: buy oat milk                          | pack_fast_path        |
| unknown_food  | log meal: flurmble glorp for breakfast         | missing_life_receipt  |
| due_prefix    | add due: finish thesis by Friday               | pack_fast_path        |
| due_nl        | gotta finish lab report by Thursday            | pack_fast_path        |
| due_list      | what's due                                     | pack_fast_path        |
| eat_q         | what did i eat                                 | pack_fast_path        |
| macros        | macros                                         | pack_fast_path        |
| good_morning  | good morning                                   | pack_fast_path        |
| due_done_miss | done: flurmble glorp                           | missing_life_receipt  |
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ada.cortex.adapter import CortexTurn, ProposedToolCall
from ada.harness.loop import _model_tool_blocked, run_turn
from ada.harness.meal_spine import build_meal_log_args
from ada.harness.session import ChatSession
from ada.hud.today import build_today
from ada.io.paths import get_paths
from ada.logs.connection import open_life_db
from ada.logs.food import insert_food
from ada.logs.gym_import import import_exercise_seed
from ada.memory.facts import ensure_prefs
from ada.memory.open_loops import list_loops
from ada.tools.gateway import Gateway

# P0.1g canned HUD utterances — drive via run_turn, not live Gemini.
HUD_EDGE_SMOKE: list[dict[str, str]] = [
    {
        "id": "meal_prefix",
        "utterance": "log meal: one medium banana for breakfast",
        "expect": "pack_fast_path",
    },
    {
        "id": "meal_nl",
        "utterance": "add one banana to breakfast",
        "expect": "pack_fast_path",
    },
    {"id": "wake", "utterance": "I woke up", "expect": "pack_fast_path"},
    {"id": "sleep", "utterance": "going to sleep", "expect": "pack_fast_path"},
    {"id": "sleep_period", "utterance": "going to sleep.", "expect": "pack_fast_path"},
    {"id": "stop", "utterance": "stop focus", "expect": "pack_fast_path"},
    {
        "id": "lift",
        "utterance": "log lift: flat bench 50kg x6",
        "expect": "pack_fast_path",
    },
    {
        "id": "lift_bw",
        "utterance": "log lift: pull-ups x8",
        "expect": "pack_fast_path",
    },
    {
        "id": "capture",
        "utterance": "capture: buy oat milk",
        "expect": "pack_fast_path",
    },
    {
        "id": "unknown_food",
        "utterance": "log meal: flurmble glorp for breakfast",
        "expect": "missing_life_receipt",
    },
    {
        "id": "due_prefix",
        "utterance": "add due: finish thesis by Friday",
        "expect": "pack_fast_path",
    },
    {
        "id": "due_nl",
        "utterance": "gotta finish lab report by Thursday",
        "expect": "pack_fast_path",
    },
    {"id": "due_list", "utterance": "what's due", "expect": "pack_fast_path"},
    {"id": "eat_q", "utterance": "what did i eat", "expect": "pack_fast_path"},
    {"id": "macros", "utterance": "macros", "expect": "pack_fast_path"},
    {"id": "good_morning", "utterance": "good morning", "expect": "pack_fast_path"},
    {
        "id": "due_done_miss",
        "utterance": "done: flurmble glorp",
        "expect": "missing_life_receipt",
    },
]


class _ShouldNotRunAdapter:
    model = "fake"

    def generate(self, *, system, contents, tools=None):
        raise AssertionError("pack fast-path should finish before model generate")


class _CapturingSink:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    def emit(self, event: str, payload: dict) -> None:
        self.events.append((event, payload))


class _QuietAdapter:
    """Observe/Plan path: model speaks, must not count as a log write."""

    model = "fake"

    def generate(self, *, system, contents, tools=None):
        return CortexTurn(text="logged it", tool_calls=[])


class _FactsAppendAdapter:
    model = "fake"

    def __init__(self) -> None:
        self.n = 0

    def generate(self, *, system, contents, tools=None):
        self.n += 1
        if self.n == 1:
            return CortexTurn(
                text=None,
                tool_calls=[
                    ProposedToolCall(
                        name="memory_facts_append",
                        args={"key": "capture.notes", "value": "should not stick"},
                    )
                ],
            )
        return CortexTurn(text="ok", tool_calls=[])


def _isolate_usda(monkeypatch: pytest.MonkeyPatch, data_root: Path) -> None:
    """Cache-miss meals must not hit operator USDA key on this host."""
    monkeypatch.delenv("USDA_FDC_API_KEY", raising=False)
    secrets = data_root / "secrets"
    secrets.mkdir(exist_ok=True)
    monkeypatch.setenv("ADA_SECRETS_DIR", str(secrets))


def _seed_banana() -> None:
    insert_food(
        name="Banana",
        source="custom",
        nutrients_per_100g={"energy_kcal": 89, "protein_g": 1.1, "carb_g": 22.8},
        default_serving_g=118,
        paths=get_paths(),
    )


@pytest.fixture
def hud_smoke_root(data_root: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    _isolate_usda(monkeypatch, data_root)
    ensure_prefs(get_paths())
    _seed_banana()
    import_exercise_seed(paths=get_paths())
    return data_root


def _agent_turn(utterance: str, *, sink=None):
    session = ChatSession(mode="agent")
    return run_turn(session, utterance, _ShouldNotRunAdapter(), sink=sink)


def _tools(result) -> list[str]:
    return [str(r.get("tool") or "") for r in result.tool_receipts]


def _assert_no_facts_append_ok(result) -> None:
    ok_facts = [
        r
        for r in result.tool_receipts
        if r.get("tool") == "memory_facts_append" and r.get("ok")
    ]
    assert ok_facts == []


def _meal_count() -> int:
    with open_life_db(paths=get_paths()) as conn:
        return int(conn.execute("SELECT COUNT(*) FROM meals").fetchone()[0])


def _running_count() -> int:
    with open_life_db(paths=get_paths()) as conn:
        return int(
            conn.execute(
                "SELECT COUNT(*) FROM time_blocks WHERE status = 'running'"
            ).fetchone()[0]
        )


def test_meal_search_strips_slot_words(hud_smoke_root: Path) -> None:
    built = build_meal_log_args(
        "one medium banana for breakfast",
        meal_slot="breakfast",
        fetch_remote=False,
    )
    assert built["searches"]
    assert built["searches"][0]["query"] == "banana"
    assert built["ok"] is True
    assert built["lines"][0]["display_name"] == "Banana"


def test_hud_smoke_meal_prefix_breakfast(hud_smoke_root: Path) -> None:
    result = _agent_turn("log meal: one medium banana for breakfast")
    assert result.stop_reason == "pack_fast_path"
    tools = _tools(result)
    assert "life_food_search" in tools
    assert "life_meal_log" in tools
    assert "life_nutrition_day" in tools
    _assert_no_facts_append_ok(result)

    search = next(r for r in result.tool_receipts if r.get("tool") == "life_food_search")
    query = str((search.get("args") or {}).get("query") or "")
    assert query == "banana"
    assert "breakfast" not in query.split()

    with open_life_db(paths=get_paths()) as conn:
        meal = conn.execute(
            "SELECT meal_id, meal_slot FROM meals ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        snap_row = conn.execute(
            "SELECT snapshot_json FROM meal_foods WHERE meal_id = ?",
            (meal["meal_id"],),
        ).fetchone()
        rollup = conn.execute(
            "SELECT totals_json, honest_partial FROM nutrition_day_rollup"
        ).fetchone()
    assert meal["meal_slot"] == "breakfast"
    snap = json.loads(snap_row["snapshot_json"])
    nutrients = snap.get("nutrients") or {}
    assert nutrients.get("energy_kcal") is not None
    assert nutrients.get("protein_g") is not None
    # Custom Banana cache = macros only; CORE slots stay null — do not invent Ca/Fe/D.
    assert nutrients.get("calcium_mg") is None
    assert nutrients.get("iron_mg") is None
    assert nutrients.get("vitamin_d_ug") is None

    day = next(r for r in result.tool_receipts if r.get("tool") == "life_nutrition_day")
    day_data = day.get("data") or {}
    assert day_data.get("honest_partial") is True
    totals = day_data.get("totals") or {}
    assert json.loads(rollup["totals_json"]) == totals
    assert bool(rollup["honest_partial"]) is True
    for key in ("calcium_mg", "iron_mg", "vitamin_d_ug"):
        assert totals.get(key) in (None,)

    payload = build_today(paths=get_paths())
    headline = payload.get("nutrition_headline")
    assert headline is not None
    assert headline.get("kcal") == totals.get("energy_kcal")
    assert headline.get("partial") is True

    via_tool = Gateway(mode="observe").execute("life_nutrition_day", {})
    assert via_tool.ok
    assert via_tool.data.get("totals") == totals
    assert via_tool.data.get("honest_partial") is True


def test_hud_smoke_meal_nl_add_banana(hud_smoke_root: Path) -> None:
    result = _agent_turn("add one banana to breakfast")
    assert result.stop_reason == "pack_fast_path"
    assert "life_meal_log" in _tools(result)
    _assert_no_facts_append_ok(result)
    with open_life_db(paths=get_paths()) as conn:
        row = conn.execute(
            "SELECT meal_slot FROM meals ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
    assert row["meal_slot"] == "breakfast"


def test_hud_smoke_time_wake_sleep_stop(hud_smoke_root: Path) -> None:
    wake = _agent_turn("I woke up")
    assert wake.stop_reason == "pack_fast_path"
    assert "life_time_start" in _tools(wake)
    _assert_no_facts_append_ok(wake)
    with open_life_db(paths=get_paths()) as conn:
        row = conn.execute(
            "SELECT kind, status FROM time_blocks WHERE status = 'running'"
        ).fetchone()
    assert row["kind"] == "wake"
    assert _running_count() == 1
    today = build_today(paths=get_paths())
    assert today.get("running_timer") is not None
    assert today["running_timer"]["kind"] == "wake"

    sleep = _agent_turn("going to sleep")
    assert sleep.stop_reason == "pack_fast_path"
    _assert_no_facts_append_ok(sleep)
    with open_life_db(paths=get_paths()) as conn:
        row = conn.execute(
            "SELECT kind FROM time_blocks WHERE status = 'running'"
        ).fetchone()
    assert row["kind"] == "sleep"
    assert _running_count() == 1

    sleep_dot = _agent_turn("going to sleep.")
    assert sleep_dot.stop_reason == "pack_fast_path"
    _assert_no_facts_append_ok(sleep_dot)
    assert _running_count() == 1

    stop = _agent_turn("stop focus")
    assert stop.stop_reason == "pack_fast_path"
    assert "life_time_stop" in _tools(stop)
    _assert_no_facts_append_ok(stop)
    assert _running_count() == 0
    today_after = build_today(paths=get_paths())
    assert today_after.get("running_timer") is None


def test_hud_smoke_lift_bench(hud_smoke_root: Path) -> None:
    result = _agent_turn("log lift: flat bench 50kg x6")
    assert result.stop_reason == "pack_fast_path"
    assert result.text == "Logged lift — receipt on file."
    assert "life_lift_log" in _tools(result)
    _assert_no_facts_append_ok(result)
    with open_life_db(paths=get_paths()) as conn:
        row = conn.execute(
            "SELECT load_kg, reps FROM gym_sets ORDER BY logged_at DESC LIMIT 1"
        ).fetchone()
    assert row["load_kg"] == 50.0
    assert row["reps"] == 6


def test_hud_smoke_lift_pullups_bodyweight(hud_smoke_root: Path) -> None:
    result = _agent_turn("log lift: pull-ups x8")
    assert result.stop_reason == "pack_fast_path"
    assert result.text == "Logged lift — receipt on file."
    assert "life_lift_log" in _tools(result)
    with open_life_db(paths=get_paths()) as conn:
        row = conn.execute(
            """
            SELECT gs.load_kg, gs.reps, ec.canonical_name
            FROM gym_sets gs
            JOIN exercise_catalog ec ON ec.exercise_id = gs.exercise_id
            ORDER BY gs.logged_at DESC LIMIT 1
            """
        ).fetchone()
    assert row["load_kg"] is None
    assert row["reps"] == 8
    assert row["canonical_name"] == "Pull-up"


def test_hud_fast_path_emits_token_delta(hud_smoke_root: Path) -> None:
    sink = _CapturingSink()
    result = _agent_turn("what did i eat", sink=sink)
    assert result.stop_reason == "pack_fast_path"
    assert result.text
    deltas = [p for ev, p in sink.events if ev == "token_delta"]
    assert deltas
    assert deltas[-1]["text"] == result.text
    assert result.steps == 0


def test_hud_smoke_capture_oat_milk(hud_smoke_root: Path) -> None:
    result = _agent_turn("capture: buy oat milk")
    assert result.stop_reason == "pack_fast_path"
    assert "life_capture" in _tools(result)
    cap = next(r for r in result.tool_receipts if r.get("tool") == "life_capture")
    assert cap.get("ok") is True
    _assert_no_facts_append_ok(result)


def test_hud_smoke_unknown_food_no_meal_row(hud_smoke_root: Path) -> None:
    assert _meal_count() == 0
    result = _agent_turn("log meal: flurmble glorp for breakfast")
    assert result.stop_reason == "missing_life_receipt"
    tools = _tools(result)
    assert "life_food_search" in tools
    assert "life_meal_log" not in tools
    _assert_no_facts_append_ok(result)
    assert _meal_count() == 0


def test_hud_smoke_observe_meal_no_write(hud_smoke_root: Path) -> None:
    session = ChatSession(mode="observe")
    result = run_turn(session, "log meal: one banana", _QuietAdapter())
    assert result.stop_reason != "pack_fast_path"
    assert "life_meal_log" not in _tools(result)
    _assert_no_facts_append_ok(result)
    assert _meal_count() == 0


def test_hud_smoke_memory_facts_blocked_on_life_pack(
    hud_smoke_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    session = ChatSession(mode="agent")
    session.pack_hint = {
        "tool": "life_meal_log",
        "args": {"utterance": "one banana"},
    }
    assert _model_tool_blocked(session, "memory_facts_append") is not None
    assert _model_tool_blocked(session, "life_meal_log") is None

    # Skip fast-path so the model step runs (loop deny still applies).
    monkeypatch.setattr(
        "ada.harness.loop._maybe_pack_fast_path",
        lambda *args, **kwargs: (None, None),
    )
    result = run_turn(
        ChatSession(mode="agent"),
        "log meal: one banana",
        _FactsAppendAdapter(),
    )
    facts = [r for r in result.tool_receipts if r.get("tool") == "memory_facts_append"]
    assert facts
    assert all(not r.get("ok") for r in facts)
    assert all(r.get("outcome") == "denied" for r in facts)
    assert _meal_count() == 0


def test_hud_edge_smoke_table_ids_cover_operator_list() -> None:
    ids = {row["id"] for row in HUD_EDGE_SMOKE}
    assert ids == {
        "meal_prefix",
        "meal_nl",
        "wake",
        "sleep",
        "sleep_period",
        "stop",
        "lift",
        "lift_bw",
        "capture",
        "unknown_food",
        "due_prefix",
        "due_nl",
        "due_list",
        "eat_q",
        "macros",
        "good_morning",
        "due_done_miss",
    }


def test_hud_smoke_due_prefix_and_nl(hud_smoke_root: Path) -> None:
    prefix = _agent_turn("add due: finish thesis by Friday")
    assert prefix.stop_reason == "pack_fast_path"
    tools = _tools(prefix)
    assert "memory_open_loops_upsert" in tools
    assert "memory_open_loops_list" in tools
    _assert_no_facts_append_ok(prefix)
    loops = list_loops(kind="todo", status="open", paths=get_paths())
    assert any("thesis" in str(item.get("text") or "").lower() for item in loops)
    assert any(item.get("due_at") for item in loops)

    nl = _agent_turn("gotta finish lab report by Thursday")
    assert nl.stop_reason == "pack_fast_path"
    assert "memory_open_loops_upsert" in _tools(nl)
    _assert_no_facts_append_ok(nl)
    loops_after = list_loops(kind="todo", status="open", paths=get_paths())
    assert any("lab report" in str(item.get("text") or "").lower() for item in loops_after)


def test_hud_smoke_read_questions_observe_and_agent(hud_smoke_root: Path) -> None:
    for utterance, tool in (
        ("what's due", "memory_open_loops_list"),
        ("what did i eat", "life_nutrition_day"),
        ("macros", "life_nutrition_day"),
    ):
        agent = _agent_turn(utterance)
        assert agent.stop_reason == "pack_fast_path", utterance
        assert tool in _tools(agent), utterance
        _assert_no_facts_append_ok(agent)

        session = ChatSession(mode="observe")
        observed = run_turn(session, utterance, _ShouldNotRunAdapter())
        assert observed.stop_reason == "pack_fast_path", utterance
        assert tool in _tools(observed), utterance
        _assert_no_facts_append_ok(observed)


def test_hud_smoke_good_morning_wake(hud_smoke_root: Path) -> None:
    result = _agent_turn("good morning")
    assert result.stop_reason == "pack_fast_path"
    assert "life_time_start" in _tools(result)
    _assert_no_facts_append_ok(result)
    with open_life_db(paths=get_paths()) as conn:
        row = conn.execute(
            "SELECT kind FROM time_blocks WHERE status = 'running'"
        ).fetchone()
    assert row["kind"] == "wake"


def test_hud_smoke_due_done_zero_matches(hud_smoke_root: Path) -> None:
    result = _agent_turn("done: flurmble glorp")
    assert result.stop_reason == "missing_life_receipt"
    assert "memory_open_loops_upsert" not in _tools(result)
    _assert_no_facts_append_ok(result)


def test_hud_smoke_life_status_concat(hud_smoke_root: Path) -> None:
    result = _agent_turn("how's my day")
    assert result.stop_reason == "pack_fast_path"
    tools = _tools(result)
    assert "life_nutrition_day" in tools
    assert "life_time_status" in tools
    assert "memory_open_loops_list" in tools
    _assert_no_facts_append_ok(result)

    session = ChatSession(mode="observe")
    observed = run_turn(session, "today summary", _ShouldNotRunAdapter())
    assert observed.stop_reason == "pack_fast_path"
    assert "life_nutrition_day" in _tools(observed)
    _assert_no_facts_append_ok(observed)


def test_hud_smoke_observe_due_add_no_write(hud_smoke_root: Path) -> None:
    session = ChatSession(mode="observe")
    result = run_turn(session, "add due: buy milk", _QuietAdapter())
    assert result.stop_reason != "pack_fast_path"
    assert "memory_open_loops_upsert" not in _tools(result)
    _assert_no_facts_append_ok(result)
    assert list_loops(kind="todo", status="open", paths=get_paths()) == []
