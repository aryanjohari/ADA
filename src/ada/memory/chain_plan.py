"""Chain campaign shell, bind, aim, and the plan artifact.

One wake advances one stage. The queue lives in the plan YAML, not on upsert_loop.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import yaml

from ada.io.atomic import atomic_write_text
from ada.io.paths import DataPaths, require_ada_data
from ada.memory.artifacts import write_artifact
from ada.memory.blog_packet import repo_root, source_file
from ada.memory.blog_slug import SlugError, blog_slug
from ada.memory.campaign_page import SITE, SHELL_TEXT, next_wake_iso, one_sentence
from ada.memory.chain_receipt import append_stage_receipt, latest_receipt
from ada.memory.open_loops import get_loop, upsert_loop
from ada.memory.portfolio_chain import read_portfolio_chain
from ada.tools.blog_tools import CheckoutError, resolve_portfolio_checkout

CHAIN_STAGES = (
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
)
_SECTION1 = re.compile(r"(?m)^## 1\. Question\s*\n+(.+)")
_ACCESS_DATE_LINE = re.compile(r"(?i)^access date\b")
_DOORWAY = re.compile(
    r"service[- ]area|\b(?:city|suburb)\s+grid\b|\bsuburbs\b|\bcities\b",
    re.I,
)
_FUNNEL = re.compile(r"\bfunnels?\b|\bfunnel(?:ing|ling)\b", re.I)
_SUGGESTION_TAGS = frozenset({"marketing", "hunch"})
_WORD = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?")
_FRAME = frozenset(
    """
    what does this file answer about how can a an the for of to and in on with
    from that reader page show work when where why who is are do did which
    should one
    """.split()
)
_READER_SYSTEM = (
    "You write one short question a stranger would ask. "
    "Reply with that question only."
)
_TITLE_SYSTEM = (
    "You write one title a stranger would search. "
    "Reply with that title only."
)
_BRIEF_SYSTEM = (
    "You write the idea for one page: who it is for, what it will explain, "
    "and which sources it will use. The idea is not the title and it is not the page. "
    "Reply with those sentences only."
)
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _deny(reason: str) -> dict[str, Any]:
    return {
        "ok": False,
        "outcome": "denied",
        "denied_reason": reason,
        "error": reason,
    }


def _stage_ids(loop: dict[str, Any]) -> list[str]:
    return [str(stage.get("id") or "") for stage in (loop.get("stages") or [])]


def is_chain_loop(loop: dict[str, Any] | None) -> bool:
    return bool(loop) and _stage_ids(loop or {}) == list(CHAIN_STAGES)


def open_chain_campaign(*, paths: DataPaths | None = None) -> dict[str, Any]:
    """Mint a campaign whose stages are the twelve chain ids. No page fields."""
    p = paths or require_ada_data()
    stages = [{"id": stage, "state": "pending"} for stage in CHAIN_STAGES]
    stages[0]["state"] = "active"
    created = upsert_loop(
        text=SHELL_TEXT,
        title=SHELL_TEXT,
        kind="campaign",
        status="active",
        stages=stages,
        current_stage=CHAIN_STAGES[0],
        next_wake_at=next_wake_iso(),
        paths=p,
    )
    if not created.get("ok"):
        return created
    loop = created.get("loop") or {}
    return {"ok": True, "outcome": "ok", "id": str(loop.get("id") or ""), "loop": loop}


def _require_chain(campaign_id: str, stage: str, paths: DataPaths) -> dict[str, Any] | None:
    loop = get_loop(campaign_id, paths=paths)
    if not is_chain_loop(loop):
        return _deny("not a chain campaign")
    if str(loop.get("current_stage") or "") != stage:
        return _deny(f"{stage} is not the current stage")
    return None


def _rewrite_stages(
    campaign_id: str,
    *,
    paths: DataPaths,
    current: str,
    done: set[str] | None = None,
    active: str | None = None,
    pending: set[str] | None = None,
    status: str = "active",
) -> dict[str, Any]:
    loop = get_loop(campaign_id, paths=paths) or {}
    stages: list[dict[str, str]] = []
    for raw in loop.get("stages") or []:
        stage = {"id": str(raw.get("id") or ""), "state": str(raw.get("state") or "pending")}
        if done and stage["id"] in done:
            stage["state"] = "done"
        if pending and stage["id"] in pending:
            stage["state"] = "pending"
        if active and stage["id"] == active:
            stage["state"] = "active"
        stages.append(stage)
    return upsert_loop(
        loop_id=campaign_id,
        stages=stages,
        current_stage=current,
        next_wake_at=next_wake_iso(),
        status=status,
        paths=paths,
    )


def finish_stage(
    campaign_id: str,
    stage: str,
    *,
    paths: DataPaths,
    outcome: str,
    slug: str = "",
    receipt_paths: list[str] | None = None,
    sha: str = "",
    checks: list[str] | None = None,
    remove: list[str] | None = None,
    deliver_block: bool = False,
    advance: bool = True,
    status: str = "active",
) -> dict[str, Any]:
    append_stage_receipt(
        campaign_id,
        {
            "stage": stage,
            "slug": slug,
            "outcome": outcome,
            "paths": receipt_paths or [],
            "sha": sha,
            "checks": checks or [],
            "remove": remove or [],
            "deliver_block": deliver_block,
        },
        paths=paths,
    )
    if advance and outcome in {"ok", "pass", "skip"}:
        idx = CHAIN_STAGES.index(stage)
        nxt = CHAIN_STAGES[idx + 1] if idx + 1 < len(CHAIN_STAGES) else stage
        updated = _rewrite_stages(
            campaign_id,
            paths=paths,
            current=nxt,
            done={stage},
            active=nxt if nxt != stage else None,
            status=status,
        )
    else:
        updated = upsert_loop(
            loop_id=campaign_id,
            next_wake_at=next_wake_iso(),
            status=status,
            paths=paths,
        )
    if not updated.get("ok"):
        return updated
    return {"ok": outcome in {"ok", "pass", "skip"}, "outcome": outcome, "id": campaign_id}


def utc_day() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def plan_rel(campaign_id: str) -> str:
    return f"{utc_day()}/{campaign_id}.plan.yaml"


def load_plan(campaign_id: str, *, paths: DataPaths) -> dict[str, Any] | None:
    receipt = latest_receipt(campaign_id, "understand-aim", outcome="ok", paths=paths)
    if receipt is None:
        receipt = latest_receipt(campaign_id, "plan", outcome="ok", paths=paths)
    if receipt is None or not receipt.get("paths"):
        return None
    rel = str(receipt["paths"][0])
    if rel.startswith("artifacts/"):
        rel = rel[len("artifacts/") :]
    path = (paths.artifacts / rel).resolve()
    try:
        path.relative_to(paths.artifacts.resolve())
    except ValueError:
        return None
    if not path.is_file():
        return None
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return None
    raw["_path"] = str(path)
    raw["_rel"] = f"artifacts/{rel}"
    return raw


def save_plan(plan: dict[str, Any], *, paths: DataPaths) -> None:
    path = Path(str(plan.get("_path") or ""))
    stored = {key: value for key, value in plan.items() if not key.startswith("_")}
    text = yaml.safe_dump(
        stored,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )
    atomic_write_text(path, text)


def current_item(plan: dict[str, Any]) -> dict[str, Any] | None:
    queue = plan.get("queue")
    if not isinstance(queue, list) or not queue:
        return None
    item = queue[0]
    return item if isinstance(item, dict) else None


def _published_questions(checkout: Path) -> set[str]:
    blog = checkout / "content" / "blog"
    if not blog.is_dir():
        return set()
    found: set[str] = set()
    for path in blog.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            continue
        end = text.find("\n---\n", 4)
        if end < 0:
            continue
        data = yaml.safe_load(text[4:end])
        if isinstance(data, dict) and str(data.get("question") or "").strip():
            found.add(str(data["question"]).strip())
    return found


def _section1(text: str) -> str:
    match = _SECTION1.search(text)
    if match is None:
        return ""
    return match.group(1).strip().splitlines()[0].strip()


def _is_doorway_grid(*parts: str) -> bool:
    """A city or suburb list that funnels to one page. A proven service is not one."""
    text = " ".join(part for part in parts if part)
    if _DOORWAY.search(text):
        return True
    return bool(_FUNNEL.search(text) and text.count(",") >= 1)


def _copies_keyword(question: str, banned: set[str]) -> bool:
    folded = question.casefold()
    for text in banned:
        token = text.casefold().strip()
        if token and (folded == token or token in folded):
            return True
    return False


def _is_search_url(url: str) -> bool:
    from ada.memory.chain_fetch import is_search_url

    return is_search_url(url)


def section1_refusals() -> list[dict[str, str]]:
    """Log research-card questions that blog_slug refuses. Do not shorten them."""
    root = repo_root() / "docs" / "research"
    refusals: list[dict[str, str]] = []
    if not root.is_dir():
        return refusals
    for path in sorted(root.glob("*.md")):
        question = _section1(path.read_text(encoding="utf-8"))
        if not question:
            continue
        try:
            blog_slug(question)
        except SlugError:
            rel = str(path.relative_to(repo_root()))
            refusals.append({"question": question, "source": rel, "reason": "slug"})
    return refusals


def wake_bind_site(
    campaign_id: str,
    *,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    """Read the checkout origin and the config site. Do not write the checkout."""
    p = paths or require_ada_data()
    blocked = _require_chain(campaign_id, "bind-site", p)
    if blocked:
        return blocked
    config = read_portfolio_chain(paths=p)
    if not config.get("ok"):
        finish_stage(
            campaign_id,
            "bind-site",
            paths=p,
            outcome="denied",
            advance=False,
        )
        return config
    if str(config["config"].get("site") or "") != SITE:
        finish_stage(
            campaign_id,
            "bind-site",
            paths=p,
            outcome="denied",
            advance=False,
        )
        return _deny(f"site must be {SITE}")
    try:
        checkout = resolve_portfolio_checkout()
    except CheckoutError as exc:
        finish_stage(
            campaign_id,
            "bind-site",
            paths=p,
            outcome="denied",
            advance=False,
        )
        return _deny(str(exc))
    return finish_stage(
        campaign_id,
        "bind-site",
        paths=p,
        outcome="ok",
        receipt_paths=[str(checkout)],
    )


def wake_understand_aim(
    campaign_id: str,
    *,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    """Copy audience and aims onto the plan artifact. Do not invent either."""
    p = paths or require_ada_data()
    blocked = _require_chain(campaign_id, "understand-aim", p)
    if blocked:
        return blocked
    config = read_portfolio_chain(paths=p)
    if not config.get("ok"):
        finish_stage(
            campaign_id,
            "understand-aim",
            paths=p,
            outcome="denied",
            advance=False,
        )
        return config
    cfg = config["config"]
    aim = str(cfg.get("aim") or "").strip()
    if not cfg.get("audience") or not aim:
        finish_stage(
            campaign_id,
            "understand-aim",
            paths=p,
            outcome="denied",
            advance=False,
        )
        return _deny("audience and aim are required")
    doc = {
        "campaign_id": campaign_id,
        "audience": cfg["audience"],
        "aim": aim,
        "aims": [aim],
        "suggestions": [],
        "refusals": [],
        "queue": [],
    }
    body = yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)
    rel = plan_rel(campaign_id)
    written = write_artifact(
        title="chain plan",
        body=body,
        format="md",
        source_cites=None,
        relative_path=rel,
        campaign_id=None,
        paths=p,
    )
    if not written.get("ok"):
        finish_stage(
            campaign_id,
            "understand-aim",
            paths=p,
            outcome="denied",
            advance=False,
        )
        return written
    return finish_stage(
        campaign_id,
        "understand-aim",
        paths=p,
        outcome="ok",
        receipt_paths=[str(written.get("path") or f"artifacts/{rel}")],
    )


def _suggestion_rows(raw: list[dict[str, Any]] | None) -> tuple[list[dict[str, str]], str | None]:
    rows: list[dict[str, str]] = []
    for item in raw or []:
        if not isinstance(item, dict):
            return [], "suggestion tag must be marketing or hunch"
        text = str(item.get("text") or "").strip()
        tag = str(item.get("tag") or "").strip()
        if not text or tag not in _SUGGESTION_TAGS:
            return [], "suggestion tag must be marketing or hunch"
        rows.append({"text": text, "tag": tag})
    return rows, None


def missing_content_word(text: str, source: str) -> str | None:
    """A content word in ``text`` that is not in ``source``. Frame words do not count."""
    folded = source.casefold()
    for word in _WORD.findall(text or ""):
        token = word.casefold()
        if token in _FRAME:
            continue
        if token not in folded:
            return token
    return None


_URL_IN_TEXT = re.compile(r"https?://[^\s<>\[\]()\"'`]+", re.I)
_HOST_IN_TEXT = re.compile(r"\b(?:[a-z0-9-]+\.)+[a-z]{2,}\b", re.I)
_NUMBER_IN_TEXT = re.compile(r"\d+")
_MONTH_IN_TEXT = re.compile(
    r"\b(?:january|february|march|april|june|july|august|september|october|november|december)\b",
    re.I,
)


def _added_fact(question: str, file_text: str) -> str:
    """Why a title adds a fact, or an empty string when it does not.

    A title may use the words a stranger would search. Those words do not
    have to appear in the fact or the stored passages. A new URL, host, date,
    or number is still refused.
    """
    text = question or ""
    source = file_text or ""
    folded = source.casefold()
    for url in _URL_IN_TEXT.findall(text):
        cleaned = url.rstrip(".,;:!?")
        if cleaned and cleaned not in source:
            return "title adds a url that is not in the notes"
    for host in _HOST_IN_TEXT.findall(text):
        if host.casefold() not in folded:
            return "title adds a host that is not in the notes"
    for date in _ISO_DATE.findall(text):
        if date not in source:
            return "title adds a date that is not in the notes"
    for month in _MONTH_IN_TEXT.findall(text):
        if month.casefold() not in folded:
            return "title adds a date that is not in the notes"
    for number in _NUMBER_IN_TEXT.findall(text):
        if number not in source:
            return "title adds a number that is not in the notes"
    return ""


def question_adds_fact(question: str, file_text: str) -> bool:
    """True when the title adds a URL, host, date, or number.

    A title may use the words a stranger would search. Those words do not
    have to appear in the fact or the stored passages.
    """
    return bool(_added_fact(question, file_text))


def _access_date_only(line: str) -> bool:
    """True when the line only records an access date."""
    text = " ".join(line.split())
    if not _ACCESS_DATE_LINE.match(text):
        return False
    return len(re.findall(r"[.!?]", text)) <= 1


def _split_sentences(text: str) -> list[str]:
    """Split on sentence punctuation. A dot inside https:// or backticks stays.

    A period that ends the sentence after a URL is still a sentence end.
    Nothing here is invented.
    """
    if not text:
        return []
    protected = bytearray(len(text))
    for match in re.finditer(r"`[^`]*`", text):
        for index in range(match.start(), match.end()):
            protected[index] = 1
    for match in re.finditer(r"https?://[^\s<>\[\]()\"'`]+", text):
        url = match.group(0).rstrip(".,;:!?")
        end = match.start() + len(url)
        for index in range(match.start(), end):
            protected[index] = 1
    chunks: list[str] = []
    start = 0
    for index, char in enumerate(text):
        if char in ".!?" and not protected[index]:
            chunks.append(text[start : index + 1])
            start = index + 1
    if start < len(text) and text[start:].strip():
        chunks.append(text[start:])
    return chunks


def _sentences_in_line(line: str, file_text: str) -> list[str]:
    """Sentences already written on this line. None are invented."""
    cleaned = line.strip().strip("`").strip("\"'").strip()
    if not cleaned:
        return []
    chunks = _split_sentences(cleaned) or [cleaned]
    found: list[str] = []
    for chunk in chunks:
        sentence = " ".join(chunk.split())
        if len(sentence.split()) < 2 or sentence not in file_text:
            continue
        found.append(sentence)
    return found


def deterministic_question(file_text: str, *, audience: str, aim: str) -> str:
    """The line under ``## 1. Question``, or one sentence already in the file.

    A longer question is returned whole. This function does not shorten it
    and does not wrap the first words. A line that only records an access
    date is not the sentence. Nothing here is invented.
    """
    if not str(audience).strip() or not str(aim).strip():
        return ""
    card = _section1(file_text).strip()
    if card:
        return card
    for line in file_text.splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or raw.startswith("|") or raw.startswith("```"):
            continue
        if _access_date_only(raw):
            continue
        for sentence in _sentences_in_line(raw, file_text):
            if _access_date_only(sentence):
                continue
            return sentence
    return ""


def gemini_reader_model() -> Any:
    """The Gemini adapter. Tests pass a fake with generate() and make no network call."""
    from ada.cortex.gemini import GeminiAdapter
    from ada.secrets.load import load_gemini_api_key

    return GeminiAdapter(api_key=load_gemini_api_key())


def question_from_model(
    model: Any,
    *,
    file_text: str,
    audience: str,
    aim: str,
) -> str:
    """Ask an adapter with GeminiAdapter.generate's signature. Adds no tool call."""
    from ada.cortex.gemini import user_content

    prompt = (
        f"Audience: {audience}\n"
        f"Aim: {aim}\n"
        "\n"
        "Write one short question a stranger would ask.\n"
        "One sentence. Plain words.\n"
        "Every content word must already be in the file.\n"
        'Do not copy the line under "## 1. Question".\n'
        "Do not copy a keyword.\n"
        "Do not use an access-date stamp, a repo path, or a machine name.\n"
        "\n"
        f"{file_text}"
    )
    turn = model.generate(
        system=_READER_SYSTEM,
        contents=[user_content(prompt)],
        tools=[],
    )
    return str(getattr(turn, "text", "") or "").strip()


