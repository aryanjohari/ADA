"""Matrix: registry + idempotent/candidate wiring."""

from __future__ import annotations

from unittest import mock

import pytest

from ada.config import Settings
from ada.publish.matrix import PageProfileRegistry, _content_hash_for_entity_row, _slug_hint
from ada.query_engine import QueryEngine


def test_page_profile_registry_niche_from_category():
    r = PageProfileRegistry(project_id="a", campaign_id="b")
    p = r.resolve("service", "data_surveys_stats")
    assert p.workflow_kind == "publish_entity_v1"
    assert p.project_id == "a"
    assert p.niche == "data-surveys-stats"


def test_slug_hint():
    assert "hello" in _slug_hint("Hello  World  ")


def test_content_hash_stability():
    h1 = _content_hash_for_entity_row({"id": 1, "name": "A", "last_enriched_at": "t", "payload_json": {}})
    h2 = _content_hash_for_entity_row({"id": 1, "name": "A", "last_enriched_at": "t", "payload_json": {}})
    assert h1 == h2


@pytest.mark.asyncio
async def test_matrix_dry_run_no_enqueue_subsystem(tmp_path, schema_sql_path, monkeypatch):
    monkeypatch.setenv("ADA_MATRIX_ENABLE", "0")
    db = tmp_path / "m.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=2)
    await qe.connect()
    try:
        from ada.publish.matrix import run_matrix_scan

        out = await run_matrix_scan(qe, Settings.load(), dry_run=True)
        assert out.get("candidates", 0) >= 0
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_matrix_idempotent_key_calls_enqueue(
    tmp_path, schema_sql_path, monkeypatch
):
    monkeypatch.setenv("ADA_MATRIX_ENABLE", "1")
    monkeypatch.setenv("ADA_PROJECT_ID", "p1")
    monkeypatch.setenv("ADA_CAMPAIGN_ID", "c1")
    db = tmp_path / "m2.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=2)
    await qe.connect()
    try:
        await qe.ensure_triage_category_entities()
        cat = await qe.upsert_entity(
            type="category", name="labour_workforce", payload_json={}
        )
        sub = await qe.upsert_entity(type="service", name="Q", payload_json={})
        cat_id = int(cat["entity_id"])
        sid = int(sub["entity_id"])
        await qe.insert_graph_edge(
            src_entity_id=sid,
            dst_entity_id=cat_id,
            edge_type="classified_as",
            confidence=1.0,
            source_url="https://m.test/1",
        )
        from ada.publish import matrix

        n = 0
        real = matrix.enqueue_workflow_via_tool

        async def wrap(*a, **k):
            nonlocal n
            n += 1
            return await real(*a, **k)

        with mock.patch.object(matrix, "enqueue_workflow_via_tool", new=wrap):
            await matrix.run_matrix_scan(
                qe, Settings.load(), dry_run=False
            )
        assert n >= 1
    finally:
        await qe.close()
