"""life_gym_* / life_lift_log / life_split_set gateway handlers."""

from __future__ import annotations

from typing import Any

from ada.logs import gym as gym_mod
from ada.logs.receipts import write_life_crumb


def _write(tool: str, receipt_id: str, outcome: dict[str, Any]) -> dict[str, Any]:
    if receipt_id and outcome.get("ok"):
        write_life_crumb(receipt_id=receipt_id, tool=tool, outcome=outcome)
    return outcome


def run_life_split_set(args: dict[str, Any]) -> dict[str, Any]:
    """Sticky gym_split FACT after Confirm Yes (M22 teach-in-flow)."""
    from ada.logs import gym_split as split_mod

    days = args.get("days")
    if days is None and isinstance(args.get("gym_split"), dict):
        days = (args.get("gym_split") or {}).get("days")
    outcome = split_mod.set_gym_split(
        days=days if isinstance(days, dict) else {},
        confirmed=bool(args.get("confirmed", False)),
        schema_version=int(args.get("schema_version") or 1),
    )
    if outcome.get("needs_confirm"):
        outcome["ok"] = False
    return outcome


def run_life_gym_start(args: dict[str, Any]) -> dict[str, Any]:
    receipt_id = str(args.get("receipt_id") or "")
    return _write(
        "life_gym_start",
        receipt_id,
        gym_mod.gym_start(receipt_id=receipt_id, split_day=args.get("split_day")),
    )


def run_life_lift_log(args: dict[str, Any]) -> dict[str, Any]:
    receipt_id = str(args.get("receipt_id") or "")
    sets = args.get("sets") or []
    if not sets:
        raise ValueError("sets required")
    return _write(
        "life_lift_log",
        receipt_id,
        gym_mod.lift_log(
            receipt_id=receipt_id,
            sets=sets,
            session_id=args.get("session_id"),
        ),
    )


def run_life_gym_end(args: dict[str, Any]) -> dict[str, Any]:
    receipt_id = str(args.get("receipt_id") or "")
    return _write(
        "life_gym_end",
        receipt_id,
        gym_mod.gym_end(
            receipt_id=receipt_id,
            session_id=args.get("session_id"),
            notes=args.get("notes"),
        ),
    )


def run_life_gym_status(args: dict[str, Any]) -> dict[str, Any]:
    return gym_mod.gym_status(date=args.get("date"))


def run_life_gym_day(args: dict[str, Any]) -> dict[str, Any]:
    from ada.life.gym.reflection import gym_day

    return gym_day(date=args.get("date"))


def run_life_gym_week(args: dict[str, Any]) -> dict[str, Any]:
    from ada.life.gym.reflection import gym_window, write_gym_reflection_scratch

    days = args.get("days", 7)
    try:
        days_n = int(days)
    except (TypeError, ValueError):
        days_n = 7
    result = gym_window(days=days_n)
    write_gym_reflection_scratch(result)
    return result


DISPATCH = {
    "life_gym_start": run_life_gym_start,
    "life_lift_log": run_life_lift_log,
    "life_gym_end": run_life_gym_end,
    "life_gym_status": run_life_gym_status,
    "life_gym_day": run_life_gym_day,
    "life_gym_week": run_life_gym_week,
    "life_split_set": run_life_split_set,
}
