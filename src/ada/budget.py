"""Phase 0 control plane: global token budgets (UTC) and daemon gate helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ada.config import Settings
    from ada.query_engine import QueryEngine


def utc_today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def utc_year_month_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def global_budget_blocks(
    *,
    day_total: int,
    month_total: int,
    daily_limit: int | None,
    monthly_limit: int | None,
) -> tuple[bool, str | None]:
    """Returns (blocked, scope) where scope is 'daily' or 'monthly' if blocked."""
    if daily_limit is not None and day_total >= daily_limit:
        return True, "daily"
    if monthly_limit is not None and month_total >= monthly_limit:
        return True, "monthly"
    return False, None


def daemon_should_execute_goal(
    *,
    kill_switch: bool,
    day_total: int,
    month_total: int,
    daily_limit: int | None,
    monthly_limit: int | None,
) -> tuple[bool, str | None]:
    """
    Returns (allowed, block_reason).
    block_reason: 'kill_switch' | 'global_budget_daily' | 'global_budget_monthly' | None
    """
    if kill_switch:
        return False, "kill_switch"
    blocked, scope = global_budget_blocks(
        day_total=day_total,
        month_total=month_total,
        daily_limit=daily_limit,
        monthly_limit=monthly_limit,
    )
    if blocked:
        return False, f"global_budget_{scope}"
    return True, None


async def maybe_log_daemon_block(
    qe: QueryEngine,
    *,
    block_reason: str,
    totals: dict[str, int],
    settings: Settings,
) -> None:
    """
    Log at most once per UTC day per block kind to avoid flooding action_log on every poll.
    """
    day = utc_today_str()
    if block_reason == "kill_switch":
        key = f"daemon.log.kill_switch.{day}"
        kind = "kill_switch_skip"
        payload: dict[str, Any] = {"reason": block_reason, "utc_date": day}
    elif block_reason == "global_budget_daily":
        key = f"daemon.log.budget.daily.{day}"
        kind = "global_budget_block"
        payload = {
            "scope": "daily",
            "utc_date": day,
            "used": totals.get("day_total", 0),
            "limit": settings.ada_daily_token_budget,
        }
    elif block_reason == "global_budget_monthly":
        key = f"daemon.log.budget.monthly.{day}"
        kind = "global_budget_block"
        payload = {
            "scope": "monthly",
            "utc_date": day,
            "year_month": utc_year_month_str(),
            "used": totals.get("month_total", 0),
            "limit": settings.ada_monthly_token_budget,
        }
    else:
        return
    if await qe.state_get(key):
        return
    await qe.append_action_log(kind, payload, session_id=None)
    await qe.state_set(key, "1")
