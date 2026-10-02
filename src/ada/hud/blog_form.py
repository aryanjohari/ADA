"""Run one blog step from the HUD form. One click, one step."""

from __future__ import annotations

from typing import Any

from ada.memory.blog_draft import draft_page
from ada.memory.blog_packet import gather_packet
from ada.memory.blog_status import describe_blog
from ada.memory.campaign_page import upsert_campaign_page
from ada.tools.blog_tools import run_blog_checkout_delete, run_blog_checkout_write


def _line(step: str, result: dict[str, Any]) -> str:
    if result.get("needs_confirm"):
        return str(result.get("reason") or "Needs confirm.")
    if result.get("ok") is False:
        return str(
            result.get("denied_reason") or result.get("error") or "Refused."
        )
    if step == "store":
        return "Stored the row."
    if step == "gather":
        count = len(result.get("packet") or [])
        return f"Gathered {count} spans from the source file."
    if step == "draft":
        return f"Drafted {result.get('path') or result.get('slug') or 'the file'}."
    if step == "copy":
        return f"Copied the file to {result.get('path')}."
    if step == "delete":
        return "Deleted the checkout file and cleared the slug."
    return "Done."


def run_blog_step(
    step: str,
    *,
    campaign_id: str | None = None,
    site: str | None = None,
    audience: str | None = None,
    source: str | None = None,
    question: str | None = None,
    fill: str | None = None,
    cta_label: str | None = None,
    cta_url: str | None = None,
    confirmed: bool = False,
) -> dict[str, Any]:
    """Advance the one step that is current. A later step is refused."""
    before = describe_blog(campaign_id)
    current = str(before.get("current") or "store")
    cid = before.get("campaign_id")
    if step != current:
        label = next(
            (item["label"] for item in before.get("steps") or [] if item["id"] == current),
            current,
        )
        return {
            "ok": False,
            "outcome": "denied",
            "denied_reason": f"{label} is the step that can run now.",
            "error": f"{label} is the step that can run now.",
            "result_line": f"{label} is the step that can run now.",
            "status": before,
        }

    if step == "store":
        result = upsert_campaign_page(
            site=site,
            audience=audience,
            source=source,
            question=question,
            fill=fill,
            cta_label=cta_label,
            cta_url=cta_url,
        )
        cid = result.get("id") or cid
    elif step == "gather":
        result = gather_packet(campaign_id=str(cid))
    elif step == "draft":
        result = draft_page(campaign_id=str(cid), confirmed=confirmed)
    elif step == "copy":
        result = run_blog_checkout_write(
            {"campaign_id": cid, "confirmed": confirmed}
        )
    elif step == "delete":
        result = run_blog_checkout_delete(
            {"campaign_id": cid, "confirmed": confirmed}
        )
    else:
        result = {
            "ok": False,
            "outcome": "denied",
            "denied_reason": "unknown step",
            "error": "unknown step",
        }

    status = describe_blog(str(cid) if cid else None)
    result = dict(result)
    result["result_line"] = _line(step, result)
    result["status"] = status
    return result
