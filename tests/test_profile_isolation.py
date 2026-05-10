"""Profile-local memory_dir and policy_root resolution (Settings.load)."""

from __future__ import annotations

import pytest

from ada.config import Settings


def _clear_profile_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ADA_DATA_DIR", raising=False)
    monkeypatch.delenv("ADA_PROFILE", raising=False)
    monkeypatch.delenv("ADA_PROFILE_DATA_ROOT", raising=False)
    monkeypatch.delenv("ADA_COMMERCIAL_DATA_DIR", raising=False)
    monkeypatch.delenv("ADA_MEMORY_DIR", raising=False)
    monkeypatch.delenv("ADA_POLICY_ROOT", raising=False)
    monkeypatch.delenv("ADA_REQUIRE_PROFILE_ISOLATION", raising=False)


def test_profile_mode_default_memory_and_policy_fallback(
    monkeypatch: pytest.MonkeyPatch, tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    _clear_profile_env(monkeypatch)
    monkeypatch.setenv("ADA_PROFILE", "acme")
    monkeypatch.setenv("ADA_PROFILE_DATA_ROOT", str(tmp_path))
    settings = Settings.load()
    assert settings.memory_dir == (tmp_path / "acme").resolve()
    assert settings.policy_root == (settings.project_root / "policies").resolve()
    err = capsys.readouterr().err
    assert "policy_root_fallback" in err
    assert "acme" in err


def test_profile_mode_policy_local_when_default_yaml_exists(
    monkeypatch: pytest.MonkeyPatch, tmp_path,
) -> None:
    _clear_profile_env(monkeypatch)
    prof = tmp_path / "acme"
    pol = prof / "policies"
    pol.mkdir(parents=True)
    (pol / "default.yaml").write_text("version: 1\n", encoding="utf-8")
    monkeypatch.setenv("ADA_PROFILE", "acme")
    monkeypatch.setenv("ADA_PROFILE_DATA_ROOT", str(tmp_path))
    settings = Settings.load()
    assert settings.policy_root == pol.resolve()


def test_profile_mode_no_fallback_log_when_local_policy_exists(
    monkeypatch: pytest.MonkeyPatch, tmp_path, capsys: pytest.CaptureFixture[str],
) -> None:
    _clear_profile_env(monkeypatch)
    prof = tmp_path / "acme"
    pol = prof / "policies"
    pol.mkdir(parents=True)
    (pol / "default.yaml").write_text("version: 1\n", encoding="utf-8")
    monkeypatch.setenv("ADA_PROFILE", "acme")
    monkeypatch.setenv("ADA_PROFILE_DATA_ROOT", str(tmp_path))
    capsys.readouterr()
    Settings.load()
    assert "policy_root_fallback" not in capsys.readouterr().err


def test_legacy_ada_data_dir_uses_repo_memory_and_policies(
    monkeypatch: pytest.MonkeyPatch, tmp_path,
) -> None:
    _clear_profile_env(monkeypatch)
    data = tmp_path / "mydata"
    data.mkdir()
    monkeypatch.setenv("ADA_DATA_DIR", str(data))
    settings = Settings.load()
    assert settings.memory_dir == (settings.project_root / "memory").resolve()
    assert settings.policy_root == (settings.project_root / "policies").resolve()


def test_explicit_memory_and_policy_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path,
) -> None:
    _clear_profile_env(monkeypatch)
    mem = tmp_path / "m1"
    mem.mkdir()
    pol_dir = tmp_path / "p1"
    pol_dir.mkdir()
    (pol_dir / "default.yaml").write_text("version: 1\nmatrix_planner_top_k: 2\n", encoding="utf-8")
    monkeypatch.setenv("ADA_PROFILE", "acme")
    monkeypatch.setenv("ADA_PROFILE_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("ADA_MEMORY_DIR", str(mem))
    monkeypatch.setenv("ADA_POLICY_ROOT", str(pol_dir))
    settings = Settings.load()
    assert settings.memory_dir == mem.resolve()
    assert settings.policy_root == pol_dir.resolve()


def test_relative_memory_dir_resolved_under_project(
    monkeypatch: pytest.MonkeyPatch, tmp_path,
) -> None:
    _clear_profile_env(monkeypatch)
    monkeypatch.delenv("ADA_POLICY_PACK", raising=False)
    monkeypatch.setenv("ADA_DATA_DIR", str(tmp_path / "d"))
    monkeypatch.setenv("ADA_MEMORY_DIR", "custom_mem_rel")
    settings = Settings.load()
    assert settings.memory_dir == (settings.project_root / "custom_mem_rel").resolve()


def test_commercial_mode_uses_repo_memory_by_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path,
) -> None:
    _clear_profile_env(monkeypatch)
    comm = tmp_path / "commercial_data"
    comm.mkdir()
    monkeypatch.setenv("ADA_COMMERCIAL_DATA_DIR", str(comm))
    settings = Settings.load()
    assert settings.memory_dir == (settings.project_root / "memory").resolve()
    assert settings.policy_root == (settings.project_root / "policies").resolve()


