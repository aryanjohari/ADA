from __future__ import annotations

import pytest

from ada.config import build_file_deny_prefixes
from ada.tools.file_sandbox import (
    basename_denied,
    parse_sandbox_roots,
    resolve_workspace_path,
    resolve_workspace_path_guarded,
)


def test_parse_sandbox_roots_default(tmp_path):
    r = parse_sandbox_roots("", fallback=tmp_path)
    assert r == (tmp_path.resolve(),)


def test_resolve_relative_under_primary(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    (root / "a.txt").write_text("x", encoding="utf-8")
    rr = root.resolve()
    p = resolve_workspace_path(roots=(rr,), primary_root=rr, user_path="a.txt")
    assert p == (root / "a.txt").resolve()


def test_resolve_rejects_path_traversal(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    rr = root.resolve()
    with pytest.raises(ValueError, match="outside"):
        resolve_workspace_path(roots=(rr,), primary_root=rr, user_path="../../etc/passwd")


def test_resolve_absolute_inside_root(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    f = root / "b.txt"
    f.write_text("z", encoding="utf-8")
    rr = root.resolve()
    p = resolve_workspace_path(roots=(rr,), primary_root=rr, user_path=str(f))
    assert p == f.resolve()


def test_guarded_rejects_deny_prefix(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    secret = root / "secret"
    secret.mkdir()
    rr = root.resolve()
    with pytest.raises(ValueError, match="denied"):
        resolve_workspace_path_guarded(
            roots=(rr,),
            primary_root=rr,
            user_path="secret/x.txt",
            deny_prefixes=(secret.resolve(),),
        )


def test_guarded_rejects_env_basename(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    f = root / ".env"
    f.write_text("k=v", encoding="utf-8")
    rr = root.resolve()
    with pytest.raises(ValueError, match="forbidden name"):
        resolve_workspace_path_guarded(
            roots=(rr,),
            primary_root=rr,
            user_path=".env",
            deny_prefixes=(),
        )


def test_basename_denied_pem():
    assert basename_denied("x.pem") is True
    assert basename_denied("notes.txt") is False


def test_build_file_deny_prefixes_blocks_project_when_sandbox_is_parent(tmp_path):
    home = tmp_path / "home"
    proj = home / "ADA"
    home.mkdir()
    proj.mkdir()
    data = proj / "data"
    mem = proj / "memory"
    data.mkdir()
    mem.mkdir()
    pfx = build_file_deny_prefixes(
        project_root=proj,
        data_dir=data,
        memory_dir=mem,
        primary_sandbox_root=home,
        extra_comma_separated="",
        denylist_file=None,
    )
    resolved = {x.resolve() for x in pfx}
    assert proj.resolve() in resolved
    assert data.resolve() in resolved
    assert mem.resolve() in resolved


def test_build_file_deny_prefixes_does_not_block_whole_project_when_sandbox_is_project(
    tmp_path,
):
    proj = tmp_path / "ADA"
    proj.mkdir()
    data = proj / "data"
    mem = proj / "memory"
    data.mkdir()
    mem.mkdir()
    pfx = build_file_deny_prefixes(
        project_root=proj,
        data_dir=data,
        memory_dir=mem,
        primary_sandbox_root=proj,
        extra_comma_separated="",
        denylist_file=None,
    )
    resolved = {x.resolve() for x in pfx}
    assert proj.resolve() not in resolved
    assert data.resolve() in resolved
    assert mem.resolve() in resolved
