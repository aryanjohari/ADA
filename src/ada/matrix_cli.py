"""CLI: `ada matrix-scan`."""

from __future__ import annotations

import sys
from pathlib import Path

from ada.config import Settings
from ada.publish.matrix import run_matrix_scan
from ada.query_engine import QueryEngine


async def run_matrix_scan_cli(
    settings: Settings,
    *,
    dry_run: bool,
) -> int:
    schema_path = Path(__file__).resolve().parent / "db" / "schema.sql"
    qe = QueryEngine(
        settings.state_db_path,
        schema_path,
        debounce_ms=settings.persist_debounce_ms,
    )
    await qe.connect()
    try:
        out = await run_matrix_scan(qe, settings, dry_run=dry_run)
    finally:
        await qe.close()
    print(out)
    return 0
