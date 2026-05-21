"""Motor param validation."""

from __future__ import annotations

from typing import Any

from ada.motor.types import SkillSpec
from ada.programme.packs import (
    KNOWN_PACKS,
    PACK_SKILL_ALLOWLIST,
    normalize_skill_ids,
    resolve_pack,
)
from ada.query_engine import QueryEngine


def validate_skill_params(
    spec: SkillSpec,
    params: dict[str, Any],
    *,
    mission_slug: str | None,
) -> str | None:
    """Return error message or None if valid."""
    if spec.mission_required and not (mission_slug and mission_slug.strip()):
        return f"skill {spec.id!r} requires mission_slug"
    extra = set(params) - set(spec.allowed_params)
    if extra and spec.allowed_params:
        return f"unknown params for {spec.id!r}: {sorted(extra)}"
    for key in spec.required_params:
        if key not in params or params[key] in (None, ""):
            return f"missing required param {key!r} for skill {spec.id!r}"
    return None


async def validate_skill_for_mission(
    qe: QueryEngine,
    spec: SkillSpec,
    mission_slug: str | None,
) -> str | None:
    """Return error if skill is not enabled for mission defaults (Hands H5)."""
    slug = (mission_slug or "").strip()
    if not slug:
        return None
    row = await qe.get_mission_by_slug(slug)
    if row is None:
        return f"no mission with slug {slug!r}"
    defaults = row.get("defaults_json")
    if not isinstance(defaults, dict):
        defaults = {}
    enabled = normalize_skill_ids(defaults.get("skills_enabled"))
    if not enabled:
        return None
    if spec.id not in enabled:
        return (
            f"skill {spec.id!r} not enabled on mission {slug!r} "
            f"(skills_enabled: {enabled})"
        )
    pack = resolve_pack(defaults)
    if pack and pack in KNOWN_PACKS:
        allowed = PACK_SKILL_ALLOWLIST[pack]
        if spec.id not in allowed:
            return f"skill {spec.id!r} not allowed for pack {pack!r}"
    return None
