"""Publisher schema migrations: new columns and workflow step types."""

from __future__ import annotations

import aiosqlite
import pytest

from ada.query_engine import QueryEngine
from ada.workflow.steps import WORKFLOW_VALID_STEP_TYPES


@pytest.mark.asyncio
async def test_publisher_columns_after_connect(tmp_path, schema_sql_path):
    db = tmp_path / "a.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=2)
    await qe.connect()
    try:
        async with aiosqlite.connect(db) as conn:
            cur = await conn.execute("PRAGMA table_info(entities)")
            ecols = {str(r[1]) for r in await cur.fetchall()}
            assert "last_enriched_at" in ecols
            cur = await conn.execute("PRAGMA table_info(graph_edges)")
            gcols = {str(r[1]) for r in await cur.fetchall()}
            assert "source_url" in gcols
            cur = await conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='workflow_steps'"
            )
            row = await cur.fetchone()
            assert row and "ENRICH" in (row[0] or "")
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_workflow_valid_step_types_set():
    assert "DEPLOY" in WORKFLOW_VALID_STEP_TYPES
    assert "GATE" in WORKFLOW_VALID_STEP_TYPES
