"""M07 cites + CLI + WORLDVIEW + campaign receipt (F6, F7, F12)."""

from __future__ import annotations

from pathlib import Path

import httpx
from typer.testing import CliRunner

from ada.cli.main import app
from ada.io.paths import get_paths
from ada.memory.facts import ensure_prefs
from ada.memory.open_loops import upsert_loop
from ada.memory.worldview import WorldviewError, write_digest
from ada.web import allowlist as allowlist_mod
from ada.web import cites as cites_mod
from ada.web.fetch import web_cite_get, web_fetch


def _seed() -> None:
    paths = get_paths()
    ensure_prefs(paths)
    allowlist_mod.add_host("example.com", paths=paths)


def _http_get(url, **kwargs):  # noqa: ANN001
    resp = httpx.Response(
        200,
        text="<html><title>Paper</title><body><p>ReAct abstract here.</p></body></html>",
        headers={"content-type": "text/html"},
        request=httpx.Request("GET", url),
    )
    return resp, url, [url]


def test_worldview_accepts_cite_id(data_root: Path) -> None:
    _seed()
    r = web_fetch("https://example.com/wv", http_get=_http_get)
    assert r["ok"]
    cite_ref = f"cite:{r['cite_id']}"
    out = write_digest(
        "Fetched ReAct notes.",
        cites=[cite_ref],
        title="Web note",
    )
    assert out["ok"]
    text = Path(out["path"]).read_text(encoding="utf-8")
    assert cite_ref in text


def test_worldview_rejects_missing_cite(data_root: Path) -> None:
    ensure_prefs(get_paths())
    try:
        write_digest("x", cites=["cite:c_missing000"])
        raise AssertionError("expected WorldviewError")
    except WorldviewError as exc:
        assert "not found" in str(exc)


def test_worldview_rejects_huge_html_body(data_root: Path) -> None:
    ensure_prefs(get_paths())
    html = "<!DOCTYPE html><html>" + ("x" * 100) + "</html>"
    try:
        write_digest(html, cites=["prefs.brief_time"])
        raise AssertionError("expected WorldviewError")
    except WorldviewError as exc:
        assert "HTML" in str(exc)


def test_campaign_last_receipt_accepts_fetch_receipt(data_root: Path) -> None:
    _seed()
    r = web_fetch("https://example.com/camp", http_get=_http_get)
    receipt = r.get("receipt_id") or "receipt_test_abc"
    # Ensure we have a receipt id on the cite
    cite = cites_mod.get_cite(r["cite_id"])["cite"]
    receipt = cite.get("receipt_id") or receipt
    out = upsert_loop(
        text="Watch arxiv",
        kind="campaign",
        status="active",
        stages=[
            {"id": "fetch", "state": "done", "gate": "confirm"},
            {"id": "digest", "state": "active"},
        ],
        current_stage="digest",
        last_receipt=str(receipt),
        confirmed=True,
    )
    assert out["ok"]
    assert out["loop"]["last_receipt"] == str(receipt)
    # STATUS is not page text
    assert "ReAct" not in str(out["loop"].get("status"))


def test_cli_web_cite_reads_disk_without_cortex(data_root: Path) -> None:
    _seed()
    r = web_fetch("https://example.com/cli", http_get=_http_get)
    runner = CliRunner()
    result = runner.invoke(app, ["web", "cite", r["cite_id"], "--json"])
    assert result.exit_code == 0, result.output
    assert r["cite_id"] in result.output
    assert "excerpts" in result.output


def test_cli_web_allowlist_add(data_root: Path) -> None:
    ensure_prefs(get_paths())
    runner = CliRunner()
    result = runner.invoke(app, ["web", "allowlist", "add", "arxiv.org"])
    assert result.exit_code == 0, result.output
    hosts = allowlist_mod.allowlist_hosts(get_paths())
    assert "arxiv.org" in hosts


def test_web_cite_get_direct(data_root: Path) -> None:
    _seed()
    r = web_fetch("https://example.com/get", http_get=_http_get)
    got = web_cite_get(r["cite_id"])
    assert got["ok"]
    assert got["cache"] == "disk"
    assert got["cite_id"] == r["cite_id"]


def test_atomic_cite_write_no_torn_index(data_root: Path) -> None:
    _seed()
    paths = get_paths()
    cite = cites_mod.write_cite(
        url="https://example.com/a",
        final_url="https://example.com/a",
        status=200,
        etag=None,
        last_modified=None,
        content_hash="sha256:abc",
        title="T",
        excerpts=["hello"],
        truncated=False,
        robots="honored",
        allowlist_host="example.com",
        receipt_id="rid1",
        paths=paths,
    )
    idx = (paths.cites / "index.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(idx) >= 1
    assert cite["id"] in idx[-1]
