"""ReAct multi-step tool loop — observations ground body claims."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from ada.cortex.adapter import CortexAdapter, CortexTurn
from ada.cortex.charter import CHILL_SESSION_OVERRIDE, build_system_charter
from ada.cortex.cost import estimate_usd
from ada.cortex.gemini import observation_to_content, user_content
from ada.harness.session import ChatSession
from ada.harness.stream_events import CallbackSink, NullSink, StreamSink

# Narrow chill cues (M05) — sticky for the session once matched.
_CHILL_CUE = re.compile(
    r"\b(chill|softer|stop roasting|tone it down|less roast)\b",
    re.IGNORECASE,
)


def detect_chill_cue(user_text: str) -> bool:
    """True if user asked to soften roast for the session."""
    return bool(_CHILL_CUE.search(user_text or ""))


@dataclass
class LoopResult:
    text: str | None
    stop_reason: str
    steps: int
    tool_receipts: list[dict[str, Any]] = field(default_factory=list)
    usage_rounds: list[dict[str, Any]] = field(default_factory=list)
    run_path: str | None = None


def _tool_key(name: str, args: dict[str, Any]) -> str:
    return f"{name}:{json.dumps(args, sort_keys=True, default=str)}"


def _append_usage(session: ChatSession, turn: CortexTurn, sink: StreamSink) -> dict[str, Any]:
    usage = dict(turn.usage or {})
    if usage:
        est = estimate_usd(
            session.model,
            prompt_tokens=int(usage.get("prompt_token_count") or 0),
            candidates_tokens=int(usage.get("candidates_token_count") or 0),
        )
        usage["usd_estimate"] = est.usd_estimate
        usage["usd_labeled"] = "estimate"
        usage["model"] = session.model
        session.writer.append("usage", usage)
        sink.emit("usage_update", usage)
    return usage


def _apply_chill_to_system(system_prompt: str, *, chill_active: bool) -> str:
    if not chill_active:
        return system_prompt
    if CHILL_SESSION_OVERRIDE in system_prompt:
        return system_prompt
    return system_prompt.rstrip() + "\n\n" + CHILL_SESSION_OVERRIDE


def run_turn(
    session: ChatSession,
    user_text: str,
    adapter: CortexAdapter,
    *,
    system: str | None = None,
    sink: StreamSink | None = None,
    contents: list[Any] | None = None,
    end_session: bool = True,
) -> LoopResult:
    """Run one user turn through the ReAct loop.

    Mutates *contents* in place when provided (REPL multi-turn history).
    Set end_session=False for REPL turns; call session.end() on exit.
    """
    sink = sink or NullSink()
    session.ensure_started()
    session.reset_wall_clock()
    session.writer.append("user", {"text": user_text})
    sink.emit("mode_info", {"mode": session.mode})
    sink.emit("session_receipt_path", {"path": str(session.run_path)})

    if detect_chill_cue(user_text):
        session.chill_active = True

    if system is None:
        system_prompt = build_system_charter(
            mode=session.mode, chill_active=session.chill_active
        )
    else:
        system_prompt = _apply_chill_to_system(system, chill_active=session.chill_active)

    history: list[Any] = contents if contents is not None else []
    history.append(user_content(user_text))

    receipts: list[dict[str, Any]] = []
    usage_rounds: list[dict[str, Any]] = []
    seen_calls: set[str] = set()
    last_text: str | None = None
    stop_reason = "completed"
    steps = 0

    gateway = session.gateway
    assert gateway is not None
    # Trust boundary: paste allowlist uses this turn's user text, not model args.
    gateway.turn_user_text = user_text

    while steps < session.max_steps:
        if session.wall_exceeded():
            stop_reason = "wall_time"
            break

        steps += 1
        try:
            turn = adapter.generate(system=system_prompt, contents=history)
        except Exception as exc:  # noqa: BLE001
            session.writer.append("fault", {"error": str(exc), "where": "cortex.generate"})
            stop_reason = "error"
            last_text = f"Cortex error: {exc}"
            break

        usage_rounds.append(_append_usage(session, turn, sink))

        model_payload: dict[str, Any] = {
            "text": turn.text,
            "tool_calls": [
                {"name": tc.name, "args": tc.args, "call_id": tc.call_id}
                for tc in turn.tool_calls
            ],
        }
        session.writer.append("model", model_payload)

        if turn.text:
            last_text = turn.text
            sink.emit("token_delta", {"text": turn.text})

        if not turn.tool_calls:
            stop_reason = "completed"
            if turn.raw is not None and getattr(turn.raw, "candidates", None):
                cand = turn.raw.candidates[0]
                if getattr(cand, "content", None) is not None:
                    history.append(cand.content)
            break

        if turn.raw is not None and getattr(turn.raw, "candidates", None):
            cand = turn.raw.candidates[0]
            if getattr(cand, "content", None) is not None:
                history.append(cand.content)

        duplicate = False
        for tc in turn.tool_calls:
            key = _tool_key(tc.name, tc.args)
            if key in seen_calls:
                duplicate = True
                session.writer.append(
                    "fault",
                    {"error": "duplicate_tool_call", "tool": tc.name, "args": tc.args},
                )
                stop_reason = "duplicate_tool"
                break
            seen_calls.add(key)

            session.writer.append("tool_call", {"tool": tc.name, "args": tc.args})
            sink.emit("tool_call_started", {"tool": tc.name, "args": tc.args})

            result = gateway.execute(tc.name, tc.args)
            obs = result.as_observation()
            receipts.append(obs)

            if result.outcome == "denied":
                session.writer.append("tool_denied", obs)
            else:
                session.writer.append("tool_result", obs)

            sink.emit(
                "tool_call_finished",
                {"tool": tc.name, "ok": result.ok, "receipt_id": result.receipt_id},
            )
            history.append(observation_to_content(obs, call_id=tc.call_id))

        if duplicate:
            break
    else:
        stop_reason = "max_steps"

    if end_session:
        session.end(stop_reason=stop_reason, steps=steps)

    return LoopResult(
        text=last_text,
        stop_reason=stop_reason,
        steps=steps,
        tool_receipts=receipts,
        usage_rounds=usage_rounds,
        run_path=str(session.run_path),
    )


# Re-export for tests that want a simple callback sink constructor
def make_sink() -> CallbackSink:
    return CallbackSink()
