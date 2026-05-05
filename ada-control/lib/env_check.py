"""Compare .env keys to .env.example for operator checklist."""

from __future__ import annotations

import re
from pathlib import Path

_KEY_LINE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=")


def keys_from_env_example(path: Path) -> list[str]:
    if not path.is_file():
        return []
    keys: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        m = _KEY_LINE.match(s)
        if m:
            keys.append(m.group(1))
    return keys


def parse_dotenv_file(path: Path) -> dict[str, str]:
    """Best-effort KEY=VALUE parse (no multiline continuation)."""
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if "=" not in s:
            continue
        key, _, val = s.partition("=")
        key = key.strip()
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key):
            continue
        val = val.strip()
        out[key] = val
    return out


SMOKE_REQUIRED_KEYS = (
    "GEMINI_API_KEY",
)
