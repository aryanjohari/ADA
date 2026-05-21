"""Bounded SQL/YAML ProgrammeDigest for WORK-mode chat injection (Phase D)."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from ada.mission_control.flags import collect_flags, flags_to_dicts
from ada.mission_tick import parse_tick_schedule_v1, tick_state_key
from ada.motor.registry import load_skill_registry
from ada.programme.packs import normalize_skill_ids, resolve_pack
from ada.observability.queries import (
    mission_tick_state_rows,
    task_status_counts,
    workflow_status_counts,
)

UTC = timezone.utc
PROGRAMME_DIGEST_MAX_BYTES_DEFAULT = 1500
_GOAL_PREVIEW_CHARS = 120
_BRIEF_PREVIEW_CHARS = 400


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _mission_row(
    conn: sqlite3.Connection, mission_id: int
) -> dict[str, Any] | None:
    cur = conn.execute(
        """
        SELECT id, slug, title, defaults_json, schedule_hint_json, brief_md
        FROM missions WHERE id = ?
        """,
        (mission_id,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    defaults_raw = str(row["defaults_json"] or "{}")
    try:
        defaults = json.loads(defaults_raw)
    except json.JSONDecodeError:
        defaults = {}
    if not isinstance(defaults, dict):
        defaults = {}
    sched = row["schedule_hint_json"]
    if isinstance(sched, str) and sched.strip():
        try:
            sched = json.loads(sched)
        except json.JSONDecodeError:
            sched = None
    brief_raw = str(row["brief_md"] or "")
    brief_preview = brief_raw[:_BRIEF_PREVIEW_CHARS]
    if len(brief_raw) > _BRIEF_PREVIEW_CHARS:
        brief_preview += "…"
    return {
        "id": int(row["id"]),
        "slug": str(row["slug"] or ""),
        "title": str(row["title"] or ""),
        "defaults_json": defaults,
        "schedule_hint_json": sched,
        "brief_md_preview": brief_preview if brief_raw.strip() else "",
    }


def _schedule_jobs_block(
    conn: sqlite3.Connection,
    *,
    mission_slug: str,
    schedule_hint_json: Any,
) -> list[dict[str, Any]]:
    jobs, err = parse_tick_schedule_v1(schedule_hint_json)
    if err or not jobs:
        return []
    tick_rows = {
        r["key"]: r["value"]
        for r in mission_tick_state_rows(conn, mission_slug=mission_slug)
    }
    out: list[dict[str, Any]] = []
    for job in jobs:
        jid = str(job.get("id") or "").strip()
        if not jid:
            continue
        action = job.get("action")
        if not isinstance(action, dict):
            action = {}
        atype = str(action.get("type") or "").strip()
        goal_raw = str(action.get("goal_text") or "").strip()
        preview = goal_raw[:_GOAL_PREVIEW_CHARS]
        if len(goal_raw) > _GOAL_PREVIEW_CHARS:
            preview += "…"
        key = tick_state_key(mission_slug, jid)
        raw_val = tick_rows.get(key)
        never_ran = raw_val is None
        last_run: str | None = None
        if raw_val is not None:
            last_run = str(raw_val).strip() or None
        out.append(
            {
                "id": jid,
                "action_type": atype,
                "min_interval_hours": float(job.get("min_interval_hours") or 24.0),
                "goal_text_preview": preview,
                "last_run_at": last_run,
                "never_ran": never_ran,
            }
        )
    return out


def _skills_block(defaults: dict[str, Any]) -> list[dict[str, Any]]:
    raw = defaults.get("skills_enabled")
    if not isinstance(raw, list):
        return []
    registry = load_skill_registry()
    out: list[dict[str, Any]] = []
    for sid in raw:
        skill_id = str(sid).strip()
        if not skill_id:
            continue
        spec = registry.get(skill_id)
        if spec is None:
            continue
        out.append(
            {
                "id": spec.id,
                "description": spec.description,
                "risk_tier": spec.risk_tier,
                "motor_type": spec.motor_type,
            }
        )
    return out


def _flags_top_n(
    conn: sqlite3.Connection,
    *,
    mission_id: int,
    mission_slug: str,
    top_n: int,
    profile_scope: bool,
    gemini_api_key: str,
    ada_job_queue: str,
    ada_kill_switch: bool,
    ada_profile: str,
    ada_profile_data_root: str,
    profile_fingerprint: str,
) -> list[dict[str, Any]]:
    flags = collect_flags(
        conn,
        mission_id=mission_id,
        mission_slug=mission_slug,
        profile_scope=profile_scope,
        gemini_api_key=gemini_api_key,
        ada_job_queue=ada_job_queue,
        ada_kill_switch=ada_kill_switch,
        ada_profile=ada_profile,
        ada_profile_data_root=ada_profile_data_root,
        profile_fingerprint=profile_fingerprint,
    )
    mission_flags = [f for f in flags if f.mission_id == mission_id]
    dicts = flags_to_dicts(mission_flags)
    trimmed: list[dict[str, Any]] = []
    for d in dicts[: max(0, top_n)]:
        trimmed.append(
            {
                "id": d.get("id"),
                "severity": d.get("severity"),
                "message": d.get("message"),
            }
        )
    return trimmed


def _digest_byte_size(digest: dict[str, Any]) -> int:
    return len(
        json.dumps(digest, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    )


def _trim_to_max_bytes(digest: dict[str, Any], max_bytes: int) -> dict[str, Any]:
    if _digest_byte_size(digest) <= max_bytes:
        return digest
    out = dict(digest)
    out["truncated"] = True
    for _ in range(64):
        if _digest_byte_size(out) <= max_bytes:
            return out
        jobs = out.get("schedule_jobs")
        if isinstance(jobs, list) and len(jobs) > 1:
            out["schedule_jobs"] = jobs[:-1]
            continue
        flags = out.get("flags_top_n")
        if isinstance(flags, list) and len(flags) > 1:
            out["flags_top_n"] = flags[:-1]
            continue
        skills = out.get("skills")
        if isinstance(skills, list) and len(skills) > 1:
            out["skills"] = skills[:-1]
            continue
        if isinstance(flags, list) and flags:
            out["flags_top_n"] = []
            continue
        if isinstance(jobs, list) and jobs:
            out["schedule_jobs"] = []
            continue
        if isinstance(skills, list) and skills:
            out["skills"] = []
            continue
        if out.get("brief_md_preview"):
            out["brief_md_preview"] = ""
            continue
        out.pop("workflow_status_counts", None)
        if _digest_byte_size(out) <= max_bytes:
            return out
        out.pop("task_status_counts", None)
        if _digest_byte_size(out) <= max_bytes:
            return out
        break
    return out


def build_programme_digest(
    conn: sqlite3.Connection,
    mission_id: int,
    *,
    mission_slug: str | None = None,
    max_bytes: int = PROGRAMME_DIGEST_MAX_BYTES_DEFAULT,
    flags_top_n: int = 8,
    profile_scope: bool = True,
    gemini_api_key: str = "",
    ada_job_queue: str = "legacy",
    ada_kill_switch: bool = False,
    ada_profile: str = "",
    ada_profile_data_root: str = "",
    profile_fingerprint: str = "",
) -> dict[str, Any]:
    """
    Assemble bounded ProgrammeDigest JSON (allowlisted fields only).

    Never includes raw defaults_json, payloads, or secrets.
    """
    row = _mission_row(conn, mission_id)
    if row is None:
        return {"schema_version": 1, "error": "mission_not_found", "mission_id": mission_id}

    slug = (mission_slug or row["slug"] or "").strip()
    defaults = row["defaults_json"]
    enabled_ids = normalize_skill_ids(defaults.get("skills_enabled"))
    skills_enforcement = bool(enabled_ids)
    pack = resolve_pack(defaults)
    digest: dict[str, Any] = {
        "schema_version": 1,
        "generated_at": _now_iso(),
        "mission_id": mission_id,
        "mission_slug": slug,
        "mission_title": row["title"],
        "brief_md_preview": row.get("brief_md_preview") or "",
        "pack": pack,
        "skills_enforcement": skills_enforcement,
        "schedule_jobs": _schedule_jobs_block(
            conn,
            mission_slug=slug,
            schedule_hint_json=row["schedule_hint_json"],
        ),
        "skills": _skills_block(defaults),
        "task_status_counts": task_status_counts(conn, mission_id=mission_id),
        "workflow_status_counts": workflow_status_counts(
            conn, mission_id=mission_id
        ),
        "flags_top_n": _flags_top_n(
            conn,
            mission_id=mission_id,
            mission_slug=slug,
            top_n=flags_top_n,
            profile_scope=profile_scope,
            gemini_api_key=gemini_api_key,
            ada_job_queue=ada_job_queue,
            ada_kill_switch=ada_kill_switch,
            ada_profile=ada_profile,
            ada_profile_data_root=ada_profile_data_root,
            profile_fingerprint=profile_fingerprint,
        ),
    }
    if not skills_enforcement:
        digest["skills_note"] = (
            "all actions available (not restricted)"
            if pack
            else "skills not restricted on this mission"
        )
    return _trim_to_max_bytes(digest, max_bytes)


def programme_block_from_digest(digest: dict[str, Any]) -> dict[str, Any]:
    """Subset for snapshot ``programme`` key (same builder output)."""
    keys = (
        "schema_version",
        "generated_at",
        "mission_id",
        "mission_slug",
        "mission_title",
        "brief_md_preview",
        "pack",
        "skills_enforcement",
        "skills_note",
        "schedule_jobs",
        "skills",
        "task_status_counts",
        "workflow_status_counts",
        "flags_top_n",
        "truncated",
    )
    return {k: digest[k] for k in keys if k in digest}
