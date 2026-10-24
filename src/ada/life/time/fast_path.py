"""Time write fast-paths — start/stop before cortex."""

from __future__ import annotations

from typing import Any, Callable

from ada.life.time.doors import is_time_start_utterance
from ada.life.time.intent import map_time_intent
from ada.life.time.speak import speak_time_start, speak_time_stop

ExecuteTool = Callable[..., None]
ReceiptData = Callable[[list[dict[str, Any]], str], dict[str, Any]]


def fast_path_time_start(
    session: Any,
    sink: Any,
    history: list[Any],
    receipts: list[dict[str, Any]],
    args: dict[str, Any],
    *,
    execute_tool: ExecuteTool,
    receipt_data: ReceiptData,
) -> tuple[str | None, str | None]:
    kind = args.get("kind")
    if not kind:
        return None, None
    start_args: dict[str, Any] = {"kind": str(kind)}
    if args.get("label") is not None:
        start_args["label"] = args.get("label")
    execute_tool(
        session,
        sink,
        history,
        receipts,
        tool="life_time_start",
        args=start_args,
        call_id="time-start-fast-path",
    )
    execute_tool(
        session,
        sink,
        history,
        receipts,
        tool="life_time_status",
        args={},
        call_id="time-status",
    )
    return "pack_fast_path", speak_time_start(receipt_data(receipts, "life_time_start"))


def fast_path_time_stop(
    session: Any,
    sink: Any,
    history: list[Any],
    receipts: list[dict[str, Any]],
    *,
    execute_tool: ExecuteTool,
    receipt_data: ReceiptData,
) -> tuple[str | None, str | None]:
    execute_tool(
        session,
        sink,
        history,
        receipts,
        tool="life_time_stop",
        args={},
        call_id="time-stop-fast-path",
    )
    execute_tool(
        session,
        sink,
        history,
        receipts,
        tool="life_time_status",
        args={},
        call_id="time-status",
    )
    return "pack_fast_path", speak_time_stop(receipt_data(receipts, "life_time_stop"))


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
    """Force time_start before cortex even if pack_hint is missing/wrong."""
    if session.mode != "agent":
        return None, None
    if is_time_start_utterance(user_text):
        args = map_time_intent(user_text)
        return fast_path_time_start(
            session,
            sink,
            history,
            receipts,
            args,
            execute_tool=execute_tool,
            receipt_data=receipt_data,
        )
    return None, None
