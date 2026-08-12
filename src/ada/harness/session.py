"""Chat session state: id, mode, budgets, run writer."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from ada import __version__
from ada.cortex.models import resolve_model
from ada.io.paths import DataPaths, get_paths
from ada.runs.append import RunWriter
from ada.tools.gateway import Gateway

Mode = Literal["observe", "agent", "plan"]

DEFAULT_MAX_STEPS = 8
DEFAULT_WALL_SECONDS = 90.0


def new_session_id() -> str:
    return uuid.uuid4().hex


@dataclass
class ChatSession:
    mode: Mode = "observe"
    model: str = field(default_factory=lambda: resolve_model("chat_interactive"))
    session_id: str = field(default_factory=new_session_id)
    max_steps: int = DEFAULT_MAX_STEPS
    wall_seconds: float = DEFAULT_WALL_SECONDS
    paths: DataPaths | None = None
    jsonl_path: Path | None = None
    gateway: Gateway | None = None
    writer: RunWriter | None = None
    started_monotonic: float = field(default_factory=time.monotonic)
    chill_active: bool = False
    _started: bool = False

    def __post_init__(self) -> None:
        if self.paths is None:
            self.paths = get_paths()
        if self.gateway is None:
            self.gateway = Gateway(mode=self.mode)
        else:
            self.gateway.mode = self.mode
        if self.writer is None:
            self.writer = RunWriter(
                self.session_id,
                paths=self.paths,
                jsonl_path=self.jsonl_path,
            )

    def ensure_started(self, *, host: str | None = None) -> None:
        if self._started:
            return
        import socket

        self.writer.append(
            "session_start",
            {
                "mode": self.mode,
                "model": self.model,
                "agent_version": __version__,
                "host": host or socket.gethostname(),
                "max_steps": self.max_steps,
            },
        )
        self._started = True

    def elapsed(self) -> float:
        return time.monotonic() - self.started_monotonic

    def wall_exceeded(self) -> bool:
        return self.elapsed() >= self.wall_seconds

    def end(self, *, stop_reason: str = "completed", steps: int | None = None) -> None:
        payload: dict[str, Any] = {"stop_reason": stop_reason}
        if steps is not None:
            payload["steps"] = steps
        assert self.writer is not None
        self.writer.append("session_end", payload)

    @property
    def run_path(self) -> Path:
        assert self.writer is not None
        return self.writer.path
