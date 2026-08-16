"""Local artifact writer — path-jailed under ada-data/artifacts/ (M16 Phase 0)."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from ada.body.vitals import utc_now_iso
from ada.io.atomic import atomic_write_text
from ada.io.paths import BodyFault, DataPaths, ada_data_mounted, require_ada_data
from ada.runs.append import new_receipt_id

FormatName = Literal["md", "csv"]

_SLUG_RE = re.compile(r"[^a-zA-Z0-9._-]+")
_MAX_BODY_BYTES = 512 * 1024
_ALLOWED_FORMATS = frozenset({"md", "csv"})


def _require(paths: DataPaths | None) -> DataPaths:
    p = paths or require_ada_data()
    if not ada_data_mounted(p.root):
        raise BodyFault(
            f"ada-data not mounted or missing at {p.root}; refusing artifact write"
        )
    return p


def artifacts_root(paths: DataPaths | None = None) -> Path:
    p = _require(paths)
    p.ensure_artifact_dirs()
    return p.artifacts.resolve()


def _slugify(title: str) -> str:
    raw = (title or "note").strip().lower()
    slug = _SLUG_RE.sub("-", raw).strip("-._")
    return (slug or "note")[:80]


def _resolve_under_artifacts(root: Path, rel: str) -> Path:
    rel = (rel or "").replace("\\", "/").lstrip("/")
    if not rel or rel.startswith("/") or "\x00" in rel or ".." in rel.split("/"):
        raise ValueError("invalid artifact path")
    target = (root / rel).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError("path escapes artifacts root") from exc
    return target


def list_artifacts(
    *,
    paths: DataPaths | None = None,
    limit: int = 12,
) -> list[dict[str, Any]]:
    """Last K artifacts by mtime (Phase 1 shelf)."""
    p = paths or require_ada_data()
    root = p.artifacts
    if not root.is_dir():
        return []
    files: list[Path] = []
    try:
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in {".md", ".csv", ".txt"}:
                files.append(path)
    except OSError:
        return []
    files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    out: list[dict[str, Any]] = []
    root_res = root.resolve()
    for path in files[: max(0, limit)]:
        try:
            st = path.stat()
            rel = str(path.resolve().relative_to(root_res))
        except (OSError, ValueError):
            continue
        out.append(
            {
                "path": f"artifacts/{rel}",
                "rel": rel,
                "name": path.name,
                "title": path.stem.replace("-", " "),
                "bytes": st.st_size,
                "mtime": int(st.st_mtime),
                "mtime_iso": datetime.fromtimestamp(
                    st.st_mtime, tz=timezone.utc
                ).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        )
    return out


def write_artifact(
    *,
    title: str,
    body: str,
    format: str = "md",
    source_cites: list[str] | None = None,
    overwrite: bool = False,
    confirmed: bool = False,
    relative_path: str | None = None,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    """Create/overwrite an md/csv under artifacts/. Deny path escape."""
    p = _require(paths)
    root = artifacts_root(p)
    fmt = str(format or "md").strip().lower()
    if fmt not in _ALLOWED_FORMATS:
        return {
            "ok": False,
            "outcome": "error",
            "error": f"format must be one of {sorted(_ALLOWED_FORMATS)}",
        }
    text = body if isinstance(body, str) else str(body or "")
    if not text.strip():
        return {"ok": False, "outcome": "error", "error": "body required"}
    raw_bytes = text.encode("utf-8")
    if len(raw_bytes) > _MAX_BODY_BYTES:
        return {
            "ok": False,
            "outcome": "error",
            "error": f"body exceeds {_MAX_BODY_BYTES} bytes",
        }

    if relative_path:
        rel = relative_path.replace("\\", "/").lstrip("/")
        if not rel.endswith(f".{fmt}"):
            # Allow explicit extension; otherwise append.
            if "." not in Path(rel).name:
                rel = f"{rel}.{fmt}"
    else:
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        rel = f"{day}/{_slugify(title)}.{fmt}"

    try:
        target = _resolve_under_artifacts(root, rel)
    except ValueError as exc:
        return {
            "ok": False,
            "outcome": "denied",
            "denied_reason": str(exc),
            "error": str(exc),
        }

    if target.exists() and not overwrite:
        return {
            "ok": False,
            "outcome": "error",
            "error": f"artifact exists: artifacts/{rel}; pass overwrite=true",
        }
    if target.exists() and overwrite and not confirmed:
        return {
            "ok": False,
            "needs_confirm": True,
            "outcome": "needs_confirm",
            "reason": f"overwrite artifacts/{rel} requires confirmed=true",
            "path": f"artifacts/{rel}",
        }

    cites = [str(c).strip() for c in (source_cites or []) if str(c).strip()]
    if fmt == "md" and cites:
        cite_block = "\n".join(f"- {c}" for c in cites)
        if "## Cites" not in text and "cite:" not in text[:200].lower():
            text = text.rstrip() + "\n\n## Cites\n" + cite_block + "\n"

    target.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(target, text)
    receipt_id = new_receipt_id()
    # Lightweight receipt crumb under runs/ (not a full chat session).
    try:
        day_dir = p.runs / datetime.now(timezone.utc).strftime("%Y-%m-%d")
        day_dir.mkdir(parents=True, exist_ok=True)
        crumb = day_dir / f"artifact_{receipt_id[:12]}.json"
        atomic_write_text(
            crumb,
            json.dumps(
                {
                    "receipt_id": receipt_id,
                    "ts": utc_now_iso(),
                    "tool": "artifact_write",
                    "path": f"artifacts/{rel}",
                    "bytes": len(text.encode("utf-8")),
                    "title": title,
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
        )
    except OSError:
        crumb = None

    return {
        "ok": True,
        "outcome": "ok",
        "path": f"artifacts/{rel}",
        "abspath": str(target),
        "bytes": len(text.encode("utf-8")),
        "receipt_id": receipt_id,
        "source_cites": cites,
        "receipt_crumb": str(crumb) if crumb else None,
        "title": title,
        "format": fmt,
    }
