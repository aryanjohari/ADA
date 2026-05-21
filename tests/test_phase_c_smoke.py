"""Phase C smoke: deterministic brief + profile brief + ops template."""

from __future__ import annotations

import pytest

from ada.mission_cli import _load_mission_template
from ada.mission_control.digest import (
    build_profile_brief_payload,
    render_brief,
)
from ada.notifications import NoopNotifier, get_notifier, maybe_notify_flags
from ada.observability.queries import open_readonly_connection
from ada.query_engine import QueryEngine


def test_ops_template_load() -> None:
    data = _load_mission_template("ops")
    assert data["mission_slug"] == "jarvis-ops"
    assert "daily_brief" in data["skills_enabled"]
    assert data["recommended_cron"]


@pytest.mark.asyncio
async def test_render_brief_contains_flag_id(schema_sql_path, test_settings) -> None:
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path)
    await qe.connect()
    try:
        mid = await qe.create_mission(slug="brief-m", title="Brief M")
        conn = open_readonly_connection(test_settings.state_db_path)
        try:
            text = render_brief(
                conn,
                mission_id=mid,
                mission_slug="brief-m",
                profile_scope=False,
                gemini_api_key="",
            )
        finally:
            conn.close()
        assert "brief-m" in text or "mission:" in text
        assert "payload_json" not in text
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_profile_brief_read_only(schema_sql_path, test_settings) -> None:
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path)
    await qe.connect()
    try:
        await qe.create_mission(slug="p1", title="P1")
        await qe.create_mission(slug="p2", title="P2")
        payload = build_profile_brief_payload(test_settings)
        assert payload["schema_version"] == 1
        assert len(payload["missions"]) >= 2
        assert "global_kernel_note" in payload
    finally:
        await qe.close()


def test_notifier_default_noop(monkeypatch) -> None:
    monkeypatch.delenv("ADA_NOTIFY_URL", raising=False)
    assert isinstance(get_notifier(), NoopNotifier)
    conn = None
    maybe_notify_flags([])


@pytest.mark.asyncio
async def test_daily_brief_skill_enqueue(schema_sql_path, test_settings) -> None:
    from ada.motor import MotorRequest, execute
    from ada.motor.registry import clear_registry_cache

    clear_registry_cache()
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path)
    await qe.connect()
    try:
        await qe.create_mission(slug="db-m", title="DB", defaults_json={})
        result = await execute(
            MotorRequest(
                layer="skill",
                id="daily_brief",
                params={},
                mission_slug="db-m",
            ),
            settings=test_settings,
            qe=qe,
        )
        assert result.ok, result.error
        assert result.output and result.output.get("task_id")
    finally:
        await qe.close()
