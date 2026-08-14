"""M08 pack catalog + seed + Layer 0 won't-allow (F1, F2, F4, F5, F11)."""

from __future__ import annotations

from typer.testing import CliRunner

from ada.cli.main import app
from ada.dream.merge import apply_manage_result
from ada.io.paths import get_paths
from ada.memory.facts import WHITELIST_KEYS, ensure_prefs, load_prefs
from ada.memory.staging import list_staged
from ada.web import allowlist as allowlist_mod
from ada.web.packs import (
    DAY_ONE_HOST_BUDGET,
    catalog_path,
    day_one_hosts,
    expand_pack_ref,
    list_pack_summaries,
    load_catalog,
    seed_pack,
)

CONFIRM_LATER_ABSENT = (
    "www.rbnz.govt.nz",
    "www.parliament.nz",
    "hansard.parliament.nz",
    "gazette.govt.nz",
    "www.mbie.govt.nz",
    "www.nzherald.co.nz",
    "www.stuff.co.nz",
    "linkedin.com",
    "www.seek.co.nz",
)

REDIRECT_PAIRS = (
    ("treasury.govt.nz", "www.treasury.govt.nz"),
    ("newsroom.co.nz", "www.newsroom.co.nz"),
    ("comcom.govt.nz", "www.comcom.govt.nz"),
    ("stats.govt.nz", "www.stats.govt.nz"),
)


def test_f1_catalog_no_wildcard_and_budget() -> None:
    hosts = day_one_hosts()
    assert hosts, "day-one catalog must not be empty"
    assert len(hosts) <= DAY_ONE_HOST_BUDGET
    for host in hosts:
        assert "*" not in host
        assert allowlist_mod.wont_allow_reason(host) is None


def test_confirm_later_absent_from_day_one() -> None:
    hosts = set(day_one_hosts())
    missing_ok = [h for h in CONFIRM_LATER_ABSENT if h not in hosts]
    assert missing_ok == list(CONFIRM_LATER_ABSENT)
    catalog_text = catalog_path().read_text(encoding="utf-8")
    for host in CONFIRM_LATER_ABSENT:
        assert host not in catalog_text


def test_f4_arxiv_satellites() -> None:
    hosts = day_one_hosts()
    assert "arxiv.org" in hosts
    assert "rss.arxiv.org" in hosts
    assert "export.arxiv.org" in hosts
    assert hosts["rss.arxiv.org"].host != hosts["arxiv.org"].host
    assert hosts["export.arxiv.org"].host != hosts["arxiv.org"].host
    papers = load_catalog()["lab.papers"]
    paper_hosts = {h.host for h in papers.hosts}
    assert {"arxiv.org", "rss.arxiv.org", "export.arxiv.org"} <= paper_hosts


def test_f5_redirect_pairs() -> None:
    hosts = set(day_one_hosts())
    catalog = load_catalog()
    listed_pairs = {
        tuple(sorted(pair))
        for pack in catalog.values()
        for pair in pack.redirect_pairs
    }
    for a, b in REDIRECT_PAIRS:
        assert a in hosts and b in hosts
        assert tuple(sorted((a, b))) in listed_pairs


def test_add_host_rejects_localhost_and_star(data_root: Path) -> None:
    ensure_prefs(get_paths())
    for bad in ("localhost", "127.0.0.1", "::1", "*", "*.govt.nz", ""):
        result = allowlist_mod.add_host(bad, paths=get_paths())
        assert result["ok"] is False
        assert "won't-allow" in (result.get("error") or "")
    assert "localhost" not in allowlist_mod.allowlist_hosts(get_paths())
    assert "*" not in allowlist_mod.allowlist_hosts(get_paths())


def test_add_host_rejects_url_path_private_shortener(data_root: Path) -> None:
    ensure_prefs(get_paths())
    for bad in (
        "https://arxiv.org/abs/2210.03629",
        "192.168.0.1",
        "10.0.0.5",
        "169.254.169.254",
        "bit.ly",
        "t.co",
        "metadata.google.internal",
        "ada-pi5",
    ):
        result = allowlist_mod.add_host(bad, paths=get_paths())
        assert result["ok"] is False, bad
        assert "won't-allow" in (result.get("error") or ""), bad


