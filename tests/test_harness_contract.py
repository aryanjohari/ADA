"""Harness smoke: tool declarations and workflow strict subset."""

from __future__ import annotations

from ada.tools.registry import build_agent_tools, build_shell_declarations, frozen_tool_declaration_names
from ada.workflow.steps import ENRICH_STRICT_TOOL_NAMES


def test_empty_allowlist_no_shell_declaration() -> None:
    decls = build_shell_declarations(allowed_exact_commands=frozenset())
    assert decls == []


def test_workflow_strict_subset_of_full_tools() -> None:
    full = build_agent_tools(
        allowed_exact_commands=frozenset(["echo ok"]),
        include_memory_tools=True,
        include_knowledge_tools=True,
        include_workflow_tools=True,
        include_web_search=True,
        include_web_fetch=True,
    )
    names = frozen_tool_declaration_names(full)
    assert ENRICH_STRICT_TOOL_NAMES.issubset(names)


def test_mission_defaults_not_in_prompt_fixture() -> None:
    from ada.prompt import build_system_instruction

    instr = build_system_instruction(
        soul_text="",
        master_text="ops programme",
        state_db_display_path="/data/jarvis/state.db",
        allowlist_summary="- `echo ok`",
    )
    assert "defaults_json" not in instr
