"""CallbackSink → thread-safe queue → SSE byte lines."""

from __future__ import annotations

import json
import queue
import threading
from collections.abc import Callable, Iterator
from typing import Any

from ada.harness.stream_events import CallbackSink

_SENTINEL = object()


def format_sse(event: str, payload: dict[str, Any]) -> str:
    data = json.dumps(payload, default=str, separators=(",", ":"))
    return f"event: {event}\ndata: {data}\n\n"


class StreamBridge:
    """Fan-out harness stream events into an SSE-friendly queue."""

    def __init__(self) -> None:
        self._q: queue.Queue[Any] = queue.Queue()
        self.sink = CallbackSink()
        self.sink.on(self._on_emit)

    def _on_emit(self, event: str, payload: dict[str, Any]) -> None:
        self._q.put(("event", event, payload))

    def close(self, *, turn_done: dict[str, Any] | None = None) -> None:
        if turn_done is not None:
            self._q.put(("event", "turn_done", turn_done))
        self._q.put(_SENTINEL)

    def put_fault(self, message: str, **extra: Any) -> None:
        payload = {"error": message, **extra}
        self._q.put(("event", "fault", payload))

    def iter_sse(self, *, timeout: float = 0.5) -> Iterator[str]:
        while True:
            try:
                item = self._q.get(timeout=timeout)
            except queue.Empty:
                # Keepalive comment so proxies / TestClient stay alive.
                yield ": keepalive\n\n"
                continue
            if item is _SENTINEL:
                break
            kind, event, payload = item
            if kind == "event":
                yield format_sse(event, payload)


def run_with_bridge(
    worker: Callable[[CallbackSink], dict[str, Any]],
) -> Iterator[str]:
    """Run *worker(sink)* in a thread; yield SSE until finished."""
    bridge = StreamBridge()

    result_box: dict[str, Any] = {"result": None, "error": None}

    def _target() -> None:
        try:
            result_box["result"] = worker(bridge.sink)
        except Exception as exc:  # noqa: BLE001
            result_box["error"] = str(exc)
            bridge.put_fault(str(exc))
        finally:
            done = result_box["result"] or {
                "stop_reason": "error" if result_box["error"] else "completed",
            }
            if isinstance(done, dict):
                bridge.close(turn_done=done)
            else:
                bridge.close(turn_done={"stop_reason": "completed"})

    thread = threading.Thread(target=_target, name="ada-hud-turn", daemon=True)
    thread.start()
    try:
        yield from bridge.iter_sse()
    finally:
        thread.join(timeout=120)
