"""Resolve and validate workspace paths for file tools (symlink-safe, rooted)."""

from __future__ import annotations

from pathlib import Path


def parse_sandbox_roots(raw: str, *, fallback: Path) -> tuple[Path, ...]:
    """
    Comma-separated absolute or ~ paths. Empty / whitespace-only → single `fallback`.
    """
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if not parts:
        return (fallback.expanduser().resolve(),)
    return tuple(Path(p).expanduser().resolve() for p in parts)


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
