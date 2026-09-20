"""M26 people — reflection = who_is + people_remind + Today. Not SQL, not people_day."""

from __future__ import annotations

from pathlib import Path

from ada.harness.loop import run_turn
from ada.harness.pack_router import route_utterance
from ada.harness.session import ChatSession
from ada.hud.today import build_today
from ada.io.atomic import atomic_write_text
from ada.io.paths import get_paths
from ada.memory.facts import _dump_yaml, ensure_prefs
from ada.tools.gateway import Gateway
from ada.tools.toolspec import SPECS_BY_NAME, WRITE_TOOL_NAMES


class _ShouldNotRunAdapter:
    model = "fake"

    def generate(self, *, system, contents, tools=None):
        raise AssertionError("pack fast-path should finish before model generate")


def _write_person(person_id: str, doc: dict) -> None:
    path = get_paths().people / f"{person_id}.yaml"
    atomic_write_text(path, _dump_yaml(doc))


def test_no_sql_people_day_or_conversation_tools() -> None:
    for name in (
        "life_people_day",
        "life_people_week",
        "life_person_create",
        "people_events",
        "conversation_log",
        "life_conversation_list",
    ):
        assert name not in SPECS_BY_NAME, name
    assert "life_who_is" in SPECS_BY_NAME
    assert "life_who_is" not in WRITE_TOOL_NAMES
    assert "life_people_remind" in SPECS_BY_NAME
    assert "life_people_remind" not in WRITE_TOOL_NAMES
    assert "life_person_capture" in WRITE_TOOL_NAMES


def test_who_is_is_not_a_date_pack() -> None:
    r = route_utterance("who is Mama")
    assert r is not None
    assert r["verb"] == "who_is"
    assert r["tool"] == "life_who_is"
    args = r.get("args") or {}
    assert "date" not in args
    assert "days" not in args
    remind = route_utterance("people remind")
    assert remind is not None
    assert remind["verb"] == "people_remind"
    assert remind["tool"] == "life_people_remind"
    r_args = remind.get("args") or {}
    assert "date" not in r_args
    assert "days" not in r_args


def test_who_is_observe_agent_not_new_sql(data_root: Path) -> None:
    ensure_prefs(get_paths())
    _write_person(
        "person_mama_priya",
        {
            "schema_version": 2,
            "id": "person_mama_priya",
            "display_name": "Priya Auntie",
            "aliases": [{"surface": "Mama", "sense": "mother_sibling", "confidence": 1.0}],
        },
    )
    obs = Gateway(mode="observe").execute("life_who_is", {"mention": "Mama"})
    assert obs.ok
    data = obs.data or {}
    assert data.get("person_id") == "person_mama_priya"
    denied = Gateway(mode="observe").execute(
        "life_person_capture",
        {"utterance": "met Ravi at dinner", "confirmed": True},
    )
    assert not denied.ok
    assert denied.outcome == "denied"

    listed = run_turn(
        ChatSession(mode="observe"), "who is Mama", _ShouldNotRunAdapter()
    )
    assert listed.stop_reason == "pack_fast_path"
    receipt = next(r for r in listed.tool_receipts if r.get("tool") == "life_who_is")
    assert receipt.get("ok") is True
    assert (listed.text or "").startswith("Matched ")


def test_today_birthday_soon_and_people_remind(data_root: Path) -> None:
    ensure_prefs(get_paths())
    _write_person(
        "person_ravi",
        {
            "schema_version": 2,
            "id": "person_ravi",
            "display_name": "Ravi",
            "birthday": "1990-09-25",
        },
    )
    payload = build_today(paths=get_paths())
    soon_ids = {t.get("person_id") for t in payload.get("birthday_soon") or []}
    remind_ids = {t.get("person_id") for t in payload.get("people_remind") or []}
    assert "person_ravi" in soon_ids
    assert "person_ravi" in remind_ids

    result = run_turn(
        ChatSession(mode="observe"), "people remind", _ShouldNotRunAdapter()
    )
    assert result.stop_reason == "pack_fast_path"
    receipt = next(
        r for r in result.tool_receipts if r.get("tool") == "life_people_remind"
    )
    data = receipt.get("data") or {}
    upcoming = data.get("upcoming") or data.get("birthday_soon") or []
    assert any(item.get("person_id") == "person_ravi" for item in upcoming)


def test_cli_who_thin_wrapper(data_root: Path) -> None:
    from typer.testing import CliRunner

    from ada.cli.main import app

    ensure_prefs(get_paths())
    _write_person(
        "person_mama_priya",
        {
            "schema_version": 2,
            "id": "person_mama_priya",
            "display_name": "Priya Auntie",
            "aliases": [{"surface": "Mama", "sense": "mother_sibling", "confidence": 1.0}],
        },
    )
    runner = CliRunner()
    result = runner.invoke(app, ["life", "who", "Mama", "--json"])
    assert result.exit_code == 0, result.output
    assert "Mama" in result.output or "Priya" in result.output
    assert "life_who_is" in result.output
