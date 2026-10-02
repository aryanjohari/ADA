"""External fetch, gather, and gate. New facts enter only here."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ada.io.paths import DataPaths, require_ada_data
from ada.memory import blog_packet
from ada.memory.blog_packet import gate_packet, source_file
from ada.memory.campaign_page import read_page, write_page
from ada.memory.chain_plan import (
    _FRAME,
    _WORD,
    _access_date_only,
    _require_chain,
    _sentences_in_line,
    current_item,
    finish_stage,
    load_plan,
    save_plan,
)
from ada.memory.portfolio_chain import read_portfolio_chain
from ada.web.fetch import web_fetch

_LINK = re.compile(r"\[[^\]]+\]\((https?://[^)\s]+)\)")
_HEADING = re.compile(r"^#{1,6}\s+(\S.*?)\s*$")
_LOCAL_CAP = 3
_SENTENCE_CAP = 2
_SKIP_DIR = frozenset({"node_modules", "__pycache__", "venv"})
_CHOOSE_SYSTEM = (
    "You pick at most 3 notes that teach this page. "
    "Reply with the paths only. A shared date is not a reason. "
    "Do not pick a path because it shares words with the fact sentence."
)


def _deny(reason: str) -> dict[str, Any]:
    return {
        "ok": False,
        "outcome": "denied",
        "denied_reason": reason,
        "error": reason,
    }


def is_search_url(url: str) -> bool:
    """Refuse a results query. A document under /search/docs/ is not a query."""
    text = str(url or "").strip()
    if not text:
        return False
    parsed = urlparse(text)
    path = parsed.path or ""
    if path == "/search/docs" or path.startswith("/search/docs/"):
        return False
    if "search?q=" in text:
        return True
    bare_search = path.rstrip("/") == "/search"
    if bare_search and "q=" in (parsed.query or ""):
        return True
    host = (parsed.hostname or "").lower()
    if bare_search and "google." in host:
        return True
    return False


def named_urls(item: dict[str, Any], source_text: str) -> list[str]:
    """URLs the item already names, including links written in its source card."""
    if "urls" in item and item.get("urls") is not None:
        raw = item.get("urls") or []
    else:
        raw = _LINK.findall(source_text)
    found: list[str] = []
    for url in raw:
        text = str(url).strip()
        if text and text not in found:
            found.append(text)
    return found


def _content_words(*parts: str) -> list[str]:
    """Words already written in the fact and the question. Frame words do not count."""
    found: list[str] = []
    seen: set[str] = set()
    for part in parts:
        for word in _WORD.findall(part or ""):
            token = word.casefold()
            if token in _FRAME or token in seen:
                continue
            seen.add(token)
            found.append(token)
    return found


def _heading_surface(path: Path) -> str:
    """The file name and the first heading. The body is not a match surface."""
    title = path.stem.replace("_", " ").replace("-", " ")
    heading = ""
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                match = _HEADING.match(line.strip())
                if match:
                    heading = match.group(1)
                    break
    except OSError:
        heading = ""
    return f"{title}\n{heading}".casefold()


def _word_in(surface: str, word: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(word)}(?![a-z0-9])", surface) is not None


def _skipped(rel: Path) -> bool:
    return any(part.startswith(".") or part in _SKIP_DIR for part in rel.parts)


def _first_heading(text: str) -> str:
    for line in text.splitlines():
        match = _HEADING.match(line.strip())
        if match:
            return match.group(1).strip()
    return ""


def _file_sentences(text: str, *, limit: int = _SENTENCE_CAP) -> list[str]:
    """At most ``limit`` sentences already written in the file. None are invented."""
    found: list[str] = []
    for line in text.splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or raw.startswith("|") or raw.startswith("```"):
            continue
        if _access_date_only(raw):
            continue
        for sentence in _sentences_in_line(raw, text):
            if _access_date_only(sentence) or sentence in found:
                continue
            found.append(sentence)
            if len(found) >= limit:
                return found
    return found


def fact_terms(fact: str) -> list[str]:
    """Content words in the fact. A date, a status code, and a frame word do not count."""
    terms: list[str] = []
    seen: set[str] = set()
    for word in _WORD.findall(fact or ""):
        token = word.casefold()
        if token in _FRAME or token.isdigit() or token in seen:
            continue
        seen.add(token)
        terms.append(token)
    return terms


def sentences_meet_fact(sentences: str, fact: str) -> bool:
    """True when the file's own sentences carry the fact. A shared date does not."""
    terms = fact_terms(fact)
    if not terms:
        return False
    hits = [term for term in terms if _word_in(sentences.casefold(), term)]
    if len(terms) == 1:
        return bool(hits)
    need = min(len(terms), max(2, (len(terms) + 1) // 2))
    return len(hits) >= need


def _catalog_row(path: Path, root: Path) -> dict[str, Any] | None:
    try:
        rel = path.resolve().relative_to(root)
    except ValueError:
        return None
    if _skipped(rel):
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    return {
        "path": rel.as_posix(),
        "heading": _first_heading(text),
        "sentences": _file_sentences(text),
    }


def research_catalog(named_source: str = "", extra: list[str] | None = None) -> list[dict[str, Any]]:
    """Rows for ``docs/research/**/*.md``, the named source, and proof paths.

    Each row is a path, the first heading, and at most two sentences already
    in the file. Dot directories, ``node_modules``, ``__pycache__``, and
    ``venv`` are skipped. This does not score file names and does not call Gemini.
    """
    root = blog_packet.repo_root().resolve()
    found: list[Path] = []
    research = root / "docs" / "research"
    if research.is_dir():
        for path in research.rglob("*.md"):
            if path.is_file():
                found.append(path)
    named_paths = [str(named_source or "").strip()]
    named_paths.extend(str(path).strip() for path in (extra or []) if str(path).strip())
    for named in named_paths:
        if not named:
            continue
        try:
            named_path = source_file(named)
        except (ValueError, FileNotFoundError, OSError):
            named_path = None
        if named_path is not None:
            found.append(named_path)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in sorted(found, key=lambda item: item.as_posix()):
        row = _catalog_row(path, root)
        if row is None or row["path"] in seen:
            continue
        seen.add(row["path"])
        rows.append(row)
    return rows


def _choose_prompt(
    brief: str,
    rows: list[dict[str, Any]],
    *,
    rejected: list[str] | None = None,
) -> str:
    lines = [f"Brief:\n{brief}", ""]
    if rejected:
        lines.append("These paths do not teach the page.")
        lines.append("A shared date is not a reason.")
        lines.extend(rejected)
        lines.append("")
    lines.extend(
        [
            "Return at most 3 paths that teach this page.",
            "One path per line.",
            "Use only a path from the rows.",
            "Do not pick a path because it shares words with the fact sentence.",
            "A shared date is not a reason.",
            "Do not search the web.",
            "",
            "Rows:",
        ]
    )
    for row in rows:
        lines.append(f"path: {row.get('path') or ''}")
        lines.append(f"heading: {row.get('heading') or ''}")
        lines.append("sentences: " + " ".join(str(s) for s in (row.get("sentences") or [])))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _paths_from_reply(text: str, allowed: set[str]) -> list[str]:
    found: list[str] = []
    ordered = sorted(allowed, key=len, reverse=True)
    for line in text.splitlines():
        cleaned = line.strip().strip("`").strip()
        if cleaned.startswith("- "):
            cleaned = cleaned[2:].strip()
        if cleaned.lower().startswith("path:"):
            cleaned = cleaned.split(":", 1)[1].strip()
        if cleaned in allowed and cleaned not in found:
            found.append(cleaned)
        else:
            for path in ordered:
                if path in cleaned and path not in found:
                    found.append(path)
                    break
        if len(found) >= _LOCAL_CAP:
            break
    return found


def _paragraph_blocks(text: str) -> list[str]:
    """Blank-line blocks already in the file. Nothing is joined across a gap."""
    blocks: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        if line.strip():
            current.append(line.rstrip())
        elif current:
            blocks.append("\n".join(current).strip())
            current = []
    if current:
        blocks.append("\n".join(current).strip())
    return blocks


def _block_sentences(block: str, file_text: str) -> list[str]:
    found: list[str] = []
    for line in block.splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or raw.startswith("|") or raw.startswith("```"):
            continue
        if _access_date_only(raw):
            continue
        for sentence in _sentences_in_line(raw, file_text):
            if _access_date_only(sentence) or sentence in found:
                continue
            found.append(sentence)
    return found


_OUT_TAG = re.compile(r"^\*\*(UNKNOWN|POLICY|HUNCH)\b", re.I)


def _tagged_out(block: str) -> bool:
    """A paragraph tagged UNKNOWN, POLICY, or HUNCH is not a teaching passage."""
    return bool(_OUT_TAG.match(block.strip()))


def _different_claim(block: str) -> bool:
    """A neighbor that states a different claim, including the two lab lines."""
    flat = " ".join(block.replace("*", "").split())
    if "Which path on the origin the one URL uses" in flat:
        return True
    return bool(re.search(r"indexed is UNKNOWN", flat, re.I))


def _feasible(block: str) -> bool:
    return bool(re.match(r"^\*\*FEASIBLE\b", block.strip(), re.I))


def _shares_subject(block: str, subject: str) -> bool:
    """True when the paragraph uses a content word from the idea or the fact."""
    terms = [term for term in fact_terms(subject) if len(term) >= 4]
    if not terms:
        terms = fact_terms(subject)
    if not terms:
        return False
    folded = block.casefold()
    return any(_word_in(folded, term) for term in terms)


def _fact_hits(text: str, fact: str) -> int:
    folded = text.casefold()
    return sum(1 for term in fact_terms(fact) if _word_in(folded, term))


def paragraph_meeting_fact(text: str, fact: str) -> str:
    """The later paragraph that meets the fact. A heading only locates it.

    The paragraph that already contains the fact sentence is that paragraph.
    A paragraph tagged UNKNOWN, POLICY, or HUNCH is left out. A neighbor that
    states a different claim is left out, including one that only shares some
    of the fact's words. The rest of the heading is not this paragraph.
    """
    best = ""
    best_hits = -1
    for block in _paragraph_blocks(text):
        if block.startswith("#") and "\n" not in block:
            continue
        if _tagged_out(block) or _different_claim(block):
            continue
        if fact_sentence_in(block, fact):
            return block
        if beside_other_question(block, fact):
            continue
        if not sentences_meet_fact(block, fact):
            continue
        hits = _fact_hits(block, fact)
        if hits > best_hits:
            best = block
            best_hits = hits
    return best


def _heading_for(text: str, paragraph: str) -> str:
    """The heading that locates ``paragraph``. The heading text is not the paragraph."""
    if not paragraph:
        return ""
    lines = text.splitlines()
    first = paragraph.splitlines()[0].rstrip()
    start = None
    for index, line in enumerate(lines):
        if line.rstrip() == first:
            start = index
            break
    if start is None:
        return ""
    for index in range(start, -1, -1):
        match = _HEADING.match(lines[index].strip())
        if match:
            return match.group(1).strip()
    return ""


def _heading_level(line: str) -> int | None:
    match = _HEADING.match(line.strip())
    if not match:
        return None
    return len(line.strip()) - len(line.strip().lstrip("#"))


def _section_around(text: str, paragraph: str) -> str:
    """The heading that contains ``paragraph``, through the next heading of that level."""
    if not paragraph:
        return ""
    lines = text.splitlines()
    para_lines = paragraph.splitlines()
    start_line = None
    for index in range(len(lines)):
        if lines[index].rstrip() != para_lines[0].rstrip():
            continue
        if all(
            index + offset < len(lines) and lines[index + offset].rstrip() == para.rstrip()
            for offset, para in enumerate(para_lines)
        ):
            start_line = index
            break
    if start_line is None:
        return ""
    heading_at = None
    level = None
    for index in range(start_line, -1, -1):
        found = _heading_level(lines[index])
        if found is not None:
            heading_at = index
            level = found
            break
    if heading_at is None or level is None:
        return paragraph
    end = len(lines)
    for index in range(heading_at + 1, len(lines)):
        found = _heading_level(lines[index])
        if found is not None and found <= level:
            end = index
            break
    return "\n".join(lines[heading_at:end]).strip()


def section_meeting_fact(text: str, fact: str) -> str:
    """The heading that contains the paragraph which meets the fact.

    The section runs through the line before the next heading of the same
    or higher level. It is not one block and it is not the whole file.
    """
    return _section_around(text, paragraph_meeting_fact(text, fact))


def _teaching_passages(section: str, fact: str, idea: str) -> list[str]:
    """Passages in this heading that teach the idea.

    The homepage paragraph may be one of them. It is not the only passage
    when the heading has other teaching passages. UNKNOWN, POLICY, and HUNCH
    stay out. A neighbor that states a different claim stays out.
    """
    subject = idea.strip() or fact
    kept: list[str] = []
    for block in _paragraph_blocks(section):
        if block.startswith("#") and "\n" not in block:
            continue
        if _tagged_out(block) or _different_claim(block):
            continue
        if (
            fact_sentence_in(block, fact)
            or _feasible(block)
            or _shares_subject(block, subject)
            or _shares_subject(block, fact)
        ):
            if block not in kept:
                kept.append(block)
    return kept


def _flat_fact(text: str) -> str:
    return " ".join(text.replace("`", "").split()).casefold().rstrip(".")


def fact_sentence_in(text: str, fact: str) -> bool:
    """True when ``text`` already contains the fact sentence. Backticks do not hide it."""
    left = _flat_fact(fact)
    return bool(left) and left in _flat_fact(text)


def beside_other_question(text: str, fact: str) -> bool:
    """A paragraph that repeats the measurement beside a different question.

    The named source's own fact sentence is not this case.
    """
    if not text.strip() or fact_sentence_in(text, fact):
        return False
    sentences: list[str] = []
    for line in text.splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or raw.startswith("|") or raw.startswith("```"):
            continue
        if _access_date_only(raw):
            continue
        for sentence in _sentences_in_line(raw, text):
            if _access_date_only(sentence) or sentence in sentences:
                continue
            sentences.append(sentence)
    measurement = [sentence for sentence in sentences if sentences_meet_fact(sentence, fact)]
    others = [sentence for sentence in sentences if sentence not in measurement]
    return bool(measurement and others)


def note_for_fact(
    row: dict[str, Any],
    fact: str,
    idea: str = "",
) -> dict[str, Any] | None:
    """Teaching passages under the heading that holds the fact.

    The catalog row stays a path, a heading, and at most two sentences.
    The stored note is the passages in that heading that teach the idea.
    The homepage paragraph may be one of them when the fact cites the live
    host. It is not the only stored body when that heading has other teaching
    passages. UNKNOWN, POLICY, and HUNCH stay out, as does a neighbor that
    states a different claim. The whole file is not stored.
    """
    if row.get("_note_set") and row.get("_note_idea") == idea:
        cached = row.get("_note")
        return cached if isinstance(cached, dict) else None
    sentences = [
        str(sentence).strip()
        for sentence in (row.get("sentences") or [])
        if str(sentence).strip()
    ][:_SENTENCE_CAP]
    path = str(row.get("path") or "")
    heading = str(row.get("heading") or "")
    catalog_text = " ".join(sentences)
    catalog_meets = sentences_meet_fact(catalog_text, fact) or fact_sentence_in(
        catalog_text, fact
    )
    try:
        text = source_file(path).read_text(encoding="utf-8")
    except (ValueError, FileNotFoundError, OSError):
        text = ""
    anchor = paragraph_meeting_fact(text, fact) if text else ""
    passages = _teaching_passages(_section_around(text, anchor), fact, idea) if anchor else []
    row["_note_idea"] = idea
    row["_note_set"] = True
    if passages:
        body = "\n\n".join(passages)
        note = {
            "path": path,
            "heading": _heading_for(text, anchor) or heading,
            "sentences": _block_sentences(body, text or body),
            "paragraph": body,
            "section": body,
        }
        row["_note"] = note
        return note
    if catalog_meets and not any(_different_claim(sentence) for sentence in sentences):
        note = {"path": path, "heading": heading, "sentences": sentences}
        row["_note"] = note
        return note
    row["_note"] = None
    return None


def keep_fact_files(
    paths: list[str],
    rows: dict[str, dict[str, Any]],
    fact: str,
    named_source: str,
    idea: str = "",
) -> list[str]:
    """At most three paths. A file is kept when it has a teaching passage.

    The named source is kept when it has one. A chosen file is kept because
    it teaches the idea. A fourth file is not added.
    """
    kept: list[str] = []
    named = str(named_source or "").strip()
    named_row = rows.get(named)
    if named_row is not None and note_for_fact(named_row, fact, idea=idea) is not None:
        kept.append(named)
    for path in paths:
        if path in kept or len(kept) >= _LOCAL_CAP:
            continue
        row = rows.get(path)
        if row is None:
            continue
        if note_for_fact(row, fact, idea=idea) is None:
            continue
        kept.append(path)
    return kept[:_LOCAL_CAP]


def _clear_note(row: dict[str, Any]) -> None:
    row.pop("_note_set", None)
    row.pop("_note_idea", None)
    row.pop("_note", None)


def _row_teaches(row: dict[str, Any], sentences: list[str], idea: str) -> bool:
    """True when a stored fact in this note teaches the page."""
    for sentence in sentences:
        _clear_note(row)
        if note_for_fact(row, sentence, idea=idea) is not None:
            return True
    return False


def _rows_meet(
    paths: list[str],
    rows: dict[str, dict[str, Any]],
    fact: str,
    idea: str = "",
    facts: list[str] | None = None,
) -> list[str]:
    """Keep a chosen path when it has a teaching passage.

    At most three paths. A path that does not teach is not replaced by a fourth file.
    Any stored fact sentence may be the evidence. One named source is not required.
    """
    sentences = [text for text in (facts or []) if text] or ([fact] if fact else [])
    kept: list[str] = []
    for path in paths:
        row = rows.get(path)
        if row is None or path in kept:
            continue
        if _row_teaches(row, sentences, idea):
            kept.append(path)
        if len(kept) >= _LOCAL_CAP:
            break
    return kept


def choose_notes(
    model: Any,
    *,
    brief: str,
    rows: list[dict[str, Any]],
    fact: str,
    facts: list[str] | None = None,
) -> dict[str, Any]:
    """One Gemini call sees the page and the catalog rows. It does not see the prior prompt.

    At most three paths are kept. A path is kept when it teaches the page.
    It is not kept because its catalog sentences share words with one fact
    sentence, and it is not kept because it was the one named source.
    A shared date is not a reason. If the chosen paths do not teach, the
    same catalog is shown once more. That second look does not add a fourth
    file. An empty reply denies without it. This does not search the web.
    """
    from ada.cortex.gemini import user_content

    by_path = {str(row.get("path") or ""): row for row in rows if row.get("path")}
    sentences = [text for text in (facts or []) if text] or ([fact] if fact else [])

    def once(rejected: list[str] | None = None) -> list[str]:
        prompt = _choose_prompt(brief, rows, rejected=rejected)
        turn = model.generate(
            system=_CHOOSE_SYSTEM,
            contents=[user_content(prompt)],
            tools=[],
        )
        return _paths_from_reply(str(getattr(turn, "text", "") or ""), set(by_path))

    picked = once()
    if not picked:
        return {"ok": False, "files": [], "deny": "no note teaches this page"}
    kept = _rows_meet(picked, by_path, fact, idea=brief, facts=sentences)
    if kept:
        return {"ok": True, "files": kept, "deny": ""}
    again = once(picked)
    if not again:
        return {"ok": False, "files": [], "deny": "no note teaches this page"}
    kept = _rows_meet(again, by_path, fact, idea=brief, facts=sentences)
    if not kept:
        return {"ok": False, "files": [], "deny": "no sentence in the notes"}
    return {"ok": True, "files": kept, "deny": ""}


def short_excerpt(text: str, *, limit: int = _SENTENCE_CAP) -> str:
    """A short excerpt already present in ``text``. Nothing is invented."""
    return " ".join(_file_sentences(text, limit=limit))


def local_markdown_files(fact: str, question: str, *, limit: int = _LOCAL_CAP) -> list[str]:
    """Up to three markdown files whose title or first heading uses the fact's words.

    The button does not call this. A fact that already has a stored file list
    does not call this either. A file is not chosen from a keyword list, and
    nothing here is a web search. Fewer than two matches are returned as they
    are. No match returns an empty list.
    """
    words = _content_words(fact, question)
    if not words:
        return []
    root = blog_packet.repo_root().resolve()
    scored: list[tuple[int, str]] = []
    if not root.is_dir():
        return []
    for path in root.rglob("*.md"):
        if not path.is_file():
            continue
        try:
            rel_path = path.resolve().relative_to(root)
        except ValueError:
            continue
        parts = rel_path.parts
        if any(part.startswith(".") or part in _SKIP_DIR for part in parts):
            continue
        surface = _heading_surface(path)
        score = sum(1 for word in words if _word_in(surface, word))
        if score:
            scored.append((score, rel_path.as_posix()))
    scored.sort(key=lambda row: (-row[0], row[1]))
    return [rel for _score, rel in scored[:limit]]


def _markdown_links(text: str) -> list[str]:
    found: list[str] = []
    for url in _LINK.findall(text or ""):
        if url not in found:
            found.append(url)
    return found


_TICK_URL = re.compile(r"`(https?://[^`\s]+)`")
_BARE_HTTP = re.compile(r"https?://[^\s<>\[\]()\"'`]+")


def _clean_citation(url: str) -> str:
    return str(url or "").strip().rstrip(".,;:!?")


def citation_urls(text: str) -> list[str]:
    """Markdown links, backtick URLs, and bare https URLs already in ``text``.

    A backtick URL and a bare https URL are citations. Nothing is invented.
    """
    found: list[str] = []

    def add(url: str) -> None:
        cleaned = _clean_citation(url)
        if cleaned.startswith("http") and cleaned not in found:
            found.append(cleaned)

    for url in _markdown_links(text):
        add(url)
    for url in _TICK_URL.findall(text or ""):
        add(url)
    for match in _BARE_HTTP.finditer(text or ""):
        start = match.start()
        if start > 0 and text[start - 1] in "`(":
            continue
        add(match.group(0))
    return found


def _host_allowed(url: str, paths: DataPaths) -> bool:
    from ada.web.allowlist import allowlist_hosts

    host = (urlparse(url).hostname or "").lower().rstrip(".")
    return bool(host) and host in allowlist_hosts(paths)


def fetchable_markdown_urls(text: str, *, paths: DataPaths) -> tuple[list[str], str]:
    """Allowlisted markdown links only. A search URL is refused.

    A backtick URL and a bare https URL are not requested. This does not
    call add_host and does not edit the allowlist.
    """
    links = _markdown_links(text)
    if any(is_search_url(url) for url in links):
        return [], "refusing a search query"
    found: list[str] = []
    for url in links:
        if _host_allowed(url, paths) and url not in found:
            found.append(url)
    return found, ""


def section_text(item: dict[str, Any]) -> str:
    """Sections stored on the plan item. An empty string when none were stored."""
    parts: list[str] = []
    for row in item.get("notes") or []:
        if not isinstance(row, dict):
            continue
        section = str(row.get("section") or "").strip()
        if section and section not in parts:
            parts.append(section)
    return "\n\n".join(parts)


def _local_paths(item: dict[str, Any]) -> list[str]:
    raw = item.get("local_files")
    if isinstance(raw, list) and any(str(path).strip() for path in raw):
        return [str(path).strip() for path in raw if str(path).strip()][:_LOCAL_CAP]
    source = str(item.get("source") or "").strip()
    return [source] if source else []


def gate_texts(item: dict[str, Any]) -> dict[str, str]:
    """Bodies the gate may check: selected local files, plus papers that were fetched."""
    texts = _fetch_bodies(item)
    for rel in _local_paths(item):
        if rel in texts or rel.startswith("http://") or rel.startswith("https://"):
            continue
        texts[rel] = source_file(rel).read_text(encoding="utf-8")
    return texts


def _spans_from_text(text: str, source: str) -> list[dict[str, str]]:
    facts: list[dict[str, str]] = []
    for line in text.splitlines():
        span = line.strip()
        if span and span in text:
            facts.append({"span": span, "source": source})
    return facts


def _fetch_bodies(item: dict[str, Any]) -> dict[str, str]:
    bodies: dict[str, str] = {}
    for row in item.get("fetches") or []:
        if isinstance(row, dict) and row.get("url") and row.get("body"):
            bodies[str(row["url"])] = str(row["body"])
    return bodies


def _kept_fetches(
    urls: list[str],
    *,
    http_get: Any,
    paths: DataPaths,
) -> list[dict[str, Any]]:
    """Fetch each URL once. A confirm-host response and a failed response store no span.

    Links inside a fetched page are not followed.
    """
    fetches: list[dict[str, Any]] = []
    for url in urls:
        observed = web_fetch(
            url,
            confirm_host=False,
            http_get=http_get,
            paths=paths,
        )
        if observed.get("needs_confirm") or not observed.get("ok"):
            continue
        excerpts = observed.get("excerpts") or []
        body = "\n".join(str(part) for part in excerpts if str(part).strip())
        if not body:
            continue
        excerpt = short_excerpt(body)
        fetches.append(
            {
                "url": url,
                "body": body,
                "excerpt": excerpt,
                "spans": _spans_from_text(body, url),
            }
        )
    return fetches


def _finish_fetches(
    campaign_id: str,
    plan: dict[str, Any],
    item: dict[str, Any],
    fetches: list[dict[str, Any]],
    *,
    paths: DataPaths,
    local_files: list[str] | None = None,
) -> dict[str, Any]:
    if local_files is not None:
        item["local_files"] = list(local_files)
    item["fetches"] = fetches
    item["excerpts"] = [
        {"url": str(row["url"]), "excerpt": str(row.get("excerpt") or "")}
        for row in fetches
        if row.get("url") and str(row.get("excerpt") or "").strip()
    ]
    save_plan(plan, paths=paths)
    return finish_stage(
        campaign_id,
        "external-fetch",
        paths=paths,
        outcome="ok",
        receipt_paths=[str(row["url"]) for row in fetches],
    )


def wake_external_fetch(
    campaign_id: str,
    *,
    http_get: Any = None,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    """Fetch papers named in the local notes for this fact.

    When the item has a fact, use the file list stored at plan when it has
    one, still capped at three, and do not choose a different three. With no
    stored list, choose at most three markdown files about that fact, then
    fetch the https links those files already write. A host that needs
    confirm is skipped. A search URL is refused. A link inside a fetched page
    is not followed. Each fetched body leaves a short excerpt, already in
    that body, with its URL on the plan item. An item with no fact still
    fetches only the URLs that item already names.
    """
    p = paths or require_ada_data()
    blocked = _require_chain(campaign_id, "external-fetch", p)
    if blocked:
        return blocked
    plan = load_plan(campaign_id, paths=p)
    item = current_item(plan) if plan else None
    if plan is None or item is None:
        finish_stage(campaign_id, "external-fetch", paths=p, outcome="denied", advance=False)
        return _deny("plan queue is empty")
    fact = str(item.get("fact") or "").strip()
    if fact:
        planned = item.get("local_files")
        if isinstance(planned, list) and any(str(path).strip() for path in planned):
            files = [str(path).strip() for path in planned if str(path).strip()][:_LOCAL_CAP]
        else:
            files = local_markdown_files(fact, str(item.get("question") or ""))
        if not files:
            finish_stage(campaign_id, "external-fetch", paths=p, outcome="denied", advance=False)
            return _deny("no local file matches the fact")
        stored_section = section_text(item)
        if stored_section:
            urls, reason = fetchable_markdown_urls(stored_section, paths=p)
            if reason:
                finish_stage(campaign_id, "external-fetch", paths=p, outcome="denied", advance=False)
                return _deny(reason)
            fetches = _kept_fetches(urls, http_get=http_get, paths=p)
            return _finish_fetches(
                campaign_id,
                plan,
                item,
                fetches,
                paths=p,
                local_files=files,
            )
        urls: list[str] = []
        try:
            for rel in files:
                for url in _markdown_links(source_file(rel).read_text(encoding="utf-8")):
                    if url not in urls:
                        urls.append(url)
        except (ValueError, FileNotFoundError, OSError) as exc:
            finish_stage(campaign_id, "external-fetch", paths=p, outcome="denied", advance=False)
            return _deny(f"source file is missing: {exc}")
        if any(is_search_url(url) for url in urls):
            finish_stage(campaign_id, "external-fetch", paths=p, outcome="denied", advance=False)
            return _deny("refusing a search query")
        allowed, reason = fetchable_markdown_urls("\n".join(f"[link]({url})" for url in urls), paths=p)
        if reason:
            finish_stage(campaign_id, "external-fetch", paths=p, outcome="denied", advance=False)
            return _deny(reason)
        fetches = _kept_fetches(allowed, http_get=http_get, paths=p)
        return _finish_fetches(
            campaign_id,
            plan,
            item,
            fetches,
            paths=p,
            local_files=files,
        )
    try:
        file_text = source_file(str(item.get("source") or "")).read_text(encoding="utf-8")
    except (ValueError, FileNotFoundError, OSError) as exc:
        finish_stage(campaign_id, "external-fetch", paths=p, outcome="denied", advance=False)
        return _deny(f"source file is missing: {exc}")
    urls = named_urls(item, file_text)
    if not urls:
        item["fetches"] = []
        save_plan(plan, paths=p)
        return finish_stage(
            campaign_id,
            "external-fetch",
            paths=p,
            outcome="skip",
        )
    if any(is_search_url(url) for url in urls):
        finish_stage(campaign_id, "external-fetch", paths=p, outcome="denied", advance=False)
        return _deny("refusing a search query")
    return _finish_fetches(
        campaign_id,
        plan,
        item,
        _kept_fetches(urls, http_get=http_get, paths=p),
        paths=p,
    )


def wake_gather(
    campaign_id: str,
    *,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    """Store spans from the selected notes and the papers that were fetched.

    Adds no other fact. When the item has no selected files, the one source
    path is the note.
    """
    p = paths or require_ada_data()
    blocked = _require_chain(campaign_id, "gather", p)
    if blocked:
        return blocked
    plan = load_plan(campaign_id, paths=p)
    item = current_item(plan) if plan else None
    config = read_portfolio_chain(paths=p)
    if plan is None or item is None or not config.get("ok"):
        finish_stage(campaign_id, "gather", paths=p, outcome="denied", advance=False)
        return _deny("plan queue is empty")
    cfg = config["config"]
    source = str(item.get("source") or "").strip()
    try:
        texts = gate_texts(item)
    except (ValueError, FileNotFoundError, OSError) as exc:
        finish_stage(campaign_id, "gather", paths=p, outcome="denied", advance=False)
        return _deny(f"source file is missing: {exc}")
    notes = _local_paths(item)
    if not notes:
        finish_stage(campaign_id, "gather", paths=p, outcome="denied", advance=False)
        return _deny("source file is missing: source must name one file")
    facts: list[dict[str, str]] = []
    for rel in notes:
        facts.extend(_spans_from_text(texts.get(rel, ""), rel))
    for row in item.get("fetches") or []:
        if isinstance(row, dict):
            facts.extend(row.get("spans") or [])
    page = {
        "site": cfg["site"],
        "audience": cfg["audience"],
        "source": source,
        "question": str(item.get("question") or ""),
        "fill": str(item.get("fill") or ""),
    }
    if isinstance(item.get("call_to_action"), dict):
        page["call_to_action"] = item["call_to_action"]
    gated = gate_packet(
        page=page,
        facts=facts,
        file_text=texts.get(source, ""),
        fetch_bodies=texts,
    )
    if not gated.get("ok"):
        finish_stage(campaign_id, "gather", paths=p, outcome="denied", advance=False)
        return gated
    page["packet"] = list(gated["packet"])
    write_page(campaign_id, page, paths=p)
    return finish_stage(campaign_id, "gather", paths=p, outcome="ok")


def wake_gate(
    campaign_id: str,
    *,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    """Pass the same packet, or refuse it. Do not drop, rewrite, or add a fact."""
    p = paths or require_ada_data()
    blocked = _require_chain(campaign_id, "gate", p)
    if blocked:
        return blocked
    plan = load_plan(campaign_id, paths=p)
    item = current_item(plan) if plan else None
    page = read_page(campaign_id, paths=p)
    if plan is None or item is None or page is None:
        finish_stage(campaign_id, "gate", paths=p, outcome="denied", advance=False)
        return _deny("campaign page is missing")
    packet = page.get("packet")
    if not isinstance(packet, list):
        finish_stage(campaign_id, "gate", paths=p, outcome="denied", advance=False)
        return _deny("gather has not left a packet")
    source = str(page.get("source") or "").strip()
    try:
        texts = gate_texts(item)
    except (ValueError, FileNotFoundError, OSError) as exc:
        finish_stage(campaign_id, "gate", paths=p, outcome="denied", advance=False)
        return _deny(f"source file is missing: {exc}")
    gated = gate_packet(
        page=page,
        facts=list(packet),
        file_text=texts.get(source, ""),
        fetch_bodies=texts,
    )
    if not gated.get("ok"):
        finish_stage(campaign_id, "gate", paths=p, outcome="denied", advance=False)
        return gated
    if list(gated["packet"]) != list(packet):
        finish_stage(campaign_id, "gate", paths=p, outcome="denied", advance=False)
        return _deny("gate rewrites a fact")
    stored = dict(page)
    stored["packet"] = list(packet)
    write_page(campaign_id, stored, paths=p)
    return finish_stage(campaign_id, "gate", paths=p, outcome="ok")
