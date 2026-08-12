"""Streaming / HUD event hooks — callbacks only; no Serve in M02."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol


class StreamSink(Protocol):
    def emit(self, event: str, payload: dict[str, Any]) -> None: ...


EmitFn = Callable[[str, dict[str, Any]], None]


@dataclass
class CallbackSink:
    """Fan-out callbacks for Slice 2 HUD subscribers."""

    callbacks: list[EmitFn] = field(default_factory=list)

    def on(self, fn: EmitFn) -> None:
        self.callbacks.append(fn)

    def emit(self, event: str, payload: dict[str, Any]) -> None:
        for fn in self.callbacks:
            fn(event, payload)


@dataclass
class NullSink:
    def emit(self, event: str, payload: dict[str, Any]) -> None:
        return None
