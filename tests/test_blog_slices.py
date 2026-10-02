"""Slices 1–5: one campaign row, one card, one checkout file, delete, write again.

Tests set ADA_DATA_ROOT and a temporary checkout. They do not touch a live
portfolio checkout and they do not run git push.
"""

from __future__ import annotations

import inspect
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from ada.cortex.adapter import CortexTurn
from ada.cortex.charter import build_system_charter, mode_addendum
from ada.hud.app import create_app
from ada.hud.routes_api import _CONFIRMABLE_TOOLS
from ada.io.paths import get_paths
from ada.memory.artifacts import write_artifact
from ada.memory.blog_draft import (
    BlogDraftError,
    account_prose,
    compose_markdown,
    draft_page,
    first_sentence,
)
from ada.memory.blog_packet import gate_packet, gather_packet
from ada.memory.blog_slug import SlugError, blog_slug, require_blog_segment
from ada.memory.campaign_page import SITE, read_page, upsert_campaign_page, write_page
from ada.memory.chain_receipt import append_stage_receipt
from ada.memory.open_loops import (
    CAMPAIGN_STATUSES,
    due_campaigns,
    get_loop,
    is_draft_artifact_receipt,
    upsert_loop,
)
from ada.tools.blog_tools import (
    CheckoutError,
    resolve_portfolio_checkout,
    run_blog_checkout_delete,
)
from ada.tools.gateway import Gateway
from ada.tools.toolspec import spec_for

pytestmark = pytest.mark.tier_a

SOURCE = "docs/research/01_how_discovery_works.md"
QUESTION = "What do SEO, AEO, and GEO consume on one page?"
LONG_QUESTION = (
    "What do SEO, answer-engine optimization (AEO), and generative-engine "
    "optimization (GEO) each actually consume, and which of those needs are "
    "the same page?"
)
AUDIENCE = "A reader who wants one page for those three names."
FILL = "researched"
ORIGIN = "https://github.com/aryanjohari/aryan-portfolio.git"
PAGE_KEYS = ("site", "audience", "source", "question", "fill", "call_to_action")
FRONT_KEYS = (
    "title",
    "question",
    "description",
    "published",
    "modified",
    "fill",
    "source",
    "canonical",
)


@pytest.fixture(autouse=True)
def _no_live_checkout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ADA_PORTFOLIO_CHECKOUT", raising=False)


class _Quiet:
    model = "fake"

    def generate(self, *, system, contents, tools=None):
        return CortexTurn(text="ok", tool_calls=[], usage={})


def _init_checkout(path: Path, origin: str) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "remote", "add", "origin", origin],
        cwd=path,
        check=True,
        capture_output=True,
    )
    return path


def _store(**overrides: str) -> dict:
    args = {
        "site": SITE,
        "audience": AUDIENCE,
        "source": SOURCE,
        "question": QUESTION,
        "fill": FILL,
    }
    args.update(overrides)
    gateway = Gateway(mode="agent")
    return gateway.execute("blog_page_upsert", args)


def _frontmatter(markdown: str) -> tuple[dict, str]:
    assert markdown.startswith("---\n")
    end = markdown.find("\n---\n", 4)
    assert end > 0
    data = yaml.safe_load(markdown[4:end])
    assert isinstance(data, dict)
    return data, markdown[end + 5 :]


def _table_cells(body: str) -> list[str]:
    cells: list[str] = []
    for line in body.splitlines():
        if not line.startswith("| "):
            continue
        if line.startswith("| ---"):
            continue
        assert line.endswith(" |")
        cells.append(line[2:-2])
    return cells


def _client(monkeypatch: pytest.MonkeyPatch, data_root: Path) -> TestClient:
    monkeypatch.setenv("ADA_DATA_ROOT", str(data_root))
    monkeypatch.setenv("ADA_HUD_SESSION_SECRET", "test-secret-please-change")
    monkeypatch.setenv("ADA_HUD_PASSWORD", "test-password")
    monkeypatch.setenv("ADA_HUD_COOKIE_SECURE", "0")
    app = create_app()
    app.state.chat.adapter_factory = lambda: _Quiet()
    client = TestClient(app)
    login = client.post("/api/login", json={"password": "test-password"})
    assert login.status_code == 200
    return client


