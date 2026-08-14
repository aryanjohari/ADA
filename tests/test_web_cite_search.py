"""M07 web_cite_search — local library discovery without cite_id (F13)."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from ada.cli.main import app
from ada.cortex.charter import WEB_CONTRACT, build_system_charter
from ada.io.paths import get_paths
from ada.tools.gateway import Gateway
from ada.tools.schemas import TOOL_NAMES
from ada.web import cites as cites_mod
from ada.web.fetch import web_cite_get, web_cite_search


def _seed_cite(title: str = "ReAct: Synergizing Reasoning and Acting in Language Models") -> str:
    paths = get_paths()
    cite = cites_mod.write_cite(
        url="https://arxiv.org/abs/2210.03629",
        final_url="https://arxiv.org/abs/2210.03629",
        status=200,
        etag=None,
        last_modified=None,
        content_hash="sha256:reactdemo",
        title=title,
        excerpts=["We propose ReAct, a method that…"],
        truncated=False,
        robots="honored",
        allowlist_host="arxiv.org",
        receipt_id="rid_react",
        paths=paths,
    )
    return str(cite["id"])


def test_web_cite_search_in_tool_names() -> None:
    assert "web_cite_search" in TOOL_NAMES


def test_cite_search_finds_without_id(data_root: Path) -> None:
    cid = _seed_cite()
    result = web_cite_search("ReAct")
    assert result["ok"] is True
    assert result["count"] >= 1
    assert any(h["cite_id"] == cid for h in result["hits"])
    assert any("2210.03629" in (h.get("url") or "") for h in result["hits"])


def test_cite_search_react_paper_genre_stop(data_root: Path) -> None:
    """F13 regression: 'ReAct paper' must hit title without contiguous phrase."""
    cid = _seed_cite()
    result = web_cite_search("ReAct paper")
    assert result["ok"] is True
    assert result["count"] >= 1
    assert any(h["cite_id"] == cid for h in result["hits"])


def test_cite_search_arxiv_id(data_root: Path) -> None:
    cid = _seed_cite()
    result = web_cite_search("2210.03629")
    assert result["ok"] is True
    assert result["count"] >= 1
    assert any(h["cite_id"] == cid for h in result["hits"])


def test_cite_search_miss_returns_empty(data_root: Path) -> None:
    _seed_cite()
    result = web_cite_search("totally-unknown-widget-xyz")
    assert result["ok"] is True
    assert result["count"] == 0
    assert result["hits"] == []


def test_cite_search_then_get(data_root: Path) -> None:
    cid = _seed_cite()
    hits = web_cite_search("arxiv.org/abs/2210")["hits"]
    assert hits
    got = web_cite_get(hits[0]["cite_id"])
    assert got["ok"]
    assert got["cite_id"] == cid
    assert "ReAct" in (got.get("excerpts") or [""])[0] or "ReAct" in (
        got.get("title") or ""
    )


def test_gateway_observe_cite_search(data_root: Path) -> None:
    cid = _seed_cite()
    gw = Gateway(mode="observe")
    r = gw.execute("web_cite_search", {"query": "ReAct paper"})
    assert r.ok
    assert r.data["count"] >= 1
    assert any(h["cite_id"] == cid for h in r.data["hits"])


def test_cli_web_search_local(data_root: Path) -> None:
    cid = _seed_cite()
    runner = CliRunner()
    result = runner.invoke(app, ["web", "search", "ReAct", "--json"])
    assert result.exit_code == 0, result.output
    assert cid in result.output


def test_charter_mentions_cite_search(data_root: Path) -> None:
    assert "web_cite_search" in WEB_CONTRACT
    text = build_system_charter(mode="observe")
    assert "web_cite_search" in text
