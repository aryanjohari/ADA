"""ENRICH step: deterministic connectors that write knowledge + graph edges (with source_url)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable
import hashlib
import logging

import httpx

from ada.config import Settings
from ada.query_engine import QueryEngine

log = logging.getLogger("ada.publish.enrich")

ENRICH_SOURCE_LABEL = "ada-publisher-enrich"


@dataclass
class EnrichContext:
    qe: QueryEngine
    settings: Settings
    entity_id: int


@dataclass
class EnrichResult:
    knowledge_item_ids: list[int] = field(default_factory=list)
    graph_edge_ids: list[int] = field(default_factory=list)
    last_enriched_at: str = ""


@runtime_checkable
class EnrichConnector(Protocol):
    async def __call__(self, ctx: EnrichContext) -> EnrichResult: ...


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _ref_payload_from_entity(entity: dict[str, Any]) -> dict[str, Any]:
    """`enrich_reference` in entity.payload_json; see tests for shape."""
    p = entity.get("payload_json") or {}
    if not isinstance(p, dict):
        return {}
    r = p.get("enrich_reference")
    if isinstance(r, dict):
        return r
    return {}


class ReferenceJsonEnrichConnector:
    """
    CI-friendly connector: uses `httpx` GET for `enrich_url` in payload, or
    in-process JSON from `enrich_reference` (category_code, source_url, excerpt, ...).
    """

    _TIMEOUT = 20.0

    async def __call__(self, ctx: EnrichContext) -> EnrichResult:
        ent = await ctx.qe.get_entity_by_id(ctx.entity_id)
        if ent is None:
            raise ValueError(f"enrich: missing entity {ctx.entity_id}")
        ref = _ref_payload_from_entity(ent)
        ex = str(ref.get("excerpt") or "Enrichment stub excerpt for publisher tests.").strip()
        su = str(ref.get("source_url") or "https://example.com/fact/1").strip()
        code = str(ref.get("category_code") or "policy_regulation").strip().lower()
        enrich_url = str(ref.get("enrich_url") or "").strip()
        text_body = ""
        if enrich_url:
            async with httpx.AsyncClient(
                follow_redirects=True, timeout=self._TIMEOUT
            ) as client:
                r = await client.get(enrich_url)
                r.raise_for_status()
                text_body = (r.text or "") if r else ""
            if not ex and text_body:
                ex = text_body[:2000]
            if "source_url" not in ref and enrich_url:
                su = enrich_url
        h = hashlib.sha256(
            f"{ctx.entity_id}|{ex}|{su}".encode("utf-8")
        ).hexdigest()[:32]
        kid_source = await ctx.qe.ensure_knowledge_source(
            "api",
            label=ENRICH_SOURCE_LABEL,
            base_url="",
            config_json={"role": "publisher_enrich"},
        )
        r_ins = await ctx.qe.insert_knowledge_item(
            kid_source,
            f"sha256:{h}",
            content_excerpt=ex,
            external_id=f"enrich_{ctx.entity_id}_{h[:12]}",
            payload={
                "enrich": True,
                "entity_id": ctx.entity_id,
                "ref": ref,
            },
        )
        kmid = int(r_ins.id)
        res = EnrichResult(
            knowledge_item_ids=[kmid], graph_edge_ids=[], last_enriched_at=_iso_now()
        )
        cat = await ctx.qe.upsert_entity(
            type="category",
            name=code,
            payload_json={"triage_code": code},
        )
        cid = int(cat["entity_id"])
        eid = await ctx.qe.insert_graph_edge(
            src_entity_id=ctx.entity_id,
            dst_entity_id=cid,
            edge_type="classified_as",
            confidence=1.0,
            source_url=su,
        )
        res.graph_edge_ids.append(eid)
        await ctx.qe.link_edge_evidence_upsert(
            edge_id=eid, knowledge_id=kmid, span_json={"source": "enrich"}
        )
        await ctx.qe.upsert_entity(
            type=str(ent["type"]),
            name=str(ent["name"]),
            payload_json=ent.get("payload_json") or {},
            last_enriched_at=res.last_enriched_at,
        )
        return res


def get_default_enrich_connector() -> ReferenceJsonEnrichConnector:
    return ReferenceJsonEnrichConnector()


async def run_enrich_step(
    qe: QueryEngine,
    settings: Settings,
    *,
    entity_id: int,
    connector: EnrichConnector | None = None,
) -> dict[str, Any]:
    ctx = EnrichContext(qe=qe, settings=settings, entity_id=int(entity_id))
    c = connector or get_default_enrich_connector()
    out = await c(ctx)
    return {
        "knowledge_item_ids": out.knowledge_item_ids,
        "graph_edge_ids": out.graph_edge_ids,
        "last_enriched_at": out.last_enriched_at,
    }
