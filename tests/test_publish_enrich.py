"""ENRICH: reference connector and store side-effects."""

from __future__ import annotations

import pytest

from ada.config import Settings
from ada.query_engine import TASK_KIND_GOAL, QueryEngine
from ada.publish.enrich import ReferenceJsonEnrichConnector, run_enrich_step


@pytest.mark.asyncio
async def test_reference_enrich_sets_edge_and_last_enriched_at(tmp_path, schema_sql_path):
    db = tmp_path / "e.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=2)
    await qe.connect()
    try:
        ent = await qe.upsert_entity(
            type="service",
            name="SVC 1",
            payload_json={
                "enrich_reference": {
                    "category_code": "policy_regulation",
                    "source_url": "https://op.test/doc",
                    "excerpt": "Stub excerpt for CI.",
                }
            },
        )
        eid = int(ent["entity_id"])
        settings = Settings.load()
        out = await run_enrich_step(qe, settings, entity_id=eid)
        assert out["graph_edge_ids"]
        assert out["last_enriched_at"]
        got = await qe.get_entity_by_id(eid)
        assert got and got.get("last_enriched_at")
        n = await qe.count_unique_local_facts(eid)
        assert n >= 1
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_enrich_connector_class_instantiation():
    c = ReferenceJsonEnrichConnector()
    assert c._TIMEOUT == 20.0
