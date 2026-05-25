"""J4: ada reload invokes kernel_boot and optional daemon restart."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from ada.config import Settings
from ada.reload_cli import restart_daemon_subprocess, run_reload_cli


def _fake_kernel() -> SimpleNamespace:
    return SimpleNamespace(
        as_summary=lambda: {
            "base_ops_id": 1,
            "ada_ops_id": 2,
            "memory_source_id": 3,
        }
    )


@pytest.mark.asyncio
async def test_reload_invokes_kernel_boot(schema_sql_path, test_settings) -> None:
    boot = AsyncMock(return_value=_fake_kernel())
    restart = patch(
        "ada.reload_cli.restart_daemon_subprocess",
        return_value=(True, "systemctl restart ada-daemon.service ok"),
    )
    with patch("ada.reload_cli.kernel_boot", boot), restart:
        code = await run_reload_cli(test_settings, restart_daemon=True)
    assert code == 0
    boot.assert_awaited_once()
    args = boot.await_args
    assert isinstance(args.args[1], Settings)


@pytest.mark.asyncio
async def test_reload_no_daemon_skips_systemctl(schema_sql_path, test_settings) -> None:
    boot = AsyncMock(return_value=_fake_kernel())
    with (
        patch("ada.reload_cli.kernel_boot", boot),
        patch("ada.reload_cli.restart_daemon_subprocess") as mock_restart,
    ):
        code = await run_reload_cli(test_settings, restart_daemon=False)
    assert code == 0
    mock_restart.assert_not_called()


def test_restart_daemon_subprocess_mocked(monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))

        class R:
            returncode = 0
            stdout = ""
            stderr = ""

        return R()

    monkeypatch.setenv("ADA_RELOAD_SYSTEMD_UNIT", "ada-daemon.service")
    monkeypatch.setattr("ada.reload_cli.subprocess.run", fake_run)
    ok, detail = restart_daemon_subprocess()
    assert ok
    assert calls == [["systemctl", "restart", "ada-daemon.service"]]
    assert "ok" in detail
