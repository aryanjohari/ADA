"""Entity (OPEN) ingress tool declaration contract."""

from __future__ import annotations

from ada.tools.registry import build_agent_tools, frozen_tool_declaration_names


def test_open_tool_declarations_exclude_run_skill() -> None:
    tool = build_agent_tools(
        allowed_exact_commands=frozenset(["echo ok"]),
        include_memory_tools=False,
        include_mission_control_snapshot=True,
        include_run_skill=False,
        include_propose_programme=True,
        knowledge_tool_subset=frozenset(
            {"search_knowledge", "get_entity_graph_context", "add_knowledge_source"}
        ),
    )
    names = frozen_tool_declaration_names(tool)
    assert "run_skill" not in names
    assert "propose_programme" in names
    assert "get_mission_control_snapshot" in names
    assert "search_knowledge" in names
    assert "record_entity" not in names


def test_work_tool_declarations_include_run_skill() -> None:
    tool = build_agent_tools(
        allowed_exact_commands=frozenset(),
        include_memory_tools=False,
        include_mission_control_snapshot=True,
        include_run_skill=True,
        include_propose_programme=False,
        include_knowledge_tools=True,
    )
    names = frozen_tool_declaration_names(tool)
    assert "run_skill" in names
    assert "propose_programme" not in names
