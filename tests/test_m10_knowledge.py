"""M10 knowledge/library falsifiers F1–F12 (practical smokes)."""

from __future__ import annotations

from pathlib import Path

import httpx

from ada.cortex.charter import WEB_CONTRACT, build_system_charter
from ada.dream.delta import build_delta
from ada.dream.merge import apply_manage_result
from ada.io.paths import get_paths
from ada.memory.facts import ensure_prefs
from ada.web import allowlist as allowlist_mod
from ada.web import cites as cites_mod
from ada.web.classify import classify_fetch
from ada.web.feeds import parse_feed_bytes
from ada.web.fetch import OBSERVATION_CHAR_CAP, web_cite_search, web_fetch


INCAPSULA_SHELL = """<html>
<head>
<META NAME="robots" CONTENT="noindex,nofollow">
<script src="/_Incapsula_Resource?SWJIYLWA=abc">
</script>
<body>
</body></html>
"""


def _seed(host: str = "example.com") -> None:
    paths = get_paths()
    ensure_prefs(paths)
    allowlist_mod.add_host(host, paths=paths)


def test_f1_beehive_shell_not_knowledge(data_root: Path) -> None:
    """F1: Incapsula cites are extract_ok false; knowledge search excludes them."""
    _seed("www.beehive.govt.nz")
    url = "https://www.beehive.govt.nz/release/overseas-visitor-numbers-keep-climbing"

    def http_get(u, **kwargs):  # noqa: ANN001
        return (
            httpx.Response(
                200,
                text=INCAPSULA_SHELL,
                request=httpx.Request("GET", u),
            ),
            u,
            [u],
        )

    result = web_fetch(url, http_get=http_get)
    assert result["ok"] is True
    assert result["extract_ok"] is False
    assert result["extract_status"] == "js_shell"
    assert result["kind"] == "js_shell"
    # URL slug alone must not surface as a knowledge hit.
    hits = web_cite_search("visitor")
    assert hits["ok"]
    assert not any(h["cite_id"] == result["cite_id"] for h in hits["hits"])
    # Debug path can still find it.
    debug = web_cite_search("visitor", include_non_knowledge=True)
    assert any(h["cite_id"] == result["cite_id"] for h in debug["hits"])


def test_f2_abs_html_kind(data_root: Path) -> None:
    """F2: arXiv /abs/ is abs_html, not PDF-grade."""
    _seed("arxiv.org")
    html = """<!DOCTYPE html><html><head><title>Paper Title</title></head>
<body>
<h1>Paper Title</h1>
<div class="abstract">
<p>Abstract: We study agents and governance in multi-LLM systems with
careful experimental design across many pages of related work.</p>
</div>
</body></html>"""

    def http_get(u, **kwargs):  # noqa: ANN001
        return (
            httpx.Response(200, text=html, request=httpx.Request("GET", u)),
            u,
            [u],
        )

    r = web_fetch("https://arxiv.org/abs/2608.11207", http_get=http_get)
    assert r["ok"]
    assert r["kind"] == "abs_html"
    assert r["extract_status"] == "abs_html"
    assert r["extract_ok"] is True
    assert "abstract-grade" in WEB_CONTRACT or "abstract" in WEB_CONTRACT.lower()


def test_f3_disk_extract_exceeds_observation_cap(data_root: Path) -> None:
    """F3: disk extract can exceed 12k while observation stays capped."""
    _seed()
    huge_body = "word " * 20_000
    html = f"<html><body><article><p>{huge_body}</p></article></body></html>"

    def http_get(u, **kwargs):  # noqa: ANN001
        return (
            httpx.Response(200, text=html, request=httpx.Request("GET", u)),
            u,
            [u],
        )

    r = web_fetch("https://example.com/long", http_get=http_get)
    assert r["ok"]
    assert r["truncated"] is True
    obs_len = sum(len(e) for e in r["excerpts"])
    assert obs_len <= OBSERVATION_CHAR_CAP
    cite = cites_mod.get_cite(r["cite_id"])["cite"]
    disk_chars = int(cite.get("extract_chars") or 0)
    assert disk_chars > OBSERVATION_CHAR_CAP
    assert cite.get("chunks")
    assert len(cite["chunks"]) >= 2


