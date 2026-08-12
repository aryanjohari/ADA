"""Agent/Plan from HUD require session cookie; Observe does not."""

from __future__ import annotations

from fastapi.testclient import TestClient

from ada.cortex.adapter import CortexTurn
from ada.hud.app import create_app


class _QuietCortex:
    model = "fake"

    def generate(self, *, system, contents, tools=None):
        return CortexTurn(
            text="ok",
            tool_calls=[],
            usage={
                "prompt_token_count": 1,
                "candidates_token_count": 1,
                "total_token_count": 2,
            },
        )


def _client(data_root, monkeypatch):
    monkeypatch.setenv("ADA_DATA_ROOT", str(data_root))
    monkeypatch.setenv("ADA_HUD_SESSION_SECRET", "test-secret-please-change")
    monkeypatch.setenv("ADA_HUD_PASSWORD", "test-password")
    monkeypatch.setenv("ADA_HUD_COOKIE_SECURE", "0")
    app = create_app()
    app.state.chat.adapter_factory = lambda: _QuietCortex()
    return TestClient(app)


def test_agent_without_session_returns_401(data_root, monkeypatch):
    client = _client(data_root, monkeypatch)
    resp = client.post("/api/chat", json={"message": "hi", "mode": "agent"})
    assert resp.status_code == 401
    assert resp.json()["error"] == "session_required"


def test_plan_without_session_returns_401(data_root, monkeypatch):
    client = _client(data_root, monkeypatch)
    resp = client.post("/api/chat", json={"message": "hi", "mode": "plan"})
    assert resp.status_code == 401


def test_agent_after_login_allowed(data_root, monkeypatch):
    client = _client(data_root, monkeypatch)
    login = client.post("/api/login", json={"password": "test-password"})
    assert login.status_code == 200
    assert login.json()["auth"] == "session"
    mode = client.get("/api/mode")
    assert mode.json()["auth"] == "session"
    resp = client.post("/api/chat", json={"message": "hi", "mode": "agent"})
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")
    body = resp.text
    assert "turn_done" in body or "token_delta" in body


def test_observe_without_session_allowed(data_root, monkeypatch):
    client = _client(data_root, monkeypatch)
    resp = client.post("/api/chat", json={"message": "hi", "mode": "observe"})
    assert resp.status_code == 200
