"""Lifecycle append + narrative honesty."""

from __future__ import annotations

import json
from pathlib import Path

from ada.body.lifecycle import append_event, read_events
from ada.body.narrative import story, story_uses_only_ledger
from ada.io.atomic import recover_torn_jsonl
from ada.io.paths import get_paths


def test_lifecycle_skips_torn_line_via_read(data_root: Path) -> None:
    paths = get_paths()
    paths.memory.mkdir(parents=True)
    path = paths.lifecycle_jsonl
    good = {
        "schema_version": 1,
        "id": "x",
        "ts": "2026-08-12T00:00:00Z",
        "type": "birth",
        "summary": "born",
        "details": {},
        "receipts": {},
    }
    path.write_text(json.dumps(good) + "\n{not-json", encoding="utf-8")
    assert recover_torn_jsonl(path) is True
    events = read_events(paths)
    assert len(events) == 1
    assert events[0].type == "birth"


def test_narrative_uses_only_ledger(data_root: Path) -> None:
    paths = get_paths()
    append_event("birth", summary="ADA born on ada-pi5", paths=paths)
    append_event("wake", summary="ada body service start", paths=paths)
    events = read_events(paths)
    # Filter out any auto torn_line faults (none here)
    text = story(events)
    assert story_uses_only_ledger(text, events)
    assert "ADA born on ada-pi5" in text
    assert "childhood" not in text.lower()


def test_empty_story() -> None:
    assert story([]) == "No lifecycle events recorded yet."
    assert story_uses_only_ledger(story([]), [])
