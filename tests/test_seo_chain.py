"""Chain slices: temp checkout only. No live portfolio and no git push to GitHub."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import httpx
import pytest
import yaml

from ada.io.paths import get_paths
from ada.memory.blog_packet import gate_packet, repo_root
from ada.memory.blog_slug import SlugError, blog_slug
from ada.memory.facts import ensure_prefs
from ada.memory.campaign_page import SITE
from ada.cortex.adapter import CortexTurn
from ada.memory.chain_draft import PAGE_SYSTEM, opening_answer, repair_markdown
from ada.memory.chain_fetch import is_search_url
from ada.memory.chain_librarian import is_holder_href
from ada.memory.chain_plan import (
    CHAIN_STAGES,
    load_plan,
    missing_content_word,
    open_chain_campaign,
    plan_source_questions,
    question_adds_fact,
    run_chain_wake,
    save_plan,
    section1_refusals,
)
from ada.memory.chain_receipt import latest_receipt, read_receipts
from ada.memory.open_loops import get_loop, upsert_loop
from ada.memory.portfolio_chain import read_portfolio_chain
from ada.tools.blog_tools import commit_argv, push_argv, run_blog_checkout_delete
from ada.tools.gateway import Gateway
from ada.web.allowlist import add_host, allowlist_hosts

pytestmark = pytest.mark.tier_a

SOURCE = "docs/research/01_how_discovery_works.md"
QUESTION = "What do SEO, AEO, and GEO consume on one page?"
AUDIENCE = "A person who reads about work the operator has already shipped."
KEYWORD = "best seo keywords"
URL = "https://example.com/fact"
SPAN = "Alpha span from the page."


@pytest.fixture(autouse=True)
def _no_live_checkout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ADA_PORTFOLIO_CHECKOUT", raising=False)


def _init_checkout(path: Path, origin: str) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "init", "-b", "main"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "remote", "add", "origin", origin],
        cwd=path,
        check=True,
        capture_output=True,
    )
    return path


def _origin(tmp_path: Path) -> str:
    return "https://github.com/aryanjohari/aryan-portfolio.git"


def _write_config(data_root: Path, **overrides: object) -> None:
    doc: dict = {
        "site": SITE,
        "audience": AUDIENCE,
        "aim": "educate",
        "places": [],
        "offer": "Pages about work the operator has already shipped.",
        "proof": ["docs/research/04_pipeline_steps.md records the public host."],
        "contact": "",
        "actions": {"kind": "replies", "count": 0},
        "folders": ["docs/research", "docs/modules"],
        "branch": "main",
    }
    doc.update(overrides)
    path = get_paths().portfolio_chain_yaml
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc), encoding="utf-8")


def _page_config(**extra: object) -> dict:
    doc = {
        "site": SITE,
        "audience": AUDIENCE,
        "aim": "educate",
        "places": [],
        "offer": "Pages about work the operator has already shipped.",
        "proof": ["docs/research/04_pipeline_steps.md records the public host."],
        "contact": "",
        "actions": {"kind": "replies", "count": 0},
        "folders": ["docs/research", "docs/modules"],
    }
    doc.update(extra)
    return doc


def _item(**extra: object) -> dict:
    row = {
        "source": SOURCE,
        "question": QUESTION,
        "fill": "researched",
        "urls": [],
    }
    row.update(extra)
    return row


def _open(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, origin: str | None = None) -> tuple[str, Path]:
    checkout = _init_checkout(tmp_path / "portfolio", origin or _origin(tmp_path))
    monkeypatch.setenv("ADA_PORTFOLIO_CHECKOUT", str(checkout))
    opened = open_chain_campaign()
    assert opened["ok"], opened
    return str(opened["id"]), checkout


def _prompt_text(contents: list[object]) -> str:
    chunks: list[str] = []
    for item in contents:
        if isinstance(item, str):
            chunks.append(item)
            continue
        for part in getattr(item, "parts", None) or []:
            text = getattr(part, "text", None)
            if text:
                chunks.append(str(text))
    return "\n".join(chunks)


def _spans_in_prompt(prompt: str) -> list[str]:
    label = "Excerpts:\n" if "Excerpts:\n" in prompt else "Spans:\n"
    if label not in prompt:
        return []
    spans: list[str] = []
    for line in prompt.split(label, 1)[1].splitlines():
        if ". " not in line:
            continue
        number, rest = line.split(". ", 1)
        if number.isdigit():
            spans.append(rest)
    return spans


def _paragraph_page(prompt: str) -> str:
    prose: list[str] = []
    for span in _spans_in_prompt(prompt):
        text = span.strip()
        if not text or text.startswith("#") or text.startswith("|") or text.startswith("```"):
            continue
        if text[:1].isdigit() and ". " in text[:4]:
            continue
        prose.append(text)
    if not prose:
        prose = ["Notes"]
    question = ""
    for line in prompt.splitlines():
        if line.startswith("Question: "):
            question = line.split("Question: ", 1)[1].strip()
            break
    first = prose[0]
    if question and question.rstrip("?.") not in first:
        first = f"{question.rstrip('?.')}. {first}"
    folded_q = " ".join(question.casefold().split()).rstrip(".!?")
    folded_f = " ".join(first.casefold().split()).rstrip(".!?")
    if folded_q and folded_f == folded_q:
        first = f"Yes. {first}"
    second = prose[1] if len(prose) > 1 else prose[0]
    heading = " ".join(second.split()[:6])
    parts = [first, "", f"## {heading}", "", second]
    seen = {first, second}
    for extra in prose[2:]:
        if extra in seen or len(extra) > 80:
            continue
        parts.extend(["", extra])
        seen.add(extra)
    return "\n".join(parts) + "\n"


class _PageModel:
    def __init__(self, text: str | None = None) -> None:
        self.text = text
        self.tools: list[object] = []
        self.system = ""
        self.prompts: list[str] = []

    def generate(self, *, system: str, contents: list[object], tools: object = None) -> CortexTurn:
        self.tools.append(tools)
        self.system = system
        prompt = _prompt_text(contents)
        self.prompts.append(prompt)
        if self.text is not None:
            return CortexTurn(text=self.text)
        return CortexTurn(text=_paragraph_page(prompt))


def _wake_until(cid: str, stage: str, **kwargs: object) -> None:
    writer = kwargs.pop("model", None) or _PageModel()
    for _ in range(len(CHAIN_STAGES) + 1):
        loop = get_loop(cid)
        assert loop is not None
        if loop["current_stage"] == stage:
            return
        result = run_chain_wake(cid, model=writer, **kwargs)  # type: ignore[arg-type]
        assert result.get("ok") or result.get("outcome") in {"ok", "pass", "skip"}, result
    raise AssertionError(f"never reached {stage}")


def _http_get(url, **kwargs):  # noqa: ANN001
    resp = httpx.Response(
        200,
        text=f"<html><body><p>{SPAN}</p></body></html>",
        headers={"content-type": "text/html"},
        request=httpx.Request("GET", url),
    )
    return resp, url, [url]


def test_chain_config_reads_operator_yaml(data_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def _explode(*_args, **_kwargs):  # noqa: ANN001
        raise AssertionError("config reader fetched the public host")

    monkeypatch.setattr("urllib.request.urlopen", _explode)
    _write_config(
        data_root,
        aim="hire",
        contact="mailto:ada@example.com",
        proof=[],
        folders=["docs/research", "docs/modules"],
    )
    before = get_paths().portfolio_chain_yaml.read_text(encoding="utf-8")
    read = read_portfolio_chain()
    assert read["ok"], read
    config = read["config"]
    assert config["site"] == SITE
    assert config["audience"] == AUDIENCE
    assert config["aim"] == "hire"
    assert config["aims"] == ["hire"]
    assert config["places"] == []
    assert config["offer"] == "Pages about work the operator has already shipped."
    assert config["proof"] == []
    assert config["contact"] == "mailto:ada@example.com"
    assert config["show_contact"] is True
    assert config["actions"] == {"kind": "replies", "count": 0}
    assert config["folders"] == ["docs/research", "docs/modules"]
    assert "facts" not in config
    assert "question" not in config
    assert "sentence" not in config
    assert "queue" not in config
    assert get_paths().portfolio_chain_yaml.read_text(encoding="utf-8") == before
    _write_config(data_root, aim="educate", contact="mailto:ada@example.com")
    educate = read_portfolio_chain()
    assert educate["ok"], educate
    assert educate["config"]["aim"] == "educate"
    assert educate["config"]["contact"] == "mailto:ada@example.com"
    assert educate["config"]["show_contact"] is False
    _write_config(data_root, aim="prove-shipping", contact="kept")
    shipping = read_portfolio_chain()
    assert shipping["ok"], shipping
    assert shipping["config"]["show_contact"] is False
    assert shipping["config"]["contact"] == "kept"


def test_chain_config_refuses_missing_second_site_audience_and_aim(data_root: Path) -> None:
    missing = read_portfolio_chain()
    assert missing["ok"] is False
    assert not get_paths().portfolio_chain_yaml.exists()
    _write_config(data_root, site=["github.com/example/other", SITE])
    assert read_portfolio_chain()["ok"] is False
    _write_config(data_root, sites=[SITE])
    assert read_portfolio_chain()["ok"] is False
    _write_config(data_root, audience="One sentence. Then another.")
    assert read_portfolio_chain()["ok"] is False
    _write_config(data_root, aims=["hire", "educate"])
    assert read_portfolio_chain()["denied_reason"] == "two aims"
    _write_config(data_root, aim=["hire", "book"])
    assert read_portfolio_chain()["denied_reason"] == "two aims"
    _write_config(data_root, keyword="seo")
    assert read_portfolio_chain()["ok"] is False
    _write_config(data_root, query="best page")
    assert read_portfolio_chain()["ok"] is False
    _write_config(data_root, clicks=1)
    assert read_portfolio_chain()["ok"] is False
    _write_config(data_root, default_cta={"label": "Get in touch", "mail": "mailto:a@b.c"})
    assert read_portfolio_chain()["ok"] is False
    _write_config(data_root, branch="")
    assert read_portfolio_chain()["ok"] is False


def test_portfolio_refuses_places_book_and_call(data_root: Path) -> None:
    _write_config(data_root, places=["the one suburb on the door"])
    places = read_portfolio_chain()
    assert places["ok"] is False
    assert places["denied_reason"] == "places on the portfolio must be empty"
    _write_config(
        data_root,
        aim="book",
        actions={"kind": "bookings", "count": 0},
    )
    booked = read_portfolio_chain()
    assert booked["ok"] is False
    assert booked["denied_reason"] == "aim must not be book or call on the portfolio"
    _write_config(
        data_root,
        aim="call",
        actions={"kind": "calls", "count": 0},
    )
    called = read_portfolio_chain()
    assert called["ok"] is False
    assert called["denied_reason"] == "aim must not be book or call on the portfolio"


def test_shop_book_and_call_read_and_bind_does_not_publish(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_config(
        data_root,
        site="https://example.invalid/one-shop",
        audience="A person this one shop can actually serve, close enough to visit.",
        aim="book",
        places=["the one suburb on the door"],
        offer="A haircut at that shop, during the hours on the door.",
        proof=["operator receipt: the door, the hours, and the booking method"],
        contact="the phone or the booking link on that receipt",
        actions={"kind": "bookings", "count": 0},
    )
    booked = read_portfolio_chain()
    assert booked["ok"], booked
    assert booked["config"]["site"] == "https://example.invalid/one-shop"
    assert booked["config"]["aim"] == "book"
    assert booked["config"]["places"] == ["the one suburb on the door"]
    assert booked["config"]["actions"] == {"kind": "bookings", "count": 0}
    assert booked["config"]["show_contact"] is True
    cid, checkout = _open(tmp_path, monkeypatch)
    result = run_chain_wake(cid)
    assert result["ok"] is False
    assert not (checkout / "content").exists()
    loop = get_loop(cid)
    assert loop["current_stage"] == "bind-site"
    _write_config(
        data_root,
        site="https://example.invalid/one-shop",
        audience="A person this one shop can actually serve, close enough to visit.",
        aim="call",
        places=["the one suburb on the door"],
        offer="A haircut at that shop, during the hours on the door.",
        proof=["operator receipt: the door, the hours, and the booking method"],
        contact="the phone or the booking link on that receipt",
        actions={"kind": "calls", "count": 0},
    )
    called = read_portfolio_chain()
    assert called["ok"], called
    assert called["config"]["aim"] == "call"
    assert called["config"]["actions"]["kind"] == "calls"


def test_chain_config_folders_are_paths_not_a_fact_list(data_root: Path) -> None:
    many = [f"cards/{n:02d}" for n in range(13)]
    _write_config(data_root, proof=[], folders=many)
    allowed = read_portfolio_chain()
    assert allowed["ok"], allowed
    assert allowed["config"]["proof"] == []
    assert allowed["config"]["folders"] == many
    assert "facts" not in allowed["config"]
    _write_config(
        data_root,
        folders=[
            {
                "sentence": "A cut is a service the shop performs.",
                "question": "What is a cut?",
                "source": "notes/cut.md",
                "url": "",
            }
        ],
    )
    refused = read_portfolio_chain()
    assert refused["ok"] is False
    assert refused["denied_reason"] == "a folder is a path"
    _write_config(data_root, folders=["../outside"])
    escaped = read_portfolio_chain()
    assert escaped["ok"] is False
    assert "repo" in escaped["denied_reason"]
    _write_config(data_root, folders=["docs/research/01_how_discovery_works.md"])
    named = read_portfolio_chain()
    assert named["ok"] is False
    assert named["denied_reason"] == "a folder is a path"
    _write_config(data_root, facts=[{"sentence": "A cut is a service.", "note": SOURCE}])
    leftover = read_portfolio_chain()
    assert leftover["ok"] is False
    assert leftover["denied_reason"] == "facts is not a field"


def test_chain_plan_chooses_the_next_unpublished_card(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ada.memory.chain_plan import record_published_page

    root = tmp_path / "notes-repo"
    cut = "A cut is a service the shop performs."
    beard = "A beard trim is different."
    grid = "Ponsonby, Grey Lynn, and Kingsland funnel to the one shop page."
    for rel, heading, body in (
        ("notes/a-grid.md", "Suburbs", grid),
        ("notes/b-cut.md", "A cut", cut),
        ("notes/c-beard.md", "A beard", beard),
    ):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {heading}\n\n{body}\n", encoding="utf-8")
    monkeypatch.setattr("ada.memory.blog_packet.repo_root", lambda: root)
    _write_config(data_root, folders=["notes"])
    cid, checkout = _open(tmp_path, monkeypatch)
    before = get_paths().portfolio_chain_yaml.read_text(encoding="utf-8")
    assert "facts:" not in before
    assert run_chain_wake(cid)["ok"]
    assert run_chain_wake(cid)["ok"]
    planned = run_chain_wake(
        cid,
        suggestions=[{"text": KEYWORD, "tag": "marketing"}],
    )
    assert planned["ok"], planned
    doc = yaml.safe_load(
        (data_root / latest_receipt(cid, "plan", outcome="ok")["paths"][0]).read_text(
            encoding="utf-8"
        )
    )
    assert len(doc["queue"]) == 1
    item = doc["queue"][0]
    assert item["card"] == "notes/b-cut.md"
    assert item["page"] == "notes/b-cut.md"
    assert item["source"] == "notes/b-cut.md"
    assert item["question"] == cut
    assert item["question"] != KEYWORD
    assert KEYWORD not in item["question"]
    assert grid not in item["question"]
    assert len(item["local_files"]) <= 3
    assert "notes/a-grid.md" not in item["local_files"]
    assert "notes/b-cut.md" in item["local_files"]
    reasons = {row["reason"] for row in doc["refusals"]}
    assert "service-area" in reasons
    assert get_paths().portfolio_chain_yaml.read_text(encoding="utf-8") == before
    assert not (checkout / "content" / "blog").exists()
    record_published_page(item["card"], paths=get_paths())
    cid2, _checkout2 = _open(tmp_path / "next", monkeypatch)
    assert run_chain_wake(cid2)["ok"]
    assert run_chain_wake(cid2)["ok"]
    again = run_chain_wake(cid2)
    assert again["ok"], again
    second = yaml.safe_load(
        (data_root / latest_receipt(cid2, "plan", outcome="ok")["paths"][0]).read_text(
            encoding="utf-8"
        )
    )
    assert len(second["queue"]) == 1
    assert second["queue"][0]["card"] == "notes/c-beard.md"
    assert second["queue"][0]["card"] != item["card"]
    assert any(row["reason"] == "published" for row in second["refusals"])
    assert get_paths().portfolio_chain_yaml.read_text(encoding="utf-8") == before


def test_chain_bind_refuses_other_origin(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_config(data_root)
    cid, checkout = _open(
        tmp_path,
        monkeypatch,
        origin="https://github.com/example/9horsemen.git",
    )
    result = run_chain_wake(cid)
    assert result["ok"] is False
    assert not (checkout / "content").exists()
    loop = get_loop(cid)
    assert loop["current_stage"] == "bind-site"
    assert loop["stages"][0]["state"] != "done"


def test_chain_plan_queues_card01_short_question(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_config(data_root)
    cid, _checkout = _open(tmp_path, monkeypatch)
    assert run_chain_wake(cid)["ok"]
    assert run_chain_wake(cid)["ok"]
    planned = run_chain_wake(cid, items=[_item()])
    assert planned["ok"], planned
    plan_receipt = latest_receipt(cid, "plan", outcome="ok")
    assert plan_receipt is not None
    rel = str(plan_receipt["paths"][0])
    text = (data_root / rel).read_text(encoding="utf-8")
    doc = yaml.safe_load(text)
    assert doc["queue"][0]["question"] == QUESTION
    assert doc["queue"][0]["fill"] == "researched"
    assert doc["queue"][0]["source"] == SOURCE
    assert doc["queue"][0]["aim"] == "educate"
    assert doc["audience"] == AUDIENCE
    assert "-2" not in text
    assert not (tmp_path / "portfolio" / "content" / "blog").exists()


def test_chain_plan_refuses_section1_without_shortening(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_config(data_root)
    cid, _checkout = _open(tmp_path, monkeypatch)
    run_chain_wake(cid)
    run_chain_wake(cid)
    run_chain_wake(cid, items=[_item()])
    long_q = ""
    for row in section1_refusals():
        if row["source"] == SOURCE:
            long_q = row["question"]
    card = (repo_root() / SOURCE).read_text(encoding="utf-8")
    assert long_q and long_q in card
    with pytest.raises(SlugError):
        blog_slug(long_q)
    plan_text = (data_root / latest_receipt(cid, "plan", outcome="ok")["paths"][0]).read_text(
        encoding="utf-8"
    )
    doc = yaml.safe_load(plan_text)
    assert long_q not in [item["question"] for item in doc["queue"]]
    assert any(row["question"] == long_q and row["reason"] == "slug" for row in doc["refusals"])
    assert "-2" not in plan_text
    assert long_q[:80] not in [item["question"] for item in doc["queue"]]


def test_chain_plan_keeps_keyword_off_question(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_config(data_root)
    cid, _checkout = _open(tmp_path, monkeypatch)
    run_chain_wake(cid)
    run_chain_wake(cid)
    run_chain_wake(
        cid,
        items=[_item(), _item(question=KEYWORD)],
        suggestions=[{"text": KEYWORD, "tag": "marketing"}],
    )
    doc = yaml.safe_load(
        (data_root / latest_receipt(cid, "plan", outcome="ok")["paths"][0]).read_text(
            encoding="utf-8"
        )
    )
    questions = [item["question"] for item in doc["queue"]]
    assert QUESTION in questions
    assert KEYWORD not in questions
    assert doc["suggestions"] == [{"text": KEYWORD, "tag": "marketing"}]


def test_chain_plan_empty_items_writes_empty_queue(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_config(data_root)
    cid, _checkout = _open(tmp_path, monkeypatch)
    assert run_chain_wake(cid)["ok"]
    assert run_chain_wake(cid)["ok"]
    planned = run_chain_wake(cid, items=[])
    assert planned["ok"], planned
    doc = yaml.safe_load(
        (data_root / latest_receipt(cid, "plan", outcome="ok")["paths"][0]).read_text(
            encoding="utf-8"
        )
    )
    assert doc["queue"] == []


def test_planner_writes_one_question_and_keeps_the_keyword_off_it() -> None:
    text = (repo_root() / "src/ada/memory/blog_slug.py").read_text(encoding="utf-8")
    card = ""
    for row in section1_refusals():
        if row["source"] == SOURCE:
            card = row["question"]
    planned = plan_source_questions(
        [
            {
                "source": "src/ada/memory/blog_slug.py",
                "fill": "researched",
                "keyword": KEYWORD,
            }
        ],
        audience=AUDIENCE,
        aim="educate",
    )
    assert planned["suggestions"] == [{"text": KEYWORD, "tag": "hunch"}]
    assert len(planned["items"]) == 1
    question = planned["items"][0]["question"]
    assert question == "Blog slug from the question."
    assert question != KEYWORD
    assert KEYWORD not in question
    assert question != card
    assert card not in question
    assert "What does this file answer about" not in question


class _FakeReader:
    def __init__(self, text: str) -> None:
        self.text = text
        self.tools: list[object] = []
        self.prompts: list[str] = []

    def generate(self, *, system: str, contents: list[object], tools: object = None) -> CortexTurn:
        self.tools.append(tools)
        self.prompts.append(_prompt_text(contents))
        return CortexTurn(text=self.text)


def test_planner_model_refuses_a_fact_that_is_not_in_the_file() -> None:
    fake = _FakeReader("How did the invented 1999 launch ship?")
    planned = plan_source_questions(
        [{"source": "src/ada/memory/blog_slug.py", "fill": "researched"}],
        audience=AUDIENCE,
        aim="educate",
        model=fake,
    )
    assert fake.tools == [[]]
    assert planned["items"] == []
    assert planned["refusals"][0]["reason"] == "fact"
    assert planned["refusals"][0]["question"] == "How did the invented 1999 launch ship?"


def test_planner_model_queues_a_short_question_already_in_the_file(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_text = (repo_root() / SOURCE).read_text(encoding="utf-8")
    card = ""
    for row in section1_refusals():
        if row["source"] == SOURCE:
            card = row["question"]
    access = "Access date for every source below: 2026-09-29."
    question = "How does Google Search crawl a page?"
    assert card
    assert access in source_text
    assert question != card
    assert question != access
    assert question_adds_fact(question, source_text) is False
    fake = _FakeReader(question)
    _write_config(data_root)
    cid, _checkout = _open(tmp_path, monkeypatch)
    assert run_chain_wake(cid)["ok"]
    assert run_chain_wake(cid)["ok"]
    planned = plan_source_questions(
        [{"source": SOURCE, "fill": "researched"}],
        audience=AUDIENCE,
        aim="educate",
        model=fake,
    )
    assert fake.tools == [[]]
    assert "Write one short question a stranger would ask." in fake.prompts[0]
    assert planned["items"][0]["question"] == question
    assert "What does this file answer about" not in question
    assert all(row.get("reason") != "card-question" for row in planned["refusals"])
    queued = run_chain_wake(cid, items=planned["items"])
    assert queued["ok"], queued
    doc = yaml.safe_load(
        (data_root / latest_receipt(cid, "plan", outcome="ok")["paths"][0]).read_text(
            encoding="utf-8"
        )
    )
    assert doc["queue"][0]["question"] == question
    questions = [item["question"] for item in doc["queue"]]
    assert card not in questions
    assert access not in questions


def test_question_line_that_fits_is_the_queued_title(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    question = "How does one page name its topic?"
    access = "Access date for every source below: 2026-09-29."
    root = tmp_path / "sources"
    path = root / "notes" / "topic.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        f"{access}\n\n## 1. Question\n\n{question}\n\nThe page names the topic.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("ada.memory.blog_packet.repo_root", lambda: root)
    _write_config(data_root)
    cid, _checkout = _open(tmp_path / "camp", monkeypatch)
    assert run_chain_wake(cid)["ok"]
    assert run_chain_wake(cid)["ok"]
    planned = plan_source_questions(
        [{"source": "notes/topic.md", "fill": "researched"}],
        audience=AUDIENCE,
        aim="educate",
    )
    assert planned["items"][0]["question"] == question
    queued = run_chain_wake(cid, items=planned["items"])
    assert queued["ok"], queued
    doc = yaml.safe_load(
        (data_root / latest_receipt(cid, "plan", outcome="ok")["paths"][0]).read_text(
            encoding="utf-8"
        )
    )
    assert doc["queue"][0]["question"] == question
    assert access not in [item["question"] for item in doc["queue"]]
    assert "What does this file answer about" not in doc["queue"][0]["question"]


def test_long_question_line_is_refused_whole(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    card = ""
    for row in section1_refusals():
        if row["source"] == SOURCE:
            card = row["question"]
    access = "Access date for every source below: 2026-09-29."
    assert card and access in (repo_root() / SOURCE).read_text(encoding="utf-8")
    planned = plan_source_questions(
        [{"source": SOURCE, "fill": "researched"}],
        audience=AUDIENCE,
        aim="educate",
    )
    assert planned["items"][0]["question"] == card
    assert access != planned["items"][0]["question"]
    _write_config(data_root)
    cid, _checkout = _open(tmp_path, monkeypatch)
    run_chain_wake(cid)
    run_chain_wake(cid)
    run_chain_wake(cid, items=planned["items"])
    plan_text = (data_root / latest_receipt(cid, "plan", outcome="ok")["paths"][0]).read_text(
        encoding="utf-8"
    )
    doc = yaml.safe_load(plan_text)
    questions = [item["question"] for item in doc["queue"]]
    assert card not in questions
    assert access not in questions
    assert all("What does this file answer about" not in item for item in questions)
    assert any(row["question"] == card and row["reason"] == "slug" for row in doc["refusals"])
    assert "-2" not in plan_text
    assert card[:80] not in questions


def test_plan_skips_an_access_date_when_the_file_has_no_question(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    access = "Access date for every source below: 2026-09-29."
    sentence = "The packet names the topic."
    root = tmp_path / "sources"
    path = root / "notes" / "note.md"
    path.parent.mkdir(parents=True)
    path.write_text(f"{access}\n\n{sentence}\n", encoding="utf-8")
    monkeypatch.setattr("ada.memory.blog_packet.repo_root", lambda: root)
    _write_config(data_root)
    cid, _checkout = _open(tmp_path / "camp", monkeypatch)
    assert run_chain_wake(cid)["ok"]
    assert run_chain_wake(cid)["ok"]
    planned = plan_source_questions(
        [{"source": "notes/note.md", "fill": "researched"}],
        audience=AUDIENCE,
        aim="educate",
    )
    assert planned["items"][0]["question"] == sentence
    queued = run_chain_wake(cid, items=planned["items"])
    assert queued["ok"], queued
    doc = yaml.safe_load(
        (data_root / latest_receipt(cid, "plan", outcome="ok")["paths"][0]).read_text(
            encoding="utf-8"
        )
    )
    assert doc["queue"][0]["question"] == sentence
    assert access not in [item["question"] for item in doc["queue"]]


def test_chain_one_wake_one_stage(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_config(data_root)
    cid, _checkout = _open(tmp_path, monkeypatch)
    observed = Gateway(mode="observe").execute("blog_chain_wake", {"campaign_id": cid})
    assert observed.ok is False
    once = Gateway(mode="agent").execute("blog_chain_wake", {"campaign_id": cid})
    assert once.ok, once
    loop = get_loop(cid)
    states = {stage["id"]: stage["state"] for stage in loop["stages"]}
    assert states["bind-site"] == "done"
    assert states["understand-aim"] == "active"
    assert states["plan"] == "pending"
    assert loop["current_stage"] == "understand-aim"
    assert loop["next_wake_at"]
    assert loop["status"] == "active"
    assert "queue" not in loop


def test_chain_fetch_skips_when_no_url(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_config(data_root)
    cid, checkout = _open(tmp_path, monkeypatch)
    _wake_until(cid, "external-fetch", items=[_item()])
    result = run_chain_wake(cid)
    assert result["outcome"] == "skip"
    assert latest_receipt(cid, "external-fetch", outcome="skip") is not None
    assert not list(checkout.rglob("*.md"))


def test_chain_fetch_keeps_only_named_verbatim_spans(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "ada.web.fetch._robots_allowed",
        lambda url, ignore_robots=False: (True, "honored"),
    )
    ensure_prefs()
    add_host("example.com")
    seen: list[str] = []

    def http_get(url, **kwargs):  # noqa: ANN001
        seen.append(url)
        return _http_get(url)

    _write_config(data_root)
    cid, _checkout = _open(tmp_path, monkeypatch)
    _wake_until(cid, "external-fetch", items=[_item(urls=[URL])])
    result = run_chain_wake(cid, http_get=http_get)
    assert result["ok"], result
    assert seen == [URL]
    from ada.memory.chain_plan import load_plan

    plan = load_plan(cid, paths=get_paths())
    spans = [fact["span"] for row in plan["queue"][0]["fetches"] for fact in row["spans"]]
    assert SPAN in spans
    assert "invented span" not in spans
    assert all(row["url"] == URL for row in plan["queue"][0]["fetches"])


def test_chain_fetch_does_not_confirm_host(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[bool] = []
    real = __import__("ada.memory.chain_fetch", fromlist=["web_fetch"]).web_fetch

    def spy(url, **kwargs):  # noqa: ANN001
        calls.append(bool(kwargs.get("confirm_host")))
        return real(url, **kwargs)

    monkeypatch.setattr("ada.memory.chain_fetch.web_fetch", spy)
    _write_config(data_root)
    cid, _checkout = _open(tmp_path, monkeypatch)
    host_url = "https://not-on-the-list.example/page"
    _wake_until(cid, "external-fetch", items=[_item(urls=[host_url])])
    run_chain_wake(cid)
    assert calls == [False]
    assert "not-on-the-list.example" not in allowlist_hosts()
    from ada.memory.chain_plan import load_plan

    plan = load_plan(cid, paths=get_paths())
    assert plan["queue"][0].get("fetches") == []


DOCS_URL = "https://developers.google.com/search/docs/appearance/ai-features"
SEARCH_URL = "https://www.google.com/search?q=seo"


def test_is_search_url_allows_docs_and_refuses_a_results_query() -> None:
    assert is_search_url(DOCS_URL) is False
    assert is_search_url("https://developers.google.com/search/docs/fundamentals/ai-optimization-guide") is False
    assert is_search_url(SEARCH_URL) is True
    assert is_search_url("https://google.com/search?q=seo") is True
    assert is_search_url("https://example.com/search?q=seo") is True


def test_chain_fetch_reads_a_docs_url_and_refuses_a_search_query(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "ada.web.fetch._robots_allowed",
        lambda url, ignore_robots=False: (True, "honored"),
    )
    ensure_prefs()
    add_host("developers.google.com")
    docs_span = "Docs span from the guide."
    seen: list[str] = []

    def http_get(url, **kwargs):  # noqa: ANN001
        seen.append(url)
        resp = httpx.Response(
            200,
            text=f"<html><body><p>{docs_span}</p></body></html>",
            headers={"content-type": "text/html"},
            request=httpx.Request("GET", url),
        )
        return resp, url, [url]

    _write_config(data_root)
    cid, _checkout = _open(tmp_path, monkeypatch)
    _wake_until(cid, "external-fetch", items=[_item(urls=[DOCS_URL])])
    result = run_chain_wake(cid, http_get=http_get)
    assert result["ok"], result
    assert seen == [DOCS_URL]
    from ada.memory.chain_plan import load_plan

    plan = load_plan(cid, paths=get_paths())
    spans = [fact["span"] for row in plan["queue"][0]["fetches"] for fact in row["spans"]]
    assert docs_span in spans

    cid2, _checkout2 = _open(tmp_path / "search", monkeypatch)
    _wake_until(cid2, "external-fetch", items=[_item()])
    from ada.memory.chain_plan import save_plan

    queued = load_plan(cid2, paths=get_paths())
    queued["queue"][0]["urls"] = [SEARCH_URL]
    save_plan(queued, paths=get_paths())
    refused = run_chain_wake(cid2, http_get=http_get)
    assert refused["ok"] is False
    assert "search" in str(refused.get("error") or refused.get("denied_reason") or "")
    assert seen == [DOCS_URL]


def _note(root: Path, rel: str, heading: str, body: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# {heading}\n\n{body}\n", encoding="utf-8")


def _patch_repo(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    monkeypatch.setattr("ada.memory.blog_packet.repo_root", lambda: root)


def _bare_checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    bare = tmp_path / "remotes" / "aryanjohari" / "aryan-portfolio.git"
    bare.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "init", "--bare", "-b", "main", str(bare)],
        check=True,
        capture_output=True,
    )
    path = tmp_path / "portfolio"
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "remote", "add", "origin", bare.as_uri()],
        cwd=path,
        check=True,
        capture_output=True,
    )
    monkeypatch.setenv("ADA_PORTFOLIO_CHECKOUT", str(path))
    return path


READER_QUESTION = "Is a cut a service the shop performs?"


class _FactReader:
    def __init__(self, text: str) -> None:
        self.text = text
        self.tools: list[object] = []
        self.prompts: list[str] = []

    def generate(self, *, system: str, contents: list[object], tools: object = None) -> CortexTurn:
        self.tools.append(tools)
        self.prompts.append(_prompt_text(contents))
        return CortexTurn(text=self.text)


def _title_from_prompt(prompt: str) -> str:
    """A sentence already in the passages. The fact's date sentence is not the title."""
    paragraphs = ""
    if "Passages:\n" in prompt:
        paragraphs = prompt.split("Passages:\n", 1)[1]
    elif "Paragraphs:\n" in prompt:
        paragraphs = prompt.split("Paragraphs:\n", 1)[1]
    if paragraphs:
        marker = "\nWrite one title"
        if marker in paragraphs:
            paragraphs = paragraphs.split(marker, 1)[0]
    text = paragraphs.strip()
    for chunk in re.findall(r"[^.!?\n]*[.!?]", text) or ([text] if text else []):
        sentence = " ".join(chunk.split())
        if not sentence or re.search(r"\d{4}-\d{2}-\d{2}", sentence):
            continue
        return sentence
    if "public host" in text.casefold():
        return "What did the public host return?"
    return ""


