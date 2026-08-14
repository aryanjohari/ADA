"""M09 watches / RSS ingest — falsifiers F1–F13."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

import httpx
from typer.testing import CliRunner

from ada.cli.main import app
from ada.io.paths import get_paths
from ada.memory.facts import ensure_prefs
from ada.memory.open_loops import (
    due_watch_campaigns,
    get_loop,
    list_watch_campaigns,
    upsert_loop,
)
from ada.memory.proactivity import in_quiet_hours, proactivity_suppressed
from ada.web import allowlist as allowlist_mod
from ada.web import cites as cites_mod
from ada.web.feeds import normalize_url, parse_feed_bytes, pull_feed
from ada.web.packs import seed_pack
from ada.watch.run import watch_run
from ada.watch.triage import cite_index_fresh, triage_feed_items
from ada.web.feeds import FeedItem

RUNNER = CliRunner()

ARXIV_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>cs.AI</title>
<item><title>Agents Paper</title>
<link>https://arxiv.org/abs/2608.11111</link>
<guid isPermaLink="true">oai:arXiv.org:2608:11111</guid>
<pubDate>Thu, 14 Aug 2026 06:00:00 GMT</pubDate></item>
<item><title>Old Paper</title>
<link>https://arxiv.org/abs/2601.00001</link>
<guid>oai:arXiv.org:2601:00001</guid>
<pubDate>Mon, 01 Jan 2026 00:00:00 GMT</pubDate></item>
</channel></rss>"""

BIG_RSS_ITEMS = "\n".join(
    f"""<item><title>P{i}</title>
<link>https://arxiv.org/abs/2608.{i:05d}</link>
<guid>guid-{i}</guid>
<pubDate>Thu, 14 Aug 2026 06:00:00 GMT</pubDate></item>"""
    for i in range(50)
)


def _seed_arxiv_pack() -> None:
    paths = get_paths()
    ensure_prefs(paths)
    seed_pack("lab.papers", paths=paths)


def _mock_feed_response(xml: str = ARXIV_RSS, url: str = "https://rss.arxiv.org/rss/cs.AI"):
    def http_get(u, **kwargs):  # noqa: ANN001
        return (
            httpx.Response(
                200,
                text=xml,
                headers={"content-type": "application/rss+xml", "etag": '"feed-1"'},
                request=httpx.Request("GET", u),
            ),
            url,
            [url],
        )

    return http_get


def _mock_article_response(text: str = "<html><title>Article</title><body>text</body></html>"):
    def http_get(u, **kwargs):  # noqa: ANN001
        if "rss" in u or u.endswith(".AI"):
            return _mock_feed_response()(u, **kwargs)
        return (
            httpx.Response(
                200,
                text=text,
                headers={"content-type": "text/html"},
                request=httpx.Request("GET", u),
            ),
            u,
            [u],
        )

    return http_get


def _agents_lit_campaign(*, max_items: int = 5, paths=None) -> str:
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    r = upsert_loop(
        text="Agents literature watch",
        kind="campaign",
        status="active",
        title="Agents literature watch",
        cadence="daily",
        next_wake_at=past,
        stages=[{"id": "ingest", "state": "active"}],
        current_stage="ingest",
        watches=[
            {
                "id": "arxiv_cs_ai",
                "kind": "rss",
                "url": "https://rss.arxiv.org/rss/cs.AI",
                "pack": "lab.papers",
                "max_items_per_wake": max_items,
                "max_age_hours": 168,
            }
        ],
        paths=paths,
    )
    assert r["ok"]
    return r["loop"]["id"]


def test_f1_fake_read_requires_fetch(data_root: Path) -> None:
    """F1: cannot claim article body without web_fetch receipt."""
    _seed_arxiv_pack()
    cid = _agents_lit_campaign()
    fetch_calls: list[str] = []

    def tracking_fetch(url, **kwargs):  # noqa: ANN001
        fetch_calls.append(url)
        return {
            "ok": True,
            "outcome": "ok",
            "cite_id": "c_test123",
            "cache": "miss",
            "url": url,
            "title": "Agents Paper",
            "excerpts": ["body text"],
        }

    result = watch_run(
        campaign_id=cid,
        http_get=_mock_article_response(),
        web_fetch_fn=tracking_fetch,
    )
    assert result["ok"]
    assert result["fetched"] >= 1
    assert fetch_calls
    camp = get_loop(cid)
    assert camp["last_receipt"].startswith("runs/")
    assert "watch_" in camp["last_receipt"]


def test_f2_duplicate_guid_skips_second_wake(data_root: Path) -> None:
    """F2: same guid within TTL → skip on second wake."""
    _seed_arxiv_pack()
    cid = _agents_lit_campaign(max_items=5)
    http = _mock_article_response()
    r1 = watch_run(campaign_id=cid, http_get=http)
    assert r1["fetched"] >= 1
    article_calls = 0

    def count_articles(url, **kwargs):  # noqa: ANN001
        nonlocal article_calls
        if "rss" in url:
            return _mock_feed_response()(url, **kwargs)
        article_calls += 1
        return (
            httpx.Response(
                200,
                text="<html><body>x</body></html>",
                request=httpx.Request("GET", url),
            ),
            url,
            [url],
        )

    r2 = watch_run(campaign_id=cid, http_get=count_articles)
    assert r2["ok"]
    assert article_calls == 0


