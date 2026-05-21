from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from ada.analytics.planner import (
    GSCPlanningWindow,
    build_gsc_campaign_plan_payload,
    ctr_gap,
    opportunity_score,
    ranking_gap,
)
from ada.daemon_goal import maybe_generate_gsc_plan_for_goal
from ada.query_engine import TASK_KIND_GOAL, QueryEngine
from ada.stream_types import CompletedFunctionCall
from ada.tool_executor import StreamingToolExecutor
from ada.tools.registry import build_agent_tools, frozen_tool_declaration_names


async def _seed_rows(qe: QueryEngine) -> None:
    provider_id = await qe.ensure_analytics_provider(
        provider="gsc",
        property_ref="https://example.com/",
        config_json={"schema_version": "gsc.v1"},
    )
    snapshot_id = await qe.upsert_analytics_snapshot(
        provider_id=provider_id,
        ingest_job_id=None,
        window_start="2026-01-01",
        window_end="2026-01-31",
        request_hash="gsc-plan-seed",
        response_version="gsc.v1",
        row_count=3,
    )
    rows = [
        ("2026-01-05", "ada pricing", "https://example.com/home", 2, 1200, 0.0017, 11.0),
        ("2026-01-06", "ada pricing", "https://example.com/pricing", 8, 700, 0.0114, 8.0),
        ("2026-01-07", "ada migration", "", 0, 900, 0.0, 18.0),
    ]
    for idx, r in enumerate(rows, start=1):
        await qe.upsert_gsc_search_analytics_row(
            provider_id=provider_id,
            snapshot_id=snapshot_id,
            data_date=r[0],
            query=r[1],
            page=r[2],
            country="nz",
            device="desktop",
            clicks=float(r[3]),
            impressions=float(r[4]),
            ctr=float(r[5]),
            position=float(r[6]),
            row_hash=f"rh-{idx}",
        )
    await qe.append_action_log("test_seed_gsc_planner", {"ok": True})


def test_gsc_scoring_is_deterministic():
    assert ranking_gap(5.0) == 0.0
    assert ranking_gap(30.0) == 14.0
    assert ctr_gap(0.20) == 0.0
    assert ctr_gap(0.01) == pytest.approx(0.11)
    assert opportunity_score(impressions=1000, avg_position=10.0, ctr=0.01) == pytest.approx(
        550.0
    )


@pytest.mark.asyncio
async def test_gsc_tool_declaration_and_executor_hook():
    tool = build_agent_tools(
        allowed_exact_commands=frozenset(),
        include_memory_tools=False,
        include_plan_tools=False,
        include_gsc_read_tools=True,
    )
    assert "get_gsc_opportunities" in frozen_tool_declaration_names(tool)

    async def fake_reader(call: CompletedFunctionCall) -> dict:
        assert call.args["site"] == "https://example.com/"
        return {"top_queries": [], "quick_wins": [], "content_gaps": [], "page_fixes": []}

    ex = StreamingToolExecutor(
        allowlist_exact=frozenset(),
        max_output_bytes=1024,
        timeout_sec=5.0,
        gsc_read=fake_reader,
    )
    out = await ex.run_ordered(
        [
            CompletedFunctionCall(
                name="get_gsc_opportunities",
                args={
                    "site": "https://example.com/",
                    "start_date": "2026-01-01",
                    "end_date": "2026-01-31",
                    "limit": 10,
                },
                id="gsc1",
            )
        ]
    )
    assert "top_queries" in out[0].response


@pytest.mark.asyncio
async def test_e2e_gsc_plan_generation_populates_required_shape(tmp_path, schema_sql_path):
    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path)
    await qe.connect()
    try:
        await _seed_rows(qe)
        tid = await qe.insert_task(
            "grow organic traffic", status="pending", task_kind=TASK_KIND_GOAL
        )
        settings = SimpleNamespace(
            enable_gsc_read_tools=True,
            gsc_site_url="https://example.com/",
            gsc_plan_default_lookback_days=180,
            gsc_plan_max_items=10,
        )
        await maybe_generate_gsc_plan_for_goal(
            qe, settings=settings, task_id=tid, goal="grow organic traffic"
        )
        payload = json.loads(await qe.get_task_plan_json(tid))
        for key in (
            "campaign_goal",
            "top_opportunities",
            "proposed_pages",
            "proposed_updates",
            "priority_order",
            "approval_status",
        ):
            assert key in payload
        assert payload["approval_status"] == "pending"
        assert isinstance(payload["top_opportunities"], list)
        assert payload["top_opportunities"][0]["score"] >= 0
    finally:
        await qe.close()
