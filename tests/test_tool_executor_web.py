from __future__ import annotations

import pytest

import ada.tool_executor as tool_executor_mod
from ada.stream_types import CompletedFunctionCall
from ada.tool_executor import StreamingToolExecutor, WebToolConfig
from ada.tools import web_runtime


@pytest.mark.asyncio
async def test_web_search_not_configured():
    ex = StreamingToolExecutor(
        allowlist_exact=frozenset(),
        max_output_bytes=1024,
        timeout_sec=5.0,
    )
    r = await ex.run_ordered(
        [CompletedFunctionCall(name="web_search", args={"query": "x"}, id="1")]
    )
    assert r[0].response.get("error") == "web tools not configured"


@pytest.mark.asyncio
async def test_web_search_missing_serper_key():
    cfg = WebToolConfig(
        serper_api_key=None,
        web_search_max_results=5,
        web_search_timeout_sec=10.0,
        fetch_mode="jina",
        fetch_max_urls=2,
        fetch_max_chars=1000,
        fetch_max_bytes=50000,
        fetch_timeout_sec=10.0,
        fetch_host_allowlist=frozenset(),
        jina_reader_base_url="https://r.jina.ai/",
        jina_api_key=None,
    )
    ex = StreamingToolExecutor(
        allowlist_exact=frozenset(),
        max_output_bytes=1024,
        timeout_sec=5.0,
        web=cfg,
    )
    r = await ex.run_ordered(
        [CompletedFunctionCall(name="web_search", args={"query": "x"}, id="1")]
    )
    assert "missing Serper" in (r[0].response.get("error") or "")


@pytest.mark.asyncio
async def test_web_search_mocked(monkeypatch):
    async def fake_serper(**kwargs: object) -> dict:
        assert kwargs["query"] == "ada test"
        return {"results": [{"title": "T", "url": "https://a.com", "snippet": "S"}], "provider": "serper"}

    monkeypatch.setattr(tool_executor_mod, "serper_search", fake_serper)

    cfg = WebToolConfig(
        serper_api_key="k",
        web_search_max_results=5,
        web_search_timeout_sec=10.0,
        fetch_mode="jina",
        fetch_max_urls=2,
        fetch_max_chars=1000,
        fetch_max_bytes=50000,
        fetch_timeout_sec=10.0,
        fetch_host_allowlist=frozenset(),
        jina_reader_base_url="https://r.jina.ai/",
        jina_api_key=None,
    )
    ex = StreamingToolExecutor(
        allowlist_exact=frozenset(),
        max_output_bytes=1024,
        timeout_sec=5.0,
        web=cfg,
    )
    r = await ex.run_ordered(
        [
            CompletedFunctionCall(
                name="web_search",
                args={"query": "ada test", "num_results": 3},
                id="1",
            )
        ]
    )
    assert r[0].response["provider"] == "serper"
    assert len(r[0].response["results"]) == 1


@pytest.mark.asyncio
async def test_fetch_url_text_mocked(monkeypatch):
    async def fake_fetch(urls: list[str], **kwargs: object) -> dict:
        return {
            "pages": [
                {"url": "https://ex.org/x", "text": "hello", "truncated": False, "error": None}
            ]
        }

    monkeypatch.setattr(tool_executor_mod, "fetch_url_text_batch", fake_fetch)

    cfg = WebToolConfig(
        serper_api_key=None,
        web_search_max_results=5,
        web_search_timeout_sec=10.0,
        fetch_mode="jina",
        fetch_max_urls=2,
        fetch_max_chars=1000,
        fetch_max_bytes=50000,
        fetch_timeout_sec=10.0,
        fetch_host_allowlist=frozenset(),
        jina_reader_base_url="https://r.jina.ai/",
        jina_api_key=None,
    )
    ex = StreamingToolExecutor(
        allowlist_exact=frozenset(),
        max_output_bytes=1024,
        timeout_sec=5.0,
        web=cfg,
    )
    r = await ex.run_ordered(
        [
            CompletedFunctionCall(
                name="fetch_url_text",
                args={"urls": ["https://ex.org/x"]},
                id="1",
            )
        ]
    )
    assert r[0].response["pages"][0]["text"] == "hello"


def test_validate_https_url_blocks_localhost():
    u, err = web_runtime.validate_https_url("https://localhost/foo")
    assert u is None and err is not None


@pytest.mark.asyncio
async def test_list_session_web_sources_hook():
    async def fake_list(limit: int) -> list[dict]:
        assert limit == 10
        return [{"id": 1, "url": "https://x.com"}]

    ex = StreamingToolExecutor(
        allowlist_exact=frozenset(),
        max_output_bytes=1024,
        timeout_sec=5.0,
        web_sources_reader=fake_list,
    )
    r = await ex.run_ordered(
        [
            CompletedFunctionCall(
                name="list_session_web_sources",
                args={"limit": 10},
                id="1",
            )
        ]
    )
    assert r[0].response["count"] == 1


@pytest.mark.asyncio
async def test_list_session_web_sources_not_configured():
    ex = StreamingToolExecutor(
        allowlist_exact=frozenset(),
        max_output_bytes=1024,
        timeout_sec=5.0,
    )
    r = await ex.run_ordered(
        [
            CompletedFunctionCall(
                name="list_session_web_sources",
                args={},
                id="1",
            )
        ]
    )
    assert "not configured" in (r[0].response.get("error") or "")


def test_host_allowlist_blocks():
    u, err = web_runtime.validate_url_with_allowlist(
        "https://allowed.example/path",
        frozenset(["other.com"]),
    )
    assert err is not None
