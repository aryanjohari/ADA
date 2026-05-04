"""Shared publish ENRICH body (workflow DAG + optional batch CLI)."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from ada.config import Settings
from ada.orchestrator import orchestrate_turn
from ada.publish.enrich import run_enrich_step
from ada.query_engine import QueryEngine
from ada.tool_executor import build_web_tool_config
from ada.workflow.enrich_sufficiency import evaluate_enrich_graph_sufficiency
from ada.workflow.enrich_verify import enrich_postcondition_met
from ada.workflow.steps import KNOWLEDGE_TOOLS_ENRICH


def enrich_retry_system_suffix(min_unique_facts: int) -> str:
    n = int(min_unique_facts)
    return (
        "\n\n[ENRICH graph-only retry]\n"
        "The prior model turn did not produce verifiable graph progress for this subject. "
        "Do not end with questions to the user; when ambiguous, pick sensible defaults "
        "(map niche hints to category or policy-style edges using existing destination nodes). "
        "Your final actions must include durable graph writes: record_edge and/or link_evidence, "
        "using search_knowledge, get_entity_graph_context, and EXISTING_SUBGRAPH in the user message. "
        "Web tools are disabled on this retry. Prefer anchoring new edges to existing dst_entity_id "
        "values from EXISTING_SUBGRAPH; use record_entity only when no existing node fits. "
        f"The next GATE checks that this subject has at least {n} distinct canonical https URLs on "
        "non-hypothesis record_edge rows (counts DISTINCT source_url; repeating one URL adds nothing). "
        "Introduce new edges with new canonical page URLs—not more tool chatter reusing one citation URL."
    )


def enrich_live_web_eligible(settings: Settings) -> bool:
    if not settings.enable_web_tools:
        return False
    if not (settings.serper_api_key or "").strip():
        return False
    if not (settings.gemini_api_key or "").strip():
        return False
    return True


def enrich_max_tool_rounds(default: int) -> int:
    raw = os.environ.get("ADA_ENRICH_MAX_TOOL_ROUNDS", "").strip()
    if not raw:
        return default
    try:
        return max(1, min(48, int(raw)))
    except ValueError:
        return default


def build_enrich_user_text(
    *,
    goal_text: str,
    entity_id: int,
    entity: dict[str, Any],
    merged_params: dict[str, Any],
    min_unique_facts: int,
    subgraph_pack: dict[str, Any] | None = None,
) -> str:
    niche = str(merged_params.get("niche") or "").strip()
    hints = {k: merged_params[k] for k in merged_params if k != "entity_id"}
    lines: list[str] = [
        "[WORKFLOW_STEP:ENRICH — live web + graph]",
        f"Parent goal: {goal_text}",
        f"Subject entity_id={entity_id} name={entity.get('name')!r} type={entity.get('type')!r}.",
        f"Optional niche hint: {niche or '(none)'}",
        f"Merged params / hints: {json.dumps(hints, ensure_ascii=False)}",
        "Instructions:",
        "1) Use web_search (Serper) to find relevant https sources.",
        "2) Use fetch_url_text for pages that need full text (Jina reader when ADA_WEB_FETCH_MODE=jina).",
        "3) Use search_knowledge if prior knowledge_items already cover the topic; "
        "use get_entity_graph_context(entity_id) to re-read the bounded subject subgraph when needed.",
        "4) Persist facts with record_entity, record_edge, and link_evidence as needed. "
        "Prefer record_edge to **existing** dst_entity_id nodes from EXISTING_SUBGRAPH when the "
        "relationship fits (same spirit as EXTRACT grounding); create record_entity only when necessary.",
        "5) Do not end your turn with questions to the user—commit defaults when uncertain.",
        f"6) Publishing GATE counts DISTINCT source_url on your non-hypothesis record_edge calls "
        f"from this subject. You need **at least {int(min_unique_facts)} distinct** canonical "
        "https URLs (different pages)—e.g. `https://example.org/a` and `https://example.org/b` count "
        "as two; five edges citing the **same** URL still count as **one** for GATE. "
        "Do not rely on duplicating one URL to pass. Invalid or missing https source_url on fact edges fails.",
    ]
    if subgraph_pack is not None:
        lines.extend(
            [
                "## EXISTING_SUBGRAPH",
                "Bounded subject subgraph (newest edges first). Connect new edges to existing "
                "dst nodes here when possible.",
                json.dumps(subgraph_pack, ensure_ascii=False, indent=2),
            ]
        )
    return "\n".join(lines)


def build_enrich_graph_only_user_text(
    *,
    goal_text: str,
    entity_id: int,
    entity: dict[str, Any],
    merged_params: dict[str, Any],
    min_unique_facts: int,
    subgraph_pack: dict[str, Any] | None = None,
) -> str:
    """ENRICH without web_search / fetch_url_text (DB + prior knowledge only)."""
    niche = str(merged_params.get("niche") or "").strip()
    hints = {k: merged_params[k] for k in merged_params if k != "entity_id"}
    lines: list[str] = [
        "[WORKFLOW_STEP:ENRICH — graph + knowledge, no web]",
        f"Parent goal: {goal_text}",
        f"Subject entity_id={entity_id} name={entity.get('name')!r} type={entity.get('type')!r}.",
        f"Optional niche hint: {niche or '(none)'}",
        f"Merged params / hints: {json.dumps(hints, ensure_ascii=False)}",
        "Instructions:",
        "1) Do NOT use web_search or fetch_url_text; they are disabled.",
        "2) Use get_entity_graph_context and search_knowledge on stored knowledge_items.",
        "3) Use record_entity, record_edge, and link_evidence to persist. Prefer record_edge to "
        "existing dst_entity_id in EXISTING_SUBGRAPH when the relationship fits.",
        "4) Do not end with questions to the user—commit defaults when uncertain.",
        f"5) Non-hypothesis record_edge requires a canonical https source_url each time; GATE needs "
        f"**at least {int(min_unique_facts)} distinct** URLs across outgoing fact edges from this "
        "subject (distinct pages—reusing one URL repeatedly does not increase the count).",
    ]
    if subgraph_pack is not None:
        lines.extend(
            [
                "## EXISTING_SUBGRAPH",
                json.dumps(subgraph_pack, ensure_ascii=False, indent=2),
            ]
        )
    return "\n".join(lines)


async def run_publish_entity_enrich(
    qe: QueryEngine,
    settings: Settings,
    *,
    entity_id: int,
    entity: dict[str, Any],
    merged_params: dict[str, Any],
    goal_text: str,
    system_instruction: str,
    session_id: int,
    max_tool_rounds: int,
    shell_max_output_bytes: int,
    shell_timeout_sec: float,
    stream_chunk_idle_timeout_sec: float | None,
    stream_leg_max_wall_sec: float | None,
    rewire_after_tombstone: bool,
    max_session_tokens: int,
    debug_stream: bool,
    knowledge_feed_host_allowlist: frozenset[str],
    knowledge_embeddings_enabled: bool,
    knowledge_embedding_model: str,
    knowledge_embedding_dim: int,
    knowledge_embedding_min_cosine: float,
    knowledge_tool_max_results: int,
    knowledge_tool_excerpt_chars: int,
    enrich_tool_rounds_cap: int | None = None,
) -> dict[str, Any]:
    """
    Execute one ENRICH pass for a publish subject (same semantics as workflow ENRICH step).
    ``session_id`` is the transcript session (parent goal task id for DAG; synthetic task for batch).
    """
    eid_int = int(entity_id)
    ent = entity
    use_live = enrich_live_web_eligible(settings)
    suff = None
    graph_only = False
    suff_skip_llm = False
    if use_live and not settings.enrich_suff_force_web:
        suff = await evaluate_enrich_graph_sufficiency(qe, eid_int, settings)
        if suff.sufficient:
            if settings.enrich_suff_graph_refine:
                graph_only = True
            else:
                suff_skip_llm = True

    if use_live and suff_skip_llm:
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        payload = ent.get("payload_json")
        if not isinstance(payload, dict):
            payload = {}
        await qe.upsert_entity(
            type=str(ent["type"]),
            name=str(ent["name"]),
            payload_json=payload,
            last_enriched_at=now,
        )
        return {
            "path": "graph_sufficient",
            "reason": suff.reason if suff is not None else "thresholds_met",
            "metrics": suff.metrics if suff is not None else {},
            "thresholds": {
                "min_unique_local_facts": suff.threshold_unique_local_facts
                if suff is not None
                else None,
                "min_outgoing_edges": suff.threshold_outgoing_edges
                if suff is not None
                else None,
                "mode": suff.mode if suff is not None else "all",
            },
            "providers": [],
            "subgraph_injected": False,
            "last_enriched_at": now,
        }

    web_cfg = build_web_tool_config(settings) if use_live else None
    if not graph_only and use_live and web_cfg is None:
        use_live = False
    if use_live and (graph_only or web_cfg is not None):
        pack = await qe.load_subject_subgraph_context_pack(eid_int)
        if graph_only:
            user_txt = build_enrich_graph_only_user_text(
                goal_text=goal_text,
                entity_id=eid_int,
                entity=ent,
                merged_params=merged_params,
                min_unique_facts=settings.ada_publish_min_unique_facts,
                subgraph_pack=pack,
            )
            first_allow_web = False
        else:
            user_txt = build_enrich_user_text(
                goal_text=goal_text,
                entity_id=eid_int,
                entity=ent,
                merged_params=merged_params,
                min_unique_facts=settings.ada_publish_min_unique_facts,
                subgraph_pack=pack,
            )
            first_allow_web = True
        active_web_cfg = None if graph_only else web_cfg
        enrich_rounds = enrich_max_tool_rounds(max_tool_rounds)
        if enrich_tool_rounds_cap is not None:
            enrich_rounds = min(enrich_rounds, max(1, int(enrich_tool_rounds_cap)))
        snap_edge = await qe.max_graph_edge_id_for_src_entity(eid_int)
        snap_facts = await qe.count_unique_local_facts(eid_int)
        snap_seq = await qe.max_message_sequence(session_id)
        final = await orchestrate_turn(
            qe,
            session_id=session_id,
            user_text=user_txt,
            system_instruction=system_instruction,
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            shell_allowlist=frozenset(),
            max_tool_rounds=enrich_rounds,
            shell_max_output_bytes=shell_max_output_bytes,
            shell_timeout_sec=shell_timeout_sec,
            stream_chunk_idle_timeout_sec=stream_chunk_idle_timeout_sec,
            stream_leg_max_wall_sec=stream_leg_max_wall_sec,
            rewire_after_tombstone=rewire_after_tombstone,
            enable_memory_tools=False,
            memory_config=None,
            include_plan_tools=False,
            include_goal_recall_tool=False,
            file_config=None,
            max_session_tokens=max_session_tokens,
            on_file_guard_violation=None,
            web_config=active_web_cfg,
            enable_list_session_web_sources=False,
            debug_stream=debug_stream,
            include_knowledge_tools=False,
            knowledge_feed_host_allowlist=knowledge_feed_host_allowlist,
            knowledge_embeddings_enabled=knowledge_embeddings_enabled,
            knowledge_embedding_model=knowledge_embedding_model,
            knowledge_embedding_dim=knowledge_embedding_dim,
            knowledge_embedding_min_cosine=knowledge_embedding_min_cosine,
            knowledge_tool_max_results=knowledge_tool_max_results,
            knowledge_tool_excerpt_chars=knowledge_tool_excerpt_chars,
            knowledge_tool_subset=KNOWLEDGE_TOOLS_ENRICH,
            workflow_strict=True,
            workflow_strict_allow_web=first_allow_web,
            include_workflow_tools=False,
            workflow_max_steps=None,
            enrich_subject_entity_id=eid_int,
        )
        after_edge = await qe.max_graph_edge_id_for_src_entity(eid_int)
        after_facts = await qe.count_unique_local_facts(eid_int)
        chain_after = await qe.load_chain_for_api(session_id)
        post_ok = enrich_postcondition_met(
            snap_edge_max=snap_edge,
            snap_facts=snap_facts,
            snap_seq=snap_seq,
            after_edge_max=after_edge,
            after_facts=after_facts,
            chain_after=chain_after,
        )
        retry_used = False
        if not post_ok:
            retry_used = True
            snap_edge_b = after_edge
            snap_facts_b = after_facts
            snap_seq_b = await qe.max_message_sequence(session_id)
            final = await orchestrate_turn(
                qe,
                session_id=session_id,
                user_text=user_txt,
                system_instruction=system_instruction
                + enrich_retry_system_suffix(settings.ada_publish_min_unique_facts),
                api_key=settings.gemini_api_key,
                model=settings.gemini_model,
                shell_allowlist=frozenset(),
                max_tool_rounds=enrich_rounds,
                shell_max_output_bytes=shell_max_output_bytes,
                shell_timeout_sec=shell_timeout_sec,
                stream_chunk_idle_timeout_sec=stream_chunk_idle_timeout_sec,
                stream_leg_max_wall_sec=stream_leg_max_wall_sec,
                rewire_after_tombstone=rewire_after_tombstone,
                enable_memory_tools=False,
                memory_config=None,
                include_plan_tools=False,
                include_goal_recall_tool=False,
                file_config=None,
                max_session_tokens=max_session_tokens,
                on_file_guard_violation=None,
                web_config=None,
                enable_list_session_web_sources=False,
                debug_stream=debug_stream,
                include_knowledge_tools=False,
                knowledge_feed_host_allowlist=knowledge_feed_host_allowlist,
                knowledge_embeddings_enabled=knowledge_embeddings_enabled,
                knowledge_embedding_model=knowledge_embedding_model,
                knowledge_embedding_dim=knowledge_embedding_dim,
                knowledge_embedding_min_cosine=knowledge_embedding_min_cosine,
                knowledge_tool_max_results=knowledge_tool_max_results,
                knowledge_tool_excerpt_chars=knowledge_tool_excerpt_chars,
                knowledge_tool_subset=KNOWLEDGE_TOOLS_ENRICH,
                workflow_strict=True,
                workflow_strict_allow_web=False,
                include_workflow_tools=False,
                workflow_max_steps=None,
                enrich_subject_entity_id=eid_int,
            )
            after_edge_2 = await qe.max_graph_edge_id_for_src_entity(eid_int)
            after_facts_2 = await qe.count_unique_local_facts(eid_int)
            chain_2 = await qe.load_chain_for_api(session_id)
            post_ok = enrich_postcondition_met(
                snap_edge_max=snap_edge_b,
                snap_facts=snap_facts_b,
                snap_seq=snap_seq_b,
                after_edge_max=after_edge_2,
                after_facts=after_facts_2,
                chain_after=chain_2,
            )
            if not post_ok:
                raise ValueError(
                    "ENRICH live: no verifiable graph progress after initial turn "
                    "and graph-only retry (no new outgoing edge id, no increased "
                    "distinct source_url facts, no successful record_edge tool row)."
                )
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        payload = ent.get("payload_json")
        if not isinstance(payload, dict):
            payload = {}
        await qe.upsert_entity(
            type=str(ent["type"]),
            name=str(ent["name"]),
            payload_json=payload,
            last_enriched_at=now,
        )
        chain = await qe.load_chain_for_api(session_id)
        tool_rows = sum(1 for r in chain if r.get("role") == "tool")
        if graph_only:
            return {
                "assistant_excerpt": final[:4000],
                "tool_rounds": tool_rows,
                "path": "graph_refine",
                "graph_sufficiency": suff.metrics if suff is not None else {},
                "providers": [],
                "last_enriched_at": now,
                "subgraph_injected": True,
                "post_condition_ok": True,
                "retry_used": retry_used,
            }
        return {
            "assistant_excerpt": final[:4000],
            "tool_rounds": tool_rows,
            "providers": ["serper", "jina"],
            "path": "live_web",
            "last_enriched_at": now,
            "subgraph_injected": True,
            "post_condition_ok": True,
            "retry_used": retry_used,
        }
    return await run_enrich_step(qe, settings, entity_id=eid_int)
