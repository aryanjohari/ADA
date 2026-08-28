"""M24 Slice 2 — gym multi-set / ladder parse + fail-closed ask."""

from __future__ import annotations

from pathlib import Path

from ada.harness.gym_spine import build_lift_log_args
from ada.harness.loop import run_turn
from ada.harness.pack_router import route_utterance
from ada.harness.session import ChatSession
from ada.io.paths import get_paths
from ada.logs.connection import open_life_db
from ada.logs.gym_import import import_exercise_seed


class _ShouldNotRunAdapter:
    model = "fake"

    def generate(self, *, system, contents, tools=None):
        raise AssertionError("pack fast-path should finish before model generate")


def test_ladder_space_separated() -> None:
    built = build_lift_log_args(
        "lat pulldown 30kg x 12 reps 35kg x12 reps 40kg x 8 reps"
    )
    assert built["ok"] is True
    assert len(built["sets"]) == 3
    assert built["sets"][0]["exercise_name"].lower().startswith("lat")
    assert built["sets"][0]["load_kg"] == 30.0
    assert built["sets"][0]["reps"] == 12
    assert built["sets"][1]["load_kg"] == 35.0
    assert built["sets"][1]["reps"] == 12
    assert built["sets"][2]["load_kg"] == 40.0
    assert built["sets"][2]["reps"] == 8


def test_ladder_slash() -> None:
    built = build_lift_log_args("lat pulldown 30×12/35×12/40×8")
    assert built["ok"] is True
    assert len(built["sets"]) == 3
    assert [s["load_kg"] for s in built["sets"]] == [30.0, 35.0, 40.0]
    assert [s["reps"] for s in built["sets"]] == [12, 12, 8]


def test_incomplete_parse_fail_closed() -> None:
    built = build_lift_log_args("lat pulldown somehow heavy")
    assert built["ok"] is False
    assert built.get("sets") == []
    assert "ask" in built
    assert "30kg" in built["ask"] or "reps" in built["ask"].lower()


def test_route_lat_pulldown_ladder() -> None:
    r = route_utterance(
        "Log lat pulldown 30kg x 12 reps 35kg x12 reps 40kg x 8 reps"
    )
    assert r is not None
    assert r["tool"] == "life_lift_log"


def test_lift_fast_path_ladder_writes(data_root: Path) -> None:
    import_exercise_seed(paths=get_paths())
    session = ChatSession(mode="agent")
    result = run_turn(
        session,
        "log lift: lat pulldown 30kg x 12 reps 35kg x12 reps 40kg x 8 reps",
        _ShouldNotRunAdapter(),
    )
    assert result.stop_reason == "pack_fast_path"
    assert any(r.get("tool") == "life_lift_log" for r in result.tool_receipts)
    with open_life_db(paths=get_paths()) as conn:
        rows = conn.execute(
            "SELECT load_kg, reps FROM gym_sets ORDER BY logged_at ASC"
        ).fetchall()
    assert len(rows) >= 3
    loads = [float(r["load_kg"]) for r in rows[-3:]]
    reps = [int(r["reps"]) for r in rows[-3:]]
    assert loads == [30.0, 35.0, 40.0]
    assert reps == [12, 12, 8]


def test_lift_incomplete_speaks_ask(data_root: Path) -> None:
    """Incomplete parse → human ask, never silent no-tool (F-M24-3)."""
    session = ChatSession(mode="agent")
    result = run_turn(
        session,
        "log lift: lat pulldown somehow heavy",
        _ShouldNotRunAdapter(),
    )
    assert result.stop_reason == "missing_life_receipt"
    assert result.text
    assert "30kg" in result.text or "reps" in result.text.lower()
    assert not any(r.get("tool") == "life_lift_log" for r in result.tool_receipts)
