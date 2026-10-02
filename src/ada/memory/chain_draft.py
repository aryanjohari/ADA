"""Draft one local markdown file from a gated packet. The page is a reading of the packet in the model's own words."""

from __future__ import annotations

import re
from typing import Any

from ada.io.atomic import atomic_write_text
from ada.io.paths import DataPaths, require_ada_data
from ada.memory.artifacts import _resolve_under_artifacts, artifacts_root, write_artifact
from ada.memory.blog_draft import (
    compose_markdown,
    first_sentence,
    utc_calendar_day,
)
from ada.memory.blog_packet import gate_packet, source_file
from ada.memory.blog_slug import SlugError, blog_slug
from ada.memory.campaign_page import read_page, write_page
from ada.memory.chain_fetch import citation_urls, gate_texts, section_text
from ada.memory.chain_plan import (
    _require_chain,
    current_item,
    finish_stage,
    load_plan,
    save_plan,
)
from ada.memory.chain_receipt import append_stage_receipt, latest_receipt, slug_was_pushed
from ada.memory.portfolio_chain import read_portfolio_chain

PAGE_SYSTEM = "You write one page in plain language. Reply with the page only."
_STOCK = (
    "The gathered packet is what this page accounts for.",
    "This page is an account of the gathered packet.",
)
_STOCK_HEADINGS = ("## The problem", "## How it works", "## Spans")


def _deny(reason: str) -> dict[str, Any]:
    return {
        "ok": False,
        "outcome": "denied",
        "denied_reason": reason,
        "error": reason,
    }


def body_start(markdown: str) -> int:
    """Index of the body after frontmatter, or 0 when there is none."""
    if markdown.startswith("---\n"):
        end = markdown.find("\n---\n", 4)
        if end >= 0:
            return end + 5
    return 0


def opening_answer(markdown: str) -> str:
    """The first paragraph, after frontmatter and an optional title line."""
    chunk: list[str] = []
    for line in markdown[body_start(markdown) :].splitlines():
        if line.startswith("# ") and not chunk:
            continue
        if line.startswith("## "):
            break
        if not line.strip():
            if chunk:
                break
            continue
        chunk.append(line.strip())
    return " ".join(chunk).strip()


def insert_after_opening(markdown: str, addition: str) -> str:
    """Place text after the opening paragraph, not inside a title line."""
    answer = opening_answer(markdown)
    if not answer:
        return markdown
    start = body_start(markdown)
    at = markdown.find(answer, start)
    if at < 0:
        return markdown
    line_start = markdown.rfind("\n", start, at) + 1
    if markdown[line_start:].startswith("# "):
        newline = markdown.find("\n", line_start)
        if newline < 0:
            return markdown
        at = markdown.find(answer, newline + 1)
        if at < 0:
            return markdown
    end_at = at + len(answer)
    return markdown[:end_at] + addition + markdown[end_at:]


def draft_materials(item: dict[str, Any]) -> tuple[str, list[str], list[str], str]:
    """The brief, the stored section, its sentences, and the URLs named there.

    A backtick URL and a bare https URL are citations, as is a markdown link.
    This does not read every line of a chosen file and does not paste one.
    """
    brief = str(item.get("brief") or "").strip()
    if not brief:
        return "", [], [], ""
    excerpts: list[str] = []
    blobs: list[str] = []
    stored = section_text(item)
    for row in item.get("notes") or []:
        if not isinstance(row, dict):
            continue
        section = str(row.get("section") or "").strip()
        paragraph = str(row.get("paragraph") or "").strip()
        sentences = [
            str(sentence).strip()
            for sentence in (row.get("sentences") or [])
            if str(sentence).strip()
        ]
        if paragraph and not sentences:
            sentences = [paragraph]
        if section:
            blobs.append(section)
        elif paragraph:
            blobs.append(paragraph)
        for text in sentences:
            if text not in excerpts:
                excerpts.append(text)
            if text not in blobs:
                blobs.append(text)
        if section and not sentences and section not in excerpts:
            excerpts.append(section)
    urls: list[str] = []
    if stored:
        blobs = [stored]
    for blob in blobs:
        for url in citation_urls(blob):
            if url not in urls:
                urls.append(url)
    if not stored:
        for row in item.get("excerpts") or []:
            if not isinstance(row, dict):
                continue
            url = str(row.get("url") or "").strip()
            if url and url not in urls:
                urls.append(url)
    return brief, excerpts, urls, stored


