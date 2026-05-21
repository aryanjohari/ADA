"""Read-only operator health checks (profile, job queue, system_jobs)."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ada.config import Settings
from ada.mission_control.flags import collect_flags
from ada.observability.queries import open_readonly_connection, system_jobs_stuck_summary

# Phase A daily surface — see docs/OPS_DAILY.md
DAILY_FLAG_IDS: frozenset[str] = frozenset(
    {
        "profile_fingerprint_mismatch",
        "gemini_api_key_missing",
        "system_jobs_dead",
        "mission_tick_job_overdue",
        "chat_task_missing_mission",
        "workflow_step_failed",
    }
)


@dataclass
class DoctorFinding:
    level: str  # ok | warn | error
    code: str
    message: str


@dataclass
class DoctorReport:
    findings: list[DoctorFinding] = field(default_factory=list)
    exit_code: int = 0

    def add(self, level: str, code: str, message: str) -> None:
        self.findings.append(DoctorFinding(level=level, code=code, message=message))
        if level == "error":
            self.exit_code = 1
        elif level == "warn" and self.exit_code == 0:
            self.exit_code = 0


def _read_profile_state(db_path: Path) -> dict[str, str]:
    if not db_path.is_file():
        return {}
    conn = sqlite3.connect(f"file:{db_path.resolve().as_posix()}?mode=ro", uri=True)
    try:
        cur = conn.execute(
            "SELECT key, value FROM state WHERE key LIKE 'profile.%'"
        )
        return {str(r[0]): str(r[1]) for r in cur.fetchall()}
    finally:
        conn.close()


def run_doctor(settings: Settings) -> DoctorReport:
    """Run checks; never prints secrets."""
    report = DoctorReport()
    db_path = settings.state_db_path

    if not settings.gemini_api_key.strip():
        report.add(
            "warn",
            "gemini_api_key_missing",
            "GEMINI_API_KEY is unset; daemon/system_jobs worker will idle.",
        )

    jq = settings.ada_job_queue.strip().lower()
    if jq not in ("legacy", "system_jobs"):
        report.add("error", "invalid_job_queue", f"ADA_JOB_QUEUE must be legacy or system_jobs; got {jq!r}")
    else:
        report.add("ok", "job_queue_mode", f"ADA_JOB_QUEUE={jq}")

    if not db_path.is_file():
        report.add("warn", "state_db_missing", f"state.db not found at {db_path}")
        return report

    prof = _read_profile_state(db_path)
    for key, expected in (
        ("profile.id", settings.ada_profile),
        ("profile.data_root", str(settings.ada_profile_data_root)),
        ("profile.fingerprint", settings.profile_fingerprint),
    ):
        if key not in prof:
            report.add("warn", "profile_uninitialized", f"{key} not in state table yet (first run?)")
            continue
        if prof[key] != expected:
            report.add(
                "error",
                "profile_mismatch",
                f"{key}: database={prof[key]!r} runtime={expected!r}",
            )
        else:
            report.add("ok", key, "matches runtime")

    try:
        conn = open_readonly_connection(db_path)
    except OSError as e:
        report.add("error", "db_open_failed", str(e))
        return report

    with conn:
        summary = system_jobs_stuck_summary(conn)
        flags = collect_flags(
            conn,
            profile_scope=True,
            gemini_api_key=settings.gemini_api_key,
            ada_job_queue=settings.ada_job_queue,
            ada_kill_switch=settings.ada_kill_switch,
            ada_profile=settings.ada_profile,
            ada_profile_data_root=str(settings.ada_profile_data_root),
            profile_fingerprint=settings.profile_fingerprint,
        )
    if summary:
        report.add(
            "ok",
            "system_jobs_counts",
            json.dumps(summary, sort_keys=True),
        )
    for fl in flags:
        if fl.id in DAILY_FLAG_IDS:
            report.add(fl.severity, fl.id, fl.message)

    report.add(
        "ok",
        "single_owner_reminder",
        "Run only one job plane per state.db — see docs/JOB_QUEUE_SINGLE_OWNER.md",
    )
    return report


def format_doctor_report(report: DoctorReport) -> str:
    lines: list[str] = []
    for f in report.findings:
        lines.append(f"[{f.level}] {f.code}: {f.message}")
    return "\n".join(lines)
