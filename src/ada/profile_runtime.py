"""Runtime guards for profile isolation."""

from __future__ import annotations

from ada.config import Settings
from ada.query_engine import QueryEngine


async def enforce_profile_identity(qe: QueryEngine, settings: Settings) -> None:
    """Fail fast when runtime profile does not match DB identity."""
    await qe.ensure_profile_identity(
        profile_id=settings.ada_profile,
        profile_data_root=str(settings.ada_profile_data_root),
        profile_fingerprint=settings.profile_fingerprint,
    )