def test_seed_idempotent_no_duplicate(data_root: Path) -> None:
    paths = get_paths()
    ensure_prefs(paths)
    first = seed_pack("lab.papers", paths=paths)
    assert first["ok"]
    assert "rss.arxiv.org" in first["added"]
    n = len(first["allowlist"])
    hosts = [e["host"] for e in first["allowlist"]]
    assert len(hosts) == len(set(hosts))
    second = seed_pack("lab.papers", paths=paths)
    assert second["ok"]
    assert second["added"] == []
    assert set(second["already"]) >= set(hosts)
    assert len(second["allowlist"]) == n
    hosts2 = [e["host"] for e in second["allowlist"]]
    assert len(hosts2) == len(set(hosts2))


def test_seed_does_not_wipe_unrelated(data_root: Path) -> None:
    paths = get_paths()
    ensure_prefs(paths)
    allowlist_mod.add_host("example.com", paths=paths, note="preexisting")
    seed_pack("nz.law", paths=paths)
    hosts = allowlist_mod.allowlist_hosts(paths)
    assert "example.com" in hosts
    assert "www.legislation.govt.nz" in hosts
    notes = {e["host"]: e.get("note") for e in allowlist_mod.load_allowlist(paths)}
    assert notes["example.com"] == "preexisting"
    assert notes["www.legislation.govt.nz"] == "pack:nz.law"


def test_seed_lab_alias_and_redirect_coapply(data_root: Path) -> None:
    paths = get_paths()
    ensure_prefs(paths)
    ids = expand_pack_ref("lab")
    assert ids == [
        "lab.code",
        "lab.cortex-docs",
        "lab.encyclopedia",
        "lab.papers",
        "lab.standards",
    ]
    result = seed_pack("nz.economy", paths=paths)
    assert result["ok"]
    hosts = allowlist_mod.allowlist_hosts(paths)
    assert "treasury.govt.nz" in hosts
    assert "www.treasury.govt.nz" in hosts
    assert "comcom.govt.nz" in hosts
    assert "www.comcom.govt.nz" in hosts


def test_f11_web_allowlist_not_dream_whitelist(data_root: Path) -> None:
    assert "web_allowlist" not in WHITELIST_KEYS
    paths = get_paths()
    ensure_prefs(paths)
    poisoned = [{"host": "evil.example", "ttl_seconds": 900}]
    info = apply_manage_result(
        {
            "fact_candidates": [{"key": "web_allowlist", "value": poisoned}],
            "conflicts": [],
        },
        paths=paths,
        dream_id="m08-f11",
    )
    assert not any(
        (m.get("key") or "").endswith("web_allowlist") for m in info["merged"]
    )
    staged = list_staged(paths=paths)
    assert any(s.get("reason") == "non_whitelist" for s in staged)
    prefs = load_prefs(paths)
    assert prefs.get("web_allowlist") != poisoned
    assert "evil.example" not in {
        e["host"] if isinstance(e, dict) else e
        for e in (prefs.get("web_allowlist") or [])
    }


def test_cli_allowlist_packs_and_list_note(data_root: Path) -> None:
    paths = get_paths()
    ensure_prefs(paths)
    runner = CliRunner()
    packs = runner.invoke(app, ["web", "allowlist", "packs"])
    assert packs.exit_code == 0, packs.output
    assert "lab.papers" in packs.output
    assert "nz.law" in packs.output
    seed = runner.invoke(app, ["web", "allowlist", "seed", "lab.papers"])
    assert seed.exit_code == 0, seed.output
    listed = runner.invoke(app, ["web", "allowlist", "list"])
    assert listed.exit_code == 0, listed.output
    assert "arxiv.org" in listed.output
    assert "note=pack:lab.papers" in listed.output
    assert "rss.arxiv.org" in listed.output


def test_cli_add_rejects_wont_allow(data_root: Path) -> None:
    ensure_prefs(get_paths())
    runner = CliRunner()
    result = runner.invoke(app, ["web", "allowlist", "add", "localhost"])
    assert result.exit_code != 0
    assert "won't-allow" in result.output or "refused" in result.output


def test_list_pack_summaries_counts() -> None:
    rows = {r["id"]: r for r in list_pack_summaries()}
    assert rows["lab.papers"]["host_count"] == 6
    assert rows["field.agents"]["host_count"] == 0
    assert rows["field.agents"]["inherits"] == ["lab.papers", "lab.cortex-docs"]
