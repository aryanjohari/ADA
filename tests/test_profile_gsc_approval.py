from __future__ import annotations

from datetime import date
import pytest

from ada.ingest.gsc_models import GSCQueryRequest
from ada.query_engine import QueryEngine
from ada.workflow.enqueue import enqueue_workflow_via_tool


@pytest.mark.asyncio
async def test_profile_identity_guard_mismatch(tmp_path, schema_sql_path):
    db = tmp_path / "state.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=2)
    await qe.connect()
    try:
        await qe.ensure_profile_identity(
            profile_id="client_a",
            profile_data_root="/tmp/profiles",
            profile_fingerprint="abc123",
        )
        with pytest.raises(ValueError, match="profile mismatch"):
            await qe.ensure_profile_identity(
                profile_id="client_b",
                profile_data_root="/tmp/profiles",
                profile_fingerprint="zzz999",
            )
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_enqueue_requires_approval(tmp_path, schema_sql_path):
    db = tmp_path / "state.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=2)
    await qe.connect()
    try:
        out = await enqueue_workflow_via_tool(
            qe,
            kind="publish_entity_v1",
            goal_text="Publish entity 1",
            params_json='{"entity_id":1,"project_id":"p","campaign_id":"c","niche":"n"}',
            idempotency_key="publish:1:abc",
            max_steps=10,
            require_approval=True,
        )
        assert "error" in out
        assert out["artifact_type"] == "workflow_enqueue"

        await qe.upsert_approval_record(
            artifact_type="workflow_enqueue",
            artifact_ref="publish:1:abc",
            status="approved",
            approved_by="tester",
            set_decided=True,
        )
        out2 = await enqueue_workflow_via_tool(
            qe,
            kind="publish_entity_v1",
            goal_text="Publish entity 1",
            params_json='{"entity_id":1,"project_id":"p","campaign_id":"c","niche":"n"}',
            idempotency_key="publish:1:abc",
            max_steps=10,
            require_approval=True,
        )
        assert out2.get("error") is None
        assert out2["created_new"] is True
    finally:
        await qe.close()


def test_gsc_query_request_dimensions_validation():
    req = GSCQueryRequest(
        site_url="https://example.com/",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 7),
        dimensions=["date", "query"],
        row_limit=100,
    )
    assert req.dimensions == ["date", "query"]
    with pytest.raises(ValueError):
        GSCQueryRequest(
            site_url="https://example.com/",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 7),
            dimensions=["date", "foo"],
            row_limit=100,
        )
