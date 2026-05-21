"""Closed whitelist for `ada` subprocess argv. No arbitrary shell."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ada.motor.argv import validate_mission_slug, validate_workflow_id


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
    "mission_init": WhitelistEntry(
        "mission_init",
        "ada mission init <slug> --title …",
        writes_db=True,
        needs_network=False,
        needs_gemini=False,
        notes="Creates a mission row in SQLite for this profile's state.db.",
    ),
    "mission_migrate_env_dry": WhitelistEntry(
        "mission_migrate_env_dry",
        "ada mission migrate-env <slug>",
        writes_db=False,
        needs_network=False,
        needs_gemini=False,
        notes="Prints JSON patch from deprecated env vars; no --apply (dry preview only).",
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
    mission_init_slug: str = "",
    mission_init_title: str = "",
    mission_init_niche: str = "",
    mission_init_topic: str = "",
    mission_init_defaults_json: str = "",
    mission_init_schedule_json: str = "",
    mission_migrate_only: str = "",
) -> list[str]:
    """Return argv or raise ValueError (delegates to motor.argv)."""
    from ada.motor.argv import build_op_argv

    return build_op_argv(
        ada_bin,
        command_id=command_id,
        mission_slug=mission_slug,
        mission_show_slug=mission_show_slug,
        goal_status=goal_status,
        goal_limit=goal_limit,
        mission_limit=mission_limit,
        workflow_id=workflow_id,
        gate_failures_limit=gate_failures_limit,
        gate_failures_all_kinds=gate_failures_all_kinds,
        matrix_deterministic=matrix_deterministic,
        mission_init_slug=mission_init_slug,
        mission_init_title=mission_init_title,
        mission_init_niche=mission_init_niche,
        mission_init_topic=mission_init_topic,
        mission_init_defaults_json=mission_init_defaults_json,
        mission_init_schedule_json=mission_init_schedule_json,
        mission_migrate_only=mission_migrate_only,
    )
