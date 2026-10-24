"""Ordered life-domain fast-path hooks for harness.loop.run_turn.

Runtime order matches the prior inlined loop (food draft → meal → gym → time →
habits → dues → people → pack catch-all). Domains register as they extract;
unextracted domains stay as None until moved.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

ExecuteTool = Callable[..., None]
ReceiptData = Callable[[list[dict[str, Any]], str], dict[str, Any]]


@dataclass
class FastPathCtx:
    session: Any
    sink: Any
    history: list[Any]
    receipts: list[dict[str, Any]]
    user_text: str
    execute_tool: ExecuteTool
    receipt_data: ReceiptData


def try_food_draft_divert(ctx: FastPathCtx) -> tuple[str | None, str | None]:
    """Open meal-draft divert — first write hook (before meal log)."""
    from ada.life.food.fast_path import try_draft_divert

    return try_draft_divert(
        ctx.session,
        ctx.sink,
        ctx.history,
        ctx.receipts,
        ctx.user_text,
        execute_tool=ctx.execute_tool,
        receipt_data=ctx.receipt_data,
    )


def try_food_meal_write(ctx: FastPathCtx) -> tuple[str | None, str | None]:
    """Structural meal log — after draft divert, before gym."""
    from ada.life.food.fast_path import try_meal_write

    return try_meal_write(
        ctx.session,
        ctx.sink,
        ctx.history,
        ctx.receipts,
        ctx.user_text,
        execute_tool=ctx.execute_tool,
        receipt_data=ctx.receipt_data,
    )


def try_time_write(ctx: FastPathCtx) -> tuple[str | None, str | None]:
    from ada.life.time.fast_path import try_write_fast_path

    return try_write_fast_path(
        ctx.session,
        ctx.sink,
        ctx.history,
        ctx.receipts,
        ctx.user_text,
        execute_tool=ctx.execute_tool,
        receipt_data=ctx.receipt_data,
    )


def try_gym_write(ctx: FastPathCtx) -> tuple[str | None, str | None]:
    """Gym start/end/lift writes — called from loop before time (not in WRITE_FAST_PATHS yet)."""
    from ada.life.gym.fast_path import try_write_fast_path

    return try_write_fast_path(
        ctx.session,
        ctx.sink,
        ctx.history,
        ctx.receipts,
        ctx.user_text,
        execute_tool=ctx.execute_tool,
        receipt_data=ctx.receipt_data,
    )


def try_habit_write(ctx: FastPathCtx) -> tuple[str | None, str | None]:
    """Habit do/miss writes — called from loop after time, before dues."""
    from ada.life.habits.fast_path import try_write_fast_path

    return try_write_fast_path(
        ctx.session,
        ctx.sink,
        ctx.history,
        ctx.receipts,
        ctx.user_text,
        execute_tool=ctx.execute_tool,
        receipt_data=ctx.receipt_data,
    )


def try_people_fast_path(
    ctx: FastPathCtx,
    *,
    fast_path_read: Callable[..., tuple[str | None, str | None]],
    fast_path_confirm_bound: Callable[..., tuple[str | None, str | None]],
    life_save_fail_ack: str = "That didn't save — try once more.",
) -> tuple[str | None, str | None]:
    """People Observe+Agent reads / Agent writes — after dues, outside Agent-only block."""
    from ada.life.people.fast_path import try_people_fast_path as _try

    return _try(
        ctx.session,
        ctx.sink,
        ctx.history,
        ctx.receipts,
        ctx.user_text,
        execute_tool=ctx.execute_tool,
        receipt_data=ctx.receipt_data,
        fast_path_read=fast_path_read,
        fast_path_confirm_bound=fast_path_confirm_bound,
        life_save_fail_ack=life_save_fail_ack,
    )


# Write-path order for run_turn Agent mode:
# food draft → food meal → gym → time → habits → dues → people → pack catch-all.
# Loop still invokes these as separate blocks (meal keeps loop._fast_path_meal for
# test monkeypatches); collapse into one try_write_fast_paths pass in a later trim.
WRITE_FAST_PATHS: list[Callable[[FastPathCtx], tuple[str | None, str | None]]] = [
    try_food_draft_divert,
    try_food_meal_write,
    try_gym_write,
    try_time_write,
    try_habit_write,
]


def try_write_fast_paths(ctx: FastPathCtx) -> tuple[str | None, str | None]:
    """Run registered write fast-paths in order; first hit wins."""
    for hook in WRITE_FAST_PATHS:
        stop, text = hook(ctx)
        if stop:
            return stop, text
    return None, None
