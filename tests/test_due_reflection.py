"""M26 dues — reflection = due_list + Today strip. Not SQL, not due_day."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from ada.harness.loop import run_turn
from ada.harness.pack_router import route_utterance
from ada.harness.session import ChatSession
from ada.hud.today import build_today
from ada.io.paths import get_paths
from ada.memory.facts import ensure_prefs
from ada.memory.open_loops import upsert_loop
from ada.tools.gateway import Gateway
from ada.tools.toolspec import SPECS_BY_NAME, WRITE_TOOL_NAMES


class _ShouldNotRunAdapter:
    model = "fake"

    def generate(self, *, system, contents, tools=None):
        raise AssertionError("pack fast-path should finish before model generate")


def test_no_sql_due_day_or_life_due_tools() -> None:
    for name in (
        "life_due_day",
        "life_due_week",
        "life_due_list",
        "life_due_add",
        "life_due_done",
        "due_events",
    ):
        assert name not in SPECS_BY_NAME, name
    assert "memory_open_loops_list" in SPECS_BY_NAME
    assert "memory_open_loops_list" not in WRITE_TOOL_NAMES
    assert "memory_open_loops_upsert" in WRITE_TOOL_NAMES


def test_pack_due_list_passes_kind_status() -> None:
    r = route_utterance("what's due")
    assert r is not None
    assert r["verb"] == "due_list"
    assert r["tool"] == "memory_open_loops_list"
    assert r["args"]["kind"] == "todo"
    assert r["args"]["status"] == "open"
    grocery = route_utterance("grocery list")
    assert grocery is not None
    assert grocery["verb"] == "due_list"
    assert grocery["args"]["kind"] == "todo"
    assert grocery["args"]["status"] == "open"


def test_due_list_observe_agent_not_new_sql(data_root: Path) -> None:
    ensure_prefs(get_paths())
    upsert_loop(text="finish thesis chapter", kind="todo", status="open")
    obs = Gateway(mode="observe").execute(
        "memory_open_loops_list", {"kind": "todo", "status": "open"}
    )
    assert obs.ok
    data = obs.data or {}
    loops = data.get("loops") or []
    assert any("thesis" in str(item.get("text") or "").lower() for item in loops)
    denied = Gateway(mode="observe").execute(
        "memory_open_loops_upsert",
        {"kind": "todo", "text": "should not write", "status": "open"},
    )
    assert not denied.ok
    assert denied.outcome == "denied"

    listed = run_turn(
        ChatSession(mode="observe"), "what's due", _ShouldNotRunAdapter()
    )
    assert listed.stop_reason == "pack_fast_path"
    receipt = next(
        r for r in listed.tool_receipts if r.get("tool") == "memory_open_loops_list"
    )
    n = int((receipt.get("data") or {}).get("count") or 0)
    assert (listed.text or "").strip() == f"{n} open due(s)."


def test_today_due_todos_and_remind_soon(data_root: Path) -> None:
    ensure_prefs(get_paths())
    now = datetime.now(timezone.utc)
    past = (now - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    soon = (now + timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    later = (now + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    due = upsert_loop(
        text="Pay rent", kind="todo", status="open", due_at=past
    )
    remind = upsert_loop(
        text="stretch", kind="todo", status="open", remind_at=soon
    )
    upsert_loop(text="later thing", kind="todo", status="open", due_at=later)
    payload = build_today(paths=get_paths(), now=now)
    due_ids = {t.get("id") for t in payload.get("due_todos") or []}
    remind_ids = {t.get("id") for t in payload.get("remind_soon") or []}
    assert due["loop"]["id"] in due_ids
    assert remind["loop"]["id"] in remind_ids
    assert due["loop"]["id"] not in remind_ids


def test_cli_due_list_thin_wrapper(data_root: Path) -> None:
    from typer.testing import CliRunner

    from ada.cli.main import app

    ensure_prefs(get_paths())
    upsert_loop(text="finish thesis chapter", kind="todo", status="open")
    runner = CliRunner()
    result = runner.invoke(app, ["life", "due-list", "--json"])
    assert result.exit_code == 0, result.output
    assert "thesis" in result.output.lower()
    assert "memory_open_loops_list" in result.output