def test_f3_allowlist_deny_skips_item(data_root: Path) -> None:
    """F3: non-allowlisted item URL → deny/skip; no confirm from timer."""
    paths = get_paths()
    ensure_prefs(paths)
    allowlist_mod.add_host("rss.arxiv.org", paths=paths)
    cid = _agents_lit_campaign(paths=paths)
    bad_rss = """<rss version="2.0"><channel>
<item><title>Bad</title>
<link>https://evil.example.com/story</link>
<guid>bad-1</guid>
<pubDate>Thu, 14 Aug 2026 06:00:00 GMT</pubDate></item>
</channel></rss>"""
    fetch_calls: list[str] = []

    def track(url, **kwargs):  # noqa: ANN001
        fetch_calls.append(url)
        return {"ok": True, "cite_id": "c_x", "cache": "miss"}

    watch_run(
        campaign_id=cid,
        http_get=_mock_feed_response(bad_rss),
        web_fetch_fn=track,
        paths=paths,
    )
    assert not any("evil.example.com" in u for u in fetch_calls)


def test_f4_ssrf_item_denied(data_root: Path) -> None:
    """F4: SSRF-ish item link denied at fetch layer."""
    paths = get_paths()
    _seed_arxiv_pack()
    result = pull_feed(
        "https://rss.arxiv.org/rss/cs.AI",
        paths=paths,
        http_get=_mock_feed_response(),
    )
    assert result["ok"]
    # Direct fetch to metadata / loopback denied by ssrf
    from ada.web.fetch import web_fetch

    denied = web_fetch("http://127.0.0.1/secret", paths=paths)
    assert denied.get("ok") is False


def test_f5_cap_burst(data_root: Path) -> None:
    """F5: 50-item feed → ≤max_items_per_wake fetches."""
    _seed_arxiv_pack()
    cid = _agents_lit_campaign(max_items=5)
    big = f"<rss version='2.0'><channel>{BIG_RSS_ITEMS}</channel></rss>"
    n = 0

    def count_fetch(url, **kwargs):  # noqa: ANN001
        nonlocal n
        n += 1
        return {"ok": True, "cite_id": f"c_{n}", "cache": "miss"}

    watch_run(
        campaign_id=cid,
        http_get=_mock_feed_response(big),
        web_fetch_fn=count_fetch,
    )
    assert n <= 5


def test_f6_never_crawl_allowlist() -> None:
    """F6: watch run module never iterates prefs.web_allowlist as fetch targets."""
    import inspect

    import ada.watch.run as watch_run_mod

    source = inspect.getsource(watch_run_mod)
    assert "allowlist_hosts(" not in source
    assert "load_allowlist(" not in source
    assert "seed_pack(" not in source


def test_f7_one_campaign_per_tick(data_root: Path) -> None:
    """F7: due_watch_campaigns returns at most one for timer dispatch."""
    _seed_arxiv_pack()
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    for i in range(3):
        upsert_loop(
            text=f"Watch {i}",
            kind="campaign",
            status="active",
            next_wake_at=past,
            watches=[
                {
                    "id": f"w{i}",
                    "kind": "rss",
                    "url": "https://rss.arxiv.org/rss/cs.AI",
                    "max_items_per_wake": 1,
                }
            ],
        )
    due = due_watch_campaigns(limit=1)
    assert len(due) == 1


def test_f8_quiet_hours_ingest_ok_check_suppressed(data_root: Path) -> None:
    """F8: ingest-only during quiet; campaigns check nudges suppressed."""
    paths = get_paths()
    ensure_prefs(paths)
    nz = ZoneInfo("Pacific/Auckland")
    night = datetime(2026, 8, 13, 2, 0, tzinfo=nz)
    assert in_quiet_hours(now=night) is True
    suppress = proactivity_suppressed(paths=paths, now=night)
    assert suppress["suppressed"] is True
    _seed_arxiv_pack()
    cid = _agents_lit_campaign(paths=paths)
    result = watch_run(
        campaign_id=cid,
        ingest_only=True,
        now=night,
        http_get=_mock_article_response(),
        web_fetch_fn=lambda url, **k: {"ok": True, "cite_id": "c_n", "cache": "miss"},
        paths=paths,
    )
    assert result["ok"]


def test_f9_receipt_points_to_runs(data_root: Path) -> None:
    """F9: last_receipt references runs/…watch….jsonl."""
    _seed_arxiv_pack()
    cid = _agents_lit_campaign()
    watch_run(
        campaign_id=cid,
        http_get=_mock_article_response(),
        web_fetch_fn=lambda url, **k: {"ok": True, "cite_id": "c_r", "cache": "miss"},
    )
    camp = get_loop(cid)
    assert camp["last_receipt"].startswith("runs/")
    assert "watch_" in camp["last_receipt"]
    paths = get_paths()
    rel, _evt = camp["last_receipt"].split("#", 1)
    assert (paths.root / rel).is_file()


