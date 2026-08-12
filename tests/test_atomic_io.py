"""Crash-safe atomic replace / append / torn-line recovery."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from ada.io.atomic import append_jsonl_line, atomic_write_text, recover_torn_jsonl


def test_atomic_replace_survives_partial_tmp(data_root: Path) -> None:
    target = data_root / "memory" / "facts" / "identity.yaml"
    target.parent.mkdir(parents=True)
    atomic_write_text(target, "version: 1\n")
    assert target.read_text(encoding="utf-8") == "version: 1\n"

    # Simulate kill leaving a tmp beside the good file — reader must see old content.
    orphan = target.with_name(f"{target.name}.tmp.99999")
    orphan.write_text("CORRUPT", encoding="utf-8")
    assert target.read_text(encoding="utf-8") == "version: 1\n"

    atomic_write_text(target, "version: 2\n")
    assert target.read_text(encoding="utf-8") == "version: 2\n"
    assert not orphan.exists() or orphan.read_text(encoding="utf-8") == "CORRUPT"


def test_lifecycle_append_fsync_contract(data_root: Path) -> None:
    path = data_root / "memory" / "lifecycle.jsonl"
    with patch("ada.io.atomic.os.fsync") as fsync:
        append_jsonl_line(path, {"type": "wake", "n": 1})
        assert fsync.called
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["type"] == "wake"


def test_lifecycle_skips_torn_line(data_root: Path) -> None:
    path = data_root / "memory" / "lifecycle.jsonl"
    path.parent.mkdir(parents=True)
    good1 = {"schema_version": 1, "id": "a", "ts": "t1", "type": "birth", "summary": "born"}
    good2 = {"schema_version": 1, "id": "b", "ts": "t2", "type": "wake", "summary": "woke"}
    path.write_text(
        json.dumps(good1) + "\n" + json.dumps(good2) + "\n" + '{"type":"fault","sum',
        encoding="utf-8",
    )
    recovered = recover_torn_jsonl(path)
    assert recovered is True
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 2
    assert json.loads(lines[0])["id"] == "a"
    assert json.loads(lines[1])["id"] == "b"
