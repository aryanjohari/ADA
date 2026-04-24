"""DRAFT workflow step: Gemini → JSON → PageJsonV1 (no tool loop, no critic)."""

from __future__ import annotations

import json
import logging
from typing import Any

from google import genai
from google.genai import types

from ada.config import Settings
from ada.knowledge_embeddings import embed_query_text
from ada.publish.page_schema_v1 import PageJsonV1
from ada.query_engine import QueryEngine

log = logging.getLogger("ada.publish.draft")

# Cap graph-anchored RAG query length (embedding + FTS input).
_DRAFT_GRAPH_ANCHORED_QUERY_MAX = 8000


def _draft_retrieval_query_string(params: dict[str, Any], entity: dict[str, Any]) -> str:
    name = str(entity.get("name") or "").strip()
    et = str(entity.get("type") or "").strip()
    niche = str(params.get("niche") or "").strip()
    extra = params.get("draft_search_keywords")
    if isinstance(extra, str) and extra.strip():
        kw = extra.strip()
    elif isinstance(extra, (list, tuple)):
        kw = " ".join(str(x).strip() for x in extra if str(x).strip())
    else:
        kw = ""
    parts = [p for p in (name, et, niche, kw) if p]
    return " ".join(parts).strip()


def _draft_graph_anchored_query(
    pack: dict[str, Any], params: dict[str, Any], entity: dict[str, Any]
) -> str:
    """
    Build a search string from the subject subgraph: entity + niche + each edge
    (type, destination name/type) so knowledge_items hybrid search targets the same topic.
    """
    base = _draft_retrieval_query_string(params, entity)
    parts: list[str] = [base] if base else []
    subj = pack.get("subject")
    if isinstance(subj, dict) and not base:
        n = str(subj.get("name") or "").strip()
        t = str(subj.get("type") or "").strip()
        parts = [" ".join(p for p in (n, t) if p).strip()]
    edges = pack.get("outgoing_edges")
    if not isinstance(edges, list):
        return (parts[0] if parts else "").strip()[:_DRAFT_GRAPH_ANCHORED_QUERY_MAX]
    for e in edges[:60]:
        if not isinstance(e, dict):
            continue
        et = str(e.get("edge_type") or "").strip()
        dst = e.get("dst")
        dn = dt = ""
        if isinstance(dst, dict):
            dn = str(dst.get("name") or "").strip()
            dt = str(dst.get("type") or "").strip()
        segs = [s for s in (et, dn, dt) if s]
        if segs:
            parts.append(" ".join(segs))
    q = "\n".join(p for p in parts if p).strip()
    if len(q) > _DRAFT_GRAPH_ANCHORED_QUERY_MAX:
        return q[: _DRAFT_GRAPH_ANCHORED_QUERY_MAX - 1] + "…"
    return q