def _pipeline(data_root: Path) -> tuple[str, str]:
    stored = _store()
    assert stored.ok, stored
    cid = stored.data["id"]
    gathered = gather_packet(campaign_id=cid)
    assert gathered["ok"], gathered
    drafted = draft_page(campaign_id=cid)
    assert drafted["ok"], drafted
    slug = drafted["slug"]
    return cid, slug


def test_slice1_sidecar_and_open_loops_shell(data_root: Path) -> None:
    paths = get_paths()
    assert paths.campaign_pages == paths.facts / "campaign_pages"
    assert CAMPAIGN_STATUSES == frozenset(
        {"active", "blocked", "waiting_on_aryan", "paused", "done", "failed"}
    )
    params = set(inspect.signature(upsert_loop).parameters)
    for key in PAGE_KEYS:
        assert key not in params

    observed = Gateway(mode="observe").execute(
        "blog_page_upsert",
        {
            "site": SITE,
            "audience": AUDIENCE,
            "source": SOURCE,
            "question": QUESTION,
            "fill": FILL,
        },
    )
    assert observed.outcome == "denied"

    spec = spec_for("blog_page_upsert")
    assert spec is not None
    assert spec.side_effect == "append_local"
    assert spec.modes == frozenset({"agent"})

    stored = _store()
    assert stored.ok, stored
    cid = stored.data["id"]
    page = read_page(cid)
    assert page is not None
    assert page["site"] == SITE
    assert page["audience"] == AUDIENCE
    assert page["source"] == SOURCE
    assert page["question"] == QUESTION
    assert page["fill"] == FILL
    assert "call_to_action" not in page
    assert paths.campaign_pages.joinpath(f"{cid}.yaml").is_file()

    raw = paths.open_loops_yaml.read_text(encoding="utf-8")
    loops = yaml.safe_load(raw)["loops"]
    assert len(loops) == 1
    loop = loops[0]
    assert loop["kind"] == "campaign"
    assert loop["status"] == "active"
    assert loop["next_wake_at"]
    assert loop["stages"]
    for key in PAGE_KEYS:
        assert key not in loop
    assert SITE not in raw
    assert QUESTION not in raw
    assert SOURCE not in raw
    assert AUDIENCE not in raw
    assert FILL not in raw

    paired = upsert_campaign_page(
        site=SITE,
        audience=AUDIENCE,
        source=SOURCE,
        question="Where does one public HTML URL come from?",
        fill=FILL,
        cta_label="Notes",
        cta_url="https://example.com/notes",
    )
    assert paired["ok"]
    paired_page = read_page(paired["id"])
    assert paired_page["call_to_action"] == {
        "label": "Notes",
        "url": "https://example.com/notes",
    }
    paired_loop = get_loop(paired["id"])
    assert "call_to_action" not in paired_loop
    assert "Notes" not in paths.open_loops_yaml.read_text(encoding="utf-8")


def test_slice1_refuses_other_site_and_long_question(data_root: Path) -> None:
    paths = get_paths()
    other = _store(site="github.com/example/other")
    assert other.ok is False
    assert other.outcome == "denied"
    half = Gateway(mode="agent").execute(
        "blog_page_upsert",
        {
            "site": SITE,
            "audience": AUDIENCE,
            "source": SOURCE,
            "question": QUESTION,
            "fill": FILL,
            "cta_label": "Notes",
        },
    )
    assert half.outcome == "denied"
    two = _store(audience="One sentence. Then another.")
    assert two.outcome == "denied"

    slug = ""
    try:
        blog_slug(LONG_QUESTION)
    except SlugError as exc:
        assert "not shortened" in str(exc)
        assert "146" in str(exc)
    else:
        raise AssertionError("long question was accepted")
    folded = __import__("re").sub(r"[^a-z0-9]+", "-", LONG_QUESTION.lower()).strip("-")
    assert len(folded) == 146
    assert len(folded) > 80
    refused = _store(question=LONG_QUESTION)
    assert refused.ok is False
    assert refused.outcome == "denied"
    assert "not shortened" in (refused.denied_reason or "")
    assert not paths.campaign_pages.exists()
    assert not paths.open_loops_yaml.exists()
    short = folded[:80]
    assert short != folded
    assert not short.endswith("-2")
    with pytest.raises(SlugError):
        require_blog_segment("..")
    with pytest.raises(SlugError):
        require_blog_segment("a/b")
    assert blog_slug("a" * 80) == "a" * 80
    with pytest.raises(SlugError):
        blog_slug("a" * 81)
    assert slug == ""


