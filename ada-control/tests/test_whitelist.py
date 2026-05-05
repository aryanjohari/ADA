"""Tests for ada subprocess argv whitelist."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib.whitelist import build_argv  # noqa: E402


def test_mission_list():
    assert build_argv("/x/ada", command_id="mission_list", mission_limit=10) == [
        "/x/ada",
        "mission",
        "list",
        "--limit",
        "10",
    ]


def test_mission_tick_requires_slug():
    with pytest.raises(ValueError, match="mission slug"):
        build_argv("ada", command_id="mission_tick_dry_run", mission_slug=None)


def test_matrix_dry_run_optional_mission():
    a = build_argv("ada", command_id="matrix_scan_dry_run")
    assert "matrix-scan" in a and "--dry-run" in a
    b = build_argv(
        "ada",
        command_id="matrix_scan_dry_run",
        mission_slug="acme_site",
        matrix_deterministic=True,
    )
    assert "--mission" in b and "acme_site" in b and "--deterministic" in b
