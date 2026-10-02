"""Machine checks from card 10 §6. A fail does not write the checkout."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import yaml

from ada.io.paths import DataPaths, require_ada_data
from ada.memory.artifacts import _resolve_under_artifacts, artifacts_root
from ada.memory.blog_draft import first_sentence
from ada.memory.blog_packet import source_file
from ada.memory.blog_slug import blog_slug
from ada.memory.campaign_page import FILLS, read_page
from ada.memory.chain_diagram import (
    is_generic_alt,
    is_keyword_alt,
    section_is_flow,
    unsplash_or_hotlink,
)
from ada.memory.chain_draft import (
    answers_question,
    inventory_table,
    is_pipe_dump,
    opening_answer,
    second_list,
)
from ada.memory.chain_fetch import section_text
from ada.memory.chain_librarian import is_holder_href, known_urls, rel_carriers, source_names
from ada.memory.chain_plan import (
    _require_chain,
    _rewrite_stages,
    current_item,
    finish_stage,
    load_plan,
    save_plan,
)
from ada.memory.portfolio_chain import CTA_LABEL, read_portfolio_chain
from ada.tools.blog_tools import CheckoutError, blog_dest, resolve_portfolio_checkout

_FRONT_KEYS = (
    "title",
    "question",
    "description",
    "published",
    "modified",
    "fill",
    "source",
    "canonical",
)
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_HREF = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
_IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_SERVICE = re.compile(r"service[- ]area|\bsuburb\b", re.I)
_WORD = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?")
_GENERIC_ANCHOR = frozenset({"here", "read more"})


def _deny(reason: str) -> dict[str, Any]:
    return {
        "ok": False,
        "outcome": "denied",
        "denied_reason": reason,
        "error": reason,
    }


def _front(markdown: str) -> tuple[dict[str, Any], str] | None:
    if not markdown.startswith("---\n"):
        return None
    end = markdown.find("\n---\n", 4)
    if end < 0:
        return None
    data = yaml.safe_load(markdown[4:end])
    if not isinstance(data, dict):
        return None
    return data, markdown[end + 5 :]


def _opens_with_paragraph(body: str) -> bool:
    for line in body.splitlines():
        if not line.strip():
            continue
        return not line.startswith("#")
    return False


def _has_later_paragraph(body: str, answer: str) -> bool:
    at = body.find(answer)
    if at < 0:
        return False
    current: list[str] = []
    for line in body[at + len(answer) :].splitlines():
        stripped = line.strip()
        if (
            not stripped
            or stripped.startswith("#")
            or stripped.startswith("|")
            or stripped.startswith("![")
            or (stripped.startswith("[") and CTA_LABEL in stripped)
        ):
            if current:
                return True
            continue
        current.append(stripped)
    return bool(current)


def _names_for(source_text: str, spans: list[str], href: str) -> set[str]:
    names: set[str] = set()
    for blob in (source_text, *spans):
        for name in source_names(blob, href):
            names.add(name.casefold())
    return names


def _sentence_around(body: str, start: int, end: int) -> str:
    left = max(
        body.rfind(".", 0, start),
        body.rfind("!", 0, start),
        body.rfind("?", 0, start),
        body.rfind("\n", 0, start),
    )
    rights = [
        pos
        for pos in (
            body.find(".", end),
            body.find("!", end),
            body.find("?", end),
            body.find("\n", end),
        )
        if pos >= 0
    ]
    right = min(rights) + 1 if rights else len(body)
    return body[left + 1 : right]


def anchor_is_fragment(
    body: str,
    anchor: str,
    href: str,
    *,
    names: set[str],
) -> bool:
    """True when the anchor is a URL, "here", or a cut through a sentence.

    The source's name may sit inside one whole sentence. A whole-sentence anchor may too.
    """
    label = (anchor or "").strip()
    folded = label.casefold()
    if not label or folded in _GENERIC_ANCHOR:
        return True
    if folded.startswith("http://") or folded.startswith("https://"):
        return True
    if label.rstrip(".,/") == (href or "").strip().rstrip("/"):
        return True
    if folded in names:
        return False
    needle = f"[{anchor}]({href})"
    at = body.find(needle)
    if at < 0:
        return False
    sentence = _sentence_around(body, at, at + len(needle))
    link_at = sentence.find(needle)
    if link_at < 0:
        return False
    before = sentence[:link_at]
    after = sentence[link_at + len(needle) :]
    if _WORD.search(before) and _WORD.search(after):
        return True
    return False


_CARD_LABEL = re.compile(r"\*\*(FEASIBLE|POLICY|UNKNOWN|HUNCH)\b")
_CLAIM_SKIP = frozenset(
    """
    what does this file answer about how can a an the for of to and in on with
    from that reader page show work when where why who is are do did which
    should one unknown feasible policy hunch card this does not
    """.split()
)


def _text_blocks(text: str) -> list[str]:
    blocks: list[str] = []
    current: list[str] = []
    for line in (text or "").splitlines():
        if line.strip():
            current.append(line.rstrip())
        elif current:
            blocks.append("\n".join(current).strip())
            current = []
    if current:
        blocks.append("\n".join(current).strip())
    return blocks


def _heading_neighbors(source_text: str, notes: str) -> list[str]:
    """Other paragraphs under the heading that locates the stored paragraph."""
    kept = (notes or "").strip()
    if not kept or kept not in (source_text or ""):
        return []
    lines = source_text.splitlines()
    first = kept.splitlines()[0].rstrip()
    start = None
    for index, line in enumerate(lines):
        if line.rstrip() == first:
            start = index
            break
    if start is None:
        return []
    heading_at = 0
    level = 1
    for index in range(start, -1, -1):
        match = re.match(r"^(#{1,6})\s+\S", lines[index].strip())
        if match:
            heading_at = index
            level = len(match.group(1))
            break
    end = len(lines)
    for index in range(heading_at + 1, len(lines)):
        match = re.match(r"^(#{1,6})\s+\S", lines[index].strip())
        if match and len(match.group(1)) <= level:
            end = index
            break
    neighbors: list[str] = []
    for block in _text_blocks("\n".join(lines[heading_at:end])):
        if block.startswith("#") or block == kept or block in kept:
            continue
        neighbors.append(block)
    return neighbors


def _unknown_claims(blocks: list[str]) -> list[str]:
    found: list[str] = []
    for block in blocks:
        if re.match(r"^\*\*UNKNOWN\b", block, re.I):
            found.append(block)
        elif re.search(r"\bis \*\*UNKNOWN\*\*", block) or re.search(r"\bis UNKNOWN\b", block):
            found.append(block)
    return found


def _claim_words(claim: str) -> list[str]:
    words: list[str] = []
    for word in _WORD.findall(claim or ""):
        token = word.casefold()
        if token in _CLAIM_SKIP or len(token) < 4 or token in words:
            continue
        words.append(token)
    return words


def _word_in(text: str, word: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(word)}(?![a-z0-9])", text) is not None


def opening_answers_unknown(opening: str, notes: str, source_text: str) -> bool:
    """True when the opening answers a claim the notes mark unknown."""
    if not (notes or "").strip() or not (opening or "").strip():
        return False
    claims = _unknown_claims(_text_blocks(notes))
    claims.extend(_unknown_claims(_heading_neighbors(source_text, notes)))
    folded = opening.casefold()
    for claim in claims:
        words = _claim_words(claim)
        if len(words) < 2:
            continue
        hits = [word for word in words if _word_in(folded, word)]
        if len(hits) >= 2:
            return True
    return False


def body_is_card(body: str, notes: str, source_text: str) -> bool:
    """True when the body is still the research card.

    A label such as FEASIBLE, or a neighbor paragraph from the same heading,
    is that card. The stored paragraph's own words are the fact.
    """
    if not (notes or "").strip():
        return False
    text = body or ""
    if _CARD_LABEL.search(text):
        return True
    for block in _heading_neighbors(source_text, notes):
        for line in block.splitlines():
            sentence = line.strip()
            if len(sentence) >= 40 and sentence in text:
                return True
    return False


def critic_checks(
    markdown: str,
    *,
    question: str,
    slug: str,
    packet: list[dict[str, Any]],
    source_text: str,
    cta: dict[str, str] | None,
    published: set[str],
    staged: str | None,
    staged_bytes: bytes | None,
    notes: str = "",
) -> list[str]:
    """Return the failed check names. An empty list is a pass."""
    failed: list[str] = []
    parsed = _front(markdown)
    if parsed is None:
        return ["frontmatter"]
    front, body = parsed
    for key in _FRONT_KEYS:
        if key not in front:
            failed.append(f"frontmatter-{key}")
    if str(front.get("canonical") or "") != f"/blog/{slug}":
        failed.append("canonical")
    if str(front.get("title") or "") != question or str(front.get("question") or "") != question:
        failed.append("question")
    if str(front.get("description") or "") != first_sentence(question):
        failed.append("description")
    if str(front.get("fill") or "") not in FILLS:
        failed.append("fill")
    for key in ("published", "modified"):
        value = str(front.get(key) or "")
        if not _DATE.match(value):
            failed.append(key)
            continue
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            failed.append(key)
    if source_text.strip() and (
        body.strip() == source_text.strip() or source_text.strip() in body
    ):
        failed.append("pasted-source")
    spans = [str(fact.get("span") or "") for fact in packet]
    answer = opening_answer(markdown)
    if (
        not answer
        or not _opens_with_paragraph(body)
        or not _has_later_paragraph(body, answer)
        or not answers_question(answer, question)
    ):
        failed.append("direct-answer")
    else:
        direct_at = body.find(answer)
        image_at = body.find("![")
        if image_at >= 0 and direct_at >= 0 and image_at < direct_at:
            failed.append("section-order")
        cta_at = body.find(f"[{CTA_LABEL}]")
        if cta_at >= 0 and cta_at < direct_at:
            failed.append("cta-before-answer")
    if opening_answers_unknown(answer, notes, source_text):
        failed.append("unknown")
    if body_is_card(body, notes, source_text):
        failed.append("card")
    if is_pipe_dump(body, spans):
        failed.append("pipe-dump")
    if inventory_table(body) or second_list(body):
        failed.append("inventory")
    urls = set(known_urls(packet, source_text, *spans))
    allowed_cta = {cta["mail"], cta["call"]} if cta else set()
    hrefs = _HREF.findall(body)
    cta_hrefs = [href for _label, href in hrefs if href in allowed_cta]
    if cta is None:
        if any(label == CTA_LABEL for label, _href in hrefs):
            failed.append("cta")
    else:
        if not any(href == cta["call"] or href == cta["mail"] for _label, href in hrefs):
            failed.append("cta-close")
        if any(label != CTA_LABEL for label, href in hrefs if href in allowed_cta):
            failed.append("cta-label")
        if any(href not in allowed_cta and href not in urls and not href.startswith("/") for _l, href in hrefs):
            failed.append("cta-href")
        if len(set(cta_hrefs)) > 2:
            failed.append("cta-third")
    self_path = f"/blog/{slug}"
    quoted = {
        href
        for span in spans
        for _anchor, href in _HREF.findall(span)
    }
    for anchor, href in hrefs:
        if href in quoted:
            continue
        if href in allowed_cta:
            continue
        if anchor_is_fragment(
            body,
            anchor,
            href,
            names=_names_for(source_text, spans, href),
        ):
            failed.append("anchor")
        if is_holder_href(href):
            failed.append("holder")
        if href.startswith("/") and href not in published and href != self_path:
            failed.append("internal-link")
        if href.startswith("http") and href not in urls:
            failed.append("external-link")
    if rel_carriers(body):
        failed.append("rel")
    if unsplash_or_hotlink(body):
        failed.append("unsplash")
    images = _IMAGE.findall(body)
    if len(images) > 1:
        failed.append("image-count")
    elif len(images) == 1:
        alt, src = images[0]
        expected = {f"content/blog/media/{slug}.svg", f"content/blog/media/{slug}.webp"}
        if src not in expected:
            failed.append("image-path")
        if is_keyword_alt(alt) or is_generic_alt(alt):
            failed.append("alt")
        has_table = any(
            line.strip().startswith("|")
            and line.strip().endswith("|")
            and line.strip().count("|") >= 2
            for line in body.splitlines()
        )
        if has_table and not section_is_flow(body):
            failed.append("image-table")
        if not staged or staged_bytes is None:
            failed.append("staged-bytes")
        elif b"unsplash" in staged_bytes.lower():
            failed.append("unsplash")
    elif staged and staged.endswith((".svg", ".webp")) and staged_bytes:
        failed.append("image-missing")
    if _SERVICE.search(question) or _SERVICE.search(body):
        failed.append("service-area")
    return list(dict.fromkeys(failed))


def _staged(campaign_id: str, plan_item: dict[str, Any], paths: DataPaths) -> tuple[str | None, bytes | None]:
    diagram = plan_item.get("diagram")
    if not diagram or diagram == "skip":
        return None, None
    rel = str(diagram)
    if rel.startswith("artifacts/"):
        rel = rel[len("artifacts/") :]
    try:
        path = _resolve_under_artifacts(artifacts_root(paths), rel)
    except ValueError:
        return str(diagram), None
    if not path.is_file():
        return str(diagram), None
    return str(diagram), path.read_bytes()


def wake_critic(
    campaign_id: str,
    *,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    """Pass or fail. Do not write the checkout and do not add a fact."""
    p = paths or require_ada_data()
    blocked = _require_chain(campaign_id, "critic", p)
    if blocked:
        return blocked
    plan = load_plan(campaign_id, paths=p)
    item = current_item(plan) if plan else None
    page = read_page(campaign_id, paths=p)
    config = read_portfolio_chain(paths=p)
    if plan is None or item is None or page is None or not config.get("ok"):
        finish_stage(campaign_id, "critic", paths=p, outcome="denied", advance=False)
        return _deny("plan queue is empty")
    packet_before = list(page.get("packet") or [])
    draft_path = str(item.get("draft_path") or "")
    try:
        rel = draft_path[len("artifacts/") :] if draft_path.startswith("artifacts/") else draft_path
        markdown = _resolve_under_artifacts(artifacts_root(p), rel).read_text(encoding="utf-8")
        source_text = source_file(str(page.get("source") or "")).read_text(encoding="utf-8")
    except (OSError, ValueError) as exc:
        finish_stage(campaign_id, "critic", paths=p, outcome="denied", advance=False)
        return _deny(str(exc))
    question = str(page.get("question") or "")
    try:
        slug = str(page.get("slug") or "") or blog_slug(question)
    except ValueError as exc:
        finish_stage(campaign_id, "critic", paths=p, outcome="denied", advance=False)
        return _deny(str(exc))
    published: set[str] = set()
    deliver_block = False
    try:
        checkout = resolve_portfolio_checkout()
        blog = checkout / "content" / "blog"
        if blog.is_dir():
            for path in blog.glob("*.md"):
                published.add(f"/blog/{path.stem}")
        dest = blog_dest(checkout, slug)
        deliver_block = dest.exists()
    except (CheckoutError, ValueError):
        checkout = None
    cta = config["config"].get("default_cta")
    staged_path, staged_bytes = _staged(campaign_id, item, p)
    failed = critic_checks(
        markdown,
        question=question,
        slug=slug,
        packet=packet_before,
        source_text=source_text,
        cta=cta if isinstance(cta, dict) else None,
        published=published,
        staged=staged_path,
        staged_bytes=staged_bytes,
        notes=section_text(item),
    )
    if page.get("packet") != packet_before:
        finish_stage(campaign_id, "critic", paths=p, outcome="denied", advance=False)
        return _deny("critic adds a fact")
    if not failed:
        return finish_stage(
            campaign_id,
            "critic",
            paths=p,
            outcome="pass",
            slug=slug,
            receipt_paths=[draft_path] + ([staged_path] if staged_path else []),
            deliver_block=deliver_block,
        )
    fails = int(item.get("critic_fails") or 0) + 1
    item["critic_fails"] = fails
    save_plan(plan, paths=p)
    remove = _remove_targets(
        markdown,
        failed,
        source_text=source_text,
        spans=[str(fact.get("span") or "") for fact in packet_before],
        notes=section_text(item),
    )
    if fails >= 2:
        finish_stage(
            campaign_id,
            "critic",
            paths=p,
            outcome="fail",
            slug=slug,
            checks=failed,
            remove=remove,
            advance=False,
            status="failed",
        )
        return {"ok": False, "outcome": "fail", "checks": failed, "id": campaign_id}
    finish_stage(
        campaign_id,
        "critic",
        paths=p,
        outcome="fail",
        slug=slug,
        checks=failed,
        remove=remove,
        advance=False,
    )
    _rewrite_stages(
        campaign_id,
        paths=p,
        current="draft",
        active="draft",
        pending={"librarian", "diagram", "critic", "deliver", "push"},
    )
    return {"ok": False, "outcome": "fail", "checks": failed, "id": campaign_id}


def _covers(existing: str, piece: str) -> bool:
    return bool(piece) and (piece in existing or existing in piece)


def _remove_targets(
    markdown: str,
    failed: list[str],
    *,
    source_text: str = "",
    spans: list[str] | None = None,
    notes: str = "",
) -> list[str]:
    """The sentence, link, or image that made a check fail. Repair deletes only these."""
    targets: list[str] = []

    def add(piece: str) -> None:
        if piece and piece in markdown and not any(_covers(item, piece) for item in targets):
            targets.append(piece)

    if "rel" in failed:
        for carrier in rel_carriers(markdown):
            add(carrier)
    if any(name in failed for name in ("unsplash", "image-path", "alt", "image-count")):
        for alt, src in _IMAGE.findall(markdown):
            add(f"![{alt}]({src})")
    link_checks = {"external-link", "holder", "internal-link", "cta-href", "anchor"}
    if link_checks & set(failed):
        for anchor, href in _HREF.findall(markdown):
            piece = f"[{anchor}]({href})"
            if "external-link" in failed and href.startswith("http"):
                add(piece)
            elif "holder" in failed and is_holder_href(href):
                add(piece)
            elif "internal-link" in failed and href.startswith("/"):
                add(piece)
            elif "cta-href" in failed and href.startswith("http"):
                add(piece)
            elif "anchor" in failed and anchor_is_fragment(
                markdown,
                anchor,
                href,
                names=_names_for(source_text, list(spans or []), href),
            ):
                add(piece)
    if "service-area" in failed:
        for line in markdown.splitlines():
            if _SERVICE.search(line):
                add(line)
    if "unknown" in failed:
        answer = opening_answer(markdown)
        if answer:
            add(answer)
    if "card" in failed:
        for line in markdown.splitlines():
            stripped = line.strip()
            if _CARD_LABEL.search(stripped) or (
                len(stripped) >= 40 and stripped in (source_text or "") and stripped not in (notes or "")
            ):
                add(stripped)
    if "pasted-source" in failed:
        parsed = _front(markdown)
        body = parsed[1] if parsed else markdown
        if body.strip() and body.strip() in markdown:
            add(body.strip())
    if "pipe-dump" in failed:
        for line in markdown.splitlines():
            stripped = line.strip()
            if stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") == 2:
                add(stripped)
    if "inventory" in failed:
        for line in markdown.splitlines():
            stripped = line.strip()
            if stripped.startswith("|") and stripped.endswith("|"):
                add(stripped)
            elif re.match(r"^\d+\. \S", stripped) or stripped.startswith(("- ", "* ")):
                add(stripped)
    if "image-table" in failed:
        for alt, src in _IMAGE.findall(markdown):
            add(f"![{alt}]({src})")
    return targets
