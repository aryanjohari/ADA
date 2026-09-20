"""M26 people v1.0 — pack door: wrappers force the six people verbs."""

from __future__ import annotations

from pathlib import Path

import pytest

from ada.harness.loop import run_turn
from ada.harness.pack_router import (
    is_birthday_set_utterance,
    is_due_add_utterance,
    is_due_done_utterance,
    is_gym_start_utterance,
    is_habit_do_utterance,
    is_people_remind_utterance,
    is_person_capture_utterance,
    is_person_note_utterance,
    is_remind_utterance,
    is_time_start_utterance,
    is_who_is_utterance,
    route_utterance,
)
from ada.harness.session import ChatSession
from ada.io.paths import get_paths
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


@pytest.fixture
def people_root(data_root: Path) -> Path:
    ensure_prefs(paths=get_paths())
    return data_root


# --- Router ---


@pytest.mark.parametrize(
    "text,verb,tool",
    [
        ("met Ravi at dinner, kid starts school", "person_capture", "life_person_capture"),
        ("Met Ravi at dinner", "person_capture", "life_person_capture"),
        ("who is Mama", "who_is", "life_who_is"),
        ("note for Ravi: kid starts school", "person_note", "life_person_note"),
        ("alias set: Dad → person_dad_uncle", "alias_set", "life_alias_set"),
        ("set birthday: Ravi 1990-05-20", "birthday_set", "life_birthday_set"),
        ("people remind", "people_remind", "life_people_remind"),
        ("upcoming birthdays", "people_remind", "life_people_remind"),
    ],
)
def test_route_people_wrappers_hit_six_verbs(text: str, verb: str, tool: str) -> None:
    r = route_utterance(text)
    assert r is not None, text
    assert r["verb"] == verb, text
    assert r["tool"] == tool, text


def test_chip_met_and_who_prefill() -> None:
    from ada.harness.pack_router import resolve_chip

    met = resolve_chip("met")
    assert met is not None
    assert met["verb"] == "person_capture"
    assert met["prefill"] == "met "
    who = resolve_chip("who")
    assert who is not None
    assert who["verb"] == "who_is"
    assert who["prefill"] == "who is "


def test_bare_ravi_is_not_people_door() -> None:
    text = "Ravi"
    assert not is_person_capture_utterance(text)
    assert not is_who_is_utterance(text)
    assert not is_person_note_utterance(text)
    assert not is_people_remind_utterance(text)
    r = route_utterance(text)
    if r is not None:
        assert r["verb"] not in {
            "person_capture",
            "who_is",
            "person_note",
            "alias_set",
            "birthday_set",
            "people_remind",
        }


def test_habit_done_skincare_is_not_people() -> None:
    text = "habit done skincare"
    assert is_habit_do_utterance(text)
    assert not is_person_capture_utterance(text)
    r = route_utterance(text)
    assert r is not None
    assert r["verb"] == "habit_do"
    assert r["tool"] == "life_habit_do"


def test_im_at_the_gym_is_not_people() -> None:
    text = "I'm at the gym"
    assert is_gym_start_utterance(text)
    assert not is_person_capture_utterance(text)
    r = route_utterance(text)
    assert r is not None
    assert r["verb"] == "gym_start"
    assert r["tool"] == "life_gym_start"


def test_im_starting_gym_commute_is_not_people() -> None:
    text = "I'm starting gym commute"
    assert is_time_start_utterance(text)
    assert not is_person_capture_utterance(text)
    r = route_utterance(text)
    assert r is not None
    assert r["verb"] == "time_start"
    assert r["tool"] == "life_time_start"


def test_add_due_and_done_colon_are_not_people() -> None:
    add = "add due: finish thesis by Friday"
    assert is_due_add_utterance(add)
    assert not is_person_capture_utterance(add)
    r_add = route_utterance(add)
    assert r_add is not None
    assert r_add["verb"] == "due_add"

    done = "done: thesis"
    assert is_due_done_utterance(done)
    assert not is_person_capture_utterance(done)
    r_done = route_utterance(done)
    assert r_done is not None
    assert r_done["verb"] == "due_done"


def test_remind_me_to_call_ravi_is_dues_not_people_remind() -> None:
    text = "remind me to call Ravi Friday"
    assert is_remind_utterance(text)
    assert not is_people_remind_utterance(text)
    assert not is_person_capture_utterance(text)
    r = route_utterance(text)
    assert r is not None
    assert r["verb"] == "remind"
    assert r["tool"] == "memory_open_loops_upsert"


# --- Loop / HUD ---


