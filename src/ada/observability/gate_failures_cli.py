"""CLI: read-only summary of failed GATE workflow steps."""

from __future__ import annotations

import json
import sys
from typing import Any

from ada.config import Settings
from ada.observability.queries import (
    gate_failed_steps_recent,
    gate_failure_buckets,
    open_readonly_connection,
)


def run_gate_failures_cli(settings: Settings, *, limit: int, publish_entity_only: bool) -> int:
    settings.ensure_data_dir()
    db_path = settings.state_db_path.resolve()
    if not db_path.is_file():
        print(f"state DB not found: {db_path}", file=sys.stderr)
        return 1
    lim = max(1, min(500, int(limit)))
    conn = open_readonly_connection(db_path)
    try:
        steps = gate_failed_steps_recent(
            conn, limit=lim, publish_entity_only=publish_entity_only
        )
        buckets = gate_failure_buckets(conn, publish_entity_only=publish_entity_only)
        out: dict[str, Any] = {
            "state_db": str(db_path),
            "threshold_env": "ADA_PUBLISH_MIN_UNIQUE_FACTS",
            "failed_gate_steps_recent": steps,
            "failure_buckets": buckets,
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0
    finally:
        conn.close()
