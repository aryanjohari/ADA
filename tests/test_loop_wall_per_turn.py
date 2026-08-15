"""Wall budget is per run_turn, not ChatSession lifetime."""

from __future__ import annotations

import time

from ada.cortex.adapter import CortexTurn
from ada.harness.loop import run_turn
from ada.harness.session import ChatSession


class _TextCortex:
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


def test_wall_resets_each_turn(data_root, monkeypatch):
    monkeypatch.setenv("ADA_DATA_ROOT", str(data_root))
    session = ChatSession(mode="observe", max_steps=2, wall_seconds=1.0)
    contents: list = []
    cortex = _TextCortex()

    # Simulate session already past wall before turn 1 (HUD long-lived session).
    session.started_monotonic = time.monotonic() - 100.0
    assert session.wall_exceeded()

    r1 = run_turn(
        session,
        "first",
        cortex,
        system="test",
        contents=contents,
        end_session=False,
    )
    assert r1.stop_reason == "completed"
    assert r1.steps == 1
    assert r1.text == "ok"

    # Expire wall again between turns; turn 2 must still get a fresh budget.
    session.started_monotonic = time.monotonic() - 100.0
    assert session.wall_exceeded()

    r2 = run_turn(
        session,
        "second",
        cortex,
        system="test",
        contents=contents,
        end_session=False,
    )
    assert r2.stop_reason == "completed"
    assert r2.steps == 1
    assert r2.text == "ok"
    assert len(contents) == 2
