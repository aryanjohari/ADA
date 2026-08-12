"""Purpose → model map. Agent does not shop models per turn (M02 §5.6)."""

from __future__ import annotations

import os

# Lab default — re-check client.models.list + deprecations at deploy time.
MODEL_CHAT_INTERACTIVE = "gemini-2.5-flash"
MODEL_DREAM_MANAGE = "gemini-2.5-flash"
MODEL_OPTIONAL_HEAVY = "gemini-2.5-pro"

ENV_GEMINI_MODEL = "ADA_GEMINI_MODEL"

PURPOSE_MAP: dict[str, str] = {
    "chat_interactive": MODEL_CHAT_INTERACTIVE,
    "dream_manage": MODEL_DREAM_MANAGE,
    "optional_heavy": MODEL_OPTIONAL_HEAVY,
}


def resolve_model(purpose: str = "chat_interactive") -> str:
    """Return configured model id for *purpose*.

    Override: ADA_GEMINI_MODEL wins for interactive chat (and any purpose
    when set — operator pin, not agent shopping).
    """
    override = os.environ.get(ENV_GEMINI_MODEL, "").strip()
    if override:
        return override
    return PURPOSE_MAP.get(purpose, MODEL_CHAT_INTERACTIVE)
