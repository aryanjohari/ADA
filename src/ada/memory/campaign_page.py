"""Campaign page sidecar. Page fields stay off upsert_loop."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

from ada.io.atomic import atomic_write_text
from ada.io.paths import DataPaths, require_ada_data
from ada.memory.blog_slug import SlugError, blog_slug
from ada.memory.open_loops import upsert_loop

SITE = "github.com/aryanjohari/aryan-portfolio"
FILLS = frozenset({"build-log", "lesson", "researched"})
SHELL_TEXT = "campaign page"
_SENTENCE_MARK = re.compile(r"[.!?]")


def next_wake_iso() -> str:
    when = datetime.now(timezone.utc) + timedelta(hours=24)
    return when.strftime("%Y-%m-%dT%H:%M:%SZ")


def _fresh_stages() -> list[dict[str, str]]:
    return [
        {"id": "gather", "state": "pending"},
        {"id": "gate", "state": "pending"},
        {"id": "draft", "state": "pending"},
        {"id": "deploy", "state": "pending"},
    ]


def _deny(reason: str) -> dict[str, Any]:
    return {
        "ok": False,
        "outcome": "denied",
        "denied_reason": reason,
        "error": reason,
    }


def _safe_id(campaign_id: str) -> str:
    cid = (campaign_id or "").strip()
    if (
        not cid
        or cid in {".", ".."}
        or "/" in cid
        or "\\" in cid
        or cid.startswith(".")
    ):
        raise ValueError("invalid campaign id")
    return cid


def page_path(campaign_id: str, paths: DataPaths) -> Path:
    cid = _safe_id(campaign_id)
    root = paths.campaign_pages.resolve()
    target = (root / f"{cid}.yaml").resolve()
    target.relative_to(root)
    return target


def read_page(
    campaign_id: str,
    *,
    paths: DataPaths | None = None,
) -> dict[str, Any] | None:
    p = paths or require_ada_data()
    try:
        path = page_path(campaign_id, p)
    except ValueError:
        return None
    if not path.is_file():
        return None
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return None
    return raw


def write_page(
    campaign_id: str,
    page: dict[str, Any],
    *,
    paths: DataPaths | None = None,
) -> None:
    p = paths or require_ada_data()
    path = page_path(campaign_id, p)
    text = yaml.safe_dump(
        page,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        default_style='"',
    )
    atomic_write_text(path, text)


def one_sentence(text: str) -> bool:
    body = text.strip()
    if not body:
        return False
    marks = _SENTENCE_MARK.findall(body)
    if len(marks) > 1:
        return False
    if len(marks) == 1 and body[-1] not in ".!?":
        return False
    return True


def _normalize_cta(
    label: str | None,
    url: str | None,
) -> tuple[dict[str, str] | None, str | None]:
    lab = (label or "").strip()
    href = (url or "").strip()
    if not lab and not href:
        return None, None
    if not lab or not href:
        return None, "call to action needs both a label and a URL"
    return {"label": lab, "url": href}, None


def upsert_campaign_page(
    *,
    site: str | None,
    audience: str | None,
    source: str | None,
    question: str | None,
    fill: str | None,
    cta_label: str | None = None,
    cta_url: str | None = None,
    campaign_id: str | None = None,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    """Store page fields on the sidecar and a campaign shell on open_loops.

    The shell receives status, stages, and next_wake_at only.
    """
    p = paths or require_ada_data()
    site_v = (site or "").strip()
    audience_v = (audience or "").strip()
    source_v = (source or "").strip()
    question_v = (question or "").strip()
    fill_v = (fill or "").strip()
    if not site_v or not audience_v or not source_v or not question_v or not fill_v:
        return _deny("site, audience, source, question, and fill are required")
    if site_v != SITE:
        return _deny(f"site must be {SITE}")
    if not one_sentence(audience_v):
        return _deny("audience must be one sentence")
    if fill_v not in FILLS:
        return _deny("fill must be build-log, lesson, or researched")
    cta, cta_err = _normalize_cta(cta_label, cta_url)
    if cta_err:
        return _deny(cta_err)
    try:
        blog_slug(question_v)
    except SlugError as exc:
        return _deny(str(exc))

    created = upsert_loop(
        text=SHELL_TEXT,
        title=SHELL_TEXT,
        loop_id=(campaign_id or "").strip() or None,
        kind="campaign",
        status="active",
        stages=_fresh_stages(),
        current_stage="gather",
        next_wake_at=next_wake_iso(),
        paths=p,
    )
    if not created.get("ok"):
        return created
    loop = created.get("loop") or {}
    cid = str(loop.get("id") or "")
    page: dict[str, Any] = {
        "site": site_v,
        "audience": audience_v,
        "source": source_v,
        "question": question_v,
        "fill": fill_v,
    }
    if cta is not None:
        page["call_to_action"] = cta
    write_page(cid, page, paths=p)
    return {"ok": True, "outcome": "ok", "id": cid, "page": page}
