"""Hands catalog drift: live code vs docs/hands_catalog.json."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ada.config import _find_project_root
from ada.motor.manifest_sync import (
    INTERNAL_ONLY_CHAT_TOOLS,
    build_hands_catalog_dict,
    chat_tool_ids_from_code,
    collect_actions,
    collect_capabilities,
    collect_pipelines,
)
from ada.motor.registry import load_skill_registry
from ada.tools.registry import build_agent_tools, frozen_tool_declaration_names
from ada.workflow.templates import WORKFLOW_KINDS


@pytest.fixture
def catalog_path() -> Path:
    return _find_project_root() / "docs" / "hands_catalog.json"


def test_catalog_capabilities_match_registry() -> None:
    caps = collect_capabilities()
    cap_names = {c["tool_name"] for c in caps}
    code_names = {tid.removeprefix("tool.") for tid in chat_tool_ids_from_code()}
    assert code_names.issubset(cap_names)
    assert cap_names - code_names == INTERNAL_ONLY_CHAT_TOOLS
    internal = [c for c in caps if c["tool_name"] in INTERNAL_ONLY_CHAT_TOOLS]
    assert len(internal) == len(INTERNAL_ONLY_CHAT_TOOLS)
    assert all(not c["chat_declared"] for c in internal)


def test_catalog_actions_match_skills_dir() -> None:
    actions = collect_actions()
    action_ids = {a["skill_id"] for a in actions}
    assert action_ids == set(load_skill_registry().keys())


def test_catalog_pipelines_match_workflow_kinds() -> None:
    pipelines = collect_pipelines()
    pipe_kinds = {p["workflow_kind"] for p in pipelines}
    assert pipe_kinds == set(WORKFLOW_KINDS)


def test_committed_json_matches_generator(catalog_path: Path) -> None:
    assert catalog_path.is_file(), f"missing {catalog_path}; run scripts/generate_hands_catalog.py"
    committed = json.loads(catalog_path.read_text(encoding="utf-8"))
    generated = build_hands_catalog_dict()
    assert committed == generated


def test_build_agent_tools_maximal_matches_catalog_chat_tool_names(catalog_path: Path) -> None:
    """Catalog chat-declared tool_name set matches all-flags-on build_agent_tools."""
    committed = json.loads(catalog_path.read_text(encoding="utf-8"))
    catalog_chat_names = {
        c["tool_name"] for c in committed["capabilities"] if c.get("chat_declared")
    }
    tool = build_agent_tools(
        allowed_exact_commands=frozenset(["echo test"]),
        include_memory_tools=True,
        include_plan_tools=True,
        include_goal_recall_tool=True,
        include_gsc_read_tools=True,
        include_file_tools=True,
        include_web_search=True,
        include_web_fetch=True,
        include_list_session_web_sources=True,
        include_knowledge_tools=True,
        include_workflow_tools=True,
        include_mission_control_snapshot=True,
        include_run_skill=True,
        include_propose_programme=True,
        include_apply_programme=True,
    )
    code_names = frozen_tool_declaration_names(tool)
    assert catalog_chat_names == set(code_names)
    assert INTERNAL_ONLY_CHAT_TOOLS <= {
        c["tool_name"] for c in committed["capabilities"]
    } - catalog_chat_names
