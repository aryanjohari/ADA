"""People fast-paths — six verbs before cortex; writes Agent-only, reads Observe+Agent."""

from __future__ import annotations

from typing import Any, Callable

from ada.harness.mouth import CONFIRM_PERSON, CONFIRM_PERSON_CREATE
from ada.life.people.doors import (
    alias_set_body,
    birthday_set_body,
    is_alias_set_utterance,
    is_birthday_set_utterance,
    is_people_remind_utterance,
    is_person_capture_utterance,
    is_person_note_utterance,
    is_who_is_utterance,
    person_note_body,
    who_is_mention,
)
from ada.life.people.spine import (
    build_birthday_args,
    build_capture_args,
    build_note_args,
)

ExecuteTool = Callable[..., None]
ReceiptData = Callable[[list[dict[str, Any]], str], dict[str, Any]]
FastPathRead = Callable[..., tuple[str | None, str | None]]
FastPathConfirmBound = Callable[..., tuple[str | None, str | None]]

LIFE_SAVE_FAIL_ACK = "That didn't save — try once more."


def fast_path_people_write(
    session: Any,
    sink: Any,
    history: list[Any],
    receipts: list[dict[str, Any]],
    *,
    verb: str,
    tool: str,
    args: dict[str, Any],
    execute_tool: ExecuteTool,
    life_save_fail_ack: str = LIFE_SAVE_FAIL_ACK,
) -> tuple[str | None, str | None]:
    if verb == "person_capture":
        utterance = str(args.get("utterance") or args.get("body") or "").strip()
        if not utterance:
            return "missing_life_receipt", None
        parsed = build_capture_args(utterance)
        if parsed.get("needs_confirm"):
            confirm_tool = str(parsed.get("confirm_tool") or tool)
            tick_args = parsed.get("args")
            if not isinstance(tick_args, dict):
                return "missing_life_receipt", life_save_fail_ack
            execute_tool(
                session,
                sink,
                history,
                receipts,
                tool=confirm_tool,
                args=tick_args,
                call_id="person-capture-confirm-probe",
            )
            last = receipts[-1] if receipts else {}
            if parsed.get("create"):
                return "pack_fast_path", CONFIRM_PERSON_CREATE
            if last.get("needs_confirm") or (last.get("data") or {}).get("needs_confirm"):
                return "pack_fast_path", CONFIRM_PERSON
            if last.get("ok"):
                return "pack_fast_path", "Person saved."
            return "missing_life_receipt", life_save_fail_ack
        if not parsed.get("ok") or not parsed.get("args"):
            return "missing_life_receipt", None
        execute_tool(
            session,
            sink,
            history,
            receipts,
            tool=tool,
            args=parsed["args"],
            call_id="person-capture-fast-path",
        )
        last = receipts[-1] if receipts else {}
        if not last.get("ok"):
            return "missing_life_receipt", None
        return "pack_fast_path", "Person saved."

    if verb == "birthday_set":
        body = str(args.get("body") or args.get("utterance") or "").strip()
        if not body:
            return "missing_life_receipt", None
        parsed = build_birthday_args(body)
        if not parsed.get("ok"):
            return "missing_life_receipt", None
        execute_tool(
            session,
            sink,
            history,
            receipts,
            tool=tool,
            args=parsed["args"],
            call_id="birthday-set-fast-path",
        )
        last = receipts[-1] if receipts else {}
        if not last.get("ok"):
            return "missing_life_receipt", None
        return "pack_fast_path", "Birthday saved."

    if verb == "person_note":
        text = str(args.get("text") or "").strip()
        mention = str(args.get("mention") or "").strip()
        blob = " ".join(p for p in (mention, text) if p).strip() or text
        if not blob:
            return "missing_life_receipt", None
        parsed = build_note_args(blob)
        if parsed.get("needs_confirm"):
            confirm_tool = str(parsed.get("confirm_tool") or tool)
            note_args = parsed.get("args")
            if not isinstance(note_args, dict):
                return "missing_life_receipt", life_save_fail_ack
            execute_tool(
                session,
                sink,
                history,
                receipts,
                tool=confirm_tool,
                args=note_args,
                call_id="person-note-confirm-probe",
            )
            last = receipts[-1] if receipts else {}
            if last.get("needs_confirm") or (last.get("data") or {}).get("needs_confirm"):
                return "pack_fast_path", CONFIRM_PERSON
            if last.get("ok"):
                return "pack_fast_path", "Note saved."
            return "missing_life_receipt", life_save_fail_ack
        if not parsed.get("ok") or not parsed.get("args"):
            return "missing_life_receipt", None
        execute_tool(
            session,
            sink,
            history,
            receipts,
            tool=tool,
            args=parsed["args"],
            call_id="person-note-fast-path",
        )
        last = receipts[-1] if receipts else {}
        if not last.get("ok"):
            return "missing_life_receipt", None
        return "pack_fast_path", "Note saved."

    return None, None


def try_people_fast_path(
    session: Any,
    sink: Any,
    history: list[Any],
    receipts: list[dict[str, Any]],
    user_text: str,
    *,
    execute_tool: ExecuteTool,
    receipt_data: ReceiptData,
    fast_path_read: FastPathRead,
    fast_path_confirm_bound: FastPathConfirmBound,
    life_save_fail_ack: str = LIFE_SAVE_FAIL_ACK,
) -> tuple[str | None, str | None]:
    """Force the six people verbs before cortex; pack_hint optional.

    Writes Agent-only. Reads Observe+Agent. After meal/lift/gym/time/habit/due.
    """
    _ = receipt_data
    if is_person_capture_utterance(user_text):
        if session.mode != "agent":
            return None, None
        return fast_path_people_write(
            session,
            sink,
            history,
            receipts,
            verb="person_capture",
            tool="life_person_capture",
            args={"utterance": user_text},
            execute_tool=execute_tool,
            life_save_fail_ack=life_save_fail_ack,
        )
    if is_person_note_utterance(user_text):
        if session.mode != "agent":
            return None, None
        return fast_path_people_write(
            session,
            sink,
            history,
            receipts,
            verb="person_note",
            tool="life_person_note",
            args={"text": person_note_body(user_text)},
            execute_tool=execute_tool,
            life_save_fail_ack=life_save_fail_ack,
        )
    if is_birthday_set_utterance(user_text):
        if session.mode != "agent":
            return None, None
        return fast_path_people_write(
            session,
            sink,
            history,
            receipts,
            verb="birthday_set",
            tool="life_birthday_set",
            args={"body": birthday_set_body(user_text)},
            execute_tool=execute_tool,
            life_save_fail_ack=life_save_fail_ack,
        )
    if is_alias_set_utterance(user_text):
        if session.mode != "agent":
            return None, None
        return fast_path_confirm_bound(
            session,
            sink,
            history,
            receipts,
            verb="alias_set",
            tool="life_alias_set",
            args={"utterance": alias_set_body(user_text)},
        )
    if session.mode not in ("observe", "agent"):
        return None, None
    if is_who_is_utterance(user_text):
        session.pack_hint = {
            "verb": "who_is",
            "tool": "life_who_is",
            "args": {"mention": who_is_mention(user_text)},
        }
        return fast_path_read(session, sink, history, receipts)
    if is_people_remind_utterance(user_text):
        session.pack_hint = {
            "verb": "people_remind",
            "tool": "life_people_remind",
            "args": {},
        }
        return fast_path_read(session, sink, history, receipts)
    return None, None
