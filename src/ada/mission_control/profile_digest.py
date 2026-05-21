"""Bounded profile-wide digest for Entity (OPEN) chat injection."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from ada.mission_control.flags import collect_flags, flags_to_dicts
from ada.observability.queries import missions_overview_list, system_jobs_stuck_summary
from ada.programme.packs import normalize_skill_ids, resolve_pack

UTC = timezone.utc
PROFILE_DIGEST_MAX_BYTES_DEFAULT = 1500
_BRIEF_PREVIEW_CHARS = 80


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _digest_byte_size(digest: dict[str, Any]) -> int:
    return len(json.dumps(digest, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def _brief_md_preview(brief_raw: str) -> str:
    text = str(brief_raw or "").strip()
    if not text:
        return ""
    preview = text[:_BRIEF_PREVIEW_CHARS]
    if len(text) > _BRIEF_PREVIEW_CHARS:
        preview += "…"
    return preview


def _mission_enrichment_by_id(
    conn: sqlite3.Connection, mission_ids: list[int]
) -> dict[int, dict[str, Any]]:
    if not mission_ids:
        return {}
    placeholders = ",".join("?" * len(mission_ids))
    cur = conn.execute(
        f"""
        SELECT id, brief_md, defaults_json
        FROM missions
        WHERE id IN ({placeholders})
        """,
        tuple(mission_ids),
    )
    out: dict[int, dict[str, Any]] = {}
    for row in cur.fetchall():
        mid = int(row["id"])
        defaults_raw = str(row["defaults_json"] or "{}")
        try:
            defaults = json.loads(defaults_raw)
        except json.JSONDecodeError:
            defaults = {}
        if not isinstance(defaults, dict):
            defaults = {}
        enabled_ids = normalize_skill_ids(defaults.get("skills_enabled"))
        out[mid] = {
            "pack": resolve_pack(defaults),
            "skills_enforcement": bool(enabled_ids),
            "brief_md_preview": _brief_md_preview(str(row["brief_md"] or "")),
        }
    return out


def _trim_to_max_bytes(digest: dict[str, Any], max_bytes: int) -> dict[str, Any]:
    if _digest_byte_size(digest) <= max_bytes:
        return digest
    out = dict(digest)
    out["truncated"] = True
    for _ in range(128):
        if _digest_byte_size(out) <= max_bytes:
            return out
        missions = out.get("missions")
        if isinstance(missions, list):
            trimmed = False
            for m in reversed(missions):
                if isinstance(m, dict) and m.get("brief_md_preview"):
                    m["brief_md_preview"] = ""
                    trimmed = True
                    break
            if trimmed:
                continue
            if len(missions) > 1:
                out["missions"] = missions[:-1]
                continue
        flags = out.get("flags_top_n")
        if isinstance(flags, list) and len(flags) > 4:
            out["flags_top_n"] = flags[:4]
            continue
        if isinstance(missions, list) and len(missions) > 8:
            out["missions"] = missions[:8]
            continue
        out.pop("system_jobs_summary", None)
        if _digest_byte_size(out) <= max_bytes:
            return out
        if isinstance(flags, list) and len(flags) > 2:
            out["flags_top_n"] = flags[:2]
            continue
        if isinstance(missions, list) and len(missions) > 4:
            out["missions"] = missions[:4]
            continue
        if isinstance(flags, list) and flags:
            out["flags_top_n"] = []
            continue
        if isinstance(missions, list) and missions:
            out["missions"] = []
            continue
        break
    while _digest_byte_size(out) > max_bytes:
        flags = out.get("flags_top_n")
        missions = out.get("missions")
        if isinstance(flags, list) and flags:
            out["flags_top_n"] = flags[: max(0, len(flags) - 1)]
            continue
        if isinstance(missions, list) and missions:
            out["missions"] = missions[: max(0, len(missions) - 1)]
            continue
        out.pop("system_jobs_summary", None)
        if _digest_byte_size(out) <= max_bytes:
            break
        if out.get("profile"):
            out.pop("profile", None)
            continue
        break
    return out


def build_profile_digest(
    conn: sqlite3.Connection,
    *,
    max_bytes: int = PROFILE_DIGEST_MAX_BYTES_DEFAULT,
    flags_top_n: int = 12,
    missions_max: int = 20,
    profile_scope: bool = True,
    gemini_api_key: str = "",
    ada_job_queue: str = "legacy",
    ada_kill_switch: bool = False,
    ada_profile: str = "",
    ada_profile_data_root: str = "",
    profile_fingerprint: str = "",
) -> dict[str, Any]:
    """
    Profile-wide digest: mission slugs, top flags, system job summary.

    Never includes raw ``defaults_json``, schedules, or secrets.
    """
    flags = collect_flags(
        conn,
        mission_id=None,
        mission_slug=None,
        profile_scope=profile_scope,
        gemini_api_key=gemini_api_key,
        ada_job_queue=ada_job_queue,
        ada_kill_switch=ada_kill_switch,
        ada_profile=ada_profile,
        ada_profile_data_root=ada_profile_data_root,
        profile_fingerprint=profile_fingerprint,
    )
    flag_dicts = flags_to_dicts(flags)[:flags_top_n]
    missions_raw = missions_overview_list(conn, slug_filter=None)
    slice_raw = missions_raw[:missions_max]
    enrichment = _mission_enrichment_by_id(
        conn, [int(r["id"]) for r in slice_raw]
    )
    missions_out: list[dict[str, Any]] = []
    for r in slice_raw:
        mid = int(r["id"])
        extra = enrichment.get(mid, {})
        missions_out.append(
            {
                "id": mid,
                "slug": str(r["slug"] or ""),
                "title": str(r["title"] or ""),
                "pending_goals": r.get("pending_goals"),
                "flag_count_hint": r.get("pending_system_jobs"),
                "pack": extra.get("pack"),
                "skills_enforcement": extra.get("skills_enforcement", False),
                "brief_md_preview": extra.get("brief_md_preview") or "",
            }
        )
    digest: dict[str, Any] = {
        "schema_version": 1,
        "generated_at": _now_iso(),
        "profile_scope": True,
        "missions": missions_out,
        "flags_top_n": flag_dicts,
        "system_jobs_summary": system_jobs_stuck_summary(conn),
    }
    if ada_profile:
        digest["profile"] = ada_profile
    return _trim_to_max_bytes(digest, max_bytes)
