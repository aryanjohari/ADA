"""Tests for resolve_runtime_paths_from_environ (shared with Settings.load)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from ada.config import resolve_runtime_paths_from_environ


def test_legacy_data_dir_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ADA_PROFILE", raising=False)
    monkeypatch.delenv("ADA_PROFILE_DATA_ROOT", raising=False)
    monkeypatch.delenv("ADA_COMMERCIAL_DATA_DIR", raising=False)
    monkeypatch.delenv("ADA_REQUIRE_PROFILE_ISOLATION", raising=False)
    monkeypatch.setenv("ADA_DATA_DIR", str(tmp_path / "data"))
    rp = resolve_runtime_paths_from_environ(
        project_root=tmp_path,
        environ=dict(os.environ),
        warn_policy_fallback=False,
    )
    assert rp.data_dir == (tmp_path / "data").resolve()
    assert rp.memory_dir == (tmp_path / "memory").resolve()
    assert rp.active_profile_slug is None


def test_profile_mode_memory_under_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "profiles"
    root.mkdir()
    prof = "acme"
    monkeypatch.delenv("ADA_MEMORY_DIR", raising=False)
    monkeypatch.delenv("ADA_POLICY_ROOT", raising=False)
    monkeypatch.delenv("ADA_REQUIRE_PROFILE_ISOLATION", raising=False)
    env = {
        "ADA_PROFILE": prof,
        "ADA_PROFILE_DATA_ROOT": str(root),
    }
    rp = resolve_runtime_paths_from_environ(
        project_root=tmp_path,
        environ=env,
        warn_policy_fallback=False,
    )
    assert rp.data_dir == (root / prof).resolve()
    assert rp.memory_dir == (root / prof).resolve()
    assert rp.active_profile_slug == prof


def test_require_isolation_rejects_repo_memory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "profiles"
    root.mkdir()
    env = {
        "ADA_REQUIRE_PROFILE_ISOLATION": "1",
        "ADA_PROFILE": "t1",
        "ADA_PROFILE_DATA_ROOT": str(root),
        "ADA_MEMORY_DIR": "memory",
    }
    with pytest.raises(ValueError, match="ADA_MEMORY_DIR"):
        resolve_runtime_paths_from_environ(
            project_root=tmp_path,
            environ=env,
            warn_policy_fallback=False,
        )