def _same_text(left: str, right: str) -> bool:
    return " ".join((left or "").casefold().split()) == " ".join((right or "").casefold().split())


def _unknown_lines(text: str) -> list[str]:
    """Lines that mark a claim unknown. A plain question is not one of these."""
    found: list[str] = []
    for line in (text or "").splitlines():
        raw = line.strip()
        if not raw:
            continue
        if raw.startswith("**UNKNOWN"):
            found.append(raw)
        elif re.search(r"\bis \*\*UNKNOWN\*\*", raw) or re.search(r"\bis UNKNOWN\b", raw):
            found.append(raw)
    return found


def _question_words(question: str) -> list[str]:
    words: list[str] = []
    for word in _WORD.findall(question or ""):
        token = word.casefold()
        if token in _FRAME or len(token) <= 3 or token in words:
            continue
        words.append(token)
    return words


def _line_has_words(line: str, words: list[str]) -> bool:
    folded = line.casefold()
    return bool(words) and all(re.search(rf"(?<![a-z0-9]){re.escape(word)}(?![a-z0-9])", folded) for word in words)


def research_frame_question(question: str, source_text: str) -> bool:
    """The line under ``## 1. Question`` is a research frame, not a title."""
    frame = _section1(source_text).strip()
    return bool(frame) and _same_text(question, frame)


