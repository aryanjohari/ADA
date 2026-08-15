"""Single ChatSession owner for the HUD process — calls harness.run_turn only."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Callable

from ada.cortex.adapter import CortexAdapter
from ada.cortex.charter import build_system_charter
from ada.cortex.gemini import GeminiAdapter
from ada.cortex.models import resolve_model
from ada.harness.loop import LoopResult, run_turn
from ada.harness.session import ChatSession, Mode
from ada.harness.stream_events import StreamSink
from ada.secrets.load import MissingSecret, load_gemini_api_key


AdapterFactory = Callable[[], CortexAdapter]


class ChatService:
    """One interactive writer assumption (v1): do not also run `ada chat` on same JSONL."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.session: ChatSession | None = None
        self.adapter: CortexAdapter | None = None
        self.history: list[Any] = []
        self.last_denials: list[dict[str, Any]] = []
        self.mode: Mode = "observe"
        # Tests inject a fake cortex via this hook.
        self.adapter_factory: AdapterFactory | None = None
        self._no_key_message: str | None = None

    def current_mode(self) -> Mode:
        if self.session is not None:
            return self.session.mode
        return self.mode

    def run_path(self) -> Path | None:
        if self.session is None:
            return None
        return self.session.run_path

    def _ensure_session(self, mode: Mode) -> None:
        if self.session is not None and self.session.mode == mode:
            return
        # Mode change: end previous session cleanly, start fresh history.
        if self.session is not None and self.session._started:
            self.session.end(stop_reason="mode_switch")
        self.history = []
        self.mode = mode
        model = resolve_model("chat_interactive")
        self.session = ChatSession(mode=mode, model=model)
        if self.adapter_factory is not None:
            self.adapter = self.adapter_factory()
            self._no_key_message = None
            return
        try:
            api_key = load_gemini_api_key()
        except MissingSecret as exc:
            self.adapter = None
            self._no_key_message = exc.message
            return
        self.adapter = GeminiAdapter(api_key, model=model)
        self._no_key_message = None

    def run_user_turn(
        self,
        user_text: str,
        *,
        mode: Mode = "observe",
        sink: StreamSink | None = None,
    ) -> dict[str, Any]:
        """Synchronous turn — intended to run off the ASGI event loop thread."""
        with self._lock:
            self._ensure_session(mode)
            assert self.session is not None

            if self.adapter is None:
                self.session.ensure_started()
                self.session.writer.append(
                    "fault",
                    {"error": "no_key", "detail": self._no_key_message or "missing"},
                )
                if sink is not None:
                    sink.emit("mode_info", {"mode": self.session.mode})
                    sink.emit(
                        "session_receipt_path",
                        {"path": str(self.session.run_path)},
                    )
                    sink.emit(
                        "fault",
                        {
                            "error": "no_key",
                            "message": self._no_key_message or "GEMINI_API_KEY missing",
                        },
                    )
                self.session.end(stop_reason="no_key")
                path = str(self.session.run_path)
                # Reset so next attempt can retry key load.
                self.session = None
                self.adapter = None
                return {
                    "stop_reason": "no_key",
                    "text": None,
                    "steps": 0,
                    "run_path": path,
                }

            system = build_system_charter(
                mode=mode, chill_active=self.session.chill_active
            )
            result: LoopResult = run_turn(
                self.session,
                user_text,
                self.adapter,
                system=system,
                sink=sink,
                contents=self.history,
                end_session=False,
            )
            for receipt in result.tool_receipts:
                if receipt.get("outcome") == "denied" or receipt.get("denied_reason"):
                    self.last_denials.append(
                        {
                            "tool": receipt.get("tool"),
                            "args": receipt.get("args"),
                            "denied_reason": receipt.get("denied_reason"),
                            "receipt_id": receipt.get("receipt_id"),
                        }
                    )
            return {
                "stop_reason": result.stop_reason,
                "text": result.text,
                "steps": result.steps,
                "run_path": result.run_path,
            }

    def confirm_tool(self, tool: str, args: dict[str, Any]) -> dict[str, Any]:
        """Operator confirm — gateway execute with confirmed=true (no model)."""
        from ada.tools.gateway import Gateway

        with self._lock:
            self._ensure_session("agent")
            assert self.session is not None
            self.session.ensure_started()
            merged = dict(args or {})
            merged["confirmed"] = True
            gateway = Gateway(mode="agent", turn_user_text="[hud confirm]")
            result = gateway.execute(tool, merged)
            obs = result.as_observation()
            if result.outcome == "denied":
                self.session.writer.append("tool_denied", obs)
                self.last_denials.append(
                    {
                        "tool": obs.get("tool"),
                        "args": obs.get("args"),
                        "denied_reason": obs.get("denied_reason"),
                        "receipt_id": obs.get("receipt_id"),
                    }
                )
            else:
                self.session.writer.append("tool_result", obs)
            return obs
