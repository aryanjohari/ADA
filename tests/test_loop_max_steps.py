"""Loop stops at max_steps when cortex always tool-calls."""

from __future__ import annotations

from ada.cortex.adapter import CortexTurn, ProposedToolCall
from ada.harness.loop import run_turn
from ada.harness.session import ChatSession


def test_max_steps_stops(data_root, monkeypatch):
    monkeypatch.setenv("ADA_DATA_ROOT", str(data_root))
    session = ChatSession(mode="observe", max_steps=3, wall_seconds=60)

    class VaryingToolCortex:
        model = "fake"
        n = 0

        def generate(self, *, system, contents, tools=None):
            self.n += 1
            # Distinct args avoid duplicate-tool stop before max_steps.
            return CortexTurn(
                text=None,
                tool_calls=[
                    ProposedToolCall(name="body_story", args={"n": self.n})
                ],
                usage={
                    "prompt_token_count": 1,
                    "candidates_token_count": 1,
                    "total_token_count": 2,
                },
            )

    result = run_turn(session, "ping", VaryingToolCortex(), system="test charter")
    assert result.stop_reason == "max_steps"
    assert result.steps == 3
    text = session.run_path.read_text(encoding="utf-8")
    assert "session_end" in text
    assert "max_steps" in text
