"""Graph-lite system instruction assembly (no live Gemini)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from ada.extract.graph_lite import (
    graph_lite_invariants_text,
    resolve_graph_lite_system_instruction,
)
from ada.policy.load import PolicyConfig, clamp_graph_lite_job_limits


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


def test_graph_lite_invariants_contains_job_bounds() -> None:
    inv = graph_lite_invariants_text(effective_limit=40, effective_token_cap=8000)
    assert "at most 40 knowledge rows" in inv
    assert "token_cap=8000" in inv


def test_resolve_graph_lite_empty_intent_stable_markers(tmp_path: Path) -> None:
    mem = tmp_path / "memory"
    mem.mkdir(parents=True, exist_ok=True)
    settings = MagicMock()
    settings.memory_dir = mem
    policy = _default_policy()
    out = resolve_graph_lite_system_instruction(
        settings,
        policy,
        effective_limit=40,
        effective_token_cap=8000,
    )
    assert "Extract a small knowledge graph" in out
    assert "## Invariants" in out
    assert "organization" in out and "government_body" in out
    assert "routine weather forecasts" in out
    assert "at most 40 knowledge rows" in out
    assert "token_cap=8000" in out
    assert "## Operator intent" not in out


def test_resolve_graph_lite_with_intent_section(tmp_path: Path) -> None:
    mem = tmp_path / "memory"
    mem.mkdir(parents=True, exist_ok=True)
    (mem / "intent.md").write_text("Prioritize RBNZ and housing policy.", encoding="utf-8")
    settings = MagicMock()
    settings.memory_dir = mem
    policy = _default_policy()
    out = resolve_graph_lite_system_instruction(
        settings,
        policy,
        effective_limit=10,
        effective_token_cap=4000,
    )
    assert "## Operator intent" in out
    assert "RBNZ" in out
    assert "at most 10 knowledge rows" in out


def test_clamp_graph_lite_job_limits() -> None:
    p = PolicyConfig(
        version=1,
        intent_max_bytes=65536,
        matrix_planner_top_k=5,
        graph_lite_max_items_per_job=50,
        graph_lite_token_cap_per_job=4000,
        batch_enrich_max_entities=10,
        batch_enrich_max_tool_rounds=48,
    )
    lim, cap = clamp_graph_lite_job_limits(200, 8000, p)
    assert lim == 50
    assert cap == 4000