def test_strict_rejects_memory_under_repo(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    _clear_profile_env(monkeypatch)
    pol = tmp_path / "ext_policies"
    pol.mkdir()
    (pol / "default.yaml").write_text("version: 1\n", encoding="utf-8")
    monkeypatch.setenv("ADA_REQUIRE_PROFILE_ISOLATION", "1")
    monkeypatch.setenv("ADA_PROFILE", "t1")
    monkeypatch.setenv("ADA_PROFILE_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("ADA_MEMORY_DIR", "memory")
    monkeypatch.setenv("ADA_POLICY_ROOT", str(pol))
    with pytest.raises(ValueError, match="ADA_MEMORY_DIR"):
        Settings.load()


def test_strict_rejects_policy_under_repo(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    _clear_profile_env(monkeypatch)
    monkeypatch.setenv("ADA_REQUIRE_PROFILE_ISOLATION", "1")
    monkeypatch.setenv("ADA_PROFILE", "t1")
    monkeypatch.setenv("ADA_PROFILE_DATA_ROOT", str(tmp_path))
    with pytest.raises(ValueError, match="ADA_POLICY_ROOT"):
        Settings.load()


def test_strict_succeeds_when_memory_and_policy_outside_repo(
    monkeypatch: pytest.MonkeyPatch, tmp_path,
) -> None:
    _clear_profile_env(monkeypatch)
    pol = tmp_path / "t1" / "policies"
    pol.mkdir(parents=True)
    (pol / "default.yaml").write_text("version: 1\n", encoding="utf-8")
    monkeypatch.setenv("ADA_REQUIRE_PROFILE_ISOLATION", "1")
    monkeypatch.setenv("ADA_PROFILE", "t1")
    monkeypatch.setenv("ADA_PROFILE_DATA_ROOT", str(tmp_path))
    settings = Settings.load()
    root = settings.project_root.resolve()
    assert not settings.memory_dir.resolve().is_relative_to(root)
    assert not settings.policy_root.resolve().is_relative_to(root)


def test_file_deny_prefixes_include_profile_memory(
    monkeypatch: pytest.MonkeyPatch, tmp_path,
) -> None:
    _clear_profile_env(monkeypatch)
    monkeypatch.setenv("ADA_PROFILE", "p1")
    monkeypatch.setenv("ADA_PROFILE_DATA_ROOT", str(tmp_path))
    settings = Settings.load()
    assert settings.memory_dir.resolve() in settings.file_deny_prefixes


def test_ensure_data_dir_creates_profile_memory(
    monkeypatch: pytest.MonkeyPatch, tmp_path,
) -> None:
    _clear_profile_env(monkeypatch)
    monkeypatch.setenv("ADA_PROFILE", "p1")
    monkeypatch.setenv("ADA_PROFILE_DATA_ROOT", str(tmp_path))
    settings = Settings.load()
    assert not settings.memory_dir.exists()
    settings.ensure_data_dir()
    assert settings.memory_dir.is_dir()
    assert settings.data_dir.is_dir()
