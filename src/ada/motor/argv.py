"""Build whitelisted ``ada`` argv (delegated from operator_whitelist)."""

from __future__ import annotations

import json
import re
from typing import Literal

from typing import Literal

CommandId = Literal[
    "help",
    "mission_list",
    "mission_show",
    "goal_list",
    "workflow_status",
    "gate_failures",
    "mission_tick_dry_run",
    "matrix_scan_dry_run",
    "mission_init",
    "mission_migrate_env_dry",
]

_OP_COMMAND_IDS: tuple[str, ...] = (
    "help",
    "mission_list",
    "mission_show",
    "goal_list",
    "workflow_status",
    "gate_failures",
    "mission_tick_dry_run",
    "matrix_scan_dry_run",
    "mission_init",
    "mission_migrate_env_dry",
)

_MISSION_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,63}$")


def validate_mission_slug(slug: str) -> bool:
    s = slug.strip()
    return bool(s and _MISSION_SLUG_RE.fullmatch(s))


def validate_workflow_id(wid: int) -> bool:
    return isinstance(wid, int) and wid > 0


def list_command_ids() -> list[str]:
    return sorted(_OP_COMMAND_IDS)


def build_op_argv(
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
    mission_init_slug: str = "",
    mission_init_title: str = "",
    mission_init_niche: str = "",
    mission_init_topic: str = "",
    mission_init_defaults_json: str = "",
    mission_init_schedule_json: str = "",
    mission_migrate_only: str = "",
) -> list[str]:
    """Return argv or raise ValueError."""
    argv: list[str] = [ada_bin]

    if command_id == "help":
        argv.append("--help")

    elif command_id == "mission_list":
        lim = max(1, min(500, mission_limit))
        argv.extend(["mission", "list", "--limit", str(lim)])

    elif command_id == "mission_show":
        s = mission_show_slug.strip()
        if not validate_mission_slug(s):
            raise ValueError("mission slug invalid")
        argv.extend(["mission", "show", s])

    elif command_id == "goal_list":
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

    elif command_id == "workflow_status":
        if not validate_workflow_id(workflow_id):
            raise ValueError("workflow id must be a positive integer")
        argv.extend(["workflow", "status", str(workflow_id)])

    elif command_id == "gate_failures":
        lim = max(1, min(500, gate_failures_limit))
        argv.extend(["gate-failures", "--limit", str(lim)])
        if gate_failures_all_kinds:
            argv.append("--all-kinds")

    elif command_id == "mission_tick_dry_run":
        if not mission_slug or not validate_mission_slug(mission_slug.strip()):
            raise ValueError("mission slug required")
        argv.extend(["mission", "tick", "--mission", mission_slug.strip(), "--dry-run"])

    elif command_id == "matrix_scan_dry_run":
        argv.extend(["matrix-scan", "--dry-run"])
        if matrix_deterministic:
            argv.append("--deterministic")
        if mission_slug and mission_slug.strip():
            ms = mission_slug.strip()
            if not validate_mission_slug(ms):
                raise ValueError("mission slug invalid for --mission")
            argv.extend(["--mission", ms])

    elif command_id == "mission_init":
        slug = mission_init_slug.strip()
        if not validate_mission_slug(slug):
            raise ValueError("mission init: invalid slug")
        title = mission_init_title.strip()
        if not title:
            raise ValueError("mission init: title required")
        argv.extend(["mission", "init", slug, "--title", title])
        niche = mission_init_niche.strip()
        topic = mission_init_topic.strip()
        if niche:
            argv.extend(["--niche", niche])
        if topic:
            argv.extend(["--topic", topic])
        dj = mission_init_defaults_json.strip()
        if dj:
            try:
                parsed = json.loads(dj)
            except json.JSONDecodeError as e:
                raise ValueError(f"defaults-json invalid JSON: {e}") from e
            if not isinstance(parsed, dict):
                raise ValueError("defaults-json must be a JSON object")
            argv.extend(["--defaults-json", dj])
        sj = mission_init_schedule_json.strip()
        if sj:
            try:
                parsed_s = json.loads(sj)
            except json.JSONDecodeError as e:
                raise ValueError(f"schedule-hint-json invalid JSON: {e}") from e
            if not isinstance(parsed_s, dict):
                raise ValueError("schedule-hint-json must be a JSON object")
            argv.extend(["--schedule-hint-json", sj])

    elif command_id == "mission_migrate_env_dry":
        slug = (mission_slug or "").strip()
        if not validate_mission_slug(slug):
            raise ValueError("mission migrate-env: invalid slug")
        argv.extend(["mission", "migrate-env", slug])
        only = mission_migrate_only.strip()
        if only:
            argv.extend(["--only", only])

    else:
        raise ValueError("unknown command_id")

    return argv
