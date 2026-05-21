"""H3: capability profiles and chat surface tool declarations."""

from __future__ import annotations

from ada.chat_capability import profile_agent, profile_chat, profile_plan
from ada.chat_ingress import ChatSurfaceMode, resolve_chat_surface_mode
from ada.config import Settings
from ada.tools.registry import build_agent_tools, frozen_tool_declaration_names


def test_resolve_surface_modes() -> None:
    assert resolve_chat_surface_mode() == ChatSurfaceMode.CHAT
    assert resolve_chat_surface_mode(plan_mode=True) == ChatSurfaceMode.PLAN
    assert resolve_chat_surface_mode(agent_mode=True) == ChatSurfaceMode.AGENT
    assert resolve_chat_surface_mode(setup_mode=True) == ChatSurfaceMode.SETUP


def _tool_names(**kwargs: object) -> frozenset[str]:
    tool = build_agent_tools(
        allowed_exact_commands=frozenset(),
        include_memory_tools=False,
        include_mission_control_snapshot=True,
        **kwargs,
    )
    return frozen_tool_declaration_names(tool)


def test_chat_profile_tools() -> None:
    p = profile_chat(Settings.load())
    names = _tool_names(
        include_run_skill=p.include_run_skill,
        include_propose_programme=p.include_propose_programme,
        include_apply_programme=p.include_apply_programme,
        include_workflow_tools=p.include_workflow_status,
        knowledge_tool_subset=p.knowledge_tool_subset,
    )
    assert "propose_programme" in names
    assert "run_skill" not in names
    assert "apply_programme" not in names
    assert "enqueue_workflow" not in names


def test_plan_profile_tools() -> None:
    p = profile_plan(Settings.load())
    names = _tool_names(
        include_run_skill=p.include_run_skill,
        include_propose_programme=p.include_propose_programme,
        include_apply_programme=p.include_apply_programme,
        knowledge_tool_subset=p.knowledge_tool_subset,
    )
    assert "propose_programme" in names
    assert "apply_programme" in names
    assert "run_skill" not in names
    assert "enqueue_workflow" not in names


def test_agent_profile_tools() -> None:
    p = profile_agent(Settings.load())
    names = _tool_names(
        include_run_skill=p.include_run_skill,
        include_propose_programme=p.include_propose_programme,
        include_apply_programme=p.include_apply_programme,
        include_workflow_tools=p.include_workflow_status,
        include_knowledge_tools=True,
    )
    assert "run_skill" in names
    assert "propose_programme" not in names
    assert "apply_programme" not in names
    assert "enqueue_workflow" not in names
