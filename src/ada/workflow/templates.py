"""Deterministic workflow templates (v1 planner). Kinds are code-defined only."""

from __future__ import annotations

import json
from typing import Any

# Public set of kinds for CLI/help and validation.
WORKFLOW_KINDS: frozenset[str] = frozenset({"rss_fetch_then_graph_then_synth"})


def _base_steps(kind: str) -> list[dict[str, Any]]:
    k = str(kind).strip()
    if k == "rss_fetch_then_graph_then_synth":
        return [
            {
                "step_index": 0,
                "step_type": "FETCH",
                "input_json": {},
            },
            {
                "step_index": 1,
                "step_type": "EXTRACT",
                "input_json": {"recent_item_limit": 40},
            },
            {
                "step_index": 2,
                "step_type": "SYNTHESIZE",
                "input_json": {},
            },
        ]
    raise ValueError(f"unknown workflow kind: {kind!r}")


def validate_workflow_step_dependencies(steps: list[dict[str, Any]]) -> None:
    """Public wrapper for tests: ensure depends_on_step_index < step_index for each step."""
    _validate_dependency_graph(steps)


def _validate_dependency_graph(steps: list[dict[str, Any]]) -> None:
    """Reject invalid depends_on_step_index (must be < step_index; acyclic)."""
    for st in steps:
        idx = int(st["step_index"])
        inp = st.get("input_json") if isinstance(st.get("input_json"), dict) else {}
        dep = inp.get("depends_on_step_index")
        if dep is None:
            continue
        try:
            d = int(dep)
        except (TypeError, ValueError) as e:
            raise ValueError("depends_on_step_index must be integer") from e
        if d >= idx:
            raise ValueError(
                f"depends_on_step_index {d} must be < step_index {idx} for DAG safety"
            )


def expand_workflow_template(
    kind: str,
    params: dict[str, Any],
    *,
    max_steps: int | None,
) -> list[dict[str, Any]]:
    """
    Return step rows ready for PersistentState.enqueue_workflow (step_index, step_type, input_json).
    Merges ``params`` into SYNTHESIZE step (topic) and EXTRACT (recent_item_limit override).
    """
    steps = [dict(s) for s in _base_steps(kind)]
    topic = str(params.get("topic") or "Summarize recent ingested knowledge.").strip()
    lim_raw = params.get("recent_item_limit")
    recent_lim = 40
    if lim_raw is not None:
        try:
            recent_lim = max(1, min(int(lim_raw), 500))
        except (TypeError, ValueError):
            recent_lim = 40
    for st in steps:
        inp = dict(st.get("input_json") or {})
        if st["step_type"] == "SYNTHESIZE":
            inp["topic"] = topic
        if st["step_type"] == "EXTRACT":
            inp["recent_item_limit"] = recent_lim
        st["input_json"] = inp
    _validate_dependency_graph(steps)
    if max_steps is not None and len(steps) > max_steps:
        raise ValueError(
            f"workflow has {len(steps)} steps; ADA_MAX_TASK_STEPS allows {max_steps}"
        )
    return steps


def parse_params_json_object(raw: str | None) -> dict[str, Any]:
    if raw is None or not str(raw).strip():
        return {}
    try:
        obj = json.loads(str(raw).strip())
    except json.JSONDecodeError as e:
        raise ValueError("params_json must be valid JSON object string") from e
    if not isinstance(obj, dict):
        raise ValueError("params_json must decode to a JSON object")
    return obj
