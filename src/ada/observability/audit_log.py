"""Append operator UI audit rows to SQLite ``action_log`` (short transactions)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

OPERATOR_UI_ACTION_LOG_KIND = "operator_ui_bootstrap"

# Payload must never include these keys (defense in depth).
_FORBIDDEN_PAYLOAD_KEYS = frozenset(
    {
        "GEMINI_API_KEY",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "GSC_SERVICE_ACCOUNT_JSON",
        "ADA_JINA_API_KEY",
        "SERPER_API_KEY",
        "ADA_SERPER_API_KEY",
        "DATAFORSEO_PASSWORD",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
    }
)


def _strip_forbidden(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            k: _strip_forbidden(v)
            for k, v in obj.items()
            if k not in _FORBIDDEN_PAYLOAD_KEYS
        }
    if isinstance(obj, list):
        return [_strip_forbidden(x) for x in obj]
    return obj


def append_operator_action_log(
    state_db_path: Path,
    payload: dict[str, Any],
    *,
    timeout_sec: float = 5.0,
) -> int | None:
    """
    Insert one row with kind ``operator_ui_bootstrap``. Returns row id or None if DB missing.

    Uses WAL and a busy timeout; may still fail if the database is locked.
    """
    p = Path(state_db_path).expanduser().resolve()
    if not p.is_file():
        return None
    safe = _strip_forbidden(payload)
    body = json.dumps(safe, ensure_ascii=False)
    uri = f"file:{p.as_posix()}?mode=rwc"
    conn = sqlite3.connect(uri, uri=True, timeout=timeout_sec)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        cur = conn.execute(
            """
            INSERT INTO action_log (session_id, kind, payload_json)
            VALUES (?, ?, ?)
            """,
            (None, OPERATOR_UI_ACTION_LOG_KIND, body),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()
