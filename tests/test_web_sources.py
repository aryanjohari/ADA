from __future__ import annotations

from pathlib import Path

import aiosqlite
import pytest

from ada.query_engine import QueryEngine, TASK_KIND_CHAT
from ada.web_persistence import (
    MAX_EXCERPT_CHARS,
    MAX_URL_CHARS,
    content_sha256_hex,
    rows_for_web_tool,
)


def test_rows_web_search_skips_error():
    assert (
        rows_for_web_tool(
            "web_search",
            {"query": "q"},
            {"error": "x", "results": [{"url": "https://a.com", "snippet": "s"}]},
        )
        == []
    )


def test_rows_web_search_per_hit():
    rows = rows_for_web_tool(
        "web_search",
        {"query": "ada harness"},
        {
            "results": [
                {"title": "T", "url": "https://ex.org/p", "snippet": "snippet text"},
            ],
            "provider": "serper",
        },
    )
    assert len(rows) == 1
    url, kind, q, excerpt, sha = rows[0]
    assert kind == "search_hit"
    assert url == "https://ex.org/p"
    assert q == "ada harness"
    assert excerpt == "snippet text"
    assert sha == content_sha256_hex("search_hit", url, excerpt)


def test_rows_fetch_skips_page_error():
    rows = rows_for_web_tool(
        "fetch_url_text",
        {"urls": ["https://a.com"]},
        {
            "pages": [
                {
                    "url": "https://a.com",
                    "text": "",
                    "error": "blocked",
                }
            ]
        },
    )
    assert rows == []


def test_rows_fetch_success():
    rows = rows_for_web_tool(
        "fetch_url_text",
        {"urls": ["https://a.com"]},
        {"pages": [{"url": "https://a.com", "text": "body", "truncated": False}]},
    )
    assert len(rows) == 1
    assert rows[0][1] == "page_fetch"
    assert rows[0][3] == "body"
    assert rows[0][2] is None


def test_truncation_constants():
    long_url = "https://x.com/" + "a" * MAX_URL_CHARS
    rows = rows_for_web_tool(
        "web_search",
        {"query": "q"},
        {"results": [{"url": long_url, "snippet": "s"}]},
    )
    assert len(rows[0][0]) <= MAX_URL_CHARS
    long_ex = "z" * (MAX_EXCERPT_CHARS + 10)
    rows2 = rows_for_web_tool(
        "fetch_url_text",
        {},
        {"pages": [{"url": "https://z.com", "text": long_ex}]},
    )
    assert len(rows2[0][3]) <= MAX_EXCERPT_CHARS


@pytest.mark.asyncio
async def test_migration_adds_web_sources_table(tmp_path):
    legacy = Path(__file__).resolve().parent / "fixtures" / "schema_legacy_no_web_sources.sql"
    db = tmp_path / "legacy.db"
    qe = QueryEngine(db, legacy, debounce_ms=5)
    await qe.connect()
    try:
        async with aiosqlite.connect(db) as raw:
            cur = await raw.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='web_sources'"
            )
            assert await cur.fetchone() is not None
            cur2 = await raw.execute("PRAGMA table_info(web_sources)")
            cols = {str(r[1]) for r in await cur2.fetchall()}
            assert "content_sha256" in cols
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_record_and_list_web_sources_roundtrip(tmp_path, schema_sql_path):
    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        tid = await qe.insert_task("t", status="executing", task_kind=TASK_KIND_CHAT)
        await qe.record_web_tool_artifacts(
            tid,
            "web_search",
            {"query": "q1"},
            {
                "results": [
                    {"url": "https://a.org", "snippet": "one"},
                    {"url": "https://b.org", "snippet": "two"},
                ]
            },
        )
        await qe.record_web_tool_artifacts(
            tid,
            "fetch_url_text",
            {"urls": ["https://c.org"]},
            {"pages": [{"url": "https://c.org", "text": "full"}]},
        )
        rows = await qe.list_web_sources(tid, limit=10)
        assert len(rows) == 3
        kinds = {r["source_kind"] for r in rows}
        assert kinds == {"search_hit", "page_fetch"}
        urls = {r["url"] for r in rows}
        assert "https://a.org" in urls
        assert "https://c.org" in urls
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_non_web_tool_noops(tmp_path, schema_sql_path):
    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        tid = await qe.insert_task("t", status="executing", task_kind=TASK_KIND_CHAT)
        await qe.record_web_tool_artifacts(
            tid,
            "read_task_plan",
            {},
            {"plan_json": "{}"},
        )
        assert await qe.list_web_sources(tid) == []
    finally:
        await qe.close()
