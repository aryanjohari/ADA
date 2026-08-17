"""M19a P0.2 due_spine — parse then upsert; no guess on due_done."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from ada.harness.due_spine import build_due_upsert_args
from ada.io.paths import get_paths
from ada.memory.facts import ensure_prefs
from ada.memory.open_loops import upsert_loop


def _local(iso: str, paths=None) -> datetime:
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    prefs = ensure_prefs(paths or get_paths())
    tz = ZoneInfo(str(prefs.get("preferred_tz") or "Pacific/Auckland"))
    return dt.astimezone(tz)


def test_due_add_by_friday_sets_due_at(data_root: Path) -> None:
    ensure_prefs(get_paths())
    parsed = build_due_upsert_args("add due: finish thesis by Friday", verb="due_add")
    assert parsed["ok"] is True
    args = parsed["args"]
    assert args["kind"] == "todo"
    assert args["status"] == "open"
    assert "thesis" in args["text"].lower()
    assert args.get("due_at")
    assert _local(args["due_at"]).weekday() == 4


def test_gotta_finish_by_thursday(data_root: Path) -> None:
    ensure_prefs(get_paths())
    parsed = build_due_upsert_args(
        "gotta finish lab report by Thursday", verb="due_add"
    )
    assert parsed["ok"] is True
    assert "lab report" in parsed["args"]["text"].lower()
    assert _local(parsed["args"]["due_at"]).weekday() == 3


def test_remind_me_at_7pm(data_root: Path) -> None:
    ensure_prefs(get_paths())
    parsed = build_due_upsert_args("remind me to stretch at 7pm", verb="remind")
    assert parsed["ok"] is True
    args = parsed["args"]
    assert args["kind"] == "todo"
    assert "stretch" in args["text"].lower()
    assert args.get("remind_at")
    assert _local(args["remind_at"]).hour == 19


def test_due_done_zero_matches_is_miss(data_root: Path) -> None:
    ensure_prefs(get_paths())
    parsed = build_due_upsert_args("done: flurmble glorp", verb="due_done")
    assert parsed["ok"] is False
    assert parsed["match_count"] == 0


def test_due_done_one_match(data_root: Path) -> None:
    ensure_prefs(get_paths())
    created = upsert_loop(text="finish thesis chapter", kind="todo", status="open")
    parsed = build_due_upsert_args("done: thesis", verb="due_done")
    assert parsed["ok"] is True
    assert parsed["args"]["status"] == "done"
    assert parsed["args"]["id"] == created["loop"]["id"]


def test_due_done_ambiguous_is_miss(data_root: Path) -> None:
    ensure_prefs(get_paths())
    upsert_loop(text="finish thesis chapter", kind="todo", status="open")
    upsert_loop(text="thesis bibliography", kind="todo", status="open")
    parsed = build_due_upsert_args("done: thesis", verb="due_done")
    assert parsed["ok"] is False
    assert parsed["match_count"] == 2
