"""Resolve ADA paths without importing the ada package."""

from __future__ import annotations

import os
from pathlib import Path


def resolve_data_dir(repo_root: Path, *, dotenv_hints: dict[str, str]) -> Path:
    raw = (dotenv_hints.get("ADA_DATA_DIR") or os.environ.get("ADA_DATA_DIR") or "").strip()
    if raw:
        p = Path(raw).expanduser()
        if not p.is_absolute():
            p = (repo_root / p).resolve()
        return p.resolve()
    return (repo_root / "data").resolve()


def resolve_memory_dir(repo_root: Path, *, dotenv_hints: dict[str, str]) -> Path:
    raw = (dotenv_hints.get("ADA_MEMORY_DIR") or os.environ.get("ADA_MEMORY_DIR") or "").strip()
    if raw:
        p = Path(raw).expanduser()
        if not p.is_absolute():
            p = (repo_root / p).resolve()
        return p.resolve()
    return (repo_root / "memory").resolve()


def resolve_state_db_path(data_dir: Path) -> Path:
    return (data_dir / "state.db").resolve()
