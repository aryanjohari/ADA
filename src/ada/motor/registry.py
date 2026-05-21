"""Load merged motor registry: skills YAML + playbooks + operator commands + shell."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from ada.config import _find_project_root
from ada.motor.types import RiskTier, SkillSpec
from ada.tools.shell_allowlist import load_allowlist_exact_lines
from ada.workflow.playbook_resolve import registry_path as playbook_registry_path

_SKILLS_DIR = Path("skills")
_ALLOWED_SKILL_KEYS = frozenset(
    {
        "id",
        "description",
        "risk_tier",
        "ring",
        "motor_type",
        "workflow_kind",
        "playbook_id",
        "argv_template",
        "handler",
        "allowed_params",
        "required_params",
        "mission_required",
        "require_approval",
        "op_command_id",
    }
)


def skills_dir(project_root: Path | None = None) -> Path:
    root = project_root if project_root is not None else _find_project_root()
    return (root / _SKILLS_DIR).resolve()


def clear_registry_cache() -> None:
    _load_skills_from_dir.cache_clear()


@lru_cache(maxsize=8)
def _load_skills_from_dir(dir_str: str) -> dict[str, SkillSpec]:
    d = Path(dir_str)
    out: dict[str, SkillSpec] = {}
    if not d.is_dir():
        return out
    for path in sorted(d.glob("*.yaml")):
        raw = path.read_text(encoding="utf-8")
        try:
            data = yaml.safe_load(raw)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid skill YAML: {path}: {e}") from e
        if not isinstance(data, dict):
            raise ValueError(f"skill file must be a mapping: {path}")
        extra = set(data) - _ALLOWED_SKILL_KEYS
        if extra:
            raise ValueError(f"unknown keys in {path.name}: {sorted(extra)}")
        sid = str(data.get("id") or path.stem).strip()
        if not sid:
            raise ValueError(f"skill id required: {path}")
        spec = _parse_skill_dict(data, default_id=sid)
        if spec.id in out:
            raise ValueError(f"duplicate skill id {spec.id!r}")
        out[spec.id] = spec
    return out


def _parse_skill_dict(data: dict[str, Any], *, default_id: str) -> SkillSpec:
    risk = str(data.get("risk_tier") or "medium").strip().lower()
    if risk not in ("low", "medium", "high"):
        raise ValueError(f"invalid risk_tier {risk!r}")
    motor_type = str(data.get("motor_type") or "").strip()
    if motor_type not in ("workflow_enqueue", "ada_argv", "internal_fn", "goal_add"):
        raise ValueError(f"invalid motor_type {motor_type!r}")
    ring_raw = data.get("ring", 2)
    ring = int(ring_raw)
    allowed = data.get("allowed_params") or []
    required = data.get("required_params") or []
    if not isinstance(allowed, list) or not isinstance(required, list):
        raise ValueError("allowed_params and required_params must be lists")
    argv_t = data.get("argv_template")
    argv_list: list[str] | None = None
    if argv_t is not None:
        if not isinstance(argv_t, list):
            raise ValueError("argv_template must be a list")
        argv_list = [str(x) for x in argv_t]
    return SkillSpec(
        id=str(data.get("id") or default_id).strip(),
        description=str(data.get("description") or "").strip(),
        risk_tier=risk,  # type: ignore[arg-type]
        ring=ring,
        motor_type=motor_type,  # type: ignore[arg-type]
        workflow_kind=(
            str(data["workflow_kind"]).strip() if data.get("workflow_kind") else None
        ),
        playbook_id=(
            str(data["playbook_id"]).strip() if data.get("playbook_id") else None
        ),
        argv_template=argv_list,
        handler=str(data["handler"]).strip() if data.get("handler") else None,
        allowed_params=frozenset(str(x) for x in allowed),
        required_params=frozenset(str(x) for x in required),
        mission_required=bool(data.get("mission_required", False)),
        require_approval=bool(data.get("require_approval", False)),
        op_command_id=(
            str(data["op_command_id"]).strip() if data.get("op_command_id") else None
        ),
    )


def load_skill_registry(project_root: Path | None = None) -> dict[str, SkillSpec]:
    root = project_root if project_root is not None else _find_project_root()
    return dict(_load_skills_from_dir(str(skills_dir(root))))


def get_skill(skill_id: str, project_root: Path | None = None) -> SkillSpec | None:
    return load_skill_registry(project_root).get(skill_id.strip())


def load_shell_allowlist(memory_dir: Path) -> frozenset[str]:
    return load_allowlist_exact_lines(memory_dir / "shell_allowlist.txt")


def list_op_command_ids() -> list[str]:
    from ada.motor.argv import list_command_ids

    return list_command_ids()


def playbook_registry_exists(project_root: Path | None = None) -> bool:
    return playbook_registry_path(project_root).is_file()
