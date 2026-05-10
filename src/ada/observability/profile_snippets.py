"""Profile discovery and EnvironmentFile helpers."""

from __future__ import annotations

from pathlib import Path

from ada.config import PROFILE_SLUG_RE


def list_profile_slugs(profile_data_root: Path) -> list[str]:
    """List child directory names that match ADA profile slug rules."""
    root = Path(profile_data_root).expanduser().resolve()
    if not root.is_dir():
        return []
    out: list[str] = []
    try:
        for child in sorted(root.iterdir()):
            if child.is_dir() and PROFILE_SLUG_RE.fullmatch(child.name):
                out.append(child.name)
    except OSError:
        return []
    return out
