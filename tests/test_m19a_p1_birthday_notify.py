"""M19a P1.3 — birthday notify falsifiers F-P1.3a–c."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import yaml

from ada.harness.loop import run_turn
from ada.harness.session import ChatSession
from ada.io.atomic import atomic_write_text
from ada.io.paths import get_paths
from ada.memory.facts import ensure_prefs, _dump_yaml, save_prefs, load_prefs
from ada.memory import notify as notify_mod
from ada.memory import open_loops as loops_mod
from ada.tools.gateway import Gateway


class _ShouldNotRunAdapter:
    model = "fake"

    def generate(self, *, system, contents, tools=None):
        raise AssertionError("pack fast-path should finish before model generate")


def _write_person(person_id: str, doc: dict) -> None:
    path = get_paths().people / f"{person_id}.yaml"
    atomic_write_text(path, _dump_yaml(doc))


def test_f_p1_3a_birthday_open_loop_people_ids(data_root: Path) -> None:
    ensure_prefs()
    _write_person(
        "person_ravi",
        {
            "schema_version": 2,
            "id": "person_ravi",
            "display_name": "Ravi",
        },
    )
    session = ChatSession(mode="agent")
    session.gateway = Gateway(mode="agent")
    result = run_turn(
        session,
        "set birthday: Ravi 1990-05-20",
        _ShouldNotRunAdapter(),
    )
    assert result.stop_reason == "pack_fast_path"
    loops = loops_mod.list_loops(kind="todo", status="open")
    birthday = [t for t in loops if "Birthday" in (t.get("title") or "")]
    assert birthday
    assert birthday[0].get("people_ids") == ["person_ravi"]
    doc = yaml.safe_load((get_paths().people / "person_ravi.yaml").read_text())
    assert doc.get("birthday") == "1990-05-20"


def test_f_p1_3c_notify_honest_skip_when_disabled(data_root: Path) -> None:
    ensure_prefs()
    prefs = load_prefs()
    prefs["notify_enabled"] = False
    save_prefs(prefs)
    result = notify_mod.notify_send(message="test ping", paths=get_paths())
    assert result.get("outcome") in {"skipped", "ok"}
    assert result.get("skipped") or result.get("reason") == "notify_disabled"


def test_f_p1_3b_notify_limit_one_per_check(data_root: Path) -> None:
    ensure_prefs()
    prefs = load_prefs()
    prefs["notify_enabled"] = True
    prefs["notify_budget_per_day"] = 5
    save_prefs(prefs)
    now = datetime.now(timezone.utc)
    for i in range(3):
        loops_mod.upsert_loop(
            kind="todo",
            status="open",
            title=f"due {i}",
            text=f"due {i}",
            remind_at=now.isoformat().replace("+00:00", "Z"),
            notify=True,
        )
    with patch("ada.memory.notify.notify_send") as mock_send:
        mock_send.return_value = {"ok": True, "outcome": "ok", "skipped": False}
        result = notify_mod.notify_check_and_send(limit=1)
    assert len(result.get("results") or []) <= 1


def test_people_remind_read(data_root: Path) -> None:
    ensure_prefs()
    _write_person(
        "person_ravi",
        {
            "schema_version": 2,
            "id": "person_ravi",
            "display_name": "Ravi",
            "birthday": "1990-05-20",
        },
    )
    obs = Gateway(mode="observe").execute("life_people_remind", {"horizon_days": 400})
    assert obs.ok
    assert isinstance(obs.data.get("upcoming"), list)
