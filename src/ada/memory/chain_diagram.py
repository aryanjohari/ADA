"""Stage one SVG under artifacts/. Deliver copies it after the critic passes."""

from __future__ import annotations

import re
from typing import Any

from ada.io.atomic import atomic_write_text
from ada.io.paths import DataPaths, require_ada_data
from ada.memory.artifacts import _resolve_under_artifacts, artifacts_root
from ada.memory.campaign_page import read_page
from ada.memory.chain_draft import body_start, opening_answer
from ada.memory.chain_plan import (
    _require_chain,
    current_item,
    finish_stage,
    load_plan,
    save_plan,
)

_NUMBERED = re.compile(r"^\d+\. \S")
_IMAGE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)", re.IGNORECASE)
_UNSPLASH = re.compile(r"unsplash\.com", re.IGNORECASE)
ALT = "Diagram of how it works"


def _deny(reason: str) -> dict[str, Any]:
    return {
        "ok": False,
        "outcome": "denied",
        "denied_reason": reason,
        "error": reason,
    }


def _table_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2


def flow_span(markdown: str) -> tuple[int, int] | None:
    """Offsets of the first numbered sequence in the body. A table is not a flow."""
    start = body_start(markdown)
    offset = start
    block_start: int | None = None
    block_end: int | None = None
    for line in markdown[start:].splitlines(keepends=True):
        if _table_line(line):
            if block_start is not None:
                break
            offset += len(line)
            continue
        if _NUMBERED.match(line.strip()):
            if block_start is None:
                block_start = offset
            block_end = offset + len(line)
        elif block_start is not None:
            break
        offset += len(line)
    if block_start is None or block_end is None:
        return None
    return block_start, block_end


def how_it_works(markdown: str) -> str:
    """The numbered sequence. A table is not a flow, and ordinary paragraphs are empty."""
    found = flow_span(markdown)
    if not found:
        return ""
    return markdown[found[0] : found[1]]


def section_is_flow(markdown: str) -> bool:
    return flow_span(markdown) is not None


def is_keyword_alt(alt: str) -> bool:
    text = (alt or "").strip()
    if not text:
        return True
    if text.count(",") >= 3:
        return True
    return False


def is_generic_alt(alt: str) -> bool:
    """True for a stock label or an alt that quotes table rows."""
    raw = alt or ""
    folded = " ".join(raw.casefold().split())
    if not folded or folded in {"how it works", ALT.casefold()}:
        return True
    if "|" in raw:
        return True
    return False


def flow_labels(block: str) -> list[str]:
    """Step text from a numbered sequence. A table row is not a step."""
    labels: list[str] = []
    for raw in block.splitlines():
        stripped = raw.strip()
        if not _NUMBERED.match(stripped):
            continue
        labels.append(stripped.split(". ", 1)[1].strip())
    return labels


def diagram_alt(labels: list[str]) -> str:
    """Alt text that names the steps. A table row is not a label."""
    if any("|" in label for label in labels):
        return ""

    def clip(label: str) -> str:
        cleaned = label
        for mark in (",", "[", "]", "(", ")"):
            cleaned = cleaned.replace(mark, " ")
        return " ".join(cleaned.split()[:8])

    shown = [clip(label) for label in labels if clip(label)]
    if not shown:
        return ""
    if len(shown) == 1:
        return f"Diagram of {shown[0]}"
    return f"Diagram of {shown[0]} and {shown[-1]}"


def unsplash_or_hotlink(markdown: str) -> bool:
    if _UNSPLASH.search(markdown):
        return True
    for target in _IMAGE.findall(markdown):
        if target.startswith("http://") or target.startswith("https://"):
            return True
    return False