def copied_from_unknown(question: str, source_text: str) -> bool:
    """A question whose content words are the UNKNOWN line."""
    words = _question_words(question)
    return any(_line_has_words(line, words) for line in _unknown_lines(source_text))


def from_tagged_line(question: str, source_text: str, kept: str) -> bool:
    """A second question invented from a POLICY or UNKNOWN line in the file.

    Words already in the stored paragraph are the fact, not that line.
    """
    words = _question_words(question)
    if not words:
        return False
    if _line_has_words(kept, words):
        return False
    tagged: list[str] = []
    for line in (source_text or "").splitlines():
        raw = line.strip()
        if raw.startswith("**UNKNOWN") or raw.startswith("**POLICY"):
            tagged.append(raw)
        elif re.search(r"\bis \*\*UNKNOWN\*\*", raw) or re.search(r"\bis UNKNOWN\b", raw):
            tagged.append(raw)
    return any(_line_has_words(line, words) for line in tagged)


def plain_operator_question(question: str, source_text: str, fact: str) -> bool:
    """The YAML question is a frame. It is not put on the page.

    ``Where is this work published?`` is a frame. It is refused as the title
    whenever a model is present. The line under ``## 1. Question``, a question
    copied from an UNKNOWN line, and the fact's date sentence are not titles.
    """
    text = " ".join((question or "").split())
    if not text:
        return False
    if research_frame_question(text, source_text):
        return False
    if copied_from_unknown(text, source_text):
        return False
    dated = fact_date_sentence(fact)
    if dated and _same_text(text, dated):
        return False
    return False


