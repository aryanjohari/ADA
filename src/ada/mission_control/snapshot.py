"""Bounded read-only mission control snapshot (SQLite-derived JSON)."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from ada.mission_control.flags import collect_flags, flags_to_dicts
from ada.mission_control.programme_digest import (
    build_programme_digest,
    programme_block_from_digest,
)
from ada.observability.queries import (
    mission_tick_state_rows,
    missions_overview_list,
    open_readonly_connection,
    system_jobs_stuck_summary,
    task_status_counts,
    workflow_status_counts,
)

SNAPSHOT_MAX_BYTES_DEFAULT = 12_000


def build_mission_control_snapshot(
    conn: sqlite3.Connection,
    *,
    mission_id: int | None = None,
    mission_slug: str | None = None,
    profile_scope: bool = True,
    gemini_api_key: str = "",
    ada_job_queue: str = "legacy",
    ada_kill_switch: bool = False,
    ada_profile: str = "",
    ada_profile_data_root: str = "",
    profile_fingerprint: str = "",
    max_bytes: int = SNAPSHOT_MAX_BYTES_DEFAULT,
    include_programme: bool = False,
) -> dict[str, Any]:
    """
    Assemble a bounded JSON snapshot for setup assist / CLI status.

    Contains only digests and counts — never raw secrets or full payloads.
    """
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
    snap: dict[str, Any] = {
        "schema_version": 1,
        "mission_id": mission_id,
        "mission_slug": mission_slug,
        "flags": flags_to_dicts(flags),
        "system_jobs_summary": system_jobs_stuck_summary(conn),
    }
    if mission_id is not None:
        snap["task_status_counts"] = task_status_counts(conn, mission_id=mission_id)
        snap["workflow_status_counts"] = workflow_status_counts(
            conn, mission_id=mission_id
        )
    if mission_slug:
        snap["tick_state"] = mission_tick_state_rows(conn, mission_slug=mission_slug)
    overview = missions_overview_list(
        conn, slug_filter=mission_slug if mission_slug else None
    )
    snap["missions_overview"] = [
        {
            "id": r["id"],
            "slug": r["slug"],
            "title": r["title"],
            "schedule_job_ids": r.get("schedule_job_ids"),
            "pending_goals": r.get("pending_goals"),
            "pending_workflows": r.get("pending_workflows"),
            "pending_system_jobs": r.get("pending_system_jobs"),
            "defaults_json_digest": r.get("defaults_json_digest"),
        }
        for r in overview
    ]
    if include_programme and mission_id is not None:
        digest = build_programme_digest(
            conn,
            mission_id,
            mission_slug=mission_slug,
            profile_scope=profile_scope,
            gemini_api_key=gemini_api_key,
            ada_job_queue=ada_job_queue,
            ada_kill_switch=ada_kill_switch,
            ada_profile=ada_profile,
            ada_profile_data_root=ada_profile_data_root,
            profile_fingerprint=profile_fingerprint,
        )
        snap["programme"] = programme_block_from_digest(digest)

    def _size(d: dict[str, Any]) -> int:
        return len(json.dumps(d, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))

    if _size(snap) <= max_bytes:
        return snap
    # Trim: overview → flags → programme → tick_state
    if mission_id is not None:
        snap["missions_overview"] = [
            r for r in snap["missions_overview"] if r["id"] == mission_id
        ]
    snap["flags"] = snap["flags"][:30]
    snap["truncated"] = True
    if _size(snap) > max_bytes:
        snap.pop("missions_overview", None)
        snap["flags"] = snap["flags"][:15]
    if _size(snap) > max_bytes:
        snap.pop("programme", None)
    if _size(snap) > max_bytes:
        snap.pop("tick_state", None)
    return snap


def build_snapshot_from_settings(
    settings: Any,
    *,
    mission_id: int | None = None,
    mission_slug: str | None = None,
    profile_scope: bool = True,
    max_bytes: int = SNAPSHOT_MAX_BYTES_DEFAULT,
    include_programme: bool = False,
) -> dict[str, Any]:
    conn = open_readonly_connection(settings.state_db_path)
    try:
        return build_mission_control_snapshot(
            conn,
            mission_id=mission_id,
            mission_slug=mission_slug,
            profile_scope=profile_scope,
            gemini_api_key=settings.gemini_api_key,
            ada_job_queue=settings.ada_job_queue,
            ada_kill_switch=settings.ada_kill_switch,
            ada_profile=settings.ada_profile,
            ada_profile_data_root=str(settings.ada_profile_data_root),
            profile_fingerprint=settings.profile_fingerprint,
            max_bytes=max_bytes,
            include_programme=include_programme,
        )
    finally:
        conn.close()
