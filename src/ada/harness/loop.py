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
    CONFIRM_HABIT,
    CONFIRM_HABIT_CREATE,
    CONFIRM_LINE,
    CONFIRM_SPLIT,
    apply_register_pass,
)
from ada.harness.pack_router import (
    ADMIN_WRITE_VERBS,
    CONFIRM_BOUND_VERBS,
    READ_PACK_VERBS,
    gym_read_takes_priority,
    is_gym_end_utterance,
    is_gym_start_utterance,
    is_incomplete_lift_utterance,
    is_lift_log_utterance,
    is_meal_log_utterance,
    is_time_start_utterance,
    lift_log_fast_path_args,
    meal_log_fast_path_args,
)
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

# Honest ack when Gemini returns no text and no tools (not a retry, not a mouth).
EMPTY_CORTEX_ACK = "No reply that turn. Try once more."
LIFE_SAVE_FAIL_ACK = "That didn't save — try once more."
MEAL_EMPTY_MACROS_ACK = (
    "Couldn't log that — nutrients came back empty. Try another food name."
)
_MEAL_LOGGED_CLAIM = re.compile(
    r"\b(?:logged|entries?\s+are\s+on\s+the\s+board|saved\s+(?:that|the)\s+meal)\b",
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
        ask = str(meal_args.get("ask") or "").strip()
        if ask:
            return "missing_life_receipt", ask
        misses = meal_args.get("misses") or []
        if any(str(m.get("reason") or "") == "empty_macros" for m in misses):
            return (
                "missing_life_receipt",
                MEAL_EMPTY_MACROS_ACK,
            )
        return "missing_life_receipt", None
    log_args: dict[str, Any] = {
        "lines": meal_args["lines"],
        "meal_slot": meal_args.get("meal_slot"),
    }
    if meal_args.get("resolve"):
        log_args["resolve"] = meal_args["resolve"]
    if meal_args.get("needs_confirm"):
        log_args["confirmed"] = False
        log_args["save_favorite"] = bool(meal_args.get("save_favorite", True))
    _execute_tool(
        session,
        sink,
        history,
        receipts,
        tool="life_meal_log",
        args=log_args,
        call_id="meal-fast-path",
    )
    meal_data = _receipt_data(receipts, "life_meal_log")
    if meal_data.get("needs_confirm"):
        return "pack_fast_path", CONFIRM_LINE
    if meal_data.get("ok") is False or str(meal_data.get("reason") or "") == "empty_macros":
        reason = str(meal_data.get("reason") or meal_data.get("error") or "")
        if reason == "empty_macros":
            return "missing_life_receipt", MEAL_EMPTY_MACROS_ACK
        if reason == "spine_required":
            return "missing_life_receipt", LIFE_SAVE_FAIL_ACK
        return "missing_life_receipt", LIFE_SAVE_FAIL_ACK
    _execute_tool(
        session,
        sink,
        history,
        receipts,
        tool="life_nutrition_day",
        args={},
        call_id="meal-rollup",
    )
    return "pack_fast_path", "Logged that meal."


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
    return "pack_fast_path", _speak_time_start(_receipt_data(receipts, "life_time_start"))


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
    return "pack_fast_path", _speak_time_stop(_receipt_data(receipts, "life_time_stop"))


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
    from ada.logs.gym import last_open_session_exercise_name

    follow_on = last_open_session_exercise_name()
    lift_args = build_lift_log_args(utterance, follow_on_name=follow_on)
    if not lift_args.get("ok") or not lift_args.get("sets"):
        ask = str(lift_args.get("ask") or "").strip()
        # Fail closed with a human ask — never silent no-tool (F-M24-3).
        return "missing_life_receipt", ask or (
            "Need load and reps for that lift — say it like 30kg x 12."
        )
    _execute_tool(
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
    return "pack_fast_path", _speak_lift_log(data)


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


def _meal_receipt_outcome(receipts: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Latest life_meal_log data blob, or None if no meal tool ran."""
    for row in reversed(receipts):
        if str(row.get("tool") or "") != "life_meal_log":
            continue
        data = row.get("data")
        if isinstance(data, dict):
            return data
        # Gateway sometimes surfaces needs_confirm on the observation itself.
        if row.get("needs_confirm") or row.get("ok") is False:
            return {
                "ok": bool(row.get("ok")),
                "needs_confirm": bool(row.get("needs_confirm")),
                "reason": row.get("reason") or row.get("denied_reason"),
            }
    return None


def _honest_meal_mouth(
    text: str | None, receipts: list[dict[str, Any]]
) -> str | None:
    """M23/M26: refuse lying 'Logged…' when meal tool failed or needs Confirm."""
    meal = _meal_receipt_outcome(receipts)
    if meal is None or not text:
        return text
    failed = (
        meal.get("ok") is False
        or meal.get("needs_confirm")
        or str(meal.get("reason") or "") in {"empty_macros", "needs_confirm", "spine_required"}
        or str(meal.get("error") or "") in {"empty_macros", "spine_required"}
    )
    if not failed:
        return text
    if not _MEAL_LOGGED_CLAIM.search(text):
        return text
    if meal.get("needs_confirm"):
        return CONFIRM_LINE
    if str(meal.get("reason") or meal.get("error") or "") == "empty_macros":
        return MEAL_EMPTY_MACROS_ACK
    return LIFE_SAVE_FAIL_ACK


def _speak_gym_end(data: dict[str, Any]) -> str:
    n = int(data.get("set_count") or 0)
    if n == 0:
        return "Closed the gym — no sets that session."
    muscles: list[str] = []
    for row in data.get("exercises") or []:
        if not isinstance(row, dict):
            continue
        for m in row.get("muscles") or []:
            token = str(m or "").strip()
            if token and token not in muscles:
                muscles.append(token)
    text = f"Closed the gym — {n} sets logged."
    if muscles:
        text += f" Hit {', '.join(muscles[:4])}."
    return text


def _speak_lift_log(data: dict[str, Any]) -> str:
    if data.get("ok") is False:
        return LIFE_SAVE_FAIL_ACK
    resolved = data.get("resolved") or []
    row = resolved[0] if resolved and isinstance(resolved[0], dict) else {}
    name = (
        row.get("exercise_name")
        or row.get("canonical_name")
        or (data.get("exercise_names") or [None])[0]
        or "lift"
    )
    load = row.get("load_kg")
    reps = row.get("reps")
    bits = [f"Logged {name}"]
    if load is not None and reps is not None:
        bits.append(f"— {load} kg × {reps}")
    elif reps is not None:
        bits.append(f"— {reps} reps")
    last_load = data.get("last_load_kg")
    if last_load is None:
        last_load = row.get("last_load_kg")
    last_reps = data.get("last_reps")
    if last_reps is None:
        last_reps = row.get("last_reps")
    if last_load is not None and last_reps is not None:
        bits.append(f"Last closed was {last_load} × {last_reps}.")
    text = " ".join(bits)
    if not text.endswith("."):
        text += "."
    return text


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
    mix = data.get("provenance_mix") or []
    if "estimate" in mix or data.get("has_estimate"):
        text += " Includes estimate lines — not lab-exact."
    if data.get("honest_partial"):
        text += " Partial micronutrients only — not inventing Ca/Fe/C/D."
    return text


def _fast_path_meal_draft_start(
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
        tool="life_meal_draft_start",
        args={"session_id": session.session_id},
        call_id="meal-draft-start",
    )
    data = _receipt_data(receipts, "life_meal_draft_start")
    ask = str((data or {}).get("ask") or "Type a food or paste a barcode.")
    return "pack_fast_path", ask


def _fast_path_meal_draft_add(
    session: ChatSession,
    sink: StreamSink,
    history: list[Any],
    receipts: list[dict[str, Any]],
    utterance: str,
) -> tuple[str | None, str | None]:
    from ada.harness.meal_draft_spine import build_draft_add_from_utterance

    built = build_draft_add_from_utterance(
        utterance, session_id=session.session_id
    )
    for search in built.get("searches") or []:
        _execute_tool(
            session,
            sink,
            history,
            receipts,
            tool="life_food_search",
            args={"query": search.get("query"), "limit": 5},
            call_id=f"draft-search-{search.get('query')}",
        )
    if not built.get("ok"):
        return "missing_life_receipt", str(built.get("ask") or LIFE_SAVE_FAIL_ACK)
    add_args: dict[str, Any] = {
        "session_id": session.session_id,
        "lines": built["lines"],
        "save_favorite": True,
    }
    if built.get("resolve"):
        add_args["resolve"] = built["resolve"]
    if built.get("needs_confirm"):
        add_args["confirmed"] = False
    _execute_tool(
        session,
        sink,
        history,
        receipts,
        tool="life_meal_draft_add",
        args=add_args,
        call_id="meal-draft-add",
    )
    data = _receipt_data(receipts, "life_meal_draft_add")
    if data.get("needs_confirm"):
        return "pack_fast_path", CONFIRM_LINE
    if data.get("ok") is False:
        return "missing_life_receipt", str(data.get("ask") or LIFE_SAVE_FAIL_ACK)
    ask = str(data.get("ask") or "Add another, or say done / save this meal?")
    n = int(data.get("line_count") or 0)
    name = ""
    if data.get("lines"):
        name = str((data["lines"][-1] or {}).get("display_name") or "")
    prefix = f"Added {name}. " if name else ""
    return "pack_fast_path", f"{prefix}{ask} ({n} line(s))"


def _fast_path_meal_draft_save(
    session: ChatSession,
    sink: StreamSink,
    history: list[Any],
    receipts: list[dict[str, Any]],
    args: dict[str, Any],
) -> tuple[str | None, str | None]:
    save_args = {
        "session_id": session.session_id,
        "name": args.get("name"),
        "confirmed": False,
    }
    _execute_tool(
        session,
        sink,
        history,
        receipts,
        tool="life_meal_draft_save",
        args=save_args,
        call_id="meal-draft-save",
    )
    data = _receipt_data(receipts, "life_meal_draft_save")
    if data.get("needs_confirm"):
        return "pack_fast_path", CONFIRM_LINE
    if data.get("needs_name") or data.get("reason") == "name_required":
        return "pack_fast_path", str(data.get("ask") or "What should I call this meal?")
    if data.get("ok") is False:
        return "missing_life_receipt", str(data.get("ask") or LIFE_SAVE_FAIL_ACK)
    return "pack_fast_path", str(data.get("ask") or "Saved that meal preset.")


def _fast_path_meal_draft_cancel(
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
        tool="life_meal_draft_cancel",
        args={"session_id": session.session_id},
        call_id="meal-draft-cancel",
    )
    data = _receipt_data(receipts, "life_meal_draft_cancel")
    return "pack_fast_path", str((data or {}).get("ask") or "Cancelled.")


def _fast_path_meal_preset_log(
    session: ChatSession,
    sink: StreamSink,
    history: list[Any],
    receipts: list[dict[str, Any]],
    args: dict[str, Any],
) -> tuple[str | None, str | None]:
    name = str(args.get("name") or "").strip()
    if not name:
        return "missing_life_receipt", "Which preset should I log?"
    _execute_tool(
        session,
        sink,
        history,
        receipts,
        tool="life_meal_preset_log",
        args={
            "name": name,
            "meal_slot": args.get("meal_slot"),
            "confirmed": False,
        },
        call_id="meal-preset-log",
    )
    data = _receipt_data(receipts, "life_meal_preset_log") or _receipt_data(
        receipts, "life_meal_log"
    )
    if data.get("needs_confirm"):
        return "pack_fast_path", CONFIRM_LINE
    if data.get("ok") is False:
        return "missing_life_receipt", str(
            data.get("ask") or data.get("reason") or LIFE_SAVE_FAIL_ACK
        )
    _execute_tool(
        session,
        sink,
        history,
        receipts,
        tool="life_nutrition_day",
        args={},
        call_id="preset-meal-rollup",
    )
    return "pack_fast_path", f"Logged preset {name}."


def _fast_path_barcode(
    session: ChatSession,
    sink: StreamSink,
    history: list[Any],
    receipts: list[dict[str, Any]],
    args: dict[str, Any],
) -> tuple[str | None, str | None]:
    from ada.logs import meal_draft as draft_mod

    barcode = str(args.get("barcode") or args.get("gtin") or "").strip()
    if not barcode:
        return "missing_life_receipt", "Paste a GTIN after barcode:"
    _execute_tool(
        session,
        sink,
        history,
        receipts,
        tool="life_barcode_lookup",
        args={"barcode": barcode},
        call_id="barcode-lookup",
    )
    hit = _receipt_data(receipts, "life_barcode_lookup")
    if not hit.get("ok"):
        return "missing_life_receipt", "Barcode miss — try another GTIN or type the name."
    # Build a one-line draft add or one-shot meal from ref.
    display = str(hit.get("name") or barcode)
    ref_id = str(hit.get("ref_id") or "")
    line = {
        "display_name": display,
        "ref_id": ref_id,
        "serving_qty": 1,
        "serving_unit": "serving",
        "provenance": hit.get("provenance") or "barcode",
        "nutrients": hit.get("nutrients_preview") or {},
    }
    open_draft = draft_mod.load_draft(session.session_id)
    if open_draft:
        resolve = {
            "bind_authority": "meal_spine",
            "needs_confirm": True,
            "reasons": ["barcode"],
            "rows": [
                {
                    "query": display,
                    "query_norm": barcode,
                    "reasons": ["barcode"],
                    "proposed_ref_id": ref_id,
                    "candidates": [
                        {
                            "ref_id": ref_id,
                            "label": display,
                            "nutrients": hit.get("nutrients_preview") or {},
                        }
                    ],
                }
            ],
        }
        _execute_tool(
            session,
            sink,
            history,
            receipts,
            tool="life_meal_draft_add",
            args={
                "session_id": session.session_id,
                "lines": [line],
                "resolve": resolve,
                "confirmed": False,
                "save_favorite": True,
            },
            call_id="barcode-draft-add",
        )
        data = _receipt_data(receipts, "life_meal_draft_add")
        if data.get("needs_confirm"):
            return "pack_fast_path", CONFIRM_LINE
        return "pack_fast_path", str(data.get("ask") or "Added barcode line to draft.")
    # One-shot meal line
    resolve = {
        "bind_authority": "meal_spine",
        "needs_confirm": True,
        "reasons": ["barcode"],
        "rows": [
            {
                "query": display,
                "query_norm": barcode,
                "reasons": ["barcode"],
                "proposed_ref_id": ref_id,
                "candidates": [
                    {
                        "ref_id": ref_id,
                        "label": display,
                        "nutrients": hit.get("nutrients_preview") or {},
                    }
                ],
            }
        ],
    }
    _execute_tool(
        session,
        sink,
        history,
        receipts,
        tool="life_meal_log",
        args={
            "lines": [line],
            "resolve": resolve,
            "confirmed": False,
            "save_favorite": True,
        },
        call_id="barcode-meal-log",
    )
    data = _receipt_data(receipts, "life_meal_log")
    if data.get("needs_confirm"):
        return "pack_fast_path", CONFIRM_LINE
    if data.get("ok"):
        return "pack_fast_path", f"Logged {display}."
    return "missing_life_receipt", LIFE_SAVE_FAIL_ACK


def _maybe_open_draft_divert(
    session: ChatSession,
    sink: StreamSink,
    history: list[Any],
    receipts: list[dict[str, Any]],
    user_text: str,
) -> tuple[str | None, str | None]:
    """When a meal draft is open, route food/barcode/done/save/cancel into draft ops."""
    from ada.logs import meal_draft as draft_mod
    from ada.harness import meal_draft_spine as draft_spine

    if not draft_mod.load_draft(session.session_id):
        return None, None
    text = (user_text or "").strip()
    if draft_spine.is_meal_draft_cancel(text):
        return _fast_path_meal_draft_cancel(session, sink, history, receipts)
    if draft_spine.is_draft_done(text):
        return _fast_path_meal_draft_save(session, sink, history, receipts, {})
    save_name = draft_spine.parse_save_as_name(text)
    if save_name:
        return _fast_path_meal_draft_save(
            session, sink, history, receipts, {"name": save_name}
        )
    gtin = draft_spine.parse_barcode_gtin(text)
    if gtin:
        return _fast_path_barcode(
            session, sink, history, receipts, {"barcode": gtin}
        )
    # Only divert food-shaped turns — leave reads / other packs alone.
    lower = text.lower()
    foodish = bool(
        is_meal_log_utterance(text)
        or re.match(r"^(?:log|add)\b", lower)
        or re.search(r"\b\d+(?:\.\d+)?\s*(?:g|grams?)\b", lower)
        or re.search(
            r"\b(?:egg|eggs|rice|chicken|salmon|coffee|oat|bread|milk)\b",
            lower,
        )
    )
    if not foodish:
        return None, None
    cleaned = re.sub(
        r"^(?:ada[, ]+)?(?:log|add)\s+(?:meal\s+)?",
        "",
        text,
        flags=re.I,
    ).strip() or text
    return _fast_path_meal_draft_add(
        session, sink, history, receipts, cleaned
    )


def _speak_nutrition_week(data: dict[str, Any]) -> str:
    if not data.get("days_logged"):
        return str(data.get("message") or "No meals logged in this window.")
    window = int(data.get("window_days") or 7)
    logged = int(data.get("days_logged") or 0)
    ag = data.get("aggregates") or {}
    bits = [f"Last {window} days: {logged} day(s) logged."]
    avg_p = ag.get("avg_protein_g")
    if avg_p is not None:
        bits.append(f"Avg {avg_p}g protein")
    avg_k = ag.get("avg_energy_kcal")
    if avg_k is not None:
        bits.append(f"avg {avg_k} kcal")
    days = data.get("days") if isinstance(data.get("days"), list) else []
    cites = [
        str(d.get("cite"))
        for d in days
        if isinstance(d, dict) and d.get("meal_count", 0) > 0 and d.get("cite")
    ]
    if cites:
        bits.append(f"Logged: {', '.join(cites[:2])}")
    for pat in data.get("patterns") or []:
        bits.append(pat)
    text = ". ".join(bits)
    if not text.endswith("."):
        text += "."
    return text


def _speak_time_status(data: dict[str, Any]) -> str:
    active = data.get("active")
    if isinstance(active, dict):
        kind = active.get("kind") or "timer"
        return f"Running: {kind}."
    return "No timer running."


def _speak_time_start(data: dict[str, Any]) -> str:
    """Ack from start receipt only — never invent duration_s."""
    if data.get("ok") is False:
        return "Could not start a timer."
    label = str(data.get("label") or "").strip()
    kind = str(data.get("kind") or "timer").replace("_", " ")
    name = label or kind
    return f"Started {name}."


def _speak_time_stop(data: dict[str, Any]) -> str:
    """Ack from stop receipt. Miss-stop never claims minutes."""
    if data.get("ok") is False or data.get("reason") == "no_active_block":
        return "No timer running."
    kind = str(data.get("kind") or "timer").replace("_", " ")
    duration = data.get("duration_s")
    if duration is None:
        return f"Stopped {kind}."
    return f"Stopped {kind} ({duration}s)."


def _speak_time_day(data: dict[str, Any]) -> str:
    date = data.get("date") or "that day"
    n = int(data.get("block_count") or 0)
    if n == 0:
        return str(data.get("message") or f"No time blocks logged for {date}.")
    bits = [f"{date}: {n} time block(s)"]
    duration = data.get("duration_s")
    if isinstance(duration, int) and duration > 0:
        bits.append(f"{duration}s")
    cite = data.get("cite")
    if cite:
        bits.append(str(cite))
    text = ". ".join(bits)
    if not text.endswith("."):
        text += "."
    return text


def _speak_time_week(data: dict[str, Any]) -> str:
    if not data.get("days_logged"):
        return str(data.get("message") or "No time blocks logged in this window.")
    window = int(data.get("window_days") or 7)
    logged = int(data.get("days_logged") or 0)
    bits = [f"Last {window} days: {logged} day(s) with time blocks"]
    ag = data.get("aggregates") if isinstance(data.get("aggregates"), dict) else {}
    duration = ag.get("sum_duration_s")
    if isinstance(duration, int) and duration > 0:
        bits.append(f"{duration}s")
    days = data.get("days") if isinstance(data.get("days"), list) else []
    cites = [
        str(d.get("cite"))
        for d in days
        if isinstance(d, dict) and d.get("block_count", 0) > 0 and d.get("cite")
    ]
    if cites:
        bits.append(f"Logged: {', '.join(cites[:2])}")
    text = ". ".join(bits)
    if not text.endswith("."):
        text += "."
    return text


def _speak_due_list(data: dict[str, Any]) -> str:
    loops = data.get("loops") if isinstance(data.get("loops"), list) else []
    count = data.get("count")
    n = int(count) if isinstance(count, int) else len(loops)
    return f"{n} open due(s)."


def _speak_gym_status(data: dict[str, Any]) -> str:
    if isinstance(data.get("exercises"), list):
        return _speak_gym_end(data)
    n = len(data.get("sets_today") or [])
    exercises = data.get("exercises_today") or []
    if exercises and isinstance(exercises[0], dict):
        row = exercises[0]
        last_load = row.get("last_load_kg")
        last_reps = row.get("last_reps")
        if last_load is not None and last_reps is not None:
            name = row.get("canonical_name") or row.get("exercise_name") or "lift"
            prior = f"Last closed {name}: {last_load} × {last_reps}."
            if data.get("active_session"):
                if n == 0:
                    return f"Gym session's open — no sets yet. {prior}"
                return f"Gym session's open — {n} sets today. {prior}"
            if n == 0:
                return f"No gym sets logged today. {prior}"
            return f"{n} sets today. {prior}"
    if data.get("active_session"):
        if n == 0:
            return "Gym session's open — no sets yet."
        return f"Gym session's open — {n} sets today."
    if n == 0:
        return "No gym sets logged today."
    return f"{n} sets logged today."


def _speak_gym_day(data: dict[str, Any]) -> str:
    date = data.get("date") or "that day"
    n = int(data.get("set_count") or 0)
    if n == 0:
        return str(data.get("message") or f"No gym sets logged for {date}.")
    bits = [f"{date}: {n} sets"]
    tonnage = data.get("tonnage_kg")
    if isinstance(tonnage, (int, float)) and float(tonnage) > 0:
        bits.append(f"{tonnage} kg tonnage")
    label = data.get("split_label")
    if label:
        bits.append(str(label))
    cite = data.get("cite")
    if cite:
        bits.append(str(cite))
    text = ". ".join(bits)
    if not text.endswith("."):
        text += "."
    return text


def _speak_gym_week(data: dict[str, Any]) -> str:
    if not data.get("days_logged"):
        return str(data.get("message") or "No gym sets logged in this window.")
    window = int(data.get("window_days") or 7)
    logged = int(data.get("days_logged") or 0)
    bits = [f"Last {window} days: {logged} day(s) lifted"]
    ag = data.get("aggregates") if isinstance(data.get("aggregates"), dict) else {}
    tonnage = ag.get("sum_tonnage_kg")
    if isinstance(tonnage, (int, float)) and float(tonnage) > 0:
        bits.append(f"{tonnage} kg tonnage")
    rest_n = ag.get("rest_day_count")
    if isinstance(rest_n, int) and rest_n > 0:
        bits.append(f"{rest_n} rest day(s)")
    days = data.get("days") if isinstance(data.get("days"), list) else []
    cites = [
        str(d.get("cite"))
        for d in days
        if isinstance(d, dict) and d.get("set_count", 0) > 0 and d.get("cite")
    ]
    if cites:
        bits.append(f"Logged: {', '.join(cites[:2])}")
    for pat in data.get("patterns") or []:
        bits.append(str(pat))
    text = ". ".join(bits)
    if not text.endswith("."):
        text += "."
    return text


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
    return f"{count} matches — tap Confirm on the card."


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
    return "pack_fast_path", f"{verb.replace('_', ' ')} logged."


def _fast_path_gym_start(
    session: ChatSession,
    sink: StreamSink,
    history: list[Any],
    receipts: list[dict[str, Any]],
) -> tuple[str | None, str | None]:
    from ada.logs.gym_split import empty_day_slots, has_gym_split

    _execute_tool(
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
        _execute_tool(
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


def _fast_path_gym_end(
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
        tool="life_gym_end",
        args={},
        call_id="gym-end-fast-path",
    )
    last = receipts[-1] if receipts else {}
    if not last.get("ok"):
        return "missing_life_receipt", LIFE_SAVE_FAIL_ACK
    data = last.get("data") if isinstance(last.get("data"), dict) else {}
    return "pack_fast_path", _speak_gym_end(data)


def _maybe_gym_write_fast_path(
    session: ChatSession,
    sink: StreamSink,
    history: list[Any],
    receipts: list[dict[str, Any]],
    user_text: str,
) -> tuple[str | None, str | None]:
    """Force gym start/end/lift before cortex even if pack_hint is missing/wrong."""
    if session.mode != "agent":
        return None, None
    if gym_read_takes_priority(user_text):
        return None, None
    if is_incomplete_lift_utterance(user_text):
        from ada.harness.gym_spine import INCOMPLETE_ASK, build_lift_log_args

        built = build_lift_log_args(user_text)
        ask = str(built.get("ask") or "").strip()
        return "missing_life_receipt", ask or INCOMPLETE_ASK
    if is_lift_log_utterance(user_text):
        args = lift_log_fast_path_args(user_text) or {"utterance": user_text}
        return _fast_path_lift(session, sink, history, receipts, args)
    if is_gym_start_utterance(user_text):
        return _fast_path_gym_start(session, sink, history, receipts)
    if is_gym_end_utterance(user_text):
        return _fast_path_gym_end(session, sink, history, receipts)
    return None, None


def _maybe_time_write_fast_path(
    session: ChatSession,
    sink: StreamSink,
    history: list[Any],
    receipts: list[dict[str, Any]],
    user_text: str,
) -> tuple[str | None, str | None]:
    """Force time_start before cortex even if pack_hint is missing/wrong."""
    if session.mode != "agent":
        return None, None
    if is_time_start_utterance(user_text):
        from ada.harness.time_intent import map_time_intent

        args = map_time_intent(user_text)
        return _fast_path_time_start(session, sink, history, receipts, args)
    return None, None


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
    if parsed.get("needs_confirm"):
        confirm_tool = str(parsed.get("confirm_tool") or tool)
        tick_args = parsed.get("args")
        if not isinstance(tick_args, dict):
            return "missing_life_receipt", LIFE_SAVE_FAIL_ACK
        _execute_tool(
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
        return "pack_fast_path", "Habit miss logged."
    if verb == "routine_run":
        return "pack_fast_path", "Routine logged."
    return "pack_fast_path", "Habit logged."


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
        return "pack_fast_path", "Person saved."

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
        return "pack_fast_path", "Birthday saved."

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
        return "pack_fast_path", "Note saved."

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
            fast_stop, fast_text = _fast_path_meal(
                session, sink, history, receipts, meal_args
            )
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
