"""Keyword-led publish: provision a subject entity for ``publish_keyword_v1`` (no matrix entity)."""

from __future__ import annotations

from typing import Any

from ada.query_engine import QueryEngine
from ada.workflow.templates import validate_target_keyword_cluster


async def provision_keyword_stub_entity(
    qe: QueryEngine, params: dict[str, Any]
) -> int:
    """
    Create or merge a ``keyword_landing`` entity named after the target cluster.
    Payload records workflow and publisher/brand context for operators and DRAFT.
    """
    kw = validate_target_keyword_cluster(params.get("target_keyword_cluster"))
    payload: dict[str, Any] = {
        "workflow": "publish_keyword_v1",
        "project_id": str(params.get("project_id") or "").strip(),
        "campaign_id": str(params.get("campaign_id") or "").strip(),
        "niche": str(params.get("niche") or "").strip(),
        "keyword_stub": True,
    }
    src = params.get("keyword_source")
    if isinstance(src, dict) and src:
        payload["keyword_source"] = src
    for k in ("brand_name", "vertical"):
        v = params.get(k)
        if v is not None and str(v).strip():
            payload[k] = str(v).strip()
    row = await qe.upsert_entity(
        type="keyword_landing",
        name=kw,
        payload_json=payload,
    )
    return int(row["entity_id"])
