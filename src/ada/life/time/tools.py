"""life_time_* gateway handlers."""

from __future__ import annotations

from typing import Any

from ada.logs import time as time_mod
from ada.logs.receipts import write_life_crumb


def _write(tool: str, receipt_id: str, outcome: dict[str, Any]) -> dict[str, Any]:
    if receipt_id and outcome.get("ok"):
        write_life_crumb(receipt_id=receipt_id, tool=tool, outcome=outcome)
    return outcome


def run_life_time_start(args: dict[str, Any]) -> dict[str, Any]:
    receipt_id = str(args.get("receipt_id") or "")
    kind = args.get("kind")
    if not kind:
        raise ValueError("kind required")
    return _write(
        "life_time_start",
        receipt_id,
        time_mod.start_block(
            kind=str(kind),
            label=args.get("label"),
            receipt_id=receipt_id,
        ),
    )


def run_life_time_stop(args: dict[str, Any]) -> dict[str, Any]:
    receipt_id = str(args.get("receipt_id") or "")
    return _write(
        "life_time_stop",
        receipt_id,
        time_mod.stop_block(receipt_id=receipt_id, block_id=args.get("block_id")),
    )


def run_life_time_status(args: dict[str, Any]) -> dict[str, Any]:
    return time_mod.time_status()


def run_life_time_day(args: dict[str, Any]) -> dict[str, Any]:
    from ada.life.time.reflection import time_day

    return time_day(date=args.get("date"))


def run_life_time_week(args: dict[str, Any]) -> dict[str, Any]:
    from ada.life.time.reflection import time_window, write_time_reflection_scratch

    days = args.get("days", 7)
    try:
        days_n = int(days)
    except (TypeError, ValueError):
        days_n = 7
    result = time_window(days=days_n)
    write_time_reflection_scratch(result)
    return result


DISPATCH = {
    "life_time_start": run_life_time_start,
    "life_time_stop": run_life_time_stop,
    "life_time_status": run_life_time_status,
    "life_time_day": run_life_time_day,
    "life_time_week": run_life_time_week,
}
