"""Mission-over-env for tick/matrix programme keys (Phase A A10)."""

from __future__ import annotations

import pytest

from ada.mission_defaults_resolve import overlay_tick_merged, resolve_programme_str


def test_mission_wins_over_env_gsc_site() -> None:
    assert (
        resolve_programme_str(
            mission_defaults={"gsc_site_url": "https://mission.example/"},
            key="gsc_site_url",
            env_value="https://env.example/",
        )
        == "https://mission.example/"
    )


def test_env_fallback_when_mission_empty() -> None:
    assert (
        resolve_programme_str(
            mission_defaults={},
            key="gsc_site_url",
            env_value="https://env.example/",
        )
        == "https://env.example/"
    )


def test_effective_triage_cap_mission_over_env() -> None:
    from ada.mission_defaults_resolve import effective_triage_lead_daily_cap

    assert (
        effective_triage_lead_daily_cap(
            mission_defaults={"triage_lead_daily_cap": 99},
            env_cap=10,
        )
        == 99
    )


def test_overlay_tick_merged() -> None:
    merged = overlay_tick_merged(
        {"type": "gsc_keyword_publish"},
        {"gsc_site_url": "https://m.example/"},
        gsc_site_url_env="https://e.example/",
    )
    assert merged["gsc_site_url"] == "https://m.example/"


@pytest.mark.asyncio
async def test_resolve_matrix_isr_ids_mission_over_env(
    tmp_path, schema_sql_path, monkeypatch
) -> None:
    monkeypatch.setenv("ADA_PROJECT_ID", "env-proj")
    monkeypatch.setenv("ADA_CAMPAIGN_ID", "env-camp")
    from ada.publish.matrix import resolve_matrix_isr_ids
    from ada.query_engine import QueryEngine

    db = tmp_path / "matrix_isr.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        await qe.create_mission(
            slug="ada_ops",
            title="Ops",
            defaults_json={
                "project_id": "mission-proj",
                "campaign_id": "mission-camp",
            },
        )
        pid, cid = await resolve_matrix_isr_ids(qe, "ada_ops")
        assert pid == "mission-proj"
        assert cid == "mission-camp"
    finally:
        await qe.close()
