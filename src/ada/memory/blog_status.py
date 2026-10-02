"""Which blog step can run next. This module only reads."""

from __future__ import annotations

from typing import Any

from ada.io.paths import DataPaths, require_ada_data
from ada.memory.blog_slug import SlugError
from ada.memory.campaign_page import read_page
from ada.memory.open_loops import get_loop, is_draft_artifact_receipt
from ada.tools.blog_tools import CheckoutError, blog_dest, resolve_portfolio_checkout

STEP_ORDER = ("store", "gather", "draft", "copy", "delete")

STEP_TEXT = {
    "store": "Saves site, audience, source, question, and fill on the sidecar.",
    "gather": "Reads the one source file on the row. Each fact is a line from that file.",
    "draft": "Writes artifacts/{date}/{slug}.md, then waits.",
    "copy": "Confirm copies that file into the portfolio checkout.",
    "delete": "Confirm removes the checkout file and clears the slug.",
}

STEP_LABEL = {
    "store": "Store",
    "gather": "Gather",
    "draft": "Draft",
    "copy": "Copy",
    "delete": "Delete",
}


def latest_campaign_id(paths: DataPaths | None = None) -> str | None:
    p = paths or require_ada_data()
    root = p.campaign_pages
    if not root.is_dir():
        return None
    files = [path for path in root.glob("*.yaml") if path.is_file()]
    if not files:
        return None
    files.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return files[0].stem


def _checkout_probe(slug: str) -> dict[str, Any]:
    try:
        checkout = resolve_portfolio_checkout()
    except CheckoutError as exc:
        return {"ok": False, "file_exists": False, "detail": str(exc)}
    if not slug:
        return {
            "ok": True,
            "file_exists": False,
            "detail": "Checkout is ready. No slug is stored yet.",
        }
    try:
        dest = blog_dest(checkout, slug)
    except SlugError as exc:
        return {"ok": False, "file_exists": False, "detail": str(exc)}
    if dest.is_file():
        return {
            "ok": True,
            "file_exists": True,
            "detail": f"Checkout file is {dest.name}.",
        }
    return {
        "ok": True,
        "file_exists": False,
        "detail": "Checkout file is absent.",
    }


def _current_step(
    page: dict[str, Any] | None,
    loop: dict[str, Any] | None,
    *,
    file_exists: bool,
) -> str:
    if page is None:
        return "store"
    packet = page.get("packet")
    if not isinstance(packet, list) or not packet:
        return "gather"
    slug = str(page.get("slug") or "").strip()
    status = str((loop or {}).get("status") or "")
    receipt = str((loop or {}).get("last_receipt") or "")
    drafted = (
        bool(slug)
        and status == "waiting_on_aryan"
        and is_draft_artifact_receipt(receipt)
    )
    if not drafted:
        return "draft"
    if file_exists:
        return "delete"
    return "copy"


def describe_blog(
    campaign_id: str | None = None,
    *,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    p = paths or require_ada_data()
    cid = (campaign_id or "").strip() or latest_campaign_id(p)
    page = read_page(cid, paths=p) if cid else None
    if page is None:
        cid = None
    loop = get_loop(cid, paths=p) if cid else None
    slug = str((page or {}).get("slug") or "").strip()
    checkout = _checkout_probe(slug)
    current = _current_step(page, loop, file_exists=bool(checkout.get("file_exists")))
    index = STEP_ORDER.index(current)
    steps = []
    for i, step_id in enumerate(STEP_ORDER):
        if i < index:
            state = "done"
        elif i == index:
            state = "current"
        else:
            state = "later"
        detail = STEP_TEXT[step_id]
        if step_id == current and step_id in {"copy", "delete"}:
            detail = f"{detail} {checkout.get('detail') or ''}".strip()
        steps.append(
            {
                "id": step_id,
                "label": STEP_LABEL[step_id],
                "state": state,
                "detail": detail,
            }
        )
    packet = (page or {}).get("packet")
    packet_count = len(packet) if isinstance(packet, list) else 0
    return {
        "ok": True,
        "campaign_id": cid,
        "current": current,
        "steps": steps,
        "loop_status": (loop or {}).get("status"),
        "slug": slug,
        "packet_count": packet_count,
        "checkout": checkout,
        "page": {
            "site": (page or {}).get("site") or "",
            "audience": (page or {}).get("audience") or "",
            "source": (page or {}).get("source") or "",
            "question": (page or {}).get("question") or "",
            "fill": (page or {}).get("fill") or "",
            "cta_label": ((page or {}).get("call_to_action") or {}).get("label") or "",
            "cta_url": ((page or {}).get("call_to_action") or {}).get("url") or "",
        }
        if page
        else None,
    }
