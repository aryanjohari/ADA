from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from ada.config import Settings
from ada.prompt import (
    build_system_instruction,
    format_allowlist_summary,
    format_file_tools_note,
)


def test_worker_mode_adds_daemon_note():
    base = build_system_instruction(
        soul_text="",
        master_text="",
        state_db_display_path="/data/state.db",
        allowlist_summary="(none)",
        worker_mode=False,
    )
    worker = build_system_instruction(
        soul_text="",
        master_text="",
        state_db_display_path="/data/state.db",
        allowlist_summary="(none)",
        worker_mode=True,
    )
    assert "ada daemon" not in base.lower()
    assert "ada daemon" in worker.lower()
    assert "read_task_plan" in worker
    assert "architecture-proposal" in worker.lower()


def test_schema_digest_note_in_harness():
    from ada.prompt import format_schema_digest_note

    note = format_schema_digest_note("# Hello\n\nSchema.")
    assert note is not None
    s = build_system_instruction(
        soul_text="",
        master_text="",
        state_db_display_path="/data/state.db",
        allowlist_summary="(none)",
        schema_digest_note=note,
    )
    assert "Hello" in s
    assert "schema digest" in s.lower()


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
    assert "append_master_section" in s


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


def test_file_tools_note_in_harness():
    base = Settings.load()
    note = format_file_tools_note(
        replace(
            base,
            file_sandbox_roots=(Path("/tmp/ada_sandbox").resolve(),),
            file_deny_prefixes=(),
        )
    )
    s = build_system_instruction(
        soul_text="",
        master_text="",
        state_db_display_path="/data/state.db",
        allowlist_summary="(none)",
        file_tools_note=note,
    )
    assert "read_workspace_file" in s
    assert "write_workspace_file" in s
    assert "list_workspace_directory" in s
    assert "ada_sandbox" in s or "/tmp" in s
