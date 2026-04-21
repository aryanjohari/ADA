"""Phase 1: RSS allowlist, oversized body, keywords/GETS ingest_raw, gov allowlist."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import httpx
import pytest

from ada.ingest.gets import ingest_gets_index, parse_gets_index_html
from ada.ingest.keywords import ingest_keywords_batch
from ada.ingest.rss import ingest_rss_feeds
from ada.query_engine import QueryEngine

FIXTURE_XML = (
    Path(__file__).resolve().parent / "fixtures" / "sample_rss.xml"
).read_text(encoding="utf-8")

GETS_HTML = """
<html><body>
<table>
<tr><td><a href="/NZBS/ExternalTenderDetails.htm?id=12345">Test tender title</a></td></tr>
</table>
</body></html>
"""


def _settings_rss(**kwargs):
    base = dict(
        knowledge_feed_host_allowlist=frozenset({"example.com"}),
        ingest_gatekeeper=False,
        gemini_api_key="",
        ingest_gate_model="gemini-2.5-flash-lite",
        ingest_gate_max_output_tokens=None,
        knowledge_default_retention_days=None,
        enable_knowledge_embeddings=False,
        knowledge_embedding_model="m",
        knowledge_embedding_dim=768,
        ingest_rss_max_feeds=None,
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


@pytest.mark.asyncio
async def test_rss_allowlist_denies_bad_host(tmp_path, schema_sql_path):
    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        await qe.insert_knowledge_source(
            "rss", label="Bad", base_url="https://evil.example/notfeed.xml"
        )
        settings = _settings_rss(knowledge_feed_host_allowlist=frozenset({"example.com"}))

        async def fake_fetch(url: str) -> str:
            return FIXTURE_XML

        res = await ingest_rss_feeds(
            qe,
            settings=settings,
            max_items_per_feed=10,
            fetch_text=fake_fetch,
        )
        assert res.feeds_ok == 0
        assert res.errors
        assert "allowlist" in res.errors[0].lower()
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_rss_oversized_body_fetch_text(tmp_path, schema_sql_path):
    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        await qe.insert_knowledge_source(
            "rss", label="T", base_url="https://example.com/feed.xml"
        )
        settings = _settings_rss()

        async def huge(_url: str) -> str:
            return "x" * 5000

        res = await ingest_rss_feeds(
            qe,
            settings=settings,
            max_items_per_feed=10,
            max_response_bytes=100,
            fetch_text=huge,
        )
        assert res.feeds_ok == 0
        assert any("max_response_bytes" in e for e in res.errors)
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_parse_gets_index_html():
    rows = parse_gets_index_html(GETS_HTML)
    assert len(rows) == 1
    assert rows[0]["rfx_id"] == "12345"
    assert "Test tender" in rows[0]["title"]


@pytest.mark.asyncio
async def test_ingest_keywords_mock_httpx(tmp_path, schema_sql_path):
    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        settings = SimpleNamespace(
            ada_keyword_terms="a,b",
            ada_keyword_max_terms_per_run=100,
            ada_keyword_language_code="en",
            ada_keyword_location_code=2004,
            ada_dataforseo_use_live=True,
            dataforseo_login="u",
            dataforseo_password="p",
            gov_api_host_allowlist=frozenset({"api.dataforseo.com"}),
            persist_debounce_ms=5,
        )
        mock_json = '{"status_code":20000,"tasks":[{"result":[{"keyword":"a","search_volume":1}]}]}'

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text=mock_json)

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            res = await ingest_keywords_batch(
                qe,
                settings,
                keywords=["hello", "world"],
                http_client=client,
                idempotency_key="kw-test-1",
            )
        assert res.error == ""
        assert res.terms_submitted == 2
        assert res.raw_row_id > 0
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_ingest_keywords_requires_gov_allowlist(tmp_path, schema_sql_path):
    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        settings = SimpleNamespace(
            ada_keyword_terms="a",
            ada_keyword_max_terms_per_run=10,
            ada_keyword_language_code="en",
            ada_keyword_location_code=2004,
            ada_dataforseo_use_live=True,
            dataforseo_login="u",
            dataforseo_password="p",
            gov_api_host_allowlist=frozenset(),
            persist_debounce_ms=5,
        )
        res = await ingest_keywords_batch(qe, settings, keywords=["x"])
        assert res.error
        assert "ADA_GOV_API_HOST_ALLOWLIST" in res.error
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_ingest_gets_mock_fetch(tmp_path, schema_sql_path):
    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=5)
    await qe.connect()
    try:
        settings = SimpleNamespace(
            ada_gets_poll_url="https://www.gets.govt.nz/ExternalIndex.htm",
            gov_api_host_allowlist=frozenset({"www.gets.govt.nz", "gets.govt.nz"}),
            ingest_rss_timeout_sec=45.0,
            ingest_rss_max_response_bytes=2_000_000,
            persist_debounce_ms=5,
        )

        async def fake_fetch(_url: str) -> str:
            return GETS_HTML

        res = await ingest_gets_index(
            qe, settings, fetch_text=fake_fetch, idempotency_key="gets-test-1"
        )
        assert not res.error
        assert res.items_inserted == 1
        assert res.tenders_parsed == 1
    finally:
        await qe.close()
