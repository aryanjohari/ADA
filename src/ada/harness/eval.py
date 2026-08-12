"""Eval helpers — falsify ungrounded body claims (M02 §10.1)."""

from __future__ import annotations

import re
from typing import Any


_DISK_CLAIM = re.compile(
    r"\b(remounted|disk\s+free|gb\s+free|ada-data\s+is\s+(mounted|ok)|temp(?:erature)?\s+is\s+\d)",
    re.IGNORECASE,
)


def claims_body_metric_without_receipt(
    answer: str,
    tool_receipts: list[dict[str, Any]],
) -> bool:
    """True if answer looks like a body metric claim without a successful tool_result."""
    if not _DISK_CLAIM.search(answer or ""):
        return False
    ok_tools = {
        r.get("tool")
        for r in tool_receipts
        if r.get("ok") and r.get("tool") in {"body_vitals", "body_doctor", "body_whoami", "body_story"}
    }
    return not ok_tools
