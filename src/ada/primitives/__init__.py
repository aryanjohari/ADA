"""J1 primitives — closed handler list for personal CRM and body check."""

from __future__ import annotations

from typing import Any

from ada.config import Settings
from ada.primitives.catalog import PRIMITIVE_IDS, PRIMITIVES
from ada.primitives.handlers import execute_primitive
from ada.query_engine import QueryEngine

__all__ = [
    "PRIMITIVE_IDS",
    "PRIMITIVES",
    "execute_primitive",
    "run_primitive",
]


async def run_primitive(
    qe: QueryEngine,
    settings: Settings,
    primitive_id: str,
    args: dict[str, Any] | None = None,
    *,
    kernel=None,
) -> dict[str, Any]:
    """Public entry: run one primitive and return structured JSON."""
    return await execute_primitive(
        qe, settings, primitive_id, args, kernel=kernel
    )
