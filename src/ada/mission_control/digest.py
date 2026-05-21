"""Deterministic operator brief from SQLite flags + bounded snapshot (no LLM)."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from ada.config import Settings
from ada.mission_control.flags import collect_flags, flags_to_dicts
from ada.mission_control.snapshot import build_mission_control_snapshot
from ada.observability.queries import mission_id_from_slug, open_readonly_connection

UTC = timezone.utc

DAEMON_GOAL_SUFFIX = (
    "\n\n---\n"
    "Daemon: Summarize only the grounded brief above. "
    "Use get_mission_control_snapshot for job/workflow counts — do not invent numbers."
)


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def render_brief(
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
) -> str:
    """Markdown brief from flags + snapshot only — never invents job counts."""
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
    snap = build_mission_control_snapshot(
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
    lines: list[str] = [
        "# ADA brief",
        f"generated_at: {_now_iso()}",
    ]
    if mission_slug:
        lines.append(f"mission: {mission_slug}")
    if ada_profile:
        lines.append(f"profile: {ada_profile}")
    lines.append("")

    if flags:
        lines.append("## Flags")
        for f in flags:
            rec = f.recovery_action or ""
            lines.append(f"- [{f.severity}] `{f.id}`: {f.message}")
            if rec:
                lines.append(f"  - recovery: {rec}")
    else:
        lines.append("## Flags")
        lines.append("- (none)")

    lines.append("")
    lines.append("## Snapshot (SQL-derived)")
    sj = snap.get("system_jobs_summary")
    if isinstance(sj, dict):
        for k in ("dead", "pending_stale", "expired_lease"):
            if k in sj:
                lines.append(f"- system_jobs_{k}: {sj[k]}")
    tsc = snap.get("task_status_counts")
    if isinstance(tsc, dict):
        for k, v in sorted(tsc.items()):
            lines.append(f"- tasks_{k}: {v}")
    wsc = snap.get("workflow_status_counts")
    if isinstance(wsc, dict):
        for k, v in sorted(wsc.items()):
            lines.append(f"- workflows_{k}: {v}")
    tick = snap.get("tick_state")
    if isinstance(tick, list) and tick:
        lines.append("- tick_jobs:")
        for row in tick[:10]:
            if isinstance(row, dict):
                jid = row.get("job_id") or row.get("id") or "?"
                lines.append(f"  - {jid}: last_run={row.get('last_run_at', '?')}")
    if snap.get("truncated"):
        lines.append("- note: snapshot truncated for size")

    return "\n".join(lines) + "\n"


def render_brief_from_settings(
    settings: Settings,
    *,
    mission_slug: str | None = None,
) -> str:
    conn = open_readonly_connection(settings.state_db_path)
    try:
        mid: int | None = None
        slug = (mission_slug or "").strip() or None
        if slug:
            mid = mission_id_from_slug(conn, slug)
        return render_brief(
            conn,
            mission_id=mid,
            mission_slug=slug,
            profile_scope=True,
            gemini_api_key=settings.gemini_api_key,
            ada_job_queue=settings.ada_job_queue,
            ada_kill_switch=settings.ada_kill_switch,
            ada_profile=settings.ada_profile,
            ada_profile_data_root=str(settings.ada_profile_data_root),
            profile_fingerprint=settings.profile_fingerprint,
        )
    finally:
        conn.close()


def goal_text_for_daily_brief(brief_md: str) -> str:
    return brief_md.strip() + DAEMON_GOAL_SUFFIX


def brief_artifact_path(settings: Settings, *, day: date | None = None) -> Path:
    d = day or datetime.now(UTC).date()
    base = settings.data_dir / "artifacts" / "brief"
    base.mkdir(parents=True, exist_ok=True)
    slug = (settings.ada_profile or "default").strip() or "default"
    return base / f"{slug}-{d.isoformat()}.md"


def write_brief_artifact(settings: Settings, text: str, *, day: date | None = None) -> Path:
    path = brief_artifact_path(settings, day=day)
    path.write_text(text, encoding="utf-8")
    return path


def build_profile_brief_payload(settings: Settings) -> dict[str, Any]:
    """Read-only cross-mission brief JSON (no writes)."""
    conn = open_readonly_connection(settings.state_db_path)
    try:
        flags = collect_flags(
            conn,
            mission_id=None,
            mission_slug=None,
            profile_scope=True,
            gemini_api_key=settings.gemini_api_key,
            ada_job_queue=settings.ada_job_queue,
            ada_kill_switch=settings.ada_kill_switch,
            ada_profile=settings.ada_profile,
            ada_profile_data_root=str(settings.ada_profile_data_root),
            profile_fingerprint=settings.profile_fingerprint,
        )
        from ada.observability.queries import missions_overview_list

        missions_raw = missions_overview_list(conn, slug_filter=None)
        flag_by_mid: dict[int, int] = {}
        for f in flags:
            if f.mission_id is not None:
                flag_by_mid[f.mission_id] = flag_by_mid.get(f.mission_id, 0) + 1

        missions_out = [
            {
                "id": r["id"],
                "slug": r["slug"],
                "title": r["title"],
                "pending_goals": r.get("pending_goals"),
                "pending_workflows": r.get("pending_workflows"),
                "pending_system_jobs": r.get("pending_system_jobs"),
                "flag_count": flag_by_mid.get(int(r["id"]), 0),
            }
            for r in missions_raw
        ]
        return {
            "schema_version": 1,
            "generated_at": _now_iso(),
            "profile": settings.ada_profile,
            "profile_fingerprint": settings.profile_fingerprint,
            "flags": flags_to_dicts(flags),
            "missions": missions_out,
            "global_kernel_note": (
                "Rows with mission_id IS NULL (triage categories, shared RSS pool, "
                "market_metrics) are profile-global — see docs/CROSS_MISSION_READ.md."
            ),
        }
    finally:
        conn.close()
