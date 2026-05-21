"""mission_tick helpers and ada mission tick behavior."""

from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone

UTC = timezone.utc

import pytest

from ada.config import Settings
from ada.mission_tick import (
    job_due,
    merge_action_defaults,
    parse_last_run_iso,
    parse_tick_schedule_v1,
    run_mission_tick,
    tick_state_key,
    utc_now,
)
from ada.query_engine import QueryEngine


def test_tick_state_key():
    assert tick_state_key("ab", "q") == "mission.tick.ab.q"


def test_parse_last_run_iso_z():
    dt = parse_last_run_iso("2026-05-01T12:00:00Z")
    assert dt is not None
    assert dt.tzinfo is not None


def test_job_due_force():
    past = datetime(2020, 1, 1, tzinfo=UTC)
    now = datetime(2026, 1, 1, tzinfo=UTC)
    assert job_due(now, past, 9999.0, force=True) is True


def test_job_due_interval():
    now = utc_now()
    last = now - timedelta(hours=2)
    assert job_due(now, last, 1.0, force=False) is True
    assert job_due(now, last, 24.0, force=False) is False


def test_merge_action_defaults():
    m = merge_action_defaults(
        {"a": 1, "gsc_site_url": "x"},
        {"type": "gsc_keyword_publish", "ingest_days": 7},
    )
    assert m["type"] == "gsc_keyword_publish"
    assert m["a"] == 1
    assert m["ingest_days"] == 7
    assert m["gsc_site_url"] == "x"


def test_parse_tick_schedule_v1_ok():
    jobs, err = parse_tick_schedule_v1({"version": 1, "jobs": [{"id": "j1", "action": {}}]})
    assert err == ""
    assert jobs == [{"id": "j1", "action": {}}]


def test_parse_tick_schedule_v1_bad_version():
    jobs, err = parse_tick_schedule_v1({"version": 2})
    assert jobs is None
    assert "unsupported" in err


@pytest.mark.asyncio
async def test_mission_tick_dry_run_no_state_write(tmp_path, schema_sql_path, monkeypatch):
    monkeypatch.setenv("ADA_DATA_DIR", str(tmp_path))
    hint = json.dumps(
        {
            "version": 1,
            "jobs": [
                {"id": "kw", "min_interval_hours": 0, "action": {"type": "unknown_x"}}
            ],
        }
    )

    db = tmp_path / "state.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=2)
    await qe.connect()
    try:
        await qe.create_mission(
            "ms-tick",
            "T",
            schedule_hint_json=json.loads(hint),
        )
        k = tick_state_key("ms-tick", "kw")
        assert await qe.state_get(k) is None

        rc = await run_mission_tick(
            qe,
            Settings.load(),
            mission_slug="ms-tick",
            dry_run=False,
            force=True,
        )
        assert rc == 1

        await qe.state_set(k, "2020-01-01T00:00:00Z")
        rv = await run_mission_tick(
            qe,
            Settings.load(),
            mission_slug="ms-tick",
            dry_run=True,
            force=True,
        )
        assert rv == 1
        assert await qe.state_get(k) == "2020-01-01T00:00:00Z"
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_mission_tick_unknown_mission(tmp_path, schema_sql_path, monkeypatch):
    monkeypatch.setenv("ADA_DATA_DIR", str(tmp_path))
    qe = QueryEngine(tmp_path / "state.db", schema_sql_path, debounce_ms=2)
    await qe.connect()
    try:
        rc = await run_mission_tick(
            qe, Settings.load(), mission_slug="nope", dry_run=True, force=True
        )
        assert rc == 2
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_mission_tick_gsc_enqueues_system_job(
    tmp_path, schema_sql_path, monkeypatch
):
    """GSC tick enqueues ``tick.gsc_keyword_publish``; tick state bumps in the worker."""
    monkeypatch.setenv("ADA_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ADA_ENABLE_GSC_INGEST", "1")
    monkeypatch.setenv("GSC_SITE_URL", "https://example.com/")
    qe = QueryEngine(tmp_path / "state.db", schema_sql_path, debounce_ms=2)
    await qe.connect()
    try:
        await qe.create_mission(
            "ms-kw",
            "K",
            defaults_json=json.dumps(
                {
                    "gsc_site_url": "https://sc-domain:example.test",
                    "project_id": "p",
                    "campaign_id": "c",
                    "niche": "n",
                    "keyword_start_date": "2026-01-01",
                    "keyword_end_date": "2026-05-06",
                    "ingest_days": 2,
                    "dimensions": "date,query",
                    "row_limit": 5,
                }
            ),
            schedule_hint_json={
                "version": 1,
                "jobs": [
                    {
                        "id": "g1",
                        "min_interval_hours": 0,
                        "action": {"type": "gsc_keyword_publish"},
                    }
                ],
            },
        )
        mrow = await qe.get_mission_by_slug("ms-kw")
        assert mrow is not None
        mid = int(mrow["id"])

        rc = await run_mission_tick(
            qe,
            Settings.load(),
            mission_slug="ms-kw",
            dry_run=False,
            force=True,
        )
        assert rc == 0

        key = tick_state_key("ms-kw", "g1")
        assert await qe.state_get(key) is None

        jobs = await qe.list_system_jobs(
            mission_id=mid, kind="tick.gsc_keyword_publish", limit=5
        )
        assert len(jobs) == 1
        assert jobs[0]["status"] == "pending"
        payload = jobs[0].get("payload_json") or {}
        assert payload.get("tick_state_key") == key
        assert payload.get("mission_slug") == "ms-kw"
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_mission_cli_init_defaults_json_roundtrip(tmp_path, schema_sql_path, monkeypatch):
    from ada.mission_cli import async_main as mission_async_main

    monkeypatch.setenv("ADA_DATA_DIR", str(tmp_path))
    dj = json.dumps({"project_id": "px"})
    assert (
        await mission_async_main(
            [
                "init",
                "mjson",
                "--title",
                "J",
                "--defaults-json",
                dj,
            ]
        )
        == 0
    )

    s = io.StringIO()
    with redirect_stdout(s):
        assert await mission_async_main(["show", "mjson"]) == 0
    out = s.getvalue()
    assert '"project_id": "px"' in out
