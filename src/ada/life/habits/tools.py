"""life_habit_* / life_routine_run gateway handlers."""

from __future__ import annotations

from typing import Any

from ada.logs import habits as habits_mod
from ada.logs.receipts import write_life_crumb


def _write(tool: str, receipt_id: str, outcome: dict[str, Any]) -> dict[str, Any]:
    if receipt_id and outcome.get("ok"):
        write_life_crumb(receipt_id=receipt_id, tool=tool, outcome=outcome)
    return outcome


def _habit_id_exists(habit_id: str | None) -> bool:
    hid = str(habit_id or "").strip()
    if not hid:
        return False
    return any(h.get("habit_id") == hid for h in habits_mod.list_habit_definitions())


def _habit_create_confirm(name: str, *, tick_after: bool = True) -> dict[str, Any]:
    """0-match → Confirm-create payload (HUD remaps to life_habit_create)."""
    return habits_mod.create_habit(
        display_name=name,
        confirmed=False,
        tick_after=tick_after,
    )


def _habit_ambiguous_confirm(
    *,
    name: str,
    matches: list[dict[str, Any]],
    resolve: dict[str, Any] | None = None,
    candidates: list[Any] | None = None,
    habit_id: Any = None,
) -> dict[str, Any]:
    from ada.harness.resolve_gate import decide_habit_bind

    if resolve and (candidates or resolve.get("candidates")):
        cands = list(candidates or resolve.get("candidates") or [])
        return {
            "ok": False,
            "needs_confirm": True,
            "outcome": "needs_confirm",
            "reason": resolve.get("reason") or "ambiguous",
            "reasons": list(resolve.get("reasons") or ["many"]),
            "candidates": cands,
            "resolve": resolve,
            "name": name,
            "habit_id": habit_id or resolve.get("proposed_habit_id"),
        }
    decision = decide_habit_bind(query=name, matches=matches)
    return {
        "ok": False,
        "needs_confirm": True,
        "outcome": "needs_confirm",
        "reason": "ambiguous",
        "reasons": list(decision.get("reasons") or ["many"]),
        "candidates": list(decision.get("candidates") or []),
        "resolve": {
            "reason": "ambiguous",
            "candidates": list(decision.get("candidates") or []),
            "proposed_habit_id": decision.get("proposed_habit_id"),
            "query": name,
        },
        "name": name,
        "habit_id": decision.get("proposed_habit_id"),
    }


def _gate_habit_tick(args: dict[str, Any], *, allow_create: bool) -> dict[str, Any] | None:
    """Return needs_confirm / create payload, or None to proceed with bound habit_id.

    Never silent-create. Never write a stale/invented habit_id (FK class).
    Chat Yes alone is not Confirm — cortex confirmed=true still re-resolves.
    """
    from ada.life.habits.spine import clean_habit_name

    confirmed = bool(args.get("confirmed", False))
    resolve = args.get("resolve") if isinstance(args.get("resolve"), dict) else None
    candidates = list(args.get("candidates") or [])
    if resolve and not candidates:
        candidates = list(resolve.get("candidates") or [])
    name = clean_habit_name(
        str(args.get("name") or args.get("utterance") or args.get("display_name") or "")
    )
    habit_id = str(args.get("habit_id") or "").strip() or None

    # Stale / model-invented id — drop and re-resolve (Consent Integrity).
    if habit_id and not _habit_id_exists(habit_id):
        habit_id = None

    if (resolve or (len(candidates) > 1)) and not confirmed:
        return _habit_ambiguous_confirm(
            name=name,
            matches=[],
            resolve=resolve,
            candidates=candidates,
            habit_id=habit_id or args.get("habit_id"),
        )

    if habit_id:
        # Real id after Confirm or unique bind — proceed.
        args["habit_id"] = habit_id
        if name:
            args["name"] = name
        return None

    if not name:
        return {"ok": False, "reason": "missing_name", "outcome": "error"}

    resolved = habits_mod.resolve_habit(name)
    if resolved.get("ok"):
        args["habit_id"] = resolved["habit_id"]
        args["name"] = name
        return None

    matches = list(resolved.get("matches") or [])
    if len(matches) > 1:
        return _habit_ambiguous_confirm(name=name, matches=matches)

    if allow_create:
        # 0-match — Confirm-create (no silent SQL; no FK).
        return _habit_create_confirm(name, tick_after=True)

    return {
        "ok": False,
        "reason": "missing_life_receipt",
        "match_count": 0,
        "matches": [],
        "name": name,
    }


