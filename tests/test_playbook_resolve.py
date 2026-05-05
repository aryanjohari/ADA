"""Playbook registry merge + validation (resolve_playbook / resolve_for_kind)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from ada.policy.load import PolicyConfig
from ada.workflow.playbook_resolve import (
    clear_playbook_registry_cache,
    registry_path,
    resolve_for_kind,
    resolve_playbook,
)


def _policy(*, graph_lim: int = 200) -> PolicyConfig:
    return PolicyConfig(
        version=1,
        intent_max_bytes=65536,
        matrix_planner_top_k=5,
        graph_lite_max_items_per_job=graph_lim,
        graph_lite_token_cap_per_job=8000,
        batch_enrich_max_entities=10,
        batch_enrich_max_tool_rounds=48,
    )


def test_merge_precedence_policy_then_mission_then_delta():
    p = _policy(graph_lim=111)
    r = resolve_playbook(
        "ingest_rss_summarize",
        policy=p,
        mission_defaults={"recent_item_limit": 50, "topic": "from_mission"},
        params_delta={"topic": "from_delta"},
    )
    assert r.params["topic"] == "from_delta"
    assert r.params["recent_item_limit"] == 50
    assert r.workflow_kind == "rss_fetch_then_graph_then_synth"


def test_merge_policy_default_when_mission_empty():
    p = _policy(graph_lim=173)
    r = resolve_playbook(
        "ingest_rss_summarize",
        policy=p,
        mission_defaults={},
        params_delta={"topic": "solo"},
    )
    assert r.params["topic"] == "solo"
    assert r.params["recent_item_limit"] == 173


def test_unknown_param_key_in_delta():
    with pytest.raises(ValueError, match=r"unknown param key.*bad_key"):
        resolve_playbook(
            "publish_entity_v1",
            policy=_policy(),
            mission_defaults={},
            params_delta={
                "bad_key": 1,
                "entity_id": 1,
                "project_id": "p",
                "campaign_id": "c",
                "niche": "n",
            },
        )


def test_unknown_param_key_in_mission_defaults():
    with pytest.raises(ValueError, match=r"unknown param key.*tone"):
        resolve_playbook(
            "publish_entity_v1",
            policy=_policy(),
            mission_defaults={"tone": "x"},
            params_delta={
                "entity_id": 1,
                "project_id": "p",
                "campaign_id": "c",
                "niche": "n",
            },
        )


def test_missing_required_publish_entity():
    with pytest.raises(ValueError, match="missing or empty required"):
        resolve_playbook(
            "publish_entity_v1",
            policy=_policy(),
            mission_defaults={},
            params_delta={"project_id": "p"},
        )


def test_unknown_playbook_id_message():
    with pytest.raises(ValueError) as ei:
        resolve_playbook(
            "no_such_playbook_zz",
            policy=_policy(),
            mission_defaults={},
            params_delta={},
        )
    msg = str(ei.value)
    assert "Unknown playbook_id" in msg
    assert "ingest_rss_summarize" in msg or "publish_entity_v1" in msg
    rp = registry_path()
    assert str(rp) in msg


def test_resolve_for_kind_matches_explicit_playbook():
    p = _policy()
    a = resolve_for_kind(
        "publish_entity_v1",
        policy=p,
        mission_defaults={},
        params_delta={
            "entity_id": 7,
            "project_id": "pr",
            "campaign_id": "ca",
            "niche": "ni",
        },
    )
    b = resolve_playbook(
        "publish_entity_v1",
        policy=p,
        mission_defaults={},
        params_delta={
            "entity_id": 7,
            "project_id": "pr",
            "campaign_id": "ca",
            "niche": "ni",
        },
    )
    assert a.workflow_kind == b.workflow_kind == "publish_entity_v1"
    assert a.params == b.params
    assert a.playbook_id == "publish_entity_v1"


def test_backwards_compat_matrix_style_publish_entity_empty_mission():
    """Same deltas as legacy matrix payloads; mission defaults omitted."""
    p = _policy()
    delta = {
        "entity_id": 99,
        "project_id": "proj-x",
        "campaign_id": "camp-y",
        "niche": "widgets",
        "slug": "acme-widget",
    }
    r = resolve_playbook(
        "publish_entity_v1",
        policy=p,
        mission_defaults={},
        params_delta=delta,
    )
    assert r.params["entity_id"] == 99
    assert r.params["slug"] == "acme-widget"
    assert "recent_item_limit" not in r.params


def test_unknown_kind_mapping_uses_registry_path(tmp_path: Path):
    reg = tmp_path / "playbooks"
    reg.mkdir(parents=True)
    data = yaml.safe_load(
        """
registry_version: 1
kind_default_playbook:
  rss_fetch_then_graph_then_synth: ingest_rss_summarize
playbooks:
  ingest_rss_summarize:
    workflow_kind: rss_fetch_then_graph_then_synth
    description: ""
    required_params: []
    allowed_params: [topic, recent_item_limit]
    policy_bindings:
      recent_item_limit: graph_lite_max_items_per_job
"""
    )
    (reg / "registry.yaml").write_text(
        yaml.dump(data, sort_keys=False), encoding="utf-8"
    )
    clear_playbook_registry_cache()
    try:
        with pytest.raises(ValueError) as ei:
            resolve_for_kind(
                "publish_entity_v1",
                policy=_policy(),
                mission_defaults={},
                params_delta={},
                project_root=tmp_path,
            )
        assert str(registry_path(tmp_path)) in str(ei.value)
    finally:
        clear_playbook_registry_cache()
