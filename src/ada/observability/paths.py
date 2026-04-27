"""Resolve state.db path from environment (mirrors ada.config.Settings.load data_dir rules).

Does not call Settings.load() so GEMINI_API_KEY and other settings are not read into memory.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

PROFILE_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,63}$")


def _find_project_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()


def resolve_data_dir() -> Path:
    """Return resolved profile/data directory (same rules as Settings.load)."""
    root = _find_project_root()
    require_profile_isolation = os.environ.get(
        "ADA_REQUIRE_PROFILE_ISOLATION", "0"
    ).strip().lower() in ("1", "true", "yes", "on")
    profile_raw = os.environ.get("ADA_PROFILE", "").strip().lower()
    profile_root_raw = os.environ.get("ADA_PROFILE_DATA_ROOT", "").strip()
    commercial_raw = os.environ.get("ADA_COMMERCIAL_DATA_DIR", "").strip()
    if profile_raw or profile_root_raw:
        if commercial_raw:
            raise ValueError(
                "ADA_COMMERCIAL_DATA_DIR cannot be combined with ADA_PROFILE/ADA_PROFILE_DATA_ROOT"
            )
        if not profile_raw:
            raise ValueError("ADA_PROFILE is required when ADA_PROFILE_DATA_ROOT is set")
        if not PROFILE_SLUG_RE.match(profile_raw):
            raise ValueError("ADA_PROFILE must match ^[a-z0-9][a-z0-9_-]{1,63}$")
        if not profile_root_raw:
            raise ValueError("ADA_PROFILE_DATA_ROOT is required when ADA_PROFILE is set")
        profile_data_root = Path(profile_root_raw).expanduser()
        if not profile_data_root.is_absolute():
            raise ValueError("ADA_PROFILE_DATA_ROOT must be an absolute path")
        data_dir = profile_data_root / profile_raw
    elif commercial_raw:
        data_dir = Path(commercial_raw).expanduser()
    else:
        data_dir = Path(os.environ.get("ADA_DATA_DIR", str(root / "data"))).expanduser()
    if require_profile_isolation and not profile_raw:
        raise ValueError(
            "ADA_REQUIRE_PROFILE_ISOLATION=1 requires ADA_PROFILE and ADA_PROFILE_DATA_ROOT"
        )
    return data_dir.resolve()


def resolve_state_db_path() -> Path:
    """Absolute path to state.db for the current environment."""
    return (resolve_data_dir() / "state.db").resolve()