def run_life_habit_create(args: dict[str, Any]) -> dict[str, Any]:
    """Confirm-create habit definition (teach-in-flow); optional same-turn tick."""
    receipt_id = str(args.get("receipt_id") or "")
    display_name = str(
        args.get("display_name") or args.get("proposed_display_name") or args.get("name") or ""
    ).strip()
    outcome = habits_mod.create_habit(
        display_name=display_name,
        aliases=args.get("aliases") if isinstance(args.get("aliases"), list) else None,
        schedule=args.get("schedule") if isinstance(args.get("schedule"), dict) else None,
        confirmed=bool(args.get("confirmed", False)),
        tick_after=bool(args.get("tick_after", False)),
        note=args.get("note"),
        receipt_id=receipt_id or None,
    )
    if outcome.get("needs_confirm"):
        outcome["ok"] = False
        return outcome
    return _write("life_habit_create", receipt_id, outcome)


def run_life_habit_do(args: dict[str, Any]) -> dict[str, Any]:
    receipt_id = str(args.get("receipt_id") or "")
    gated = _gate_habit_tick(args, allow_create=True)
    if gated is not None:
        return gated
    return _write(
        "life_habit_do",
        receipt_id,
        habits_mod.habit_do(
            habit_id=args.get("habit_id"),
            name=args.get("name"),
            note=args.get("note"),
            receipt_id=receipt_id,
        ),
    )


def run_life_habit_miss(args: dict[str, Any]) -> dict[str, Any]:
    receipt_id = str(args.get("receipt_id") or "")
    gated = _gate_habit_tick(args, allow_create=False)
    if gated is not None:
        return gated
    return _write(
        "life_habit_miss",
        receipt_id,
        habits_mod.habit_miss(
            habit_id=args.get("habit_id"),
            name=args.get("name"),
            note=args.get("note"),
            receipt_id=receipt_id,
        ),
    )


def run_life_routine_run(args: dict[str, Any]) -> dict[str, Any]:
    receipt_id = str(args.get("receipt_id") or "")
    return _write(
        "life_routine_run",
        receipt_id,
        habits_mod.routine_run(
            routine_id=args.get("routine_id"),
            name=args.get("name"),
            steps=args.get("steps"),
            receipt_id=receipt_id,
        ),
    )


def run_life_habit_status(args: dict[str, Any]) -> dict[str, Any]:
    return habits_mod.habit_status(
        habit_id=args.get("habit_id"),
        date=args.get("date"),
        window_days=int(args.get("window_days") or 7),
    )


def run_life_habit_day(args: dict[str, Any]) -> dict[str, Any]:
    from ada.life.habits.reflection import habit_day

    return habit_day(date=args.get("date"))


def run_life_habit_week(args: dict[str, Any]) -> dict[str, Any]:
    from ada.life.habits.reflection import habit_window, write_habit_reflection_scratch

    days = args.get("days", 7)
    try:
        days_n = int(days)
    except (TypeError, ValueError):
        days_n = 7
    result = habit_window(days=days_n)
    write_habit_reflection_scratch(result)
    return result


DISPATCH = {
    "life_habit_create": run_life_habit_create,
    "life_habit_do": run_life_habit_do,
    "life_habit_miss": run_life_habit_miss,
    "life_routine_run": run_life_routine_run,
    "life_habit_status": run_life_habit_status,
    "life_habit_day": run_life_habit_day,
    "life_habit_week": run_life_habit_week,
}