def test_f6_feed_blob_excluded_from_knowledge_search(data_root: Path) -> None:
    """F6: RSS XML cites are not papers in knowledge search."""
    _seed("rss.arxiv.org")
    rss = """<?xml version="1.0"?><rss version="2.0"><channel>
<title>cs.AI updates on arXiv.org</title>
<item><title>Some Paper</title>
<link>https://arxiv.org/abs/2608.11207</link>
<description>Abstract about multi-agent governance</description>
</item></channel></rss>"""

    def http_get(u, **kwargs):  # noqa: ANN001
        return (
            httpx.Response(200, text=rss, request=httpx.Request("GET", u)),
            u,
            [u],
        )

    r = web_fetch("https://rss.arxiv.org/rss/cs.AI", http_get=http_get)
    assert r["ok"]
    assert r["kind"] == "feed_blob"
    assert r["extract_ok"] is False
    hits = web_cite_search("cs.AI")
    assert not any(h["cite_id"] == r["cite_id"] for h in hits["hits"])


def test_f7_identical_shell_hash_classified_shell() -> None:
    """F7: identical Incapsula body → js_shell, not same release."""
    c1 = classify_fetch(
        url="https://www.beehive.govt.nz/release/a",
        raw_body=INCAPSULA_SHELL,
        extracted_text="",
    )
    c2 = classify_fetch(
        url="https://www.beehive.govt.nz/release/b",
        raw_body=INCAPSULA_SHELL,
        extracted_text="",
    )
    assert c1.kind == c2.kind == "js_shell"
    assert c1.extract_ok is False


def test_f8_dream_delta_includes_cite_heads(data_root: Path) -> None:
    """F8: manage input contains per-watch cite heads, not prefs-only."""
    _seed()
    cite = cites_mod.write_cite(
        url="https://example.com/visitors-release",
        final_url="https://example.com/visitors-release",
        status=200,
        etag=None,
        last_modified=None,
        content_hash="sha256:abc",
        title="Visitor numbers",
        excerpts=["Overseas visitor arrivals rose."],
        truncated=False,
        robots="honored",
        allowlist_host="example.com",
        receipt_id="rid",
        kind="page",
        extract_status="feed_item_fallback",
        extract_ok=True,
        extract_source="feed_item",
        full_extract="Overseas visitor arrivals rose in the year to June.",
        campaign_id="nz-civic",
        watch_id="beehive_rss",
        paths=get_paths(),
    )
    delta = build_delta(paths=get_paths(), since_ts=None)
    assert delta["cite_head_count"] >= 1
    assert any(h["id"] == cite["id"] for h in delta["cite_heads"])
    assert "cite_heads" in delta["summary_text"]
    assert "nz-civic" in delta["summary_text"] or cite["id"] in delta["summary_text"]
    assert "Visitor" in delta["summary_text"] or "visitor" in delta["summary_text"].lower()


def test_f4_worldview_cites_web_heads(data_root: Path) -> None:
    """F4: Dream merge attaches cite:c_… for extract_ok web heads."""
    _seed()
    cite = cites_mod.write_cite(
        url="https://example.com/page",
        final_url="https://example.com/page",
        status=200,
        etag=None,
        last_modified=None,
        content_hash="sha256:f4",
        title="Page",
        excerpts=["Hello world excerpt"],
        truncated=False,
        robots="honored",
        allowlist_host="example.com",
        receipt_id="rid",
        kind="page",
        extract_status="ok",
        extract_ok=True,
        paths=get_paths(),
    )
    info = apply_manage_result(
        {
            "digest": "Noted the page.",
            "fact_candidates": [],
            "worldview_notes": ["Web note"],
            "open_loops": [],
            "conflicts": [],
        },
        paths=get_paths(),
        dream_id="dream-test",
        delta={
            "cite_heads": [
                {
                    "id": cite["id"],
                    "extract_ok": True,
                    "extract_status": "ok",
                }
            ]
        },
    )
    assert info["digest_path"]
    text = Path(info["digest_path"]).read_text(encoding="utf-8")
    assert f"cite:{cite['id']}" in text


