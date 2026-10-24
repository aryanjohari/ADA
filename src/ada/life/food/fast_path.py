"""Food write fast-paths — draft divert, meal log, barcode, presets."""

from __future__ import annotations

import re
from typing import Any, Callable

from ada.harness.mouth import CONFIRM_LINE
from ada.life.food.doors import is_meal_log_utterance, meal_log_fast_path_args
from ada.life.food.speak import LIFE_SAVE_FAIL_ACK, MEAL_EMPTY_MACROS_ACK

ExecuteTool = Callable[..., None]
ReceiptData = Callable[[list[dict[str, Any]], str], dict[str, Any]]

__all__ = [
    "MEAL_EMPTY_MACROS_ACK",
    "fast_path_barcode",
    "fast_path_meal",
    "fast_path_meal_draft_add",
    "fast_path_meal_draft_cancel",
    "fast_path_meal_draft_save",
    "fast_path_meal_draft_start",
    "fast_path_meal_preset_log",
    "maybe_open_draft_divert",
    "try_draft_divert",
    "try_meal_write",
]

def fast_path_meal(
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
    if not utterance or args.get("lines"):
        return None, None
    from ada.life.food.spine import build_meal_log_args

    meal_args = build_meal_log_args(utterance, meal_slot=args.get("meal_slot"))
    for search in meal_args.get("searches") or []:
        execute_tool(
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
    execute_tool(
        session,
        sink,
        history,
        receipts,
        tool="life_meal_log",
        args=log_args,
        call_id="meal-fast-path",
    )
    meal_data = receipt_data(receipts, "life_meal_log")
    if meal_data.get("needs_confirm"):
        return "pack_fast_path", CONFIRM_LINE
    if meal_data.get("ok") is False or str(meal_data.get("reason") or "") == "empty_macros":
        reason = str(meal_data.get("reason") or meal_data.get("error") or "")
        if reason == "empty_macros":
            return "missing_life_receipt", MEAL_EMPTY_MACROS_ACK
        if reason == "spine_required":
            return "missing_life_receipt", LIFE_SAVE_FAIL_ACK
        return "missing_life_receipt", LIFE_SAVE_FAIL_ACK
    execute_tool(
        session,
        sink,
        history,
        receipts,
        tool="life_nutrition_day",
        args={},
        call_id="meal-rollup",
    )
    return "pack_fast_path", "Logged that meal."
def fast_path_meal_draft_start(
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
        tool="life_meal_draft_start",
        args={"session_id": session.session_id},
        call_id="meal-draft-start",
    )
    data = receipt_data(receipts, "life_meal_draft_start")
    ask = str((data or {}).get("ask") or "Type a food or paste a barcode.")
    return "pack_fast_path", ask
def fast_path_meal_draft_add(
    session: Any,
    sink: Any,
    history: list[Any],
    receipts: list[dict[str, Any]],
    utterance: str,
    *,
    execute_tool: ExecuteTool,
    receipt_data: ReceiptData,
) -> tuple[str | None, str | None]:
    from ada.life.food.draft_spine import build_draft_add_from_utterance

    built = build_draft_add_from_utterance(
        utterance, session_id=session.session_id
    )
    for search in built.get("searches") or []:
        execute_tool(
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
    execute_tool(
        session,
        sink,
        history,
        receipts,
        tool="life_meal_draft_add",
        args=add_args,
        call_id="meal-draft-add",
    )
    data = receipt_data(receipts, "life_meal_draft_add")
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
def fast_path_meal_draft_save(
    session: Any,
    sink: Any,
    history: list[Any],
    receipts: list[dict[str, Any]],
    args: dict[str, Any],
    *,
    execute_tool: ExecuteTool,
    receipt_data: ReceiptData,
) -> tuple[str | None, str | None]:
    save_args = {
        "session_id": session.session_id,
        "name": args.get("name"),
        "confirmed": False,
    }
    execute_tool(
        session,
        sink,
        history,
        receipts,
        tool="life_meal_draft_save",
        args=save_args,
        call_id="meal-draft-save",
    )
    data = receipt_data(receipts, "life_meal_draft_save")
    if data.get("needs_confirm"):
        return "pack_fast_path", CONFIRM_LINE
    if data.get("needs_name") or data.get("reason") == "name_required":
        return "pack_fast_path", str(data.get("ask") or "What should I call this meal?")
    if data.get("ok") is False:
        return "missing_life_receipt", str(data.get("ask") or LIFE_SAVE_FAIL_ACK)
    return "pack_fast_path", str(data.get("ask") or "Saved that meal preset.")
def fast_path_meal_draft_cancel(
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
        tool="life_meal_draft_cancel",
        args={"session_id": session.session_id},
        call_id="meal-draft-cancel",
    )
    data = receipt_data(receipts, "life_meal_draft_cancel")
    return "pack_fast_path", str((data or {}).get("ask") or "Cancelled.")
def fast_path_meal_preset_log(
    session: Any,
    sink: Any,
    history: list[Any],
    receipts: list[dict[str, Any]],
    args: dict[str, Any],
    *,
    execute_tool: ExecuteTool,
    receipt_data: ReceiptData,
) -> tuple[str | None, str | None]:
    name = str(args.get("name") or "").strip()
    if not name:
        return "missing_life_receipt", "Which preset should I log?"
    execute_tool(
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
    data = receipt_data(receipts, "life_meal_preset_log") or receipt_data(
        receipts, "life_meal_log"
    )
    if data.get("needs_confirm"):
        return "pack_fast_path", CONFIRM_LINE
    if data.get("ok") is False:
        return "missing_life_receipt", str(
            data.get("ask") or data.get("reason") or LIFE_SAVE_FAIL_ACK
        )
    execute_tool(
        session,
        sink,
        history,
        receipts,
        tool="life_nutrition_day",
        args={},
        call_id="preset-meal-rollup",
    )
    return "pack_fast_path", f"Logged preset {name}."
def fast_path_barcode(
    session: Any,
    sink: Any,
    history: list[Any],
    receipts: list[dict[str, Any]],
    args: dict[str, Any],
    *,
    execute_tool: ExecuteTool,
    receipt_data: ReceiptData,
) -> tuple[str | None, str | None]:
    from ada.logs import meal_draft as draft_mod

    barcode = str(args.get("barcode") or args.get("gtin") or "").strip()
    if not barcode:
        return "missing_life_receipt", "Paste a GTIN after barcode:"
    execute_tool(
        session,
        sink,
        history,
        receipts,
        tool="life_barcode_lookup",
        args={"barcode": barcode},
        call_id="barcode-lookup",
    )
    hit = receipt_data(receipts, "life_barcode_lookup")
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
        execute_tool(
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
        data = receipt_data(receipts, "life_meal_draft_add")
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
    execute_tool(
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
    data = receipt_data(receipts, "life_meal_log")
    if data.get("needs_confirm"):
        return "pack_fast_path", CONFIRM_LINE
    if data.get("ok"):
        return "pack_fast_path", f"Logged {display}."
    return "missing_life_receipt", LIFE_SAVE_FAIL_ACK
def maybe_open_draft_divert(
    session: Any,
    sink: Any,
    history: list[Any],
    receipts: list[dict[str, Any]],
    user_text: str,
    *,
    execute_tool: ExecuteTool,
    receipt_data: ReceiptData,
) -> tuple[str | None, str | None]:
    """When a meal draft is open, route food/barcode/done/save/cancel into draft ops."""
    from ada.logs import meal_draft as draft_mod
    from ada.life.food import draft_spine

    if not draft_mod.load_draft(session.session_id):
        return None, None
    text = (user_text or "").strip()
    if draft_spine.is_meal_draft_cancel(text):
        return fast_path_meal_draft_cancel(
            session, sink, history, receipts,
            execute_tool=execute_tool, receipt_data=receipt_data,
        )
    if draft_spine.is_draft_done(text):
        return fast_path_meal_draft_save(
            session, sink, history, receipts, {},
            execute_tool=execute_tool, receipt_data=receipt_data,
        )
    save_name = draft_spine.parse_save_as_name(text)
    if save_name:
        return fast_path_meal_draft_save(
            session, sink, history, receipts, {"name": save_name},
            execute_tool=execute_tool, receipt_data=receipt_data,
        )
    # Do not strip "add a meal" into draft_add("a meal") / wipe mid-compose.
    if draft_spine.is_meal_draft_start(text):
        return (
            "pack_fast_path",
            "Meal draft already open — add a food, say done / save as …, or cancel meal.",
        )
    gtin = draft_spine.parse_barcode_gtin(text)
    if gtin:
        return fast_path_barcode(
            session, sink, history, receipts, {"barcode": gtin},
            execute_tool=execute_tool, receipt_data=receipt_data,
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
    return fast_path_meal_draft_add(
        session, sink, history, receipts, cleaned,
        execute_tool=execute_tool, receipt_data=receipt_data,
    )


def try_draft_divert(
    session: Any,
    sink: Any,
    history: list[Any],
    receipts: list[dict[str, Any]],
    user_text: str,
    *,
    execute_tool: ExecuteTool,
    receipt_data: ReceiptData,
) -> tuple[str | None, str | None]:
    """Open-draft divert — first food hook in run_turn Agent mode."""
    if session.mode != "agent":
        return None, None
    return maybe_open_draft_divert(
        session,
        sink,
        history,
        receipts,
        user_text,
        execute_tool=execute_tool,
        receipt_data=receipt_data,
    )


def try_meal_write(
    session: Any,
    sink: Any,
    history: list[Any],
    receipts: list[dict[str, Any]],
    user_text: str,
    *,
    execute_tool: ExecuteTool,
    receipt_data: ReceiptData,
) -> tuple[str | None, str | None]:
    """Structural meal log write — after draft divert, before gym."""
    if session.mode != "agent":
        return None, None
    if not is_meal_log_utterance(user_text):
        return None, None
    meal_args = meal_log_fast_path_args(user_text)
    if not meal_args:
        return None, None
    return fast_path_meal(
        session,
        sink,
        history,
        receipts,
        meal_args,
        execute_tool=execute_tool,
        receipt_data=receipt_data,
    )
