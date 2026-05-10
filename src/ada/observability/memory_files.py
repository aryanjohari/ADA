"""Allowlisted read/write for bootstrap memory markdown under ``memory_dir``."""

from __future__ import annotations

from pathlib import Path

# Editable bootstrap files (basenames only). Intent/soul/master required by plan; others common in ADA.
DEFAULT_BOOTSTRAP_BASENAMES: tuple[str, ...] = (
    "intent.md",
    "master.md",
    "soul.md",
    "wakeup.md",
    "shell_allowlist.txt",
)

_DENY_BASENAMES = frozenset({".env", ".env.local", "id_rsa"})
_DENY_SUFFIXES = (".pem", ".key")


def is_basename_allowed(name: str) -> bool:
    if not name or name in _DENY_BASENAMES or "/" in name or "\\" in name:
        return False
    lower = name.lower()
    if any(lower.endswith(s) for s in _DENY_SUFFIXES):
        return False
    return name in DEFAULT_BOOTSTRAP_BASENAMES


def resolve_memory_bootstrap_file(memory_dir: Path, basename: str) -> Path:
    return (memory_dir / basename).resolve()


def memory_write_allowed(
    *,
    target: Path,
    memory_dir: Path,
    project_root: Path,
    require_profile_isolation: bool,
) -> tuple[bool, str]:
    """Return (ok, reason)."""
    mem_r = memory_dir.resolve()
    try:
        tgt_r = target.resolve()
    except OSError as e:
        return False, str(e)
    try:
        if not tgt_r.is_relative_to(mem_r):
            return False, "path escapes memory_dir"
    except (OSError, ValueError):
        return False, "path escapes memory_dir"
    if not is_basename_allowed(tgt_r.name):
        return False, "basename not allowlisted for operator UI"
    if require_profile_isolation:
        try:
            if mem_r.is_relative_to(project_root.resolve()):
                return False, (
                    "ADA_REQUIRE_PROFILE_ISOLATION=1: memory_dir is under project root; "
                    "edit files in your editor, not via this UI"
                )
        except (OSError, ValueError):
            pass
    return True, ""


def list_bootstrap_files(memory_dir: Path) -> list[str]:
    if not memory_dir.is_dir():
        return list(DEFAULT_BOOTSTRAP_BASENAMES)
    out: list[str] = []
    for name in DEFAULT_BOOTSTRAP_BASENAMES:
        if is_basename_allowed(name):
            out.append(name)
    return out