def brief_from_yaml(
    *,
    audience: str,
    aim: str,
    fact: str,
    offer: str = "",
    proof: str = "",
) -> str:
    """Sentences already written in the audience, the aim, the offer, and the fact."""
    found: list[str] = []
    for text in (fact, audience, aim, offer, proof):
        for line in (text or "").splitlines():
            raw = line.strip()
            if not raw or raw.startswith("#"):
                continue
            for sentence in _sentences_in_line(raw, text):
                if _access_date_only(sentence) or sentence in found:
                    continue
                found.append(sentence)
    return " ".join(found)


def fact_date_sentence(fact: str) -> str:
    """The fact sentence that carries a calendar date. An ordinary sentence is not one."""
    text = " ".join((fact or "").split())
    if not text or _ISO_DATE.search(text) is None:
        return ""
    chunks = _split_sentences(text) or [text]
    for chunk in chunks:
        sentence = " ".join(chunk.split())
        if sentence and _ISO_DATE.search(sentence):
            return sentence
    return ""


def brief_from_model(
    model: Any,
    *,
    audience: str,
    aim: str,
    fact: str,
    offer: str = "",
    proof: str = "",
    sources: str = "",
) -> str:
    """One new prompt. It writes the idea. It does not receive the previous prompt.

    The idea says who the page is for, what the page will explain, and which
    sources it will use. The fact is evidence the page may cite. It is not
    the subject and it is not the title. A YAML question is not a frame.
    The idea is not the page.
    """
    from ada.cortex.gemini import user_content

    prompt = (
        f"Audience: {audience}\n"
        f"Aim: {aim}\n"
        f"Offer: {offer}\n"
        f"Proof:\n{proof}\n"
        f"Fact: {fact}\n"
        "The fact is evidence the page may cite.\n"
        "It is not the subject and it is not the title.\n"
        "\n"
        "Sources:\n"
        f"{sources}\n"
        "\n"
        "Write the idea.\n"
        "Who the page is for, what the page will explain, and which sources it will use.\n"
        "Ordinary words are allowed.\n"
        "Do not write the title.\n"
        "Do not write the page.\n"
        "Do not search the web.\n"
    )
    turn = model.generate(
        system=_BRIEF_SYSTEM,
        contents=[user_content(prompt)],
        tools=[],
    )
    return str(getattr(turn, "text", "") or "").strip()


