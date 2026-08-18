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
from ada.harness.pack_router import ADMIN_WRITE_VERBS, CONFIRM_BOUND_VERBS, READ_PACK_VERBS
from ada.harness.plan_artifact import parse_plan_from_assistant
from ada.harness.session import ChatSession
from ada.harness.stream_events import CallbackSink, NullSink, StreamSink

# Narrow chill cues (M05) — sticky for the session once matched.
_CHILL_CUE = re.compile(
    r"\b(chill|softer|stop roasting|tone it down|less roast)\b",
    re.IGNORECASE,
)

_FACT_TOOLS_BLOCKED_ON_LIFE_PACK = frozenset(
    {"memory_facts_append", "memory_facts_propose_edit"}
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
    utterance = str(args.get("utterance") or "").strip()
    if not utterance or args.get("lines"):
        return None, None
    from ada.harness.meal_spine import build_meal_log_args

    meal_args = build_meal_log_args(utterance, meal_slot=args.get("meal_slot"))
    for search in meal_args.get("searches") or []:
        _execute_tool(
            session,
            sink,
            history,
            receipts,
            tool="life_food_search",
            args={"query": search.get("query"), "limit": 5},
            call_id=f"meal-search-{search.get('query')}",
        )
    if not meal_args.get("ok") or not meal_args.get("lines"):
        return "missing_life_receipt", None
    _execute_tool(
        session,
        sink,
        history,
        receipts,
        tool="life_meal_log",
        args={"lines": meal_args["lines"], "meal_slot": meal_args.get("meal_slot")},
        call_id="meal-fast-path",
    )
    _execute_tool(
        session,
        sink,
        history,
        receipts,
        tool="life_nutrition_day",
        args={},
        call_id="meal-rollup",
    )
    return "pack_fast_path", "Logged meal — receipt on file."


def _fast_path_time_start(
    session: ChatSession,
    sink: StreamSink,
    history: list[Any],
    receipts: list[dict[str, Any]],
    args: dict[str, Any],
) -> tuple[str | None, str | None]:
    kind = args.get("kind")
    if not kind:
        return None, None
    start_args: dict[str, Any] = {"kind": str(kind)}
    if args.get("label") is not None:
        start_args["label"] = args.get("label")
    _execute_tool(
        session,
        sink,
        history,
        receipts,
        tool="life_time_start",
        args=start_args,
        call_id="time-start-fast-path",
    )
    _execute_tool(
        session,
        sink,
        history,
        receipts,
        tool="life_time_status",
        args={},
        call_id="time-status",
    )
    label = str(kind).replace("_", " ")
    return "pack_fast_path", f"Started {label} block — receipt on file."


def _fast_path_time_stop(
    session: ChatSession,
    sink: StreamSink,
    history: list[Any],
    receipts: list[dict[str, Any]],
) -> tuple[str | None, str | None]:
    _execute_tool(
        session,
        sink,
        history,
        receipts,
        tool="life_time_stop",
        args={},
        call_id="time-stop-fast-path",
    )
    _execute_tool(
        session,
        sink,
        history,
        receipts,
        tool="life_time_status",
        args={},
        call_id="time-status",
    )
    return "pack_fast_path", "Stopped timer — receipt on file."


def _fast_path_lift(
    session: ChatSession,
    sink: StreamSink,
    history: list[Any],
    receipts: list[dict[str, Any]],
    args: dict[str, Any],
) -> tuple[str | None, str | None]:
    utterance = str(args.get("utterance") or "").strip()
    if not utterance or args.get("sets"):
        return None, None
    from ada.harness.gym_spine import build_lift_log_args

    lift_args = build_lift_log_args(utterance)
    if not lift_args.get("ok") or not lift_args.get("sets"):
        return "missing_life_receipt", None
    _execute_tool(
        session,
        sink,
        history,
        receipts,
        tool="life_lift_log",
        args={"sets": lift_args["sets"]},
        call_id="lift-fast-path",
    )
    return "pack_fast_path", "Logged lift — receipt on file."


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
    return "pack_fast_path", "Capture logged — receipt on file."


def _receipt_data(receipts: list[dict[str, Any]], tool: str) -> dict[str, Any]:
    for row in reversed(receipts):
        if str(row.get("tool") or "") == tool:
            data = row.get("data")
            return data if isinstance(data, dict) else {}
    return {}


def _speak_nutrition_day(data: dict[str, Any]) -> str:
    totals = data.get("totals") or {}
    date = data.get("date") or "today"
    kcal = totals.get("energy_kcal")
    protein = totals.get("protein_g")
    if not totals:
        text = f"No meals logged for {date}."
    else:
        bits = [f"{date}:"]
        if kcal is not None:
            bits.append(f"{kcal} kcal")
        if protein is not None:
            bits.append(f"{protein}g protein")
        text = " ".join(bits)
    if data.get("honest_partial"):
        text += " honest_partial — Ca/Fe/C/D not invented."
    return text


def _speak_time_status(data: dict[str, Any]) -> str:
    active = data.get("active")
    if isinstance(active, dict):
        kind = active.get("kind") or "timer"
        return f"Running: {kind}."
    return "No timer running."


def _speak_due_list(data: dict[str, Any]) -> str:
    loops = data.get("loops") if isinstance(data.get("loops"), list) else []
    count = data.get("count")
    n = int(count) if isinstance(count, int) else len(loops)
    return f"{n} open due(s)."


def _speak_gym_status(data: dict[str, Any]) -> str:
    n = len(data.get("sets_today") or [])
    if data.get("active_session"):
        return f"Open gym session, {n} sets today."
    return f"No open gym session. {n} sets today."


def _speak_habit_status(data: dict[str, Any]) -> str:
    habits = data.get("habits") or []
    if not habits:
        return "No habits seeded yet."
    rate = data.get("continuity_rate")
    done = sum(1 for h in habits if h.get("done_today"))
    text = f"Habits today: {done}/{len(habits)} done."
    if rate is not None:
        text += f" Continuity {int(float(rate) * 100)}% over {data.get('window_days', 7)} days."
    return text


def _speak_who_is(data: dict[str, Any]) -> str:
    count = int(data.get("match_count") or len(data.get("candidates") or []))
    if count == 0:
        return "No person match — offer to capture a stub."
    if count == 1:
        cand = (data.get("candidates") or [{}])[0]
        name = cand.get("display_name") or data.get("person_id") or "person"
        return f"Matched {name}."
    return f"{count} candidates — Confirm required, no silent bind."


def _speak_people_remind(data: dict[str, Any]) -> str:
    upcoming = data.get("upcoming") or data.get("birthday_soon") or []
    if not upcoming:
        return "No upcoming kin events in horizon."
    names = ", ".join(str(x.get("display_name") or x.get("person_id")) for x in upcoming[:3])
    return f"Upcoming: {names}."


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
    elif verb == "time_status" or tool == "life_time_status":
        speech = _speak_time_status(data)
    elif verb == "due_list" or tool == "memory_open_loops_list":
        speech = _speak_due_list(data)
    elif verb == "gym_status" or tool == "life_gym_status":
        speech = _speak_gym_status(data)
    elif verb == "streak_show" or tool == "life_habit_status":
        speech = _speak_habit_status(data)
    elif verb == "who_is" or tool == "life_who_is":
        speech = _speak_who_is(data)
    elif verb == "people_remind" or tool == "life_people_remind":
        speech = _speak_people_remind(data)
    else:
        speech = "Read receipt on file."
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
) -> tuple[str | None, str | None]:
    hint = session.pack_hint or {}
    verb = str(hint.get("verb") or "")
    args = hint.get("args") if isinstance(hint.get("args"), dict) else {}
    utterance = str(
        (args or {}).get("utterance")
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
    from ada.harness.people_spine import resolve_mention_for_due

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
    return "pack_fast_path", f"{verb.replace('_', ' ')} — receipt on file."


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
    utterance = str(args.get("utterance") or args.get("name") or args.get("body") or "").strip()
    if not utterance:
        return "missing_life_receipt", None
    from ada.harness.habit_spine import build_habit_tick_args

    parsed = build_habit_tick_args(utterance, verb=verb)
    if not parsed.get("ok") or not parsed.get("args"):
        return "missing_life_receipt", None
    _execute_tool(
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
        reason = (last.get("data") or {}).get("reason") if isinstance(last.get("data"), dict) else None
        if reason == "already_done":
            return "pack_fast_path", "Already logged today."
        return "missing_life_receipt", None
    _execute_tool(
        session,
        sink,
        history,
        receipts,
        tool="life_habit_status",
        args={},
        call_id=f"{verb}-status",
    )
    if verb == "habit_miss":
        return "pack_fast_path", "Habit miss logged — receipt on file."
    if verb == "routine_run":
        return "pack_fast_path", "Routine logged — receipt on file."
    return "pack_fast_path", "Habit logged — receipt on file."


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
    if verb == "person_capture":
        utterance = str(args.get("utterance") or args.get("body") or "").strip()
        if not utterance:
            return "missing_life_receipt", None
        from ada.harness.people_spine import build_capture_args

        parsed = build_capture_args(utterance)
        if not parsed.get("ok"):
            return "missing_life_receipt", None
        _execute_tool(
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
        return "pack_fast_path", "Person capture — receipt on file."

    if verb == "birthday_set":
        body = str(args.get("body") or args.get("utterance") or "").strip()
        if not body:
            return "missing_life_receipt", None
        from ada.harness.people_spine import build_birthday_args

        parsed = build_birthday_args(body)
        if not parsed.get("ok"):
            return "missing_life_receipt", None
        _execute_tool(
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
        return "pack_fast_path", "Birthday set — receipt on file."

    if verb == "person_note":
        text = str(args.get("text") or "").strip()
        mention = str(args.get("mention") or "").strip()
        if not text:
            return "missing_life_receipt", None
        from ada.memory import people as people_mod

        if not args.get("person_id") and mention:
            resolved = people_mod.resolve_mention(mention)
            if not resolved.get("ok"):
                return "missing_life_receipt", None
            args = {**args, "person_id": resolved["person_id"]}
        _execute_tool(
            session,
            sink,
            history,
            receipts,
            tool=tool,
            args={"person_id": args.get("person_id"), "text": text},
            call_id="person-note-fast-path",
        )
        last = receipts[-1] if receipts else {}
        if not last.get("ok"):
            return "missing_life_receipt", None
        return "pack_fast_path", "Note saved — receipt on file."

    return None, None


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
        return "pack_fast_path", "Confirm candidates — no silent bind."
    if last.get("ok"):
        return "pack_fast_path", f"{verb.replace('_', ' ')} — receipt on file."
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

    if verb in {"person_capture", "birthday_set", "person_note"}:
        return _fast_path_people_write(
            session, sink, history, receipts, verb=verb, tool=tool, args=args or {}
        )

    if not tool.startswith("life_") or not isinstance(args, dict):
        return None, None

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

    fast_stop, fast_text = _maybe_pack_fast_path(session, sink, history, receipts)
    if fast_stop:
        stop_reason = fast_stop
        last_text = fast_text
        if fast_text:
            sink.emit("token_delta", {"text": fast_text})
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

            _execute_tool(
                session,
                sink,
                history,
                receipts,
                tool=tc.name,
                args=tc.args,
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
