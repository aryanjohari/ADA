"""Allowlisted read-only host commands — shared by tool + CLI (M12).

Fail-closed: unknown binaries, metacharacters, and free-form argv are denied.
No shell interpolation; argv list only. Prefer typed body_vitals first.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from typing import Any

# Size caps — keep tool receipts bounded.
_MAX_STDOUT = 4096
_MAX_STDERR = 1024
_DEFAULT_TIMEOUT_S = 3.0

# Characters that imply shell metachar / injection even inside argv tokens.
_FORBIDDEN_TOKEN_RE = re.compile(r"[;|&`$<>(){}\[\]\\]|\$\(")

# Exact path allowlist for df (when path args are present).
_DF_ALLOWED_PATHS = frozenset({"/", "/mnt/ada-data"})

# vcgencmd: exact second-token patterns only (no free-form).
_VCGENCMD_ALLOWED: frozenset[tuple[str, ...]] = frozenset(
    {
        ("measure_temp",),
        ("get_throttled",),
        ("measure_clock", "arm"),
    }
)

# uname: prefer subset flags only.
_UNAME_ALLOWED: frozenset[tuple[str, ...]] = frozenset(
    {
        ("-m",),
        ("-r",),
        ("-a",),
    }
)


@dataclass(frozen=True)
class ReadonlyCmdResult:
    ok: bool
    argv: list[str]
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    denied_reason: str | None = None
    error: str | None = None


def _deny(argv: list[str], reason: str) -> ReadonlyCmdResult:
    return ReadonlyCmdResult(ok=False, argv=list(argv), denied_reason=reason)


def validate_argv(argv: list[str] | tuple[str, ...]) -> str | None:
    """Return deny reason or None if argv is allowlisted."""
    if not argv:
        return "empty argv"
    tokens = [str(t) for t in argv]
    for t in tokens:
        if not t:
            return "empty token"
        if _FORBIDDEN_TOKEN_RE.search(t):
            return f"forbidden metacharacter in token: {t!r}"
        if any(c.isspace() for c in t):
            return f"whitespace in token (no shell words): {t!r}"

    binary = tokens[0]
    rest = tuple(tokens[1:])

    if binary == "nproc":
        if rest:
            return "nproc takes no arguments"
        return None

    if binary == "uname":
        if rest not in _UNAME_ALLOWED:
            return "uname only allows -m, -r, or -a"
        return None

    if binary == "vcgencmd":
        if rest not in _VCGENCMD_ALLOWED:
            return (
                "vcgencmd only allows measure_temp, get_throttled, "
                "or measure_clock arm"
            )
        return None

    if binary == "free":
        if rest not in (("-b",), ("-h",)):
            return "free only allows -b or -h"
        return None

    if binary == "df":
        return _validate_df(rest)

    return f"binary not allowlisted: {binary!r}"


def _validate_df(rest: tuple[str, ...]) -> str | None:
    if not rest:
        return None  # df with no flags — output still filtered at run time
    if rest[0] not in ("-h", "-B1"):
        return "df first arg must be -h or -B1 (or omit flags)"
    paths = rest[1:]
    for p in paths:
        if p not in _DF_ALLOWED_PATHS:
            return f"df path not allowed: {p!r} (only / and /mnt/ada-data)"
    return None


def _filter_df_stdout(stdout: str) -> str:
    """When df ran without path args, keep only allowlisted mount rows."""
    lines = stdout.splitlines()
    if not lines:
        return stdout
    kept = [lines[0]]  # header
    for line in lines[1:]:
        parts = line.split()
        if not parts:
            continue
        # Last column is usually Mounted on
        mount = parts[-1]
        if mount in _DF_ALLOWED_PATHS:
            kept.append(line)
    return "\n".join(kept)


def run_readonly_cmd(
    argv: list[str] | tuple[str, ...],
    *,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> ReadonlyCmdResult:
    """Validate then exec argv list (no shell). Fail closed on deny."""
    tokens = [str(t) for t in argv]
    reason = validate_argv(tokens)
    if reason is not None:
        return _deny(tokens, reason)

    try:
        result = subprocess.run(
            tokens,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            shell=False,
        )
    except subprocess.TimeoutExpired:
        return ReadonlyCmdResult(
            ok=False,
            argv=tokens,
            error=f"timeout after {timeout_s}s",
        )
    except OSError as exc:
        return ReadonlyCmdResult(ok=False, argv=tokens, error=str(exc))

    stdout = (result.stdout or "")[:_MAX_STDOUT]
    stderr = (result.stderr or "")[:_MAX_STDERR]
    if tokens[0] == "df" and (
        len(tokens) == 1
        or (len(tokens) == 2 and tokens[1] in ("-h", "-B1"))
    ):
        stdout = _filter_df_stdout(stdout)

    return ReadonlyCmdResult(
        ok=result.returncode == 0,
        argv=tokens,
        stdout=stdout,
        stderr=stderr,
        exit_code=result.returncode,
        error=None if result.returncode == 0 else (stderr.strip() or f"exit {result.returncode}"),
    )


def result_to_dict(result: ReadonlyCmdResult) -> dict[str, Any]:
    out: dict[str, Any] = {
        "ok": result.ok,
        "argv": result.argv,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.exit_code,
    }
    if result.denied_reason is not None:
        out["denied_reason"] = result.denied_reason
    if result.error is not None:
        out["error"] = result.error
    return out
