"""Load and validate allowlisted argv lines for `run_allowlisted_shell`."""

from __future__ import annotations

import shlex
from pathlib import Path


def load_allowlist_exact_lines(path: Path) -> frozenset[str]:
    """Each non-empty, non-comment line is an allowed command string (exact match after strip)."""
    if not path.is_file():
        return frozenset()
    lines: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        lines.add(line)
    return frozenset(lines)


def command_to_argv(command_line: str) -> list[str]:
    parts = shlex.split(command_line.strip())
    if not parts:
        raise ValueError("empty command")
    return parts