def test_slice2_gather_reads_that_card_only(data_root: Path) -> None:
    paths = get_paths()
    stored = _store()
    assert stored.ok, stored
    cid = stored.data["id"]
    source_path = Path("docs/research/01_how_discovery_works.md").resolve()
    file_text = source_path.read_text(encoding="utf-8")
    expected = [line.strip() for line in file_text.splitlines() if line.strip()]

    missing = gate_packet(
        page={
            "site": SITE,
            "audience": AUDIENCE,
            "source": SOURCE,
            "question": QUESTION,
            "fill": FILL,
        },
        facts=[{"span": "this string is not in the card", "source": SOURCE}],
        file_text=file_text,
    )
    assert missing["ok"] is False
    bad_fill = gate_packet(
        page={
            "site": SITE,
            "audience": AUDIENCE,
            "source": SOURCE,
            "question": QUESTION,
            "fill": "seo",
        },
        facts=[{"span": expected[0], "source": SOURCE}],
        file_text=file_text,
    )
    assert bad_fill["ok"] is False
    empty = gate_packet(
        page={
            "site": SITE,
            "audience": AUDIENCE,
            "source": SOURCE,
            "question": QUESTION,
            "fill": FILL,
        },
        facts=[],
        file_text=file_text,
    )
    assert empty["ok"] is False
    second = gate_packet(
        page={
            "site": SITE,
            "audience": AUDIENCE,
            "source": SOURCE,
            "question": QUESTION,
            "fill": FILL,
        },
        facts=[{"span": expected[0], "source": "docs/research/02_google_page_rules.md"}],
        file_text=file_text,
    )
    assert second["ok"] is False
    no_audience = gate_packet(
        page={"site": SITE, "source": SOURCE, "question": QUESTION, "fill": FILL},
        facts=[{"span": expected[0], "source": SOURCE}],
        file_text=file_text,
    )
    assert no_audience["ok"] is False

    gathered = gather_packet(campaign_id=cid)
    assert gathered["ok"], gathered
    page = read_page(cid)
    packet = page["packet"]
    assert [fact["span"] for fact in packet] == expected
    assert {fact["source"] for fact in packet} == {SOURCE}
    assert all(fact["span"] in file_text for fact in packet)
    assert "this string is not in the card" not in {fact["span"] for fact in packet}
    assert not paths.cites.exists()
    assert not paths.scratch_web.exists()
    if paths.runs.exists():
        blob = "\n".join(
            path.read_text(encoding="utf-8")
            for path in paths.runs.rglob("*")
            if path.is_file()
        )
        assert "web_fetch" not in blob


