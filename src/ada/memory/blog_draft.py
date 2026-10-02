"""Draft one local markdown file from a gated packet."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from ada.io.paths import DataPaths, require_ada_data
from ada.memory.artifacts import write_artifact
from ada.memory.blog_packet import gate_packet, source_file
from ada.memory.blog_slug import SlugError, blog_slug
from ada.memory.campaign_page import next_wake_iso, read_page, write_page
from ada.memory.open_loops import upsert_loop

_PICTURE = re.compile(r"^[A-Za-z0-9_./-]+\.(?:png|jpe?g|gif|webp|svg|avif)$")
_IMAGE_LINE = re.compile(r"!\[[^\]]*\]\([^)]+\)|<img\b", re.IGNORECASE)
_SENTENCE_END = re.compile(r"[.!?]")


class BlogDraftError(ValueError):
    """The draft refuses to emit this markdown."""


def first_sentence(question: str) -> str:
    """First sentence of the question. Adds no word the question did not contain."""
    text = (question or "").strip()
    if not text:
        return ""
    match = _SENTENCE_END.search(text)
    if match is None:
        return text
    return text[: match.end()]


def utc_calendar_day() -> str:
    """UTC calendar date of this call. Not a date copied out of a packet."""
    return datetime.now(timezone.utc).date().isoformat()


def _is_picture_path(span: str) -> bool:
    return bool(_PICTURE.match(span.strip()))


def _deny(reason: str) -> dict[str, Any]:
    return {
        "ok": False,
        "outcome": "denied",
        "denied_reason": reason,
        "error": reason,
    }


def account_prose(span_count: int) -> str:
    """New sentences. An account of the packet, not a paste of the source."""
    return (
        "This page is an account of the gathered packet. "
        f"Its table repeats {span_count} spans from that packet.\n"
    )


def _table(spans: list[str]) -> str:
    cells = [span for span in spans if span and "\n" not in span and "|" not in span]
    if not cells:
        return ""
    lines = [f"| {cells[0]} |", "| --- |"]
    lines.extend(f"| {cell} |" for cell in cells[1:])
    return "\n".join(lines)


def _cta_line(call_to_action: dict[str, Any] | None) -> str:
    if not call_to_action:
        return ""
    label = str(call_to_action.get("label") or "").strip()
    url = str(call_to_action.get("url") or "").strip()
    if not label or not url:
        return ""
    return f"[{label}]({url})"


def compose_markdown(
    *,
    question: str,
    fill: str,
    source: str,
    slug: str,
    prose: str,
    spans: list[str],
    published: str,
    modified: str,
    call_to_action: dict[str, Any] | None = None,
    image: bool = False,
    span_table: bool = True,
) -> str:
    """Frontmatter blog.ts requires, plus prose, a table of spans, and an optional CTA.

    The blog form keeps ``span_table`` on. The chain draft turns it off.
    """
    if not prose.strip():
        raise BlogDraftError("prose required")
    picture = next((span for span in spans if _is_picture_path(span)), None)
    if image and picture is None:
        raise BlogDraftError(
            "image line refused: no packet span is a picture path"
        )
    description = first_sentence(question)
    front = "\n".join(
        [
            "---",
            f"title: {json.dumps(question, ensure_ascii=False)}",
            f"question: {json.dumps(question, ensure_ascii=False)}",
            f"description: {json.dumps(description, ensure_ascii=False)}",
            f"published: {json.dumps(published, ensure_ascii=False)}",
            f"modified: {json.dumps(modified, ensure_ascii=False)}",
            f"fill: {json.dumps(fill, ensure_ascii=False)}",
            f"source: {json.dumps(source, ensure_ascii=False)}",
            f"canonical: {json.dumps('/blog/' + slug, ensure_ascii=False)}",
            "---",
            "",
            prose.rstrip(),
            "",
        ]
    )
    if span_table:
        table = _table(spans)
        if table:
            front += table + "\n"
    cta = _cta_line(call_to_action)
    if cta:
        front += "\n" + cta + "\n"
    if image and picture is not None:
        front += f"\n![]({picture})\n"
    if _IMAGE_LINE.search(front) and picture is None:
        raise BlogDraftError(
            "image line refused: no packet span is a picture path"
        )
    return front if front.endswith("\n") else front + "\n"


def replace_frontmatter_dates(markdown: str, day: str) -> str:
    """Set published and modified in the frontmatter to ``day``. Leave the body."""
    parsed = datetime.strptime(day, "%Y-%m-%d").date()
    if parsed.isoformat() != day:
        raise BlogDraftError("date must be YYYY-MM-DD")
    if parsed > datetime.now(timezone.utc).date():
        raise BlogDraftError("refusing a future date")
    if not markdown.startswith("---\n"):
        raise BlogDraftError("missing frontmatter")
    end = markdown.find("\n---\n", 4)
    if end < 0:
        raise BlogDraftError("missing frontmatter close")
    head = markdown[4:end]
    rest = markdown[end:]
    found: set[str] = set()
    lines: list[str] = []
    for line in head.splitlines():
        key = line.split(":", 1)[0].strip().strip('"')
        if key in {"published", "modified"}:
            lines.append(f"{key}: {json.dumps(day)}")
            found.add(key)
        else:
            lines.append(line)
    if found != {"published", "modified"}:
        raise BlogDraftError("frontmatter dates missing")
    return "---\n" + "\n".join(lines) + rest


def draft_page(
    *,
    campaign_id: str,
    confirmed: bool = False,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    """Write artifacts/{UTC date}/{slug}.md from the gated packet. Adds no fact."""
    p = paths or require_ada_data()
    page = read_page(campaign_id, paths=p)
    if page is None:
        return _deny("campaign page is missing")
    packet = page.get("packet")
    if not isinstance(packet, list) or not packet:
        return _deny("gather has not left a packet")
    source = str(page.get("source") or "").strip()
    try:
        file_text = source_file(source).read_text(encoding="utf-8")
    except (ValueError, FileNotFoundError, OSError) as exc:
        return _deny(f"source file is missing: {exc}")
    gated = gate_packet(page=page, facts=list(packet), file_text=file_text)
    if not gated.get("ok"):
        return gated
    if list(gated["packet"]) != list(packet):
        return _deny("draft adds no fact")
    question = str(page.get("question") or "")
    try:
        slug = blog_slug(question)
    except SlugError as exc:
        return _deny(str(exc))
    spans = [str(fact["span"]) for fact in gated["packet"]]
    prose = account_prose(len(spans))
    day = utc_calendar_day()
    try:
        markdown = compose_markdown(
            question=question,
            fill=str(page.get("fill") or ""),
            source=source,
            slug=slug,
            prose=prose,
            spans=spans,
            published=day,
            modified=day,
            call_to_action=page.get("call_to_action")
            if isinstance(page.get("call_to_action"), dict)
            else None,
            image=False,
        )
    except BlogDraftError as exc:
        return _deny(str(exc))
    rel = f"{day}/{slug}.md"
    exists = (p.artifacts / rel).is_file()
    result = write_artifact(
        title="campaign page",
        body=markdown,
        format="md",
        source_cites=None,
        overwrite=exists,
        confirmed=confirmed,
        relative_path=rel,
        campaign_id=campaign_id,
        next_stage="deploy",
        paths=p,
    )
    if not result.get("ok"):
        return result
    handshake = result.get("handshake") or {}
    if handshake.get("ok") is False:
        return handshake
    stored = dict(page)
    stored["packet"] = list(packet)
    stored["slug"] = slug
    write_page(campaign_id, stored, paths=p)
    upsert_loop(
        loop_id=campaign_id,
        next_wake_at=next_wake_iso(),
        paths=p,
    )
    result["slug"] = slug
    return result
