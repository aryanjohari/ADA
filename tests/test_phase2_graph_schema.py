from __future__ import annotations

import aiosqlite
import pytest

from ada.query_engine import QueryEngine


@pytest.mark.asyncio
async def test_phase2_graph_tables_exist(tmp_path, schema_sql_path):
    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    await qe.close()

    async with aiosqlite.connect(db) as conn:
        cur = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {str(r[0]) for r in await cur.fetchall()}

    assert "entities" in tables
    assert "graph_edges" in tables
    assert "edge_evidence" in tables

