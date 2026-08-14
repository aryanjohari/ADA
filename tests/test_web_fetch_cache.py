"""M07 fetch cache / TTL / observation cap (F4, F5, F11) — mocked HTTP."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import httpx
import pytest

from ada.io.paths import get_paths
from ada.memory.facts import ensure_prefs
from ada.web import allowlist as allowlist_mod
from ada.web import cites as cites_mod
from ada.web.fetch import OBSERVATION_CHAR_CAP, web_fetch
from ada.web.ssrf import SsrfError, assert_redirect_safe


def _seed_allowlist(host: str = "example.com") -> None:
    paths = get_paths()
    ensure_prefs(paths)
    allowlist_mod.add_host(host, paths=paths)


def _mock_response(
    *,
    status: int = 200,
    text: str = "<html><title>Hi</title><body><p>Hello world</p></body></html>",
    headers: dict[str, str] | None = None,
    url: str = "https://example.com/page",
) -> httpx.Response:
    return httpx.Response(
        status,
        text=text,
        headers=headers or {"content-type": "text/html"},
        request=httpx.Request("GET", url),
    )


def test_web_fetch_unknown_host_needs_confirm(data_root: Path) -> None:
    result = web_fetch("https://not-allowlisted.example/x")
    assert result.get("needs_confirm") is True
    assert result.get("outcome") == "needs_confirm"


def test_web_observation_truncates_huge_page(data_root: Path) -> None:
    _seed_allowlist()
    huge = "<html><body>" + ("word " * 20_000) + "</body></html>"

    def http_get(url, **kwargs):  # noqa: ANN001
        return _mock_response(text=huge, url=url), url, [url]

    result = web_fetch("https://example.com/huge", http_get=http_get)
    assert result["ok"] is True
    assert result["truncated"] is True
    total = sum(len(e) for e in result["excerpts"])
    assert total <= OBSERVATION_CHAR_CAP
    assert "html" not in result


def test_web_fetch_ttl_hit_skips_network(data_root: Path) -> None:
    _seed_allowlist()
    calls: list[str] = []

    def http_get(url, **kwargs):  # noqa: ANN001
        calls.append(url)
        return _mock_response(url=url), url, [url]

    r1 = web_fetch("https://example.com/cached", http_get=http_get)
    assert r1["ok"] and r1["cache"] == "miss"
    assert len(calls) == 1

    def boom(url, **kwargs):  # noqa: ANN001
        raise AssertionError("network should not be called on TTL hit")

    r2 = web_fetch("https://example.com/cached", http_get=boom)
    assert r2["ok"] is True
    assert r2["cache"] == "hit"
    assert r2["cite_id"] == r1["cite_id"]


def test_force_bypasses_ttl(data_root: Path) -> None:
    _seed_allowlist()
    calls = 0

    def http_get(url, **kwargs):  # noqa: ANN001
        nonlocal calls
        calls += 1
        return (
            _mock_response(text=f"<html><body>v{calls}</body></html>", url=url),
            url,
            [url],
        )

    web_fetch("https://example.com/force", http_get=http_get)
    web_fetch("https://example.com/force", force=True, http_get=http_get)
    assert calls == 2


def test_etag_304_refreshes_fetched_at(data_root: Path) -> None:
    _seed_allowlist()
    paths = get_paths()

    def http_get_200(url, **kwargs):  # noqa: ANN001
        return (
            _mock_response(
                text="<html><body>stable</body></html>",
                headers={"etag": '"abc"', "content-type": "text/html"},
                url=url,
            ),
            url,
            [url],
        )

    r1 = web_fetch("https://example.com/etag", http_get=http_get_200)
    cites_mod.update_cite_fetched_at(
        r1["cite_id"],
        fetched_at="2020-01-01T00:00:00+00:00",
        paths=paths,
    )

    def http_get_304(url, **kwargs):  # noqa: ANN001
        assert kwargs.get("headers", {}).get("If-None-Match") == '"abc"'
        return (
            httpx.Response(
                304,
                headers={"etag": '"abc"'},
                request=httpx.Request("GET", url),
            ),
            url,
            [url],
        )

    r2 = web_fetch("https://example.com/etag", http_get=http_get_304)
    assert r2["ok"] and r2["cache"] == "revalidate"
    assert r2["cite_id"] == r1["cite_id"]
    fresh = cites_mod.get_cite(r1["cite_id"], paths=paths)["cite"]
    assert fresh["fetched_at"] != "2020-01-01T00:00:00+00:00"


def test_new_hash_new_cite_version(data_root: Path) -> None:
    _seed_allowlist()
    n = 0

    def http_get(url, **kwargs):  # noqa: ANN001
        nonlocal n
        n += 1
        return (
            _mock_response(text=f"<html><body>version {n}</body></html>", url=url),
            url,
            [url],
        )

    r1 = web_fetch("https://example.com/ver", http_get=http_get)
    cites_mod.update_cite_fetched_at(
        r1["cite_id"],
        fetched_at="2020-01-01T00:00:00+00:00",
        paths=get_paths(),
    )
    r2 = web_fetch("https://example.com/ver", http_get=http_get)
    assert r1["cite_id"] != r2["cite_id"]
    assert cites_mod.get_cite(r1["cite_id"])["ok"]
    assert cites_mod.get_cite(r2["cite_id"])["ok"]


def test_redirect_to_private_denied(data_root: Path) -> None:
    _seed_allowlist()

    def http_get(url, **kwargs):  # noqa: ANN001
        raise SsrfError("SSRF: host 127.0.0.1 resolves only to blocked addresses")

    result = web_fetch("https://example.com/redir", http_get=http_get)
    assert result["ok"] is False
    assert "SSRF" in (result.get("error") or "") or "blocked" in (
        result.get("error") or ""
    )


def test_redirect_to_non_allowlisted_denied(data_root: Path) -> None:
    with patch("ada.web.ssrf.validate_resolved", return_value="93.184.216.34"):
        with pytest.raises(SsrfError, match="not allowlisted"):
            assert_redirect_safe(
                "https://evil.example/x",
                allowlisted_hosts={"example.com"},
                pasted_hosts=set(),
            )