def _stored_question(
    fact: str,
    notes: str,
    yaml_question: str,
    source_text: str = "",
) -> str:
    """One sentence already in the fact or the opened passages.

    The YAML question is not substituted. ``What is a cut?`` is not the title
    when the fact already states the service. The fact's date sentence is not
    the title. A slug that does not fit is kept whole by the caller.
    """
    corpus = f"{fact}\n{notes}"
    dated = fact_date_sentence(fact)
    plain_fact = " ".join((fact or "").split())
    if (
        plain_fact
        and not dated
        and one_sentence(plain_fact)
        and not _same_text(plain_fact, yaml_question)
        and not research_frame_question(plain_fact, source_text)
        and (plain_fact in corpus or plain_fact in (notes or ""))
    ):
        return plain_fact
    found: list[str] = []
    for line in (notes or "").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or raw.startswith("|") or raw.startswith("```"):
            continue
        if _access_date_only(raw):
            continue
        for sentence in _sentences_in_line(raw, notes):
            if _access_date_only(sentence) or _same_text(sentence, yaml_question):
                continue
            if research_frame_question(sentence, source_text):
                continue
            if dated and _same_text(sentence, dated):
                continue
            if not one_sentence(sentence) or question_adds_fact(sentence, corpus):
                continue
            if sentence not in found:
                found.append(sentence)
    return found[0] if found else ""


def _paragraphs_text(note_rows: list[dict[str, Any]]) -> str:
    """The stored sections, or the paragraph, or the catalog sentences."""
    parts: list[str] = []
    for row in note_rows:
        section = str(row.get("section") or "").strip()
        if section:
            parts.append(section)
            continue
        paragraph = str(row.get("paragraph") or "").strip()
        if paragraph:
            parts.append(paragraph)
            continue
        for sentence in row.get("sentences") or []:
            text = str(sentence).strip()
            if text and text not in parts:
                parts.append(text)
    return "\n".join(parts)


def title_from_model(
    model: Any,
    *,
    brief: str,
    paragraphs: str,
) -> str:
    """One new call. It sees the idea and the stored passages, not the prior prompt."""
    from ada.cortex.gemini import user_content

    prompt = (
        f"Idea:\n{brief}\n"
        "\n"
        "Passages:\n"
        f"{paragraphs}\n"
        "\n"
        "Write one title a stranger would search.\n"
        "Ordinary words are allowed.\n"
        "The title may use the words a stranger would type, and it does not have to reuse the wording of the passages.\n"
        "The title still has to name what those passages say, and must not promise a guide, a definition, or a procedure the passages do not contain.\n"
        "The title does not have to be a question.\n"
        "Do not copy the YAML question.\n"
        'Do not copy "## 1. Question".\n'
        "Do not copy an UNKNOWN line.\n"
        "Do not use the date sentence.\n"
    )
    turn = model.generate(
        system=_TITLE_SYSTEM,
        contents=[user_content(prompt)],
        tools=[],
    )
    return str(getattr(turn, "text", "") or "").strip()


def _title_deny(reason: str, source: str, question: str = "") -> dict[str, Any]:
    return {
        "ok": False,
        "deny": reason,
        "items": [],
        "refusals": [{"question": question, "source": source, "reason": reason}],
    }


def _catalog_text(rows: list[dict[str, Any]]) -> str:
    """The catalog the idea may name. Each row stays a path, a heading, and sentences."""
    lines: list[str] = []
    for row in rows:
        lines.append(f"path: {row.get('path') or ''}")
        lines.append(f"heading: {row.get('heading') or ''}")
        lines.append("sentences: " + " ".join(str(sentence) for sentence in (row.get("sentences") or [])))
        lines.append("")
    return "\n".join(lines).strip()


def _title_refusal(
    candidate: str,
    *,
    fact: str,
    paragraphs: str,
    yaml_question: str,
    source_text: str,
) -> str:
    """Why this title is refused, or an empty string when it may be queued."""
    text = " ".join((candidate or "").split())
    if not text:
        return "no sentence in the fact or the notes"
    if _same_text(text, yaml_question) or research_frame_question(text, source_text):
        return "refusing the YAML question"
    if _same_text(text, "Where is this work published?"):
        return "refusing the YAML question"
    if copied_from_unknown(text, source_text) or from_tagged_line(text, source_text, paragraphs):
        return "refusing a question from an UNKNOWN line"
    dated = fact_date_sentence(fact)
    if dated and _same_text(text, dated):
        return "the date sentence is not the title"
    if not one_sentence(text):
        return "no sentence in the fact or the notes"
    added = _added_fact(text, f"{fact}\n{paragraphs}")
    if added:
        return added
    if plain_operator_question(text, source_text, fact):
        return "refusing the YAML question"
    return ""


def published_pages_path(paths: DataPaths) -> Path:
    return paths.facts / "published_pages.yaml"


def _same_page(left: str, right: str) -> bool:
    def norm(value: str) -> str:
        return " ".join((value or "").casefold().split()).rstrip(".!?")

    return bool(norm(left)) and norm(left) == norm(right)


def read_published_pages(*, paths: DataPaths) -> list[str]:
    """Pages already published. Does not read a YAML question and appends nothing."""
    path = published_pages_path(paths)
    if not path.is_file():
        return []
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    pages = raw.get("pages") if isinstance(raw, dict) else None
    if not isinstance(pages, list):
        return []
    found: list[str] = []
    for item in pages:
        text = " ".join(str(item).split())
        if text and not any(_same_page(text, earlier) for earlier in found):
            found.append(text)
    return found


