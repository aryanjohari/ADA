"""H6 slug-aware ProgrammeDigest inject for CHAT/PLAN surfaces."""

from __future__ import annotations

import pytest

from ada.chat_ingress import ChatSurfaceMode
from ada.mission_control.inject_policy import (
    should_inject_programme_digest_for_chat,
    slug_mentioned_in_user_text,
)
from ada.observability.queries import open_readonly_connection
from ada.query_engine import QueryEngine


def test_slug_mentioned_word_boundary() -> None:
    slugs = ["jarvis-ops", "ops"]
    assert slug_mentioned_in_user_text("check jarvis-ops status", slugs) == "jarvis-ops"
    assert slug_mentioned_in_user_text("no match here", slugs) is None


@pytest.mark.asyncio
async def test_should_inject_programme_digest_for_chat_turn_gt_zero(
    tmp_path, schema_sql_path
) -> None:
    db = tmp_path / "slug.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=1)
    await qe.connect()
    try:
        await qe.create_mission(slug="target-m", title="Target")
    finally:
        await qe.close()
    conn = open_readonly_connection(db)
    try:
        ok, slug = should_inject_programme_digest_for_chat(
            surface=ChatSurfaceMode.CHAT,
            mission_id=None,
            user_turn_count_before=1,
            user_text="What is the status of target-m?",
            conn=conn,
        )
        assert ok is True
        assert slug == "target-m"
        ok0, _ = should_inject_programme_digest_for_chat(
            surface=ChatSurfaceMode.CHAT,
            mission_id=None,
            user_turn_count_before=0,
            user_text="target-m",
            conn=conn,
        )
        assert ok0 is False
        ok_agent, _ = should_inject_programme_digest_for_chat(
            surface=ChatSurfaceMode.AGENT,
            mission_id=None,
            user_turn_count_before=1,
            user_text="target-m",
            conn=conn,
        )
        assert ok_agent is False
    finally:
        conn.close()
