"""H6 ProfileDigest enrichment: pack, skills_enforcement, brief_md_preview."""

from __future__ import annotations

import json

import pytest

from ada.mission_control.profile_digest import build_profile_digest
from ada.observability.queries import open_readonly_connection
from ada.query_engine import QueryEngine


@pytest.mark.asyncio
async def test_profile_digest_h6_mission_fields(tmp_path, schema_sql_path) -> None:
    db = tmp_path / "h6.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        await qe.create_mission(
            slug="h6-enriched",
            title="H6 Mission",
            defaults_json=json.dumps(
                {
                    "pack": "core-ops",
                    "skills_enabled": ["daily_brief", "mission_tick_dry_run"],
                }
            ),
            brief_md="Programme intent for concierge index preview field.",
        )
    finally:
        await qe.close()
    conn = open_readonly_connection(db)
    try:
        digest = build_profile_digest(conn)
    finally:
        conn.close()
    missions = digest.get("missions") or []
    assert len(missions) >= 1
    row = next(m for m in missions if m.get("slug") == "h6-enriched")
    assert row["pack"] == "core-ops"
    assert row["skills_enforcement"] is True
    assert "Programme intent" in row["brief_md_preview"]
    blob = json.dumps(digest)
    assert "defaults_json" not in blob


@pytest.mark.asyncio
async def test_profile_digest_h6_trim_drops_previews(tmp_path, schema_sql_path) -> None:
    from ada.mission_control.profile_digest import _digest_byte_size

    db = tmp_path / "h6trim.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        for i in range(12):
            await qe.create_mission(
                slug=f"trim-{i}",
                title=f"Trim {i}",
                brief_md="x" * 120,
                defaults_json='{"pack": "core-ops", "skills_enabled": ["daily_brief"]}',
            )
    finally:
        await qe.close()
    max_bytes = 400
    conn = open_readonly_connection(db)
    try:
        digest = build_profile_digest(conn, max_bytes=max_bytes)
    finally:
        conn.close()
    assert _digest_byte_size(digest) <= max_bytes
    assert digest.get("truncated") is True
    missions = digest.get("missions") or []
    assert any(not m.get("brief_md_preview") for m in missions) or len(missions) < 12
