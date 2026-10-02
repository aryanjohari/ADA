"""Append-only stage receipts. Not keys on upsert_loop."""

from __future__ import annotations

from typing import Any

import yaml

from ada.io.atomic import atomic_write_text
from ada.io.paths import DataPaths, require_ada_data
from ada.memory.campaign_page import page_path


def receipts_path(campaign_id: str, paths: DataPaths):
    page = page_path(campaign_id, paths)
    return page.with_name(f"{page.stem}.receipts.yaml")


def read_receipts(
    campaign_id: str,
    *,
    paths: DataPaths | None = None,
) -> list[dict[str, Any]]:
    p = paths or require_ada_data()
    try:
        path = receipts_path(campaign_id, p)
    except ValueError:
        return []
    if not path.is_file():
        return []
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return []
    rows = raw.get("receipts")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def append_stage_receipt(
    campaign_id: str,
    receipt: dict[str, Any],
    *,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    """Append one receipt. Does not write open_loops.yaml."""
    p = paths or require_ada_data()
    path = receipts_path(campaign_id, p)
    rows = read_receipts(campaign_id, paths=p)
    row = {
        "stage": str(receipt.get("stage") or ""),
        "campaign_id": campaign_id,
        "slug": str(receipt.get("slug") or ""),
        "outcome": str(receipt.get("outcome") or ""),
        "paths": [str(item) for item in (receipt.get("paths") or [])],
    }
    if receipt.get("sha"):
        row["sha"] = str(receipt["sha"])
    if receipt.get("checks"):
        row["checks"] = [str(item) for item in receipt["checks"]]
    if receipt.get("remove"):
        row["remove"] = [str(item) for item in receipt["remove"]]
    if receipt.get("deliver_block"):
        row["deliver_block"] = True
    rows.append(row)
    text = yaml.safe_dump(
        {"receipts": rows},
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )
    atomic_write_text(path, text)
    return row


def slug_was_pushed(slug: str, *, paths: DataPaths | None = None) -> bool:
    """True when any campaign has a push receipt for this slug."""
    text = str(slug or "").strip()
    if not text:
        return False
    root = (paths or require_ada_data()).campaign_pages
    if not root.is_dir():
        return False
    for path in root.glob("*.receipts.yaml"):
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except OSError:
            continue
        rows = raw.get("receipts") if isinstance(raw, dict) else None
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            if (
                row.get("stage") == "push"
                and row.get("outcome") == "ok"
                and str(row.get("slug") or "") == text
            ):
                return True
    return False


def latest_receipt(
    campaign_id: str,
    stage: str,
    *,
    outcome: str | None = None,
    paths: DataPaths | None = None,
) -> dict[str, Any] | None:
    found: dict[str, Any] | None = None
    for row in read_receipts(campaign_id, paths=paths):
        if row.get("stage") != stage:
            continue
        if outcome is not None and row.get("outcome") != outcome:
            continue
        found = row
    return found