def record_published_page(page: str, *, paths: DataPaths) -> None:
    """Remember one published page. Does not append a fact and does not edit the operator file."""
    text = " ".join((page or "").split())
    if not text:
        return
    pages = read_published_pages(paths=paths)
    if any(_same_page(text, earlier) for earlier in pages):
        return
    pages.append(text)
    path = published_pages_path(paths)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(
        path,
        yaml.safe_dump({"pages": pages}, sort_keys=False, allow_unicode=True),
    )


def _published_card(path: str, published: list[str]) -> bool:
    return any(path == earlier or _same_page(path, earlier) for earlier in published)


def _list_cards(folders: list[str]) -> list[dict[str, Any]]:
    """Markdown cards in the configured folders. Does not name one source file."""
    from ada.memory import blog_packet
    from ada.memory.chain_fetch import _catalog_row, _skipped

    root = blog_packet.repo_root().resolve()
    found: list[Path] = []
    for folder in folders:
        base = (root / str(folder)).resolve()
        try:
            base.relative_to(root)
        except ValueError:
            continue
        if not base.is_dir():
            continue
        for path in base.rglob("*.md"):
            if not path.is_file():
                continue
            try:
                rel = path.resolve().relative_to(root)
            except ValueError:
                continue
            if _skipped(rel):
                continue
            found.append(path)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in sorted(found, key=lambda item: item.as_posix()):
        row = _catalog_row(path, root)
        if row is None or row["path"] in seen:
            continue
        seen.add(row["path"])
        rows.append(row)
    return rows


def _keep_teaching(
    paths: list[str],
    by_path: dict[str, dict[str, Any]],
    sentences: list[str],
    passage: str,
) -> list[dict[str, Any]]:
    """At most three notes that teach the page, and the passage each one stores."""
    from ada.memory.chain_fetch import _row_teaches

    notes: list[dict[str, Any]] = []
    for path in paths:
        if len(notes) >= 3:
            break
        row = by_path.get(path)
        if row is None:
            continue
        if not _row_teaches(row, sentences, passage):
            continue
        note = row.get("_note")
        if not isinstance(note, dict):
            continue
        stored = dict(note)
        stored["path"] = path
        notes.append(stored)
    return notes


def plan_one_page(
    cfg: dict[str, Any],
    *,
    model: Any | None = None,
    published: list[str] | None = None,
) -> dict[str, Any]:
    """Choose the next unpublished card, then the notes, the passages, and the title.

    Reads the whole config. Lists the markdown cards in the card folders,
    skips a card already recorded in published pages, and chooses one
    remaining card that has a passage. Opens at most three notes that teach
    that page and stores those passages. The title may use the words a
    stranger would type, and it has to name what the passages say. A new
    URL, host, date, or number is still refused. Does not search the web,
    does not append a fact, and does not start from one named source file.
    One page.
    """
    from ada.memory.chain_fetch import choose_notes

    folders = [str(folder).strip() for folder in (cfg.get("folders") or []) if str(folder).strip()]
    already = list(published or [])
    rows = _list_cards(folders)
    if not rows:
        return _title_deny("no card", "")
    by_path = {str(row.get("path") or ""): row for row in rows}
    refusals: list[dict[str, str]] = []
    published_hits = 0
    card = ""
    sentences: list[str] = []
    for row in rows:
        path = str(row.get("path") or "")
        if not path:
            continue
        if _published_card(path, already):
            published_hits += 1
            refusals.append({"question": "", "source": path, "reason": "published"})
            continue
        held = [str(sentence).strip() for sentence in (row.get("sentences") or []) if str(sentence).strip()]
        if not held:
            continue
        try:
            text = source_file(path).read_text(encoding="utf-8")
        except (ValueError, FileNotFoundError, OSError):
            refusals.append({"question": "", "source": path, "reason": "missing-source"})
            continue
        if _is_doorway_grid(text, str(row.get("heading") or "")):
            refusals.append({"question": "", "source": path, "reason": "service-area"})
            continue
        card = path
        sentences = held
        break
    if not card:
        if published_hits:
            return {
                "ok": True,
                "deny": "that page is already published",
                "items": [],
                "refusals": refusals,
            }
        return {
            "ok": False,
            "deny": "no sentence in the card",
            "items": [],
            "refusals": refusals,
        }
    passage = "\n".join(sentences)
    if model is None:
        order = [card] + [path for path in by_path if path != card]
    else:
        chosen = choose_notes(
            model,
            brief=passage,
            rows=rows,
            fact=sentences[0],
            facts=sentences,
        )
        picked = list(chosen.get("files") or []) if chosen.get("ok") else []
        order = [card] + [path for path in picked if path != card]
    note_rows = _keep_teaching(order, by_path, sentences, passage)
    if not note_rows:
        return _title_deny("no sentence in the notes", card)
    files = [str(row.get("path") or "") for row in note_rows if str(row.get("path") or "")]
    paragraphs = _paragraphs_text(note_rows)
    source_parts: list[str] = []
    for path in files:
        try:
            source_parts.append(source_file(path).read_text(encoding="utf-8"))
        except (ValueError, FileNotFoundError, OSError):
            continue
    source_text = "\n".join(source_parts)
    fact_text = "\n".join(sentences)
    if model is None:
        question = _stored_question(fact_text, paragraphs, "", source_text)
        if not question:
            return _title_deny("no sentence in the fact or the notes", card)
    else:
        question = title_from_model(model, brief=passage, paragraphs=paragraphs).strip()
        refused = _title_refusal(
            question,
            fact=fact_text,
            paragraphs=paragraphs,
            yaml_question="",
            source_text=source_text,
        )
        if refused:
            return _title_deny(refused, card, question)
    item = {
        "question": question,
        "page": card,
        "card": card,
        "fact": fact_text,
        "source": card,
        "fill": "researched",
        "local_files": files,
        "brief": paragraphs or passage,
        "notes": note_rows,
        "paragraphs": paragraphs,
    }
    try:
        blog_slug(question)
    except SlugError:
        return {"ok": True, "deny": "", "items": [item], "refusals": refusals}
    return {"ok": True, "deny": "", "items": [item], "refusals": refusals}


