"""Local Dream seal — checksummed package → dream/outbox (no LLM required)."""

from __future__ import annotations

import hashlib
import json
import shutil
import uuid
from pathlib import Path
from typing import Any

from ada import __version__
from ada.body.vitals import utc_now_iso
from ada.io.atomic import atomic_write_text
from ada.io.paths import BodyFault, DataPaths, ada_data_mounted, require_ada_data


def _require(paths: DataPaths | None) -> DataPaths:
    p = paths or require_ada_data()
    if not ada_data_mounted(p.root):
        raise BodyFault(
            f"ada-data not mounted or missing at {p.root}; refusing durable writes"
        )
    return p


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def seal_package(
    delta: dict[str, Any],
    *,
    paths: DataPaths | None = None,
    dream_id: str | None = None,
) -> dict[str, Any]:
    """Build staging dir → MANIFEST + checksums → promote to outbox.

    LLM manage is *not* required for seal success.
    """
    p = _require(paths)
    p.ensure_memory_dirs()
    p.ensure_dream_dirs()

    did = dream_id or f"dream-{utc_now_iso().replace(':', '').replace('-', '')}-{uuid.uuid4().hex[:8]}"
    staging = p.dream_staging / did
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)

    # Identity + prefs copies (small metal).
    files_copied: list[str] = []
    for src, name in (
        (p.identity_yaml, "identity.yaml"),
        (p.prefs_yaml, "prefs.yaml"),
        (p.open_loops_yaml, "open_loops.yaml"),
    ):
        if src.is_file():
            dest = staging / name
            shutil.copy2(src, dest)
            files_copied.append(name)

    delta_path = staging / "delta.json"
    delta_bytes = json.dumps(delta, indent=2, ensure_ascii=False).encode("utf-8")
    atomic_write_text(delta_path, delta_bytes.decode("utf-8"))
    files_copied.append("delta.json")

    # Checksums for every file in staging.
    checksums: dict[str, str] = {}
    for path in sorted(staging.rglob("*")):
        if path.is_file():
            rel = str(path.relative_to(staging))
            checksums[rel] = _sha256_file(path)

    born_at = None
    hostname = None
    if p.identity_yaml.is_file():
        try:
            import yaml

            ident = yaml.safe_load(p.identity_yaml.read_text(encoding="utf-8")) or {}
            if isinstance(ident, dict):
                born_at = ident.get("born_at")
                hostname = ident.get("body_hostname")
        except Exception:  # noqa: BLE001
            pass

    manifest = {
        "schema_version": 1,
        "dream_id": did,
        "sealed_at": utc_now_iso(),
        "agent_version": __version__,
        "hostname": hostname,
        "born_at": born_at,
        "since": delta.get("since"),
        "files": files_copied,
        "checksums": checksums,
        "package_sha256": None,  # filled after manifest without this field
    }
    # Compute package hash over sorted checksums.
    pack_src = json.dumps(checksums, sort_keys=True, separators=(",", ":")).encode("utf-8")
    manifest["package_sha256"] = _sha256_bytes(pack_src)

    manifest_path = staging / "MANIFEST.json"
    atomic_write_text(
        manifest_path, json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    )

    # Promote staging → outbox (directory move).
    outbox_dest = p.dream_outbox / did
    if outbox_dest.exists():
        shutil.rmtree(outbox_dest)
    shutil.move(str(staging), str(outbox_dest))

    return {
        "ok": True,
        "dream_id": did,
        "outbox_path": str(outbox_dest),
        "manifest": manifest,
        "package_sha256": manifest["package_sha256"],
        "sealed_at": manifest["sealed_at"],
    }
