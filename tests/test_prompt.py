from __future__ import annotations

from ada.prompt import build_system_instruction, format_allowlist_summary


def test_system_instruction_wraps_soul():
    s = build_system_instruction(
        soul_text="Be brief.",
        master_text="",
        state_db_display_path="/tmp/state.db",
        allowlist_summary="(none)",
    )
    assert "<user_soul>" in s
    assert "Be brief." in s
    assert "ADA" in s
    assert "SQLite" in s


def test_harness_without_soul():
    s = build_system_instruction(
        soul_text="",
        master_text="",
        state_db_display_path="/data/state.db",
        allowlist_summary="- `uname -a`",
    )
    assert "<user_soul>" not in s
    assert "ADA" in s
    assert "uname" in s


def test_master_block_included():
    s = build_system_instruction(
        soul_text="",
        master_text="You are a toaster.",
        state_db_display_path="/data/state.db",
        allowlist_summary="(none)",
    )
    assert "<master>" in s
    assert "toaster" in s


def test_format_allowlist_summary_empty():
    assert "disabled" in format_allowlist_summary(frozenset()).lower()
