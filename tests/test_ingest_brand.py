from __future__ import annotations

from types import SimpleNamespace

import pytest

from ada.ingest.brand import ingest_brand_site
from ada.query_engine import QueryEngine


def _settings() -> SimpleNamespace:
    return SimpleNamespace(
        brand_ingest_max_urls=4,
        brand_ingest_timeout_sec=10.0,
        brand_ingest_max_response_bytes=1_000_000,
    )


@pytest.mark.asyncio
async def test_ingest_brand_happy_path_and_dedupe(tmp_path, schema_sql_path):
    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=2)
    await qe.connect()
    try:
        pages = {
            "https://example.com/": '<html><a href="/services">Services</a></html>',
            "https://example.com/services": "<html><h1>Roofing Service</h1></html>",
        }

        async def fake_fetch(url: str) -> str:
            return pages[url]

        r1 = await ingest_brand_site(
            qe,
            _settings(),
            site_url="https://example.com/",
            max_urls=3,
            fetch_text=fake_fetch,
        )
        r2 = await ingest_brand_site(
            qe,
            _settings(),
            site_url="https://example.com/",
            max_urls=3,
            fetch_text=fake_fetch,
        )
        assert r1.items_inserted >= 1
        assert r2.items_deduped >= 1
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_ingest_brand_dry_run_no_writes(tmp_path, schema_sql_path):
    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=2)
    await qe.connect()
    try:
        async def fake_fetch(_url: str) -> str:
            return "<html><body>Brand homepage</body></html>"

        res = await ingest_brand_site(
            qe,
            _settings(),
            site_url="https://example.com/",
            max_urls=2,
            dry_run=True,
            fetch_text=fake_fetch,
        )
        rows = await qe.list_knowledge_items(limit=20)
        assert res.pages_fetched >= 1
        assert rows == []
    finally:
        await qe.close()


@pytest.mark.asyncio
async def test_ingest_brand_invalid_url(tmp_path, schema_sql_path):
    db = tmp_path / "s.db"
    qe = QueryEngine(db, schema_sql_path, debounce_ms=2)
    await qe.connect()
    try:
        with pytest.raises(ValueError, match="site_url must be http"):
            await ingest_brand_site(
                qe, _settings(), site_url="ftp://bad", max_urls=2, dry_run=True
            )
    finally:
        await qe.close()
