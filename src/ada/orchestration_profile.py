"""Optional interaction profiles for orchestrate_turn (fast vs full background)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OrchestrationProfile:
    """Tighten tool breadth / depth for responsive turns vs heavy background work."""

    name: str
    max_tool_rounds: int | None = None
    disable_web_tools: bool = False
    disable_gsc_read_tools: bool = False


INTERACTIVE_FAST = OrchestrationProfile(
    name="interactive_fast",
    max_tool_rounds=4,
    disable_web_tools=True,
    disable_gsc_read_tools=True,
)

SETUP_ASSIST = OrchestrationProfile(
    name="setup_assist",
    max_tool_rounds=6,
    disable_web_tools=True,
    disable_gsc_read_tools=True,
)

BACKGROUND_FULL = OrchestrationProfile(
    name="background_full",
    max_tool_rounds=None,
    disable_web_tools=False,
    disable_gsc_read_tools=False,
)


def orchestrate_turn_kwargs(
    profile: OrchestrationProfile | None,
    *,
    base_max_tool_rounds: int,
    include_gsc_read_tools: bool,
    web_config: Any,
) -> dict[str, Any]:
    """Return kwargs to merge into ``orchestrate_turn`` for this profile."""
    if profile is None:
        return {}
    out: dict[str, Any] = {}
    if profile.max_tool_rounds is not None:
        out["max_tool_rounds"] = min(base_max_tool_rounds, profile.max_tool_rounds)
    if profile.disable_web_tools:
        out["web_config"] = None
    if profile.disable_gsc_read_tools:
        out["include_gsc_read_tools"] = False
    return out
