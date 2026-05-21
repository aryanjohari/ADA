"""Resolve programme knobs: mission ``defaults_json`` over process env (Phase A/B)."""

from __future__ import annotations

from typing import Any

from ada.query_engine import QueryEngine


def resolve_programme_str(
    *,
    mission_defaults: dict[str, Any],
    key: str,
    env_value: Any,
) -> str:
    """Mission non-empty value wins; else env; else empty."""
    raw = mission_defaults.get(key)
    if raw is not None and str(raw).strip():
        return str(raw).strip()
    if env_value is not None and str(env_value).strip():
        return str(env_value).strip()
    return ""


def overlay_tick_merged(
    merged: dict[str, Any],
    mission_defaults: dict[str, Any],
    *,
    gsc_site_url_env: str,
) -> dict[str, Any]:
    """Apply mission-over-env for tick GSC site URL."""
    out = dict(merged)
    out["gsc_site_url"] = resolve_programme_str(
        mission_defaults=mission_defaults,
        key="gsc_site_url",
        env_value=gsc_site_url_env,
    )
    return out


async def mission_defaults_for_slug(
    qe: QueryEngine, mission_slug: str | None
) -> dict[str, Any]:
    if not mission_slug or not str(mission_slug).strip():
        return {}
    row = await qe.get_mission_by_slug(str(mission_slug).strip())
    if row is None:
        return {}
    raw = row.get("defaults_json")
    return dict(raw) if isinstance(raw, dict) else {}


def effective_gsc_site_url(
    *, mission_defaults: dict[str, Any], env_site: str
) -> str:
    return resolve_programme_str(
        mission_defaults=mission_defaults,
        key="gsc_site_url",
        env_value=env_site,
    )


def effective_triage_lead_daily_cap(
    *, mission_defaults: dict[str, Any], env_cap: int
) -> int:
    raw = resolve_programme_str(
        mission_defaults=mission_defaults,
        key="triage_lead_daily_cap",
        env_value=str(env_cap),
    )
    if not raw:
        return int(env_cap)
    try:
        return max(0, int(raw))
    except ValueError:
        return int(env_cap)


def effective_int_programme(
    *,
    mission_defaults: dict[str, Any],
    key: str,
    env_value: int,
) -> int:
    raw = resolve_programme_str(
        mission_defaults=mission_defaults,
        key=key,
        env_value=str(env_value),
    )
    if not raw:
        return int(env_value)
    try:
        return int(raw)
    except ValueError:
        return int(env_value)