def test_feed_item_summary_and_fallback(data_root: Path) -> None:
    """FeedItem.summary from description; fallback rewrites js_shell cite."""
    rss = b"""<?xml version="1.0"?><rss version="2.0"><channel>
<item><title>Overseas visitor numbers keep climbing</title>
<link>https://www.beehive.govt.nz/release/overseas-visitor-numbers-keep-climbing</link>
<guid>https://www.beehive.govt.nz/128029</guid>
<description>Visitor arrivals rose 12 percent compared with last year.</description>
</item></channel></rss>"""
    items = parse_feed_bytes(rss, feed_url="https://www.beehive.govt.nz/rss.xml")
    assert items
    assert items[0].summary
    assert "12 percent" in items[0].summary

    _seed("www.beehive.govt.nz")

    def http_get(u, **kwargs):  # noqa: ANN001
        return (
            httpx.Response(
                200,
                text=INCAPSULA_SHELL,
                request=httpx.Request("GET", u),
            ),
            u,
            [u],
        )

    r = web_fetch(items[0].url, http_get=http_get)
    assert r["extract_status"] == "js_shell"
    fb = cites_mod.apply_feed_item_fallback(
        r["cite_id"],
        summary=items[0].summary or "",
        title=items[0].title,
        paths=get_paths(),
    )
    assert fb["ok"]
    assert fb["extract_ok"] is True
    assert fb["extract_status"] == "feed_item_fallback"
    assert "12 percent" in " ".join(fb.get("excerpts") or [])
    # Now searchable as knowledge.
    hits = web_cite_search("visitor")
    assert any(h["cite_id"] == r["cite_id"] for h in hits["hits"])


def test_search_matches_chunk_text(data_root: Path) -> None:
    """web_cite_search haystack includes chunk/extract text."""
    _seed()
    cite = cites_mod.write_cite(
        url="https://example.com/unique-page",
        final_url="https://example.com/unique-page",
        status=200,
        etag=None,
        last_modified=None,
        content_hash="sha256:chunk",
        title="Generic Title",
        excerpts=["head"],
        truncated=False,
        robots="honored",
        allowlist_host="example.com",
        receipt_id="rid",
        kind="page",
        extract_status="ok",
        extract_ok=True,
        full_extract="The zygomorphic quokka policy was announced quietly.",
        paths=get_paths(),
    )
    hits = web_cite_search("zygomorphic quokka")
    assert any(h["cite_id"] == cite["id"] for h in hits["hits"])


def test_f9_charter_retrieve_cite_honesty(data_root: Path) -> None:
    """F9/F2 charter: retrieve+cite; empty extract; abs honesty."""
    text = build_system_charter(mode="observe")
    assert "extract_ok" in text or "js_shell" in text
    assert "cite:c_" in text or "retrieve" in text.lower()
    assert "abstract" in WEB_CONTRACT.lower() or "abs" in WEB_CONTRACT.lower()


def test_reclassify_tombstones_shells(data_root: Path) -> None:
    """Tombstone path marks shells without deleting files."""
    _seed("www.beehive.govt.nz")
    paths = get_paths()
    cite = cites_mod.write_cite(
        url="https://www.beehive.govt.nz/release/foxton-solar",
        final_url="https://www.beehive.govt.nz/release/foxton-solar",
        status=200,
        etag=None,
        last_modified=None,
        content_hash="sha256:d02032286070b4dd9d8fbd985a7bdca8af8edf52b89ff177db3bfcb2c8a9c43d",
        title=None,
        excerpts=[],
        truncated=False,
        robots="honored",
        allowlist_host="www.beehive.govt.nz",
        receipt_id="rid",
        paths=paths,
        save_raw_html=INCAPSULA_SHELL,
    )
    # Force legacy-looking row (page/ok) then reclassify.
    cites_mod.rewrite_cite_record(
        cite["id"],
        updates={
            "kind": "page",
            "extract_status": "ok",
            "extract_ok": True,
            "knowledge_hidden": False,
        },
        paths=paths,
    )
    out = cites_mod.reclassify_existing_cites(paths=paths, dry_run=False)
    assert out["count"] >= 1
    got = cites_mod.get_cite(cite["id"], paths=paths)["cite"]
    assert got["kind"] == "js_shell"
    assert got["knowledge_hidden"] is True
    assert cites_mod.cite_md_path(paths, cite["id"]).is_file()