def plan_source_questions(
    sources: list[dict[str, Any]] | None,
    *,
    audience: str,
    aim: str,
    model: Any | None = None,
) -> dict[str, Any]:
    """One title per named source. wake_plan still queues only what it is given.

    When a model is given, ask it for the title even if the file has a line
    under ``## 1. Question``. That question is one short sentence a stranger
    would ask, in words already in the file.
    With no model, the title is the line under ``## 1. Question``, or one
    sentence already in the file. An access-date stamp is not that sentence.
    A keyword is a hunch suggestion and is not copied into question.
    A question whose slug is too long is returned whole, for wake_plan to log as slug.
    """
    items: list[dict[str, str]] = []
    refusals: list[dict[str, str]] = []
    suggestions: list[dict[str, str]] = []
    seen_keywords: set[str] = set()
    for raw in sources or []:
        if not isinstance(raw, dict):
            continue
        source = str(raw.get("source") or "").strip()
        fill = str(raw.get("fill") or "").strip()
        keyword = str(raw.get("keyword") or "").strip()
        if keyword and keyword not in seen_keywords:
            seen_keywords.add(keyword)
            suggestions.append({"text": keyword, "tag": "hunch"})
        if not source and not fill and not keyword:
            continue
        try:
            file_text = source_file(source).read_text(encoding="utf-8")
        except (ValueError, FileNotFoundError, OSError):
            refusals.append({"question": "", "source": source, "reason": "missing-source"})
            continue
        if model is None:
            question = deterministic_question(file_text, audience=audience, aim=aim)
        else:
            question = question_from_model(
                model,
                file_text=file_text,
                audience=audience,
                aim=aim,
            )
        question = question.strip()
        if not question:
            refusals.append({"question": question, "source": source, "reason": "question"})
            continue
        if keyword and keyword.casefold() in question.casefold():
            refusals.append({"question": question, "source": source, "reason": "keyword"})
            continue
        try:
            blog_slug(question)
        except SlugError:
            items.append({"question": question, "source": source, "fill": fill})
            continue
        if not one_sentence(question):
            refusals.append({"question": question, "source": source, "reason": "sentence"})
            continue
        if question_adds_fact(question, file_text):
            refusals.append({"question": question, "source": source, "reason": "fact"})
            continue
        items.append({"question": question, "source": source, "fill": fill})
    return {
        "ok": True,
        "outcome": "ok",
        "items": items,
        "suggestions": suggestions,
        "refusals": refusals,
    }