@pytest.mark.parametrize(
    "text,tool",
    [
        ("met Ravi at dinner, kid starts school", "life_person_capture"),
        ("Met Ravi at dinner", "life_person_capture"),
        ("who is Mama", "life_who_is"),
        ("people remind", "life_people_remind"),
        ("upcoming birthdays", "life_people_remind"),
    ],
)
def test_people_fast_path_no_generate(people_root: Path, text: str, tool: str) -> None:
    session = ChatSession(mode="agent")
    result = run_turn(session, text, _ShouldNotRunAdapter())
    assert result.stop_reason == "pack_fast_path", text
    tools = [r.get("tool") for r in result.tool_receipts]
    assert tool in tools, text
    assert "life_habit_do" not in tools, text
    assert "life_gym_start" not in tools, text
    assert "life_time_start" not in tools, text
    assert "life_meal_log" not in tools, text


def test_note_for_alias_birthday_finish_before_generate(people_root: Path) -> None:
    note = run_turn(
        ChatSession(mode="agent"),
        "note for Ravi: kid starts school",
        _ShouldNotRunAdapter(),
    )
    assert note.stop_reason in {"pack_fast_path", "missing_life_receipt"}
    birthday = run_turn(
        ChatSession(mode="agent"),
        "set birthday: Ravi 1990-05-20",
        _ShouldNotRunAdapter(),
    )
    assert birthday.stop_reason in {"pack_fast_path", "missing_life_receipt"}
    alias = run_turn(
        ChatSession(mode="agent"),
        "alias set: Dad → person_dad_uncle",
        _ShouldNotRunAdapter(),
    )
    assert alias.stop_reason in {"pack_fast_path", "missing_life_receipt"}


def test_who_is_fast_path_observe_and_agent(people_root: Path) -> None:
    agent = run_turn(ChatSession(mode="agent"), "who is Mama", _ShouldNotRunAdapter())
    assert agent.stop_reason == "pack_fast_path"
    assert any(r.get("tool") == "life_who_is" for r in agent.tool_receipts)
    observed = run_turn(
        ChatSession(mode="observe"), "who is Mama", _ShouldNotRunAdapter()
    )
    assert observed.stop_reason == "pack_fast_path"
    assert any(r.get("tool") == "life_who_is" for r in observed.tool_receipts)


def test_people_remind_fast_path_observe_and_agent(people_root: Path) -> None:
    agent = run_turn(ChatSession(mode="agent"), "people remind", _ShouldNotRunAdapter())
    assert agent.stop_reason == "pack_fast_path"
    observed = run_turn(
        ChatSession(mode="observe"), "upcoming birthdays", _ShouldNotRunAdapter()
    )
    assert observed.stop_reason == "pack_fast_path"
    assert any(
        r.get("tool") == "life_people_remind" for r in observed.tool_receipts
    )


def test_met_forces_without_pack_hint(
    people_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "ada.harness.pack_router.route_utterance",
        lambda text, **kwargs: None,
    )
    session = ChatSession(mode="agent")
    result = run_turn(
        session, "met Ravi at dinner, kid starts school", _ShouldNotRunAdapter()
    )
    assert result.stop_reason == "pack_fast_path"
    assert any(r.get("tool") == "life_person_capture" for r in result.tool_receipts)


def test_observe_met_does_not_write(people_root: Path) -> None:
    session = ChatSession(mode="observe")
    result = run_turn(session, "met Ravi at dinner", _QuietAdapter())
    assert result.stop_reason != "pack_fast_path"
    assert not any(
        r.get("tool") == "life_person_capture" for r in result.tool_receipts
    )
    assert not list(get_paths().people.glob("person_*.yaml"))
    spoken = (result.text or "").lower()
    assert "person saved" not in spoken


def test_habit_done_fast_path_stays_habit(people_root: Path) -> None:
    from ada.logs import habits as habits_mod

    habits_mod.seed_default_habits()
    result = run_turn(
        ChatSession(mode="agent"), "habit done skincare", _ShouldNotRunAdapter()
    )
    assert result.stop_reason == "pack_fast_path"
    assert any(r.get("tool") == "life_habit_do" for r in result.tool_receipts)
    assert not any(
        r.get("tool") == "life_person_capture" for r in result.tool_receipts
    )


def test_im_at_the_gym_fast_path_stays_gym(people_root: Path) -> None:
    result = run_turn(
        ChatSession(mode="agent"), "I'm at the gym", _ShouldNotRunAdapter()
    )
    assert result.stop_reason == "pack_fast_path"
    assert any(r.get("tool") == "life_gym_start" for r in result.tool_receipts)
    assert not any(
        r.get("tool") == "life_person_capture" for r in result.tool_receipts
    )


