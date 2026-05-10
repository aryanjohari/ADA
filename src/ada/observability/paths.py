"""Resolve state.db path from environment (mirrors ada.config.Settings.load data_dir rules).

Does not call Settings.load() so full settings are not materialized. Uses
``resolve_runtime_paths_from_environ`` for a single source of truth.
"""

from __future__ import annotations

from pathlib import Path

from ada.config import resolve_runtime_paths_from_environ


def resolve_data_dir() -> Path:
    """Return resolved profile/data directory (same rules as Settings.load)."""
    return resolve_runtime_paths_from_environ().data_dir


def resolve_state_db_path() -> Path:
    """Absolute path to state.db for the current environment."""
    return resolve_runtime_paths_from_environ().state_db_path
