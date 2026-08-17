"""Runs crumbs for life capture writes (M19a)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ada.body.vitals import utc_now_iso
from ada.io.atomic import atomic_write_text
from ada.io.paths import DataPaths, get_paths
from ada.runs.append import utc_date_dir


def write_life_crumb(
    *,
    receipt_id: str,
    tool: str,
    outcome: dict[str, Any],
    paths: DataPaths | None = None,
) -> Path:
    p = paths or get_paths()
    day = utc_date_dir()
    dest = p.runs / day / f"life_{receipt_id}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "kind": "life_capture",
        "receipt_id": receipt_id,
        "tool": tool,
        "ts": utc_now_iso(),
        "outcome": outcome,
    }
    atomic_write_text(dest, json.dumps(payload, indent=2) + "\n")
    return dest
