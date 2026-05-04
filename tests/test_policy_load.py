"""Policy YAML merge and intent loader."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from unittest.mock import MagicMock

from ada.policy.load import (
    DEFAULT_BATCH_ENRICH_MAX_ENTITIES,
    DEFAULT_GRAPH_LITE_MAX_ITEMS_PER_JOB,
    load_intent_md,
    load_merged_policy,
    load_merged_policy_for,
    load_policy_yaml_dict,
)


def test_load_merged_defaults_when_yaml_missing(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "policies").mkdir(parents=True, exist_ok=True)
    cfg = load_merged_policy(project_root=tmp_path)
    assert cfg.version == 1
    assert cfg.matrix_planner_top_k == 5
    assert cfg.graph_lite_max_items_per_job == DEFAULT_GRAPH_LITE_MAX_ITEMS_PER_JOB
    assert cfg.batch_enrich_max_entities == DEFAULT_BATCH_ENRICH_MAX_ENTITIES


def test_merged_yaml_order_overlay_env(tmp_path: Path, monkeypatch):
    (tmp_path / "policies").mkdir(parents=True, exist_ok=True)
    base = tmp_path / "policies" / "default.yaml"
    base.write_text(
        yaml.safe_dump(
            {"version": 1, "intent_max_bytes": 4096, "matrix_planner_top_k": 3},
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    overlay_dir = tmp_path / "ov"
    overlay_dir.mkdir(parents=True, exist_ok=True)
    (overlay_dir / "extra.yaml").write_text(
        "matrix_planner_top_k: 7\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("ADA_POLICY_PACK", str(overlay_dir))
    monkeypatch.setenv("ADA_INTENT_MAX_BYTES", "8192")
    monkeypatch.delenv("ADA_MATRIX_PLANNER_TOP_K", raising=False)

    cfg = load_merged_policy(project_root=tmp_path)
    assert cfg.intent_max_bytes == 8192
    assert cfg.matrix_planner_top_k == 7


def test_overlay_file_requires_yaml_suffix(tmp_path: Path, monkeypatch):
    (tmp_path / "policies").mkdir(parents=True, exist_ok=True)
    (tmp_path / "policies" / "default.yaml").write_text("version: 1\n")
    junk = tmp_path / "oops.txt"
    junk.write_text("x")
    monkeypatch.setenv("ADA_POLICY_PACK", str(junk))
    with pytest.raises(ValueError, match="\\.yaml"):
        load_merged_policy(project_root=tmp_path)


def test_invalid_default_yaml_raises(tmp_path: Path):
    (tmp_path / "policies").mkdir(parents=True, exist_ok=True)
    path = tmp_path / "policies" / "default.yaml"
    path.write_text("{broken", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid policy YAML"):
        load_policy_yaml_dict(project_root=tmp_path)


def test_bad_version_type_raises(tmp_path: Path):
    (tmp_path / "policies").mkdir(parents=True, exist_ok=True)
    (tmp_path / "policies" / "default.yaml").write_text(
        yaml.safe_dump({"version": "nope"}), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="version"):
        load_merged_policy(project_root=tmp_path)


def test_bad_graph_lite_max_items_raises(tmp_path: Path):
    (tmp_path / "policies").mkdir(parents=True, exist_ok=True)
    (tmp_path / "policies" / "default.yaml").write_text(
        yaml.safe_dump({"version": 1, "graph_lite_max_items_per_job": "x"}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="graph_lite_max_items_per_job"):
        load_merged_policy(project_root=tmp_path)


def test_intent_md_missing_returns_empty(tmp_path: Path):
    mem = tmp_path / "memory"
    mem.mkdir(parents=True, exist_ok=True)
    assert load_intent_md(mem) == ""


def test_intent_md_respects_cap(tmp_path: Path):
    mem = tmp_path / "memory"
    mem.mkdir(parents=True, exist_ok=True)
    (mem / "intent.md").write_text("abcdefghi", encoding="utf-8")
    assert load_intent_md(mem, max_bytes=4) == "abcd"


def test_load_policy_yaml_dict_with_policy_root(tmp_path: Path) -> None:
    pr = tmp_path / "policies_alt"
    pr.mkdir(parents=True)
    (pr / "default.yaml").write_text("version: 1\nmatrix_planner_top_k: 9\n", encoding="utf-8")
    data = load_policy_yaml_dict(policy_root=pr)
    assert data.get("matrix_planner_top_k") == 9


def test_load_merged_policy_policy_root_wins_over_project_root(tmp_path: Path) -> None:
    """Explicit policy_root overrides project_root."""
    fake_proj = tmp_path / "fakeproj"
    fake_proj.mkdir()
    (fake_proj / "policies").mkdir(parents=True)
    (fake_proj / "policies" / "default.yaml").write_text(
        "version: 1\nmatrix_planner_top_k: 1\n", encoding="utf-8"
    )
    pr = tmp_path / "winner"
    pr.mkdir(parents=True)
    (pr / "default.yaml").write_text("version: 1\nmatrix_planner_top_k: 99\n", encoding="utf-8")
    cfg = load_merged_policy(project_root=fake_proj, policy_root=pr)
    assert cfg.matrix_planner_top_k == 99


def test_relative_ada_policy_pack_resolves_against_policy_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    pr = tmp_path / "policies_here"
    pr.mkdir(parents=True)
    (pr / "default.yaml").write_text("version: 1\nmatrix_planner_top_k: 3\n", encoding="utf-8")
    (pr / "overlay.yaml").write_text("matrix_planner_top_k: 8\n", encoding="utf-8")
    monkeypatch.setenv("ADA_POLICY_PACK", "overlay.yaml")
    cfg = load_merged_policy(policy_root=pr)
    assert cfg.matrix_planner_top_k == 8


def test_relative_ada_policy_pack_with_project_root_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "policies").mkdir(parents=True)
    (tmp_path / "policies" / "default.yaml").write_text(
        "version: 1\nmatrix_planner_top_k: 3\n", encoding="utf-8"
    )
    (tmp_path / "policies" / "overlay.yaml").write_text("matrix_planner_top_k: 6\n", encoding="utf-8")
    monkeypatch.setenv("ADA_POLICY_PACK", "overlay.yaml")
    cfg = load_merged_policy(project_root=tmp_path)
    assert cfg.matrix_planner_top_k == 6


def test_load_merged_policy_for(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    pr = tmp_path / "policies"
    pr.mkdir(parents=True)
    (pr / "default.yaml").write_text("version: 1\nmatrix_planner_top_k: 4\n", encoding="utf-8")
    monkeypatch.delenv("ADA_POLICY_PACK", raising=False)
    st = MagicMock()
    st.policy_root = pr
    cfg = load_merged_policy_for(st)
    assert cfg.matrix_planner_top_k == 4

