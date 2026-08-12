"""Cortex adapter protocol — Gemini primary; Claude slot later."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class ProposedToolCall:
    name: str
    args: dict[str, Any]
    call_id: str | None = None


@dataclass
class CortexTurn:
    """One model round: optional text + proposed tool calls + usage."""

    text: str | None = None
    tool_calls: list[ProposedToolCall] = field(default_factory=list)
    usage: dict[str, Any] = field(default_factory=dict)
    raw: Any = None


@runtime_checkable
class CortexAdapter(Protocol):
    """Thin cortex interface — harness owns the tool loop."""

    model: str

    def generate(
        self,
        *,
        system: str,
        contents: list[Any],
        tools: list[Any] | None = None,
    ) -> CortexTurn:
        """Generate one turn. Must not auto-execute tools (AFC off)."""
        ...