def page_prompt(
    *,
    audience: str,
    aim: str,
    question: str,
    spans: list[str],
    brief: str = "",
    excerpts: list[str] | None = None,
    urls: list[str] | None = None,
    section: str = "",
) -> str:
    """The user prompt for one plain page.

    With a brief, the prompt is that brief, the reader question, the stored
    paragraph, and the URLs named in that paragraph. It is not the card.
    Without a brief, the spans are numbered.
    """
    writing = (
        f"Audience: {audience}\n"
        f"Aim: {aim}\n"
        f"Question: {question}\n"
        "\n"
        "Write only the post those passages can support, in your own words, as a few plain paragraphs a person would read.\n"
        "Write for a stranger.\n"
        "Simple words. Short sentences. Say the useful part first.\n"
        "The first paragraph is the useful fact, not a repeat of the title.\n"
        "Answer the question, and do not review the file line by line.\n"
        "A heading or a list appears only when the passages themselves are a sequence or a comparison.\n"
        "A claim has to come from the passages.\n"
        "A URL has to be one the passages already name.\n"
        "Do not repeat the question as a heading.\n"
        "Do not paste the source. Do not restate the card.\n"
        "Do not use FEASIBLE, POLICY, UNKNOWN, or HUNCH as the voice.\n"
        "Do not answer a claim the notes mark unknown.\n"
        "Do not write a pipe table of every line.\n"
        "Leave out an access-date stamp, a repo path, and a machine name.\n"
    )
    if brief.strip():
        shown = list(excerpts or [])
        numbered = "\n".join(f"{index}. {span}" for index, span in enumerate(shown, start=1))
        listed = "\n".join(str(url) for url in (urls or []))
        section_body = section.strip() or "\n\n".join(shown)
        return (
            f"Audience: {audience}\n"
            f"Aim: {aim}\n"
            f"Title: {question}\n"
            f"Question: {question}\n"
            "\n"
            "Write only the post those passages can support, in your own words, as a few plain paragraphs a person would read.\n"
            "Simple words. Short sentences.\n"
            "The first paragraph is the useful fact, not a repeat of the title.\n"
            "A heading or a list appears only when the passages themselves are a sequence or a comparison.\n"
            "A claim has to come from the passages.\n"
            "A URL has to be one the passages already name.\n"
            "Do not paste the source. Do not restate the card.\n"
            "Do not use FEASIBLE, POLICY, UNKNOWN, or HUNCH as the voice.\n"
            "Do not answer a claim the notes mark unknown.\n"
            "Do not repeat the title as a heading.\n"
            "A claim that needs a source uses one of these URLs.\n"
            "Do not write a pipe table of every line.\n"
            "Leave out an access-date stamp, a repo path, and a machine name.\n"
            "\n"
            f"Idea:\n{brief.strip()}\n"
            "\n"
            f"Brief:\n{brief.strip()}\n"
            "\n"
            "Passages:\n"
            f"{section_body}\n"
            "\n"
            "Section:\n"
            f"{section_body}\n"
            "\n"
            "Excerpts:\n"
            f"{numbered}\n"
            "\n"
            "URLs:\n"
            f"{listed}\n"
        )
    numbered = "\n".join(f"{index}. {span}" for index, span in enumerate(spans, start=1))
    return (
        f"{writing}"
        "\n"
        "Spans:\n"
        f"{numbered}\n"
    )


