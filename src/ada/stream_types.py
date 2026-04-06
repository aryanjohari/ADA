"""Shared types for streaming + function calling (keeps imports acyclic)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CompletedFunctionCall:
    name: str
    args: dict[str, Any]
    id: str | None


@dataclass
class StreamLegResult:
    text: str
    function_calls: list[CompletedFunctionCall]
    usage: dict[str, Any]
    finish_reason: str | None
