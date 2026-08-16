"""M18 Tier A gate CLI smoke — help + marker registration (no full suite)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ada.cli.main import app

runner = CliRunner()

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.tier_a
def test_tier_a_help() -> None:
    result = runner.invoke(app, ["tier-a", "--help"])
    assert result.exit_code == 0
    assert "check" in result.stdout.lower()


@pytest.mark.tier_a
def test_tier_a_check_help() -> None:
    result = runner.invoke(app, ["tier-a", "check", "--help"])
    assert result.exit_code == 0
    assert "--json" in result.stdout


@pytest.mark.tier_a
def test_tier_a_marker_registered() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--markers"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "tier_a:" in proc.stdout
