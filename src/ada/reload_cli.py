"""`ada reload` — refresh kernel cache and restart the goal daemon (no DB wipe)."""

from __future__ import annotations

import os
import subprocess
import sys

from ada.boot import kernel_boot
from ada.config import Settings
from ada.profile_runtime import enforce_profile_identity
from ada.query_engine import QueryEngine


def _default_schema_path():
    from pathlib import Path

    import ada

    return Path(ada.__path__[0]) / "db" / "schema.sql"


def _systemd_unit() -> str | None:
    raw = (
        os.environ.get("ADA_RELOAD_SYSTEMD_UNIT", "").strip()
        or os.environ.get("ADA_PI_SYSTEMD_SERVICE_NAME", "").strip()
    )
    return raw or None


def _systemd_user_mode() -> bool:
    return os.environ.get("ADA_RELOAD_SYSTEMD_USER", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def restart_daemon_subprocess(*, unit: str | None = None) -> tuple[bool, str]:
    """
    Restart the long-running `ada daemon` worker.

    Uses systemctl when ADA_RELOAD_SYSTEMD_UNIT or ADA_PI_SYSTEMD_SERVICE_NAME is set.
    Returns (ok, human-readable detail).
    """
    resolved = unit if unit is not None else _systemd_unit()
    if not resolved:
        return (
            False,
            "no systemd unit configured "
            "(set ADA_RELOAD_SYSTEMD_UNIT or ADA_PI_SYSTEMD_SERVICE_NAME)",
        )
    cmd = ["systemctl"]
    if _systemd_user_mode():
        cmd.append("--user")
    cmd.extend(["restart", resolved])
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except FileNotFoundError:
        return False, "systemctl not found on PATH"
    except subprocess.TimeoutExpired:
        return False, f"timed out running {' '.join(cmd)}"
    detail = (proc.stderr or proc.stdout or "").strip()
    if proc.returncode != 0:
        msg = detail or f"exit {proc.returncode}"
        return False, f"{' '.join(cmd)} failed: {msg}"
    return True, f"{' '.join(cmd)} ok"


async def run_reload_cli(
    settings: Settings,
    *,
    restart_daemon: bool = True,
) -> int:
    """
    Connect, kernel_boot, optionally restart daemon via systemd.

    Does not wipe SQLite or restart Streamlit.
    """
    settings.ensure_data_dir()
    schema_path = _default_schema_path()
    qe = QueryEngine(
        settings.state_db_path,
        schema_path,
        debounce_ms=settings.persist_debounce_ms,
    )
    await qe.connect()
    try:
        await enforce_profile_identity(qe, settings)
        kernel = await kernel_boot(qe, settings)
        summary = kernel.as_summary()
        print(
            "kernel reload ok:"
            f" base_ops_id={summary['base_ops_id']}"
            f" ada_ops_id={summary['ada_ops_id']}"
            f" memory_source_id={summary['memory_source_id']}"
        )
    finally:
        await qe.close()

    print("reload: no database wipe (state.db row data preserved)", flush=True)

    daemon_ok = True
    if not restart_daemon:
        print("daemon: skipped (--no-daemon)", flush=True)
    else:
        daemon_ok, detail = restart_daemon_subprocess()
        if daemon_ok:
            print(f"daemon: {detail}", flush=True)
        else:
            print(f"daemon: {detail}", file=sys.stderr, flush=True)
            print(
                "daemon: restart manually, e.g. "
                "sudo systemctl restart ada-daemon.service "
                "(see docs/ADA_CORE_OPS.md)",
                file=sys.stderr,
                flush=True,
            )

    print(
        "streamlit: not restarted by reload — stop and re-run `ada hud` if the HUD is open",
        flush=True,
    )
    return 0 if (not restart_daemon or daemon_ok) else 1