def test_f11_chat_parity_same_web_fetch(data_root: Path) -> None:
    """F11: watch wake uses same web_fetch module as CLI."""
    from ada.web import fetch as fetch_mod

    _seed_arxiv_pack()
    cid = _agents_lit_campaign(max_items=1)
    with patch.object(fetch_mod, "web_fetch", wraps=fetch_mod.web_fetch) as wrapped:
        watch_run(
            campaign_id=cid,
            http_get=_mock_article_response(),
        )
        assert wrapped.called


def test_f13_dry_run_no_article_fetch(data_root: Path) -> None:
    """F13: --dry-run lists would-fetch without article web_fetch."""
    _seed_arxiv_pack()
    cid = _agents_lit_campaign()
    fetch_calls: list[str] = []

    def boom(url, **kwargs):  # noqa: ANN001
        fetch_calls.append(url)
        raise AssertionError("dry-run must not web_fetch articles")

    result = watch_run(
        campaign_id=cid,
        dry_run=True,
        http_get=_mock_feed_response(),
        web_fetch_fn=boom,
    )
    assert result["ok"]
    assert result["dry_run"] is True
    assert result["fetched"] >= 1
    assert not fetch_calls


def test_normalize_url_strips_utm() -> None:
    raw = "http://Example.com/path?utm_source=x&id=1"
    norm = normalize_url(raw)
    assert norm.startswith("https://")
    assert "utm_source" not in norm
    assert "id=1" in norm


def test_parse_arxiv_rss_smoke() -> None:
    items = parse_feed_bytes(ARXIV_RSS.encode(), feed_url="https://rss.arxiv.org/rss/cs.AI")
    assert len(items) == 2
    assert items[0].guid.startswith("oai:arXiv")


def test_triage_cite_fresh_skips(data_root: Path) -> None:
    """Cite-index fresh → skip fetch (M09 triage)."""
    paths = get_paths()
    _seed_arxiv_pack()
    url = "https://arxiv.org/abs/2608.99999"
    cites_mod.write_cite(
        url=url,
        final_url=url,
        status=200,
        etag=None,
        last_modified=None,
        content_hash="sha256:abc",
        title="Cached",
        excerpts=["x"],
        truncated=False,
        robots="honored",
        allowlist_host="arxiv.org",
        receipt_id="r1",
        paths=paths,
    )
    assert cite_index_fresh(url, paths=paths) is True
    items = [
        FeedItem(
            guid="g1",
            url=url,
            title="Cached",
            published_at=datetime.now(timezone.utc),
        )
    ]
    watch = {"id": "w", "max_items_per_wake": 5, "max_age_hours": 168}
    selected, skips = triage_feed_items(items, watch=watch, cursor={}, paths=paths)
    assert not selected
    assert any(s["reason"] == "cite_fresh" for s in skips)


def test_cli_watch_list_and_dry_run(data_root: Path) -> None:
    _seed_arxiv_pack()
    cid = _agents_lit_campaign()
    r = RUNNER.invoke(app, ["watch", "list"])
    assert r.exit_code == 0
    assert cid in r.stdout
    r2 = RUNNER.invoke(app, ["watch", "status", "--campaign", cid])
    assert r2.exit_code == 0
    assert "arxiv_cs_ai" in r2.stdout


def test_watches_schema_validation(data_root: Path) -> None:
    paths = get_paths()
    import pytest

    with pytest.raises(ValueError, match="requires url"):
        upsert_loop(
            text="Bad watch",
            kind="campaign",
            watches=[{"id": "x", "kind": "rss"}],
            paths=paths,
        )
    r = upsert_loop(
        text="Ok",
        kind="campaign",
        watches=[
            {
                "id": "arxiv_cs_ai",
                "kind": "rss",
                "url": "https://rss.arxiv.org/rss/cs.AI",
                "max_items_per_wake": 5,
            }
        ],
        paths=paths,
    )
    assert r["ok"]
    assert list_watch_campaigns(paths=paths)


def test_watch_session_jsonl_events(data_root: Path) -> None:
    _seed_arxiv_pack()
    cid = _agents_lit_campaign(max_items=1)
    watch_run(
        campaign_id=cid,
        http_get=_mock_article_response(),
        web_fetch_fn=lambda url, **k: {"ok": True, "cite_id": "c_e", "cache": "miss"},
    )
    paths = get_paths()
    camp = get_loop(cid)
    rel = camp["last_receipt"].split("#")[0]
    lines = (paths.root / rel).read_text(encoding="utf-8").strip().splitlines()
    types = {json.loads(line)["type"] for line in lines}
    assert "feed_pulled" in types
    assert "watch_wake_end" in types
