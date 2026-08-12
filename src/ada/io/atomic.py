"""Crash-safe write helpers for identity (replace) and lifecycle (append).

Protocol mirrors body §6.2 / M00 §7:
  replace: tmp → fsync file → rename → fsync parent dir
  append:  write line + \\n → flush → fsync file
  recovery: truncate incomplete trailing JSONL line only
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def _fsync_dir(directory: Path) -> None:
    fd = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_write_text(path: Path, text: str, *, encoding: str = "utf-8") -> None:
    """Atomically replace *path* with *text* (tmp → fsync → rename → fsync dir)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    try:
        with open(tmp, "w", encoding=encoding) as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        _fsync_dir(path.parent)
    except Exception:
        # Never leave a promoted half-write; orphan temps are ignored on read.
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        raise


def append_jsonl_line(path: Path, obj: dict[str, Any], *, encoding: str = "utf-8") -> None:
    """Append one JSON object as a single line, then fsync the file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(obj, separators=(",", ":"), ensure_ascii=False) + "\n"
    with open(path, "a", encoding=encoding) as fh:
        fh.write(line)
        fh.flush()
        os.fsync(fh.fileno())


def recover_torn_jsonl(path: Path, *, encoding: str = "utf-8") -> bool:
    """If the last line is not valid JSON, truncate it and return True.

    Bound loss: at most the unfinished trailing line. Prior history is kept.
    Empty / missing files are no-ops.
    """
    path = Path(path)
    if not path.is_file():
        return False

    data = path.read_bytes()
    if not data:
        return False

    # Work on text lines without rewriting intact history.
    text = data.decode(encoding, errors="replace")
    # Preserve whether file ended with newline for truncation math on bytes.
    if text.endswith("\n"):
        body = text[:-1]
        lines = body.split("\n") if body else []
    else:
        # Incomplete final line (no trailing newline) — classic torn write.
        lines = text.split("\n")

    if not lines:
        return False

    last = lines[-1]
    if not last.strip():
        # Trailing blank after newline: treat as nothing useful.
        return False

    try:
        json.loads(last)
        # Last line valid. If file lacked trailing newline but parsed, leave it —
        # a complete object without \\n is unusual but readable; normalize next append.
        return False
    except json.JSONDecodeError:
        pass

    # Drop torn last line; rewrite only the good prefix.
    good = lines[:-1]
    new_text = ("\n".join(good) + "\n") if good else ""
    # Use atomic replace so a crash mid-recovery does not double-corrupt.
    atomic_write_text(path, new_text, encoding=encoding)
    return True


def cleanup_orphan_tmps(directory: Path, stem: str) -> list[Path]:
    """Delete leftover ``stem.tmp.*`` files; never promote them."""
    directory = Path(directory)
    if not directory.is_dir():
        return []
    removed: list[Path] = []
    for candidate in directory.glob(f"{stem}.tmp.*"):
        try:
            candidate.unlink()
            removed.append(candidate)
        except OSError:
            pass
    return removed
