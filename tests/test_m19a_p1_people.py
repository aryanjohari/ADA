"""M19a P1.2 — people falsifiers F-P1.2a–d."""

from __future__ import annotations

from pathlib import Path

import yaml

from ada.dream.merge import apply_manage_result
from ada.harness.loop import run_turn
from ada.harness.people_spine import build_capture_args, resolve_mention_for_due
from ada.harness.session import ChatSession
from ada.io.paths import get_paths
from ada.io.atomic import atomic_write_text
from ada.memory.facts import ensure_prefs, _dump_yaml
from ada.memory import people as people_mod
from ada.tools.gateway import Gateway


class _ShouldNotRunAdapter:
    model = "fake"

    def generate(self, *, system, contents, tools=None):
        raise AssertionError("pack fast-path should finish before model generate")


def _write_person(person_id: str, doc: dict) -> None:
    p = get_paths()
    path = p.people / f"{person_id}.yaml"
    atomic_write_text(path, _dump_yaml(doc))


def test_f_p1_2b_person_capture_yaml_row(data_root: Path) -> None:
    """Unknown met X → Confirm-create; no YAML until Confirm Yes."""
    from ada.hud.chat_service import ChatService

    ensure_prefs()
    gw = Gateway(mode="agent")
    obs = gw.execute(
        "life_person_capture",
        {"utterance": "met Ravi at dinner, kid starts school"},
    )
    assert obs.ok is False
    assert obs.needs_confirm
    path = get_paths().people / "person_ravi.yaml"
    assert not path.is_file()

    session = ChatSession(mode="agent")
    session.gateway = Gateway(mode="agent")
    result = run_turn(
        session,
        "met Ravi at dinner, kid starts school",
        _ShouldNotRunAdapter(),
    )
    assert result.stop_reason == "pack_fast_path"
    assert "Confirm save person" in (result.text or "")
    assert "Person saved" not in (result.text or "")
    assert not path.is_file()

    probe = next(
        r for r in result.tool_receipts if r.get("tool") == "life_person_capture"
    )
    assert probe.get("needs_confirm") or (probe.get("data") or {}).get("needs_confirm")
    svc = ChatService()
    svc._ensure_session("agent")
    stash = dict(probe.get("args") or {})
    data = probe.get("data") if isinstance(probe.get("data"), dict) else {}
    for key in ("display_name", "proposed_display_name", "note", "utterance"):
        if data.get(key) is not None and key not in stash:
            stash[key] = data[key]
    svc.pending_confirms[probe.get("receipt_id")] = {
        "tool": "life_person_capture",
        "args": stash,
    }
    out = svc.confirm_tool(
        "life_person_capture",
        {},
        pending_id=probe.get("receipt_id"),
    )
    assert out.get("ok")
    assert path.is_file()
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert doc.get("display_name") == "Ravi"
    assert doc.get("interactions")


def test_f_p1_2c_who_is_many_no_silent_pick(data_root: Path) -> None:
    ensure_prefs()
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
    obs = Gateway(mode="observe").execute("life_who_is", {"mention": "Dad"})
    assert obs.ok
    assert obs.data.get("match_count", 0) >= 2
    assert obs.data.get("person_id") is None


def test_f_p1_2a_alias_clash_confirm(data_root: Path) -> None:
    ensure_prefs()
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
    session = ChatSession(mode="agent")
    session.gateway = Gateway(mode="agent")
    result = run_turn(
        session,
        "alias set: Dad → person_dad_uncle",
        _ShouldNotRunAdapter(),
    )
    assert result.stop_reason == "pack_fast_path"
    assert "Confirm" in (result.text or "")
    path = get_paths().people / "person_dad_uncle.yaml"
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    aliases = [a.get("surface") for a in doc.get("aliases") or [] if isinstance(a, dict)]
    assert aliases.count("Dad") == 1


def test_who_is_fast_path_observe(data_root: Path) -> None:
    ensure_prefs()
    _write_person(
        "person_mama_priya",
        {
            "schema_version": 2,
            "id": "person_mama_priya",
            "display_name": "Priya Auntie",
            "kin": {"indian_terms": ["Mama"]},
            "aliases": [{"surface": "Mama", "sense": "mother_sibling", "confidence": 1.0}],
        },
    )
    session = ChatSession(mode="observe")
    session.gateway = Gateway(mode="observe")
    result = run_turn(session, "who is Mama", _ShouldNotRunAdapter())
    assert result.stop_reason == "pack_fast_path"
    assert "Matched" in (result.text or "")


