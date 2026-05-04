"""LLM context builder parity and policy sections."""

from ada.llm_context import build_llm_context
from ada.policy.load import PolicyConfig
from ada.triage.run import _TRIAGE_LEGACY_BASE


def _default_policy() -> PolicyConfig:
    return PolicyConfig(
        version=1,
        intent_max_bytes=65536,
        matrix_planner_top_k=5,
        graph_lite_max_items_per_job=200,
        graph_lite_token_cap_per_job=8000,
        batch_enrich_max_entities=10,
        batch_enrich_max_tool_rounds=48,
    )


def test_triage_parity_with_default_policy():
    policy = _default_policy()
    out = build_llm_context(
        "triage",
        base=_TRIAGE_LEGACY_BASE,
        invariants="",
        intent_text="",
        policy=policy,
    )
    assert out == _TRIAGE_LEGACY_BASE.strip()


def test_intent_section_appends():
    policy = _default_policy()
    out = build_llm_context(
        "x",
        base="BASE",
        invariants="INV",
        intent_text="do the thing",
        policy=policy,
    )
    assert "BASE" in out
    assert "## Invariants\nINV" in out
    assert "## Operator intent\ndo the thing" in out


def test_mapping_policy_renders_limits():
    out = build_llm_context(
        "x",
        base="ROOT",
        policy={"intent_max_bytes": 123},
    )
    assert "ROOT" in out
    assert "## Policy limits" in out
    assert "123" in out
