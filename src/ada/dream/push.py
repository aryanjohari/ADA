"""dream.push — INTERFACE ONLY in v1; always skipped with clear receipt."""

from __future__ import annotations

from typing import Any


def push_outbox(
    *,
    dream_id: str | None = None,
    outbox_path: str | None = None,
) -> dict[str, Any]:
    """Stub: never uploads. Local seal is the durability win first."""
    return {
        "ok": True,
        "push": "skipped",
        "reason": "dream.push stub — remote not configured in v1; local seal retained",
        "dream_id": dream_id,
        "outbox_path": outbox_path,
    }
