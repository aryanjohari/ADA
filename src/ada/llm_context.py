"""Assemble prompts for data-plane pipelines: base → invariants → intent → numeric policy."""

from __future__ import annotations

from typing import Any, Mapping

from ada.policy.load import (
    DEFAULT_BATCH_ENRICH_MAX_ENTITIES,
    DEFAULT_BATCH_ENRICH_MAX_TOOL_ROUNDS,
    DEFAULT_GRAPH_LITE_MAX_ITEMS_PER_JOB,
    DEFAULT_GRAPH_LITE_TOKEN_CAP_PER_JOB,
    DEFAULT_INTENT_MAX_BYTES,
    DEFAULT_MATRIX_PLANNER_TOP_K,
    PolicyConfig,
)


def _render_policy_constraints(policy: PolicyConfig) -> str:
    """YAML numbers only — omit block when aligned with canonical defaults."""
    lines: list[str] = []
    if policy.version != 1:
        lines.append(f"policy_version={policy.version}")
    if policy.intent_max_bytes != DEFAULT_INTENT_MAX_BYTES:
        lines.append(f"intent_max_bytes={policy.intent_max_bytes}")
    if policy.matrix_planner_top_k != DEFAULT_MATRIX_PLANNER_TOP_K:
        lines.append(f"matrix_planner_top_k={policy.matrix_planner_top_k}")
    if policy.graph_lite_max_items_per_job != DEFAULT_GRAPH_LITE_MAX_ITEMS_PER_JOB:
        lines.append(f"graph_lite_max_items_per_job={policy.graph_lite_max_items_per_job}")
    if policy.graph_lite_token_cap_per_job != DEFAULT_GRAPH_LITE_TOKEN_CAP_PER_JOB:
        lines.append(f"graph_lite_token_cap_per_job={policy.graph_lite_token_cap_per_job}")
    if policy.batch_enrich_max_entities != DEFAULT_BATCH_ENRICH_MAX_ENTITIES:
        lines.append(f"batch_enrich_max_entities={policy.batch_enrich_max_entities}")
    if policy.batch_enrich_max_tool_rounds != DEFAULT_BATCH_ENRICH_MAX_TOOL_ROUNDS:
        lines.append(f"batch_enrich_max_tool_rounds={policy.batch_enrich_max_tool_rounds}")
    if not lines:
        return ""
    return "## Policy limits\n" + "\n".join(lines)


def build_llm_context(
    role: str,
    *,
    base: str,
    invariants: str = "",
    intent_text: str = "",
    policy: PolicyConfig | Mapping[str, Any] | None = None,
) -> str:
    """
    Stable ordering: ``base``, optional **Invariants**, optional **Operator intent**, optional numeric policy section.

    ``role`` is reserved for callers / logging — not inlined into output (avoids prompt injection from labels).
    """
    _ = role
    sections: list[str] = []
    base_s = (base or "").strip()
    if base_s:
        sections.append(base_s)
    inv = (invariants or "").strip()
    if inv:
        sections.append(f"## Invariants\n{inv}")
    inte = (intent_text or "").strip()
    if inte:
        sections.append(f"## Operator intent\n{inte}")

    constraint = ""
    if policy is None:
        constraint = ""
    elif isinstance(policy, PolicyConfig):
        constraint = _render_policy_constraints(policy)
    elif isinstance(policy, Mapping):
        # Escape hatch for tests — never pass raw prose; keys should be numeric.
        vals = [(k, v) for k, v in policy.items() if v is not None and str(k).strip()]
        if vals:
            lines = ["## Policy limits"] + [
                f"- {k}: {v}"
                for k, v in sorted(vals, key=lambda x: str(x[0]))
            ]
            constraint = "\n".join(lines)
    if constraint.strip():
        sections.append(constraint.strip())

    return "\n\n".join(sections).strip()
