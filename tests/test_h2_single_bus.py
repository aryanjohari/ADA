"""H2: single chat execution bus — pipelines via run_skill, not enqueue_workflow."""

from __future__ import annotations

from ada.tools.registry import build_agent_tools, frozen_tool_declaration_names


def test_work_chat_tools_single_bus() -> None:
    tool = build_agent_tools(
        allowed_exact_commands=frozenset(),
        include_memory_tools=False,
        include_workflow_tools=True,
        include_run_skill=True,
        include_knowledge_tools=True,
    )
    names = frozen_tool_declaration_names(tool)
    assert "run_skill" in names
    assert "get_workflow_status" in names
    assert "enqueue_workflow" not in names


def test_workflow_tools_off_excludes_status_and_enqueue() -> None:
    tool = build_agent_tools(
        allowed_exact_commands=frozenset(),
        include_memory_tools=False,
        include_workflow_tools=False,
        include_run_skill=True,
    )
    names = frozen_tool_declaration_names(tool)
    assert "get_workflow_status" not in names
    assert "enqueue_workflow" not in names