def _path_that_teaches(prompt: str) -> str:
    """A catalog path whose sentences contain the page, else a note that is not a keyword list."""
    page = ""
    if prompt.startswith("Brief:\n"):
        page = prompt.split("\n", 2)[1].strip()
    path = ""
    first = ""
    sentences = ""
    fallback = ""
    for line in prompt.splitlines():
        if line.startswith("path: "):
            if path and page and page.casefold() in sentences.casefold():
                return path
            path = line.split("path: ", 1)[1].strip()
            if not first:
                first = path
            sentences = ""
        elif line.startswith("sentences: "):
            sentences = line.split("sentences: ", 1)[1]
            if path and "keyword" not in path and not fallback:
                fallback = path
    if path and page and page.casefold() in sentences.casefold():
        return path
    return fallback or first


class _ButtonModel:
    """Page, then paths, then one title. Each call is only that step's prompt."""

    def __init__(
        self,
        replies: list[str] | None = None,
        brief: str | None = None,
        title: str | None = None,
        page: str | None = None,
    ) -> None:
        self.replies = list(replies or [])
        self.brief = brief
        self.title = title
        self.page = page
        self.tools: list[object] = []
        self.prompts: list[str] = []
        self._choose = 0

    def generate(self, *, system: str, contents: list[object], tools: object = None) -> CortexTurn:
        self.tools.append(tools)
        prompt = _prompt_text(contents)
        self.prompts.append(prompt)
        if "Choose one page" in prompt:
            if self.page is not None:
                return CortexTurn(text=self.page)
            if self.brief:
                return CortexTurn(text=self.brief)
            for line in prompt.splitlines():
                if line.startswith("- ") and "(note:" in line:
                    sentence = line[2:].split(" (note:", 1)[0].strip().rstrip(".!?")
                    words = sentence.split()
                    if len(words) > 4:
                        return CortexTurn(text=" ".join(words[:4]))
            return CortexTurn(text=self.brief or "The shop cut")
        if "Return at most 3 paths" in prompt:
            if self.replies:
                text = self.replies[min(self._choose, len(self.replies) - 1)]
                self._choose += 1
                return CortexTurn(text=text)
            return CortexTurn(text=_path_that_teaches(prompt))
        if "Write one title a stranger would search." in prompt:
            return CortexTurn(text=self.title if self.title is not None else _title_from_prompt(prompt))
        return CortexTurn(text=self.brief or "")


