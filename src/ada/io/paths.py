"""Resolve durable data paths under ADA_DATA_ROOT.

Default production root is /mnt/ada-data (HDD autobiography substrate).
Tests override via ADA_DATA_ROOT so they never touch the real mount.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_ADA_DATA_ROOT = "/mnt/ada-data"
ENV_ADA_DATA_ROOT = "ADA_DATA_ROOT"


class BodyFault(Exception):
    """Hard body fault — refuse durable writes; do not fake success."""

    def __init__(self, message: str, *, code: int = 3) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class DataPaths:
    """Canonical layout under the durable substrate."""

    root: Path

    @property
    def memory(self) -> Path:
        return self.root / "memory"

    @property
    def facts(self) -> Path:
        return self.memory / "facts"

    @property
    def identity_yaml(self) -> Path:
        return self.facts / "identity.yaml"

    @property
    def lifecycle_jsonl(self) -> Path:
        return self.memory / "lifecycle.jsonl"

    @property
    def runs(self) -> Path:
        """Episodic chat transcripts / tool receipts (M02)."""
        return self.root / "runs"


def get_data_root() -> Path:
    raw = os.environ.get(ENV_ADA_DATA_ROOT, DEFAULT_ADA_DATA_ROOT)
    return Path(raw).expanduser().resolve()


def get_paths(root: Path | None = None) -> DataPaths:
    return DataPaths(root=root if root is not None else get_data_root())


def ada_data_mounted(root: Path | None = None) -> bool:
    """Honesty gate: durable substrate present and acceptable for writes.

    Production (default root): directory must exist and be a mount point.
    Override via ADA_DATA_ROOT or an explicit non-default *root*: existence
    of the directory is enough (pytest tmp_path sandboxes are not mounts).
    """
    path = (root if root is not None else get_data_root()).resolve()
    if not path.is_dir():
        return False

    default = Path(DEFAULT_ADA_DATA_ROOT).resolve()
    sandbox = ENV_ADA_DATA_ROOT in os.environ or path != default
    if sandbox:
        return True

    try:
        return path.is_mount()
    except OSError:
        return False


def require_ada_data(root: Path | None = None) -> DataPaths:
    """Return paths or raise BodyFault when substrate is missing."""
    paths = get_paths(root)
    if not ada_data_mounted(paths.root):
        raise BodyFault(
            f"ada-data not mounted or missing at {paths.root}; refusing durable writes"
        )
    return paths
