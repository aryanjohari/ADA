"""Habit write fast-paths — do/miss before cortex."""

from __future__ import annotations

from typing import Any, Callable

from ada.harness.mouth import CONFIRM_HABIT, CONFIRM_HABIT_CREATE
from ada.life.habits.doors import is_habit_do_utterance, is_habit_miss_utterance
from ada.life.habits.speak import speak_habit_tick
from ada.life.habits.spine import build_habit_tick_args

ExecuteTool = Callable[..., None]
ReceiptData = Callable[[list[dict[str, Any]], str], dict[str, Any]]

LIFE_SAVE_FAIL_ACK = "That didn't save — try once more."

__all__ = [
    "fast_path_habit",
    "try_write_fast_path",
]


def fast_path_habit(
    session: Any,
    sink: Any,
    history: list[Any],
    receipts: list[dict[str, Any]],
    *,
    verb: str,
    tool: str,
    args: dict[str, Any],
    execute_tool: ExecuteTool,
) -> tuple[str | None, str | None]:
    utterance = str(args.get("utterance") or args.get("name") or args.get("body") or "").strip()
    if not utterance:
        return "missing_life_receipt", None

    parsed = build_habit_tick_args(utterance, verb=verb)
    if parsed.get("needs_confirm"):
        confirm_tool = str(parsed.get("confirm_tool") or tool)
        tick_args = parsed.get("args")
        if not isinstance(tick_args, dict):
            return "missing_life_receipt", LIFE_SAVE_FAIL_ACK
        execute_tool(
            session,
            sink,
            history,
            receipts,
            tool=confirm_tool,
            args=tick_args,
            call_id=f"{verb}-confirm-probe",
        )
        last = receipts[-1] if receipts else {}
        if parsed.get("create"):
            return "pack_fast_path", CONFIRM_HABIT_CREATE
        if last.get("needs_confirm") or (last.get("data") or {}).get("needs_confirm"):
            return "pack_fast_path", CONFIRM_HABIT
        if last.get("ok"):
            return "pack_fast_path", "Habit logged."
        return "missing_life_receipt", LIFE_SAVE_FAIL_ACK
    if not parsed.get("ok") or not parsed.get("args"):
        return "missing_life_receipt", LIFE_SAVE_FAIL_ACK
    execute_tool(
        session,
        sink,
        history,
        receipts,
        tool=tool,
        args=parsed["args"],
        call_id=f"{verb}-fast-path",
    )
    last = receipts[-1] if receipts else {}
    if not last.get("ok"):
        data = last.get("data") if isinstance(last.get("data"), dict) else {}
        reason = data.get("reason")
        if reason == "already_done":
            return "pack_fast_path", speak_habit_tick(data, verb=verb)
        return "missing_life_receipt", speak_habit_tick(data or {"ok": False}, verb=verb)
    execute_tool(
        session,
        sink,
        history,
        receipts,
        tool="life_habit_status",
        args={},
        call_id=f"{verb}-status",
    )
    write_data = last.get("data") if isinstance(last.get("data"), dict) else {}
    return "pack_fast_path", speak_habit_tick(
        {"ok": True, **write_data}, verb=verb
    )


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
    """Force habit_do / habit_miss before cortex; pack_hint optional."""
    if session.mode != "agent":
        return None, None
    args = {"utterance": user_text, "name": user_text}
    if is_habit_do_utterance(user_text):
        return fast_path_habit(
            session,
            sink,
            history,
            receipts,
            verb="habit_do",
            tool="life_habit_do",
            args=args,
            execute_tool=execute_tool,
        )
    if is_habit_miss_utterance(user_text):
        return fast_path_habit(
            session,
            sink,
            history,
            receipts,
            verb="habit_miss",
            tool="life_habit_miss",
            args=args,
            execute_tool=execute_tool,
        )
    return None, None
