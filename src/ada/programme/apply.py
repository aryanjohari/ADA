"""Apply ProgrammePacket after operator approval (closed mutations)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ada.config import Settings
from ada.programme.packet import ProgrammePacket
from ada.programme.packs import validate_programme_skills
from ada.query_engine import QueryEngine


async def apply_packet(
    qe: QueryEngine,
    settings: Settings,
    packet: ProgrammePacket,
    *,
    session_id: int | None = None,
) -> dict[str, Any]:
    """
    Closed mutations only:
    - missions upsert (slug, title, defaults_json, schedule_hint_json)
    - knowledge_sources via store
    - artifacts/cron/<slug>.snippet
    - defaults_json.skills_enabled merge
    """
    err = validate_programme_skills(packet.skills_enabled, packet.defaults_json)
    if err:
        return {"ok": False, "error": err}
    slug = packet.mission_slug.strip()
    existing = await qe.get_mission_by_slug(slug)
    defaults = dict(packet.defaults_json)
    if packet.skills_enabled:
        defaults["skills_enabled"] = list(packet.skills_enabled)
    schedule = packet.schedule_hint_json
    brief = packet.brief_md.strip()
    niche = defaults.get("niche") if isinstance(defaults.get("niche"), str) else None
    topic = defaults.get("topic") if isinstance(defaults.get("topic"), str) else None

    if existing is None:
        mid = await qe.create_mission(
            slug=slug,
            title=packet.title.strip() or slug,
            niche=niche,
            topic=topic,
            defaults_json=defaults,
            brief_md=brief,
            schedule_hint_json=schedule,
        )
        created = True
    else:
        mid = int(existing["id"])
        await qe.update_mission_meta(
            slug,
            title=packet.title.strip() or None,
            brief_md=brief,
            schedule_hint_json=schedule,
        )
        await qe.update_mission_defaults_json(slug, defaults, force=True)
        created = False

    sources_added: list[dict[str, str]] = []
    for ks in packet.knowledge_sources:
        url = ks.url.strip()
        if not url:
            continue
        kind = ks.kind.strip() or "rss"
        if kind not in ("api", "rss", "web", "brand"):
            kind = "rss"
        kid = await qe.insert_knowledge_source(
            kind,  # type: ignore[arg-type]
            label=url,
            base_url=url,
            mission_id=mid,
        )
        sources_added.append({"id": str(kid), "url": url, "kind": kind})

    cron_path = _write_cron_snippet(settings, slug, packet)
    await qe.append_action_log(
        "programme_apply",
        {
            "mission_slug": slug,
            "created": created,
            "mission_id": mid,
            "sources_added": len(sources_added),
            "cron_snippet": str(cron_path) if cron_path else None,
        },
        session_id=session_id,
    )
    return {
        "ok": True,
        "mission_id": mid,
        "mission_slug": slug,
        "created": created,
        "sources_added": sources_added,
        "cron_snippet_path": str(cron_path) if cron_path else None,
    }


def _write_cron_snippet(
    settings: Settings, slug: str, packet: ProgrammePacket
) -> Path | None:
    if not packet.recommended_cron:
        return None
    base = settings.data_dir / "artifacts" / "cron"
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"{slug}.snippet"
    lines: list[str] = []
    for entry in packet.recommended_cron:
        if entry.comment.strip():
            lines.append(f"# {entry.comment.strip()}")
        if entry.line.strip():
            lines.append(entry.line.strip())
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


async def confirm_and_apply(
    qe: QueryEngine,
    settings: Settings,
    packet: ProgrammePacket,
    *,
    approved: bool,
    session_id: int | None = None,
) -> dict[str, Any]:
    if not approved:
        await qe.append_action_log(
            "programme_apply_denied",
            {"mission_slug": packet.mission_slug},
            session_id=session_id,
        )
        return {"ok": False, "denied": True}
    return await apply_packet(qe, settings, packet, session_id=session_id)