def wake_plan(
    campaign_id: str,
    *,
    items: list[dict[str, Any]] | None = None,
    suggestions: list[dict[str, Any]] | None = None,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    """Queue one page from the next unpublished card. A keyword stays off the title.

    With no items argument, the plan reads the whole file, chooses one
    remaining card that has a passage, and queues that page. It does not
    append a fact and does not start from one named source file. An explicit
    items list is the form path and is not a second page from a named source.
    """
    p = paths or require_ada_data()
    blocked = _require_chain(campaign_id, "plan", p)
    if blocked:
        return blocked
    plan = load_plan(campaign_id, paths=p)
    config = read_portfolio_chain(paths=p)
    if plan is None or not config.get("ok"):
        finish_stage(campaign_id, "plan", paths=p, outcome="denied", advance=False)
        return _deny("plan artifact is missing")
    cfg = config["config"]
    suggestion_rows, suggestion_err = _suggestion_rows(suggestions)
    if suggestion_err:
        finish_stage(campaign_id, "plan", paths=p, outcome="denied", advance=False)
        return _deny(suggestion_err)
    banned = {row["text"] for row in suggestion_rows}
    try:
        checkout = resolve_portfolio_checkout()
        published = _published_questions(checkout)
    except CheckoutError:
        published = set()
    aim = str(cfg.get("aim") or "").strip()
    if not aim:
        finish_stage(campaign_id, "plan", paths=p, outcome="denied", advance=False)
        return _deny("the config aim is not a single copied aim")
    extra_refusals: list[dict[str, str]] = []
    if items is None:
        prepared = plan_one_page(
            cfg,
            published=read_published_pages(paths=p),
        )
        if not prepared.get("ok"):
            finish_stage(campaign_id, "plan", paths=p, outcome="denied", advance=False)
            return _deny(str(prepared.get("deny") or "no card"))
        items = list(prepared.get("items") or [])
        extra_refusals = [
            row for row in (prepared.get("refusals") or []) if isinstance(row, dict)
        ]
    cta = cfg.get("default_cta") or "absent"
    refusals = section1_refusals() + extra_refusals
    known_pages = read_published_pages(paths=p)
    queue: list[dict[str, Any]] = []
    for raw in items or []:
        if not isinstance(raw, dict):
            continue
        question = str(raw.get("question") or "").strip()
        source = str(raw.get("source") or "").strip()
        fill = str(raw.get("fill") or "").strip()
        fact = str(raw.get("fact") or "").strip()
        page_name = str(raw.get("page") or "").strip()
        if page_name and any(_same_page(page_name, earlier) for earlier in known_pages):
            refusals.append({"question": question, "source": source, "reason": "published"})
            continue
        if _copies_keyword(question, banned):
            refusals.append({"question": question, "source": source, "reason": "keyword"})
            continue
        if _is_doorway_grid(question, source, fact):
            refusals.append(
                {"question": question, "source": source, "reason": "service-area"}
            )
            continue
        if question in published:
            refusals.append({"question": question, "source": source, "reason": "published"})
            continue
        try:
            blog_slug(question)
        except SlugError:
            refusals.append({"question": question, "source": source, "reason": "slug"})
            continue
        try:
            source_file(source)
        except (ValueError, FileNotFoundError, OSError):
            refusals.append(
                {"question": question, "source": source, "reason": "missing-source"}
            )
            continue
        if fill not in {"build-log", "lesson", "researched"}:
            refusals.append({"question": question, "source": source, "reason": "fill"})
            continue
        for url in raw.get("urls") or []:
            if _is_search_url(str(url)):
                refusals.append(
                    {"question": question, "source": source, "reason": "search-url"}
                )
                question = ""
                break
        if not question:
            continue
        item: dict[str, Any] = {
            "question": question,
            "fill": fill,
            "source": source,
            "aim": aim,
            "call_to_action": cta if isinstance(cta, dict) else "absent",
            "critic_fails": 0,
        }
        if fact:
            item["fact"] = fact
        if page_name:
            item["page"] = page_name
        card = str(raw.get("card") or "").strip()
        if card:
            item["card"] = card
        if isinstance(raw.get("local_files"), list):
            kept = [str(path).strip() for path in raw["local_files"] if str(path).strip()][:3]
            if kept:
                item["local_files"] = kept
        brief = str(raw.get("brief") or "").strip()
        if brief:
            item["brief"] = brief
        paragraphs = str(raw.get("paragraphs") or "").strip()
        if paragraphs:
            item["paragraphs"] = paragraphs
        if isinstance(raw.get("notes"), list):
            note_rows: list[dict[str, Any]] = []
            for row in raw["notes"]:
                if not isinstance(row, dict):
                    continue
                path = str(row.get("path") or "").strip()
                if not path:
                    continue
                paragraph = str(row.get("paragraph") or "").strip()
                section = str(row.get("section") or "").strip()
                sentences = [
                    str(sentence).strip()
                    for sentence in (row.get("sentences") or [])
                    if str(sentence).strip()
                ]
                if not paragraph and not section:
                    sentences = sentences[:2]
                stored_note: dict[str, Any] = {
                    "path": path,
                    "heading": str(row.get("heading") or "").strip(),
                    "sentences": sentences,
                }
                if paragraph:
                    stored_note["paragraph"] = paragraph
                if section:
                    stored_note["section"] = section
                note_rows.append(stored_note)
            if note_rows:
                item["notes"] = note_rows[:3]
        if "urls" in raw:
            item["urls"] = [str(url) for url in (raw.get("urls") or [])]
        queue.append(item)
    plan["audience"] = cfg["audience"]
    plan["aim"] = aim
    plan["aims"] = [aim]
    plan["suggestions"] = suggestion_rows
    plan["refusals"] = refusals
    plan["queue"] = queue
    save_plan(plan, paths=p)
    rel = str(plan.get("_rel") or "")
    return finish_stage(
        campaign_id,
        "plan",
        paths=p,
        outcome="ok",
        receipt_paths=[rel] if rel else [],
    )


def run_chain_wake(
    campaign_id: str,
    *,
    paths: DataPaths | None = None,
    http_get: Any = None,
    items: list[dict[str, Any]] | None = None,
    suggestions: list[dict[str, Any]] | None = None,
    model: Any | None = None,
) -> dict[str, Any]:
    """Advance the current stage of this campaign once, then sleep."""
    p = paths or require_ada_data()
    cid = (campaign_id or "").strip()
    if not cid:
        return _deny("campaign_id required")
    loop = get_loop(cid, paths=p)
    if not is_chain_loop(loop):
        return _deny("not a chain campaign")
    stage = str((loop or {}).get("current_stage") or "")
    state = ""
    for raw in (loop or {}).get("stages") or []:
        if str(raw.get("id") or "") == stage:
            state = str(raw.get("state") or "")
    if state == "done":
        append_stage_receipt(
            cid,
            {"stage": stage, "outcome": "skip", "paths": []},
            paths=p,
        )
        upsert_loop(loop_id=cid, next_wake_at=next_wake_iso(), paths=p)
        return {"ok": True, "outcome": "skip", "id": cid, "stage": stage}
    if stage == "bind-site":
        return wake_bind_site(cid, paths=p)
    if stage == "understand-aim":
        return wake_understand_aim(cid, paths=p)
    if stage == "plan":
        return wake_plan(cid, items=items, suggestions=suggestions, paths=p)
    if stage == "external-fetch":
        from ada.memory.chain_fetch import wake_external_fetch

        return wake_external_fetch(cid, http_get=http_get, paths=p)
    if stage == "gather":
        from ada.memory.chain_fetch import wake_gather

        return wake_gather(cid, paths=p)
    if stage == "gate":
        from ada.memory.chain_fetch import wake_gate

        return wake_gate(cid, paths=p)
    if stage == "draft":
        from ada.memory.chain_draft import wake_draft

        return wake_draft(cid, paths=p, model=model)
    if stage == "librarian":
        from ada.memory.chain_librarian import wake_librarian

        return wake_librarian(cid, paths=p)
    if stage == "diagram":
        from ada.memory.chain_diagram import wake_diagram

        return wake_diagram(cid, paths=p)
    if stage == "critic":
        from ada.memory.chain_critic import wake_critic

        return wake_critic(cid, paths=p)
    if stage == "deliver":
        from ada.tools.blog_tools import run_blog_checkout_write

        result = run_blog_checkout_write({"campaign_id": cid})
        if not result.get("ok"):
            finish_stage(cid, "deliver", paths=p, outcome="denied", advance=False)
        return result
    if stage == "push":
        from ada.tools.blog_tools import run_blog_checkout_push

        result = run_blog_checkout_push({"campaign_id": cid})
        if not result.get("ok"):
            finish_stage(cid, "push", paths=p, outcome="denied", advance=False)
        return result
    return _deny(f"unknown stage {stage}")
