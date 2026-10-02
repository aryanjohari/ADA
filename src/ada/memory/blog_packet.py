"""Gather one source file into a packet of verbatim spans."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ada.io.paths import DataPaths, require_ada_data
from ada.memory.campaign_page import FILLS, next_wake_iso, read_page, write_page
from ada.memory.open_loops import upsert_loop

_REQUIRED = ("site", "audience", "source", "question", "fill")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _deny(reason: str) -> dict[str, Any]:
    return {
        "ok": False,
        "outcome": "denied",
        "denied_reason": reason,
        "error": reason,
    }


def source_file(source: str) -> Path:
    """Resolve the row's source to one file under the repo. No second path."""
    raw = (source or "").strip()
    if not raw or raw.startswith("/") or raw.startswith("\\"):
        raise ValueError("source must name one file")
    parts = Path(raw).parts
    if ".." in parts or not parts:
        raise ValueError("source must name one file")
    path = (repo_root() / raw).resolve()
    path.relative_to(repo_root().resolve())
    if not path.is_file():
        raise FileNotFoundError(raw)
    return path


def gate_packet(
    *,
    page: dict[str, Any],
    facts: list[dict[str, Any]],
    file_text: str,
    fetch_bodies: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Pass the packet unchanged, or refuse it.

    A file fact's span must sit in that file. A URL fact's span must sit in
    the stored body for that URL, and the URL must already be in
    ``fetch_bodies``. Any other source fails. A researched packet that is
    empty still fails. This function does not drop, rewrite, or add a fact
    that passed those checks.
    """
    bodies = fetch_bodies or {}
    for key in _REQUIRED:
        if not str(page.get(key) or "").strip():
            return _deny(f"missing field {key}")
    fill = str(page.get("fill") or "").strip()
    if fill not in FILLS:
        return _deny("fill must be build-log, lesson, or researched")
    source = str(page.get("source") or "").strip()
    if fill == "researched" and not facts:
        return _deny("researched packet is empty")
    kept: list[dict[str, str]] = []
    for fact in facts:
        if not isinstance(fact, dict):
            return _deny("missing field span")
        span = fact.get("span")
        fact_source = str(fact.get("source") or "").strip()
        if not isinstance(span, str) or not span:
            return _deny("missing field span")
        if not fact_source:
            return _deny("missing field source")
        if fact_source == source:
            if span not in file_text:
                return _deny("span is not in the source file")
        elif fact_source in bodies:
            if span not in bodies[fact_source]:
                return _deny("span is not in the fetched body")
        else:
            return _deny("fact source is not the row source")
        kept.append({"span": span, "source": fact_source})
    return {"ok": True, "outcome": "ok", "packet": kept}


def _spans_from_file(text: str, source: str) -> list[dict[str, str]]:
    facts: list[dict[str, str]] = []
    for line in text.splitlines():
        span = line.strip()
        if not span:
            continue
        if span not in text:
            continue
        facts.append({"span": span, "source": source})
    return facts


def gather_packet(
    *,
    campaign_id: str,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    """Read the source path on the row and no other file. Store the gated packet."""
    p = paths or require_ada_data()
    page = read_page(campaign_id, paths=p)
    if page is None:
        return _deny("campaign page is missing")
    for key in _REQUIRED:
        if not str(page.get(key) or "").strip():
            return _deny(f"missing field {key}")
    source = str(page["source"]).strip()
    try:
        path = source_file(source)
    except (ValueError, FileNotFoundError, OSError) as exc:
        return _deny(f"source file is missing: {exc}")
    file_text = path.read_text(encoding="utf-8")
    facts = _spans_from_file(file_text, source)
    gated = gate_packet(page=page, facts=facts, file_text=file_text)
    if not gated.get("ok"):
        return gated
    stored = dict(page)
    stored["packet"] = gated["packet"]
    write_page(campaign_id, stored, paths=p)
    upsert_loop(
        loop_id=campaign_id,
        stages=[
            {"id": "gather", "state": "done"},
            {"id": "gate", "state": "done"},
            {"id": "draft", "state": "active"},
            {"id": "deploy", "state": "pending"},
        ],
        current_stage="draft",
        next_wake_at=next_wake_iso(),
        paths=p,
    )
    return {
        "ok": True,
        "outcome": "ok",
        "id": campaign_id,
        "packet": gated["packet"],
        "source": source,
    }