def test_slice3_draft_frontmatter_table_and_no_paste(data_root: Path) -> None:
    stored = _store()
    cid = stored.data["id"]
    gather_packet(campaign_id=cid)
    before = read_page(cid)["packet"]
    drafted = draft_page(campaign_id=cid)
    assert drafted["ok"], drafted
    after = read_page(cid)["packet"]
    assert after == before
    slug = blog_slug(QUESTION)
    assert drafted["slug"] == slug
    assert not slug.endswith("-2")
    assert len(slug) <= 80
    day = datetime.now(timezone.utc).date().isoformat()
    path = get_paths().artifacts / day / f"{slug}.md"
    assert path.is_file()
    markdown = path.read_text(encoding="utf-8")
    front, body = _frontmatter(markdown)
    for key in FRONT_KEYS:
        assert front[key]
    assert set(front) == set(FRONT_KEYS)
    assert front["title"] == QUESTION
    assert front["question"] == QUESTION
    assert front["description"] == first_sentence(QUESTION)
    assert QUESTION.startswith(front["description"])
    assert front["fill"] == FILL
    assert front["source"] == SOURCE
    assert front["canonical"] == f"/blog/{slug}"
    assert front["published"] == day
    assert front["modified"] == day
    source = Path(SOURCE).read_text(encoding="utf-8")
    prose = account_prose(len(before))
    assert prose.strip() in body
    assert prose.strip() not in source
    assert source.strip() not in body
    assert body.strip() != source.strip()
    cells = _table_cells(body)
    spans = [fact["span"] for fact in before]
    assert cells == spans
    assert cells
    assert "![" not in markdown
    assert "<img" not in markdown.lower()
    assert "## Cites" not in markdown
    for line in body.splitlines():
        if line.startswith("| "):
            continue
        assert "](" not in line
    loop = get_loop(cid)
    assert loop["status"] == "waiting_on_aryan"
    assert loop["status"] != "done"
    assert is_draft_artifact_receipt(loop["last_receipt"])
    assert loop["last_receipt"] == f"artifacts/{day}/{slug}.md"

    with pytest.raises(BlogDraftError):
        compose_markdown(
            question=QUESTION,
            fill=FILL,
            source=SOURCE,
            slug=slug,
            prose="A new sentence accounts for the packet.\n",
            spans=["hello"],
            published=day,
            modified=day,
            image=True,
        )
    pictured = compose_markdown(
        question=QUESTION,
        fill=FILL,
        source=SOURCE,
        slug=slug,
        prose="A new sentence accounts for the packet.\n",
        spans=["plots/one.png"],
        published=day,
        modified=day,
        image=True,
    )
    assert "![](plots/one.png)" in pictured
    linked = compose_markdown(
        question=QUESTION,
        fill=FILL,
        source=SOURCE,
        slug=slug,
        prose="A new sentence accounts for the packet.\n",
        spans=["alpha span"],
        published=day,
        modified=day,
        call_to_action={"label": "Notes", "url": "https://example.com/notes"},
    )
    assert "[Notes](https://example.com/notes)" in linked
    plain = compose_markdown(
        question=QUESTION,
        fill=FILL,
        source=SOURCE,
        slug=slug,
        prose="A new sentence accounts for the packet.\n",
        spans=["alpha span"],
        published=day,
        modified=day,
    )
    assert "[Notes](https://example.com/notes)" not in plain
    assert "](" not in plain.split("\n---\n", 1)[1]


