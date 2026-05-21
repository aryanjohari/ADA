"""Extract allowlist ids from code for drift checks against ALLOWLIST_MANIFEST.md.

Also builds the Hands catalog (capabilities, actions, pipelines, playbooks) for H1 drift tests.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from ada.config import _find_project_root
from ada.motor.argv import list_command_ids
from ada.motor.registry import load_shell_allowlist, load_skill_registry
from ada.tools.registry import build_agent_tools, frozen_tool_declaration_names
from ada.workflow.playbook_resolve import registry_path as playbook_registry_path
from ada.workflow.templates import WORKFLOW_KINDS, _base_steps

_MANIFEST_ID_RE = re.compile(r"`([a-z][a-z0-9_.]+)`")


def _has_run_skill_flag() -> bool:
    import inspect

    sig = inspect.signature(build_agent_tools)
    return "include_run_skill" in sig.parameters


def _has_propose_programme_flag() -> bool:
    import inspect

    sig = inspect.signature(build_agent_tools)
    return "include_propose_programme" in sig.parameters


def _has_apply_programme_flag() -> bool:
    import inspect

    sig = inspect.signature(build_agent_tools)
    return "include_apply_programme" in sig.parameters


def chat_tool_ids_from_code() -> frozenset[str]:
    """Declared chat tools when all feature flags enabled."""
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
        include_run_skill=_has_run_skill_flag(),
        include_propose_programme=_has_propose_programme_flag(),
        include_apply_programme=_has_apply_programme_flag(),
    )
    names = frozen_tool_declaration_names(tool)
    return frozenset(f"tool.{n}" for n in names)


def op_ids_from_code() -> frozenset[str]:
    return frozenset(f"op.{cid}" for cid in list_command_ids())


def shell_ids_from_code(*, memory_dir: Path) -> frozenset[str]:
    lines = load_shell_allowlist(memory_dir)
    out = {"shell.loader", "tool.run_allowlisted_shell"}
    if lines:
        out.add("shell.exact_line")
    return frozenset(out)


def parse_manifest_ids(manifest_path: Path) -> frozenset[str]:
    text = manifest_path.read_text(encoding="utf-8")
    found: set[str] = set()
    for m in _MANIFEST_ID_RE.finditer(text):
        fid = m.group(1)
        if fid.startswith(("tool.", "op.", "shell.", "host.", "streamlit.")):
            found.add(fid)
    return frozenset(found)


def collect_code_ids(*, memory_dir: Path) -> frozenset[str]:
    ids: set[str] = set()
    ids.update(chat_tool_ids_from_code())
    ids.update(f"tool.{n}" for n in INTERNAL_ONLY_CHAT_TOOLS)
    ids.update(op_ids_from_code())
    ids.update(shell_ids_from_code(memory_dir=memory_dir))
    return frozenset(ids)


# --- Hands catalog (H1) ---

_ENTITY_KNOWLEDGE_TOOLS = frozenset(
    {"search_knowledge", "get_entity_graph_context", "add_knowledge_source"}
)

_LATER = "later"

# Not declared to Gemini in chat (H2); CLI and internal callers use enqueue_workflow_via_tool.
INTERNAL_ONLY_CHAT_TOOLS: frozenset[str] = frozenset({"enqueue_workflow"})

_TOOL_ENV_FLAGS: dict[str, list[str]] = {
    "check_token_usage": [],
    "get_mission_control_snapshot": ["wired in chat_session"],
    "propose_programme": ["ingress: chat, plan"],
    "apply_programme": ["ingress: plan"],
    "run_skill": ["ingress: agent"],
    "run_allowlisted_shell": ["memory/shell_allowlist.txt non-empty"],
    "append_master_section": ["ADA_ENABLE_MEMORY_TOOLS"],
    "append_soul_fragment": ["ADA_ENABLE_MEMORY_TOOLS"],
    "read_task_plan": ["ADA_ENABLE_PLAN_TOOLS"],
    "write_task_plan": ["ADA_ENABLE_PLAN_TOOLS"],
    "read_goal_task_view": ["ADA_ENABLE_GOAL_RECALL_TOOL"],
    "get_gsc_opportunities": ["ADA_ENABLE_GSC_READ_TOOLS"],
    "list_workspace_directory": ["ADA_ENABLE_FILE_TOOLS"],
    "read_workspace_file": ["ADA_ENABLE_FILE_TOOLS"],
    "write_workspace_file": ["ADA_ENABLE_FILE_TOOLS"],
    "web_search": ["ADA_ENABLE_WEB_TOOLS", "ADA_SERPER_API_KEY"],
    "fetch_url_text": ["ADA_ENABLE_WEB_TOOLS"],
    "list_session_web_sources": ["ADA_ENABLE_WEB_SOURCES_TOOL"],
    "search_knowledge": ["ADA_ENABLE_KNOWLEDGE_TOOLS"],
    "get_entity_graph_context": ["ADA_ENABLE_KNOWLEDGE_TOOLS"],
    "record_synthesis": ["ADA_ENABLE_KNOWLEDGE_TOOLS"],
    "record_market_edge": ["ADA_ENABLE_KNOWLEDGE_TOOLS"],
    "add_knowledge_source": ["ADA_ENABLE_KNOWLEDGE_TOOLS"],
    "record_entity": ["ADA_ENABLE_KNOWLEDGE_TOOLS"],
    "record_edge": ["ADA_ENABLE_KNOWLEDGE_TOOLS"],
    "link_evidence": ["ADA_ENABLE_KNOWLEDGE_TOOLS"],
    "enqueue_workflow": ["ADA_ENABLE_WORKFLOW_TOOLS"],
    "get_workflow_status": ["ADA_ENABLE_WORKFLOW_TOOLS"],
}

_TOOL_RISK: dict[str, str] = {
    "check_token_usage": "L",
    "get_mission_control_snapshot": "L",
    "propose_programme": "L",
    "apply_programme": "H",
    "run_skill": "M",
    "run_allowlisted_shell": "M",
    "append_master_section": "M",
    "append_soul_fragment": "M",
    "read_task_plan": "L",
    "write_task_plan": "M",
    "read_goal_task_view": "L",
    "get_gsc_opportunities": "M",
    "list_workspace_directory": "M",
    "read_workspace_file": "M",
    "write_workspace_file": "H",
    "web_search": "M",
    "fetch_url_text": "M",
    "list_session_web_sources": "L",
    "search_knowledge": "M",
    "get_entity_graph_context": "M",
    "record_synthesis": "M",
    "record_market_edge": "M",
    "add_knowledge_source": "M",
    "record_entity": "H",
    "record_edge": "H",
    "link_evidence": "M",
    "enqueue_workflow": "H",
    "get_workflow_status": "L",
}

_TOOL_MISSION_REQUIRED: dict[str, str] = {
    "search_knowledge": "when_scoped",
    "get_entity_graph_context": "when_scoped",
    "record_synthesis": "when_scoped",
    "record_market_edge": "when_scoped",
    "record_entity": "when_scoped",
    "record_edge": "when_scoped",
    "link_evidence": "when_scoped",
    "enqueue_workflow": "when_scoped",
    "run_skill": "when_scoped",
    "get_mission_control_snapshot": "when_scoped",
}


def _maximal_tool_names() -> frozenset[str]:
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
        include_run_skill=_has_run_skill_flag(),
        include_propose_programme=_has_propose_programme_flag(),
        include_apply_programme=_has_apply_programme_flag(),
    )
    return frozen_tool_declaration_names(tool)


def _ingress_availability(tool_name: str) -> dict[str, str]:
    """H3 surfaces: chat | plan | agent | setup (+ legacy entity/work keys)."""
    kn = tool_name in _ENTITY_KNOWLEDGE_TOOLS or tool_name in {
        "search_knowledge",
        "get_entity_graph_context",
        "record_synthesis",
        "record_market_edge",
        "add_knowledge_source",
        "record_entity",
        "record_edge",
        "link_evidence",
    }
    chat: str
    plan: str
    agent: str
    setup: str
    if tool_name == "propose_programme":
        chat, plan, agent, setup = "yes", "yes", "no", "no"
    elif tool_name == "apply_programme":
        chat, plan, agent, setup = "no", "yes", "no", "no"
    elif tool_name == "run_skill":
        chat, plan, agent, setup = "no", "no", "yes", "no"
    elif tool_name in ("read_task_plan", "write_task_plan"):
        chat, plan, agent, setup = "no", "no", "yes", "yes"
    elif tool_name in (
        "list_workspace_directory",
        "read_workspace_file",
        "write_workspace_file",
    ):
        chat, plan, agent, setup = "no", "no", "yes", "yes"
    elif tool_name == "get_gsc_opportunities":
        chat, plan, agent, setup = "no", "no", "yes", "no"
    elif tool_name == "enqueue_workflow":
        chat, plan, agent, setup = "no", "no", "no", "no"
    elif tool_name == "get_workflow_status":
        chat, plan, agent, setup = "no", "no", "yes", "yes"
    elif tool_name == "get_mission_control_snapshot":
        chat, plan, agent, setup = "yes", "yes", "if_mission", "if_mission"
    elif kn and tool_name in _ENTITY_KNOWLEDGE_TOOLS:
        chat, plan, agent, setup = "subset", "subset", "yes", "yes"
    elif kn:
        chat, plan, agent, setup = "no", "no", "yes", "yes"
    else:
        chat, plan, agent, setup = "yes", "yes", "yes", "yes"
    return {
        "chat": chat,
        "plan": plan,
        "agent": agent,
        "setup": setup,
        "entity": chat,
        "work": agent,
    }


def collect_capabilities() -> list[dict[str, Any]]:
    """Structured capability rows for chat declarations plus internal-only tools."""
    declared = _maximal_tool_names()
    names = sorted(declared | INTERNAL_ONLY_CHAT_TOOLS)
    out: list[dict[str, Any]] = []
    for name in names:
        row: dict[str, Any] = {
            "id": f"cap.{name}",
            "tool_name": name,
            "chat_declared": name in declared,
            "env_flags": list(_TOOL_ENV_FLAGS.get(name, [])),
            "risk": _TOOL_RISK.get(name, "M"),
            "mission_required": _TOOL_MISSION_REQUIRED.get(name, "no"),
        }
        row.update(_ingress_availability(name))
        out.append(row)
    return out


def collect_actions(*, project_root: Path | None = None) -> list[dict[str, Any]]:
    registry = load_skill_registry(project_root)
    rows: list[dict[str, Any]] = []
    for sid in sorted(registry):
        spec = registry[sid]
        rows.append(
            {
                "id": f"action.{sid}",
                "skill_id": sid,
                "description": spec.description,
                "motor_type": spec.motor_type,
                "risk_tier": spec.risk_tier,
                "mission_required": spec.mission_required,
                "require_approval": spec.require_approval,
                "playbook_id": spec.playbook_id,
                "workflow_kind": spec.workflow_kind,
            }
        )
    return rows


def collect_pipelines() -> list[dict[str, Any]]:
    actions = load_skill_registry()
    by_kind: dict[str, list[str]] = {}
    for sid, spec in actions.items():
        if spec.workflow_kind:
            by_kind.setdefault(spec.workflow_kind, []).append(sid)
    rows: list[dict[str, Any]] = []
    for kind in sorted(WORKFLOW_KINDS):
        steps = _base_steps(kind)
        rows.append(
            {
                "id": f"pipeline.{kind}",
                "workflow_kind": kind,
                "steps": [
                    {
                        "step_index": s["step_index"],
                        "step_type": s["step_type"],
                        "input_json": s.get("input_json") or {},
                    }
                    for s in steps
                ],
                "enqueued_by_actions": sorted(by_kind.get(kind, [])),
            }
        )
    return rows


def collect_playbooks(*, project_root: Path | None = None) -> list[dict[str, Any]]:
    root = project_root if project_root is not None else _find_project_root()
    path = playbook_registry_path(root)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"invalid playbook registry: {path}")
    playbooks = raw.get("playbooks") or {}
    if not isinstance(playbooks, dict):
        raise ValueError(f"playbooks key must be a mapping: {path}")
    rows: list[dict[str, Any]] = []
    for pid in sorted(playbooks):
        entry = playbooks[pid]
        if not isinstance(entry, dict):
            continue
        rows.append(
            {
                "id": f"playbook.{pid}",
                "playbook_id": pid,
                "workflow_kind": str(entry.get("workflow_kind") or "").strip(),
                "risk_tier": str(entry.get("risk_tier") or "").strip(),
                "operator_visible": False,
            }
        )
    return rows


def build_hands_catalog_dict(*, project_root: Path | None = None) -> dict[str, Any]:
    """Machine-readable Hands catalog (capabilities, actions, pipelines, playbooks)."""
    return {
        "version": 1,
        "generated_by": "ada.motor.manifest_sync.build_hands_catalog_dict",
        "capabilities": collect_capabilities(),
        "actions": collect_actions(project_root=project_root),
        "pipelines": collect_pipelines(),
        "playbooks": collect_playbooks(project_root=project_root),
    }
