from __future__ import annotations

import inspect
import json
import logging
from dataclasses import dataclass
from typing import Any

from ada.query_engine import QueryEngine

log = logging.getLogger("ada.extract.graph_lite")

# Canonical types (plus common LLM synonyms mapped before upsert).
_GRAPH_ENTITY_TYPES: frozenset[str] = frozenset(
    {
        "organization",
        "government_body",
        "person",
        "sector",
        "instrument",
        "policy_instrument",
        "event",
        "location",
        "category",
    }
)
_ENTITY_TYPE_ALIASES: dict[str, str] = {
    "company": "organization",
    "niche": "sector",
    "region": "location",
    "agency": "government_body",
}


@dataclass
class GraphLiteExtractStats:
    processed_docs: int = 0
    entities_upserted: int = 0
    edges_created: int = 0
    evidence_links_created: int = 0
    rejected: int = 0


def _default_extractor_payload(items: list[dict[str, Any]]) -> dict[str, Any]:
    # Deterministic no-op fallback; real extraction is injected by caller/LLM path.
    return {"entities": [], "edges": [], "evidence": []}


def _parse_model_json_object(raw: str) -> dict[str, Any] | None:
    """Parse Gemini JSON text; return None on empty/invalid output (e.g. truncation)."""
    s = (raw or "").strip()
    if not s:
        return None
    if s.startswith("```"):
        lines = s.splitlines()
        if len(lines) >= 2 and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() in ("```", "```json"):
            lines = lines[:-1]
        s = "\n".join(lines).strip()
    try:
        data = json.loads(s)
    except json.JSONDecodeError as e:
        log.warning("graph-lite model output is not valid JSON (%s); skipping batch", e)
        return None
    if not isinstance(data, dict):
        return None
    return data


def _build_extraction_prompt(items: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for d in items:
        kid = int(d["id"])
        excerpt = str(d.get("content_excerpt") or "")
        payload = d.get("payload") if isinstance(d.get("payload"), dict) else {}
        title = str(payload.get("title") or "").strip()
        link = str(payload.get("link") or "").strip()
        block = [f"knowledge_id: {kid}"]
        if title:
            block.append(f"title: {title}")
        if link:
            block.append(f"link: {link}")
        block.append("excerpt:")
        block.append(excerpt[:3000])
        blocks.append("\n".join(block))
    return "\n\n---\n\n".join(blocks)


def build_llm_graph_extractor(
    *,
    api_key: str,
    model: str,
    token_cap: int,
):
    from google import genai
    from google.genai import types

    system = (
        "Extract a small knowledge graph from the documents. Return JSON only with keys "
        "`entities`, `edges`, and optional `schema_rationale` (one short debug line; ignored by storage).\n"
        "Entity types (use one per entity): organization, government_body, person, sector, "
        "instrument, policy_instrument, event, location, category. "
        "Category nodes represent the fixed triage taxonomy (e.g. type category, name policy_regulation).\n"
        "Entity schema: {key, type, name, aliases?, external_ids?, payload?}.\n"
        "Edge types (lowercase snake_case): announces, funds, regulates, reports_on, affects_sector, "
        "part_of, located_in, competes_with, supplies_to, under_category, classified_as.\n"
        "Link non-category entities to a category parent with under_category when the text supports it; "
        "every edge must cite evidence_item_ids from the provided knowledge_id values only.\n"
        "Edge schema: {src_key, dst_key, edge_type, confidence, evidence_item_ids}.\n"
        "Rules: confidence in [0,1]; skip uncertain claims; avoid duplicate entities; prefer NZ-relevant facts.\n"
        "Hard exclusions — do not extract entities or edges for: routine weather forecasts; "
        "routine traffic accidents / road closures unless the piece clearly ties to major infrastructure, "
        "freight, or material economic impact; entertainment, cartoons, sport, celebrity, or pure "
        "human-interest with no business/policy/economic hook. "
        "Do not use under_category (or other edges) to file those topics into category nodes. "
        "If the document is only excluded content above, return "
        '{"entities": [], "edges": []} '
        "and optional schema_rationale explaining e.g. skipped: excluded content."
    )
    client = genai.Client(api_key=api_key)
    # `token_cap` bounds the *input* excerpt budget in `run_graph_lite_extraction`; reusing
    # it for max_output_tokens makes small --token-cap values truncate JSON (invalid JSON).
    max_out = min(8192, max(4096, token_cap))

    async def _extract(items: list[dict[str, Any]]) -> dict[str, Any]:
        if not items:
            return _default_extractor_payload(items)
        prompt = _build_extraction_prompt(items)
        resp = await client.aio.models.generate_content(
            model=model,
            contents=[
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=prompt)],
                )
            ],
            config=types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
                temperature=0.1,
                max_output_tokens=max_out,
            ),
        )
        raw = (getattr(resp, "text", None) or "").strip()
        data = _parse_model_json_object(raw)
        if data is None:
            return _default_extractor_payload(items)
        data.pop("schema_rationale", None)
        return data

    return _extract


