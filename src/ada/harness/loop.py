"""ReAct multi-step tool loop — observations ground body claims."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from ada.cortex.adapter import CortexAdapter, CortexTurn
from ada.cortex.charter import (
    CHILL_SESSION_OVERRIDE,
    build_system_charter,
    merge_pack_hint_into_charter,
)
from ada.cortex.cost import estimate_usd
from ada.cortex.gemini import observation_to_content, user_content
from ada.harness.mouth import (
    CONFIRM_LINE,
    CONFIRM_PERSON,
    apply_register_pass,
)
from ada.harness.pack_router import (
    ADMIN_WRITE_VERBS,
    CONFIRM_BOUND_VERBS,
    READ_PACK_VERBS,
    is_due_add_utterance,
    is_due_done_utterance,
    is_incomplete_lift_utterance,
    is_lift_log_utterance,
    is_meal_log_utterance,
    is_remind_utterance,
    meal_log_fast_path_args,
)
from ada.harness.plan_artifact import parse_plan_from_assistant
from ada.harness.session import ChatSession
from ada.harness.stream_events import CallbackSink, NullSink, StreamSink
from ada.life.food.fast_path import (
    fast_path_barcode,
    fast_path_meal,
    fast_path_meal_draft_add,
    fast_path_meal_draft_cancel,
    fast_path_meal_draft_save,
    fast_path_meal_draft_start,
    fast_path_meal_preset_log,
)
from ada.life.food.speak import (
    MEAL_EMPTY_MACROS_ACK,
    honest_meal_mouth as _honest_meal_mouth,
    speak_nutrition_day as _speak_nutrition_day,
    speak_nutrition_week as _speak_nutrition_week,
)
from ada.life.gym.fast_path import (
    fast_path_gym_end,
    fast_path_gym_start,
    fast_path_lift,
)
from ada.life.gym.speak import (
    speak_gym_day as _speak_gym_day,
    speak_gym_end as _speak_gym_end,
    speak_gym_status as _speak_gym_status,
    speak_gym_week as _speak_gym_week,
    speak_lift_log as _speak_lift_log,
)
from ada.life.habits.fast_path import fast_path_habit
from ada.life.habits.speak import (
    speak_habit_day as _speak_habit_day,
    speak_habit_status as _speak_habit_status,
    speak_habit_tick as _speak_habit_tick,
    speak_habit_week as _speak_habit_week,
)
from ada.life.people.speak import (
    speak_people_remind as _speak_people_remind,
    speak_who_is as _speak_who_is,
)
from ada.life.registry import (
    FastPathCtx,
    try_food_draft_divert,
    try_gym_write,
    try_habit_write,
    try_people_fast_path,
    try_time_write,
)
from ada.life.time.fast_path import fast_path_time_start, fast_path_time_stop
from ada.life.time.speak import (
    speak_time_day as _speak_time_day,
    speak_time_start as _speak_time_start,
    speak_time_status as _speak_time_status,
    speak_time_stop as _speak_time_stop,
    speak_time_week as _speak_time_week,
)

# Narrow chill cues (M05) — sticky for the session once matched.
_CHILL_CUE = re.compile(
    r"\b(chill|softer|stop roasting|tone it down|less roast)\b",
    re.IGNORECASE,
)

_FACT_TOOLS_BLOCKED_ON_LIFE_PACK = frozenset(
    {"memory_facts_append", "memory_facts_propose_edit"}
)

# Honest ack when Gemini returns no text and no tools (not a retry, not a mouth).
EMPTY_CORTEX_ACK = "No reply that turn. Try once more."
LIFE_SAVE_FAIL_ACK = "That didn't save — try once more."


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
    plan: dict[str, Any] | None = None


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


def _pack_life_tool(hint: dict[str, Any] | None) -> str:
    return str((hint or {}).get("tool") or "")


def _model_tool_blocked(session: ChatSession, tool_name: str) -> str | None:
    if session.mode == "agent":
        if tool_name == "life_meal_log":
            return "meal writes use meal_spine — operator Confirm on card"
        gateway = session.gateway
        turn_text = str(getattr(gateway, "turn_user_text", None) or "")
        if tool_name == "life_food_search" and is_meal_log_utterance(turn_text):
            return "meal_spine owns food search on log turns"
        if is_incomplete_lift_utterance(turn_text) and tool_name in {
            "life_lift_log",
            "life_gym_start",
        }:
            return "incomplete lift — ask, no session, no row"
        if tool_name == "life_lift_log" and is_lift_log_utterance(turn_text):
            return "gym writes use gym_spine — spine owns sets[]"

    hint = session.pack_hint or {}
    verb = str(hint.get("verb") or "")
    pack_tool = _pack_life_tool(hint)
    blocks_facts = (
        pack_tool.startswith("life_")
        or verb in READ_PACK_VERBS
        or verb in ADMIN_WRITE_VERBS
    )
    if blocks_facts and tool_name in _FACT_TOOLS_BLOCKED_ON_LIFE_PACK:
        route = pack_tool or verb or "life capture"
        return (
            f"pack_hint routes this turn to {route}; "
            f"use {route} (life capture) — not {tool_name}"
        )
    return None


def _execute_tool(
    session: ChatSession,
    sink: StreamSink,
    history: list[Any],
    receipts: list[dict[str, Any]],
    *,
    tool: str,
    args: dict[str, Any],
    call_id: str | None = None,
) -> None:
    gateway = session.gateway
    assert gateway is not None
    # Draft scratch is keyed by HUD/chat session — never trust model-invented ids
    # (phone f024fb03… cortex used session_id=meal_draft_1 → divert miss).
    if tool.startswith("life_meal_draft_"):
        args = dict(args or {})
        args["session_id"] = session.session_id
    session.writer.append("tool_call", {"tool": tool, "args": args})
    sink.emit("tool_call_started", {"tool": tool, "args": args})
    result = gateway.execute(tool, args)
    obs = result.as_observation()
    receipts.append(obs)
    if result.outcome == "denied":
        session.writer.append("tool_denied", obs)
    else:
        session.writer.append("tool_result", obs)
    finished: dict[str, Any] = {
        "tool": tool,
        "ok": result.ok,
        "receipt_id": result.receipt_id,
        "outcome": result.outcome,
        "needs_confirm": bool(result.needs_confirm),
        "args": result.args,
    }
    if result.needs_confirm:
        finished["pending_id"] = result.receipt_id
        # Surface resolve on Confirm card / pending stash (meal multi-slot).
        data = result.data if isinstance(result.data, dict) else {}
        card_args = dict(result.args or {})
        if data.get("resolve") and not card_args.get("resolve"):
            card_args["resolve"] = data["resolve"]
        if data.get("candidates") and not card_args.get("candidates"):
            card_args["candidates"] = data["candidates"]
        if data.get("proposed_display_name") and not card_args.get("proposed_display_name"):
            card_args["proposed_display_name"] = data["proposed_display_name"]
        if data.get("display_name") and not card_args.get("display_name"):
            card_args["display_name"] = data["display_name"]
        if data.get("lines") and not card_args.get("lines"):
            card_args["lines"] = data["lines"]
        if data.get("meal_slot") is not None and card_args.get("meal_slot") is None:
            card_args["meal_slot"] = data.get("meal_slot")
        if data.get("save_favorite") is not None:
            card_args["save_favorite"] = data.get("save_favorite")
        finished["args"] = card_args
        # Keep observation.args aligned so HUD pending_confirms stashes resolve.
        obs["args"] = card_args
        receipts[-1] = obs
    sink.emit("tool_call_finished", finished)
    if tool == "life_nutrition_day" and result.ok and isinstance(obs.get("data"), dict):
        sink.emit(
            "view_open",
            {
                "panel_kind": "nutrition_day",
                "receipt_id": result.receipt_id,
                "tool": tool,
                "data": obs.get("data") or {},
                "speak": _speak_nutrition_day(obs.get("data") or {}),
            },
        )
    history.append(observation_to_content(obs, call_id=call_id or tool))


def _fast_path_meal(
    session: ChatSession,
    sink: StreamSink,
    history: list[Any],
    receipts: list[dict[str, Any]],
    args: dict[str, Any],
) -> tuple[str | None, str | None]:
    return fast_path_meal(
        session,
        sink,
        history,
        receipts,
        args,
        execute_tool=_execute_tool,
        receipt_data=_receipt_data,
    )


def _fast_path_time_start(
    session: ChatSession,
    sink: StreamSink,
    history: list[Any],
    receipts: list[dict[str, Any]],
    args: dict[str, Any],
) -> tuple[str | None, str | None]:
    return fast_path_time_start(
        session,
        sink,
        history,
        receipts,
        args,
        execute_tool=_execute_tool,
        receipt_data=_receipt_data,
    )


def _fast_path_time_stop(
    session: ChatSession,
    sink: StreamSink,
    history: list[Any],
    receipts: list[dict[str, Any]],
) -> tuple[str | None, str | None]:
    return fast_path_time_stop(
        session,
        sink,
        history,
        receipts,
        execute_tool=_execute_tool,
        receipt_data=_receipt_data,
    )


def _fast_path_lift(
    session: ChatSession,
    sink: StreamSink,
    history: list[Any],
    receipts: list[dict[str, Any]],
    args: dict[str, Any],
) -> tuple[str | None, str | None]:
    return fast_path_lift(
        session,
        sink,
        history,
        receipts,
        args,
        execute_tool=_execute_tool,
        receipt_data=_receipt_data,
    )


def _fast_path_capture(
    session: ChatSession,
    sink: StreamSink,
    history: list[Any],
    receipts: list[dict[str, Any]],
    args: dict[str, Any],
) -> tuple[str | None, str | None]:
    text = str(args.get("text") or "").strip()
    if not text:
        return None, None
    _execute_tool(
        session,
        sink,
        history,
        receipts,
        tool="life_capture",
        args={"text": text},
        call_id="capture-fast-path",
    )
    return "pack_fast_path", "Captured that."


def _receipt_data(receipts: list[dict[str, Any]], tool: str) -> dict[str, Any]:
    for row in reversed(receipts):
        if str(row.get("tool") or "") == tool:
            data = row.get("data")
            return data if isinstance(data, dict) else {}
    return {}


def _fast_path_meal_draft_start(
    session: ChatSession,
    sink: StreamSink,
    history: list[Any],
    receipts: list[dict[str, Any]],
) -> tuple[str | None, str | None]:
    return fast_path_meal_draft_start(
        session,
        sink,
        history,
        receipts,
        execute_tool=_execute_tool,
        receipt_data=_receipt_data,
    )


def _fast_path_meal_draft_add(
    session: ChatSession,
    sink: StreamSink,
    history: list[Any],
    receipts: list[dict[str, Any]],
    utterance: str,
) -> tuple[str | None, str | None]:
    return fast_path_meal_draft_add(
        session,
        sink,
        history,
        receipts,
        utterance,
        execute_tool=_execute_tool,
        receipt_data=_receipt_data,
    )


def _fast_path_meal_draft_save(
    session: ChatSession,
    sink: StreamSink,
    history: list[Any],
    receipts: list[dict[str, Any]],
    args: dict[str, Any],
) -> tuple[str | None, str | None]:
    return fast_path_meal_draft_save(
        session,
        sink,
        history,
        receipts,
        args,
        execute_tool=_execute_tool,
        receipt_data=_receipt_data,
    )


def _fast_path_meal_draft_cancel(
    session: ChatSession,
    sink: StreamSink,
    history: list[Any],
    receipts: list[dict[str, Any]],
) -> tuple[str | None, str | None]:
    return fast_path_meal_draft_cancel(
        session,
        sink,
        history,
        receipts,
        execute_tool=_execute_tool,
        receipt_data=_receipt_data,
    )


def _fast_path_meal_preset_log(
    session: ChatSession,
    sink: StreamSink,
    history: list[Any],
    receipts: list[dict[str, Any]],
    args: dict[str, Any],
) -> tuple[str | None, str | None]:
    return fast_path_meal_preset_log(
        session,
        sink,
        history,
        receipts,
        args,
        execute_tool=_execute_tool,
        receipt_data=_receipt_data,
    )


def _fast_path_barcode(
    session: ChatSession,
    sink: StreamSink,
    history: list[Any],
    receipts: list[dict[str, Any]],
    args: dict[str, Any],
) -> tuple[str | None, str | None]:
    return fast_path_barcode(
        session,
        sink,
        history,
        receipts,
        args,
        execute_tool=_execute_tool,
        receipt_data=_receipt_data,
    )


def _maybe_open_draft_divert(
    session: ChatSession,
    sink: StreamSink,
    history: list[Any],
    receipts: list[dict[str, Any]],
    user_text: str,
) -> tuple[str | None, str | None]:
    return try_food_draft_divert(
        FastPathCtx(
            session=session,
            sink=sink,
            history=history,
            receipts=receipts,
            user_text=user_text,
            execute_tool=_execute_tool,
            receipt_data=_receipt_data,
        )
    )


def _speak_due_list(data: dict[str, Any]) -> str:
    loops = data.get("loops") if isinstance(data.get("loops"), list) else []
    count = data.get("count")
    n = int(count) if isinstance(count, int) else len(loops)
    return f"{n} open due(s)."


def _fast_path_read(
    session: ChatSession,
    sink: StreamSink,
    history: list[Any],
    receipts: list[dict[str, Any]],
) -> tuple[str | None, str | None]:
    hint = session.pack_hint or {}
    verb = str(hint.get("verb") or "")
    if verb == "life_status":
        return _fast_path_life_status(session, sink, history, receipts)
    tool = _pack_life_tool(hint)
    args = dict(hint.get("args") or {}) if isinstance(hint.get("args"), dict) else {}
    if tool == "memory_open_loops_list":
        args.setdefault("kind", "todo")
        args.setdefault("status", "open")
    if not tool:
        return "missing_life_receipt", None
    _execute_tool(
        session,
        sink,
        history,
        receipts,
        tool=tool,
        args=args,
        call_id=f"{verb or tool}-fast-path",
    )
    last = receipts[-1] if receipts else {}
    if not last.get("ok"):
        return "missing_life_receipt", None
    data = last.get("data") if isinstance(last.get("data"), dict) else {}
    if verb == "nutrition_day" or tool == "life_nutrition_day":
        speech = _speak_nutrition_day(data)
    elif verb == "nutrition_week" or tool == "life_nutrition_week":
        speech = _speak_nutrition_week(data)
    elif verb == "time_status" or tool == "life_time_status":
        speech = _speak_time_status(data)
    elif verb == "time_day" or tool == "life_time_day":
        speech = _speak_time_day(data)
    elif verb == "time_week" or tool == "life_time_week":
        speech = _speak_time_week(data)
    elif verb == "due_list" or tool == "memory_open_loops_list":
        speech = _speak_due_list(data)
    elif verb == "gym_status" or tool == "life_gym_status":
        speech = _speak_gym_status(data)
    elif verb == "gym_day" or tool == "life_gym_day":
        speech = _speak_gym_day(data)
    elif verb == "gym_week" or tool == "life_gym_week":
        speech = _speak_gym_week(data)
    elif verb == "streak_show" or tool == "life_habit_status":
        speech = _speak_habit_status(data)
    elif verb == "habit_day" or tool == "life_habit_day":
        speech = _speak_habit_day(data)
    elif verb == "habit_week" or tool == "life_habit_week":
        speech = _speak_habit_week(data)
    elif verb == "who_is" or tool == "life_who_is":
        speech = _speak_who_is(data)
    elif verb == "people_remind" or tool == "life_people_remind":
        speech = _speak_people_remind(data)
    else:
        speech = "Here's what I found."
    return "pack_fast_path", speech


def _fast_path_life_status(
    session: ChatSession,
    sink: StreamSink,
    history: list[Any],
    receipts: list[dict[str, Any]],
) -> tuple[str | None, str | None]:
    hint = session.pack_hint or {}
    preferred = hint.get("preferred_tools")
    tools = (
        [str(t) for t in preferred]
        if isinstance(preferred, list) and preferred
        else ["life_nutrition_day", "life_time_status", "memory_open_loops_list"]
    )
    for tool in tools:
        args: dict[str, Any] = {}
        if tool == "memory_open_loops_list":
            args = {"kind": "todo", "status": "open"}
        _execute_tool(
            session,
            sink,
            history,
            receipts,
            tool=tool,
            args=args,
            call_id=f"life-status-{tool}",
        )
    if not any(r.get("ok") for r in receipts):
        return "missing_life_receipt", None
    parts = [
        _speak_nutrition_day(_receipt_data(receipts, "life_nutrition_day")),
        _speak_time_status(_receipt_data(receipts, "life_time_status")),
        _speak_due_list(_receipt_data(receipts, "memory_open_loops_list")),
    ]
    return "pack_fast_path", " ".join(parts)


def _fast_path_due(
    session: ChatSession,
    sink: StreamSink,
    history: list[Any],
    receipts: list[dict[str, Any]],
    *,
    verb: str | None = None,
    utterance: str | None = None,
) -> tuple[str | None, str | None]:
    hint = session.pack_hint or {}
    verb = str(verb or hint.get("verb") or "")
    args = hint.get("args") if isinstance(hint.get("args"), dict) else {}
    utterance = str(
        utterance
        or (args or {}).get("utterance")
        or (args or {}).get("text")
        or hint.get("body")
        or ""
    ).strip()
    if not utterance:
        return "missing_life_receipt", None
    from ada.harness.due_spine import build_due_upsert_args

    parsed = build_due_upsert_args(utterance, verb=verb)
    if not parsed.get("ok") or not parsed.get("args"):
        return "missing_life_receipt", None
    upsert_args = dict(parsed["args"])
    title = str(parsed.get("title") or upsert_args.get("text") or "")
    from ada.life.people.spine import resolve_mention_for_due

    person_hit = resolve_mention_for_due(title)
    if person_hit.get("ok"):
        upsert_args["people_ids"] = [person_hit["person_id"]]
    _execute_tool(
        session,
        sink,
        history,
        receipts,
        tool="memory_open_loops_upsert",
        args=upsert_args,
        call_id=f"{verb}-fast-path",
    )
    upsert = receipts[-1] if receipts else {}
    if not upsert.get("ok"):
        return "missing_life_receipt", None
    _execute_tool(
        session,
        sink,
        history,
        receipts,
        tool="memory_open_loops_list",
        args={"kind": "todo", "status": "open"},
        call_id=f"{verb}-list",
    )
    return "pack_fast_path", f"{verb.replace('_', ' ')} logged."


def _fast_path_gym_start(
    session: ChatSession,
    sink: StreamSink,
    history: list[Any],
    receipts: list[dict[str, Any]],
) -> tuple[str | None, str | None]:
    return fast_path_gym_start(
        session, sink, history, receipts, execute_tool=_execute_tool
    )


def _fast_path_gym_end(
    session: ChatSession,
    sink: StreamSink,
    history: list[Any],
    receipts: list[dict[str, Any]],
) -> tuple[str | None, str | None]:
    return fast_path_gym_end(
        session, sink, history, receipts, execute_tool=_execute_tool
    )


def _maybe_gym_write_fast_path(
    session: ChatSession,
    sink: StreamSink,
    history: list[Any],
    receipts: list[dict[str, Any]],
    user_text: str,
) -> tuple[str | None, str | None]:
    """Force gym start/end/lift before cortex even if pack_hint is missing/wrong."""
    return try_gym_write(
        FastPathCtx(
            session=session,
            sink=sink,
            history=history,
            receipts=receipts,
            user_text=user_text,
            execute_tool=_execute_tool,
            receipt_data=_receipt_data,
        )
    )


def _maybe_time_write_fast_path(
    session: ChatSession,
    sink: StreamSink,
    history: list[Any],
    receipts: list[dict[str, Any]],
    user_text: str,
) -> tuple[str | None, str | None]:
    """Force time_start before cortex even if pack_hint is missing/wrong."""
    return try_time_write(
        FastPathCtx(
            session=session,
            sink=sink,
            history=history,
            receipts=receipts,
            user_text=user_text,
            execute_tool=_execute_tool,
            receipt_data=_receipt_data,
        )
    )


def _maybe_habit_write_fast_path(
    session: ChatSession,
    sink: StreamSink,
    history: list[Any],
    receipts: list[dict[str, Any]],
    user_text: str,
) -> tuple[str | None, str | None]:
    """Force habit_do / habit_miss before cortex; pack_hint optional."""
    return try_habit_write(
        FastPathCtx(
            session=session,
            sink=sink,
            history=history,
            receipts=receipts,
            user_text=user_text,
            execute_tool=_execute_tool,
            receipt_data=_receipt_data,
        )
    )


def _maybe_due_write_fast_path(
    session: ChatSession,
    sink: StreamSink,
    history: list[Any],
    receipts: list[dict[str, Any]],
    user_text: str,
) -> tuple[str | None, str | None]:
    """Force due_add / remind / due_done before cortex; pack_hint optional."""
    if session.mode != "agent":
        return None, None
    if is_due_done_utterance(user_text):
        return _fast_path_due(
            session, sink, history, receipts, verb="due_done", utterance=user_text
        )
    if is_remind_utterance(user_text):
        return _fast_path_due(
            session, sink, history, receipts, verb="remind", utterance=user_text
        )
    if is_due_add_utterance(user_text):
        return _fast_path_due(
            session, sink, history, receipts, verb="due_add", utterance=user_text
        )
    return None, None


def _maybe_people_fast_path(
    session: ChatSession,
    sink: StreamSink,
    history: list[Any],
    receipts: list[dict[str, Any]],
    user_text: str,
) -> tuple[str | None, str | None]:
    """Force the six people verbs before cortex; pack_hint optional."""
    return try_people_fast_path(
        FastPathCtx(
            session=session,
            sink=sink,
            history=history,
            receipts=receipts,
            user_text=user_text,
            execute_tool=_execute_tool,
            receipt_data=_receipt_data,
        ),
        fast_path_read=_fast_path_read,
        fast_path_confirm_bound=_fast_path_confirm_bound,
        life_save_fail_ack=LIFE_SAVE_FAIL_ACK,
    )


def _fast_path_habit(
    session: ChatSession,
    sink: StreamSink,
    history: list[Any],
    receipts: list[dict[str, Any]],
    *,
    verb: str,
    tool: str,
    args: dict[str, Any],
) -> tuple[str | None, str | None]:
    return fast_path_habit(
        session,
        sink,
        history,
        receipts,
        verb=verb,
        tool=tool,
        args=args,
        execute_tool=_execute_tool,
    )


def _fast_path_people_write(
    session: ChatSession,
    sink: StreamSink,
    history: list[Any],
    receipts: list[dict[str, Any]],
    *,
    verb: str,
    tool: str,
    args: dict[str, Any],
) -> tuple[str | None, str | None]:
    from ada.life.people.fast_path import fast_path_people_write

    return fast_path_people_write(
        session,
        sink,
        history,
        receipts,
        verb=verb,
        tool=tool,
        args=args,
        execute_tool=_execute_tool,
        life_save_fail_ack=LIFE_SAVE_FAIL_ACK,
    )


def _fast_path_confirm_bound(
    session: ChatSession,
    sink: StreamSink,
    history: list[Any],
    receipts: list[dict[str, Any]],
    *,
    verb: str,
    tool: str,
    args: dict[str, Any],
) -> tuple[str | None, str | None]:
    probe_args = dict(args)
    probe_args.setdefault("confirmed", False)
    utterance = str(args.get("utterance") or args.get("body") or "").strip()
    if verb == "alias_set" and utterance:
        probe_args["utterance"] = utterance
    _execute_tool(
        session,
        sink,
        history,
        receipts,
        tool=tool,
        args=probe_args,
        call_id=f"{verb}-confirm-probe",
    )
    last = receipts[-1] if receipts else {}
    if last.get("needs_confirm") or (last.get("data") or {}).get("needs_confirm"):
        if verb in {"alias_set", "kin_link", "person_update"}:
            return "pack_fast_path", CONFIRM_PERSON
        return "pack_fast_path", CONFIRM_LINE
    if last.get("ok"):
        return "pack_fast_path", f"{verb.replace('_', ' ')} saved."
    return "missing_life_receipt", None


def _maybe_pack_fast_path(
    session: ChatSession,
    sink: StreamSink,
    history: list[Any],
    receipts: list[dict[str, Any]],
) -> tuple[str | None, str | None]:
    """Deterministic pack executor: reads in Observe+Agent; writes Agent-only."""
    hint = session.pack_hint or {}
    verb = str(hint.get("verb") or "")
    tool = _pack_life_tool(hint)
    args = hint.get("args") if isinstance(hint.get("args"), dict) else {}

    if verb in READ_PACK_VERBS:
        if session.mode not in ("observe", "agent"):
            return None, None
        return _fast_path_read(session, sink, history, receipts)

    if session.mode != "agent":
        return None, None

    if verb in ADMIN_WRITE_VERBS:
        return _fast_path_due(session, sink, history, receipts)

    if verb in CONFIRM_BOUND_VERBS:
        return _fast_path_confirm_bound(
            session, sink, history, receipts, verb=verb, tool=tool, args=args or {}
        )

    if verb in {"habit_do", "habit_miss", "routine_run"}:
        return _fast_path_habit(
            session, sink, history, receipts, verb=verb, tool=tool, args=args or {}
        )

    if verb == "gym_start":
        return _fast_path_gym_start(session, sink, history, receipts)

    if verb == "gym_end":
        return _fast_path_gym_end(session, sink, history, receipts)

    if verb in {"person_capture", "birthday_set", "person_note"}:
        return _fast_path_people_write(
            session, sink, history, receipts, verb=verb, tool=tool, args=args or {}
        )

    if not tool.startswith("life_") or not isinstance(args, dict):
        return None, None

    if verb == "meal_draft_start" or tool == "life_meal_draft_start":
        return _fast_path_meal_draft_start(session, sink, history, receipts)
    if verb == "meal_draft_save" or tool == "life_meal_draft_save":
        return _fast_path_meal_draft_save(session, sink, history, receipts, args)
    if verb == "meal_draft_cancel" or tool == "life_meal_draft_cancel":
        return _fast_path_meal_draft_cancel(session, sink, history, receipts)
    if verb == "meal_preset_log" or tool == "life_meal_preset_log":
        return _fast_path_meal_preset_log(session, sink, history, receipts, args)
    if verb == "barcode_lookup" or tool == "life_barcode_lookup":
        return _fast_path_barcode(session, sink, history, receipts, args)

    if tool == "life_meal_log":
        return _fast_path_meal(session, sink, history, receipts, args)
    if tool == "life_time_start":
        return _fast_path_time_start(session, sink, history, receipts, args)
    if tool == "life_time_stop":
        return _fast_path_time_stop(session, sink, history, receipts)
    if tool == "life_lift_log":
        return _fast_path_lift(session, sink, history, receipts, args)
    if tool == "life_capture":
        return _fast_path_capture(session, sink, history, receipts, args)
    return None, None


def run_turn(
    session: ChatSession,
    user_text: str,
    adapter: CortexAdapter,
    *,
    system: str | None = None,
    sink: StreamSink | None = None,
    contents: list[Any] | None = None,
    end_session: bool = True,
    input_kind: str | None = None,
    face: str | None = None,
    device_id: str | None = None,
    device_name: str | None = None,
    tailscale_user: str | None = None,
) -> LoopResult:
    """Run one user turn through the ReAct loop.

    Mutates *contents* in place when provided (REPL multi-turn history).
    Set end_session=False for REPL turns; call session.end() on exit.

    HUD stamps optional provenance (face / device_* / tailscale_user).
    CLI leaves those omitted; input_kind defaults to typed.
    """
    sink = sink or NullSink()
    session.ensure_started()
    session.reset_wall_clock()
    kind = (input_kind or "typed").strip().lower()
    if kind not in ("typed", "stt"):
        kind = "typed"
    user_payload: dict[str, Any] = {"text": user_text, "input": kind}
    if face:
        user_payload["face"] = face
    if device_id:
        user_payload["device_id"] = device_id
    if device_name:
        user_payload["device_name"] = device_name
    if tailscale_user:
        user_payload["tailscale_user"] = tailscale_user
    session.writer.append("user", user_payload)
    try:
        from ada.harness.pack_router import route_utterance

        session.pack_hint = route_utterance(user_text)
    except Exception:  # noqa: BLE001
        session.pack_hint = None
    sink.emit("mode_info", {"mode": session.mode})
    sink.emit("session_receipt_path", {"path": str(session.run_path)})

    if detect_chill_cue(user_text):
        session.chill_active = True

    if system is None:
        system_prompt = build_system_charter(
            mode=session.mode,
            chill_active=session.chill_active,
            pack_hint=session.pack_hint,
        )
    else:
        system_prompt = _apply_chill_to_system(system, chill_active=session.chill_active)
        system_prompt = merge_pack_hint_into_charter(system_prompt, session.pack_hint)

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
    gateway.turn_user_text = user_text

    if session.mode == "agent":
        divert_stop, divert_text = _maybe_open_draft_divert(
            session, sink, history, receipts, user_text
        )
        if divert_stop:
            stop_reason = divert_stop
            last_text = divert_text
            if divert_stop == "missing_life_receipt" and not last_text:
                last_text = LIFE_SAVE_FAIL_ACK
            if divert_stop == "pack_fast_path" and divert_text:
                last_text = apply_register_pass(
                    adapter,
                    receipts=receipts,
                    template=divert_text,
                )
            if last_text:
                sink.emit("token_delta", {"text": last_text})
            if end_session:
                session.end(stop_reason=stop_reason, steps=steps)
            return LoopResult(
                text=last_text,
                stop_reason=stop_reason,
                steps=steps,
                tool_receipts=receipts,
                usage_rounds=usage_rounds,
                run_path=str(session.run_path),
                plan=None,
            )

    if session.mode == "agent" and is_meal_log_utterance(user_text):
        meal_args = meal_log_fast_path_args(user_text)
        if meal_args:
            meal_stop, meal_text = _fast_path_meal(
                session, sink, history, receipts, meal_args
            )
            if meal_stop:
                stop_reason = meal_stop
                last_text = meal_text
                if meal_stop == "missing_life_receipt" and not last_text:
                    last_text = LIFE_SAVE_FAIL_ACK
                if meal_stop == "pack_fast_path" and meal_text:
                    last_text = apply_register_pass(
                        adapter,
                        receipts=receipts,
                        template=meal_text,
                    )
                if last_text:
                    sink.emit("token_delta", {"text": last_text})
                if end_session:
                    session.end(stop_reason=stop_reason, steps=steps)
                return LoopResult(
                    text=last_text,
                    stop_reason=stop_reason,
                    steps=steps,
                    tool_receipts=receipts,
                    usage_rounds=usage_rounds,
                    run_path=str(session.run_path),
                    plan=None,
                )

    if session.mode == "agent":
        gym_stop, gym_text = _maybe_gym_write_fast_path(
            session, sink, history, receipts, user_text
        )
        if gym_stop:
            stop_reason = gym_stop
            last_text = gym_text
            if gym_stop == "missing_life_receipt" and not last_text:
                last_text = LIFE_SAVE_FAIL_ACK
            if gym_stop == "pack_fast_path" and gym_text:
                last_text = apply_register_pass(
                    adapter,
                    receipts=receipts,
                    template=gym_text,
                )
            if last_text:
                sink.emit("token_delta", {"text": last_text})
            if end_session:
                session.end(stop_reason=stop_reason, steps=steps)
            return LoopResult(
                text=last_text,
                stop_reason=stop_reason,
                steps=steps,
                tool_receipts=receipts,
                usage_rounds=usage_rounds,
                run_path=str(session.run_path),
                plan=None,
            )

        time_stop, time_text = _maybe_time_write_fast_path(
            session, sink, history, receipts, user_text
        )
        if time_stop:
            stop_reason = time_stop
            last_text = time_text
            if time_stop == "missing_life_receipt" and not last_text:
                last_text = LIFE_SAVE_FAIL_ACK
            if time_stop == "pack_fast_path" and time_text:
                last_text = apply_register_pass(
                    adapter,
                    receipts=receipts,
                    template=time_text,
                )
            if last_text:
                sink.emit("token_delta", {"text": last_text})
            if end_session:
                session.end(stop_reason=stop_reason, steps=steps)
            return LoopResult(
                text=last_text,
                stop_reason=stop_reason,
                steps=steps,
                tool_receipts=receipts,
                usage_rounds=usage_rounds,
                run_path=str(session.run_path),
                plan=None,
            )

        habit_stop, habit_text = _maybe_habit_write_fast_path(
            session, sink, history, receipts, user_text
        )
        if habit_stop:
            stop_reason = habit_stop
            last_text = habit_text
            if habit_stop == "missing_life_receipt" and not last_text:
                last_text = LIFE_SAVE_FAIL_ACK
            if habit_stop == "pack_fast_path" and habit_text:
                last_text = apply_register_pass(
                    adapter,
                    receipts=receipts,
                    template=habit_text,
                )
            if last_text:
                sink.emit("token_delta", {"text": last_text})
            if end_session:
                session.end(stop_reason=stop_reason, steps=steps)
            return LoopResult(
                text=last_text,
                stop_reason=stop_reason,
                steps=steps,
                tool_receipts=receipts,
                usage_rounds=usage_rounds,
                run_path=str(session.run_path),
                plan=None,
            )

        due_stop, due_text = _maybe_due_write_fast_path(
            session, sink, history, receipts, user_text
        )
        if due_stop:
            stop_reason = due_stop
            last_text = due_text
            if due_stop == "missing_life_receipt" and not last_text:
                last_text = LIFE_SAVE_FAIL_ACK
            if due_stop == "pack_fast_path" and due_text:
                last_text = apply_register_pass(
                    adapter,
                    receipts=receipts,
                    template=due_text,
                )
            if last_text:
                sink.emit("token_delta", {"text": last_text})
            if end_session:
                session.end(stop_reason=stop_reason, steps=steps)
            return LoopResult(
                text=last_text,
                stop_reason=stop_reason,
                steps=steps,
                tool_receipts=receipts,
                usage_rounds=usage_rounds,
                run_path=str(session.run_path),
                plan=None,
            )

    people_stop, people_text = _maybe_people_fast_path(
        session, sink, history, receipts, user_text
    )
    if people_stop:
        stop_reason = people_stop
        last_text = people_text
        if people_stop == "missing_life_receipt" and not last_text:
            last_text = LIFE_SAVE_FAIL_ACK
        if people_stop == "pack_fast_path" and people_text:
            last_text = apply_register_pass(
                adapter,
                receipts=receipts,
                template=people_text,
            )
        if last_text:
            sink.emit("token_delta", {"text": last_text})
        if end_session:
            session.end(stop_reason=stop_reason, steps=steps)
        return LoopResult(
            text=last_text,
            stop_reason=stop_reason,
            steps=steps,
            tool_receipts=receipts,
            usage_rounds=usage_rounds,
            run_path=str(session.run_path),
            plan=None,
        )

    fast_stop, fast_text = _maybe_pack_fast_path(session, sink, history, receipts)
    if fast_stop:
        stop_reason = fast_stop
        last_text = fast_text
        if fast_stop == "missing_life_receipt" and not last_text:
            last_text = LIFE_SAVE_FAIL_ACK
        if fast_stop == "pack_fast_path" and fast_text:
            last_text = apply_register_pass(
                adapter,
                receipts=receipts,
                template=fast_text,
            )
        if last_text:
            sink.emit("token_delta", {"text": last_text})
        if end_session:
            session.end(stop_reason=stop_reason, steps=steps)
        return LoopResult(
            text=last_text,
            stop_reason=stop_reason,
            steps=steps,
            tool_receipts=receipts,
            usage_rounds=usage_rounds,
            run_path=str(session.run_path),
            plan=None,
        )

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
            last_text = LIFE_SAVE_FAIL_ACK
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
            if not turn.text:
                stop_reason = "empty_cortex"
                last_text = EMPTY_CORTEX_ACK
                session.writer.append("fault", {"where": "cortex.empty"})
                sink.emit("token_delta", {"text": last_text})
            else:
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

            blocked = _model_tool_blocked(session, tc.name)
            if blocked:
                from ada.runs.append import new_receipt_id
                from ada.body.vitals import utc_now_iso

                obs = {
                    "ok": False,
                    "tool": tc.name,
                    "args": tc.args,
                    "receipt_id": new_receipt_id(),
                    "ts": utc_now_iso(),
                    "denied_reason": blocked,
                    "outcome": "denied",
                }
                receipts.append(obs)
                session.writer.append("tool_denied", obs)
                sink.emit(
                    "tool_call_finished",
                    {
                        "tool": tc.name,
                        "ok": False,
                        "outcome": "denied",
                        "args": tc.args,
                        "denied_reason": blocked,
                    },
                )
                history.append(observation_to_content(obs, call_id=tc.call_id))
                continue

            # Consent Integrity: model must never self-Confirm (F-M24-4).
            call_args = dict(tc.args or {})
            from ada.harness.pack_router import MODEL_STRIP_CONFIRMED

            if tc.name in MODEL_STRIP_CONFIRMED and "confirmed" in call_args:
                call_args.pop("confirmed", None)

            _execute_tool(
                session,
                sink,
                history,
                receipts,
                tool=tc.name,
                args=call_args,
                call_id=tc.call_id,
            )

        if duplicate:
            break
    else:
        stop_reason = "max_steps"

    plan: dict[str, Any] | None = None
    if (
        session.pack_hint
        and (
            _pack_life_tool(session.pack_hint).startswith("life_")
            or str(session.pack_hint.get("verb") or "") in READ_PACK_VERBS
            or str(session.pack_hint.get("verb") or "") in ADMIN_WRITE_VERBS
        )
        and not any(
            str(r.get("tool") or "").startswith("life_")
            or str(r.get("tool") or "") in {
                "memory_open_loops_list",
                "memory_open_loops_upsert",
            }
            for r in receipts
        )
        and stop_reason == "completed"
    ):
        stop_reason = "missing_life_receipt"
    if session.mode == "plan" and last_text:
        plan = parse_plan_from_assistant(
            last_text, source_run=str(session.run_path)
        )
        if plan is not None:
            session.writer.append("plan_artifact", plan)
            sink.emit("plan_artifact", plan)

    honest = _honest_meal_mouth(last_text, receipts)
    if honest != last_text and honest:
        last_text = honest
        sink.emit("token_delta", {"text": last_text})
    else:
        last_text = honest

    if end_session:
        session.end(stop_reason=stop_reason, steps=steps)

    return LoopResult(
        text=last_text,
        stop_reason=stop_reason,
        steps=steps,
        tool_receipts=receipts,
        usage_rounds=usage_rounds,
        run_path=str(session.run_path),
        plan=plan,
    )


def make_sink() -> CallbackSink:
    return CallbackSink()
