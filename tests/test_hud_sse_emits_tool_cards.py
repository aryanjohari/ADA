"""SSE stream emits gateway tool cards from CallbackSink."""

from __future__ import annotations

from fastapi.testclient import TestClient

from ada.cortex.adapter import CortexTurn, ProposedToolCall
from ada.hud.app import create_app


class _OneTool:
    model = "fake"
    n = 0

    def generate(self, *, system, contents, tools=None):
        self.n += 1
        if self.n == 1:
            return CortexTurn(
                text=None,
                tool_calls=[
                    ProposedToolCall(name="body_vitals", args={"section": "summary"})
                ],
                usage={
                    "prompt_token_count": 1,
                    "candidates_token_count": 1,
                    "total_token_count": 2,
                },
            )
        return CortexTurn(
            text="done",
            tool_calls=[],
            usage={
                "prompt_token_count": 1,
                "candidates_token_count": 1,
                "total_token_count": 2,
            },
        )


class _NutritionRead:
    model = "fake"
    n = 0

    def generate(self, *, system, contents, tools=None):
        self.n += 1
        if self.n == 1:
            return CortexTurn(
                text=None,
                tool_calls=[
                    ProposedToolCall(name="life_nutrition_day", args={})
                ],
                usage={
                    "prompt_token_count": 1,
                    "candidates_token_count": 1,
                    "total_token_count": 2,
                },
            )
        return CortexTurn(
            text="done",
            tool_calls=[],
            usage={
                "prompt_token_count": 1,
                "candidates_token_count": 1,
                "total_token_count": 2,
            },
        )


def test_sse_emits_tool_cards(data_root, monkeypatch):
    monkeypatch.setenv("ADA_DATA_ROOT", str(data_root))
    monkeypatch.setenv("ADA_HUD_COOKIE_SECURE", "0")
    app = create_app()
    app.state.chat.adapter_factory = lambda: _OneTool()
    client = TestClient(app)
    resp = client.post("/api/chat", json={"message": "vitals?", "mode": "observe"})
    assert resp.status_code == 200
    body = resp.text
    assert "event: tool_call_started" in body
    assert "body_vitals" in body
    assert "section" in body
    assert "event: tool_call_finished" in body
    assert "event: turn_done" in body


def test_sse_emits_view_open_for_nutrition_day(data_root, monkeypatch):
    monkeypatch.setenv("ADA_DATA_ROOT", str(data_root))
    monkeypatch.setenv("ADA_HUD_COOKIE_SECURE", "0")
    app = create_app()
    app.state.chat.adapter_factory = lambda: _NutritionRead()
    client = TestClient(app)
    resp = client.post("/api/chat", json={"message": "macros", "mode": "observe"})
    assert resp.status_code == 200
    body = resp.text
    assert "event: view_open" in body
    assert '"panel_kind":"nutrition_day"' in body
    assert '"tool":"life_nutrition_day"' in body