def page_from_model(
    model: Any,
    *,
    audience: str,
    aim: str,
    question: str,
    spans: list[str],
    refusal: str = "",
    brief: str = "",
    excerpts: list[str] | None = None,
    urls: list[str] | None = None,
    section: str = "",
) -> str:
    """Ask GeminiAdapter.generate with no tools. The reply is the page.

    A refusal sentence is the same prompt plus that sentence, for one retry.
    The call receives the brief and this step's excerpts. It does not receive
    the previous prompt or every line of the catalog.
    """
    from ada.cortex.gemini import user_content

    prompt = page_prompt(
        audience=audience,
        aim=aim,
        question=question,
        spans=spans,
        brief=brief,
        excerpts=excerpts,
        urls=urls,
        section=section,
    )
    if refusal.strip():
        prompt = f"{prompt.rstrip()}\n\n{refusal.strip()}\n"
    turn = model.generate(
        system=PAGE_SYSTEM,
        contents=[user_content(prompt)],
        tools=[],
    )
    return str(getattr(turn, "text", "") or "").strip()


def repeats_question_heading(page: str, question: str) -> bool:
    """True when a heading line is the question."""
    target = question.strip()
    if not target:
        return False
    for line in page.splitlines():
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        if stripped.lstrip("#").strip() == target:
            return True
    return False


_ANSWER_STOP = frozenset(
    "a an the for of to and in on with from that this is are it or as by at "
    "do did does what which who where when why how can one".split()
)
_SEQUENCE_CUE = re.compile(r"\b(first|next|finally|step)\b", re.I)
_THEN = re.compile(r"\bthen\b", re.I)
_SET_CUE = re.compile(r"\b(including|such as|for example)\b", re.I)
_NUMBERED_ITEM = re.compile(r"^\d+\. \S")
_INVENTORY_HEADER = frozenset({
    "name",
    "names",
    "url",
    "urls",
    "block",
    "blocks",
    "tag",
    "tags",
    "source",
    "sources",
    "behavior",
    "behaviors",
    "behaviour",
    "behaviours",
    "policy",
    "policies",
    "role",
    "roles",
    "what",
    "why",
    "how",
    "description",
    "contains",
    "content",
    "type",
    "kind",
})


