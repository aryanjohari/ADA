"""Profile digest builder for Entity ingress."""

from __future__ import annotations

import json

import pytest

from ada.mission_control.profile_digest import (
    PROFILE_DIGEST_MAX_BYTES_DEFAULT,
    build_profile_digest,
)
from ada.observability.queries import open_readonly_connection
from ada.query_engine import QueryEngine


@pytest.mark.asyncio
async def test_profile_digest_size_cap(tmp_path, schema_sql_path) -> None:
    db = tmp_path / "prof.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        for i in range(15):
            await qe.create_mission(slug=f"m-{i}", title=f"M {i}")
    finally:
        await qe.close()
    conn = open_readonly_connection(db)
    try:
        digest = build_profile_digest(conn, max_bytes=800)
    finally:
        conn.close()
    raw = json.dumps(digest, ensure_ascii=False)
    assert len(raw.encode("utf-8")) <= PROFILE_DIGEST_MAX_BYTES_DEFAULT + 200


@pytest.mark.asyncio
async def test_profile_digest_no_defaults_json(tmp_path, schema_sql_path) -> None:
    db = tmp_path / "prof2.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        await qe.create_mission(
            slug="rss-m",
            title="RSS",
            defaults_json='{"rss_feeds": ["https://example.com/feed"]}',
        )
    finally:
        await qe.close()
    conn = open_readonly_connection(db)
    try:
        digest = build_profile_digest(conn)
    finally:
        conn.close()
    blob = json.dumps(digest)
    assert "defaults_json" not in blob
    assert "rss_feeds" not in blob
    assert "missions" in digest