async def run_graph_lite_extraction(
    qe: QueryEngine,
    *,
    limit: int,
    token_cap: int,
    source_id: int | None = None,
    extractor: Any | None = None,
    seed_triage_categories: bool = True,
) -> GraphLiteExtractStats:
    stats = GraphLiteExtractStats()
    lim = max(1, min(limit, 200))
    if seed_triage_categories:
        await qe.ensure_triage_category_entities()
    docs = await qe.list_knowledge_items(source_id=source_id, limit=lim, valid_at_now=True)
    stats.processed_docs = len(docs)
    if not docs:
        return stats

    # Bound model context by deterministic token-ish cap proxy (character budget).
    budget_chars = max(2000, token_cap * 4)
    bounded_docs: list[dict[str, Any]] = []
    used = 0
    for d in docs:
        excerpt = str(d.get("content_excerpt") or "")
        if used + len(excerpt) > budget_chars:
            break
        used += len(excerpt)
        bounded_docs.append(d)
    docs_by_id = {int(d["id"]): d for d in bounded_docs}

    runner = extractor or _default_extractor_payload
    if callable(runner):
        maybe_payload = runner(bounded_docs)
        payload = (
            await maybe_payload
            if inspect.isawaitable(maybe_payload)
            else maybe_payload
        )
    else:
        payload = _default_extractor_payload(bounded_docs)
    if not isinstance(payload, dict):
        stats.rejected += 1
        return stats
    if isinstance(payload, dict):
        payload.pop("schema_rationale", None)

    entity_map: dict[str, int] = {}
    for row in payload.get("entities", []):
        if not isinstance(row, dict):
            stats.rejected += 1
            continue
        name = str(row.get("name") or "").strip()
        raw_type = str(row.get("type") or "").strip().lower()
        etype = _ENTITY_TYPE_ALIASES.get(raw_type, raw_type)
        if not name or not etype or etype not in _GRAPH_ENTITY_TYPES:
            stats.rejected += 1
            continue
        rec = await qe.upsert_entity(
            type=etype,
            name=name,
            aliases=row.get("aliases") if isinstance(row.get("aliases"), list) else None,
            external_ids=row.get("external_ids") if isinstance(row.get("external_ids"), dict) else None,
            payload_json=row.get("payload") if isinstance(row.get("payload"), dict) else None,
        )
        entity_id = int(rec["entity_id"])
        norm = qe.normalize_entity_name(name)
        for t in {etype, raw_type}:
            entity_map[f"{t}:{norm}"] = entity_id
        key_raw = row.get("key")
        if isinstance(key_raw, str) and key_raw.strip():
            entity_map[key_raw.strip()] = entity_id
        if rec.get("inserted"):
            stats.entities_upserted += 1

    for row in payload.get("edges", []):
        if not isinstance(row, dict):
            stats.rejected += 1
            continue
        src_key = str(row.get("src_key") or "").strip()
        dst_key = str(row.get("dst_key") or "").strip()
        edge_type = str(row.get("edge_type") or "").strip().lower()
        try:
            confidence = float(row.get("confidence"))
        except (TypeError, ValueError):
            stats.rejected += 1
            continue
        evidence_ids = row.get("evidence_item_ids")
        if not isinstance(evidence_ids, list):
            stats.rejected += 1
            continue
        if confidence < 0.45:
            stats.rejected += 1
            continue
        if confidence < 0.60 and len(evidence_ids) < 2:
            stats.rejected += 1
            continue
        evidence_ints: list[int] = []
        for eid in evidence_ids:
            try:
                evidence_ints.append(int(eid))
            except (TypeError, ValueError):
                stats.rejected += 1
                evidence_ints = []
                break
        if not evidence_ints:
            continue
        if confidence < 0.70:
            source_ids = {
                int(d.get("source_id"))
                for eid in evidence_ints
                for d in [docs_by_id.get(eid)]
                if d is not None and d.get("source_id") is not None
            }
            if len(source_ids) <= 1:
                # Single-source spikes should not be promoted at low confidence.
                stats.rejected += 1
                continue
        src_id = entity_map.get(src_key)
        dst_id = entity_map.get(dst_key)
        if src_id is None or dst_id is None or not edge_type:
            stats.rejected += 1
            continue
        try:
            edge_id = await qe.insert_graph_edge(
                src_entity_id=src_id,
                dst_entity_id=dst_id,
                edge_type=edge_type,
                confidence=confidence,
            )
        except Exception:
            stats.rejected += 1
            continue
        stats.edges_created += 1
        for kid in evidence_ints:
            try:
                out = await qe.link_edge_evidence_upsert(
                    edge_id=edge_id,
                    knowledge_id=kid,
                )
            except Exception:
                stats.rejected += 1
                continue
            if out.get("upserted") is True:
                stats.evidence_links_created += 1
    log.debug(
        "graph-lite extraction processed=%s entities_upserted=%s edges_created=%s evidence_links=%s rejected=%s",
        stats.processed_docs,
        stats.entities_upserted,
        stats.edges_created,
        stats.evidence_links_created,
        stats.rejected,
    )
    return stats
