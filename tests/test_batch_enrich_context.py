"""Batch enrich-graph system instruction (no live LLM)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from ada.policy.load import PolicyConfig, load_intent_md
from ada.publish.batch_enrich_context import resolve_batch_enrich_system_instruction


def _policy() -> PolicyConfig:
    return PolicyConfig(
        version=1,
        intent_max_bytes=65536,
        matrix_planner_top_k=5,
        graph_lite_max_items_per_job=200,
        graph_lite_token_cap_per_job=8000,
        batch_enrich_max_entities=10,
        batch_enrich_max_tool_rounds=48,
    )


def test_resolve_batch_enrich_contains_role_and_intent(tmp_path: Path) -> None:
    mem = tmp_path / "memory"
    mem.mkdir(parents=True, exist_ok=True)
    (mem / "intent.md").write_text("Focus on NZ macro.", encoding="utf-8")
    settings = MagicMock()
    settings.memory_dir = mem
    out = resolve_batch_enrich_system_instruction(settings, _policy())
    assert "background ENRICH" in out
    assert "## Operator intent" in out
    assert "NZ macro" in out


def test_load_intent_respects_policy_cap(tmp_path: Path) -> None:
    mem = tmp_path / "memory"
    mem.mkdir(parents=True, exist_ok=True)
    (mem / "intent.md").write_text("x" * 100, encoding="utf-8")
    p = PolicyConfig(
        version=1,
        intent_max_bytes=10,
        matrix_planner_top_k=5,
        graph_lite_max_items_per_job=200,
        graph_lite_token_cap_per_job=8000,
        batch_enrich_max_entities=10,
        batch_enrich_max_tool_rounds=48,
    )
    assert len(load_intent_md(mem, max_bytes=p.intent_max_bytes)) <= 10
