"""Chat ingress: operator surfaces (H3) and legacy ingress modes.

Operator-facing surfaces: **chat** | **plan** | **agent** | **setup**.
Legacy ``ChatIngressMode`` remains for transitional code paths one release.
"""

from __future__ import annotations

from enum import Enum


class ChatSurfaceMode(str, Enum):
    """Operator-facing chat surface (tasks.mission_id NULL except SETUP with --mission)."""

    CHAT = "chat"
    PLAN = "plan"
    AGENT = "agent"
    SETUP = "setup"


class ChatIngressMode(str, Enum):
    """Legacy ingress enum (OPEN = global concierge)."""

    OPEN = "open"
    PROGRAMME = "programme"
    WORK = "work"
    SETUP = "setup"

    @property
    def is_entity(self) -> bool:
        return self is ChatIngressMode.OPEN


def surface_operator_label(mode: ChatSurfaceMode) -> str:
    """Operator-facing label for CLI / Streamlit banners."""
    return mode.value


def ingress_operator_label(mode: ChatIngressMode) -> str:
    """Legacy ingress label (prefer surface_operator_label for H3 UI)."""
    if mode == ChatIngressMode.OPEN:
        return "entity"
    if mode == ChatIngressMode.PROGRAMME:
        return "programme"
    if mode == ChatIngressMode.SETUP:
        return "setup_assist"
    if mode == ChatIngressMode.WORK:
        return "work"
    return mode.value


def surface_to_ingress(surface: ChatSurfaceMode) -> ChatIngressMode:
    """Map H3 surface to legacy ingress for code still reading ChatIngressMode."""
    if surface == ChatSurfaceMode.SETUP:
        return ChatIngressMode.SETUP
    if surface in (ChatSurfaceMode.CHAT, ChatSurfaceMode.PLAN):
        return ChatIngressMode.OPEN
    if surface == ChatSurfaceMode.AGENT:
        return ChatIngressMode.WORK
    return ChatIngressMode.OPEN


def resolve_chat_surface_mode(
    *,
    setup_mode: bool = False,
    plan_mode: bool = False,
    agent_mode: bool = False,
) -> ChatSurfaceMode:
    if setup_mode:
        return ChatSurfaceMode.SETUP
    if plan_mode:
        return ChatSurfaceMode.PLAN
    if agent_mode:
        return ChatSurfaceMode.AGENT
    return ChatSurfaceMode.CHAT


def resolve_chat_ingress_mode(
    *,
    setup_mode: bool,
    programme_mode: bool,
    mission_id: int | None,
    surface: ChatSurfaceMode | None = None,
) -> ChatIngressMode:
    if surface is not None:
        if surface == ChatSurfaceMode.SETUP:
            return ChatIngressMode.SETUP
        if surface == ChatSurfaceMode.AGENT and mission_id is not None:
            return ChatIngressMode.WORK
        if surface in (ChatSurfaceMode.CHAT, ChatSurfaceMode.PLAN):
            return ChatIngressMode.OPEN
        if surface == ChatSurfaceMode.AGENT:
            return ChatIngressMode.WORK
    if setup_mode:
        return ChatIngressMode.SETUP
    if programme_mode:
        return ChatIngressMode.PROGRAMME
    if mission_id is not None:
        return ChatIngressMode.WORK
    return ChatIngressMode.OPEN
