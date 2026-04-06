from __future__ import annotations

import pytest

from ada.tools.file_sandbox import parse_sandbox_roots, resolve_workspace_path


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
