"""Operator UI action_log append helper."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from ada.observability.audit_log import (
    OPERATOR_UI_ACTION_LOG_KIND,
    append_operator_action_log,
)


def _mk_db(path: Path) -> None:
    conn = sqlite3.connect(str(path))
    conn.execute(
        """
        CREATE TABLE action_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            kind TEXT NOT NULL,
            payload_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()
    conn.close()


def test_append_operator_action_log_roundtrip(tmp_path: Path) -> None:
    db = tmp_path / "state.db"
    _mk_db(db)
    rid = append_operator_action_log(
        db,
        {"action": "test", "client_action_id": "x", "GEMINI_API_KEY": "should_strip"},
    )
    assert rid is not None
    conn = sqlite3.connect(str(db))
    cur = conn.execute(
        "SELECT kind, payload_json FROM action_log WHERE id = ?", (rid,)
    )
    row = cur.fetchone()
    conn.close()
    assert row is not None
    assert row[0] == OPERATOR_UI_ACTION_LOG_KIND
    payload = json.loads(row[1])
    assert payload["action"] == "test"
    assert "GEMINI_API_KEY" not in payload
