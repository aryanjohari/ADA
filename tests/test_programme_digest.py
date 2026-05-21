"""ProgrammeDigest builder and inject policy (Phase D, no Gemini)."""

from __future__ import annotations

import json

import pytest

from ada.mission_control.inject_policy import (
    should_inject_programme_digest,
    user_message_matches_programme_intent,
)
from ada.mission_control.programme_digest import (
    PROGRAMME_DIGEST_MAX_BYTES_DEFAULT,
    build_programme_digest,
)
from ada.observability.queries import open_readonly_connection
from ada.query_engine import QueryEngine


def test_user_message_matches_programme_intent() -> None:
    assert user_message_matches_programme_intent("When does tick run?")
    assert user_message_matches_programme_intent("what does daily_brief do")
    assert not user_message_matches_programme_intent("What's 2+2?")


def test_should_inject_first_turn() -> None:
    assert should_inject_programme_digest(
        work_mode=True,
        mission_id=1,
        user_turn_count_before=0,
        user_text="hello",
    )


def test_should_inject_intent_on_later_turn() -> None:
    assert should_inject_programme_digest(
        work_mode=True,
        mission_id=1,
        user_turn_count_before=3,
        user_text="mission status please",
    )
    assert not should_inject_programme_digest(
        work_mode=True,
        mission_id=1,
        user_turn_count_before=3,
        user_text="hello again",
    )


@pytest.mark.asyncio
async def test_programme_digest_daily_brief_enqueue_goal(
    schema_sql_path, test_settings, monkeypatch
) -> None:
    monkeypatch.setenv("ADA_INJECT_PROGRAMME_DIGEST", "1")
    schedule = {
        "version": 1,
        "jobs": [
            {
                "id": "daily_brief",
                "min_interval_hours": 24,
                "action": {
                    "type": "enqueue_goal",
                    "goal_text": "Daily ops brief — run daily_brief skill",
                },
            }
        ],
    }
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        mid = await qe.create_mission(
            slug="digest-ops",
            title="Digest Ops",
            brief_md="Daily ops programme intent for digest preview.",
            schedule_hint_json=schedule,
            defaults_json={"skills_enabled": ["daily_brief"]},
        )
        conn = open_readonly_connection(test_settings.state_db_path)
        try:
            digest = build_programme_digest(conn, mid, mission_slug="digest-ops")
        finally:
            conn.close()
        jobs = digest["schedule_jobs"]
        assert len(jobs) == 1
        job = jobs[0]
        assert job["id"] == "daily_brief"
        assert job["action_type"] == "enqueue_goal"
        assert job["min_interval_hours"] == 24.0
        assert job["never_ran"] is True
        skills = digest["skills"]
        assert any(s["id"] == "daily_brief" for s in skills)
        assert "Daily ops programme intent" in digest.get("brief_md_preview", "")
        assert "description" in skills[0]
        raw = json.dumps(digest, ensure_ascii=False)
        assert len(raw.encode("utf-8")) <= PROGRAMME_DIGEST_MAX_BYTES_DEFAULT + 200
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_programme_digest_byte_cap(schema_sql_path, test_settings) -> None:
    qe = QueryEngine(test_settings.state_db_path, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        jobs = [
            {
                "id": f"j{i}",
                "min_interval_hours": 1,
                "action": {"type": "enqueue_goal", "goal_text": "x" * 200},
            }
            for i in range(30)
        ]
        mid = await qe.create_mission(
            slug="digest-cap",
            title="Cap",
            schedule_hint_json={"version": 1, "jobs": jobs},
        )
        conn = open_readonly_connection(test_settings.state_db_path)
        try:
            digest = build_programme_digest(conn, mid, max_bytes=500)
        finally:
            conn.close()
        raw = json.dumps(digest, ensure_ascii=False, separators=(",", ":"))
        assert len(raw.encode("utf-8")) <= 600
        assert digest.get("truncated") is True
    finally:
        await qe.close()
