"""Shared pytest fixtures — always sandbox via ADA_DATA_ROOT."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture
def data_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "ada-data"
    root.mkdir()
    monkeypatch.setenv("ADA_DATA_ROOT", str(root))
    return root


@pytest.fixture
def missing_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    missing = tmp_path / "not-mounted"
    monkeypatch.setenv("ADA_DATA_ROOT", str(missing))
    return missing
