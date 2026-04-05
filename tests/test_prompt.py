from __future__ import annotations

from ada.prompt import build_system_instruction


def test_system_instruction_wraps_soul():
    s = build_system_instruction(
        soul_text="Be brief.",
        state_db_display_path="/tmp/state.db",
    )
    assert "<user_soul>" in s
    assert "Be brief." in s
    assert "ADA" in s
    assert "SQLite" in s


def test_harness_without_soul():
    s = build_system_instruction(
        soul_text="",
        state_db_display_path="/data/state.db",
    )
    assert "<user_soul>" not in s
    assert "ADA" in s