def test_person_capture_fast_path(data_root: Path) -> None:
    ensure_prefs()
    session = ChatSession(mode="agent")
    session.gateway = Gateway(mode="agent")
    result = run_turn(
        session,
        "met Ravi at dinner, kid starts school",
        _ShouldNotRunAdapter(),
    )
    assert result.stop_reason == "pack_fast_path"
    assert any(r.get("tool") == "life_person_capture" for r in result.tool_receipts)
    assert not (get_paths().people / "person_ravi.yaml").is_file()
    spoken = (result.text or "").lower()
    assert "person saved" not in spoken
    assert "confirm" in spoken


def test_due_spine_people_ids_when_resolved(data_root: Path) -> None:
    ensure_prefs()
    _write_person(
        "person_ravi",
        {
            "schema_version": 2,
            "id": "person_ravi",
            "display_name": "Ravi",
        },
    )
    hit = resolve_mention_for_due("call Ravi Friday")
    assert hit.get("ok")
    assert hit.get("person_id") == "person_ravi"


def test_f_p1_2d_dream_people_always_stage(data_root: Path) -> None:
    ensure_prefs()
    result = apply_manage_result(
        {
            "fact_candidates": [
                {"key": "people.friend", "value": {"name": "Friend"}},
            ]
        }
    )
    reasons = {s.get("reason") for s in result.get("staged") or []}
    assert "people_always_stage" in reasons


def test_capture_args_parse(data_root: Path) -> None:
    parsed = build_capture_args("Ravi at dinner, kid starts school")
    assert parsed.get("needs_confirm") is True
    assert parsed.get("create") is True
    assert parsed["args"]["display_name"] == "Ravi"
    assert parsed.get("confirm_tool") == "life_person_capture"


def test_resolve_mention_unique_many_zero(data_root: Path) -> None:
    ensure_prefs()
    _write_person(
        "person_mama_priya",
        {
            "schema_version": 2,
            "id": "person_mama_priya",
            "display_name": "Priya Auntie",
            "aliases": [{"surface": "Mama", "sense": "mother_sibling", "confidence": 1.0}],
        },
    )
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
    unique = people_mod.resolve_mention("Mama")
    assert unique.get("ok") is True
    assert unique.get("person_id") == "person_mama_priya"
    many = people_mod.resolve_mention("Dad")
    assert many.get("ok") is not True
    assert many.get("person_id") is None
    assert many.get("match_count", 0) >= 2
    assert many.get("reason") == "ambiguous"
    zero = people_mod.resolve_mention("flurmble")
    assert zero.get("ok") is not True
    assert zero.get("person_id") is None
    assert zero.get("reason") == "not_found"
    assert (zero.get("match_count") or 0) == 0


def test_spine_parses_note_for_name_colon_text(data_root: Path) -> None:
    from ada.harness.people_spine import build_note_args, parse_note_utterance

    parsed = parse_note_utterance("note for Ravi: kid starts school")
    assert parsed.get("ok")
    assert parsed["mention"] == "Ravi"
    assert parsed["text"] == "kid starts school"
    ensure_prefs()
    _write_person(
        "person_ravi",
        {"schema_version": 2, "id": "person_ravi", "display_name": "Ravi"},
    )
    bound = build_note_args("note for Ravi: kid starts school")
    assert bound.get("ok")
    assert bound.get("person_id") == "person_ravi"
    assert bound["args"]["text"] == "kid starts school"


def test_unknown_note_and_birthday_do_not_mint(data_root: Path) -> None:
    from ada.harness.people_spine import build_birthday_args, build_note_args

    ensure_prefs()
    note = build_note_args("note for flurmble: hello")
    assert note.get("ok") is not True
    assert note.get("reason") == "missing_life_receipt"
    assert note.get("person_id") is None
    birthday = build_birthday_args("flurmble 1990-05-20")
    assert birthday.get("ok") is not True
    assert birthday.get("reason") == "missing_life_receipt"
    assert birthday.get("person_id") is None

    session = ChatSession(mode="agent")
    session.gateway = Gateway(mode="agent")
    miss_note = run_turn(
        session, "note for flurmble: hello", _ShouldNotRunAdapter()
    )
    assert miss_note.stop_reason == "missing_life_receipt"
    miss_bday = run_turn(
        ChatSession(mode="agent"),
        "set birthday: flurmble 1990-05-20",
        _ShouldNotRunAdapter(),
    )
    assert miss_bday.stop_reason == "missing_life_receipt"
    people_dir = get_paths().people
    minted = list(people_dir.glob("person_flurmble*.yaml")) if people_dir.is_dir() else []
    assert minted == []


def test_unique_known_capture_confirm_none(data_root: Path) -> None:
    ensure_prefs()
    _write_person(
        "person_ravi",
        {"schema_version": 2, "id": "person_ravi", "display_name": "Ravi"},
    )
    result = run_turn(
        ChatSession(mode="agent"),
        "met Ravi at dinner, kid starts school",
        _ShouldNotRunAdapter(),
    )
    assert result.stop_reason == "pack_fast_path"
    spoken = (result.text or "").lower()
    assert "person saved" in spoken
    assert "tap confirm" not in spoken
    doc = yaml.safe_load((get_paths().people / "person_ravi.yaml").read_text())
    notes = [i.get("note") for i in (doc.get("interactions") or [])]
    assert any("dinner" in str(n).lower() or "school" in str(n).lower() for n in notes)


