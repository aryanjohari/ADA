"""Opt-in stderr diagnostics for Gemini streaming (``ADA_DEBUG_STREAM=1`` or ``Settings.debug_stream``)."""

from __future__ import annotations

import os
import sys
from typing import Any


def is_stream_debug_on(explicit: bool = False) -> bool:
    if explicit:
        return True
    return os.environ.get("ADA_DEBUG_STREAM", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def log_stream(enabled: bool, component: str, *parts: Any) -> None:
    if not enabled:
        return
    print(f"[ada:{component}]", *parts, file=sys.stderr, flush=True)