def _cut_notes(root: Path) -> dict[str, str]:
    _note(
        root,
        "notes/a-cut.md",
        "A cut",
        "A cut is a service the shop performs.\n\n"
        "The shop keeps a second sentence about the cut.\n\n"
        "# Later\n\n"
        "This extra line is only in the file and must stay out of the prompt.",
    )
    _note(root, "notes/b-shop.md", "Shop cut", "A beard trim is different.")
    _note(root, "notes/c-best-seo-keywords.md", "Best seo keywords", "A keyword list is not a page.")
    return {
        "sentence": "A cut is a service the shop performs.",
        "note": "notes/a-cut.md",
    }


def test_publish_button_writes_a_reader_question_from_the_fact_and_notes(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ada.hud.chain_form import publish_one_page
    from ada.memory.campaign_page import read_page

    root = tmp_path / "notes-repo"
    cut = _cut_notes(root)
    _patch_repo(monkeypatch, root)

    def _boom(*_args: object, **_kwargs: object) -> list[str]:
        raise AssertionError("the button used the filename word score")

    monkeypatch.setattr("ada.memory.chain_fetch.local_markdown_files", _boom)
    beard = "A beard trim is different."
    _write_config(data_root, folders=["notes"])
    before = get_paths().portfolio_chain_yaml.read_text(encoding="utf-8")
    _bare_checkout(tmp_path, monkeypatch)
    html = (Path(__file__).resolve().parents[1] / "src/ada/hud/templates/index.html").read_text(
        encoding="utf-8"
    )
    script = (Path(__file__).resolve().parents[1] / "src/ada/hud/static/js/chain.js").read_text(
        encoding="utf-8"
    )
    assert "Add a source" not in html
    assert "chain-source" not in html
    assert "Publish one page" in html
    assert "sourcesFromForm" not in script
    assert 'post("/api/chain/page", {})' in script
    reader = _ButtonModel(title="How a shop cut works")
    writer = _PageModel()
    result = publish_one_page(model=reader, draft_model=writer)
    assert result["ok"], result
    title = result["published"][0]["question"]
    assert title == "How a shop cut works"
    assert title != "What is a cut?"
    assert title != "Where is this work published?"
    assert title != cut["sentence"]
    assert result["published"][0]["source"] == cut["note"]
    assert reader.tools == [[], []]
    assert all(call == [] for call in reader.tools)
    assert "Choose one page" not in "\n".join(reader.prompts)
    assert "Return at most 3 paths" in reader.prompts[0]
    assert "Do not search the web." in reader.prompts[0]
    assert cut["sentence"] in reader.prompts[0]
    assert "notes/a-cut.md" in reader.prompts[0]
    assert "must stay out of the prompt" not in reader.prompts[0]
    assert reader.prompts[0] not in reader.prompts[1]
    assert "Passages:" in reader.prompts[1]
    assert "Write one title a stranger would search." in reader.prompts[1]
    assert (
        "The title may use the words a stranger would type, and it does not have to reuse the wording of the passages."
        in reader.prompts[1]
    )
    assert (
        "The title still has to name what those passages say, and must not promise a guide, a definition, or a procedure the passages do not contain."
        in reader.prompts[1]
    )
    assert beard not in reader.prompts[1]
    assert "must stay out of the prompt" not in reader.prompts[1]
    plan = load_plan(result["campaign_id"], paths=get_paths())
    assert plan is not None
    assert [item["question"] for item in plan["queue"]] == [title]
    assert len(plan["queue"]) == 1
    assert plan["queue"][0]["page"] == cut["note"]
    assert plan["queue"][0]["page"] != cut["sentence"]
    assert beard not in [item["question"] for item in plan["queue"]]
    local = plan["queue"][0]["local_files"]
    assert local == ["notes/a-cut.md"]
    assert len(local) <= 3
    assert "notes/c-best-seo-keywords.md" not in local
    assert "notes/b-shop.md" not in local
    notes = "\n".join((root / rel).read_text(encoding="utf-8") for rel in local)
    assert question_adds_fact(title, f"{cut['sentence']}\n{notes}") is False
    assert "Brief:" in writer.prompts[0]
    assert "Excerpts:" in writer.prompts[0]
    assert "must stay out of the prompt" not in writer.prompts[0]
    assert reader.prompts[1] not in writer.prompts[0]
    assert "The live homepage URL is a citation inside a claim. It is not the subject of the post." not in writer.prompts[0]
    assert "Headings a reader can scan." not in writer.prompts[0]
    assert "A list only for steps the reader must follow." not in writer.prompts[0]
    assert "A table only for a comparison." not in writer.prompts[0]
    assert (
        "Write only the post those passages can support, in your own words, as a few plain paragraphs a person would read."
        in writer.prompts[0]
    )
    assert "The first paragraph is the useful fact, not a repeat of the title." in writer.prompts[0]
    assert (
        "A heading or a list appears only when the passages themselves are a sequence or a comparison."
        in writer.prompts[0]
    )
    page = read_page(result["campaign_id"])
    assert page is not None
    assert page["question"] == title
    assert page["packet"]
    assert all(fact["source"] in set(local) or str(fact["source"]).startswith("http") for fact in page["packet"])
    assert get_paths().portfolio_chain_yaml.read_text(encoding="utf-8") == before


def test_button_without_a_reader_model_uses_a_sentence_already_written(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ada.hud.chain_form import publish_one_page

    root = tmp_path / "notes-repo"
    cut = _cut_notes(root)
    _patch_repo(monkeypatch, root)
    _write_config(data_root, folders=["notes"])
    _bare_checkout(tmp_path, monkeypatch)
    result = publish_one_page(draft_model=_PageModel())
    assert result["ok"], result
    title = result["published"][0]["question"]
    assert title == cut["sentence"]
    plan = load_plan(result["campaign_id"], paths=get_paths())
    assert plan["queue"][0]["question"] == title
    assert plan["queue"][0]["card"] == cut["note"]
    assert plan["queue"][0]["page"] != cut["sentence"]
    assert plan["queue"][0]["local_files"] == ["notes/a-cut.md"]
    assert "A cut is a service the shop performs." in plan["queue"][0]["paragraphs"]


def test_button_denies_when_the_fact_and_notes_have_no_sentence(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ada.hud.chain_form import publish_one_page

    root = tmp_path / "notes-repo"
    _note(root, "notes/a-cut.md", "A cut", "")
    _patch_repo(monkeypatch, root)
    _write_config(data_root, folders=["notes"])
    _bare_checkout(tmp_path, monkeypatch)
    result = publish_one_page(draft_model=_PageModel())
    assert result["ok"] is False
    assert "sentence" in result["result_line"]
    assert result.get("published") in (None, [])


def test_button_keeps_a_search_word_and_refuses_a_yaml_question_url_or_host(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ada.hud.chain_form import publish_one_page

    root = tmp_path / "notes-repo"
    frame = "Which steps does this cut own?"
    _note(
        root,
        "notes/a-cut.md",
        "A cut",
        f"## 1. Question\n\n{frame}\n\nA cut is a service the shop performs.\n",
    )
    _patch_repo(monkeypatch, root)
    _write_config(data_root, folders=["notes"])
    _bare_checkout(tmp_path, monkeypatch)
    copied = publish_one_page(
        model=_ButtonModel(title=frame),
        draft_model=_PageModel(),
    )
    assert copied["ok"] is False
    assert "YAML" in copied["result_line"]
    assert copied.get("published") in (None, [])
    linked = publish_one_page(
        model=_ButtonModel(title="See the cut at https://evil.example/shop"),
        draft_model=_PageModel(),
    )
    assert linked["ok"] is False
    assert linked.get("published") in (None, [])
    hosted = publish_one_page(
        model=_ButtonModel(title="The cut is on evil.example"),
        draft_model=_PageModel(),
    )
    assert hosted["ok"] is False
    assert hosted.get("published") in (None, [])
    invented = publish_one_page(
        model=_ButtonModel(title="How did the invented zythum launch?"),
        draft_model=_PageModel(),
    )
    assert invented["ok"], invented
    assert invented["published"][0]["question"] == "How did the invented zythum launch?"
    again = publish_one_page(
        model=_ButtonModel(title="How did the invented zythum launch?"),
        draft_model=_PageModel(),
    )
    assert again["ok"] is False
    assert "published" in again["result_line"]
    assert again.get("published") in (None, [])


def test_catalog_row_is_a_path_heading_and_sentences_already_in_the_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ada.memory.chain_fetch import research_catalog

    root = tmp_path / "notes-repo"
    body = (
        "On 2026-09-29 the public host returned HTTP 200 HTML.\n\n"
        "The public host returned that HTML.\n\n"
        "This extra line is only in the file and must stay out of the row.\n"
    )
    _note(root, "docs/research/04_pipeline_steps.md", "Pipeline steps", body)
    _note(root, "docs/research/.hidden/skip.md", "Hidden", "A hidden note stays out.")
    _note(root, "docs/research/node_modules/skip.md", "Modules", "A module note stays out.")
    _note(root, "docs/research/__pycache__/skip.md", "Cache", "A cache note stays out.")
    _note(root, "docs/research/venv/skip.md", "Venv", "A venv note stays out.")
    _patch_repo(monkeypatch, root)

    def _boom(*_args: object, **_kwargs: object) -> list[str]:
        raise AssertionError("the catalog used the filename word score")

    monkeypatch.setattr("ada.memory.chain_fetch.local_markdown_files", _boom)
    rows = research_catalog("docs/research/04_pipeline_steps.md")
    assert len(rows) == 1
    row = rows[0]
    assert set(row) == {"path", "heading", "sentences"}
    assert row["path"] == "docs/research/04_pipeline_steps.md"
    assert row["heading"] == "Pipeline steps"
    assert row["sentences"] == [
        "On 2026-09-29 the public host returned HTTP 200 HTML.",
        "The public host returned that HTML.",
    ]
    file_text = (root / row["path"]).read_text(encoding="utf-8")
    assert all(sentence in file_text for sentence in row["sentences"])
    assert "must stay out of the row" not in " ".join(row["sentences"])


def test_chooser_keeps_the_named_source_and_drops_the_dated_archive(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ada.memory.chain_plan import plan_one_page

    fact = "On 2026-09-29 the public host returned HTTP 200 HTML."
    source = "docs/research/04_pipeline_steps.md"
    archive = "docs/research/_archive/nz-business-2026-09/ARCHIVE.md"
    root = tmp_path / "notes-repo"
    _note(root, source, "Pipeline steps", fact)
    _note(
        root,
        archive,
        "Archive 2026-09",
        "The nz business archive is a closed folder.",
    )
    _patch_repo(monkeypatch, root)

    def _boom(*_args: object, **_kwargs: object) -> list[str]:
        raise AssertionError("the chooser used the filename word score")

    monkeypatch.setattr("ada.memory.chain_fetch.local_markdown_files", _boom)
    reader = _ButtonModel(replies=[archive, source])
    prepared = plan_one_page(
        _page_config(folders=["docs/research"]),
        model=reader,
    )
    assert prepared["ok"], prepared
    files = prepared["items"][0]["local_files"]
    assert prepared["items"][0]["card"] == source
    assert source in files
    assert archive not in files
    assert len(files) <= 3
    assert reader.tools
    assert all(call == [] for call in reader.tools)
    notes = [prompt for prompt in reader.prompts if "Return at most 3 paths" in prompt]
    title = reader.prompts[-1]
    assert notes
    assert notes[0] not in title
    assert "Write a few plain sentences" not in title
    assert fact in title
    assert "heading: Archive 2026-09" in notes[0]
    assert "The nz business archive is a closed folder." in notes[0]
    assert "must stay out" not in notes[0]


def test_brief_may_say_aim_or_september(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ada.hud.chain_form import publish_one_page

    root = tmp_path / "notes-repo"
    _note(
        root,
        "notes/a-cut.md",
        "A cut",
        "The aim in September is who this page is for.\n\n"
        "A cut is a service the shop performs.\n",
    )
    _patch_repo(monkeypatch, root)
    _write_config(data_root, folders=["notes"])
    before = get_paths().portfolio_chain_yaml.read_text(encoding="utf-8")
    _bare_checkout(tmp_path, monkeypatch)
    result = publish_one_page(
        model=_ButtonModel(title="How a shop cut works"),
        draft_model=_PageModel(),
    )
    assert result["ok"], result
    assert "word" not in result["result_line"]
    plan = load_plan(result["campaign_id"], paths=get_paths())
    stored = plan["queue"][0]["brief"]
    assert "aim" in stored
    assert "September" in stored
    assert stored != result["published"][0]["question"]
    assert get_paths().portfolio_chain_yaml.read_text(encoding="utf-8") == before


def test_date_sentence_is_not_the_title_when_a_model_is_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ada.memory.chain_plan import plan_one_page

    fact = "On 2026-09-29 the public host returned HTTP 200 HTML."
    source = "docs/research/04_pipeline_steps.md"
    root = tmp_path / "notes-repo"
    _note(root, source, "Pipeline steps", fact)
    _patch_repo(monkeypatch, root)
    kept = plan_one_page(
        _page_config(folders=["docs/research"]),
        model=_ButtonModel(title="What did the public host return?"),
    )
    assert kept["ok"], kept
    title = kept["items"][0]["question"]
    assert title == "What did the public host return?"
    assert title != "Where is this work published?"
    assert title != fact
    assert "2026-09-29" not in title
    dated = plan_one_page(
        _page_config(folders=["docs/research"]),
        model=_ButtonModel(title=fact),
    )
    assert dated["ok"] is False
    assert "date" in dated["deny"]
    frame = "Which steps does this host own?"
    _note(root, source, "Pipeline steps", f"## 1. Question\n\n{frame}\n\n{fact}\n")
    denied = plan_one_page(
        _page_config(folders=["docs/research"]),
        model=_ButtonModel(title=fact),
    )
    assert denied["ok"] is False
    assert "date" in denied["deny"]
    assert denied["items"] == []


def test_opened_paragraph_keeps_a_buried_fact_and_drops_the_dated_archive(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ada.memory.chain_plan import plan_one_page

    fact = "On 2026-09-29 the public host returned HTTP 200 HTML."
    source = "docs/research/04_pipeline_steps.md"
    archive = "docs/research/_archive/nz-business-2026-09/ARCHIVE.md"
    fourth = "docs/research/05_other.md"
    extra = "This extra line is only in the file and must stay out of the paragraph."
    root = tmp_path / "notes-repo"
    _note(
        root,
        source,
        "Pipeline steps",
        "The first catalog sentence is about a pipeline.\n\n"
        "The second catalog sentence is about a step.\n\n"
        f"{fact}\n\n"
        "# Later\n\n"
        f"{extra}\n",
    )
    _note(root, archive, "Archive 2026-09", "The nz business archive is a closed folder.")
    _note(root, fourth, "Other", f"A lead in.\n\nA second lead.\n\n{fact}\n")
    _patch_repo(monkeypatch, root)

    def _boom(*_args: object, **_kwargs: object) -> list[str]:
        raise AssertionError("the chooser used the filename word score")

    monkeypatch.setattr("ada.memory.chain_fetch.local_markdown_files", _boom)
    reader = _ButtonModel(replies=[f"{archive}\n{source}"])
    prepared = plan_one_page(
        _page_config(folders=["docs/research"]),
        model=reader,
    )
    assert prepared["ok"], prepared
    item = prepared["items"][0]
    assert item["card"] == source
    assert item["local_files"] == [source]
    assert archive not in item["local_files"]
    assert fourth not in item["local_files"]
    assert len(item["local_files"]) <= 3
    note = item["notes"][0]
    assert "about a pipeline" in note["paragraph"]
    assert extra not in note["paragraph"]
    assert "about a pipeline" in note["section"]
    assert extra not in note["section"]
    assert "# Later" not in note["section"]
    assert note["section"] == note["paragraph"]
    assert item["question"] != fact
    _write_config(data_root)
    cid, _checkout = _open(tmp_path / "camp", monkeypatch)
    _wake_until(cid, "draft", items=[item])
    writer = _PageModel()
    drafted = run_chain_wake(cid, model=writer)
    assert drafted["ok"], drafted
    prompt = writer.prompts[0]
    assert "Brief:" in prompt
    assert "about a pipeline" in prompt
    assert extra not in prompt
    assert "# Later" not in prompt
    file_text = (root / source).read_text(encoding="utf-8")
    assert file_text not in prompt
    assert len(writer.prompts) == 1


HOMEPAGE_FACT = (
    "The GitHub homepage field for aryanjohari/aryan-portfolio, read 2026-09-29, "
    "is https://aryan-portfolio-one-kappa.vercel.app."
)
HOMEPAGE_URL = "https://aryan-portfolio-one-kappa.vercel.app"
PIPELINE = "docs/research/04_pipeline_steps.md"
WEEKLY = "docs/research/11_one_site_weekly.md"


def _homepage_card(root: Path) -> None:
    """The deploy section, with the homepage passage first. Nothing is invented."""
    body = "\n\n".join(
        [
            (
                "**FEASIBLE.**\n"
                "The GitHub homepage field for `aryanjohari/aryan-portfolio`, "
                f"read 2026-09-29, is `{HOMEPAGE_URL}`. A fetch of that URL on 2026-09-29 "
                "returned HTTP 200 and `Content-Type: text/html`. The README and the ship "
                "checklist do not name this hostname."
            ),
            (
                "**FEASIBLE.**\n"
                "Repository `aryanjohari/aryan-portfolio`, README, section "
                '"Vercel deployment", https://github.com/aryanjohari/aryan-portfolio/blob/main/README.md, '
                "accessed 2026-09-29. The site is that Next.js repo, built on Vercel. On each deploy, "
                "`prebuild` runs `fetch:projects` and `build:guide-context`. The same README says "
                "`npm run build` runs `fetch:projects` via prebuild, then `next build`."
            ),
            (
                "**FEASIBLE.**\n"
                "Repository `aryanjohari/aryan-portfolio`, \"Ship checklist\", "
                "https://github.com/aryanjohari/aryan-portfolio/blob/main/docs/ship-checklist.md, "
                "accessed 2026-09-29. The file is pre-deploy verification: lint, build, and smoke "
                'tests of the routes it names. Under "Explicitly deferred (v2)" it lists "ADA blogs". '
                "This card does not add `/blog`."
            ),
            (
                "**HUNCH.** Those two files say the prebuild runs on each deploy. They do not name "
                "the git event that starts a Vercel deploy."
            ),
            (
                "**UNKNOWN.** Which path on the origin the one URL uses. This card does not add a route."
            ),
            "**UNKNOWN.** Whether any queue URL is indexed is UNKNOWN.",
        ]
    )
    _note(root, PIPELINE, "Pipeline steps", body)
    _note(root, WEEKLY, "One site weekly", "A weekly note stays a different card.")


def _homepage_config(**extra: object) -> dict:
    doc = _page_config(folders=["docs/research"])
    doc.update(extra)
    return doc


def test_stored_section_keeps_the_homepage_url_whole(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ada.memory.chain_fetch import citation_urls
    from ada.memory.chain_plan import plan_one_page

    root = tmp_path / "notes-repo"
    _homepage_card(root)
    _patch_repo(monkeypatch, root)
    dated_sentence = (
        "The GitHub homepage field for `aryanjohari/aryan-portfolio`, read 2026-09-29, "
        f"is `{HOMEPAGE_URL}`."
    )
    prepared = plan_one_page(
        _homepage_config(),
        model=_ButtonModel(replies=[f"{WEEKLY}\n{PIPELINE}"], title="The GitHub homepage field"),
    )
    assert prepared["ok"], prepared
    assert prepared["items"][0]["question"] == "The GitHub homepage field"
    assert prepared["items"][0]["question"] != "Where is this work published?"
    assert prepared["items"][0]["question"] != HOMEPAGE_FACT
    denied = plan_one_page(
        _homepage_config(),
        model=_ButtonModel(replies=[f"{WEEKLY}\n{PIPELINE}"], title=dated_sentence),
    )
    assert denied["ok"] is False
    assert "date" in denied["deny"]
    refused_path = plan_one_page(
        _homepage_config(),
        model=_ButtonModel(
            replies=[f"{WEEKLY}\n{PIPELINE}"],
            title="What path on the origin does the URL use?",
        ),
    )
    assert refused_path["ok"] is False
    prepared = plan_one_page(
        _homepage_config(),
        model=_ButtonModel(replies=[f"{WEEKLY}\n{PIPELINE}"], title="The GitHub homepage field"),
    )
    assert prepared["ok"], prepared
    item = prepared["items"][0]
    assert item["question"] == "The GitHub homepage field"
    assert item["question"] != "Where is this work published?"
    assert item["question"] != "What path on the origin does the URL use?"
    assert item["question"] != HOMEPAGE_FACT
    assert "indexed is UNKNOWN" not in item["question"]
    assert "2026-09-29" not in item["question"]
    assert item["local_files"] == [PIPELINE]
    assert WEEKLY not in item["local_files"]
    assert len(item["local_files"]) <= 3
    section = item["notes"][0]["section"]
    assert (
        "The GitHub homepage field for `aryanjohari/aryan-portfolio`, read 2026-09-29, "
        f"is `{HOMEPAGE_URL}`."
    ) in section
    assert "returned HTTP 200" in section
    assert "prebuild" in section
    assert "ADA blogs" in section
    homepage_only = (
        "The GitHub homepage field for `aryanjohari/aryan-portfolio`, read 2026-09-29, "
        f"is `{HOMEPAGE_URL}`. A fetch of that URL on 2026-09-29 returned HTTP 200 "
        "and `Content-Type: text/html`. The README and the ship checklist do not name this hostname."
    )
    assert section.strip() != homepage_only
    assert "Which path on the origin the one URL uses." not in section
    assert "Whether any queue URL is indexed is UNKNOWN." not in section
    assert "indexed is UNKNOWN" not in section
    assert HOMEPAGE_URL in section
    assert "https://aryan-portfolio-one-kappa." not in section.replace(HOMEPAGE_URL, "")
    from ada.memory.chain_plan import _sentences_in_line

    homepage = (
        "The GitHub homepage field for `aryanjohari/aryan-portfolio`, read 2026-09-29, "
        f"is `{HOMEPAGE_URL}`."
    )
    split = _sentences_in_line(homepage, homepage)
    assert any(HOMEPAGE_URL in sentence for sentence in split)
    assert not any(sentence.endswith("kappa.") for sentence in split)
    assert HOMEPAGE_URL in citation_urls(section)
    assert all("indexed is UNKNOWN" not in str(row.get("section") or "") for row in item["notes"])
    assert all(
        "Which path on the origin the one URL uses." not in str(row.get("section") or "")
        for row in item["notes"]
    )


def test_draft_prompt_contains_the_homepage_paragraph_not_the_unknown_path(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ada.memory.chain_plan import plan_one_page

    root = tmp_path / "notes-repo"
    _homepage_card(root)
    _patch_repo(monkeypatch, root)
    prepared = plan_one_page(
        _homepage_config(),
        model=_ButtonModel(replies=[f"{WEEKLY}\n{PIPELINE}"], title="The GitHub homepage field"),
    )
    assert prepared["ok"], prepared
    item = prepared["items"][0]
    assert item["question"] == "The GitHub homepage field"
    assert item["question"] != "Where is this work published?"
    paragraph = item["notes"][0]["paragraph"]
    assert "returned HTTP 200" in paragraph
    assert "prebuild" in paragraph
    assert "Which path on the origin the one URL uses." not in paragraph
    _write_config(data_root)
    cid, _checkout = _open(tmp_path / "camp", monkeypatch)
    _wake_until(cid, "draft", items=[item])
    writer = _PageModel()
    drafted = run_chain_wake(cid, model=writer)
    assert drafted["ok"], drafted
    prompt = writer.prompts[0]
    assert "Brief:" in prompt
    assert "Idea:" in prompt
    assert "The GitHub homepage field" in prompt
    assert "Where is this work published?" not in prompt
    assert paragraph in prompt
    assert HOMEPAGE_URL in prompt.split("URLs:\n", 1)[1]
    assert "Which path on the origin the one URL uses." not in prompt
    assert "Whether any queue URL is indexed is UNKNOWN." not in prompt
    assert (repo_root() / PIPELINE).read_text(encoding="utf-8") not in prompt


def test_url_anchor_fails_and_a_name_from_the_paragraph_passes() -> None:
    from ada.memory.chain_critic import critic_checks

    notes = (
        "**FEASIBLE.** The GitHub homepage field for `aryanjohari/aryan-portfolio`, "
        f"read 2026-09-29, is `{HOMEPAGE_URL}`. A fetch of that URL on 2026-09-29 "
        "returned HTTP 200 and `Content-Type: text/html`."
    )
    unknown = (
        "**UNKNOWN.** Which path on the origin the one URL uses. "
        "This card does not add a route."
    )
    source = "\n".join(
        [
            "## 5. What deploy writes and what the receipt is",
            "",
            notes,
            "",
            unknown,
            "",
        ]
    )
    question = "Where is this work published?"
    slug = blog_slug(question)

    def page(body: str) -> str:
        return _chain_markdown(question, body)

    shared = {
        "question": question,
        "slug": slug,
        "packet": [],
        "source_text": source,
        "cta": None,
        "published": set(),
        "staged": None,
        "staged_bytes": None,
        "notes": notes,
    }
    raw = critic_checks(
        page(
            "\n".join(
                [
                    f"This work is published at [{HOMEPAGE_URL}]({HOMEPAGE_URL}).",
                    "",
                    "## Host",
                    "",
                    "A fetch of that URL returned HTTP 200 HTML.",
                ]
            )
        ),
        **shared,
    )
    assert "anchor" in raw
    named = critic_checks(
        page(
            "\n".join(
                [
                    f"This work is published at the [GitHub homepage field]({HOMEPAGE_URL}).",
                    "",
                    "## Host",
                    "",
                    "A fetch of that URL returned HTTP 200 HTML.",
                ]
            )
        ),
        **shared,
    )
    assert "anchor" not in named
    assert "unknown" not in named
    assert "card" not in named
    answered = critic_checks(
        page(
            "\n".join(
                [
                    "This work is published on the path on the origin the URL uses.",
                    "",
                    "## Host",
                    "",
                    "A fetch of that URL returned HTTP 200 HTML.",
                ]
            )
        ),
        **shared,
    )
    assert "unknown" in answered
    receipt = critic_checks(
        page(
            "\n".join(
                [
                    "This work is published at the GitHub homepage field.",
                    "",
                    "## Host",
                    "",
                    unknown,
                ]
            )
        ),
        **shared,
    )
    assert "card" in receipt


def test_backtick_url_is_cited_and_an_allowlisted_markdown_link_is_fetched(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ada.memory.chain_librarian import apply_librarian

    monkeypatch.setattr(
        "ada.web.fetch._robots_allowed",
        lambda url, ignore_robots=False: (True, "honored"),
    )
    ensure_prefs()
    add_host("github.com")
    prefs = get_paths().prefs_yaml.read_text(encoding="utf-8")
    github = "https://github.com/aryanjohari/aryan-portfolio/blob/main/README.md"
    checklist = "https://github.com/aryanjohari/aryan-portfolio/blob/main/docs/ship-checklist.md"
    google = "https://developers.google.com/search/docs/fundamentals/seo-starter-guide"
    hop = "https://example.com/from-the-fetched-page"
    root = tmp_path / "notes-repo"
    _note(
        root,
        PIPELINE,
        "Pipeline steps",
        "\n".join(
            [
                "## 5. What deploy writes and what the receipt is",
                "",
                (
                    "The GitHub homepage field for `aryanjohari/aryan-portfolio`, read 2026-09-29, "
                    f"is `{HOMEPAGE_URL}`. A fetch of that URL on 2026-09-29 returned HTTP 200 "
                    "and `Content-Type: text/html`."
                ),
                "",
                f"[README]({github})",
                "",
                f"[Ship checklist]({checklist})",
                "",
                f"[Starter guide]({google})",
                "",
                "# Later",
                "",
                "Whether any queue URL is indexed is UNKNOWN.",
            ]
        ),
    )
    _note(root, "docs/research/a.md", "A", "A first extra file stays unused.")
    _note(root, "docs/research/b.md", "B", "A second extra file stays unused.")
    _note(root, "docs/research/c.md", "C", "A fourth file stays unused.")
    _patch_repo(monkeypatch, root)
    section = (root / PIPELINE).read_text(encoding="utf-8").split("# Later", 1)[0]
    seen: list[str] = []

    def http_get(url, **kwargs):  # noqa: ANN001
        seen.append(url)
        resp = httpx.Response(
            200,
            text=f'<html><body><p>Readme</p><a href="{hop}">elsewhere</a></body></html>',
            headers={"content-type": "text/html"},
            request=httpx.Request("GET", url),
        )
        return resp, url, [url]

    _write_config(data_root)
    cid, _checkout = _open(tmp_path / "camp", monkeypatch)
    _wake_until(
        cid,
        "external-fetch",
        items=[
            _item(
                fact=HOMEPAGE_FACT,
                question="What is the GitHub homepage field?",
                source=PIPELINE,
                local_files=[PIPELINE, "docs/research/a.md", "docs/research/b.md", "docs/research/c.md"],
                brief="The page says where the work is published.",
                notes=[
                    {
                        "path": PIPELINE,
                        "heading": "What deploy writes and what the receipt is",
                        "sentences": [HOMEPAGE_FACT],
                        "section": section,
                    }
                ],
            )
        ],
    )
    fetched = run_chain_wake(cid, http_get=http_get)
    assert fetched["ok"], fetched
    plan = load_plan(cid, paths=get_paths())
    assert plan["queue"][0]["local_files"] == [
        PIPELINE,
        "docs/research/a.md",
        "docs/research/b.md",
    ]
    assert "docs/research/c.md" not in plan["queue"][0]["local_files"]
    assert seen == [github, checklist]
    assert HOMEPAGE_URL not in seen
    assert google not in seen
    assert hop not in seen
    assert get_paths().prefs_yaml.read_text(encoding="utf-8") == prefs
    assert "developers.google.com" not in allowlist_hosts()
    assert "example.com" not in allowlist_hosts()
    page = (
        f"The work is published at {HOMEPAGE_URL}.\n\n"
        "## Host\n\n"
        "That page is the public copy of this work.\n"
    )
    writer = _PageModel(page)
    _wake_until(cid, "draft")
    drafted = run_chain_wake(cid, model=writer)
    assert drafted["ok"], drafted
    prompt = writer.prompts[0]
    assert "Brief:" in prompt
    assert "Section:" in prompt
    assert HOMEPAGE_URL in prompt.split("URLs:\n", 1)[1]
    assert "Whether any queue URL is indexed is UNKNOWN." not in prompt
    assert (root / PIPELINE).read_text(encoding="utf-8") not in prompt
    linked = run_chain_wake(cid)
    assert linked["ok"], linked
    text = (data_root / latest_receipt(cid, "draft", outcome="ok")["paths"][0]).read_text(
        encoding="utf-8"
    )
    assert f"[GitHub homepage field]({HOMEPAGE_URL})" in text
    assert f"[{HOMEPAGE_URL}]({HOMEPAGE_URL})" not in text
    assert "https://evil.example" not in text
    rewritten = apply_librarian(
        f"The public copy is `{HOMEPAGE_URL}` for a reader.\n",
        posts=[],
        urls=[],
        cta=None,
        spans=[],
        packet=[],
        source_text=section,
    )
    assert f"[GitHub homepage field]({HOMEPAGE_URL})" in rewritten
    assert f"[{HOMEPAGE_URL}]({HOMEPAGE_URL})" not in rewritten
    invented = apply_librarian(
        "The public copy is https://evil.example/not-in-the-section.\n",
        posts=[],
        urls=[],
        cta=None,
        spans=[],
        packet=[],
        source_text=section,
    )
    assert "https://evil.example" not in invented or "](https://evil.example" not in invented

    search_root = tmp_path / "search-repo"
    _note(
        search_root,
        "notes/quill.md",
        "Quill notes",
        "The quill note names a query.\n\n[results](https://www.google.com/search?q=quill)",
    )
    _patch_repo(monkeypatch, search_root)
    cid2, _checkout2 = _open(tmp_path / "search", monkeypatch)
    _wake_until(
        cid2,
        "external-fetch",
        items=[
            _item(
                fact="A quill marks the topic.",
                question="What is a quill?",
                source="notes/quill.md",
                local_files=["notes/quill.md"],
                notes=[
                    {
                        "path": "notes/quill.md",
                        "heading": "Quill notes",
                        "section": (search_root / "notes/quill.md").read_text(encoding="utf-8"),
                    }
                ],
            )
        ],
    )
    before = len(seen)
    refused = run_chain_wake(cid2, http_get=http_get)
    assert refused["ok"] is False
    assert "search" in str(refused.get("denied_reason") or refused.get("error") or "")
    assert len(seen) == before
    assert get_paths().prefs_yaml.read_text(encoding="utf-8") == prefs


def test_draft_prompt_is_the_brief_and_the_excerpts(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    extra = "This extra line is only in the file and must stay out of the prompt."
    fact = "On 2026-09-29 the public host returned HTTP 200 HTML."
    root = tmp_path / "notes-repo"
    _note(
        root,
        "docs/research/04_pipeline_steps.md",
        "Pipeline steps",
        f"{fact}\n\nThe public host returned that HTML.\n\n{extra}",
    )
    _patch_repo(monkeypatch, root)
    _write_config(data_root)
    cid, _checkout = _open(tmp_path / "camp", monkeypatch)
    _wake_until(
        cid,
        "draft",
        items=[
            _item(
                fact=fact,
                question="What did the public host return?",
                source="docs/research/04_pipeline_steps.md",
                local_files=["docs/research/04_pipeline_steps.md"],
                brief="The public host returned HTTP 200 HTML.",
                notes=[
                    {
                        "path": "docs/research/04_pipeline_steps.md",
                        "heading": "Pipeline steps",
                        "sentences": [
                            fact,
                            "The public host returned that HTML.",
                        ],
                    }
                ],
            )
        ],
    )
    writer = _PageModel()
    drafted = run_chain_wake(cid, model=writer)
    assert drafted["ok"], drafted
    prompt = writer.prompts[0]
    assert "Brief:" in prompt
    assert "The public host returned HTTP 200 HTML." in prompt
    assert "Excerpts:" in prompt
    assert fact in prompt
    assert extra not in prompt
    assert "Spans:\n" not in prompt
    file_text = (root / "docs/research/04_pipeline_steps.md").read_text(encoding="utf-8")
    assert file_text not in prompt


def test_fetch_uses_the_file_list_stored_at_plan(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "notes-repo"
    for name in ("a-quill", "b-quill", "c-quill", "d-quill"):
        _note(root, f"notes/{name}.md", "Quill notes", f"The {name} note is about a quill.")
    _patch_repo(monkeypatch, root)
    _write_config(data_root)
    cid, _checkout = _open(tmp_path / "camp", monkeypatch)
    stored = [
        "notes/d-quill.md",
        "notes/c-quill.md",
        "notes/b-quill.md",
        "notes/a-quill.md",
    ]
    _wake_until(
        cid,
        "external-fetch",
        items=[
            _item(
                fact="A quill marks the topic.",
                question="What is a quill?",
                source="notes/a-quill.md",
                local_files=stored,
            )
        ],
    )
    plan = load_plan(cid, paths=get_paths())
    assert plan["queue"][0]["local_files"] == stored[:3]
    plan["queue"][0]["local_files"] = stored
    save_plan(plan, paths=get_paths())

    def _boom(*_args: object, **_kwargs: object) -> list[str]:
        raise AssertionError("fetch chose a different file list")

    monkeypatch.setattr("ada.memory.chain_fetch.local_markdown_files", _boom)
    result = run_chain_wake(cid)
    assert result["ok"], result
    plan = load_plan(cid, paths=get_paths())
    assert plan["queue"][0]["local_files"] == stored[:3]
    assert len(plan["queue"][0]["local_files"]) <= 3
    assert "notes/a-quill.md" not in plan["queue"][0]["local_files"]


def test_second_press_replaces_an_unpushed_draft_and_leaves_a_pushed_slug(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ada.hud import chain_form

    root = tmp_path / "notes-repo"
    _note(
        root,
        "notes/a-cut.md",
        "A cut",
        "A cut is a service the shop performs.\n\nThe shop keeps a second sentence about the cut.\n",
    )
    _patch_repo(monkeypatch, root)
    _write_config(data_root, folders=["notes"])
    checkout = _bare_checkout(tmp_path, monkeypatch)
    reader = _ButtonModel()
    pages = {"n": 0}

    class _Marked(_PageModel):
        def generate(self, *, system: str, contents: list[object], tools: object = None) -> CortexTurn:
            pages["n"] += 1
            turn = super().generate(system=system, contents=contents, tools=tools)
            text = str(turn.text or "")
            last = self.prompts[-1] if self.prompts else ""
            if "Spans:\n" in last or "Excerpts:\n" in last:
                text = text.rstrip() + f"\n\nPass {pages['n']} keeps the shop cut.\n"
            return CortexTurn(text=text)

    real = chain_form.run_chain_wake
    seen = {"critic": 0}

    def _fail_first_critic(campaign_id: str, **kwargs: object) -> dict:
        loop = get_loop(campaign_id)
        if loop and loop.get("current_stage") == "critic" and seen["critic"] == 0:
            seen["critic"] = 1
            return {
                "ok": False,
                "outcome": "fail",
                "checks": ["direct-answer"],
                "denied_reason": "direct-answer",
            }
        return real(campaign_id, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(chain_form, "run_chain_wake", _fail_first_critic)
    writer = _Marked()
    first = chain_form.publish_one_page(model=reader, draft_model=writer)
    assert first["ok"] is False
    assert seen["critic"] == 1
    draft = data_root / first["draft_path"]
    assert draft.is_file()
    original = draft.read_text(encoding="utf-8")
    assert "Pass" in original
    monkeypatch.setattr(chain_form, "run_chain_wake", real)
    second = chain_form.publish_one_page(model=reader, draft_model=writer)
    assert second["ok"], second
    assert second["draft_path"] == first["draft_path"]
    replaced = draft.read_text(encoding="utf-8")
    assert replaced != original
    assert "Pass" in replaced

    pushed = draft.read_bytes()
    blog = checkout / "content" / "blog"
    for path in blog.glob("*.md"):
        path.unlink()
    held = chain_form.publish_one_page(model=reader, draft_model=writer)
    assert held["ok"] is False
    assert "published" in held["result_line"]
    assert draft.read_bytes() == pushed


def test_fetch_selects_at_most_three_local_files(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "notes-repo"
    for name in ("a-quill", "b-quill", "c-quill", "d-quill"):
        _note(root, f"notes/{name}.md", "Quill notes", f"The {name} note is about a quill.")
    _note(root, "notes/best-seo-keywords.md", "Best seo keywords", "A keyword list is not a page.")
    _patch_repo(monkeypatch, root)
    _write_config(data_root)
    cid, _checkout = _open(tmp_path / "camp", monkeypatch)
    _wake_until(
        cid,
        "external-fetch",
        items=[
            _item(
                fact="A quill marks the topic.",
                question="What is a quill?",
                source="notes/a-quill.md",
            )
        ],
    )
    result = run_chain_wake(cid)
    assert result["ok"], result
    plan = load_plan(cid, paths=get_paths())
    local = plan["queue"][0]["local_files"]
    assert local == ["notes/a-quill.md", "notes/b-quill.md", "notes/c-quill.md"]
    assert "notes/d-quill.md" not in local
    assert "notes/best-seo-keywords.md" not in local
    assert len(local) <= 3

    lonely = tmp_path / "lonely"
    _note(lonely, "notes/other.md", "Tomatoes", "The garden grows tomatoes.")
    _patch_repo(monkeypatch, lonely)
    cid2, _checkout2 = _open(tmp_path / "none", monkeypatch)
    _wake_until(
        cid2,
        "external-fetch",
        items=[
            _item(
                fact="A zythum barrel sits unused.",
                question="What is a zythum?",
                source="notes/other.md",
            )
        ],
    )
    refused = run_chain_wake(cid2)
    assert refused["ok"] is False
    assert "no local file" in str(refused.get("denied_reason") or refused.get("error") or "")


def test_fetch_keeps_an_allowlisted_paper_and_skips_a_second_hop(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ada.memory.campaign_page import read_page

    monkeypatch.setattr(
        "ada.web.fetch._robots_allowed",
        lambda url, ignore_robots=False: (True, "honored"),
    )
    ensure_prefs()
    add_host("example.com")
    paper = "https://example.com/quill-paper"
    hop = "https://arxiv.org/abs/9999.99999"
    root = tmp_path / "notes-repo"
    _note(
        root,
        "notes/paper-quill.md",
        "Quill paper",
        "The quill note cites a paper.\n\n[Quill paper](https://example.com/quill-paper)",
    )
    _note(root, "notes/other-quill.md", "Other quill", "Another quill note.")
    _patch_repo(monkeypatch, root)
    seen: list[str] = []

    def http_get(url, **kwargs):  # noqa: ANN001
        seen.append(url)
        resp = httpx.Response(
            200,
            text=(
                f"<html><body><p>{SPAN}</p>"
                f'<a href="{hop}">elsewhere</a></body></html>'
            ),
            headers={"content-type": "text/html"},
            request=httpx.Request("GET", url),
        )
        return resp, url, [url]

    _write_config(data_root)
    cid, _checkout = _open(tmp_path / "camp", monkeypatch)
    _wake_until(
        cid,
        "external-fetch",
        items=[
            _item(
                fact="A quill marks the topic.",
                question="What is a quill?",
                source="notes/paper-quill.md",
            )
        ],
    )
    fetched = run_chain_wake(cid, http_get=http_get)
    assert fetched["ok"], fetched
    assert seen == [paper]
    assert hop not in seen
    plan = load_plan(cid, paths=get_paths())
    assert len(plan["queue"][0]["local_files"]) <= 3
    assert "notes/paper-quill.md" in plan["queue"][0]["local_files"]
    rows = plan["queue"][0]["fetches"]
    assert rows[0]["url"] == paper
    assert SPAN in [fact["span"] for fact in rows[0]["spans"]]
    assert plan["queue"][0]["excerpts"][0]["url"] == paper
    assert plan["queue"][0]["excerpts"][0]["excerpt"] in rows[0]["body"]
    assert hop not in plan["queue"][0]["excerpts"][0]["excerpt"]
    gathered = run_chain_wake(cid)
    assert gathered["ok"], gathered
    page = read_page(cid)
    packet = page["packet"]
    assert {"span": SPAN, "source": paper} in packet
    assert any(fact["span"] == "The quill note cites a paper." for fact in packet)
    assert hop not in [fact["source"] for fact in packet]
    assert all(fact["source"] != hop for fact in packet)


def test_fetch_refuses_a_search_url_and_skips_a_confirm_host(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ada.memory.campaign_page import read_page

    root = tmp_path / "search-repo"
    _note(
        root,
        "notes/quill.md",
        "Quill notes",
        "The quill note names a query.\n\n[results](https://www.google.com/search?q=quill)",
    )
    _patch_repo(monkeypatch, root)
    seen: list[str] = []

    def http_get(url, **kwargs):  # noqa: ANN001
        seen.append(url)
        return _http_get(url)

    _write_config(data_root)
    cid, _checkout = _open(tmp_path / "camp", monkeypatch)
    _wake_until(
        cid,
        "external-fetch",
        items=[
            _item(
                fact="A quill marks the topic.",
                question="What is a quill?",
                source="notes/quill.md",
            )
        ],
    )
    refused = run_chain_wake(cid, http_get=http_get)
    assert refused["ok"] is False
    assert "search" in str(refused.get("denied_reason") or refused.get("error") or "")
    assert seen == []
    assert get_loop(cid)["current_stage"] == "external-fetch"

    skipped = tmp_path / "skip-repo"
    _note(
        skipped,
        "notes/quill.md",
        "Quill notes",
        "The quill note stays local.\n\n[host](https://not-on-the-list.example/page)",
    )
    _patch_repo(monkeypatch, skipped)
    cid2, _checkout2 = _open(tmp_path / "skip", monkeypatch)
    _wake_until(
        cid2,
        "external-fetch",
        items=[
            _item(
                fact="A quill marks the topic.",
                question="What is a quill?",
                source="notes/quill.md",
            )
        ],
    )
    kept = run_chain_wake(cid2, http_get=http_get)
    assert kept["ok"], kept
    assert seen == []
    assert "not-on-the-list.example" not in allowlist_hosts()
    plan = load_plan(cid2, paths=get_paths())
    assert plan["queue"][0]["local_files"] == ["notes/quill.md"]
    assert plan["queue"][0]["fetches"] == []
    gathered = run_chain_wake(cid2)
    assert gathered["ok"], gathered
    packet = read_page(cid2)["packet"]
    assert any(fact["span"] == "The quill note stays local." for fact in packet)
    assert all(fact["source"] != "https://not-on-the-list.example/page" for fact in packet)
    assert SPAN not in [fact["span"] for fact in packet]


def test_chain_gate_refuses_span_not_in_file_or_body(data_root: Path) -> None:
    page = {
        "site": SITE,
        "audience": AUDIENCE,
        "source": SOURCE,
        "question": QUESTION,
        "fill": "researched",
    }
    file_text = (repo_root() / SOURCE).read_text(encoding="utf-8")
    missing = gate_packet(
        page=page,
        facts=[{"span": "not in the file", "source": SOURCE}],
        file_text=file_text,
    )
    assert missing["ok"] is False
    foreign = gate_packet(
        page=page,
        facts=[{"span": SPAN, "source": URL}],
        file_text=file_text,
        fetch_bodies={URL: "some other body"},
    )
    assert foreign["ok"] is False
    kept = gate_packet(
        page=page,
        facts=[{"span": SPAN, "source": URL}],
        file_text=file_text,
        fetch_bodies={URL: f"prefix {SPAN} suffix"},
    )
    assert kept["ok"]
    assert kept["packet"] == [{"span": SPAN, "source": URL}]


def _drafted(
    data_root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    model: _PageModel | None = None,
) -> tuple[str, Path]:
    _write_config(data_root)
    cid, checkout = _open(tmp_path, monkeypatch)
    writer = model or _PageModel()
    _wake_until(cid, "draft", items=[_item()], model=writer)
    drafted = run_chain_wake(cid, model=writer)
    assert drafted["ok"], drafted
    return cid, checkout


def test_chain_draft_shape_has_no_links_or_image(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    writer = _PageModel()
    cid, checkout = _drafted(data_root, tmp_path, monkeypatch, model=writer)
    receipt = latest_receipt(cid, "draft", outcome="ok")
    text = (data_root / receipt["paths"][0]).read_text(encoding="utf-8")
    body = text.split("\n---\n", 1)[1]
    assert writer.tools == [[]]
    assert writer.system == PAGE_SYSTEM
    assert f"Audience: {AUDIENCE}" in writer.prompts[0]
    assert "Aim: educate" in writer.prompts[0]
    assert f"Question: {QUESTION}" in writer.prompts[0]
    assert "Write for a stranger." in writer.prompts[0]
    assert "Leave out an access-date stamp, a repo path, and a machine name." in writer.prompts[0]
    assert "Answer the question, and do not review the file line by line." in writer.prompts[0]
    assert "Spans:\n1. " in writer.prompts[0]
    assert "After that, paragraphs under headings a reader can scan." not in writer.prompts[0]
    assert "A list is only for steps the reader must follow." not in writer.prompts[0]
    assert (
        "Write only the post those passages can support, in your own words, as a few plain paragraphs a person would read."
        in writer.prompts[0]
    )
    assert "The first paragraph is the useful fact, not a repeat of the title." in writer.prompts[0]
    assert (
        "A heading or a list appears only when the passages themselves are a sequence or a comparison."
        in writer.prompts[0]
    )
    assert "## The problem" not in body
    assert "## How it works" not in body
    assert "## Spans" not in body
    assert "The gathered packet is what this page accounts for." not in body
    assert "This page is an account of the gathered packet." not in body
    assert f"# {QUESTION}" not in body
    assert f"## {QUESTION}" not in body
    assert "| --- |" not in body
    answer = opening_answer(text)
    assert answer
    assert answer in body
    assert "\n## " in body
    later = body.split(answer, 1)[1]
    assert any(line.strip() and not line.startswith("#") for line in later.splitlines())
    assert "](" not in body
    assert "![" not in text
    assert "Get in touch" not in text
    assert not (checkout / "content").exists()


def test_chain_draft_refuses_when_the_model_is_absent(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_config(data_root)
    cid, _checkout = _open(tmp_path, monkeypatch)
    _wake_until(cid, "draft", items=[_item()])
    result = run_chain_wake(cid)
    assert result["ok"] is False
    assert result["denied_reason"] == "chain draft model is absent"
    assert get_loop(cid)["current_stage"] == "draft"
    blob = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (data_root / "artifacts").rglob("*")
        if path.is_file()
    )
    assert "The gathered packet is what this page accounts for." not in blob
    assert "## The problem" not in blob
    assert "| --- |" not in blob


def test_chain_draft_accepts_a_reading_in_the_models_own_words(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    page = (
        "The file confirms the access date.\n\n"
        "Dates in the notes include 1999.\n"
    )
    _write_config(data_root)
    cid, _checkout = _open(tmp_path, monkeypatch)
    _wake_until(cid, "draft", items=[_item()])
    result = run_chain_wake(cid, model=_PageModel(page))
    assert result["ok"], result
    assert "draft adds a fact" not in str(result.get("denied_reason") or "")
    text = (data_root / latest_receipt(cid, "draft", outcome="ok")["paths"][0]).read_text(
        encoding="utf-8"
    )
    assert "confirms" in text
    assert "Dates" in text
    assert "1999" in text


def test_chain_draft_accepts_a_page_that_says_confirms(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    page = (
        "The file confirms the access date for every source below.\n\n"
        "## Access date\n\n"
        "The file confirms the access date for every source below.\n"
    )
    cid, _checkout = _drafted(data_root, tmp_path, monkeypatch, model=_PageModel(page))
    text = (data_root / latest_receipt(cid, "draft", outcome="ok")["paths"][0]).read_text(
        encoding="utf-8"
    )
    assert "confirms" in text


def test_chain_draft_adds_no_fact(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cid, _checkout = _drafted(data_root, tmp_path, monkeypatch)
    from ada.memory.campaign_page import read_page

    page = read_page(cid)
    source = (repo_root() / SOURCE).read_text(encoding="utf-8")
    text = (data_root / latest_receipt(cid, "draft", outcome="ok")["paths"][0]).read_text(
        encoding="utf-8"
    )
    assert source.strip() not in text
    assert page["packet"]
    assert all(fact["span"] in source or fact["span"] in text for fact in page["packet"])


def test_chain_draft_does_not_wait_on_aryan(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cid, _checkout = _drafted(data_root, tmp_path, monkeypatch)
    loop = get_loop(cid)
    assert loop["status"] == "active"
    assert loop["status"] != "waiting_on_aryan"
    assert loop["current_stage"] == "librarian"


def _seed_post(checkout: Path, slug: str, question: str, canonical: str) -> None:
    path = checkout / "content" / "blog" / f"{slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n"
        f"title: {question!r}\n"
        f"question: {question!r}\n"
        f"canonical: {canonical!r}\n"
        "---\n\n"
        "Already published.\n",
        encoding="utf-8",
    )


def test_chain_librarian_links_only_packet_and_published_blog(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "ada.web.fetch._robots_allowed",
        lambda url, ignore_robots=False: (True, "honored"),
    )
    ensure_prefs()
    add_host("example.com")
    _write_config(data_root)
    cid, checkout = _open(tmp_path, monkeypatch)
    _seed_post(
        checkout,
        "other-page",
        "Access date for every source below: 2026-09-29.",
        "/blog/other-page",
    )
    _seed_post(checkout, "holder", "About the site", "/about")
    _wake_until(cid, "librarian", items=[_item(urls=[URL])], http_get=_http_get)
    result = run_chain_wake(cid)
    assert result["ok"], result
    text = (data_root / latest_receipt(cid, "draft", outcome="ok")["paths"][0]).read_text(
        encoding="utf-8"
    )
    assert "](/blog/other-page)" in text
    assert "](/about)" not in text
    assert f"[{SPAN}]({URL})" in text
    assert "https://evil.example" not in text
    assert "## Spans" not in text
    assert "## Citations" not in text
    assert "The gathered packet sits beside" not in text
    assert "The gathered packet is what this page accounts for." not in text
    assert not list((checkout / "content" / "blog").glob("what-do-seo*"))


def test_chain_librarian_links_a_rewritten_sentence_without_inventing_a_url(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ada.memory.chain_librarian import apply_librarian

    source_url = "https://developers.google.com/search/docs/fundamentals/how-search-works"
    name = "In-depth guide to how Google Search works"
    page = (
        "A stranger can read one public page.\n\n"
        "## Crawling\n\n"
        f"The {name} says Google Search crawls, indexes, then serves the same public object.\n"
    )
    cid, checkout = _drafted(data_root, tmp_path, monkeypatch, model=_PageModel(page))
    _seed_post(
        checkout,
        "public-page",
        "A stranger can read one public page from the index",
        "/blog/public-page",
    )
    result = run_chain_wake(cid)
    assert result["ok"], result
    text = (data_root / latest_receipt(cid, "draft", outcome="ok")["paths"][0]).read_text(
        encoding="utf-8"
    )
    assert (
        f"The [{name}]({source_url}) says Google Search crawls, indexes, then serves "
        "the same public object."
    ) in text
    assert "[Google Search crawls" not in text
    assert "[here]" not in text
    assert "[A stranger can read one public page](/blog/public-page)" in text
    assert "from the index](/blog/public-page)" not in text
    assert 'rel="' not in text
    assert "https://evil.example" not in text
    source = (repo_root() / SOURCE).read_text(encoding="utf-8")
    for href in re.findall(r"\]\((https?://[^)]+)\)", text):
        assert href in source
    pub = "https://developers.google.com/search/docs/appearance/publication-dates"
    people = "https://developers.google.com/search/docs/fundamentals/creating-helpful-content"
    shared = apply_librarian(
        "\n".join(
            [
                "A visible, labeled date tells the reader when the page appeared.",
                "",
                "Influence your byline dates in Google Search names that date.",
                "",
                "Creating helpful, reliable, people-first content warns against a fake refresh.",
                "",
            ]
        ),
        posts=[],
        urls=[pub, people],
        cta=None,
        spans=[],
        packet=[],
        source_text="\n".join(
            [
                f'Google, "Influence your byline dates in Google Search." {pub}',
                (
                    "A visible, labeled date for a significant update stays distinct. "
                    f'Google, "Creating helpful, reliable, people-first content." {people}'
                ),
            ]
        ),
    )
    assert f"[A visible, labeled date]({people})" not in shared
    assert f"[A visible, labeled date]({pub})" not in shared
    assert f"[Influence your byline dates in Google Search]({pub})" in shared
    assert f"[Creating helpful, reliable, people-first content]({people})" in shared
    assert f"[Influence your byline dates in Google Search]({people})" not in shared


def test_chain_librarian_refuses_site_holder_paths() -> None:
    for href in ("/", "/about", "/projects", "/workshop", "/projects/ada"):
        assert is_holder_href(href)
    assert is_holder_href("/blog/other-page") is False


def test_chain_librarian_cta_from_config_or_absent(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_config(data_root)
    cid, _checkout = _open(tmp_path, monkeypatch)
    _wake_until(cid, "librarian", items=[_item()])
    assert run_chain_wake(cid)["ok"]
    text = (data_root / latest_receipt(cid, "draft", outcome="ok")["paths"][0]).read_text(
        encoding="utf-8"
    )
    assert "Get in touch" not in text

    _write_config(
        data_root,
        default_cta={
            "label": "Get in touch",
            "mail": "mailto:ada@example.com",
            "call": "https://example.com/call",
        },
    )
    cid2, _checkout2 = _open(tmp_path / "second", monkeypatch)
    _wake_until(
        cid2,
        "librarian",
        items=[_item(question="Where does one public HTML URL come from?")],
    )
    assert run_chain_wake(cid2)["ok"]
    linked = (data_root / latest_receipt(cid2, "draft", outcome="ok")["paths"][0]).read_text(
        encoding="utf-8"
    )
    assert "[Get in touch](mailto:ada@example.com)" in linked
    assert "[Get in touch](https://example.com/call)" in linked
    assert linked.index("Access date for every source below: 2026-09-29.") < linked.index(
        "[Get in touch](mailto:ada@example.com)"
    )
    assert "## The problem" not in linked
    assert "## How it works" not in linked
    assert "## Spans" not in linked


def test_chain_diagram_reads_a_sequence_or_table_in_the_body() -> None:
    from ada.memory.chain_diagram import diagram_alt, section_is_flow

    plain = "One answer paragraph.\n\n## Notes\n\nAnother paragraph.\n"
    assert section_is_flow(plain) is False
    assert section_is_flow(plain + "\n1. One answer paragraph.\n") is True
    compared = "One answer paragraph.\n\n| SEO | AEO |\n| --- | --- |\n| page | box |\n"
    assert section_is_flow(compared) is False
    policy = (
        "Google names cloaking and doorway pages.\n\n"
        "| Policy | What it refuses |\n"
        "| --- | --- |\n"
        "| Cloaking | Different content |\n"
        "| Doorway pages | A funnel |\n"
    )
    assert section_is_flow(policy) is False
    blocks = (
        "One answer paragraph.\n\n"
        "| Block | What it contains |\n"
        "| --- | --- |\n"
        "| Title | The title |\n"
        "| Call to Action | A close |\n"
    )
    assert section_is_flow(blocks) is False
    assert section_is_flow("| span one |\n| --- |\n| span two |\n") is False
    assert diagram_alt(["Block | What it is and why it's", "**Call to Action** | close"]) == ""


def test_chain_diagram_skip_writes_no_checkout_file(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cid, checkout = _drafted(data_root, tmp_path, monkeypatch)
    _wake_until(cid, "diagram")
    result = run_chain_wake(cid)
    assert result["outcome"] == "skip"
    assert latest_receipt(cid, "diagram", outcome="skip") is not None
    assert not (checkout / "content" / "blog" / "media").exists()
    assert not list((data_root / "artifacts").rglob("*.svg"))


def test_chain_diagram_svg_stays_under_artifacts(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cid, checkout = _drafted(data_root, tmp_path, monkeypatch)
    _wake_until(cid, "diagram")
    draft = data_root / latest_receipt(cid, "draft", outcome="ok")["paths"][0]
    text = draft.read_text(encoding="utf-8")
    answer = opening_answer(text)
    draft.write_text(text.rstrip() + f"\n\n1. {answer}\n", encoding="utf-8")
    result = run_chain_wake(cid)
    assert result["ok"], result
    svgs = list((data_root / "artifacts").rglob("*.svg"))
    assert len(svgs) == 1
    assert svgs[0].read_text(encoding="utf-8").startswith("<svg")
    updated = draft.read_text(encoding="utf-8")
    assert "content/blog/media/" in updated
    assert updated.index(answer) < updated.index("![")
    assert "## How it works" not in updated
    assert not (checkout / "content" / "blog" / "media").exists()


def test_chain_diagram_svg_shows_steps_and_skips_paragraphs(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ada.memory.chain_diagram import section_is_flow

    plain = "One answer paragraph.\n\n## Notes\n\nAnother paragraph.\n"
    assert section_is_flow(plain) is False
    _write_config(data_root)
    cid, checkout = _open(tmp_path, monkeypatch)
    _wake_until(cid, "diagram", items=[_item()])
    skipped = run_chain_wake(cid)
    assert skipped["outcome"] == "skip"
    assert not list((data_root / "artifacts").rglob("*.svg"))
    assert not (checkout / "content" / "blog" / "media").exists()

    cid2, _checkout2 = _open(tmp_path / "steps", monkeypatch)
    _wake_until(cid2, "diagram", items=[_item(question="Where does one public HTML URL come from?")])
    draft = data_root / latest_receipt(cid2, "draft", outcome="ok")["paths"][0]
    slug = blog_slug("Where does one public HTML URL come from?")
    src = f"content/blog/media/{slug}.svg"
    draft.write_text(
        draft.read_text(encoding="utf-8").rstrip()
        + "\n\n1. Fetch the page.\n2. Read the index.\n"
        + f"\n![Diagram of how it works]({src})\n",
        encoding="utf-8",
    )
    drawn = run_chain_wake(cid2)
    assert drawn["ok"], drawn
    svgs = list((data_root / "artifacts").rglob("*.svg"))
    assert len(svgs) == 1
    svg = svgs[0].read_text(encoding="utf-8")
    assert "Fetch the page." in svg
    assert "Read the index." in svg
    assert svg.strip() != '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 48"><text x="8" y="28">How it works</text></svg>'
    updated = draft.read_text(encoding="utf-8")
    assert updated.count("![") == 1
    assert "Diagram of how it works" not in updated
    assert "How it works" not in svg

    cid3, _checkout3 = _open(tmp_path / "table", monkeypatch)
    _wake_until(cid3, "diagram", items=[_item(question="How does one page leave the queue?")])
    table_draft = data_root / latest_receipt(cid3, "draft", outcome="ok")["paths"][0]
    table_slug = blog_slug("How does one page leave the queue?")
    table_src = f"content/blog/media/{table_slug}.svg"
    table_draft.write_text(
        table_draft.read_text(encoding="utf-8").rstrip()
        + "\n\n| Block | Role |\n| --- | --- |\n| Title | Names the page |\n| Heading | States the page |\n"
        + f"\n![Diagram of how it works]({table_src})\n",
        encoding="utf-8",
    )
    table_drawn = run_chain_wake(cid3)
    assert table_drawn["outcome"] == "skip", table_drawn
    assert not list((data_root / "artifacts").rglob(f"{table_slug}.svg"))


def test_chain_diagram_refuses_unsplash_host(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cid, checkout = _drafted(data_root, tmp_path, monkeypatch)
    _wake_until(cid, "diagram")
    draft = data_root / latest_receipt(cid, "draft", outcome="ok")["paths"][0]
    draft.write_text(
        draft.read_text(encoding="utf-8") + "\n![](https://images.unsplash.com/photo)\n",
        encoding="utf-8",
    )
    result = run_chain_wake(cid)
    assert result["ok"] is False
    assert not (checkout / "content").exists()
    assert not list((data_root / "artifacts").rglob("*.svg"))


def test_chain_critic_pass_writes_no_checkout(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cid, checkout = _drafted(data_root, tmp_path, monkeypatch)
    _wake_until(cid, "critic")
    result = run_chain_wake(cid)
    assert result["outcome"] == "pass", result
    assert latest_receipt(cid, "critic", outcome="pass") is not None
    assert not (checkout / "content" / "blog").exists() or not list(
        (checkout / "content" / "blog").glob("*.md")
    )


def test_chain_critic_passes_rel_words_and_names_a_rel_link(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_url = "https://developers.google.com/search/docs/fundamentals/how-search-works"
    cid, checkout = _drafted(data_root, tmp_path, monkeypatch)
    _wake_until(cid, "critic")
    draft = data_root / latest_receipt(cid, "draft", outcome="ok")["paths"][0]
    draft.write_text(
        draft.read_text(encoding="utf-8").rstrip()
        + '\n\nA paid placement uses rel="nofollow" or rel="sponsored" when the link is paid.\n',
        encoding="utf-8",
    )
    passed = run_chain_wake(cid)
    assert passed["outcome"] == "pass", passed
    assert not (checkout / "content" / "blog").exists() or not list(
        (checkout / "content" / "blog").glob("what-do-seo*")
    )

    cid2, checkout2 = _open(tmp_path / "rel", monkeypatch)
    _wake_until(cid2, "critic", items=[_item(question="Where does one public HTML URL come from?")])
    draft2 = data_root / latest_receipt(cid2, "draft", outcome="ok")["paths"][0]
    link = f'[paid placement]({source_url}){{rel="nofollow"}}'
    html = f'<a href="{source_url}" rel="sponsored">sponsor</a>'
    draft2.write_text(
        draft2.read_text(encoding="utf-8").rstrip() + "\n\n" + link + "\n" + html + "\n",
        encoding="utf-8",
    )
    failed = run_chain_wake(cid2)
    assert failed["outcome"] == "fail"
    assert "rel" in failed["checks"]
    receipt = latest_receipt(cid2, "critic", outcome="fail")
    assert receipt is not None
    assert link in receipt["remove"]
    assert any('rel="sponsored"' in item for item in receipt["remove"])
    assert not (checkout2 / "content").exists()


def _chain_markdown(question: str, body: str) -> str:
    import json

    from ada.memory.blog_draft import first_sentence

    slug = blog_slug(question)
    fields = {
        "title": question,
        "question": question,
        "description": first_sentence(question),
        "published": "2026-10-01",
        "modified": "2026-10-01",
        "fill": "researched",
        "source": SOURCE,
        "canonical": f"/blog/{slug}",
    }
    front = "\n".join(f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in fields.items())
    prose = body if body.endswith("\n") else body + "\n"
    return f"---\n{front}\n---\n\n{prose}"


def test_chain_draft_refuses_an_inventory_and_allows_a_sequence(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inventory = (
        "SEO, AEO, and GEO consume one public page. The spam policies name cloaking and doorway pages.\n\n"
        "| Policy | What it refuses |\n"
        "| --- | --- |\n"
        "| Cloaking | Different content |\n"
        "| Doorway pages | A funnel |\n\n"
        "1. Cloaking\n"
        "2. Doorway pages\n"
    )
    _write_config(data_root)
    cid, _checkout = _open(tmp_path, monkeypatch)
    _wake_until(cid, "draft", items=[_item()])
    refused = run_chain_wake(cid, model=_PageModel(inventory))
    assert refused["ok"] is False
    assert "table" in refused["denied_reason"] or "list" in refused["denied_reason"]

    sequence = (
        "Google Search crawls, then indexes, then serves one page.\n\n"
        "1. Crawls the public page.\n"
        "2. Indexes the public page.\n"
        "3. Serves the public page.\n\n"
        "| SEO | AEO |\n"
        "| --- | --- |\n"
        "| stores the page | lifts a box |\n"
    )
    cid2, _checkout2 = _open(tmp_path / "sequence", monkeypatch)
    _wake_until(cid2, "draft", items=[_item(question="Where does one public HTML URL come from?")])
    allowed = run_chain_wake(cid2, model=_PageModel(sequence))
    assert allowed["ok"], allowed


_TABLE_REASON = "draft restates the opening as a table"
_STOCK_REASON = "draft repeats a stock line"
_OPENING_TABLE = (
    "Cloaking and doorway pages are named in the spam policies.\n\n"
    "| Cloaking | Different content |\n"
    "| --- | --- |\n"
    "| Doorway pages | A funnel |\n"
)
_PARAGRAPHS = (
    "The file confirms the access date.\n\n"
    "Dates in the notes include 1999.\n"
)
_STOCK_PAGE = "The gathered packet is what this page accounts for.\n"


class _RetryModel:
    def __init__(self, pages: list[str]) -> None:
        self.pages = pages
        self.prompts: list[str] = []

    def generate(self, *, system: str, contents: list[object], tools: object = None) -> CortexTurn:
        self.prompts.append(_prompt_text(contents))
        index = len(self.prompts) - 1
        if index >= len(self.pages):
            raise AssertionError("draft asked for a third page")
        return CortexTurn(text=self.pages[index])


def _critic_fails(cid: str) -> int:
    plan = load_plan(cid, paths=get_paths())
    assert plan is not None
    return int(plan["queue"][0].get("critic_fails") or 0)


def test_chain_draft_retries_once_after_a_table_restatement(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    writer = _RetryModel([_OPENING_TABLE, _PARAGRAPHS])
    _write_config(data_root)
    cid, checkout = _open(tmp_path, monkeypatch)
    _wake_until(cid, "draft", items=[_item()])
    result = run_chain_wake(cid, model=writer)
    assert result["ok"], result
    assert len(writer.prompts) == 2
    assert _TABLE_REASON not in writer.prompts[0]
    assert _TABLE_REASON in writer.prompts[1]
    assert writer.prompts[1].startswith(writer.prompts[0].rstrip())
    text = (data_root / latest_receipt(cid, "draft", outcome="ok")["paths"][0]).read_text(
        encoding="utf-8"
    )
    assert "Dates in the notes include 1999." in text
    assert "| Cloaking |" not in text
    assert get_loop(cid)["current_stage"] == "librarian"
    assert _critic_fails(cid) == 0
    fails = [row for row in read_receipts(cid) if row.get("stage") == "draft" and row.get("outcome") == "fail"]
    assert fails[0]["checks"] == [_TABLE_REASON]
    assert latest_receipt(cid, "push") is None
    assert not (checkout / "content").exists()


def test_chain_draft_second_refusal_writes_nothing_and_does_not_push(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ada.hud.chain_form import make_one_chain_page

    writer = _RetryModel([_OPENING_TABLE, _STOCK_PAGE])
    _write_config(data_root)
    cid, checkout = _open(tmp_path, monkeypatch)
    _wake_until(cid, "draft", items=[_item()])
    pressed = make_one_chain_page(cid, model=writer)
    assert pressed["ok"] is False
    assert pressed["outcome"] == "denied"
    assert [step["stage"] for step in pressed["stages"]] == ["draft"]
    assert pressed["stages"][0]["outcome"] == "denied"
    assert len(writer.prompts) == 2
    assert _TABLE_REASON in writer.prompts[1]
    slug = blog_slug(QUESTION)
    assert list((data_root / "artifacts").rglob(f"{slug}.md")) == []
    denied = latest_receipt(cid, "draft", outcome="denied")
    assert denied is not None
    assert _STOCK_REASON in denied["checks"]
    assert _critic_fails(cid) == 0
    assert get_loop(cid)["current_stage"] == "draft"
    assert latest_receipt(cid, "push") is None
    assert not (checkout / "content").exists()


def test_chain_critic_fails_a_policy_table_and_a_cut_sentence(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ada.memory.chain_critic import critic_checks

    slug = blog_slug(QUESTION)
    src = f"content/blog/media/{slug}.svg"
    policy = _chain_markdown(
        QUESTION,
        "\n".join(
            [
                "SEO, AEO, and GEO consume one public page. The spam policies name cloaking and doorway pages.",
                "",
                "## Policies",
                "",
                "A later paragraph keeps the answer in prose.",
                "",
                "| Policy | What it refuses |",
                "| --- | --- |",
                "| Cloaking | Different content |",
                "| Doorway pages | A funnel |",
                "",
                f"![Diagram of Cloaking | Different content and Doorway pages | A funnel]({src})",
                "",
            ]
        ),
    )
    table_failed = critic_checks(
        policy,
        question=QUESTION,
        slug=slug,
        packet=[],
        source_text="The spam policies name cloaking and doorway pages.",
        cta=None,
        published=set(),
        staged="artifacts/2026-10-01/policy.svg",
        staged_bytes=b"<svg xmlns='http://www.w3.org/2000/svg'></svg>",
    )
    assert "inventory" in table_failed
    assert "image-table" in table_failed
    assert "alt" in table_failed
    assert "direct-answer" not in table_failed

    url = "https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls"
    cut = _chain_markdown(
        QUESTION,
        "\n".join(
            [
                "SEO, AEO, and GEO consume one public page.",
                "",
                "## Canonical",
                "",
                f"Put an absolute [rel=canonical in the head, pointing]({url}) at this URL.",
                "",
            ]
        ),
    )
    cut_failed = critic_checks(
        cut,
        question=QUESTION,
        slug=slug,
        packet=[],
        source_text=(
            'Google, "How to specify a canonical URL with rel=canonical and other methods." '
            f"{url}\n"
        ),
        cta=None,
        published=set(),
        staged=None,
        staged_bytes=None,
    )
    assert "anchor" in cut_failed
    assert "direct-answer" not in cut_failed

    page = (
        "SEO, AEO, and GEO consume one public page.\n\n"
        "## Crawling\n\n"
        "The In-depth guide to how Google Search works says Google Search crawls, indexes, then serves the same public object.\n"
    )
    cid, checkout = _drafted(data_root, tmp_path, monkeypatch, model=_PageModel(page))
    _wake_until(cid, "critic")
    passed = run_chain_wake(cid)
    assert passed["outcome"] == "pass", passed
    text = (data_root / latest_receipt(cid, "draft", outcome="ok")["paths"][0]).read_text(
        encoding="utf-8"
    )
    assert (
        "[In-depth guide to how Google Search works]"
        "(https://developers.google.com/search/docs/fundamentals/how-search-works)"
    ) in text
    assert "![" not in text
    assert not (checkout / "content" / "blog").exists() or not list(
        (checkout / "content" / "blog").glob("*.md")
    )


def test_chain_critic_fail_lists_checks(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cid, checkout = _drafted(data_root, tmp_path, monkeypatch)
    _wake_until(cid, "critic")
    draft = data_root / latest_receipt(cid, "draft", outcome="ok")["paths"][0]
    draft.write_text(draft.read_text(encoding="utf-8").replace("/blog/", "/pages/", 1), encoding="utf-8")
    result = run_chain_wake(cid)
    assert result["outcome"] == "fail"
    assert "canonical" in result["checks"]
    receipt = latest_receipt(cid, "critic", outcome="fail")
    assert "canonical" in receipt["checks"]
    assert not (checkout / "content").exists()


def test_chain_critic_second_fail_sets_failed(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cid, checkout = _drafted(data_root, tmp_path, monkeypatch)
    _wake_until(cid, "critic")
    draft = data_root / latest_receipt(cid, "draft", outcome="ok")["paths"][0]
    draft.write_text(draft.read_text(encoding="utf-8").replace("/blog/", "/pages/", 1), encoding="utf-8")
    assert run_chain_wake(cid)["outcome"] == "fail"
    assert get_loop(cid)["status"] != "failed"
    _wake_until(cid, "critic")
    again = run_chain_wake(cid)
    assert again["outcome"] == "fail"
    assert get_loop(cid)["status"] == "failed"
    assert not (checkout / "content").exists()


def test_chain_repair_cannot_add_a_fact() -> None:
    original = "This page is an account of the gathered packet.\nA bad sentence.\n"
    added = repair_markdown(original, ["A bad sentence.\n"], addition="A new fact.")
    assert added["ok"] is False
    removed = repair_markdown(original, ["A bad sentence.\n"])
    assert removed["ok"]
    assert "A bad sentence." not in removed["markdown"]
    assert "A new fact." not in removed["markdown"]


def _passed(data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[str, Path]:
    cid, checkout = _drafted(data_root, tmp_path, monkeypatch)
    _wake_until(cid, "deliver")
    return cid, checkout


def test_chain_deliver_writes_without_confirm(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cid, checkout = _passed(data_root, tmp_path, monkeypatch)
    real = subprocess.run

    def _boom(*args, **kwargs):  # noqa: ANN001
        raise AssertionError(f"git during deliver: {args!r}")

    subprocess.run = _boom
    try:
        result = run_chain_wake(cid)
    finally:
        subprocess.run = real
    assert result["ok"], result
    slug = blog_slug(QUESTION)
    dest = checkout / "content" / "blog" / f"{slug}.md"
    assert dest.is_file()
    assert "confirmed" not in (result.get("denied_reason") or "")
    assert get_loop(cid)["status"] == "active"
    assert get_loop(cid)["status"] != "done"
    receipt = latest_receipt(cid, "deliver", outcome="ok")
    assert f"content/blog/{slug}.md" in receipt["paths"]


def test_chain_deliver_refuses_without_critic_pass(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_config(data_root)
    cid, checkout = _open(tmp_path, monkeypatch)
    stages = [{"id": stage, "state": "done"} for stage in CHAIN_STAGES]
    for stage in stages:
        if stage["id"] == "deliver":
            stage["state"] = "active"
    upsert_loop(loop_id=cid, stages=stages, current_stage="deliver", status="active")
    from ada.tools.blog_tools import run_blog_checkout_write

    result = run_blog_checkout_write({"campaign_id": cid, "confirmed": True})
    assert result["ok"] is False
    assert result.get("needs_confirm") is not True
    assert not (checkout / "content" / "blog").exists()


def test_chain_deliver_refuses_existing_slug(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cid, checkout = _passed(data_root, tmp_path, monkeypatch)
    slug = blog_slug(QUESTION)
    dest = checkout / "content" / "blog" / f"{slug}.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("keep", encoding="utf-8")
    result = run_chain_wake(cid)
    assert result["ok"] is False
    assert dest.read_text(encoding="utf-8") == "keep"


def test_chain_deliver_copies_staged_svg_only(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cid, checkout = _drafted(data_root, tmp_path, monkeypatch)
    _wake_until(cid, "diagram")
    draft = data_root / latest_receipt(cid, "draft", outcome="ok")["paths"][0]
    answer = opening_answer(draft.read_text(encoding="utf-8"))
    draft.write_text(
        draft.read_text(encoding="utf-8").rstrip() + f"\n\n1. {answer}\n",
        encoding="utf-8",
    )
    assert run_chain_wake(cid)["ok"]
    _wake_until(cid, "deliver")
    result = run_chain_wake(cid)
    assert result["ok"], result
    slug = blog_slug(QUESTION)
    staged = next((data_root / "artifacts").rglob(f"{slug}.svg"))
    copied = checkout / "content" / "blog" / "media" / f"{slug}.svg"
    assert copied.read_bytes() == staged.read_bytes()
    assert list((checkout / "content" / "blog" / "media").iterdir()) == [copied]


def _bare_origin(tmp_path: Path) -> str:
    bare = tmp_path / "remotes" / "aryanjohari" / "aryan-portfolio.git"
    bare.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "--bare", "-b", "main", str(bare)], check=True, capture_output=True)
    return bare.as_uri()


def _pushed(data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[str, Path]:
    _write_config(data_root)
    cid, checkout = _open(tmp_path, monkeypatch, origin=_bare_origin(tmp_path))
    _wake_until(cid, "deliver", items=[_item()])
    assert run_chain_wake(cid)["ok"]
    return cid, checkout


def test_chain_push_commits_only_receipt_paths(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cid, checkout = _pushed(data_root, tmp_path, monkeypatch)
    result = run_chain_wake(cid)
    assert result["ok"], result
    sha = result["sha"]
    assert len(sha) == 40
    assert not sha.startswith("http")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=checkout,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert head == sha
    names = subprocess.run(
        ["git", "show", "--name-only", "--pretty=format:", "HEAD"],
        cwd=checkout,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()
    slug = blog_slug(QUESTION)
    assert names == [f"content/blog/{slug}.md"]
    assert get_loop(cid)["status"] == "active"
    assert get_loop(cid)["status"] != "done"
    assert latest_receipt(cid, "push", outcome="ok")["sha"] == sha
    assert get_loop(cid).get("last_receipt") != sha


def test_chain_push_refuses_extra_path_and_force(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cid, checkout = _pushed(data_root, tmp_path, monkeypatch)
    (checkout / "notes.txt").write_text("extra", encoding="utf-8")
    assert "--force" not in push_argv("main")
    assert "--no-verify" not in commit_argv("Publish")
    result = run_chain_wake(cid)
    assert result["ok"] is False
    assert (checkout / "notes.txt").read_text(encoding="utf-8") == "extra"
    log = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=checkout,
        capture_output=True,
        text=True,
    )
    assert log.returncode != 0


def test_chain_push_sha_does_not_mark_done(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cid, _checkout = _pushed(data_root, tmp_path, monkeypatch)
    result = run_chain_wake(cid)
    assert result["ok"], result
    loop = get_loop(cid)
    assert loop["status"] == "active"
    assert loop["status"] != "done"
    assert result["sha"] not in (loop.get("last_receipt") or "")


def test_chain10_jail_wrong_origin_writes_nothing(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    test_chain_bind_refuses_other_origin(data_root, tmp_path, monkeypatch)


def test_chain10_critic_fail_leaves_checkout_clean(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    test_chain_critic_fail_lists_checks(data_root, tmp_path, monkeypatch)


def test_chain10_existing_slug_blocks_deliver(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    test_chain_deliver_refuses_existing_slug(data_root, tmp_path, monkeypatch)


def test_chain10_delete_still_needs_confirm(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cid, checkout = _passed(data_root, tmp_path, monkeypatch)
    assert run_chain_wake(cid)["ok"]
    slug = blog_slug(QUESTION)
    dest = checkout / "content" / "blog" / f"{slug}.md"
    assert dest.is_file()
    pending = run_blog_checkout_delete({"campaign_id": cid})
    assert pending.get("needs_confirm") is True
    assert dest.is_file()
    deleted = run_blog_checkout_delete({"campaign_id": cid, "confirmed": True})
    assert deleted["ok"], deleted
    assert not dest.exists()
    from ada.memory.campaign_page import read_page

    assert read_page(cid)["slug"] == ""
    assert blog_slug(QUESTION) == slug
    assert not list((checkout / "content" / "blog").glob("*-2.md"))


def test_chain10_push_path_jail(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    test_chain_push_refuses_extra_path_and_force(data_root, tmp_path, monkeypatch)
    assert "--force" not in " ".join(push_argv("main"))