def _format_subgraph_snapshot_block(pack: dict[str, Any]) -> str:
    if not pack or not isinstance(pack, dict):
        return ""
    try:
        body = json.dumps(pack, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        body = str(pack)
    return "\n--- Subject subgraph (read this for structure, entities, and edge types) ---\n" + body


def _subgraph_has_edges(pack: dict[str, Any] | None) -> bool:
    if not pack or not isinstance(pack, dict):
        return False
    e = pack.get("outgoing_edges")
    return isinstance(e, list) and len(e) > 0


def _resolved_draft_search_mode(settings: Settings) -> str:
    raw = (settings.publish_draft_knowledge_search_mode or "auto").strip().lower()
    if raw == "auto":
        if (
            settings.enable_knowledge_embeddings
            and (settings.gemini_api_key or "").strip()
        ):
            return "hybrid"
        return "lexical"
    if raw in ("lexical", "semantic", "hybrid"):
        return raw
    return "lexical"


def _norm_excerpt_fingerprint(s: str) -> str:
    t = " ".join(str(s or "").split()).strip().lower()
    return t[:400]


def _knowledge_item_link(item: dict[str, Any]) -> str:
    pl = item.get("payload")
    if isinstance(pl, dict):
        for k in ("link", "url", "canonical_url"):
            v = pl.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
    return ""


def _format_knowledge_search_pack(
    items: list[dict[str, Any]], *, per_item_max: int, total_max: int
) -> str:
    if not items:
        return ""
    lines: list[str] = [
        "\n--- Additional knowledge (knowledge_items search; deduped vs edge evidence) ---",
    ]
    used = 0
    for i, it in enumerate(items, 1):
        kid = int(it.get("id") or 0)
        body = str(it.get("content_excerpt") or "").strip().replace("\r\n", "\n")
        if len(body) > per_item_max:
            body = body[: per_item_max - 1] + "…"
        link = _knowledge_item_link(it)
        head = f"[K{i}] knowledge_id={kid}"
        if link:
            head += f" link={link!r}"
        block = f"{head}\n{body}"
        if used + len(block) + 1 > total_max:
            break
        lines.append(block)
        used += len(block) + 1
    if len(lines) < 2:
        return ""
    return "\n".join(lines)


async def load_draft_knowledge_for_prompt(
    qe: QueryEngine,
    settings: Settings,
    params: dict[str, Any],
    entity: dict[str, Any],
    *,
    edge_excerpts: list[dict[str, Any]],
    retrieval_query: str | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """
    Top-K knowledge_items via same search path as search_knowledge; dedupe by knowledge_id
    and near-duplicate text vs edge evidence excerpts.
    """
    if not (
        settings.publish_draft_knowledge_retrieval
        or settings.publish_draft_graph_anchored_knowledge
    ):
        return "", []
    if retrieval_query is not None and str(retrieval_query).strip():
        q = str(retrieval_query).strip()
    else:
        q = _draft_retrieval_query_string(params, entity)
    if not q:
        return "", []
    exclude_ids = {int(x["knowledge_id"]) for x in edge_excerpts if x.get("knowledge_id")}
    edge_sigs = {
        _norm_excerpt_fingerprint(str(x.get("content_excerpt") or "")) for x in edge_excerpts
    }
    mode = _resolved_draft_search_mode(settings)
    q_emb: list[float] | None = None
    if mode in ("semantic", "hybrid") and settings.enable_knowledge_embeddings:
        if not (settings.gemini_api_key or "").strip():
            mode = "lexical"
        else:
            q_emb = await embed_query_text(
                settings.gemini_api_key,
                q,
                model=settings.knowledge_embedding_model,
                output_dimensionality=settings.knowledge_embedding_dim,
            )
    overfetch = max(
        settings.publish_draft_knowledge_top_k * 3,
        settings.publish_draft_knowledge_top_k + 4,
    )
    hits = await qe.search_knowledge_items(
        q,
        limit=overfetch,
        search_mode=mode,
        query_embedding=q_emb,
        embedding_model=settings.knowledge_embedding_model,
        embedding_min_cosine=settings.publish_draft_knowledge_min_cosine,
        prefer_fts=True,
    )
    pick: list[dict[str, Any]] = []
    seen_text: set[str] = set()
    for row in hits:
        kid = int(row.get("id") or 0)
        if kid in exclude_ids:
            continue
        body = str(row.get("content_excerpt") or "").strip()
        sig = _norm_excerpt_fingerprint(body)
        if not sig or sig in edge_sigs or sig in seen_text:
            continue
        seen_text.add(sig)
        pick.append(row)
        if len(pick) >= settings.publish_draft_knowledge_top_k:
            break
    block = _format_knowledge_search_pack(
        pick,
        per_item_max=settings.publish_draft_knowledge_excerpt_per_item,
        total_max=settings.publish_draft_knowledge_max_total_chars,
    )
    return block, pick


def _format_grounding_pack(excerpts: list[dict[str, Any]]) -> str:
    if not excerpts:
        return ""
    lines: list[str] = [
        "\n--- Grounding excerpts (evidence linked from this entity; stay faithful) ---",
    ]
    for i, ex in enumerate(excerpts, 1):
        su = str(ex.get("source_url") or "").strip()
        body = str(ex.get("content_excerpt") or "").strip().replace("\r\n", "\n")
        lines.append(f"[{i}] source_url={su!r}\n{body}")
    return "\n".join(lines)


def _build_draft_user_text(
    *,
    goal_text: str,
    params: dict[str, Any],
    entity: dict[str, Any],
) -> str:
    eid = params.get("entity_id")
    niche = str(params.get("niche") or "").strip()
    project_id = str(params.get("project_id") or "")
    campaign_id = str(params.get("campaign_id") or "")
    slug_hint = str(params.get("slug") or "").strip()
    return "\n".join(
        [
            "[WORKFLOW_STEP:DRAFT — pSEO page.json]",
            f"Parent workflow goal: {goal_text}",
            f"Entity id={eid!s} name={entity.get('name')!r} type={entity.get('type')!r}.",
            f"Placements: project_id={project_id!r} campaign_id={campaign_id!r} niche={niche!r}.",
            f"Optional slug hint: {slug_hint or '(derive from name; URL-safe)'}",
            "Output must be a single JSON object only (no markdown).",
            "Field `content` is semantic HTML (headings, lists, tables) suitable for"
            " dangerouslySetInnerHTML after sanitization; no full HTML document shell.",
            "SEO: `title` and `meta_description` must be compelling, keyword-aware, and under typical"
            " SERP length limits; use a clear H1 inside `content` and logical H2/H3 sections; include"
            " natural use of the entity and niche terms; avoid empty fluff.",
            "When the grounding sections provide enough substance, make `content` rich and specific",
            "— target roughly 800+ words with concrete data; otherwise do the best you can without inventing "
            "facts beyond the provided evidence.",
        ]
    )


def _pydantic_json_schema() -> dict[str, Any]:
    # Gemini JSON schema: root object, draft-07 compatible via Pydantic
    return PageJsonV1.model_json_schema()


async def run_publish_draft(
    qe: QueryEngine,
    settings: Settings,
    *,
    goal_text: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    eid = params.get("entity_id")
    if eid is None:
        raise ValueError("params_json must include entity_id for DRAFT")
    eid = int(eid)
    ent = await qe.get_entity_by_id(eid)
    if ent is None:
        raise ValueError(f"no entity for id={eid}")
    pack = await qe.load_subject_subgraph_context_pack(
        eid,
        max_edges=48,
        max_excerpt_items=20,
        excerpt_max_chars=800,
        max_total_json_chars=settings.publish_draft_subgraph_max_json_chars,
    )
    n_facts = await qe.count_unique_local_facts(eid)
    rquery = _draft_graph_anchored_query(pack, params, ent)
    excerpts = await qe.list_enrichment_excerpts_for_entity(
        eid, limit=12, excerpt_max_chars=800
    )
    know_block, _ = await load_draft_knowledge_for_prompt(
        qe,
        settings,
        params,
        ent,
        edge_excerpts=excerpts,
        retrieval_query=rquery,
    )
    user = (
        _build_draft_user_text(goal_text=goal_text, params=params, entity=ent)
        + f"\nGraph fact count (distinct source_url on active edges from entity): {n_facts}."
        + _format_subgraph_snapshot_block(pack)
        + _format_grounding_pack(excerpts)
        + know_block
    )
    if not (settings.gemini_api_key or "").strip():
        raise ValueError("GEMINI_API_KEY required for DRAFT")

    model = (settings.publish_draft_model or settings.gemini_model).strip()
    client = genai.Client(api_key=settings.gemini_api_key)
    has_rag = bool((know_block or "").strip())
    has_extra = has_rag or _subgraph_has_edges(pack)
    sys_core = (
        "You output JSON only, matching the PageJsonV1 contract, for a pSEO"
        " landing page. No tool calls; no preambles. Required top-level keys:"
        " slug, title, meta_description, content, lead_gen, json_ld; optional og_image."
    )
    if has_extra or n_facts >= 3 or len(excerpts) >= 3:
        sys = (
            sys_core
            + " Use the subject subgraph, grounding excerpts, and any additional knowledge section"
            " below. Prefer a substantial, SEO-appropriate `content` (about 800+ words) when"
            " evidence supports it; every claim must trace to the excerpts, subgraph-linked facts, "
            "or search snippets. Do not invent numbers or quotes not present in the context."
        )
    else:
        sys = sys_core
    common_kwargs: dict[str, Any] = {
        "model": model,
        "contents": [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=user)],
            )
        ],
    }
    cfg = types.GenerateContentConfig(
        system_instruction=sys,
        response_mime_type="application/json",
        response_json_schema=_pydantic_json_schema(),
        temperature=0.2,
    )
    try:
        resp = await client.aio.models.generate_content(
            **common_kwargs,
            config=cfg,
        )
    except Exception as e:
        log.warning("DRAFT with response_json_schema failed (%s); retrying JSON only", e)
        cfg2 = types.GenerateContentConfig(
            system_instruction=sys,
            response_mime_type="application/json",
            temperature=0.2,
        )
        resp = await client.aio.models.generate_content(
            **common_kwargs,
            config=cfg2,
        )
    raw = (getattr(resp, "text", None) or "").strip()
    if not raw:
        raise ValueError("empty DRAFT model response")
    try:
        page = PageJsonV1.model_validate_json(raw)
    except Exception as e:
        log.info("DRAFT validation failed: %s", e)
        raise ValueError(
            f"PageJsonV1 validation failed: {e}"
        ) from e
    return {"page": page.model_dump(mode="json", exclude_none=True)}
