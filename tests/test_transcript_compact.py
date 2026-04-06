from __future__ import annotations

import json

from ada.dream.transcript_compact import compact_message_line


def test_compact_message_line_text():
    payload = {"parts": [{"type": "text", "text": "  hello world  "}]}
    line = compact_message_line(
        1, "user", json.dumps(payload), max_len=100
    )
    assert "user" in line
    assert "hello world" in line
