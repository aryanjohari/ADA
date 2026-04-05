"""
StreamingToolExecutor — Phase 2 (claude_logic §7).

MVP: no tool rounds; orchestrator does not import this. Stub keeps a stable
module path for later allowlisted internal tools.
"""

from __future__ import annotations

from typing import Any


class StreamingToolExecutor:
    """Placeholder; full parallel/exclusive execution in Phase 2."""

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        self.discarded = False

    def discard(self) -> None:
        self.discarded = True
