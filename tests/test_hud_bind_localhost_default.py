"""HUD bind defaults — loopback only."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from ada.cli.main import app
from ada.hud import DEFAULT_HOST, DEFAULT_PORT, assert_loopback_host


def test_default_host_is_loopback():
    assert DEFAULT_HOST == "127.0.0.1"
    assert DEFAULT_PORT == 8787
    assert assert_loopback_host("127.0.0.1") == "127.0.0.1"
    assert assert_loopback_host("localhost") == "127.0.0.1"


def test_non_loopback_refused():
    with pytest.raises(ValueError, match="non-loopback"):
        assert_loopback_host("0.0.0.0")
    with pytest.raises(ValueError, match="non-loopback"):
        assert_loopback_host("192.168.1.10")


def test_cli_hud_serve_refuses_lan_bind():
    runner = CliRunner()
    result = runner.invoke(app, ["hud", "serve", "--host", "0.0.0.0", "--port", "8799"])
    assert result.exit_code == 2
    assert "bind refused" in (result.stdout + result.stderr).lower() or "non-loopback" in (
        result.stdout + result.stderr
    )
