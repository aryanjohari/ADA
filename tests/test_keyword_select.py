from __future__ import annotations

import pytest

from ada.analytics.keyword_select import select_keyword_cluster
from ada.query_engine import QueryEngine


@pytest.mark.asyncio
async def test_keyword_select_gsc_absent_fallback(tmp_path, schema_sql_path):
    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=2)
    await qe.connect()
    try:
        # Simulate missing GSC tables in legacy DB state.
        await qe._store._conn.execute("DROP TABLE gsc_search_analytics_rows")
        await qe._store._conn.commit()
        out = await select_keyword_cluster(
            qe,
            site="https://example.com/",
            start_date="2026-01-01",
            end_date="2026-01-31",
        )
        assert out.keyword_cluster is None
        assert out.fallback_reason == "gsc_table_missing"
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_keyword_select_with_data(tmp_path, schema_sql_path):
    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=2)
    await qe.connect()
    try:
        provider_id = await qe.ensure_analytics_provider(
            provider="gsc", property_ref="https://example.com/"
        )
        snap_id = await qe.upsert_analytics_snapshot(
            provider_id=provider_id,
            ingest_job_id=None,
            window_start="2026-01-01",
            window_end="2026-01-31",
            request_hash="k1",
            response_version="gsc.v1",
            row_count=1,
        )
        await qe.upsert_gsc_search_analytics_row(
            provider_id=provider_id,
            snapshot_id=snap_id,
            data_date="2026-01-03",
            query="roof repair auckland",
            page="https://example.com/roof",
            country="nz",
            device="desktop",
            clicks=2.0,
            impressions=220.0,
            ctr=0.01,
            position=9.0,
            row_hash="rk1",
        )
        out = await select_keyword_cluster(
            qe,
            site="https://example.com/",
            start_date="2026-01-01",
            end_date="2026-01-31",
        )
        assert out.keyword_cluster == "roof repair auckland"
        assert out.fallback_reason is None
    finally:
        await qe.close()
