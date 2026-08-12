"""CLI status --json via Typer CliRunner."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from ada.body.identity import create_identity
from ada.cli.main import app
from ada.io.paths import get_paths

runner = CliRunner()


def test_cli_status_json(data_root: Path) -> None:
    create_identity(paths=get_paths())
    result = runner.invoke(app, ["body", "status", "--json"])
    assert result.exit_code in {0, 2}  # 2 = soft probe degrade OK in CI sandboxes
    payload = json.loads(result.stdout)
    assert "vitals" in payload
    assert payload["vitals"]["schema_version"] == 1
    assert payload["identity"] is not None
    assert payload["identity"]["name"] == "ADA"


def test_cli_birth_idempotent(data_root: Path) -> None:
    r1 = runner.invoke(app, ["body", "birth"])
    assert r1.exit_code == 0
    assert "born" in r1.stdout.lower()
    r2 = runner.invoke(app, ["body", "birth"])
    assert r2.exit_code == 0
    assert "already born" in r2.stdout.lower()


def test_cli_doctor_missing_root(missing_root: Path) -> None:
    result = runner.invoke(app, ["body", "doctor"])
    assert result.exit_code == 3
