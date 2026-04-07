"""Resolve and validate workspace paths for file tools (rooted + denylist)."""

from __future__ import annotations

import os
from pathlib import Path

# Basename rules: exact names plus any file ending in .pem
_DEFAULT_BASENAME_EXACT: frozenset[str] = frozenset((".env", "id_rsa"))


def parse_sandbox_roots(raw: str, *, fallback: Path) -> tuple[Path, ...]:
    """
    Comma-separated absolute or ~ paths. Empty / whitespace-only → single `fallback`.
    """
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if not parts:
        return (fallback.expanduser().resolve(),)
    return tuple(Path(p).expanduser().resolve() for p in parts)


def is_under_any_root(path: Path, roots: tuple[Path, ...]) -> bool:
    """True if resolved `path` is equal to or under one of resolved `roots`."""
    rp = path.resolve()
    for root in roots:
        try:
            rp.relative_to(root.resolve())
            return True
        except ValueError:
            continue
    return False


def _is_under_deny_prefix(path: Path, deny_prefix: Path) -> bool:
    try:
        path.resolve().relative_to(deny_prefix.resolve())
        return True
    except ValueError:
        return path.resolve() == deny_prefix.resolve()


def basename_denied(name: str, extra_exact: frozenset[str] | None = None) -> bool:
    """True if file basename matches hardened deny rules (.env, id_rsa, *.pem, plus extras)."""
    exact = _DEFAULT_BASENAME_EXACT | (extra_exact or frozenset())
    if name in exact:
        return True
    return name.endswith(".pem")


def assert_not_denied(
    path: Path,
    *,
    deny_prefixes: tuple[Path, ...],
    deny_basenames_extra: frozenset[str] | None = None,
) -> None:
    """
    Raise ValueError if path is under a deny prefix or basename is forbidden.
    Prefixes should already be resolved; path may be resolved inside this call.
    """
    rp = path.resolve()
    for prefix in deny_prefixes:
        if _is_under_deny_prefix(rp, prefix):
            raise ValueError(f"path denied by policy (under {prefix})")
    if basename_denied(rp.name, deny_basenames_extra):
        raise ValueError(f"path denied by policy (forbidden name: {rp.name!r})")


def resolve_workspace_path(
    *,
    roots: tuple[Path, ...],
    primary_root: Path,
    user_path: str,
) -> Path:
    """
    Map a user-supplied path to a resolved Path that must lie under one of `roots`.

    - Relative paths are resolved against `primary_root` (first sandbox root).
    - Absolute paths must still fall under at least one root after resolution.
    """
    raw = user_path.strip()
    if not raw:
        raise ValueError("empty path")
    if "\x00" in raw:
        raise ValueError("path contains null byte")

    p = Path(raw).expanduser()
    if p.is_absolute():
        candidate = p.resolve()
    else:
        candidate = (primary_root / p).resolve()

    resolved_roots = tuple(r.resolve() for r in roots)
    for root in resolved_roots:
        try:
            candidate.relative_to(root)
            return candidate
        except ValueError:
            continue
    raise ValueError("path outside configured sandbox roots")


def resolve_workspace_path_guarded(
    *,
    roots: tuple[Path, ...],
    primary_root: Path,
    user_path: str,
    deny_prefixes: tuple[Path, ...],
    deny_basenames_extra: frozenset[str] | None = None,
) -> Path:
    """Resolve path under sandbox roots, then apply denylist."""
    candidate = resolve_workspace_path(
        roots=roots,
        primary_root=primary_root,
        user_path=user_path,
    )
    assert_not_denied(
        candidate,
        deny_prefixes=deny_prefixes,
        deny_basenames_extra=deny_basenames_extra,
    )
    return candidate


def load_denylist_paths_from_file(path: Path) -> tuple[Path, ...]:
    """One path per line; # comments; blank lines skipped. Paths expanded and resolved."""
    if not path.is_file():
        return ()
    out: list[Path] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        out.append(Path(line).expanduser().resolve())
    return tuple(out)


def list_directory_entries(
    dir_path: Path,
    *,
    max_entries: int,
) -> dict:
    """
    Non-recursive listing with follow_symlinks=False for stat.
    Returns a dict suitable for JSON tool response, or {"error": ...}.
    """
    if not dir_path.is_dir():
        return {"error": "not a directory or does not exist", "path": str(dir_path)}
    try:
        with os.scandir(dir_path) as it:
            names = sorted((e for e in it), key=lambda e: e.name)
    except OSError as e:
        return {"error": str(e), "path": str(dir_path)}
    truncated = len(names) > max_entries
    slice_names = names[:max_entries]
    entries: list[dict[str, str | bool | None]] = []
    for entry in slice_names:
        try:
            is_link = entry.is_symlink()
            is_dir = entry.is_dir(follow_symlinks=False)
            is_file = entry.is_file(follow_symlinks=False)
        except OSError:
            kind = "unknown"
        else:
            if is_link:
                kind = "symlink"
            elif is_dir:
                kind = "directory"
            elif is_file:
                kind = "file"
            else:
                kind = "other"
        try:
            st = entry.stat(follow_symlinks=False)
            size_b = st.st_size if kind == "file" else None
        except OSError:
            size_b = None
        entries.append(
            {
                "name": entry.name,
                "kind": kind,
                "size_bytes": size_b,
            }
        )
    return {
        "path": str(dir_path),
        "entries": entries,
        "truncated": truncated,
        "total_seen": len(names),
    }
