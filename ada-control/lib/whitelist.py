"""Closed whitelist for `ada` subprocess argv. No arbitrary shell."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

_MISSION_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,63}$")


def validate_mission_slug(slug: str) -> bool:
    s = slug.strip()
    return bool(s and _MISSION_SLUG_RE.fullmatch(s))


def validate_workflow_id(wid: int) -> bool:
    return isinstance(wid, int) and wid > 0


CommandId = Literal[
    "help",
    "mission_list",
    "mission_show",
    "goal_list",
    "workflow_status",
    "gate_failures",
    "mission_tick_dry_run",
    "matrix_scan_dry_run",
]


@dataclass(frozen=True)
class WhitelistEntry:
    command_id: CommandId
    label: str
    writes_db: bool
    needs_network: bool
    needs_gemini: bool
    notes: str


WHITELIST_META: dict[CommandId, WhitelistEntry] = {
    "help": WhitelistEntry(
        "help",
        "ada --help",
        writes_db=False,
        needs_network=False,
        needs_gemini=False,
        notes="Shows CLI help text only.",
    ),
    "mission_list": WhitelistEntry(
        "mission_list",
        "ada mission list",
        writes_db=False,
        needs_network=False,
        needs_gemini=False,
        notes="Reads missions from SQLite.",
    ),
    "mission_show": WhitelistEntry(
        "mission_show",
        "ada mission show <slug>",
        writes_db=False,
        needs_network=False,
        needs_gemini=False,
        notes="Reads one mission by slug.",
    ),
    "goal_list": WhitelistEntry(
        "goal_list",
        "ada goal list",
        writes_db=False,
        needs_network=False,
        needs_gemini=False,
        notes="Reads recent goal tasks from SQLite.",
    ),
    "workflow_status": WhitelistEntry(
        "workflow_status",
        "ada workflow status <id>",
        writes_db=False,
        needs_network=False,
        needs_gemini=False,
        notes="Reads workflow row and steps JSON.",
    ),
    "gate_failures": WhitelistEntry(
        "gate_failures",
        "ada gate-failures",
        writes_db=False,
        needs_network=False,
        needs_gemini=False,
        notes="Reads recent failed GATE steps (publish_entity_v1 default).",
    ),
    "mission_tick_dry_run": WhitelistEntry(
        "mission_tick_dry_run",
        "ada mission tick --mission <slug> --dry-run",
        writes_db=False,
        needs_network=False,
        needs_gemini=False,
        notes="prints due jobs only; real tick without --dry-run can enqueue (not whitelisted here).",
    ),
    "matrix_scan_dry_run": WhitelistEntry(
        "matrix_scan_dry_run",
        "ada matrix-scan --dry-run",
        writes_db=False,
        needs_network=False,
        needs_gemini=False,
        notes="Dry-run lists candidates locally; live enqueue needs ADA_MATRIX_ENABLE=1 + network/S3/Gemini downstream.",
    ),
}


def build_argv(
    ada_bin: str,
    *,
    command_id: CommandId,
    mission_slug: str | None = None,
    mission_show_slug: str = "",
    goal_status: str | None = None,
    goal_limit: int = 50,
    mission_limit: int = 50,
    workflow_id: int = 1,
    gate_failures_limit: int = 50,
    gate_failures_all_kinds: bool = False,
    matrix_deterministic: bool = False,
) -> list[str]:
    """Return argv or raise ValueError."""

    argv: list[str] = [ada_bin]

    match command_id:
        case "help":
            argv.append("--help")

        case "mission_list":
            lim = max(1, min(500, mission_limit))
            argv.extend(["mission", "list", "--limit", str(lim)])

        case "mission_show":
            s = mission_show_slug.strip()
            if not validate_mission_slug(s):
                raise ValueError("mission slug invalid")
            argv.extend(["mission", "show", s])

        case "goal_list":
            argv.extend(["goal", "list"])
            lim = max(1, min(500, goal_limit))
            argv.extend(["--limit", str(lim)])
            if mission_slug and mission_slug.strip():
                ms = mission_slug.strip()
                if not validate_mission_slug(ms):
                    raise ValueError("mission slug invalid for --mission")
                argv.extend(["--mission", ms])
            if goal_status and goal_status.strip():
                argv.extend(["--status", goal_status.strip()])

        case "workflow_status":
            if not validate_workflow_id(workflow_id):
                raise ValueError("workflow id must be a positive integer")
            argv.extend(["workflow", "status", str(workflow_id)])

        case "gate_failures":
            lim = max(1, min(500, gate_failures_limit))
            argv.extend(["gate-failures", "--limit", str(lim)])
            if gate_failures_all_kinds:
                argv.append("--all-kinds")

        case "mission_tick_dry_run":
            if not mission_slug or not validate_mission_slug(mission_slug.strip()):
                raise ValueError("mission slug required")
            argv.extend(
                ["mission", "tick", "--mission", mission_slug.strip(), "--dry-run"]
            )

        case "matrix_scan_dry_run":
            argv.extend(["matrix-scan", "--dry-run"])
            if matrix_deterministic:
                argv.append("--deterministic")
            if mission_slug and mission_slug.strip():
                ms = mission_slug.strip()
                if not validate_mission_slug(ms):
                    raise ValueError("mission slug invalid for --mission")
                argv.extend(["--mission", ms])

        case _:
            raise ValueError("unknown command_id")

    return argv