def test_im_starting_gym_commute_fast_path_stays_time(people_root: Path) -> None:
    result = run_turn(
        ChatSession(mode="agent"),
        "I'm starting gym commute",
        _ShouldNotRunAdapter(),
    )
    assert result.stop_reason == "pack_fast_path"
    assert any(r.get("tool") == "life_time_start" for r in result.tool_receipts)
    assert not any(
        r.get("tool") == "life_person_capture" for r in result.tool_receipts
    )


def test_remind_me_fast_path_stays_dues(people_root: Path) -> None:
    result = run_turn(
        ChatSession(mode="agent"),
        "remind me to call Ravi Friday",
        _ShouldNotRunAdapter(),
    )
    assert result.stop_reason == "pack_fast_path"
    assert any(
        r.get("tool") == "memory_open_loops_upsert" for r in result.tool_receipts
    )
    assert not any(
        r.get("tool") == "life_people_remind" for r in result.tool_receipts
    )
    assert not any(
        r.get("tool") == "life_person_capture" for r in result.tool_receipts
    )


def test_is_birthday_wrapper_not_due() -> None:
    text = "set birthday: Ravi 1990-05-20"
    assert is_birthday_set_utterance(text)
    assert not is_due_add_utterance(text)
    r = route_utterance(text)
    assert r is not None
    assert r["verb"] == "birthday_set"


# --- Mouth ⊆ receipt ---


_SAVED_LIE = ("person saved", "note saved", "birthday saved", "i know your")


def test_unique_capture_mouth_saved_after_ok(people_root: Path) -> None:
    from ada.io.atomic import atomic_write_text
    from ada.memory.facts import _dump_yaml

    atomic_write_text(
        get_paths().people / "person_ravi.yaml",
        _dump_yaml(
            {"schema_version": 2, "id": "person_ravi", "display_name": "Ravi"}
        ),
    )
    result = run_turn(
        ChatSession(mode="agent"),
        "met Ravi at dinner, kid starts school",
        _ShouldNotRunAdapter(),
    )
    cap = next(r for r in result.tool_receipts if r.get("tool") == "life_person_capture")
    assert cap.get("ok") is True
    spoken = (result.text or "").strip()
    assert spoken.lower() == "person saved."
    from ada.harness.mouth import should_skip_register_pass

    assert should_skip_register_pass(spoken, result.tool_receipts) is True


def test_confirm_create_mouth_does_not_say_saved(people_root: Path) -> None:
    result = run_turn(
        ChatSession(mode="agent"),
        "met Ravi at dinner, kid starts school",
        _ShouldNotRunAdapter(),
    )
    assert result.stop_reason == "pack_fast_path"
    spoken = (result.text or "").lower()
    for token in _SAVED_LIE:
        assert token not in spoken, result.text
    assert "confirm" in spoken


def test_unknown_note_mouth_does_not_say_saved(people_root: Path) -> None:
    result = run_turn(
        ChatSession(mode="agent"),
        "note for flurmble: hello",
        _ShouldNotRunAdapter(),
    )
    assert result.stop_reason == "missing_life_receipt"
    spoken = (result.text or "").lower()
    for token in _SAVED_LIE:
        assert token not in spoken, result.text


def test_who_is_mouth_matched_from_receipt(people_root: Path) -> None:
    from ada.io.atomic import atomic_write_text
    from ada.memory.facts import _dump_yaml

    atomic_write_text(
        get_paths().people / "person_mama_priya.yaml",
        _dump_yaml(
            {
                "schema_version": 2,
                "id": "person_mama_priya",
                "display_name": "Priya Auntie",
                "aliases": [{"surface": "Mama", "sense": "mother_sibling", "confidence": 1.0}],
            }
        ),
    )
    result = run_turn(
        ChatSession(mode="observe"), "who is Mama", _ShouldNotRunAdapter()
    )
    who = next(r for r in result.tool_receipts if r.get("tool") == "life_who_is")
    assert who.get("ok") is True
    spoken = (result.text or "").strip()
    assert spoken.startswith("Matched ")
    assert "uncle" not in spoken.lower()
    from ada.harness.mouth import should_skip_register_pass

    assert should_skip_register_pass(spoken, result.tool_receipts) is True


def test_people_canned_ack_skips_gemini_narrate() -> None:
    from ada.harness.mouth import should_skip_register_pass

    fake_ok = [{"ok": True, "tool": "life_person_capture", "data": {"person_id": "person_ravi"}}]
    assert should_skip_register_pass("Person saved.", fake_ok) is True
    assert should_skip_register_pass("Note saved.", fake_ok) is True
    assert should_skip_register_pass("Birthday saved.", fake_ok) is True
    assert should_skip_register_pass("Matched Priya Auntie.", fake_ok) is True
    assert should_skip_register_pass("Which person — tap Confirm on the card.", fake_ok) is True
    assert should_skip_register_pass("Confirm save person — tap Confirm on the card.", fake_ok) is True
