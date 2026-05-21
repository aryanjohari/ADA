"""Harness contract: mission note and no defaults_json in system prompt."""

from __future__ import annotations

from ada.prompt import (
    _ENTITY_MODE_NOTE,
    _PROGRAMME_MODE_NOTE,
    _WORK_MODE_MISSION_NOTE,
    build_system_instruction,
    format_concierge_routing_note,
)


def test_mission_bound_includes_work_mode_note() -> None:
    instr = build_system_instruction(
        soul_text="",
        master_text="",
        state_db_display_path="/tmp/state.db",
        allowlist_summary="(none)",
        mission_bound=True,
    )
    assert _WORK_MODE_MISSION_NOTE.split(".")[0] in instr
    assert "ProgrammeDigest" in instr
    assert "get_mission_control_snapshot" in instr


def test_setup_mode_omits_work_mode_mission_note() -> None:
    instr = build_system_instruction(
        soul_text="",
        master_text="",
        state_db_display_path="/tmp/state.db",
        allowlist_summary="(none)",
        setup_mode=True,
        mission_bound=True,
    )
    assert "Mission-bound chat" not in instr


def test_programme_mode_note() -> None:
    instr = build_system_instruction(
        soul_text="",
        master_text="",
        state_db_display_path="/tmp/state.db",
        allowlist_summary="(none)",
        programme_mode=True,
    )
    assert "propose_programme" in instr
    assert "Allowed templates:" in instr
    assert "brief_md" in instr
    assert "isr-publish" in instr or "ops" in instr


def test_concierge_routing_in_chat_and_plan_not_agent() -> None:
    chat = build_system_instruction(
        soul_text="",
        master_text="",
        state_db_display_path="/tmp/state.db",
        allowlist_summary="(none)",
        entity_mode=True,
    )
    plan = build_system_instruction(
        soul_text="",
        master_text="",
        state_db_display_path="/tmp/state.db",
        allowlist_summary="(none)",
        plan_mode=True,
    )
    agent = build_system_instruction(
        soul_text="",
        master_text="",
        state_db_display_path="/tmp/state.db",
        allowlist_summary="(none)",
        agent_mode=True,
    )
    routing = format_concierge_routing_note()
    assert routing in chat
    assert routing in plan
    assert "Concierge routing" not in agent


def test_entity_mode_note_in_system_instruction() -> None:
    instr = build_system_instruction(
        soul_text="",
        master_text="",
        state_db_display_path="/tmp/state.db",
        allowlist_summary="(none)",
        entity_mode=True,
    )
    assert "Jarvis" in instr or "concierge" in instr
    assert "ada chat --agent" in instr
    assert "run_skill" in instr
    assert "do not have `run_skill`" in instr
    assert _ENTITY_MODE_NOTE.split(".")[0] in instr
    assert "Never paste raw `defaults_json`" in instr


def test_entity_mode_no_run_skill_encouragement() -> None:
    instr = build_system_instruction(
        soul_text="",
        master_text="",
        state_db_display_path="/tmp/state.db",
        allowlist_summary="(none)",
        entity_mode=True,
    )
    assert "approved=true" not in instr


def test_no_defaults_json_in_system_instruction() -> None:
    instr = build_system_instruction(
        soul_text="persona",
        master_text="operator policy",
        state_db_display_path="/tmp/state.db",
        allowlist_summary="(none)",
    )
    assert "defaults_json" not in instr
    assert "schedule_hint_json" not in instr
