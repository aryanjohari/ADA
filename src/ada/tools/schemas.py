"""Gemini FunctionDeclaration schemas — derived from ToolSpec (M02/M04/M07)."""

from __future__ import annotations

from typing import Any

from ada.tools.toolspec import (
    TOOL_NAMES,
    WEB_GET_TOOL_NAMES,
    WRITE_TOOL_NAMES,
    function_declarations,
    spec_for,
)

__all__ = [
    "TOOL_NAMES",
    "WRITE_TOOL_NAMES",
    "WEB_GET_TOOL_NAMES",
    "function_declarations",
    "spec_for",
]


# Re-export for callers that imported from schemas historically.
def _compat() -> list[dict[str, Any]]:
    return function_declarations()
