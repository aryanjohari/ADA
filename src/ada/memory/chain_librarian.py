"""In-sentence links from the published blog set and the packet. No new facts."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from ada.io.atomic import atomic_write_text
from ada.io.paths import DataPaths, require_ada_data
from ada.memory.artifacts import _resolve_under_artifacts, artifacts_root
from ada.memory.blog_packet import source_file
from ada.memory.chain_fetch import citation_urls, section_text
from ada.memory.campaign_page import read_page
from ada.memory.chain_draft import body_start, insert_after_opening
from ada.memory.chain_plan import (
    _require_chain,
    current_item,
    finish_stage,
    load_plan,
)
from ada.memory.portfolio_chain import CTA_LABEL, read_portfolio_chain
from ada.tools.blog_tools import CheckoutError, resolve_portfolio_checkout

HOLDERS = frozenset({"/", "/about", "/projects", "/workshop"})
_GENERIC = frozenset({"here", "read more"})
_HREF = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)]+)\)")
_URL = re.compile(r"https?://[^\s<>\[\]()\"'`]+")
_LINK_OR_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)|\[[^\]]*\]\([^)]*\)")
_MD_REL = re.compile(
    r"(?<!!)\[[^\]]*\]\([^)\n]+\)\s*\{[^}\n]*\brel\s*=\s*[^}\n]*\}",
    re.IGNORECASE,
)
_HTML_A_REL = re.compile(
    r"<a\b[^>]*\brel\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s>]+)[^>]*>.*?</a>",
    re.IGNORECASE | re.DOTALL,
)
_HTML_TAG_REL = re.compile(
    r"<[a-zA-Z][^>]*\brel\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s>]+)[^>]*>",
    re.IGNORECASE,
)
_WORD = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?")
_STOP = frozenset(
    "a an the for of to and in on with from that this is are it or as by at".split()
)


def _deny(reason: str) -> dict[str, Any]:
    return {
        "ok": False,
        "outcome": "denied",
        "denied_reason": reason,
        "error": reason,
    }


def is_holder_href(href: str) -> bool:
    path = (href or "").split("?", 1)[0].strip()
    if not path.startswith("/"):
        return False
    trimmed = path.rstrip("/") or "/"
    if trimmed in HOLDERS or trimmed.startswith("/projects/"):
        return True
    return False


def published_posts(checkout: Path, *, slug: str) -> list[dict[str, str]]:
    blog = checkout / "content" / "blog"
    if not blog.is_dir():
        return []
    posts: list[dict[str, str]] = []
    for path in sorted(blog.glob("*.md")):
        if path.stem == slug:
            continue
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            continue
        end = text.find("\n---\n", 4)
        if end < 0:
            continue
        data = yaml.safe_load(text[4:end])
        if not isinstance(data, dict):
            continue
        canonical = str(data.get("canonical") or f"/blog/{path.stem}").strip()
        question = str(data.get("question") or "").strip()
        if is_holder_href(canonical) or not canonical.startswith("/blog/"):
            continue
        if not question or question.lower() in _GENERIC:
            continue
        posts.append({"canonical": canonical, "question": question, "slug": path.stem})
    return posts


def packet_urls(packet: list[dict[str, Any]]) -> list[str]:
    found: list[str] = []
    for fact in packet:
        source = str(fact.get("source") or "").strip()
        if source.startswith("http") and source not in found:
            found.append(source)
    return found


def clean_url(raw: str) -> str:
    return (raw or "").strip().rstrip(".,;:!?")


def urls_in_text(text: str) -> list[str]:
    """HTTP URLs already written in text. Nothing here is invented."""
    found: list[str] = []
    for match in _URL.findall(text or ""):
        url = clean_url(match)
        if url.startswith("http") and url not in found:
            found.append(url)
    for _anchor, href in _HREF.findall(text or ""):
        url = clean_url(href)
        if url.startswith("http") and url not in found:
            found.append(url)
    return found


def known_urls(
    packet: list[dict[str, Any]],
    *blobs: str,
) -> list[str]:
    """URLs that already appear on a packet source, a span, or the named file."""
    found = packet_urls(packet)
    for blob in blobs:
        for url in urls_in_text(blob):
            if url not in found:
                found.append(url)
    return found


def rel_carriers(text: str) -> list[str]:
    """A markdown link or an HTML tag that carries a rel attribute.

    A sentence that only talks about rel=\"nofollow\" or rel=\"sponsored\" is not a carrier.
    """
    found: list[str] = []
    covered: list[tuple[int, int]] = []
    for match in _HTML_A_REL.finditer(text or ""):
        found.append(match.group(0))
        covered.append((match.start(), match.end()))
    for match in _HTML_TAG_REL.finditer(text or ""):
        if any(start <= match.start() and match.end() <= end for start, end in covered):
            continue
        found.append(match.group(0))
    for match in _MD_REL.finditer(text or ""):
        found.append(match.group(0))
    return found


def refuse_links(
    markdown: str,
    *,
    published: set[str],
    urls: set[str],
    slug: str,
    cta: dict[str, str] | None,
    spans: list[str] | None = None,
) -> str | None:
    allowed_cta = set()
    if cta:
        allowed_cta = {cta["mail"], cta["call"]}
    quoted = {
        href
        for span in (spans or [])
        for _anchor, href in _HREF.findall(span)
    }
    self_path = f"/blog/{slug}"
    if rel_carriers(markdown):
        return "refusing rel on an editorial link"
    for anchor, href in _HREF.findall(markdown):
        if href in quoted:
            continue
        label = anchor.strip()
        target = href.strip()
        if not label or label.lower() in _GENERIC:
            return "anchor is empty or generic"
        if is_holder_href(target):
            return "refusing a site-wide holder path"
        if target in allowed_cta:
            if label != CTA_LABEL:
                return "call to action label must be Get in touch"
            continue
        if target.startswith("/"):
            if target not in published and target != self_path:
                return "internal link is not in the published set"
            continue
        if target not in urls:
            return "external link is not in the packet"
    if cta:
        hrefs = [href for _anchor, href in _HREF.findall(markdown)]
        cta_hrefs = [href for href in hrefs if href in allowed_cta]
        if len(set(cta_hrefs)) > 2:
            return "a third call to action href"
        if any(href not in allowed_cta and href.startswith("mailto:") for href in hrefs):
            return "a third call to action href"
    return None


def _question_phrases(question: str) -> list[str]:
    """The question, then shorter phrases that still name it. Not single words."""
    words = question.split()
    phrases = [question] if question else []
    for size in range(len(words) - 1, 3, -1):
        for index in range(0, len(words) - size + 1):
            window = words[index : index + size]
            content = [word for word in window if word.casefold().strip(":") not in _STOP]
            if len(content) < 3:
                continue
            phrases.append(" ".join(window))
    return phrases


def _covered(text: str) -> list[tuple[int, int]]:
    return [(match.start(), match.end()) for match in _LINK_OR_IMAGE.finditer(text)]


def _find_outside(text: str, phrase: str) -> int:
    if not phrase:
        return -1
    covered = _covered(text)
    at = text.find(phrase)
    while at >= 0:
        end = at + len(phrase)
        if not any(start < end and finish > at for start, finish in covered):
            return at
        at = text.find(phrase, at + 1)
    return -1


def _replace_outside(markdown: str, phrase: str, replacement: str) -> str:
    start = body_start(markdown)
    at = _find_outside(markdown[start:], phrase)
    if at < 0:
        return markdown
    at += start
    return markdown[:at] + replacement + markdown[at + len(phrase) :]


def _already_linked(markdown: str, url: str) -> bool:
    return f"]({url})" in markdown


def _link_internal(markdown: str, posts: list[dict[str, str]]) -> str:
    updated = markdown
    for post in sorted(posts, key=lambda item: len(item.get("question") or ""), reverse=True):
        canonical = post.get("canonical") or ""
        if not canonical.startswith("/blog/") or is_holder_href(canonical):
            continue
        if _already_linked(updated, canonical):
            continue
        for phrase in _question_phrases(post.get("question") or ""):
            if phrase not in updated[body_start(updated) :]:
                continue
            linked = _replace_outside(updated, phrase, f"[{phrase}]({canonical})")
            if linked != updated:
                updated = linked
                break
    return updated


def _words_both_sides(text: str, at: int, length: int) -> bool:
    """True when a phrase sits in the middle of a sentence, with words on both sides."""
    if at < 0:
        return False
    end = at + length
    left = max(text.rfind("\n", 0, at), text.rfind(".", 0, at), text.rfind("!", 0, at), text.rfind("?", 0, at))
    rights = [pos for pos in (text.find(".", end), text.find("!", end), text.find("?", end), text.find("\n", end)) if pos >= 0]
    right = min(rights) if rights else len(text)
    before = text[left + 1 : at]
    after = text[end:right]
    return bool(_WORD.search(before) and _WORD.search(after))


def _link_verbatim_spans(
    markdown: str,
    urls: list[str],
    facts: list[dict[str, Any]],
    spans: list[str],
) -> str:
    updated = markdown
    for url in urls:
        matched = [
            str(fact.get("span") or "")
            for fact in facts
            if str(fact.get("source") or "") == url and str(fact.get("span") or "")
        ]
        if not matched:
            matched = [span for span in spans if span and url not in span]
        matched.sort(key=len, reverse=True)
        for span in matched:
            if "](" in span or "![" in span:
                continue
            if span.strip().casefold() in _GENERIC:
                continue
            if span.strip().startswith("http://") or span.strip().startswith("https://"):
                continue
            body = updated[body_start(updated) :]
            at = _find_outside(body, span)
            if at < 0:
                continue
            if _words_both_sides(body, at, len(span)):
                continue
            updated = _replace_outside(updated, span, f"[{span}]({url})")
            break
    return updated


def _title_before(line: str, url_at: int) -> str:
    """The quoted or linked title that belongs to the URL at url_at, not an earlier URL."""
    before = line[:url_at]
    match = None
    for quote in re.finditer(r'"([^"]+)"|\[([^\]]+)\]', before):
        match = quote
    if match is None:
        return ""
    between = before[match.end() :]
    if "http://" in between or "https://" in between:
        return ""
    raw = match.group(1) if match.group(1) is not None else match.group(2)
    name = " ".join((raw or "").split()).strip().rstrip(".")
    if not name or name.casefold() in _GENERIC:
        return ""
    if name.startswith("http://") or name.startswith("https://"):
        return ""
    return name


_NAME_TAG = re.compile(
    r"^\*\*(?:FEASIBLE|EVIDENCE|POLICY|UNKNOWN|HUNCH|MARKETING)\.\*\*\s*",
    re.IGNORECASE,
)


def _phrase_before_url(line: str, url: str) -> str:
    """The name in this line that the URL belongs to. The URL is not the name."""
    at = line.find(url)
    if at < 0:
        return ""
    before = line[:at]
    before = _NAME_TAG.sub("", before.strip())
    before = before.replace("`", "")
    before = re.sub(r",?\s*is\s*$", "", before, flags=re.I)
    before = re.sub(r",?\s*at\s*$", "", before, flags=re.I)
    before = re.sub(r",?\s*read\s+\d{4}-\d{2}-\d{2},?\s*$", "", before, flags=re.I)
    if " for " in before:
        before = before.split(" for ", 1)[0]
    name = " ".join(before.split()).strip(" .,:;\"'")
    if name.casefold().startswith("the "):
        name = name[4:].strip()
    if " " not in name:
        return ""
    return name


def source_names(text: str, url: str) -> list[str]:
    """Titles this URL is cited under. A shared sentence does not give the URL every title on the line.

    A quoted title wins. When the line has none, the name is the phrase already
    in the sentence that states the URL, including a homepage address.
    """
    names: list[str] = []
    if not url or not text:
        return names

    def add(name: str) -> None:
        cleaned = " ".join(name.split()).strip().rstrip(".")
        if not cleaned or cleaned.casefold() in _GENERIC:
            return
        if cleaned.startswith("http://") or cleaned.startswith("https://"):
            return
        if cleaned.rstrip("/") == url.rstrip("/"):
            return
        if cleaned not in names:
            names.append(cleaned)

    link = re.compile(r"\[([^\]]+)\]\(\s*" + re.escape(url) + r"\s*\)")
    for match in link.finditer(text):
        add(match.group(1))
    for line in text.splitlines():
        start = 0
        while True:
            at = line.find(url, start)
            if at < 0:
                break
            add(_title_before(line, at))
            start = at + len(url)
    if names:
        return names
    for line in text.splitlines():
        if url not in line:
            continue
        add(_phrase_before_url(line, url))
    return names


def _in_whole_sentence(body: str, phrase: str) -> int:
    """Index of phrase inside one sentence that ends with punctuation, or -1."""
    if not phrase or phrase.casefold() in _GENERIC:
        return -1
    if phrase.startswith("http://") or phrase.startswith("https://"):
        return -1
    covered = _covered(body)
    at = body.find(phrase)
    while at >= 0:
        end = at + len(phrase)
        if any(start < end and finish > at for start, finish in covered):
            at = body.find(phrase, at + 1)
            continue
        rights = [pos for pos in (body.find(".", end), body.find("!", end), body.find("?", end)) if pos >= 0]
        if not rights:
            at = body.find(phrase, at + 1)
            continue
        right = min(rights)
        if "\n" in body[end:right]:
            at = body.find(phrase, at + 1)
            continue
        return at
    return -1


def _link_rewritten(
    markdown: str,
    urls: list[str],
    source_text: str,
    spans: list[str],
) -> str:
    """Link a source by its name, inside one whole sentence that uses that source.

    Two URLs do not claim the same name. A fragment, a URL, and "here" stay unlinked.
    """
    start = body_start(markdown)
    body = markdown[start:]
    blobs = [source_text, *spans]
    claimed: set[str] = set()
    for url in urls:
        if _already_linked(body, url):
            continue
        names: list[str] = []
        for blob in blobs:
            for name in source_names(blob, url):
                if name not in names:
                    names.append(name)
        names.sort(key=len, reverse=True)
        for name in names:
            key = name.casefold()
            if key in claimed:
                continue
            at = _in_whole_sentence(body, name)
            if at < 0:
                continue
            body = body[:at] + f"[{name}]({url})" + body[at + len(name) :]
            claimed.add(key)
            break
    return markdown[:start] + body


def _link_cited_urls(
    markdown: str,
    urls: list[str],
    source_text: str,
    spans: list[str],
) -> str:
    """Link a name already in the stored paragraph, in the sentence that uses that URL.

    The anchor is that name, including a homepage address the model rewrote
    into a bare URL. The anchor is not the URL. A URL that is not already
    named is not invented.
    """
    start = body_start(markdown)
    body = markdown[start:]
    blobs = [source_text, *spans]
    for url in sorted(urls, key=len, reverse=True):
        if not url.startswith("http") or _already_linked(body, url):
            continue
        names: list[str] = []
        for blob in blobs:
            for name in source_names(blob, url):
                if name not in names:
                    names.append(name)
        if not names:
            continue
        name = sorted(names, key=len, reverse=True)[0]
        tick = f"`{url}`"
        at = _find_outside(body, tick)
        if at >= 0:
            body = body[:at] + f"[{name}]({url})" + body[at + len(tick) :]
            continue
        at = _find_outside(body, url)
        if at < 0:
            continue
        body = body[:at] + f"[{name}]({url})" + body[at + len(url) :]
    return markdown[:start] + body


def apply_librarian(
    markdown: str,
    *,
    posts: list[dict[str, str]],
    urls: list[str],
    cta: dict[str, str] | None,
    spans: list[str],
    packet: list[dict[str, Any]] | None = None,
    source_text: str = "",
) -> str:
    """Thin call to action after the opening, and links inside paragraphs that use them.

    A call to action is inserted only when the config pair is present.
    A URL is linked only when it already appears in the source file or a packet span.
    """
    updated = markdown
    if cta:
        thin = f"\n\n[{CTA_LABEL}]({cta['mail']})\n"
        updated = insert_after_opening(updated, thin)
    updated = _link_internal(updated, posts)
    facts = packet or []
    updated = _link_verbatim_spans(updated, urls, facts, spans)
    known = known_urls(facts, source_text, *spans)
    updated = _link_rewritten(updated, known, source_text, spans)
    updated = _link_cited_urls(updated, known, source_text, spans)
    if cta:
        close = f"\n[{CTA_LABEL}]({cta['call']})\n"
        updated = updated.rstrip() + "\n" + close
    return updated


def wake_librarian(
    campaign_id: str,
    *,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    p = paths or require_ada_data()
    blocked = _require_chain(campaign_id, "librarian", p)
    if blocked:
        return blocked
    plan = load_plan(campaign_id, paths=p)
    item = current_item(plan) if plan else None
    page = read_page(campaign_id, paths=p)
    config = read_portfolio_chain(paths=p)
    if plan is None or item is None or page is None or not config.get("ok"):
        finish_stage(campaign_id, "librarian", paths=p, outcome="denied", advance=False)
        return _deny("plan queue is empty")
    draft_path = str(item.get("draft_path") or "")
    try:
        rel = draft_path[len("artifacts/") :] if draft_path.startswith("artifacts/") else draft_path
        target = _resolve_under_artifacts(artifacts_root(p), rel)
        markdown = target.read_text(encoding="utf-8")
    except (OSError, ValueError) as exc:
        finish_stage(campaign_id, "librarian", paths=p, outcome="denied", advance=False)
        return _deny(str(exc))
    packet = list(page.get("packet") or [])
    before = list(packet)
    slug = str(page.get("slug") or item.get("slug") or "")
    try:
        checkout = resolve_portfolio_checkout()
    except CheckoutError as exc:
        finish_stage(campaign_id, "librarian", paths=p, outcome="denied", advance=False)
        return _deny(str(exc))
    try:
        file_text = source_file(str(page.get("source") or "")).read_text(encoding="utf-8")
    except (OSError, ValueError):
        file_text = ""
    stored = section_text(item)
    source_text = stored or file_text
    posts = published_posts(checkout, slug=slug)
    spans = [str(fact.get("span") or "") for fact in packet]
    urls = known_urls(packet, source_text, *spans)
    for url in citation_urls(source_text):
        if url not in urls:
            urls.append(url)
    cta = config["config"].get("default_cta")
    updated = apply_librarian(
        markdown,
        posts=posts,
        urls=packet_urls(packet),
        cta=cta if isinstance(cta, dict) else None,
        spans=spans,
        packet=packet,
        source_text=source_text,
    )
    problem = refuse_links(
        updated,
        published={post["canonical"] for post in posts},
        urls=set(urls),
        slug=slug,
        cta=cta if isinstance(cta, dict) else None,
        spans=spans,
    )
    if problem:
        finish_stage(campaign_id, "librarian", paths=p, outcome="denied", advance=False)
        return _deny(problem)
    if page.get("packet") != before:
        finish_stage(campaign_id, "librarian", paths=p, outcome="denied", advance=False)
        return _deny("librarian adds a fact")
    atomic_write_text(target, updated)
    return finish_stage(
        campaign_id,
        "librarian",
        paths=p,
        outcome="ok",
        slug=slug,
        receipt_paths=[draft_path],
    )
