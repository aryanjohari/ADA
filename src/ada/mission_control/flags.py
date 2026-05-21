"""Deterministic operator flags derived from SQLite (no LLM inference)."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from ada.mission_tick import (
    job_due,
    parse_last_run_iso,
    parse_tick_schedule_v1,
    tick_state_key,
    utc_now,
)
from ada.observability.queries import (
    _column_exists,
    _table_exists,
    gate_failed_steps_recent,
    mission_tick_state_rows,
    missions_overview_list,
    open_readonly_connection,
    system_jobs_stuck_summary,
)

UTC = timezone.utc

# Recovery hints shown in HUD / doctor (static strings).
RECOVERY: dict[str, str] = {
    "profile_fingerprint_mismatch": "Align ADA_PROFILE / ADA_PROFILE_DATA_ROOT with state.db profile.* keys.",
    "gemini_api_key_missing": "Set GEMINI_API_KEY in profile .env.",
    "job_queue_mode_invalid": "Set ADA_JOB_QUEUE to legacy or system_jobs.",
    "system_jobs_dead": "ada jobs list --status dead; ada jobs retry <id>",
    "system_jobs_expired_lease": "Ensure single ada daemon (system_jobs mode); wait lease reclaim.",
    "system_jobs_pending_stale": "Inspect job kind and payload digest; ada jobs cancel or retry.",
    "mission_pending_system_jobs": "ada jobs list --mission-id <id>",
    "mission_pending_workflows": "ada workflow status <id>",
    "mission_pending_goals": "ada goal list --mission <slug>",
    "mission_tick_job_overdue": "ada mission tick --mission <slug> --dry-run then live tick",
    "mission_tick_never_ran": "Configure cron for ada mission tick; run first tick.",
    "workflow_step_failed": "ada workflow status <workflow_id>",
    "gate_step_failed_recent": "ada gate-failures; improve graph facts for entity publish",
    "publish_deploy_blocked": "ada approval per docs/operator-publish-gate.md",
    "global_budget_block": "Raise ADA_DAILY/MONTHLY_TOKEN_BUDGET or wait UTC reset",
    "kill_switch_active": "Unset ADA_KILL_SWITCH when ready to run daemon",
    "chat_task_missing_mission": "ada chat --mission <slug> (or ADA_CHAT_DEFAULT_MISSION)",
    "messages_tombstoned_recent": "Review transcript for failed model legs",
    "double_job_plane_risk": "See docs/JOB_QUEUE_SINGLE_OWNER.md — one job plane per state.db",
}

PENDING_STALE_HOURS = 24
TOMBSTONE_RECENT_HOURS = 48
ACTION_LOG_RECENT_HOURS = 72


@dataclass(frozen=True)
class MissionFlag:
    id: str
    severity: str  # info | warn | error
    message: str
    observed_at: str
    mission_id: int | None = None
    source_table: str | None = None
    source_id: str | None = None
    recovery_action: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "severity": self.severity,
            "message": self.message,
            "observed_at": self.observed_at,
            "mission_id": self.mission_id,
            "source_table": self.source_table,
            "source_id": self.source_id,
            "recovery_action": self.recovery_action or RECOVERY.get(self.id, ""),
        }


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _flag(
    flag_id: str,
    severity: str,
    message: str,
    *,
    mission_id: int | None = None,
    source_table: str | None = None,
    source_id: str | None = None,
    observed_at: str | None = None,
) -> MissionFlag:
    return MissionFlag(
        id=flag_id,
        severity=severity,
        message=message,
        observed_at=observed_at or _now_iso(),
        mission_id=mission_id,
        source_table=source_table,
        source_id=source_id,
        recovery_action=RECOVERY.get(flag_id, ""),
    )


def flags_to_dicts(flags: list[MissionFlag]) -> list[dict[str, Any]]:
    return [f.to_dict() for f in flags]


def _read_profile_state(conn: sqlite3.Connection) -> dict[str, str]:
    if not _table_exists(conn, "state"):
        return {}
    cur = conn.execute("SELECT key, value FROM state WHERE key LIKE 'profile.%'")
    return {str(r[0]): str(r[1]) for r in cur.fetchall()}


def _profile_flags(
    conn: sqlite3.Connection,
    *,
    ada_profile: str,
    ada_profile_data_root: str,
    profile_fingerprint: str,
) -> list[MissionFlag]:
    out: list[MissionFlag] = []
    prof = _read_profile_state(conn)
    for key, expected in (
        ("profile.id", ada_profile),
        ("profile.data_root", ada_profile_data_root),
        ("profile.fingerprint", profile_fingerprint),
    ):
        if key not in prof:
            continue
        if prof[key] != expected:
            out.append(
                _flag(
                    "profile_fingerprint_mismatch",
                    "error",
                    f"{key}: database={prof[key]!r} runtime={expected!r}",
                    source_table="state",
                    source_id=key,
                )
            )
    return out


def _env_flags(
    *,
    gemini_api_key: str,
    ada_job_queue: str,
    ada_kill_switch: bool,
) -> list[MissionFlag]:
    out: list[MissionFlag] = []
    if not gemini_api_key.strip():
        out.append(
            _flag(
                "gemini_api_key_missing",
                "warn",
                "GEMINI_API_KEY is unset; daemon/system_jobs worker will idle.",
                source_table="env",
                source_id="GEMINI_API_KEY",
            )
        )
    jq = ada_job_queue.strip().lower()
    if jq not in ("legacy", "system_jobs"):
        out.append(
            _flag(
                "job_queue_mode_invalid",
                "error",
                f"ADA_JOB_QUEUE must be legacy or system_jobs; got {jq!r}",
                source_table="env",
                source_id="ADA_JOB_QUEUE",
            )
        )
    if ada_kill_switch:
        out.append(
            _flag(
                "kill_switch_active",
                "info",
                "ADA_KILL_SWITCH=1 — daemon dequeue paused.",
                source_table="env",
                source_id="ADA_KILL_SWITCH",
            )
        )
    out.append(
        _flag(
            "double_job_plane_risk",
            "warn",
            "Run only one job plane per state.db (legacy poll OR system_jobs worker, never both).",
            source_table="docs",
            source_id="JOB_QUEUE_SINGLE_OWNER",
        )
    )
    return out


def _system_job_flags(conn: sqlite3.Connection) -> list[MissionFlag]:
    if not _table_exists(conn, "system_jobs"):
        return []
    out: list[MissionFlag] = []
    summary = system_jobs_stuck_summary(conn)
    if summary.get("dead", 0) > 0:
        cur = conn.execute(
            "SELECT id FROM system_jobs WHERE status = 'dead' ORDER BY id DESC LIMIT 20"
        )
        for r in cur.fetchall():
            jid = int(r[0])
            out.append(
                _flag(
                    "system_jobs_dead",
                    "warn",
                    f"system_job {jid} is dead",
                    source_table="system_jobs",
                    source_id=str(jid),
                )
            )
    if summary.get("expired_lease", 0) > 0:
        cur = conn.execute(
            """
            SELECT id FROM system_jobs
            WHERE status = 'running'
              AND lease_expires_at IS NOT NULL
              AND datetime(lease_expires_at) < datetime('now')
            ORDER BY id DESC LIMIT 20
            """
        )
        for r in cur.fetchall():
            jid = int(r[0])
            out.append(
                _flag(
                    "system_jobs_expired_lease",
                    "warn",
                    f"system_job {jid} has expired lease",
                    source_table="system_jobs",
                    source_id=str(jid),
                )
            )
    cur = conn.execute(
        """
        SELECT id, kind FROM system_jobs
        WHERE status = 'pending'
          AND datetime(created_at) < datetime('now', ?)
        ORDER BY id ASC
        LIMIT 20
        """,
        (f"-{PENDING_STALE_HOURS} hours",),
    )
    for r in cur.fetchall():
        jid, kind = int(r[0]), str(r[1] or "")
        out.append(
            _flag(
                "system_jobs_pending_stale",
                "warn",
                f"system_job {jid} ({kind}) pending > {PENDING_STALE_HOURS}h",
                source_table="system_jobs",
                source_id=str(jid),
            )
        )
    return out


def _mission_overview_info_flags(
    conn: sqlite3.Connection,
    *,
    mission_id: int | None,
    mission_slug: str | None,
) -> list[MissionFlag]:
    slug_filter = mission_slug if mission_slug else None
    rows = missions_overview_list(conn, slug_filter=slug_filter)
    out: list[MissionFlag] = []
    for row in rows:
        mid = int(row["id"])
        if mission_id is not None and mid != mission_id:
            continue
        slug = str(row.get("slug") or "")
        pg = int(row.get("pending_goals") or 0)
        pw = int(row.get("pending_workflows") or 0)
        psj = int(row.get("pending_system_jobs") or 0)
        if pg > 0:
            out.append(
                _flag(
                    "mission_pending_goals",
                    "info",
                    f"mission {slug!r}: {pg} pending goal(s)",
                    mission_id=mid,
                    source_table="tasks",
                    source_id=slug,
                )
            )
        if pw > 0:
            out.append(
                _flag(
                    "mission_pending_workflows",
                    "info",
                    f"mission {slug!r}: {pw} pending workflow(s)",
                    mission_id=mid,
                    source_table="workflows",
                    source_id=slug,
                )
            )
        if psj > 0:
            out.append(
                _flag(
                    "mission_pending_system_jobs",
                    "info",
                    f"mission {slug!r}: {psj} pending/running system_job(s)",
                    mission_id=mid,
                    source_table="system_jobs",
                    source_id=slug,
                )
            )
    return out


def _tick_flags_for_mission(
    conn: sqlite3.Connection,
    *,
    mission_id: int,
    mission_slug: str,
    schedule_hint_json: Any,
) -> list[MissionFlag]:
    jobs, err = parse_tick_schedule_v1(schedule_hint_json)
    if err or jobs is None:
        return []
    if not jobs:
        return []
    out: list[MissionFlag] = []
    now = utc_now()
    tick_rows = {r["key"]: r["value"] for r in mission_tick_state_rows(conn, mission_slug=mission_slug)}
    for job in jobs:
        jid = str(job.get("id") or "").strip()
        if not jid:
            continue
        key = tick_state_key(mission_slug, jid)
        raw_val = tick_rows.get(key)
        if raw_val is None:
            out.append(
                _flag(
                    "mission_tick_never_ran",
                    "info",
                    f"mission {mission_slug!r} tick job {jid!r} has no last-run state key",
                    mission_id=mission_id,
                    source_table="state",
                    source_id=key,
                )
            )
            continue
        min_h = float(job.get("min_interval_hours") or 24.0)
        last = parse_last_run_iso(raw_val)
        if job_due(now, last, min_h, force=False):
            out.append(
                _flag(
                    "mission_tick_job_overdue",
                    "warn",
                    f"mission {mission_slug!r} tick job {jid!r} is due (min_interval_hours={min_h})",
                    mission_id=mission_id,
                    source_table="state",
                    source_id=key,
                )
            )
    return out


def _workflow_failed_flags(
    conn: sqlite3.Connection,
    *,
    mission_id: int | None,
) -> list[MissionFlag]:
    if not _table_exists(conn, "workflow_steps") or not _table_exists(conn, "workflows"):
        return []
    has_wm = _column_exists(conn, "workflows", "mission_id")
    where_mid = ""
    args: list[Any] = []
    if mission_id is not None and has_wm:
        where_mid = " AND w.mission_id = ?"
        args.append(mission_id)
    elif mission_id is not None:
        return []
    cur = conn.execute(
        f"""
        SELECT ws.id, ws.workflow_id, w.mission_id
        FROM workflow_steps ws
        JOIN workflows w ON w.id = ws.workflow_id
        WHERE ws.status = 'failed'
          {where_mid}
        ORDER BY ws.updated_at DESC
        LIMIT 20
        """,
        tuple(args),
    )
    out: list[MissionFlag] = []
    for r in cur.fetchall():
        sid, wid = int(r[0]), int(r[1])
        mid = r["mission_id"]
        mid_i = int(mid) if mid is not None else None
        out.append(
            _flag(
                "workflow_step_failed",
                "error",
                f"workflow_step {sid} failed (workflow_id={wid})",
                mission_id=mid_i,
                source_table="workflow_steps",
                source_id=str(sid),
            )
        )
    return out


def _gate_failed_flags(
    conn: sqlite3.Connection,
    *,
    mission_id: int | None,
) -> list[MissionFlag]:
    steps = gate_failed_steps_recent(conn, limit=10, publish_entity_only=True)
    if mission_id is None:
        return [
            _flag(
                "gate_step_failed_recent",
                "warn",
                f"GATE failed on workflow {s['workflow_id']} step {s['step_id']}",
                source_table="workflow_steps",
                source_id=str(s["step_id"]),
            )
            for s in steps
        ]
    if not _column_exists(conn, "workflows", "mission_id"):
        return []
    out: list[MissionFlag] = []
    for s in steps:
        wid = int(s["workflow_id"])
        cur = conn.execute(
            "SELECT mission_id FROM workflows WHERE id = ?", (wid,)
        )
        row = cur.fetchone()
        if row is None:
            continue
        mid = row["mission_id"]
        if mid is None or int(mid) != mission_id:
            continue
        out.append(
            _flag(
                "gate_step_failed_recent",
                "warn",
                f"GATE failed on workflow {wid} step {s['step_id']}",
                mission_id=mission_id,
                source_table="workflow_steps",
                source_id=str(s["step_id"]),
            )
        )
    return out


def _action_log_flags(conn: sqlite3.Connection) -> list[MissionFlag]:
    if not _table_exists(conn, "action_log"):
        return []
    kinds = (
        "publish_deploy_blocked_no_approval",
        "global_budget_block",
        "kill_switch_skip",
    )
    placeholders = ",".join("?" for _ in kinds)
    cur = conn.execute(
        f"""
        SELECT id, kind, created_at FROM action_log
        WHERE kind IN ({placeholders})
          AND datetime(created_at) >= datetime('now', ?)
        ORDER BY id DESC
        LIMIT 30
        """,
        (*kinds, f"-{ACTION_LOG_RECENT_HOURS} hours"),
    )
    id_map = {
        "publish_deploy_blocked_no_approval": "publish_deploy_blocked",
        "global_budget_block": "global_budget_block",
        "kill_switch_skip": "kill_switch_active",
    }
    sev_map = {
        "publish_deploy_blocked": "warn",
        "global_budget_block": "warn",
        "kill_switch_active": "info",
    }
    out: list[MissionFlag] = []
    for r in cur.fetchall():
        kind = str(r["kind"] or "")
        fid = id_map.get(kind, kind)
        out.append(
            _flag(
                fid,
                sev_map.get(fid, "warn"),
                f"recent action_log {kind} (id={int(r['id'])})",
                source_table="action_log",
                source_id=str(int(r["id"])),
                observed_at=str(r["created_at"] or _now_iso()),
            )
        )
    return out


def _chat_missing_mission_flag(conn: sqlite3.Connection) -> list[MissionFlag]:
    if not _column_exists(conn, "tasks", "mission_id"):
        return []
    cur = conn.execute(
        """
        SELECT id, mission_id FROM tasks
        WHERE task_kind = 'chat'
        ORDER BY id DESC
        LIMIT 1
        """
    )
    row = cur.fetchone()
    if row is None:
        return []
    tid = int(row[0])
    mid = row["mission_id"]
    if mid is not None:
        return []
    return [
        _flag(
            "chat_task_missing_mission",
            "warn",
            f"Latest chat task {tid} has mission_id=NULL — use ada chat --mission <slug>",
            source_table="tasks",
            source_id=str(tid),
        )
    ]


def _tombstone_flags(
    conn: sqlite3.Connection,
    *,
    mission_id: int | None,
) -> list[MissionFlag]:
    if not _table_exists(conn, "messages"):
        return []
    has_tm = _column_exists(conn, "tasks", "mission_id")
    if mission_id is not None and not has_tm:
        return []
    join = " INNER JOIN tasks t ON t.id = m.session_id " if has_tm else ""
    where_mid = ""
    args: list[Any] = [f"-{TOMBSTONE_RECENT_HOURS} hours"]
    if mission_id is not None and has_tm:
        where_mid = " AND t.mission_id = ?"
        args.append(mission_id)
    cols = "m.uuid, m.session_id, t.mission_id" if has_tm else "m.uuid, m.session_id"
    cur = conn.execute(
        f"""
        SELECT {cols}
        FROM messages m
        {join}
        WHERE m.tombstone = 1
          AND datetime(m.created_at) >= datetime('now', ?)
          {where_mid}
        ORDER BY m.created_at DESC
        LIMIT 10
        """,
        tuple(args),
    )
    out: list[MissionFlag] = []
    for r in cur.fetchall():
        uuid_s = str(r[0])
        sid = int(r[1])
        mid = r["mission_id"] if has_tm and len(r) > 2 else None
        mid_i = int(mid) if mid is not None else None
        out.append(
            _flag(
                "messages_tombstoned_recent",
                "info",
                f"tombstoned message {uuid_s[:8]}… in session {sid}",
                mission_id=mid_i,
                source_table="messages",
                source_id=uuid_s,
            )
        )
    return out


def collect_flags(
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
) -> list[MissionFlag]:
    """
    Collect deterministic flags from SQLite (+ optional env/profile inputs).

    When ``mission_id`` is set, mission-scoped builders filter to that mission.
    When ``profile_scope`` is True, include profile-wide flags (jobs, chat scope, env).
    """
    out: list[MissionFlag] = []

    if profile_scope:
        out.extend(
            _env_flags(
                gemini_api_key=gemini_api_key,
                ada_job_queue=ada_job_queue,
                ada_kill_switch=ada_kill_switch,
            )
        )
        if ada_profile and profile_fingerprint:
            out.extend(
                _profile_flags(
                    conn,
                    ada_profile=ada_profile,
                    ada_profile_data_root=ada_profile_data_root,
                    profile_fingerprint=profile_fingerprint,
                )
            )
        out.extend(_system_job_flags(conn))
        out.extend(_action_log_flags(conn))
        out.extend(_chat_missing_mission_flag(conn))

    out.extend(
        _mission_overview_info_flags(
            conn, mission_id=mission_id, mission_slug=mission_slug
        )
    )
    out.extend(_workflow_failed_flags(conn, mission_id=mission_id))
    out.extend(_gate_failed_flags(conn, mission_id=mission_id))
    out.extend(_tombstone_flags(conn, mission_id=mission_id))

    if mission_id is not None and mission_slug:
        cur = conn.execute(
            "SELECT schedule_hint_json FROM missions WHERE id = ?", (mission_id,)
        )
        row = cur.fetchone()
        sched = None
        if row is not None:
            raw = row[0]
            if isinstance(raw, str) and raw.strip():
                try:
                    sched = json.loads(raw)
                except json.JSONDecodeError:
                    sched = raw
            else:
                sched = raw
        out.extend(
            _tick_flags_for_mission(
                conn,
                mission_id=mission_id,
                mission_slug=mission_slug,
                schedule_hint_json=sched,
            )
        )

    # De-dupe by (id, source_id, mission_id) keeping first
    seen: set[tuple[str, str | None, int | None]] = set()
    deduped: list[MissionFlag] = []
    for f in out:
        key = (f.id, f.source_id, f.mission_id)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(f)
    severity_order = {"error": 0, "warn": 1, "info": 2, "ok": 3}
    deduped.sort(key=lambda x: (severity_order.get(x.severity, 9), x.id))
    return deduped


def collect_flags_from_settings(
    settings: Any,
    *,
    mission_id: int | None = None,
    mission_slug: str | None = None,
    profile_scope: bool = True,
) -> list[MissionFlag]:
    """Open read-only DB from Settings and collect flags."""
    conn = open_readonly_connection(settings.state_db_path)
    try:
        return collect_flags(
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
        )
    finally:
        conn.close()
