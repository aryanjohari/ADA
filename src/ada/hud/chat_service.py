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
from ada.harness.plan_artifact import new_plan_id
from ada.harness.session import ChatSession, Mode
from ada.harness.stream_events import StreamSink
from ada.secrets.load import MissingSecret, load_gemini_api_key


AdapterFactory = Callable[[], CortexAdapter]

_PLAN_AGENT = frozenset({"plan", "agent"})


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
        self.last_plan: dict[str, Any] | None = None
        # Consent Integrity: receipt_id → {tool, args} for pending confirms.
        self.pending_confirms: dict[str, dict[str, Any]] = {}

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
        prev = self.session.mode if self.session is not None else None
        preserve = (
            prev is not None
            and prev in _PLAN_AGENT
            and mode in _PLAN_AGENT
        )
        # Mode change: end previous session cleanly.
        if self.session is not None and self.session._started:
            self.session.end(stop_reason="mode_switch")
        if not preserve:
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
                    "plan": None,
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
                if receipt.get("needs_confirm") or receipt.get("outcome") == "needs_confirm":
                    rid = str(receipt.get("receipt_id") or "")
                    if rid:
                        self.pending_confirms[rid] = {
                            "tool": receipt.get("tool"),
                            "args": dict(receipt.get("args") or {}),
                        }
            if result.plan is not None:
                self.last_plan = result.plan
            out: dict[str, Any] = {
                "stop_reason": result.stop_reason,
                "text": result.text,
                "steps": result.steps,
                "run_path": result.run_path,
            }
            if result.plan is not None:
                out["plan"] = result.plan
            return out

    def accept_plan(
        self,
        *,
        steps: list[dict[str, Any]],
        plan_id: str | None = None,
        raw_text: str | None = None,
    ) -> dict[str, Any]:
        """Materialize plan steps as open_loops kind:todo (no cortex, no write tools)."""
        from ada.memory.open_loops import upsert_loop

        with self._lock:
            pid = (plan_id or "").strip() or new_plan_id()
            todos: list[dict[str, str]] = []
            for step in steps:
                text = str(
                    step.get("text") if isinstance(step, dict) else step or ""
                ).strip()
                if not text:
                    continue
                due_at = None
                remind_at = None
                if isinstance(step, dict):
                    if step.get("due_at"):
                        due_at = str(step.get("due_at")).strip() or None
                    if step.get("remind_at"):
                        remind_at = str(step.get("remind_at")).strip() or None
                result = upsert_loop(
                    text=text,
                    kind="todo",
                    status="open",
                    due_at=due_at,
                    remind_at=remind_at,
                )
                loop = result.get("loop") if isinstance(result.get("loop"), dict) else {}
                loop_id = str(loop.get("id") or result.get("id") or "")
                todos.append({"id": loop_id, "text": text})

            if self.last_plan and (
                not plan_id or self.last_plan.get("plan_id") == plan_id
            ):
                self.last_plan = dict(self.last_plan)
                self.last_plan["status"] = "accepted"

            if self.session is not None:
                self.session.ensure_started()
                self.session.writer.append(
                    "plan_accepted",
                    {
                        "plan_id": pid,
                        "todos": todos,
                        "count": len(todos),
                        "raw_text": raw_text,
                    },
                )

            return {
                "plan_id": pid,
                "todos": todos,
                "count": len(todos),
            }

    def confirm_tool(
        self,
        tool: str,
        args: dict[str, Any],
        *,
        pending_id: str | None = None,
    ) -> dict[str, Any]:
        """Operator confirm — gateway execute with confirmed=true (no model)."""
        from ada.tools.gateway import Gateway

        with self._lock:
            if pending_id:
                pending = self.pending_confirms.get(pending_id)
                if pending is None:
                    raise ValueError(f"unknown pending_id {pending_id!r}")
                if pending.get("tool") != tool:
                    raise ValueError(
                        f"pending_id tool mismatch: expected {pending.get('tool')!r}"
                    )
                # Bind to stashed args (Consent Integrity) — ignore client rewrite.
                args = dict(pending.get("args") or {})

            self._ensure_session("agent")
            assert self.session is not None
            self.session.ensure_started()
            merged = dict(args or {})
            merged["confirmed"] = True
            gateway = Gateway(mode="agent", turn_user_text="[hud confirm]")
            result = gateway.execute(tool, merged)
            obs = result.as_observation()
            if pending_id:
                self.pending_confirms.pop(pending_id, None)
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
