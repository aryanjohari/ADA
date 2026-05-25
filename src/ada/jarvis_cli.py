"""`ada jarvis` — launch HUD (Streamlit) + print canonical chat hint."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from ada.config import Settings, _find_project_root


def run_jarvis_launch() -> int:
    """Start Streamlit HUD (blocks until exit)."""
    if shutil.which("streamlit") is None:
        print(
            "ada jarvis: streamlit not installed. Run: pip install -e '.[streamlit]'",
            file=sys.stderr,
        )
        return 2

    settings = Settings.load()
    root = _find_project_root()
    app = root / "scripts" / "ada_observability_app.py"
    if not app.is_file():
        print(f"ada jarvis: missing {app}", file=sys.stderr)
        return 2

    mission = (
        os.environ.get("ADA_CHAT_DEFAULT_MISSION", "").strip()
        or os.environ.get("ADA_JARVIS_MISSION", "").strip()
    )
    env = dict(os.environ)
    if mission:
        env["ADA_OPERATOR_DEFAULT_MISSION"] = mission

    print(
        "Note: `ada jarvis` is deprecated; use `ada hud` for the operator UI.",
        flush=True,
    )
    print("ADA operator HUD — Streamlit", flush=True)
    print(f"  state.db: {settings.state_db_path}", flush=True)
    if mission:
        print(f"  mission filter: {mission}", flush=True)
    chat_hint = f"ada chat --mission {mission}" if mission else "ada chat"
    print(f"  brain (canonical): {chat_hint}", flush=True)
    print("  Press Ctrl-C to stop Streamlit.", flush=True)

    argv = [
        "streamlit",
        "run",
        str(app),
        "--server.headless",
        "true",
    ]
    try:
        return int(subprocess.call(argv, cwd=str(root), env=env, shell=False))
    except KeyboardInterrupt:
        return 0
