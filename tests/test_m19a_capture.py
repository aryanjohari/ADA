"""M19a Slice 4 — capture routing tests."""

from __future__ import annotations

from pathlib import Path

from ada.io.paths import get_paths
from ada.memory.facts import ensure_prefs, save_prefs
from ada.tools.gateway import Gateway


def test_capture_todo(data_root: Path) -> None:
    gw = Gateway(mode="agent")
    obs = gw.execute("life_capture", {"text": "buy milk", "kind": "todo"})
    assert obs.ok
    assert obs.data.get("kind") == "todo"
    assert obs.data.get("open_loop_id")


def test_capture_note_artifact(data_root: Path) -> None:
    gw = Gateway(mode="agent")
    obs = gw.execute("life_capture", {"text": "Meeting notes from call", "kind": "note"})
    assert obs.ok
    assert obs.data.get("path")


def test_capture_fact_overwrite_needs_confirm(data_root: Path) -> None:
    paths = get_paths()
    ensure_prefs(paths)
    save_prefs({**ensure_prefs(paths), "brief_time": "06:00"}, paths=paths)
    gw = Gateway(mode="agent")
    obs = gw.execute(
        "life_capture",
        {
            "text": "remember that brief is 07:00",
            "kind": "fact",
            "key": "prefs.brief_time",
            "value": "07:00",
        },
    )
    assert obs.needs_confirm or obs.data.get("needs_confirm")
