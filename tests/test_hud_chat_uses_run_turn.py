"""HUD chat drives harness.run_turn — receipts land in runs/ JSONL."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from ada.cortex.adapter import CortexTurn, ProposedToolCall
from ada.hud.app import create_app
from ada.harness import loop as loop_mod


class _ToolThenDone:
    model = "fake"
    n = 0

    def generate(self, *, system, contents, tools=None):
        self.n += 1
        if self.n == 1:
            return CortexTurn(
                text=None,
                tool_calls=[ProposedToolCall(name="body_doctor", args={})],
                usage={
                    "prompt_token_count": 1,
                    "candidates_token_count": 1,
                    "total_token_count": 2,
                },
            )
        return CortexTurn(
            text="body looks fine",
            tool_calls=[],
            usage={
                "prompt_token_count": 1,
                "candidates_token_count": 1,
                "total_token_count": 2,
            },
        )


class _CaptureSystem:
    model = "fake"
    last_system = None

    def generate(self, *, system, contents, tools=None):
        self.last_system = system
        return CortexTurn(
            text="ok",
            tool_calls=[],
            usage={
                "prompt_token_count": 1,
                "candidates_token_count": 1,
                "total_token_count": 2,
            },
        )


def test_chat_uses_run_turn(data_root, monkeypatch):
    monkeypatch.setenv("ADA_DATA_ROOT", str(data_root))
    monkeypatch.setenv("ADA_HUD_COOKIE_SECURE", "0")
    calls = {"n": 0}
    real_run_turn = loop_mod.run_turn

    def wrapped(*args, **kwargs):
        calls["n"] += 1
        return real_run_turn(*args, **kwargs)

    monkeypatch.setattr(loop_mod, "run_turn", wrapped)
    # ChatService imports run_turn at module level — patch there too.
    monkeypatch.setattr("ada.hud.chat_service.run_turn", wrapped)

    app = create_app()
    app.state.chat.adapter_factory = lambda: _ToolThenDone()
    client = TestClient(app)

    resp = client.post("/api/chat", json={"message": "how is the body?", "mode": "observe"})
    assert resp.status_code == 200
    assert calls["n"] == 1

    # Find JSONL under sandbox runs/
    runs = data_root / "runs"
    files = list(runs.rglob("*.jsonl"))
    assert files, "expected a run receipt file"
    text = files[0].read_text(encoding="utf-8")
    types = [json.loads(line)["type"] for line in text.splitlines() if line.strip()]
    assert "user" in types
    assert "tool_call" in types
    assert "tool_result" in types


def test_chat_prefix_binds_pack_hint_into_system(data_root, monkeypatch):
    monkeypatch.setenv("ADA_DATA_ROOT", str(data_root))
    monkeypatch.setenv("ADA_HUD_COOKIE_SECURE", "0")
    adapter = _CaptureSystem()
    app = create_app()
    app.state.chat.adapter_factory = lambda: adapter
    client = TestClient(app)

    resp = client.post("/api/chat", json={"message": "log meal: one banana", "mode": "observe"})
    assert resp.status_code == 200
    assert adapter.last_system is not None
    assert "Pack hint (this turn only):" in adapter.last_system
    assert "life_meal_log" in adapter.last_system
