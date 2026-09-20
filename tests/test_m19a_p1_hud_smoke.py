"""M19a P1.x — HUD smoke (habits + people + birthday)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from ada.cortex.charter import build_system_charter, merge_pack_hint_into_charter
from ada.harness.loop import run_turn
from ada.harness.pack_router import route_utterance
from ada.harness.session import ChatSession
from ada.hud.today import build_today
from ada.io.atomic import atomic_write_text
from ada.io.paths import get_paths
from ada.logs import habits as habits_mod
from ada.logs.connection import open_life_db
from ada.memory.facts import ensure_prefs, _dump_yaml
from ada.memory import open_loops as loops_mod
from ada.tools.gateway import Gateway

P1_HUD_SMOKE: list[dict[str, str]] = [
    {
        "id": "habit_done",
        "utterance": "habit done: skincare",
        "mode": "agent",
        "expect": "pack_fast_path",
    },
    {
        "id": "habits_today",
        "utterance": "habits today",
        "mode": "observe",
        "expect": "pack_fast_path",
    },
    {
        "id": "who_is",
        "utterance": "who is Mama",
        "mode": "observe",
        "expect": "pack_fast_path",
    },
    {
        "id": "person_capture",
        "utterance": "met Ravi at dinner, kid starts school",
        "mode": "agent",
        "expect": "pack_fast_path",
    },
    {
        "id": "birthday_set",
        "utterance": "set birthday: Ravi 1990-05-20",
        "mode": "agent",
        "expect": "pack_fast_path",
    },
    {
        "id": "remind_person",
        "utterance": "remind me to call Ravi Friday",
        "mode": "agent",
        "expect": "pack_fast_path",
    },
    {
        "id": "unknown_habit",
        "utterance": "habit done: flurmble glorp",
        "mode": "agent",
        "expect": "pack_fast_path",
    },
    {
        "id": "habit_miss",
        "utterance": "habit miss: skincare",
        "mode": "agent",
        "expect": "pack_fast_path",
    },
    {
        "id": "unknown_habit_miss",
        "utterance": "habit miss: flurmble glorp",
        "mode": "agent",
        "expect": "missing_life_receipt",
    },
    {
        "id": "routine_run",
        "utterance": "routine run: evening",
        "mode": "agent",
        "expect": "pack_fast_path",
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


def _write_person(person_id: str, doc: dict) -> None:
    path = get_paths().people / f"{person_id}.yaml"
    atomic_write_text(path, _dump_yaml(doc))


@pytest.fixture
def p1_hud_root(data_root: Path) -> Path:
    ensure_prefs()
    habits_mod.seed_default_habits()
    _write_person(
        "person_mama_priya",
        {
            "schema_version": 2,
            "id": "person_mama_priya",
            "display_name": "Priya Auntie",
            "aliases": [{"surface": "Mama", "sense": "mother_sibling", "confidence": 1.0}],
        },
    )
    return data_root


def _turn(utterance: str, *, mode: str = "agent", sink=None):
    session = ChatSession(mode=mode)  # type: ignore[arg-type]
    session.gateway = Gateway(mode=mode)  # type: ignore[arg-type]
    return run_turn(session, utterance, _ShouldNotRunAdapter(), sink=sink)


@pytest.mark.parametrize("case", P1_HUD_SMOKE, ids=[c["id"] for c in P1_HUD_SMOKE])
def test_p1_hud_smoke_table(p1_hud_root: Path, case: dict[str, str]) -> None:
    if case["id"] == "birthday_set":
        _write_person(
            "person_ravi",
            {"schema_version": 2, "id": "person_ravi", "display_name": "Ravi"},
        )
    if case["id"] in {"remind_person", "birthday_set"} and case["id"] != "birthday_set":
        _write_person(
            "person_ravi",
            {"schema_version": 2, "id": "person_ravi", "display_name": "Ravi"},
        )
    if case["id"] == "remind_person":
        _write_person(
            "person_ravi",
            {"schema_version": 2, "id": "person_ravi", "display_name": "Ravi"},
        )
    sink = _CapturingSink() if case["expect"] == "pack_fast_path" else None
    result = _turn(case["utterance"], mode=case["mode"], sink=sink)
    assert result.stop_reason == case["expect"]
    if case["id"] == "habit_done":
        tools = [r.get("tool") for r in result.tool_receipts]
        assert "life_habit_do" in tools
        assert "life_habit_status" in tools
        with open_life_db() as conn:
            assert conn.execute("SELECT 1 FROM habit_events").fetchone()
        if sink:
            deltas = [p for ev, p in sink.events if ev == "token_delta"]
            assert deltas
    if case["id"] == "person_capture":
        assert not (get_paths().people / "person_ravi.yaml").is_file()
        assert any(r.get("tool") == "life_person_capture" for r in result.tool_receipts)
        spoken = (result.text or "").lower()
        assert "confirm" in spoken
        assert "person saved" not in spoken
    if case["id"] == "who_is":
        assert any(r.get("tool") == "life_who_is" for r in result.tool_receipts)
        assert "Matched" in (result.text or "")
    if case["id"] == "birthday_set":
        loops = loops_mod.list_loops(kind="todo", status="open")
        assert any("Birthday" in (t.get("title") or "") for t in loops)
        today = build_today()
        assert today.get("birthday_soon") is not None
    if case["id"] == "remind_person":
        upserts = [r for r in result.tool_receipts if r.get("tool") == "memory_open_loops_upsert"]
        assert upserts
        args = upserts[0].get("args") or {}
        if args.get("people_ids"):
            assert "person_ravi" in args["people_ids"]
    if case["id"] == "unknown_habit":
        assert any(
            str(r.get("tool") or "") == "life_habit_create" for r in result.tool_receipts
        )
        with open_life_db() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM habit_events WHERE habit_id LIKE '%flurmble%'"
            ).fetchone()[0]
        assert count == 0
        assert habits_mod.resolve_habit("flurmble glorp").get("ok") is not True
    if case["id"] == "habit_miss":
        assert any(str(r.get("tool") or "") == "life_habit_miss" for r in result.tool_receipts)
        with open_life_db() as conn:
            row = conn.execute(
                "SELECT kind FROM habit_events WHERE habit_id = ?",
                ("habit_skincare",),
            ).fetchone()
        assert row is not None
        assert row["kind"] == "miss"
    if case["id"] == "unknown_habit_miss":
        assert not any(
            str(r.get("tool") or "") == "life_habit_create" for r in result.tool_receipts
        )
        with open_life_db() as conn:
            count = conn.execute("SELECT COUNT(*) FROM habit_events").fetchone()[0]
        assert count == 0


def test_f_p1_xa_pack_hint_reaches_charter(p1_hud_root: Path) -> None:
    hint = route_utterance("habit done: skincare")
    assert hint is not None
    charter = build_system_charter(mode="agent", pack_hint=hint)
    assert "Pack hint (this turn only):" in charter
    assert "habit_do" in charter
    merged = merge_pack_hint_into_charter("base prompt", hint)
    assert "life_habit_do" in merged


def test_f_p1_xb_no_habits_dashboard_route() -> None:
    from ada.hud import routes_api

    paths = [getattr(r, "path", "") for r in routes_api.router.routes]
    assert not any("/habits" in str(p) for p in paths)
    assert not any("/people" in str(p) for p in paths)


def test_alias_clash_hud_smoke(p1_hud_root: Path) -> None:
    _write_person(
        "person_dad_uncle",
        {
            "schema_version": 2,
            "id": "person_dad_uncle",
            "display_name": "Uncle Raj",
            "aliases": [{"surface": "Dad", "sense": "uncle_paternal", "confidence": 1.0}],
        },
    )
    _write_person(
        "person_dad_father",
        {
            "schema_version": 2,
            "id": "person_dad_father",
            "display_name": "Father Singh",
            "aliases": [{"surface": "Dad", "sense": "father", "confidence": 1.0}],
        },
    )
    result = _turn("alias set: Dad → person_dad_uncle")
    assert result.stop_reason == "pack_fast_path"
    assert "Confirm" in (result.text or "")


def test_hud_unknown_met_confirm_create_no_yaml(p1_hud_root: Path) -> None:
    result = _turn("met Ravi at dinner, kid starts school")
    assert result.stop_reason == "pack_fast_path"
    assert not (get_paths().people / "person_ravi.yaml").is_file()
    probe = next(
        r for r in result.tool_receipts if r.get("tool") == "life_person_capture"
    )
    assert probe.get("needs_confirm") or (probe.get("data") or {}).get("needs_confirm")


def test_hud_unique_known_met_confirm_none(p1_hud_root: Path) -> None:
    _write_person(
        "person_ravi",
        {"schema_version": 2, "id": "person_ravi", "display_name": "Ravi"},
    )
    result = _turn("met Ravi at dinner, kid starts school")
    assert result.stop_reason == "pack_fast_path"
    spoken = (result.text or "").lower()
    assert "person saved" in spoken
    assert "tap confirm" not in spoken
    doc = yaml.safe_load((get_paths().people / "person_ravi.yaml").read_text())
    notes = [i.get("note") for i in (doc.get("interactions") or [])]
    assert any(notes)


def test_hud_clash_met_dad_picker_no_silent_bind(p1_hud_root: Path) -> None:
    _write_person(
        "person_dad_uncle",
        {
            "schema_version": 2,
            "id": "person_dad_uncle",
            "display_name": "Uncle Raj",
            "aliases": [{"surface": "Dad", "sense": "uncle_paternal", "confidence": 1.0}],
        },
    )
    _write_person(
        "person_dad_father",
        {
            "schema_version": 2,
            "id": "person_dad_father",
            "display_name": "Father Singh",
            "aliases": [{"surface": "Dad", "sense": "father", "confidence": 1.0}],
        },
    )
    result = _turn("met Dad at dinner")
    assert result.stop_reason == "pack_fast_path"
    assert "Confirm" in (result.text or "")
    assert "Person saved" not in (result.text or "")
    uncle = yaml.safe_load((get_paths().people / "person_dad_uncle.yaml").read_text())
    father = yaml.safe_load((get_paths().people / "person_dad_father.yaml").read_text())
    assert not (uncle.get("interactions") or [])
    assert not (father.get("interactions") or [])


def test_hud_who_is_mama_observe_and_agent(p1_hud_root: Path) -> None:
    obs = _turn("who is Mama", mode="observe")
    assert obs.stop_reason == "pack_fast_path"
    assert any(r.get("tool") == "life_who_is" for r in obs.tool_receipts)
    assert "Matched" in (obs.text or "")
    agent = _turn("who is Mama", mode="agent")
    assert agent.stop_reason == "pack_fast_path"
    assert any(r.get("tool") == "life_who_is" for r in agent.tool_receipts)


def test_hud_note_for_known_and_unknown_miss(p1_hud_root: Path) -> None:
    _write_person(
        "person_ravi",
        {"schema_version": 2, "id": "person_ravi", "display_name": "Ravi"},
    )
    known = _turn("note for Ravi: kid starts school")
    assert known.stop_reason == "pack_fast_path"
    assert "Note saved" in (known.text or "")
    miss = _turn("note for flurmble: hello")
    assert miss.stop_reason == "missing_life_receipt"
    assert "Note saved" not in (miss.text or "")
    assert not list(get_paths().people.glob("person_flurmble*.yaml"))


def test_hud_birthday_unique_people_ids_due(p1_hud_root: Path) -> None:
    _write_person(
        "person_ravi",
        {"schema_version": 2, "id": "person_ravi", "display_name": "Ravi"},
    )
    result = _turn("set birthday: Ravi 1990-05-20")
    assert result.stop_reason == "pack_fast_path"
    loops = loops_mod.list_loops(kind="todo", status="open")
    birthday = [t for t in loops if "Birthday" in (t.get("title") or "")]
    assert birthday
    assert "person_ravi" in (birthday[0].get("people_ids") or [])
    today = build_today()
    assert today.get("birthday_soon") is not None


def test_hud_observe_met_no_write(p1_hud_root: Path) -> None:
    from ada.cortex.adapter import CortexTurn

    class _Quiet:
        model = "fake"

        def generate(self, *, system, contents, tools=None):
            return CortexTurn(text="ok", tool_calls=[])

    session = ChatSession(mode="observe")
    session.gateway = Gateway(mode="observe")
    result = run_turn(session, "met Ravi at dinner", _Quiet())
    assert result.stop_reason != "pack_fast_path"
    assert not any(r.get("tool") == "life_person_capture" for r in result.tool_receipts)
    assert not (get_paths().people / "person_ravi.yaml").is_file()


def test_second_habit_done_same_day_already_done(p1_hud_root: Path) -> None:
    first = _turn("habit done: skincare")
    assert first.stop_reason == "pack_fast_path"
    second = _turn("habit done: skincare")
    assert second.stop_reason == "pack_fast_path"
    done = next(
        r for r in second.tool_receipts if str(r.get("tool") or "") == "life_habit_do"
    )
    data = done.get("data") or {}
    assert data.get("reason") == "already_done"
    spoken = (second.text or "").lower()
    assert "logged" not in spoken
    with open_life_db() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM habit_events WHERE habit_id = ? AND kind = 'done'",
            ("habit_skincare",),
        ).fetchone()[0]
    assert count == 1


def test_habits_today_hud_no_shame(p1_hud_root: Path) -> None:
    result = _turn("habits today", mode="observe")
    assert result.stop_reason == "pack_fast_path"
    text = (result.text or "").lower()
    assert "streak broken" not in text
    assert "guilt" not in text
