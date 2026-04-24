"""Pure helpers for ENRICH live harness post-conditions."""

from __future__ import annotations

from typing import Any


def enrich_postcondition_met(
    *,
    snap_edge_max: int,
    snap_facts: int,
    snap_seq: int,
    after_edge_max: int,
    after_facts: int,
    chain_after: list[dict[str, Any]],
) -> bool:
    """
    True if any durable graph signal occurred since the snapshot:
    new outgoing edge row for the subject, increased distinct source_url facts count,
    or a successful record_edge tool response persisted after ``snap_seq``.
    """
    if after_edge_max > snap_edge_max:
        return True
    if after_facts > snap_facts:
        return True
    for row in chain_after:
        if row.get("role") != "tool":
            continue
        seq = row.get("sequence")
        if seq is None:
            continue
        try:
            seq_i = int(seq)
        except (TypeError, ValueError):
            continue
        if seq_i <= snap_seq:
            continue
        parts = row.get("parts") or []
        if not parts or not isinstance(parts[0], dict):
            continue
        p0 = parts[0]
        if p0.get("name") != "record_edge":
            continue
        resp = p0.get("response")
        if not isinstance(resp, dict):
            continue
        if resp.get("error"):
            continue
        if resp.get("edge_id") is not None:
            return True
    return False
