"""Memory file allowlist for operator UI."""

from __future__ import annotations

from pathlib import Path

from ada.observability.memory_files import memory_write_allowed, resolve_memory_bootstrap_file


def test_write_denied_under_repo_when_isolation(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    mem = repo / "memory"
    mem.mkdir(parents=True)
    f = resolve_memory_bootstrap_file(mem, "soul.md")
    ok, reason = memory_write_allowed(
        target=f,
        memory_dir=mem,
        project_root=repo,
        require_profile_isolation=True,
    )
    assert not ok
    assert "REQUIRE_PROFILE_ISOLATION" in reason


def test_write_allowed_legacy(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    mem = repo / "memory"
    mem.mkdir(parents=True)
    f = resolve_memory_bootstrap_file(mem, "master.md")
    ok, reason = memory_write_allowed(
        target=f,
        memory_dir=mem,
        project_root=repo,
        require_profile_isolation=False,
    )
    assert ok
    assert reason == ""