def test_unique_note_confirm_none(data_root: Path) -> None:
    ensure_prefs()
    _write_person(
        "person_ravi",
        {"schema_version": 2, "id": "person_ravi", "display_name": "Ravi"},
    )
    result = run_turn(
        ChatSession(mode="agent"),
        "note for Ravi: kid starts school",
        _ShouldNotRunAdapter(),
    )
    assert result.stop_reason == "pack_fast_path"
    spoken = (result.text or "").lower()
    assert "note saved" in spoken
    assert "tap confirm" not in spoken
    doc = yaml.safe_load((get_paths().people / "person_ravi.yaml").read_text())
    notes = [i.get("note") for i in (doc.get("interactions") or [])]
    assert any("kid starts school" in str(n) for n in notes)


def test_capture_clash_confirm_picker_no_silent_bind(data_root: Path) -> None:
    from ada.hud.chat_service import ChatService

    ensure_prefs()
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
    result = run_turn(
        ChatSession(mode="agent"),
        "met Dad at dinner",
        _ShouldNotRunAdapter(),
    )
    assert result.stop_reason == "pack_fast_path"
    assert result.stop_reason != "missing_life_receipt"
    spoken = (result.text or "").lower()
    assert "person saved" not in spoken
    assert "confirm" in spoken
    probe = next(
        r for r in result.tool_receipts if r.get("tool") == "life_person_capture"
    )
    assert probe.get("needs_confirm") or (probe.get("data") or {}).get("needs_confirm")
    data = probe.get("data") if isinstance(probe.get("data"), dict) else {}
    cands = list(data.get("candidates") or (probe.get("args") or {}).get("candidates") or [])
    assert len(cands) >= 2
    uncle_notes = yaml.safe_load(
        (get_paths().people / "person_dad_uncle.yaml").read_text()
    ).get("interactions") or []
    father_notes = yaml.safe_load(
        (get_paths().people / "person_dad_father.yaml").read_text()
    ).get("interactions") or []
    assert uncle_notes == []
    assert father_notes == []

    svc = ChatService()
    svc._ensure_session("agent")
    stash = dict(probe.get("args") or {})
    for key in ("candidates", "resolve", "display_name", "note", "utterance"):
        if data.get(key) is not None and key not in stash:
            stash[key] = data[key]
    svc.pending_confirms[probe.get("receipt_id")] = {
        "tool": "life_person_capture",
        "args": stash,
    }
    out = svc.confirm_tool(
        "life_person_capture",
        {},
        pending_id=probe.get("receipt_id"),
        selected_ref_ids={"Dad": "person_dad_uncle"},
    )
    assert out.get("ok")
    assert (out.get("data") or {}).get("person_id") == "person_dad_uncle"
    uncle_notes = yaml.safe_load(
        (get_paths().people / "person_dad_uncle.yaml").read_text()
    ).get("interactions") or []
    father_notes = yaml.safe_load(
        (get_paths().people / "person_dad_father.yaml").read_text()
    ).get("interactions") or []
    assert uncle_notes
    assert father_notes == []


def test_people_yes_rejects_id_outside_pool(data_root: Path) -> None:
    from ada.hud.chat_service import ChatService

    ensure_prefs()
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
    probe = Gateway(mode="agent").execute(
        "life_person_capture",
        {"utterance": "met Dad at dinner", "confirmed": False},
    )
    assert probe.needs_confirm
    svc = ChatService()
    svc._ensure_session("agent")
    data = probe.data if isinstance(probe.data, dict) else {}
    stash = dict(probe.args or {})
    for key in ("candidates", "resolve", "display_name"):
        if data.get(key) is not None and key not in stash:
            stash[key] = data[key]
    svc.pending_confirms[probe.receipt_id] = {
        "tool": "life_person_capture",
        "args": stash,
    }
    try:
        svc.confirm_tool(
            "life_person_capture",
            {},
            pending_id=probe.receipt_id,
            selected_ref_ids={"Dad": "person_invented"},
        )
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_hud_people_confirm_picker_in_stream_js() -> None:
    from pathlib import Path

    js = Path(__file__).resolve().parents[1] / "src/ada/hud/static/js/stream.js"
    text = js.read_text(encoding="utf-8")
    assert "_buildPeopleConfirmPicker" in text
    assert "_buildPeopleCreateSummary" in text
    assert "_buildHabitConfirmPicker" in text
    assert "Save person" in text
    assert "JSON.stringify(args" in text
