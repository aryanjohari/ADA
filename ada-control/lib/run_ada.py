"""Run whitelisted ada argv as subprocess."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from dataclasses import dataclass


@dataclass
class AdaRunResult:
    argv: list[str]
    returncode: int
    stdout: str
    stderr: str


_MAX_CAPTURE = 256_000


def run_ada(
    argv: list[str],
    *,
    cwd: Path,
    timeout_sec: float = 120.0,
) -> AdaRunResult:
    cwd = cwd.resolve()
    env = dict(os.environ)
    try:
        proc = subprocess.run(
            argv,
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            shell=False,
            check=False,
        )
        out = proc.stdout or ""
        err = proc.stderr or ""
        if len(out) > _MAX_CAPTURE:
            out = out[:_MAX_CAPTURE] + "\n… stdout truncated …"
        if len(err) > _MAX_CAPTURE:
            err = err[:_MAX_CAPTURE] + "\n… stderr truncated …"
        return AdaRunResult(
            argv=list(argv),
            returncode=int(proc.returncode),
            stdout=out,
            stderr=err,
        )
    except subprocess.TimeoutExpired:
        return AdaRunResult(argv=list(argv), returncode=-1, stdout="", stderr="timeout")


def format_result_for_logs(r: AdaRunResult, *, max_total: int = 64_000) -> str:
    parts = [
        f"$ {' '.join(r.argv)}\nexit={r.returncode}\n--- stdout ---\n{r.stdout}",
        f"--- stderr ---\n{r.stderr}",
    ]
    s = "\n".join(parts)
    return s[:max_total] + ("\n…" if len(s) > max_total else "")
