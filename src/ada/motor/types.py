"""Motor plane request/result types (Phase B unified execution)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

MotorLayer = Literal["shell", "motor_ada", "skill", "internal"]
MotorType = Literal["workflow_enqueue", "ada_argv", "internal_fn", "goal_add"]
RiskTier = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class SkillSpec:
    """Structured skill entry (skills/*.yaml merged with playbooks)."""

    id: str
    description: str
    risk_tier: RiskTier
    ring: int
    motor_type: MotorType
    workflow_kind: str | None = None
    playbook_id: str | None = None
    argv_template: list[str] | None = None
    handler: str | None = None
    allowed_params: frozenset[str] = frozenset()
    required_params: frozenset[str] = frozenset()
    mission_required: bool = False
    require_approval: bool = False
    op_command_id: str | None = None  # when motor_type=ada_argv maps to operator CommandId


@dataclass
class MotorRequest:
    """Single motor ingress request."""

    layer: MotorLayer
    id: str
    params: dict[str, Any] | None = None
    mission_slug: str | None = None
    session_id: int | None = None
    approved: bool = False
    # shell / motor_ada extras
    shell_line: str | None = None
    ada_bin: str | None = None
    argv_kwargs: dict[str, Any] = field(default_factory=dict)


@dataclass
class MotorResult:
    ok: bool
    output: dict[str, Any] | str = ""
    action_log_id: int | None = None
    error: str | None = None
    pending_approval: bool = False
