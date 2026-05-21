"""Unified motor plane (Phase B)."""

from ada.motor.execute import execute
from ada.motor.registry import (
    clear_registry_cache,
    get_skill,
    load_skill_registry,
    load_shell_allowlist,
)
from ada.motor.types import MotorRequest, MotorResult, SkillSpec

__all__ = [
    "MotorRequest",
    "MotorResult",
    "SkillSpec",
    "execute",
    "get_skill",
    "load_skill_registry",
    "load_shell_allowlist",
    "clear_registry_cache",
]
