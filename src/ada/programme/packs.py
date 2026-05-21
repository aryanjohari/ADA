"""Programme pack allowlists and skills_enabled validation (Hands H5)."""

from __future__ import annotations

from typing import Any

from ada.motor.registry import load_skill_registry

PACK_SKILL_ALLOWLIST: dict[str, frozenset[str]] = {
    "core-ops": frozenset({"daily_brief", "mission_tick_dry_run"}),
    "isr-publish": frozenset({"publish_entity_v1", "publish_keyword_v1"}),
    "isr-research": frozenset({"ingest_rss_mission", "weekly_research_goal"}),
    "generic-research": frozenset({"ingest_rss_mission", "weekly_research_goal"}),
    "job-hunt": frozenset({"ingest_rss_mission", "weekly_research_goal"}),
}
KNOWN_PACKS = frozenset(PACK_SKILL_ALLOWLIST)


def normalize_skill_ids(raw: list[Any] | None) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        sid = str(item).strip()
        if sid:
            out.append(sid)
    return out


def resolve_pack(defaults_json: dict[str, Any]) -> str | None:
    pack = defaults_json.get("pack")
    if pack is None:
        return None
    text = str(pack).strip()
    return text or None


def validate_skills_exist(ids: list[str]) -> str | None:
    if not ids:
        return None
    registry = load_skill_registry()
    unknown = [sid for sid in ids if sid not in registry]
    if not unknown:
        return None
    known = sorted(registry.keys())
    return (
        f"unknown skill id(s): {unknown!r}; "
        f"known skills: {known}"
    )


def validate_skills_for_pack(ids: list[str], pack: str) -> str | None:
    if pack not in KNOWN_PACKS:
        return f"unknown pack {pack!r}; known packs: {sorted(KNOWN_PACKS)}"
    allowed = PACK_SKILL_ALLOWLIST[pack]
    bad = [sid for sid in ids if sid not in allowed]
    if not bad:
        return None
    return (
        f"skill(s) {bad!r} not allowed for pack {pack!r}; "
        f"pack allows: {sorted(allowed)}"
    )


def validate_programme_skills(
    skills_enabled: list[str],
    defaults_json: dict[str, Any],
) -> str | None:
    """
    Validate programme skills_enabled and pack consistency.

    Returns an error message or None if valid.
    """
    ids = normalize_skill_ids(skills_enabled)
    err = validate_skills_exist(ids)
    if err:
        return err
    pack = resolve_pack(defaults_json)
    if pack is None:
        return None
    if pack not in KNOWN_PACKS:
        return f"unknown pack {pack!r}; known packs: {sorted(KNOWN_PACKS)}"
    if not ids:
        return f"pack {pack!r} requires explicit skills_enabled"
    return validate_skills_for_pack(ids, pack)
