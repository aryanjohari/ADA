"""Runs JSONL schema roundtrip."""

import json

from ada.runs.append import EVENT_TYPES, RunWriter


def test_runs_jsonl_roundtrip(data_root):
    from ada.io.paths import get_paths

    paths = get_paths()
    writer = RunWriter("sess_test", paths=paths)
    writer.append("session_start", {"mode": "observe", "model": "gemini-2.5-flash"})
    writer.append("user", {"text": "hi"})
    writer.append(
        "tool_result",
        {
            "ok": True,
            "tool": "body_whoami",
            "receipt_id": "abc",
            "data": {"born_at": "2026-01-01T00:00:00Z"},
        },
    )
    writer.append(
        "usage",
        {
            "prompt_token_count": 10,
            "candidates_token_count": 5,
            "total_token_count": 15,
        },
    )
    writer.append("session_end", {"stop_reason": "completed"})

    lines = writer.path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 5
    for line in lines:
        obj = json.loads(line)
        assert obj["schema_version"] == 1
        assert obj["type"] in EVENT_TYPES
        assert obj["session_id"] == "sess_test"
        assert "id" in obj and "ts" in obj