def _answer_terms(question: str) -> list[str]:
    """Words that would show the opening is about this question."""
    terms: list[str] = []
    for word in re.findall(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?", question or ""):
        if word.casefold() in _ANSWER_STOP:
            continue
        if len(word) >= 5 or (len(word) >= 3 and word.isupper()):
            terms.append(word)
    return terms


def answers_question(opening: str, question: str) -> bool:
    """True when the first paragraph answers the question, not when it repeats it."""
    left = " ".join((opening or "").casefold().split()).rstrip(".!?")
    right = " ".join((question or "").casefold().split()).rstrip(".!?")
    if not left or left == right:
        return False
    terms = _answer_terms(question)
    if not terms:
        return True
    return any(term.casefold() in left for term in terms)


def opening_is_sequence(opening: str) -> bool:
    """True when the answer is an ordered sequence, not a set introduced by including."""
    text = " ".join((opening or "").split())
    if _SEQUENCE_CUE.search(text):
        return True
    if _THEN.search(text) and not _SET_CUE.search(text):
        return True
    return False


def _meta_header(cell: str) -> bool:
    cleaned = " ".join(cell.casefold().replace("*", " ").replace("`", " ").split())
    if not cleaned:
        return True
    if cleaned in _INVENTORY_HEADER:
        return True
    first = cleaned.split()[0].rstrip("s")
    return first in _INVENTORY_HEADER or cleaned.split()[0] in _INVENTORY_HEADER


def _markdown_tables(text: str) -> list[list[list[str]]]:
    tables: list[list[list[str]]] = []
    current: list[list[str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2:
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if cells and all(not cell or set(cell.replace(":", "")) <= set("- ") for cell in cells):
                continue
            current.append(cells)
            continue
        if current:
            tables.append(current)
            current = []
    if current:
        tables.append(current)
    return tables


def _compares_two(table: list[list[str]]) -> bool:
    """A comparison names two subjects in the header and sets them side by side."""
    if len(table) < 2:
        return False
    if any(len(row) != 2 for row in table):
        return False
    header = table[0]
    if any(_meta_header(cell) for cell in header):
        return False
    return True


def _column_restates(table: list[list[str]], opening: str) -> bool:
    """True when the first column repeats items the opening already stated."""
    stated = [row[0] for row in table if row and _stated_in(row[0], opening)]
    return len(stated) >= 2


def inventory_table(text: str) -> bool:
    """True when a table restates the opening or is not a comparison of two things."""
    opening = opening_answer(text)
    for table in _markdown_tables(text):
        if _compares_two(table) and not _column_restates(table, opening):
            continue
        return True
    return False


def _stated_in(item: str, opening: str) -> bool:
    folded = " ".join(item.casefold().split()).strip(".,;:")
    if len(folded) < 4:
        return False
    return folded in " ".join(opening.casefold().split())


def _list_items(text: str) -> tuple[list[str], list[str]]:
    numbered: list[str] = []
    bullets: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if _NUMBERED_ITEM.match(stripped):
            numbered.append(stripped.split(". ", 1)[1].strip())
        elif stripped.startswith(("- ", "* ")):
            bullets.append(stripped[2:].strip())
    return numbered, bullets


def second_list(text: str) -> bool:
    """True when a list repeats the opening, or a numbered list is not a sequence."""
    opening = opening_answer(text)
    numbered, bullets = _list_items(text)
    sequence = opening_is_sequence(opening)
    repeated = [item for item in numbered + bullets if _stated_in(item, opening)]
    if len(numbered) >= 2 and not sequence:
        return True
    if len(repeated) >= 2 and not sequence:
        return True
    return False


def is_pipe_dump(text: str, spans: list[str]) -> bool:
    """True when a one-column pipe table repeats every usable span."""
    cells: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not (stripped.startswith("|") and stripped.endswith("|")):
            continue
        if stripped.count("|") != 2:
            continue
        inner = stripped[1:-1].strip()
        if not inner or set(inner.replace(":", "")) <= set("- "):
            continue
        cells.append(inner)
    usable = [
        span.strip()
        for span in spans
        if span.strip() and "\n" not in span and "|" not in span
    ]
    if len(usable) < 2:
        return False
    return all(span in cells for span in usable)


def page_refusal(page: str, spans: list[str], *, question: str, file_text: str) -> str | None:
    """A reason to refuse the model page, or None when the page may be composed."""
    if not page.strip():
        return "draft model returned no page"
    for line in _STOCK:
        if line in page:
            return "draft repeats a stock line"
    for heading in _STOCK_HEADINGS:
        if heading in page:
            return "draft repeats a stock heading"
    if repeats_question_heading(page, question):
        return "draft repeats the question as a heading"
    if file_text.strip() and file_text.strip() in page:
        return "draft pastes the source"
    if is_pipe_dump(page, spans):
        return "draft writes a pipe table of every line"
    if inventory_table(page):
        return "draft restates the opening as a table"
    if second_list(page):
        return "draft restates the opening as a list"
    return None


def draft_adds_link_or_image(markdown: str, spans: list[str]) -> bool:
    """True when a link or image is not itself a packet span."""
    body = markdown.split("\n---\n", 1)[-1]
    cursor = 0
    for span in spans:
        found = body.find(span, cursor)
        if found < 0:
            continue
        body = body[:found] + body[found + len(span) :]
    if "![" in body or "<img" in body.lower():
        return True
    return "](" in body


def repair_markdown(
    markdown: str,
    remove: list[str],
    *,
    addition: str | None = None,
) -> dict[str, Any]:
    """Delete named sentences, links, or images. Adding text is a refusal."""
    if addition:
        return _deny("repair cannot add a fact")
    updated = markdown
    for piece in remove:
        if piece and piece not in updated:
            return _deny("repair can only remove a named sentence, link, or image")
        if piece:
            updated = updated.replace(piece, "", 1)
    return {"ok": True, "outcome": "ok", "markdown": updated}


def _artifact_path(paths: DataPaths, receipt_path: str):
    rel = receipt_path.replace("\\", "/")
    if rel.startswith("artifacts/"):
        rel = rel[len("artifacts/") :]
    return _resolve_under_artifacts(artifacts_root(paths), rel)


def wake_draft(
    campaign_id: str,
    *,
    paths: DataPaths | None = None,
    model: Any | None = None,
) -> dict[str, Any]:
    """Write artifacts/{UTC date}/{slug}.md from the model page. Do not call draft_page."""
    p = paths or require_ada_data()
    blocked = _require_chain(campaign_id, "draft", p)
    if blocked:
        return blocked
    plan = load_plan(campaign_id, paths=p)
    item = current_item(plan) if plan else None
    if plan is None or item is None:
        finish_stage(campaign_id, "draft", paths=p, outcome="denied", advance=False)
        return _deny("plan queue is empty")
    if int(item.get("critic_fails") or 0) >= 1:
        return _repair(campaign_id, plan, item, paths=p)
    page = read_page(campaign_id, paths=p)
    if page is None:
        finish_stage(campaign_id, "draft", paths=p, outcome="denied", advance=False)
        return _deny("campaign page is missing")
    packet = page.get("packet")
    if not isinstance(packet, list) or not packet:
        finish_stage(campaign_id, "draft", paths=p, outcome="denied", advance=False)
        return _deny("gather has not left a packet")
    source = str(page.get("source") or "").strip()
    try:
        file_text = source_file(source).read_text(encoding="utf-8")
        bodies = gate_texts(item)
    except (ValueError, FileNotFoundError, OSError) as exc:
        finish_stage(campaign_id, "draft", paths=p, outcome="denied", advance=False)
        return _deny(f"source file is missing: {exc}")
    gated = gate_packet(
        page=page,
        facts=list(packet),
        file_text=file_text,
        fetch_bodies=bodies,
    )
    if not gated.get("ok"):
        finish_stage(campaign_id, "draft", paths=p, outcome="denied", advance=False)
        return gated
    if list(gated["packet"]) != list(packet):
        finish_stage(campaign_id, "draft", paths=p, outcome="denied", advance=False)
        return _deny("draft adds no fact")
    question = str(item.get("question") or page.get("question") or "")
    try:
        slug = blog_slug(question)
    except SlugError as exc:
        finish_stage(campaign_id, "draft", paths=p, outcome="denied", advance=False)
        return _deny(str(exc))
    spans = [str(fact["span"]) for fact in packet]
    brief, excerpts, urls, section = draft_materials(item)
    if model is None:
        finish_stage(campaign_id, "draft", paths=p, outcome="denied", advance=False)
        return _deny("chain draft model is absent")
    config = read_portfolio_chain(paths=p)
    if not config.get("ok"):
        finish_stage(campaign_id, "draft", paths=p, outcome="denied", advance=False)
        return config
    cfg = config["config"]
    aims = [str(aim) for aim in (cfg.get("aims") or [])]
    audience = str(cfg.get("audience") or "")
    aim = aims[0] if aims else ""

    def ask(refusal: str = "") -> str:
        return page_from_model(
            model,
            audience=audience,
            aim=aim,
            question=question,
            spans=excerpts if brief else spans,
            refusal=refusal,
            brief=brief,
            excerpts=excerpts,
            urls=urls,
            section=section,
        )

    try:
        model_page = ask()
    except Exception as exc:
        finish_stage(campaign_id, "draft", paths=p, outcome="denied", advance=False)
        return _deny(f"draft model failed: {exc}")
    refused = page_refusal(model_page, spans, question=question, file_text=file_text)
    if refused:
        append_stage_receipt(
            campaign_id,
            {
                "stage": "draft",
                "slug": slug,
                "outcome": "fail",
                "paths": [],
                "checks": [refused],
            },
            paths=p,
        )
        try:
            model_page = ask(refused)
        except Exception as exc:
            finish_stage(campaign_id, "draft", paths=p, outcome="denied", advance=False)
            return _deny(f"draft model failed: {exc}")
        refused = page_refusal(model_page, spans, question=question, file_text=file_text)
        if refused:
            finish_stage(
                campaign_id,
                "draft",
                paths=p,
                outcome="denied",
                slug=slug,
                checks=[refused],
                advance=False,
            )
            return _deny(refused)
    day = utc_calendar_day()
    try:
        markdown = compose_markdown(
            question=question,
            fill=str(page.get("fill") or ""),
            source=source,
            slug=slug,
            prose=model_page,
            spans=spans,
            published=day,
            modified=day,
            call_to_action=None,
            image=False,
            span_table=False,
        )
    except ValueError as exc:
        finish_stage(campaign_id, "draft", paths=p, outcome="denied", advance=False)
        return _deny(str(exc))
    if file_text.strip() and file_text.strip() in markdown:
        finish_stage(campaign_id, "draft", paths=p, outcome="denied", advance=False)
        return _deny("draft pastes the source")
    if draft_adds_link_or_image(markdown, spans):
        finish_stage(campaign_id, "draft", paths=p, outcome="denied", advance=False)
        return _deny("draft adds a link or an image")
    if first_sentence(question) not in markdown:
        finish_stage(campaign_id, "draft", paths=p, outcome="denied", advance=False)
        return _deny("description left the question")
    rel = f"{day}/{slug}.md"
    replace = (p.artifacts / rel).is_file()
    if replace and slug_was_pushed(slug, paths=p):
        finish_stage(campaign_id, "draft", paths=p, outcome="denied", advance=False)
        return _deny("refusing to overwrite a pushed slug")
    written = write_artifact(
        title="campaign page",
        body=markdown,
        format="md",
        source_cites=None,
        overwrite=replace,
        confirmed=replace,
        relative_path=rel,
        campaign_id=None,
        paths=p,
    )
    if not written.get("ok"):
        finish_stage(campaign_id, "draft", paths=p, outcome="denied", advance=False)
        return written
    stored = dict(page)
    stored["packet"] = list(packet)
    stored["slug"] = slug
    write_page(campaign_id, stored, paths=p)
    item["slug"] = slug
    item["draft_path"] = str(written.get("path") or f"artifacts/{rel}")
    save_plan(plan, paths=p)
    return finish_stage(
        campaign_id,
        "draft",
        paths=p,
        outcome="ok",
        slug=slug,
        receipt_paths=[item["draft_path"]],
    )


def _repair(
    campaign_id: str,
    plan: dict[str, Any],
    item: dict[str, Any],
    *,
    paths: DataPaths,
) -> dict[str, Any]:
    failed = latest_receipt(campaign_id, "critic", outcome="fail", paths=paths)
    draft_path = str(item.get("draft_path") or "")
    if failed is None or not draft_path:
        finish_stage(campaign_id, "draft", paths=paths, outcome="denied", advance=False)
        return _deny("repair has no fail receipt")
    try:
        target = _artifact_path(paths, draft_path)
        markdown = target.read_text(encoding="utf-8")
    except (OSError, ValueError) as exc:
        finish_stage(campaign_id, "draft", paths=paths, outcome="denied", advance=False)
        return _deny(str(exc))
    repaired = repair_markdown(markdown, list(failed.get("remove") or []))
    if not repaired.get("ok"):
        finish_stage(campaign_id, "draft", paths=paths, outcome="denied", advance=False)
        return repaired
    atomic_write_text(target, repaired["markdown"])
    return finish_stage(
        campaign_id,
        "draft",
        paths=paths,
        outcome="ok",
        slug=str(item.get("slug") or ""),
        receipt_paths=[draft_path],
    )
