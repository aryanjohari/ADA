"""WORLDVIEW digests — interpretive; must cite FACTS/receipts (M04)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ada.body.vitals import utc_now_iso
from ada.io.atomic import atomic_write_text
from ada.io.paths import BodyFault, DataPaths, ada_data_mounted, require_ada_data
from ada.memory.facts import SACRED_IDENTITY_KEYS


class WorldviewError(ValueError):
    """Cite validation or write policy failure."""


def _require(paths: DataPaths | None) -> DataPaths:
    p = paths or require_ada_data()
    if not ada_data_mounted(p.root):
        raise BodyFault(
            f"ada-data not mounted or missing at {p.root}; refusing durable writes"
        )
    return p


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def validate_cites(
    cites: list[Any] | None,
    *,
    paths: DataPaths | None = None,
) -> list[str]:
    if not cites:
        raise WorldviewError("WORLDVIEW write requires non-empty cites[]")
    out: list[str] = []
    for c in cites:
        s = str(c).strip()
        if not s:
            continue
        # cite:c_… must resolve to an on-disk cite (M07 honesty).
        if s.startswith("cite:"):
            try:
                from ada.web.cites import cite_exists, normalize_cite_id

                cid = normalize_cite_id(s)
                if not cite_exists(cid, paths=paths):
                    raise WorldviewError(f"cite not found on disk: {cid}")
                s = f"cite:{cid}"
            except WorldviewError:
                raise
            except ValueError as exc:
                raise WorldviewError(str(exc)) from exc
        out.append(s)
    if not out:
        raise WorldviewError("WORLDVIEW write requires non-empty cites[]")
    return out


def write_digest(
    body: str,
    *,
    cites: list[Any] | None,
    title: str | None = None,
    dream: bool = False,
    date: str | None = None,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    """Write a dated WORLDVIEW markdown with cite header. Never mutates FACTS."""
    p = _require(paths)
    p.ensure_memory_dirs()
    if body and len(body) > 50_000:
        raise WorldviewError(
            "WORLDVIEW body too large (>50k chars); cite excerpts via cite: ids, not HTML dumps"
        )
    if body and ("<html" in body.lower() or "<!doctype html" in body.lower()):
        raise WorldviewError(
            "WORLDVIEW must not embed raw HTML; use web_fetch cites instead"
        )
    cite_list = validate_cites(cites, paths=p)
    day = date or _today()
    folder = p.dreams if dream else p.worldview
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{day}.md"
    # Append if same-day digest exists (crash-safe full rewrite of combined text).
    header_title = title or ("Dream digest" if dream else "WORLDVIEW digest")
    block = (
        f"# {header_title} ({day})\n\n"
        f"- written_at: {utc_now_iso()}\n"
        f"- truth_class: interpretive\n"
        f"- cites: {', '.join(cite_list)}\n\n"
        f"{body.strip()}\n"
    )
    if path.is_file():
        existing = path.read_text(encoding="utf-8")
        text = existing.rstrip() + "\n\n---\n\n" + block
    else:
        text = block
    # Guard: refuse any attempt to smuggle FACT mutation instructions as success.
    lower = body.lower()
    for sacred in SACRED_IDENTITY_KEYS:
        if f"overwrite {sacred}" in lower or f"set born_at" in lower:
            raise WorldviewError(
                f"WORLDVIEW must not instruct FACT overwrite of sacred key '{sacred}'"
            )
    atomic_write_text(path, text)
    # Optional index pointer.
    index = p.worldview / "index.md"
    pointer = f"- [{day}]({path.name if not dream else f'../dreams/{day}.md'}) — {header_title}\n"
    if index.is_file():
        idx = index.read_text(encoding="utf-8")
        if day not in idx:
            atomic_write_text(index, idx.rstrip() + "\n" + pointer)
    else:
        atomic_write_text(
            index,
            "# WORLDVIEW index\n\nInterpretive digests (not metal).\n\n" + pointer,
        )
    return {
        "ok": True,
        "path": str(path),
        "date": day,
        "cites": cite_list,
        "dream": dream,
        "ts": utc_now_iso(),
    }


def search_worldview(
    query: str,
    *,
    paths: DataPaths | None = None,
    max_hits: int = 20,
) -> dict[str, Any]:
    p = paths or require_ada_data()
    q = (query or "").strip().lower()
    hits: list[dict[str, Any]] = []
    if not q:
        return {"query": query, "hits": hits, "count": 0}
    roots = [p.worldview, p.dreams]
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.glob("*.md")):
            if len(hits) >= max_hits:
                break
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            if q not in text.lower():
                continue
            snippets = [ln.strip() for ln in text.splitlines() if q in ln.lower()][:3]
            hits.append(
                {
                    "path": str(path),
                    "rel": str(path.relative_to(p.memory)),
                    "snippets": snippets,
                }
            )
    return {"query": query, "hits": hits[:max_hits], "count": len(hits[:max_hits])}


def latest_digest_summary(
    *,
    paths: DataPaths | None = None,
    max_chars: int = 1600,
) -> str | None:
    """Return labeled summary of newest worldview/dreams markdown, or None."""
    p = paths or require_ada_data()
    candidates: list[Path] = []
    for root in (p.dreams, p.worldview):
        if root.is_dir():
            candidates.extend(root.glob("*.md"))
    candidates = [c for c in candidates if c.name != "index.md"]
    if not candidates:
        return None
    newest = max(candidates, key=lambda x: x.stat().st_mtime)
    try:
        text = newest.read_text(encoding="utf-8")
    except OSError:
        return None
    # Prefer first ~N chars after header.
    body = text.strip()
    if len(body) > max_chars:
        body = body[: max_chars - 20] + "\n…(truncated)"
    rel = str(newest.relative_to(p.memory)) if p.memory in newest.parents else newest.name
    return (
        f"WORLDVIEW (interpretive, cite in file — NOT metal):\n"
        f"source: memory/{rel}\n\n{body}"
    )
