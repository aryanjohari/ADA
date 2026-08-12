"""Append-only JSONL run transcripts (M02 §7.2).

Path: <ADA_DATA_ROOT>/runs/<utc-date>/<session_id>.jsonl
Crash-safe via ada.io.atomic.append_jsonl_line.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ada.io.atomic import append_jsonl_line
from ada.io.paths import DataPaths, get_paths

SCHEMA_VERSION = 1

EVENT_TYPES = frozenset(
    {
        "session_start",
        "user",
        "model",
        "tool_call",
        "tool_result",
        "tool_denied",
        "usage",
        "session_end",
        "fault",
    }
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_date_dir() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def new_receipt_id() -> str:
    """Sortable-ish unique id for receipts / events (uuid4 hex prefixed)."""
    return uuid.uuid4().hex


def session_jsonl_path(
    session_id: str,
    *,
    paths: DataPaths | None = None,
    jsonl_path: Path | None = None,
) -> Path:
    if jsonl_path is not None:
        return Path(jsonl_path)
    root = (paths or get_paths()).runs
    return root / utc_date_dir() / f"{session_id}.jsonl"


class RunWriter:
    """Append typed events for one chat session."""

    def __init__(
        self,
        session_id: str,
        *,
        paths: DataPaths | None = None,
        jsonl_path: Path | None = None,
    ) -> None:
        self.session_id = session_id
        self.path = session_jsonl_path(session_id, paths=paths, jsonl_path=jsonl_path)

    def append(self, event_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if event_type not in EVENT_TYPES:
            raise ValueError(f"unknown run event type: {event_type}")
        record = {
            "schema_version": SCHEMA_VERSION,
            "id": new_receipt_id(),
            "ts": utc_now_iso(),
            "type": event_type,
            "session_id": self.session_id,
            "payload": payload or {},
        }
        append_jsonl_line(self.path, record)
        return record
