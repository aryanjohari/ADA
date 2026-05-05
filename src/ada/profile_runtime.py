"""Runtime guards for profile isolation."""

from __future__ import annotations

from ada.config import Settings
from ada.config_deprecation import (
    deprecated_audit_already_logged,
    mark_deprecated_audit_logged,
    pending_deprecated_audit_envs,
)
from ada.query_engine import QueryEngine


async def enforce_profile_identity(qe: QueryEngine, settings: Settings) -> None:
    """Fail fast when runtime profile does not match DB identity."""
    await qe.ensure_profile_identity(
        profile_id=settings.ada_profile,
        profile_data_root=str(settings.ada_profile_data_root),
        profile_fingerprint=settings.profile_fingerprint,
    )
    if deprecated_audit_already_logged():
        return
    names = pending_deprecated_audit_envs()
    if names is None:
        return
    mark_deprecated_audit_logged()
    if not names:
        return
    try:
        await qe.append_action_log(
            "deprecated_env_used",
            {"envs": names, "profile": settings.ada_profile},
            None,
        )
    except Exception:
        pass
