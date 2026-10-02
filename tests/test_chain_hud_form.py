"""HUD SEO chain form. Temp checkout only. Never a live portfolio."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from ada.cortex.adapter import CortexTurn
from ada.hud.app import create_app
from ada.io.paths import get_paths
from ada.memory.blog_slug import SlugError, blog_slug
from ada.memory.campaign_page import SITE
from ada.memory.chain_plan import load_plan
from ada.memory.chain_receipt import latest_receipt
from ada.memory.open_loops import get_loop
from ada.memory.portfolio_chain import PUBLIC_HOST

pytestmark = pytest.mark.tier_a

SOURCE = "src/ada/memory/blog_slug.py"
BLOG_SOURCE = "docs/research/01_how_discovery_works.md"
QUESTION = "How does one page leave the queue?"
AUDIENCE = "A person who reads about work the operator has already shipped."
KEYWORD = "best seo keywords"
LONG_QUESTION = (
    "What happens when the blog slug checker refuses a question that is far "
    "longer than eighty characters and must stay whole?"
)
SLUG_QUESTION = "What is a blog slug?"
PACKET_QUESTION = "How does one source file gather a packet?"
CUT_QUESTION = "What is a cut?"
READER_QUESTION = "Is a cut a service the shop performs?"
FACT_TITLE = "A cut is a service the shop performs."
CUT_SOURCE = "notes/a-cut.md"
BEARD_QUESTION = "What is a beard trim?"


def _patch_notes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "notes-repo"
    notes = root / "notes"
    notes.mkdir(parents=True)
    (notes / "a-cut.md").write_text(
        "# A cut\n\nA cut is a service the shop performs.\n\nThe reader asks what a cut is.\n",
        encoding="utf-8",
    )
    (notes / "b-shop.md").write_text(
        "# Shop cut\n\nA beard trim is different.\n",
        encoding="utf-8",
    )
    (notes / "c-best-seo-keywords.md").write_text(
        "# Best seo keywords\n\nA keyword list is not a page.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("ada.memory.blog_packet.repo_root", lambda: root)


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


def _paragraph_page(prompt: str) -> str:
    spans: list[str] = []
    label = "Excerpts:\n" if "Excerpts:\n" in prompt else "Spans:\n"
    if label in prompt:
        for line in prompt.split(label, 1)[1].splitlines():
            if ". " not in line:
                continue
            number, rest = line.split(". ", 1)
            if number.isdigit():
                spans.append(rest.strip())
    prose = [
        span
        for span in spans
        if span and not span.startswith("#") and not span.startswith("|") and not span.startswith("```")
        and not (span[:1].isdigit() and ". " in span[:4])
    ]
    if not prose:
        prose = ["Notes"]
    question = ""
    for line in prompt.splitlines():
        if line.startswith("Question: "):
            question = line.split("Question: ", 1)[1].strip()
            break
    first = prose[0]
    folded_q = " ".join(question.casefold().split()).rstrip(".!?")
    folded_f = " ".join(first.casefold().split()).rstrip(".!?")
    if folded_q and folded_f == folded_q:
        first = f"Yes. {first}"
    second = prose[1] if len(prose) > 1 else prose[0]
    heading = " ".join(second.split()[:6])
    return f"{first}\n\n## {heading}\n\n{second}\n"


def _fact_or_path(prompt: str) -> str:
    if "Choose one page" in prompt:
        return "The shop cut"
    if "Return at most 3 paths" in prompt:
        path = ""
        for line in prompt.splitlines():
            if line.startswith("path: "):
                path = line.split("path: ", 1)[1].strip()
            elif (
                line.startswith("sentences: ")
                and "A cut is a service the shop performs." in line
                and path
            ):
                return path
        return CUT_SOURCE
    return FACT_TITLE


def _short_question(prompt: str) -> str:
    if "Gather one source file into a packet of verbatim spans." in prompt:
        return PACKET_QUESTION
    return SLUG_QUESTION


class _PageModel:
    def generate(self, *, system: str, contents: list[object], tools: object = None) -> CortexTurn:
        assert tools == []
        prompt = _prompt_text(contents)
        if "Excerpts:" in prompt or "Spans:\n" in prompt:
            return CortexTurn(text=_paragraph_page(prompt))
        if "Write one title a stranger would search." in prompt:
            if FACT_TITLE in prompt:
                return CortexTurn(text=FACT_TITLE)
            if LONG_QUESTION in prompt:
                return CortexTurn(text=LONG_QUESTION)
            return CortexTurn(text=_short_question(prompt))
        if "Return at most 3 paths" in prompt or "Fact:" in prompt:
            return CortexTurn(text=_fact_or_path(prompt))
        return CortexTurn(text=_short_question(prompt))


def _client(monkeypatch: pytest.MonkeyPatch, data_root: Path) -> TestClient:
    monkeypatch.setenv("ADA_DATA_ROOT", str(data_root))
    monkeypatch.delenv("ADA_PORTFOLIO_CHECKOUT", raising=False)
    monkeypatch.setenv("ADA_HUD_SESSION_SECRET", "test-secret-please-change")
    monkeypatch.setenv("ADA_HUD_PASSWORD", "test-password")
    monkeypatch.setenv("ADA_HUD_COOKIE_SECURE", "0")

    def _no_public_host(*_args, **_kwargs):  # noqa: ANN001
        raise AssertionError("the form fetched a public host")

    monkeypatch.setattr("urllib.request.urlopen", _no_public_host)
    monkeypatch.setattr("ada.memory.chain_plan.gemini_reader_model", lambda: _PageModel())
    client = TestClient(create_app())
    login = client.post("/api/login", json={"password": "test-password"})
    assert login.status_code == 200
    return client


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
        "folders": ["notes"],
        "branch": "main",
    }
    doc.update(overrides)
    path = get_paths().portfolio_chain_yaml
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc), encoding="utf-8")


def _bare_origin(tmp_path: Path) -> str:
    bare = tmp_path / "remotes" / "aryanjohari" / "aryan-portfolio.git"
    bare.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "init", "--bare", "-b", "main", str(bare)],
        check=True,
        capture_output=True,
    )
    return bare.as_uri()


def _checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "portfolio"
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "remote", "add", "origin", _bare_origin(tmp_path)],
        cwd=path,
        check=True,
        capture_output=True,
    )
    monkeypatch.setenv("ADA_PORTFOLIO_CHECKOUT", str(path))
    return path


def test_blog_form_still_stores_a_row(
    data_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _client(monkeypatch, data_root)
    stored = client.post(
        "/api/blog/step",
        json={
            "step": "store",
            "site": SITE,
            "audience": AUDIENCE,
            "source": BLOG_SOURCE,
            "question": QUESTION,
            "fill": "researched",
        },
    )
    assert stored.status_code == 200, stored.text
    body = stored.json()
    assert body["ok"] is True
    assert body["result_line"] == "Stored the row."
    cid = body["status"]["campaign_id"]
    page = get_paths().campaign_pages / f"{cid}.yaml"
    assert QUESTION in page.read_text(encoding="utf-8")
    assert not get_paths().portfolio_chain_yaml.exists()


def test_chain_form_queues_from_sources(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_config(data_root, folders=["notes"])
    before = get_paths().portfolio_chain_yaml.read_text(encoding="utf-8")
    client = _client(monkeypatch, data_root)
    _patch_notes(tmp_path, monkeypatch)
    checkout = _checkout(tmp_path, monkeypatch)
    made = client.post("/api/chain/page", json={})
    assert made.status_code == 200, made.text
    body = made.json()
    assert body["ok"] is True
    assert body["published"][0]["question"] == FACT_TITLE
    assert body["published"][0]["question"] != CUT_QUESTION
    assert body["published"][0]["source"] == CUT_SOURCE
    assert KEYWORD not in FACT_TITLE
    assert KEYWORD not in BEARD_QUESTION
    plan = load_plan(body["campaign_id"], paths=get_paths())
    assert plan is not None
    assert plan["audience"] == AUDIENCE
    assert plan["aims"] == ["educate"]
    assert plan["suggestions"] == []
    assert [item["question"] for item in plan["queue"]] == [FACT_TITLE]
    assert BEARD_QUESTION not in [item["question"] for item in plan["queue"]]
    assert KEYWORD not in [item["question"] for item in plan["queue"]]
    assert get_paths().portfolio_chain_yaml.read_text(encoding="utf-8") == before
    assert get_loop(body["campaign_id"])["status"] == "active"
    assert not (checkout / "content" / "blog" / f"{blog_slug(BEARD_QUESTION)}.md").exists()


def test_chain_form_refuses_to_invent_config(
    data_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _client(monkeypatch, data_root)
    missing = client.post("/api/chain/page", json={})
    assert missing.status_code == 400
    assert missing.json()["ok"] is False
    assert not get_paths().portfolio_chain_yaml.exists()
    _write_config(data_root, aims=["hire", "educate"])
    before = get_paths().portfolio_chain_yaml.read_text(encoding="utf-8")
    many = client.post("/api/chain/page", json={})
    assert many.status_code == 400
    assert "two aims" in many.json()["result_line"]
    assert get_paths().portfolio_chain_yaml.read_text(encoding="utf-8") == before


def test_chain_form_one_press_publishes_one_page(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_config(data_root, folders=["notes"])
    client = _client(monkeypatch, data_root)
    _patch_notes(tmp_path, monkeypatch)
    checkout = _checkout(tmp_path, monkeypatch)
    made = client.post("/api/chain/page", json={})
    assert made.status_code == 200, made.text
    body = made.json()
    assert body["ok"] is True
    cid = body["campaign_id"]
    first = FACT_TITLE
    second = BEARD_QUESTION
    assert first != CUT_QUESTION
    assert body["draft_path"].startswith("artifacts/")
    assert body["draft_path"].endswith(".md")
    assert (data_root / body["draft_path"]).is_file()
    assert PUBLIC_HOST not in made.text
    assert not str(body.get("sha") or "").startswith("http")
    stages = [step["stage"] for step in body["stages"]]
    assert stages == [
        "bind-site",
        "understand-aim",
        "plan",
        "external-fetch",
        "gather",
        "gate",
        "draft",
        "librarian",
        "diagram",
        "critic",
        "deliver",
        "push",
    ]
    assert [step["outcome"] for step in body["stages"]].count("ok") >= 1
    draft_step = next(step for step in body["stages"] if step["stage"] == "draft")
    assert draft_step["draft_path"] == body["draft_path"]
    assert body["published"][0]["question"] == first
    assert body["published"][0]["source"] == CUT_SOURCE
    assert KEYWORD not in first
    plan = load_plan(cid, paths=get_paths())
    assert plan is not None
    assert [item["question"] for item in plan["queue"]] == [first]
    assert second not in [item["question"] for item in plan["queue"]]
    slug = blog_slug(first)
    pages = list((checkout / "content" / "blog").glob("*.md"))
    assert [path.name for path in pages] == [f"{slug}.md"]
    published = pages[0].read_text(encoding="utf-8")
    draft = (data_root / body["draft_path"]).read_text(encoding="utf-8")
    for page in (published, draft):
        assert "## The problem" not in page
        assert "## How it works" not in page
        assert "## Spans" not in page
        assert "The gathered packet is what this page accounts for." not in page
        assert "This page is an account of the gathered packet." not in page
        assert "| --- |" not in page
        prose = page.split("\n---\n", 1)[1]
        assert not prose.lstrip().startswith("# ")
        assert "\n## " in prose
    assert not (checkout / "content" / "blog" / f"{blog_slug(second)}.md").exists()
    assert not list((checkout / "content" / "blog").glob("*-2.md"))
    loop = get_loop(cid)
    assert loop["status"] == "active"
    assert loop["status"] != "done"
    assert loop.get("next_wake_at")
    receipt = latest_receipt(cid, "push", outcome="ok")
    assert receipt is not None
    assert len(receipt["sha"]) == 40
    assert not receipt["sha"].startswith("http")
    assert loop.get("last_receipt") != receipt["sha"]
    second_draft = list((data_root / "artifacts").rglob(f"{blog_slug(second)}.md"))
    assert second_draft == []


def test_chain_form_refused_slug_is_not_shortened(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_config(data_root, folders=["notes"])
    with pytest.raises(SlugError):
        blog_slug(LONG_QUESTION)

    class _LongQuestion:
        def generate(self, *, system: str, contents: list[object], tools: object = None) -> CortexTurn:
            assert tools == []
            prompt = _prompt_text(contents)
            if "Excerpts:" in prompt or "Spans:\n" in prompt:
                return CortexTurn(text=_paragraph_page(prompt))
            if "Write one title a stranger would search." in prompt:
                return CortexTurn(text=LONG_QUESTION)
            return CortexTurn(text=_fact_or_path(prompt))

    client = _client(monkeypatch, data_root)
    monkeypatch.setattr("ada.memory.chain_plan.gemini_reader_model", lambda: _LongQuestion())
    root = tmp_path / "notes-repo"
    notes = root / "notes"
    notes.mkdir(parents=True)
    (notes / "a-cut.md").write_text(f"# A cut\n\n{LONG_QUESTION}\n", encoding="utf-8")
    monkeypatch.setattr("ada.memory.blog_packet.repo_root", lambda: root)
    _checkout(tmp_path, monkeypatch)
    saved = client.post("/api/chain/page", json={})
    assert saved.status_code == 200, saved.text
    body = saved.json()
    refused = [row for row in body["refusals"] if row["question"] == LONG_QUESTION]
    assert refused
    assert refused[0]["reason"] == "slug"
    assert refused[0]["question"] == LONG_QUESTION
    questions = [row["question"] for row in body["queue"]]
    assert LONG_QUESTION not in questions
    assert LONG_QUESTION[:80] not in questions
    assert all(not item.endswith("-2") for item in questions)
    assert questions == []
    plan = load_plan(body["campaign_id"], paths=get_paths())
    assert plan is not None
    stored = [item["question"] for item in plan["refusals"] if item["question"] == LONG_QUESTION]
    assert stored == [LONG_QUESTION]
    plan_text = (data_root / latest_receipt(body["campaign_id"], "plan", outcome="ok")["paths"][0]).read_text(
        encoding="utf-8"
    )
    assert "-2" not in plan_text
    loaded = yaml.safe_load(plan_text)
    assert [row["question"] for row in loaded["queue"]] == []
    assert any(row["question"] == LONG_QUESTION and row["reason"] == "slug" for row in loaded["refusals"])


def test_chain_form_accepts_a_reading_in_the_models_own_words(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_config(data_root, folders=["notes"])
    client = _client(monkeypatch, data_root)
    _patch_notes(tmp_path, monkeypatch)
    _checkout(tmp_path, monkeypatch)

    class _Reading:
        def generate(self, *, system: str, contents: list[object], tools: object = None) -> CortexTurn:
            assert tools == []
            prompt = _prompt_text(contents)
            if "Excerpts:" in prompt or "Spans:\n" in prompt:
                return CortexTurn(
                    text=(
                        "The file confirms the access date.\n\n"
                        "Dates in the notes include 1999.\n"
                    )
                )
            if "Write one title a stranger would search." in prompt and FACT_TITLE in prompt:
                return CortexTurn(text=FACT_TITLE)
            if "Return at most 3 paths" in prompt or "Fact:" in prompt:
                return CortexTurn(text=_fact_or_path(prompt))
            return CortexTurn(text=_short_question(prompt))

    monkeypatch.setattr("ada.memory.chain_plan.gemini_reader_model", lambda: _Reading())
    made = client.post("/api/chain/page", json={})
    body = made.json()
    assert "draft adds a fact" not in body["result_line"]
    draft = next(step for step in body["stages"] if step["stage"] == "draft")
    assert draft["outcome"] == "ok"
    assert "draft adds a fact" not in draft["reason"]
    critic = next(step for step in body["stages"] if step["stage"] == "critic")
    assert "not-an-account" not in critic["reason"]
    receipt = latest_receipt(body["campaign_id"], "critic")
    assert "not-an-account" not in ((receipt or {}).get("checks") or [])


def test_repair_button_wakes_existing_campaign_without_planner(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ada.hud import chain_form
    from ada.memory.chain_plan import open_chain_campaign, run_chain_wake

    _write_config(data_root)
    client = _client(monkeypatch, data_root)
    checkout = _checkout(tmp_path, monkeypatch)
    opened = open_chain_campaign()
    assert opened["ok"], opened
    cid = str(opened["id"])
    assert run_chain_wake(cid)["ok"]
    assert run_chain_wake(cid)["ok"]
    planned = run_chain_wake(
        cid,
        items=[{"source": SOURCE, "question": QUESTION, "fill": "researched"}],
    )
    assert planned["ok"], planned
    assert get_loop(cid)["current_stage"] == "external-fetch"

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("repair called the planner")

    monkeypatch.setattr(chain_form, "plan_source_questions", _boom)
    monkeypatch.setattr(chain_form, "open_chain_campaign", _boom)
    monkeypatch.setattr(chain_form, "queue_chain_sources", _boom)
    monkeypatch.setattr(chain_form, "publish_one_page", _boom)
    monkeypatch.setattr("ada.memory.chain_plan.question_from_model", _boom)
    monkeypatch.setattr("ada.memory.chain_plan.gemini_reader_model", _boom)
    repaired = client.post("/api/chain/repair", json={"campaign_id": cid})
    body = repaired.json()
    assert body["campaign_id"] == cid
    stages = [step["stage"] for step in body["stages"]]
    assert stages
    assert stages[0] == "external-fetch"
    assert "plan" not in stages
    assert "bind-site" not in stages
    assert str(checkout) != "/mnt/ada-data/aryan-portfolio"
    html = (Path(__file__).resolve().parents[1] / "src/ada/hud/templates/index.html").read_text(
        encoding="utf-8"
    )
    assert "Repair and publish" in html
    assert "Publish one page" in html
    assert "Add a source" not in html
    assert "chain-source" not in html


def test_chain_form_stops_on_critic_fail(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_config(data_root, folders=["notes"])
    client = _client(monkeypatch, data_root)
    _patch_notes(tmp_path, monkeypatch)
    checkout = _checkout(tmp_path, monkeypatch)
    from ada.hud import chain_form

    real = chain_form.run_chain_wake

    def _fail_critic(campaign_id: str, **kwargs: object) -> dict:
        loop = get_loop(campaign_id)
        assert loop is not None
        if loop["current_stage"] == "critic":
            return {
                "ok": False,
                "outcome": "fail",
                "checks": ["canonical"],
                "denied_reason": "canonical",
            }
        return real(campaign_id, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(chain_form, "run_chain_wake", _fail_critic)
    made = client.post("/api/chain/page", json={})
    assert made.status_code == 400, made.text
    body = made.json()
    assert body["stages"][-1]["stage"] == "critic"
    assert body["stages"][-1]["outcome"] == "fail"
    assert "canonical" in body["result_line"]
    assert "deliver" not in [step["stage"] for step in body["stages"]]
    assert "push" not in [step["stage"] for step in body["stages"]]
    assert [row["source"] for row in body["queue"]] == [CUT_SOURCE]
    assert body["queue"][0]["state"] == "stopped"
    assert not (checkout / "content" / "blog").exists()
    assert get_loop(body["campaign_id"])["status"] != "done"


def test_delete_without_confirmed_leaves_the_file(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _client(monkeypatch, data_root)
    checkout = _checkout(tmp_path, monkeypatch)
    stored = client.post(
        "/api/blog/step",
        json={
            "step": "store",
            "site": SITE,
            "audience": AUDIENCE,
            "source": BLOG_SOURCE,
            "question": QUESTION,
            "fill": "researched",
        },
    )
    assert stored.status_code == 200, stored.text
    cid = stored.json()["status"]["campaign_id"]
    gathered = client.post("/api/blog/step", json={"step": "gather", "campaign_id": cid})
    assert gathered.status_code == 200, gathered.text
    drafted = client.post("/api/blog/step", json={"step": "draft", "campaign_id": cid})
    assert drafted.status_code == 200, drafted.text
    slug = drafted.json()["slug"]
    dest = checkout / "content" / "blog" / f"{slug}.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("keep", encoding="utf-8")
    denied = client.post(
        "/api/blog/step",
        json={"step": "delete", "campaign_id": cid},
    )
    assert denied.status_code == 200, denied.text
    assert denied.json().get("needs_confirm") is True
    assert dest.read_text(encoding="utf-8") == "keep"
    assert not list((checkout / "content" / "blog").glob("*-2.md"))