def test_slice4_confirm_copies_once_and_not_wired(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    charter = (
        "On github.com/aryanjohari/aryan-portfolio, blog_checkout_write "
        "and the git push do not need confirm. blog_checkout_delete still "
        "needs confirmed=true. artifact_write does not perform the checkout "
        "write, and a commit SHA does not mark the campaign done."
    )
    assert charter in mode_addendum("agent")
    assert charter in build_system_charter(mode="agent")
    assert "blog_checkout_write" not in _CONFIRMABLE_TOOLS
    assert "blog_checkout_delete" in _CONFIRMABLE_TOOLS
    write_spec = spec_for("blog_checkout_write")
    delete_spec = spec_for("blog_checkout_delete")
    assert write_spec is not None and write_spec.side_effect == "append_local"
    assert delete_spec is not None and delete_spec.side_effect == "confirm"
    assert write_spec.modes == frozenset({"agent"})

    cid, slug = _pipeline(data_root)
    draft_day = datetime.now(timezone.utc).date().isoformat()
    checkout = _init_checkout(tmp_path / "portfolio", ORIGIN)
    monkeypatch.setenv("ADA_PORTFOLIO_CHECKOUT", str(checkout))
    dest = checkout / "content" / "blog" / f"{slug}.md"
    assert not dest.exists()
    loop = get_loop(cid)
    assert loop["status"] == "waiting_on_aryan"
    assert cid in {row["id"] for row in due_campaigns()}
    assert is_draft_artifact_receipt(loop["last_receipt"])
    assert not dest.exists()

    escaped = write_artifact(
        title="campaign page",
        body="nope\n",
        relative_path="../content/blog/escaped.md",
        campaign_id=cid,
    )
    assert escaped["ok"] is False
    assert not dest.exists()
    assert list(checkout.rglob("*")) == [checkout / ".git"] or all(
        ".git" in str(path) for path in checkout.rglob("*") if path.is_file() or path.is_dir()
    )

    blocked = Gateway(mode="agent").execute(
        "blog_checkout_write",
        {"campaign_id": cid},
    )
    assert blocked.ok is False
    assert blocked.needs_confirm is False
    assert not dest.exists()

    append_stage_receipt(
        cid,
        {
            "stage": "critic",
            "slug": slug,
            "outcome": "pass",
            "paths": [loop["last_receipt"]],
        },
    )

    import ada.memory.blog_draft as draft_mod

    real_datetime = draft_mod.datetime

    class _Clock(datetime):
        fixed = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)

        @classmethod
        def now(cls, tz=None):
            return cls.fixed

    draft_mod.datetime = _Clock
    client = _client(monkeypatch, data_root)
    real_run = subprocess.run

    def _boom(*args, **kwargs):
        raise AssertionError(f"subprocess during checkout write: {args!r}")

    subprocess.run = _boom
    try:
        copied = Gateway(mode="agent").execute(
            "blog_checkout_write",
            {"campaign_id": cid, "confirmed": False},
        )
    finally:
        subprocess.run = real_run
        draft_mod.datetime = real_datetime
    assert copied.ok, copied
    assert dest.is_file()
    text = dest.read_text(encoding="utf-8")
    front, body = _frontmatter(text)
    assert front["published"] == "2026-08-01"
    assert front["modified"] == "2026-08-01"
    assert front["published"] != "2026-09-29"
    assert "2026-09-29" in Path(SOURCE).read_text(encoding="utf-8")
    assert front["canonical"] == f"/blog/{slug}"
    assert front["title"] == QUESTION
    assert front["fill"] == FILL
    local = (data_root / "artifacts" / draft_day / f"{slug}.md").read_text(
        encoding="utf-8"
    )
    local_front, _ = _frontmatter(local)
    assert local_front["published"] == draft_day
    assert draft_day != "2026-08-01"
    assert get_loop(cid)["status"] == "waiting_on_aryan"
    assert get_loop(cid)["status"] != "done"
    assert not any(checkout.rglob("*.json"))
    assert not any(checkout.rglob("*.html"))
    assert "og:" not in text
    first_bytes = dest.read_bytes()

    draft_mod.datetime = _Clock
    _Clock.fixed = datetime(2026, 8, 2, 12, 0, tzinfo=timezone.utc)
    try:
        again = Gateway(mode="agent").execute(
            "blog_checkout_write",
            {"campaign_id": cid},
        )
    finally:
        draft_mod.datetime = real_datetime
    assert again.ok is False
    assert dest.read_bytes() == first_bytes
    assert _frontmatter(dest.read_text(encoding="utf-8"))[0]["published"] == "2026-08-01"
    prose_body = body
    assert "This page is an account of the gathered packet." in prose_body

    wired = client.post(
        "/api/confirm",
        json={"tool": "web_fetch", "args": {"url": "https://example.com"}},
    )
    assert wired.status_code == 400
    assert wired.json()["error"] == "confirm_not_wired"
    assert dest.read_bytes() == first_bytes
    unwired = client.post(
        "/api/confirm",
        json={"tool": "blog_checkout_write", "args": {"campaign_id": cid}},
    )
    assert unwired.status_code == 400
    assert unwired.json()["error"] == "confirm_not_wired"


