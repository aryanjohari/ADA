"""H3 chat capability profiles — tool and harness flags per surface mode."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ada.chat_ingress import ChatSurfaceMode
from ada.config import Settings

PRIMITIVE_ALLOWLIST: frozenset[str] = frozenset(
    {
        "log_memory",
        "recall_memory",
        "add_task",
        "list_tasks",
        "complete_task",
        "body_check",
    }
)

ENTITY_KNOWLEDGE_TOOLS: frozenset[str] = frozenset(
    {
        "search_knowledge",
        "get_entity_graph_context",
        "add_knowledge_source",
    }
)


@dataclass(frozen=True)
class ChatCapabilityProfile:
    surface: ChatSurfaceMode
    include_run_skill: bool
    include_run_primitive: bool
    primitive_allowlist: frozenset[str] | None
    include_propose_programme: bool
    include_apply_programme: bool
    include_workflow_status: bool
    include_knowledge_tools: bool
    knowledge_tool_subset: frozenset[str] | None
    include_file_tools: bool
    include_plan_tools: bool
    include_gsc_read_tools: bool
    entity_harness: bool
    mission_bound_harness: bool
    inject_programme_digest: bool


def profile_chat(settings: Settings) -> ChatCapabilityProfile:
    subset = ENTITY_KNOWLEDGE_TOOLS if settings.enable_knowledge_tools else None
    return ChatCapabilityProfile(
        surface=ChatSurfaceMode.CHAT,
        include_run_skill=False,
        include_run_primitive=True,
        primitive_allowlist=PRIMITIVE_ALLOWLIST,
        include_propose_programme=True,
        include_apply_programme=False,
        include_workflow_status=False,
        include_knowledge_tools=settings.enable_knowledge_tools,
        knowledge_tool_subset=subset,
        include_file_tools=False,
        include_plan_tools=False,
        include_gsc_read_tools=False,
        entity_harness=True,
        mission_bound_harness=False,
        inject_programme_digest=False,
    )


def profile_plan(settings: Settings) -> ChatCapabilityProfile:
    subset = ENTITY_KNOWLEDGE_TOOLS if settings.enable_knowledge_tools else None
    return ChatCapabilityProfile(
        surface=ChatSurfaceMode.PLAN,
        include_run_skill=False,
        include_run_primitive=False,
        primitive_allowlist=None,
        include_propose_programme=True,
        include_apply_programme=True,
        include_workflow_status=False,
        include_knowledge_tools=settings.enable_knowledge_tools,
        knowledge_tool_subset=subset,
        include_file_tools=False,
        include_plan_tools=False,
        include_gsc_read_tools=False,
        entity_harness=True,
        mission_bound_harness=False,
        inject_programme_digest=False,
    )


def profile_agent(settings: Settings) -> ChatCapabilityProfile:
    return ChatCapabilityProfile(
        surface=ChatSurfaceMode.AGENT,
        include_run_skill=True,
        include_run_primitive=False,
        primitive_allowlist=None,
        include_propose_programme=False,
        include_apply_programme=False,
        include_workflow_status=settings.enable_workflow_tools,
        include_knowledge_tools=settings.enable_knowledge_tools,
        knowledge_tool_subset=None,
        include_file_tools=settings.enable_file_tools,
        include_plan_tools=settings.enable_plan_tools,
        include_gsc_read_tools=settings.enable_gsc_read_tools,
        entity_harness=False,
        mission_bound_harness=True,
        inject_programme_digest=True,
    )


def profile_setup(settings: Settings) -> ChatCapabilityProfile:
    return ChatCapabilityProfile(
        surface=ChatSurfaceMode.SETUP,
        include_run_skill=False,
        include_run_primitive=False,
        primitive_allowlist=None,
        include_propose_programme=False,
        include_apply_programme=False,
        include_workflow_status=settings.enable_workflow_tools,
        include_knowledge_tools=settings.enable_knowledge_tools,
        knowledge_tool_subset=None,
        include_file_tools=settings.enable_file_tools,
        include_plan_tools=settings.enable_plan_tools,
        include_gsc_read_tools=settings.enable_gsc_read_tools,
        entity_harness=False,
        mission_bound_harness=False,
        inject_programme_digest=False,
    )


def profile_work_legacy(settings: Settings) -> ChatCapabilityProfile:
    """Mission-bound task (deprecated WORK ingress); tests only."""
    return ChatCapabilityProfile(
        surface=ChatSurfaceMode.AGENT,
        include_run_skill=True,
        include_run_primitive=False,
        primitive_allowlist=None,
        include_propose_programme=False,
        include_apply_programme=False,
        include_workflow_status=settings.enable_workflow_tools,
        include_knowledge_tools=settings.enable_knowledge_tools,
        knowledge_tool_subset=None,
        include_file_tools=settings.enable_file_tools,
        include_plan_tools=settings.enable_plan_tools,
        include_gsc_read_tools=settings.enable_gsc_read_tools,
        entity_harness=False,
        mission_bound_harness=True,
        inject_programme_digest=True,
    )


def profile_for_surface(surface: ChatSurfaceMode, settings: Settings) -> ChatCapabilityProfile:
    if surface == ChatSurfaceMode.CHAT:
        return profile_chat(settings)
    if surface == ChatSurfaceMode.PLAN:
        return profile_plan(settings)
    if surface == ChatSurfaceMode.AGENT:
        return profile_agent(settings)
    if surface == ChatSurfaceMode.SETUP:
        return profile_setup(settings)
    return profile_chat(settings)


def build_profile_orchestrate_flags(
    profile: ChatCapabilityProfile,
    settings: Settings,
    *,
    entity_mode: bool,
) -> dict[str, Any]:
    """Orchestrate-turn include_* flags derived from capability profile."""
    return {
        "include_run_skill": profile.include_run_skill,
        "include_run_primitive": profile.include_run_primitive,
        "primitive_allowlist": profile.primitive_allowlist,
        "include_propose_programme": profile.include_propose_programme,
        "include_apply_programme": profile.include_apply_programme,
        "include_workflow_tools": profile.include_workflow_status,
        "include_knowledge_tools": profile.include_knowledge_tools and not entity_mode,
        "knowledge_tool_subset": profile.knowledge_tool_subset,
        "include_plan_tools": False if entity_mode else profile.include_plan_tools,
        "include_gsc_read_tools": False if entity_mode else profile.include_gsc_read_tools,
    }
