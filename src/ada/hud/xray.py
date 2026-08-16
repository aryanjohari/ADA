"""Read-only ADA x-ray — allowlisted browse under ada-data (M13 §7.3).

Never a shell, never a write path. realpath must stay inside allowlisted roots;
deny secrets / ssh / env keys / Tailscale auth / machine-id dumps.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Literal

from ada.io.paths import get_paths

RootKey = Literal["memory", "runs", "outbox", "artifacts"]

ALLOWED_ROOTS: tuple[RootKey, ...] = ("memory", "runs", "outbox", "artifacts")

DEFAULT_MAX_BYTES = 256 * 1024
HARD_MAX_BYTES = 1024 * 1024

# Path segment / name deny (case-insensitive on the basename check).
_DENY_NAME_RE = re.compile(
    r"(^|/)("
    r"secrets|"
    r"\.ssh|"
    r"hud\.env|"
    r"gemini\.env|"
    r"id_rsa|"
    r"id_ed25519|"
    r"tailscaled\.state|"
    r"machine-id"
    r")(/|$)",
    re.IGNORECASE,
)

_DENY_SUFFIXES = (".pem", ".key")


class XrayError(Exception):
    def __init__(self, message: str, *, status: int = 404, code: str = "denied") -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code


def _root_dir(key: str) -> Path:
    if key not in ALLOWED_ROOTS:
        raise XrayError(f"unknown root {key!r}", status=404, code="bad_root")
    paths = get_paths()
    if key == "memory":
        return paths.memory.resolve()
    if key == "runs":
        return paths.runs.resolve()
    if key == "artifacts":
        return paths.artifacts.resolve()
    return paths.dream_outbox.resolve()


def _is_denied_path(path: Path) -> bool:
    try:
        resolved = path.resolve()
    except OSError:
        return True
    text = resolved.as_posix()
    if _DENY_NAME_RE.search(text):
        return True
    name = resolved.name.lower()
    if name.endswith(_DENY_SUFFIXES):
        return True
    # Refuse anything under <ada-data>/secrets even if somehow linked.
    secrets = (get_paths().root / "secrets").resolve()
    try:
        resolved.relative_to(secrets)
        return True
    except ValueError:
        pass
    ssh = Path.home().joinpath(".ssh").resolve()
    try:
        resolved.relative_to(ssh)
        return True
    except ValueError:
        pass
    return False


def resolve_under_root(root_key: str, rel: str) -> tuple[Path, Path]:
    """Return (root, target) both resolved; raise XrayError if escape/deny."""
    root = _root_dir(root_key)
    rel = (rel or "").replace("\\", "/").lstrip("/")
    if rel in ("", "."):
        target = root
    else:
        # Disallow absolute and null bytes before join.
        if rel.startswith("/") or "\x00" in rel:
            raise XrayError("invalid path", status=400, code="bad_path")
        target = (root / rel).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise XrayError("path escapes allowlisted root", status=403, code="escape") from exc
    if _is_denied_path(target):
        raise XrayError("path denied", status=403, code="denied")
    return root, target


def list_entries(root_key: str, rel: str = "") -> dict[str, Any]:
    root, target = resolve_under_root(root_key, rel)
    if not target.exists():
        raise XrayError("not found", status=404, code="missing")
    if not target.is_dir():
        raise XrayError("not a directory", status=400, code="not_dir")
    entries: list[dict[str, Any]] = []
    try:
        children = sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except OSError as exc:
        raise XrayError(str(exc), status=500, code="io") from exc
    for child in children:
        try:
            resolved = child.resolve()
        except OSError:
            continue
        try:
            resolved.relative_to(root)
        except ValueError:
            continue
        if _is_denied_path(resolved):
            continue
        st = None
        try:
            st = resolved.stat()
        except OSError:
            continue
        entries.append(
            {
                "name": child.name,
                "type": "dir" if resolved.is_dir() else "file",
                "size": None if resolved.is_dir() else st.st_size,
                "mtime": int(st.st_mtime),
            }
        )
    return {
        "root": root_key,
        "path": rel.replace("\\", "/").lstrip("/"),
        "entries": entries,
    }


def _sniff_text(sample: bytes) -> bool:
    if b"\x00" in sample:
        return False
    try:
        sample.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def read_file(root_key: str, rel: str, *, max_bytes: int = DEFAULT_MAX_BYTES) -> dict[str, Any]:
    max_bytes = max(1, min(int(max_bytes), HARD_MAX_BYTES))
    root, target = resolve_under_root(root_key, rel)
    if not target.exists():
        raise XrayError("not found", status=404, code="missing")
    if not target.is_file():
        raise XrayError("not a file", status=400, code="not_file")
    if _is_denied_path(target):
        raise XrayError("path denied", status=403, code="denied")
    try:
        size = target.stat().st_size
    except OSError as exc:
        raise XrayError(str(exc), status=500, code="io") from exc
    # Read one extra byte to detect truncation.
    try:
        with target.open("rb") as fh:
            data = fh.read(max_bytes + 1)
    except OSError as exc:
        raise XrayError(str(exc), status=500, code="io") from exc
    truncated = len(data) > max_bytes
    data = data[:max_bytes]
    if not _sniff_text(data[:4096]):
        return {
            "root": root_key,
            "path": rel.replace("\\", "/").lstrip("/"),
            "binary": True,
            "refused": True,
            "size": size,
            "message": "binary / refused",
            "content_type": "application/octet-stream",
        }
    text = data.decode("utf-8", errors="replace")
    suffix = target.suffix.lower()
    if suffix in (".md", ".markdown"):
        ctype = "text/markdown"
    elif suffix in (".yaml", ".yml"):
        ctype = "text/yaml"
    elif suffix == ".json":
        ctype = "application/json"
    elif suffix == ".jsonl":
        ctype = "application/x-ndjson"
    else:
        ctype = "text/plain"
    return {
        "root": root_key,
        "path": rel.replace("\\", "/").lstrip("/"),
        "binary": False,
        "refused": False,
        "size": size,
        "truncated": truncated,
        "max_bytes": max_bytes,
        "content_type": ctype,
        "text": text,
        "realpath": str(target),
        # Relative to allowlisted root only — never dump secrets trees.
        "root_realpath": str(root),
    }