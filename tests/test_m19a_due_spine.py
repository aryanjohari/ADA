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
    assert parsed["reason"] == "missing_life_receipt"


def test_due_spine_does_not_set_people_ids_or_next_wake(data_root: Path) -> None:
    ensure_prefs(get_paths())
    add = build_due_upsert_args("add due: finish thesis by Friday", verb="due_add")
    assert add["ok"] is True
    assert "people_ids" not in add["args"]
    assert "next_wake_at" not in add["args"]
    remind = build_due_upsert_args("remind me to stretch at 7pm", verb="remind")
    assert remind["ok"] is True
    assert "people_ids" not in remind["args"]
    assert "next_wake_at" not in remind["args"]
    assert remind["args"].get("remind_at")
    done = build_due_upsert_args("done: nobody", verb="due_done")
    assert done["ok"] is False
    assert "people_ids" not in (done.get("args") or {})


def test_due_done_code_binds_id_not_cortex_hint(data_root: Path) -> None:
    """Spine binds unique open-todo id; pack_hint id must not sole-pick."""
    from ada.harness.loop import _fast_path_due
    from ada.harness.session import ChatSession
    from ada.harness.stream_events import NullSink
    from ada.memory.open_loops import list_loops
    from ada.tools.gateway import Gateway

    ensure_prefs(get_paths())
    created = upsert_loop(text="finish thesis chapter", kind="todo", status="open")
    real_id = created["loop"]["id"]
    session = ChatSession(mode="agent")
    session.gateway = Gateway(mode="agent")
    session.pack_hint = {
        "verb": "due_done",
        "args": {"utterance": "done: thesis", "id": "loop_cortex_guess"},
    }
    receipts: list[dict] = []
    stop, _speech = _fast_path_due(session, NullSink(), [], receipts)
    assert stop == "pack_fast_path"
    upsert = next(r for r in receipts if r.get("tool") == "memory_open_loops_upsert")
    assert (upsert.get("args") or {}).get("id") == real_id
    assert (upsert.get("args") or {}).get("id") != "loop_cortex_guess"
    done = list_loops(kind="todo", status="done", paths=get_paths())
    assert any(item.get("id") == real_id for item in done)
