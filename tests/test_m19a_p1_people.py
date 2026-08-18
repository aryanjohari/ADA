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
    ensure_prefs()
    gw = Gateway(mode="agent")
    obs = gw.execute(
        "life_person_capture",
        {"utterance": "met Ravi at dinner, kid starts school"},
    )
    assert obs.ok
    path = get_paths().people / "person_ravi.yaml"
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
    assert (get_paths().people / "person_ravi.yaml").is_file()


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
    assert parsed.get("ok")
    assert parsed["args"]["display_name"] == "Ravi"