def test_slice4_checkout_guard_refuses_other_origins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(CheckoutError):
        resolve_portfolio_checkout()
    missing = tmp_path / "missing"
    monkeypatch.setenv("ADA_PORTFOLIO_CHECKOUT", str(missing))
    with pytest.raises(CheckoutError):
        resolve_portfolio_checkout()
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setenv("ADA_PORTFOLIO_CHECKOUT", str(empty))
    with pytest.raises(CheckoutError):
        resolve_portfolio_checkout()
    wrong = _init_checkout(tmp_path / "wrong", "https://github.com/example/other.git")
    monkeypatch.setenv("ADA_PORTFOLIO_CHECKOUT", str(wrong))
    with pytest.raises(CheckoutError):
        resolve_portfolio_checkout()
    good = _init_checkout(tmp_path / "good", ORIGIN)
    monkeypatch.setenv("ADA_PORTFOLIO_CHECKOUT", str(good))
    real_run = subprocess.run

    def _boom(*args, **kwargs):
        raise AssertionError(args)

    subprocess.run = _boom
    try:
        assert resolve_portfolio_checkout() == good.resolve()
    finally:
        subprocess.run = real_run


def test_slice5_delete_then_same_slug(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cid, slug = _pipeline(data_root)
    checkout = _init_checkout(tmp_path / "portfolio", ORIGIN)
    monkeypatch.setenv("ADA_PORTFOLIO_CHECKOUT", str(checkout))
    dest = checkout / "content" / "blog" / f"{slug}.md"
    client = _client(monkeypatch, data_root)
    append_stage_receipt(
        cid,
        {
            "stage": "critic",
            "slug": slug,
            "outcome": "pass",
            "paths": [get_loop(cid)["last_receipt"]],
        },
    )
    first = Gateway(mode="agent").execute(
        "blog_checkout_write",
        {"campaign_id": cid},
    )
    assert first.ok, first
    assert dest.is_file()
    outside = checkout / "secret.md"
    outside.write_text("keep", encoding="utf-8")
    page = read_page(cid)
    page["slug"] = "../secret"
    write_page(cid, page)
    jailed = run_blog_checkout_delete({"campaign_id": cid, "confirmed": True})
    assert jailed["ok"] is False
    assert outside.read_text(encoding="utf-8") == "keep"
    assert dest.is_file()
    page["slug"] = slug
    write_page(cid, page)

    pending = Gateway(mode="agent").execute(
        "blog_checkout_delete",
        {"campaign_id": cid},
    )
    assert pending.needs_confirm
    assert dest.is_file()
    client.app.state.chat.pending_confirms[pending.receipt_id] = {
        "tool": "blog_checkout_delete",
        "args": {"campaign_id": cid},
    }
    real_run = subprocess.run

    def _boom(*args, **kwargs):
        raise AssertionError(f"subprocess during checkout delete: {args!r}")

    subprocess.run = _boom
    try:
        deleted = client.post(
            "/api/confirm",
            json={
                "tool": "blog_checkout_delete",
                "args": {"campaign_id": "forged"},
                "pending_id": pending.receipt_id,
            },
        )
    finally:
        subprocess.run = real_run
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["observation"]["ok"] is True
    assert not dest.exists()
    cleared = read_page(cid)
    assert cleared["slug"] == ""
    assert cleared["question"] == QUESTION
    assert cleared["audience"] == AUDIENCE
    assert cleared["source"] == SOURCE
    assert cleared["fill"] == FILL
    assert get_loop(cid)["status"] == "active"
    assert outside.read_text(encoding="utf-8") == "keep"

    again = draft_page(campaign_id=cid, confirmed=False)
    assert again.get("needs_confirm") is True
    assert not dest.exists()
    assert read_page(cid)["slug"] == ""
    drafted = draft_page(campaign_id=cid, confirmed=True)
    assert drafted["ok"], drafted
    assert drafted["slug"] == slug
    assert get_loop(cid)["status"] == "waiting_on_aryan"
    rewritten = Gateway(mode="agent").execute(
        "blog_checkout_write",
        {"campaign_id": cid, "confirmed": False},
    )
    assert rewritten.ok, rewritten
    assert dest.is_file()
    names = sorted(path.name for path in (checkout / "content" / "blog").glob("*.md"))
    assert names == [f"{slug}.md"]
    assert not any(name.endswith("-2.md") for name in names)
    front, _ = _frontmatter(dest.read_text(encoding="utf-8"))
    assert front["canonical"] == f"/blog/{slug}"
    assert front["question"] == QUESTION