def _svg(lines: list[str]) -> str:
    height = 28 + 22 * max(len(lines), 1)
    chunks = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 720 {height}">']
    for index, line in enumerate(lines):
        safe = (
            line.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        chunks.append(f'<text x="8" y="{24 + index * 22}">{safe}</text>')
    chunks.append("</svg>\n")
    return "".join(chunks)


def _same_image(markdown: str, src: str) -> bool:
    return any(target == src for target in _IMAGE.findall(markdown))


def _replace_alt(markdown: str, src: str, alt: str) -> str:
    pattern = re.compile(r"!\[[^\]]*\]\(" + re.escape(src) + r"\)")
    return pattern.sub(f"![{alt}]({src})", markdown, count=1)


def wake_diagram(
    campaign_id: str,
    *,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    p = paths or require_ada_data()
    blocked = _require_chain(campaign_id, "diagram", p)
    if blocked:
        return blocked
    plan = load_plan(campaign_id, paths=p)
    item = current_item(plan) if plan else None
    page = read_page(campaign_id, paths=p)
    if plan is None or item is None or page is None:
        finish_stage(campaign_id, "diagram", paths=p, outcome="denied", advance=False)
        return _deny("plan queue is empty")
    draft_path = str(item.get("draft_path") or "")
    slug = str(page.get("slug") or item.get("slug") or "")
    try:
        rel = draft_path[len("artifacts/") :] if draft_path.startswith("artifacts/") else draft_path
        target = _resolve_under_artifacts(artifacts_root(p), rel)
        markdown = target.read_text(encoding="utf-8")
    except (OSError, ValueError) as exc:
        finish_stage(campaign_id, "diagram", paths=p, outcome="denied", advance=False)
        return _deny(str(exc))
    if unsplash_or_hotlink(markdown):
        finish_stage(campaign_id, "diagram", paths=p, outcome="denied", advance=False)
        return _deny("refusing an Unsplash or hotlinked image")
    if "content/blog/" in rel or rel.startswith("content/"):
        finish_stage(campaign_id, "diagram", paths=p, outcome="denied", advance=False)
        return _deny("diagram stays under artifacts/")
    if not section_is_flow(markdown):
        item["diagram"] = "skip"
        save_plan(plan, paths=p)
        return finish_stage(
            campaign_id,
            "diagram",
            paths=p,
            outcome="skip",
            slug=slug,
        )
    found = flow_span(markdown)
    if not found:
        item["diagram"] = "skip"
        save_plan(plan, paths=p)
        return finish_stage(
            campaign_id,
            "diagram",
            paths=p,
            outcome="skip",
            slug=slug,
        )
    labels = flow_labels(markdown[found[0] : found[1]])
    alt = diagram_alt(labels)
    if not labels or not alt or is_keyword_alt(alt) or is_generic_alt(alt):
        finish_stage(campaign_id, "diagram", paths=p, outcome="denied", advance=False)
        return _deny("alt text is a keyword list")
    day = rel.split("/", 1)[0]
    svg_rel = f"{day}/{slug}.svg"
    try:
        svg_path = _resolve_under_artifacts(artifacts_root(p), svg_rel)
    except ValueError as exc:
        finish_stage(campaign_id, "diagram", paths=p, outcome="denied", advance=False)
        return _deny(str(exc))
    atomic_write_text(svg_path, _svg(labels))
    src = f"content/blog/media/{slug}.svg"
    if _same_image(markdown, src):
        updated = _replace_alt(markdown, src, alt)
    else:
        image = f"\n![{alt}]({src})\n"
        _start_at, end_at = found
        updated = markdown[:end_at] + image + markdown[end_at:]
    answer = opening_answer(updated)
    direct = updated.find(answer) if answer else -1
    image_at = updated.find("![")
    if direct < 0 or image_at < direct:
        finish_stage(campaign_id, "diagram", paths=p, outcome="denied", advance=False)
        return _deny("image sits above the direct answer")
    if updated.count("![") > 1:
        finish_stage(campaign_id, "diagram", paths=p, outcome="denied", advance=False)
        return _deny("diagram already has its one image")
    atomic_write_text(target, updated)
    staged = f"artifacts/{svg_rel}"
    item["diagram"] = staged
    save_plan(plan, paths=p)
    return finish_stage(
        campaign_id,
        "diagram",
        paths=p,
        outcome="ok",
        slug=slug,
        receipt_paths=[staged, draft_path],
    )

