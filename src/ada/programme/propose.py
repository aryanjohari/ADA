"""Read-only programme propose (no SQLite writes)."""

from __future__ import annotations

import json
from typing import Any

from ada.programme.packet import ProgrammePacket, validate_packet_dict
from ada.programme.packs import validate_programme_skills


def propose_packet(raw: str | dict[str, Any]) -> dict[str, Any]:
    """Validate and return canonical packet dict. Never writes DB."""
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            return {"error": f"invalid JSON: {e}"}
    else:
        data = raw
    if not isinstance(data, dict):
        return {"error": "packet must be a JSON object"}
    try:
        packet = validate_packet_dict(data)
    except Exception as e:
        return {"error": str(e)}
    err = validate_programme_skills(packet.skills_enabled, packet.defaults_json)
    if err:
        return {"error": err}
    out = packet.model_dump(mode="json")
    brief = packet.brief_md.strip()
    preview = brief[:400]
    if len(brief) > 400:
        preview += "…"
    return {
        "packet": out,
        "summary": {
            "mission_slug": packet.mission_slug,
            "title": packet.title,
            "knowledge_source_count": len(packet.knowledge_sources),
            "cron_line_count": len(packet.recommended_cron),
            "skills_enabled": list(packet.skills_enabled),
            "risk_summary": packet.risk_summary,
            "brief_md_chars": len(brief),
            "brief_md_preview": preview if brief else "",
        },
    }
