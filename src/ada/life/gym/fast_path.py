"""Gym write fast-paths — start/end/lift before cortex."""

from __future__ import annotations

from typing import Any, Callable

from ada.harness.mouth import CONFIRM_SPLIT
from ada.life.gym.doors import (
    gym_read_takes_priority,
    is_gym_end_utterance,
    is_gym_start_utterance,
    is_incomplete_lift_utterance,
    is_lift_log_utterance,
    lift_log_fast_path_args,
)
from ada.life.gym.speak import speak_gym_end, speak_lift_log
from ada.life.gym.spine import FOLLOW_ON_ASK, INCOMPLETE_ASK, NEED_KG_ASK, build_lift_log_args

ExecuteTool = Callable[..., None]
ReceiptData = Callable[[list[dict[str, Any]], str], dict[str, Any]]

LIFE_SAVE_FAIL_ACK = "That didn't save — try once more."

# Re-export ask constants for callers that historically imported from fast_path.
__all__ = [
    "FOLLOW_ON_ASK",
    "INCOMPLETE_ASK",
    "NEED_KG_ASK",
    "fast_path_gym_end",
    "fast_path_gym_start",
    "fast_path_lift",
    "try_write_fast_path",
]


def fast_path_lift(
    session: Any,
    sink: Any,
    history: list[Any],
    receipts: list[dict[str, Any]],
    args: dict[str, Any],
    *,
    execute_tool: ExecuteTool,
    receipt_data: ReceiptData,
) -> tuple[str | None, str | None]:
    utterance = str(args.get("utterance") or "").strip()
    if not utterance or args.get("sets"):
        return None, None
    from ada.logs.gym import last_open_session_exercise_name

    follow_on = last_open_session_exercise_name()
    lift_args = build_lift_log_args(utterance, follow_on_name=follow_on)
    if not lift_args.get("ok") or not lift_args.get("sets"):
        ask = str(lift_args.get("ask") or "").strip()
        # Fail closed with a human ask — never silent no-tool (F-M24-3).
        return "missing_life_receipt", ask or (
            "Need load and reps for that lift — say it like 30kg x 12."
        )
    execute_tool(
        session,
        sink,
        history,
        receipts,
        tool="life_lift_log",
        args={"sets": lift_args["sets"]},
        call_id="lift-fast-path",
    )
    last = receipts[-1] if receipts else {}
    if not last.get("ok"):
        return "missing_life_receipt", LIFE_SAVE_FAIL_ACK
    data = last.get("data") if isinstance(last.get("data"), dict) else {}
    return "pack_fast_path", speak_lift_log(data)


def fast_path_gym_start(
    session: Any,
    sink: Any,
    history: list[Any],
    receipts: list[dict[str, Any]],
    *,
    execute_tool: ExecuteTool,
) -> tuple[str | None, str | None]:
    from ada.logs.gym_split import empty_day_slots, has_gym_split

    execute_tool(
        session,
        sink,
        history,
        receipts,
        tool="life_gym_start",
        args={},
        call_id="gym-start-fast-path",
    )
    last = receipts[-1] if receipts else {}
    if not last.get("ok"):
        return "missing_life_receipt", LIFE_SAVE_FAIL_ACK
    if not has_gym_split():
        execute_tool(
            session,
            sink,
            history,
            receipts,
            tool="life_split_set",
            args={"days": empty_day_slots(), "confirmed": False},
            call_id="gym-split-confirm-probe",
        )
        split = receipts[-1] if receipts else {}
        if split.get("needs_confirm") or (split.get("data") or {}).get("needs_confirm"):
            return "pack_fast_path", CONFIRM_SPLIT
    return "pack_fast_path", "Gym session's open."


def fast_path_gym_end(
    session: Any,
    sink: Any,
    history: list[Any],
    receipts: list[dict[str, Any]],
    *,
    execute_tool: ExecuteTool,
) -> tuple[str | None, str | None]:
    execute_tool(
        session,
        sink,
        history,
        receipts,
        tool="life_gym_end",
        args={},
        call_id="gym-end-fast-path",
    )
    last = receipts[-1] if receipts else {}
    if not last.get("ok"):
        return "missing_life_receipt", LIFE_SAVE_FAIL_ACK
    data = last.get("data") if isinstance(last.get("data"), dict) else {}
    return "pack_fast_path", speak_gym_end(data)


def try_write_fast_path(
    session: Any,
    sink: Any,
    history: list[Any],
    receipts: list[dict[str, Any]],
    user_text: str,
    *,
    execute_tool: ExecuteTool,
    receipt_data: ReceiptData,
) -> tuple[str | None, str | None]:
    """Force gym start/end/lift before cortex even if pack_hint is missing/wrong."""
    if session.mode != "agent":
        return None, None
    if gym_read_takes_priority(user_text):
        return None, None
    if is_incomplete_lift_utterance(user_text):
        built = build_lift_log_args(user_text)
        ask = str(built.get("ask") or "").strip()
        return "missing_life_receipt", ask or INCOMPLETE_ASK
    if is_lift_log_utterance(user_text):
        args = lift_log_fast_path_args(user_text) or {"utterance": user_text}
        return fast_path_lift(
            session,
            sink,
            history,
            receipts,
            args,
            execute_tool=execute_tool,
            receipt_data=receipt_data,
        )
    if is_gym_start_utterance(user_text):
        return fast_path_gym_start(
            session, sink, history, receipts, execute_tool=execute_tool
        )
    if is_gym_end_utterance(user_text):
        return fast_path_gym_end(
            session, sink, history, receipts, execute_tool=execute_tool
        )
    return None, None
