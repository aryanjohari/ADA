"""Closed primitive catalog (J1): id → spec."""

from __future__ import annotations

from dataclasses import dataclass

BASE_OPS_HAT = "base_ops"
ADA_OPS_HAT = "ada_ops"


@dataclass(frozen=True)
class PrimitiveSpec:
    id: str
    hat: str
    risk: str
    required_args: frozenset[str]
    optional_args: frozenset[str] = frozenset()


PRIMITIVES: dict[str, PrimitiveSpec] = {
    "add_task": PrimitiveSpec(
        id="add_task",
        hat=BASE_OPS_HAT,
        risk="low",
        required_args=frozenset({"goal"}),
        optional_args=frozenset({"status"}),
    ),
    "list_tasks": PrimitiveSpec(
        id="list_tasks",
        hat=BASE_OPS_HAT,
        risk="low",
        required_args=frozenset(),
        optional_args=frozenset({"status", "limit"}),
    ),
    "complete_task": PrimitiveSpec(
        id="complete_task",
        hat=BASE_OPS_HAT,
        risk="low",
        required_args=frozenset({"task_id"}),
    ),
    "log_memory": PrimitiveSpec(
        id="log_memory",
        hat=BASE_OPS_HAT,
        risk="low",
        required_args=frozenset({"content"}),
        optional_args=frozenset({"tags"}),
    ),
    "recall_memory": PrimitiveSpec(
        id="recall_memory",
        hat=BASE_OPS_HAT,
        risk="low",
        required_args=frozenset(),
        optional_args=frozenset({"query", "limit"}),
    ),
    "body_check": PrimitiveSpec(
        id="body_check",
        hat=ADA_OPS_HAT,
        risk="low",
        required_args=frozenset(),
    ),
}

PRIMITIVE_IDS: frozenset[str] = frozenset(PRIMITIVES)


def get_primitive_spec(primitive_id: str) -> PrimitiveSpec:
    spec = PRIMITIVES.get(primitive_id)
    if spec is None:
        known = sorted(PRIMITIVE_IDS)
        raise ValueError(f"unknown primitive {primitive_id!r}; known: {known}")
    return spec
