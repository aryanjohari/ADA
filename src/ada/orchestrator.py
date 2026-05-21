"""Agentic turn: stream legs + allowlisted tools (claude_logic §6–7)."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable, Coroutine
from typing import Any

from ada.adapters.gemini_stream import (
    apply_turn_harness_appendix_to_contents,
    chain_rows_to_contents,
    stream_one_model_leg,
)
from ada.config import Settings
from ada.knowledge_urls import validate_knowledge_feed_url
from ada.tools.web_runtime import validate_https_url
from ada.stream_debug import is_stream_debug_on, log_stream
from ada.stream_types import CompletedFunctionCall
from ada.query_engine import QueryEngine
from ada.tool_executor import (
    FileToolConfig,
    MemoryToolConfig,
    PlanToolHooks,
    StreamingToolExecutor,
    WebToolConfig,
)
from ada.knowledge_embeddings import embed_query_text
from ada.tools.registry import (
    build_agent_tools,
    frozen_tool_declaration_names,
)
from ada.workflow.enqueue import get_workflow_status_via_tool

log = logging.getLogger("ada.orchestrator")

# Stream occasionally returns 200 with empty text (esp. flash-lite). Retry before
# persisting: otherwise finalize+raise leaves empty assistant rows in the chain.
_EMPTY_MODEL_STREAM_RETRIES = 3


class StreamFailed(Exception):
    """Raised when the model stream ends without usable output."""


class SessionTokenLimitExceeded(Exception):
    """Raised when summed session usage_ledger tokens exceed ADA_MAX_SESSION_TOKENS."""


def file_guard_audit_hook(
    qe: QueryEngine,
    session_id: int,
    *,
    enabled: bool,
) -> Callable[[str, str, str], Coroutine[Any, Any, None]] | None:
    """Optional callback for StreamingToolExecutor when a path hits the file sandbox deny rules."""
    if not enabled:
        return None

    async def _cb(tool: str, path: str, reason: str) -> None:
        await qe.append_action_log(
            "file_access_denied",
            {"tool": tool, "path": path, "reason": reason},
            session_id=session_id,
        )

    return _cb


async def orchestrate_turn(
    qe: QueryEngine,
    *,
    session_id: int,
    user_text: str,
    system_instruction: str,
    api_key: str,
    model: str,
    on_delta: Callable[[str], Coroutine[Any, Any, None]] | None = None,
    max_retries: int = 1,
    shell_allowlist: frozenset[str] | None = None,
    max_tool_rounds: int = 12,
    shell_max_output_bytes: int = 65536,
    shell_timeout_sec: float = 60.0,
    stream_chunk_idle_timeout_sec: float | None = 120.0,
    stream_leg_max_wall_sec: float | None = 600.0,
    rewire_after_tombstone: bool = True,
    enable_memory_tools: bool = True,
    memory_config: MemoryToolConfig | None = None,
    include_plan_tools: bool = False,
    include_goal_recall_tool: bool = False,
    include_gsc_read_tools: bool = False,
    file_config: FileToolConfig | None = None,
    max_session_tokens: int = 50000,
    on_file_guard_violation: Callable[[str, str, str], Coroutine[Any, Any, None]]
    | None = None,
    web_config: WebToolConfig | None = None,
    enable_list_session_web_sources: bool = False,
    debug_stream: bool = False,
    include_knowledge_tools: bool = False,
    knowledge_feed_host_allowlist: frozenset[str] = frozenset(),
    knowledge_embeddings_enabled: bool = False,
    knowledge_embedding_model: str = "gemini-embedding-001",
    knowledge_embedding_dim: int = 768,
    knowledge_embedding_min_cosine: float = 0.25,
    knowledge_tool_max_results: int = 8,
    knowledge_tool_excerpt_chars: int = 1200,
    knowledge_tool_subset: frozenset[str] | None = None,
    workflow_strict: bool = False,
    workflow_strict_allow_web: bool = False,
    include_workflow_tools: bool = False,
    workflow_max_steps: int | None = None,
    workflow_require_approval: bool = False,
    enrich_subject_entity_id: int | None = None,
    mission_control_snapshot_fn: Callable[[], Awaitable[dict[str, Any]]] | None = None,
    include_run_skill: bool = False,
    include_propose_programme: bool = False,
    include_apply_programme: bool = False,
    motor_settings: Settings | None = None,
    chat_mission_slug: str | None = None,
    effective_mission_id: int | None = None,
    turn_harness_appendix: str | None = None,
) -> str:
    """
    Persist user once, then run one or more model legs with optional tool rounds.
    Retries only if no tool results were persisted for this user turn.
    On retry: StreamingToolExecutor.discard() on the failed attempt's executor.
    """
    dbg = is_stream_debug_on(debug_stream)
    user_uuid = await qe.persist_user(session_id, user_text)
    allow = shell_allowlist or frozenset()
    wf_strict = bool(workflow_strict)
    strict_web = wf_strict and bool(workflow_strict_allow_web)
    eff_memory = enable_memory_tools and not wf_strict
    eff_plan = include_plan_tools and not wf_strict
    eff_goal_recall = include_goal_recall_tool and not wf_strict
    eff_gsc_read = include_gsc_read_tools and not wf_strict
    eff_file_cfg = None if wf_strict else file_config
    eff_web_cfg = web_config if (not wf_strict or strict_web) else None
    eff_ws_list = enable_list_session_web_sources and (not wf_strict or strict_web)
    eff_shell = frozenset() if wf_strict else allow
    gemini_tool = build_agent_tools(
        allowed_exact_commands=eff_shell,
        include_memory_tools=eff_memory,
        include_plan_tools=eff_plan,
        include_goal_recall_tool=eff_goal_recall,
        include_gsc_read_tools=eff_gsc_read,
        include_file_tools=eff_file_cfg is not None,
        include_web_search=eff_web_cfg is not None and bool(eff_web_cfg.serper_api_key),
        include_web_fetch=eff_web_cfg is not None,
        include_list_session_web_sources=eff_ws_list,
        include_knowledge_tools=include_knowledge_tools and knowledge_tool_subset is None,
        knowledge_tool_subset=knowledge_tool_subset,
        include_workflow_tools=include_workflow_tools,
        include_mission_control_snapshot=mission_control_snapshot_fn is not None,
        include_run_skill=include_run_skill,
        include_propose_programme=include_propose_programme,
        include_apply_programme=include_apply_programme,
    )
    dispatch_allowlist = (
        frozen_tool_declaration_names(gemini_tool) if wf_strict else None
    )
    log_stream(
        dbg,
        "orchestrator",
        "turn_start",
        f"session_id={session_id}",
        f"include_web_search={web_config is not None and bool(web_config.serper_api_key)}",
        f"include_web_fetch={web_config is not None}",
        f"web_tools_enabled={web_config is not None}",
    )
    legs_cap = max(1, max_tool_rounds)
    memory = memory_config if eff_memory else None
    knowledge_mission_scope = effective_mission_id
    if knowledge_mission_scope is None:
        knowledge_mission_scope = await qe.get_task_mission_id(session_id)

    async def _read_plan_bound() -> str:
        return await qe.get_task_plan_json(session_id)

    async def _write_plan_bound(text: str) -> None:
        await qe.set_task_plan_json(session_id, text)

    plan_hooks: PlanToolHooks | None = (
        PlanToolHooks(read_plan=_read_plan_bound, write_plan=_write_plan_bound)
        if eff_plan
        else None
    )

    async def _goal_recall_bound(task_id: int) -> dict[str, Any]:
        return await qe.get_goal_task_view_for_tool(task_id)

    goal_recall_reader = _goal_recall_bound if eff_goal_recall else None
    gsc_read_fn = None
    if eff_gsc_read:

        async def _gsc_read_bound(call: CompletedFunctionCall) -> dict[str, Any]:
            site = str(call.args.get("site") or "").strip()
            start_date = str(call.args.get("start_date") or "").strip()
            end_date = str(call.args.get("end_date") or "").strip()
            lim_raw = call.args.get("limit")
            lim = 25
            if lim_raw is not None:
                try:
                    lim = int(lim_raw)
                except (TypeError, ValueError):
                    return {"error": "limit must be an integer"}
            if not site:
                return {"error": "site is required"}
            quick_wins = await qe.list_gsc_quick_wins(
                site=site,
                start_date=start_date,
                end_date=end_date,
                limit=lim,
            )
            content_gaps = await qe.list_gsc_content_gaps(
                site=site,
                start_date=start_date,
                end_date=end_date,
                limit=lim,
            )
            page_fixes = await qe.list_gsc_page_fixes(
                site=site,
                start_date=start_date,
                end_date=end_date,
                limit=lim,
            )
            top_queries = await qe.list_gsc_top_queries(
                site=site,
                start_date=start_date,
                end_date=end_date,
                limit=lim,
            )
            top_pages = await qe.list_gsc_top_pages(
                site=site,
                start_date=start_date,
                end_date=end_date,
                limit=lim,
            )
            await qe.append_action_log(
                "gsc_read_tool_called",
                {
                    "site": site,
                    "start_date": start_date,
                    "end_date": end_date,
                    "limit": lim,
                    "counts": {
                        "top_queries": len(top_queries),
                        "top_pages": len(top_pages),
                        "quick_wins": len(quick_wins),
                        "content_gaps": len(content_gaps),
                        "page_fixes": len(page_fixes),
                    },
                },
                session_id=session_id,
            )
            return {
                "site": site,
                "start_date": start_date,
                "end_date": end_date,
                "top_queries": top_queries,
                "top_pages": top_pages,
                "quick_wins": quick_wins,
                "content_gaps": content_gaps,
                "page_fixes": page_fixes,
            }

        gsc_read_fn = _gsc_read_bound

    knowledge_search_fn = None
    knowledge_record_fn = None
    knowledge_record_market_edge_fn = None
    knowledge_add_fn = None
    knowledge_record_entity_fn = None
    knowledge_record_edge_fn = None
    knowledge_link_evidence_fn = None
    knowledge_graph_context_fn = None
    need_knowledge = include_knowledge_tools or knowledge_tool_subset is not None
    if need_knowledge:
        hosts = knowledge_feed_host_allowlist

        async def _knowledge_search_bound(
            call: CompletedFunctionCall,
        ) -> dict[str, Any]:
            q = str(call.args.get("query") or "").strip()
            lim_raw = call.args.get("limit")
            lim = 20
            if lim_raw is not None:
                try:
                    lim = max(1, min(int(lim_raw), 100))
                except (TypeError, ValueError):
                    lim = 20
            # Keep result payload bounded to avoid token bleed in chat/daemon loops.
            response_cap = max(1, min(25, knowledge_tool_max_results))
            tag = call.args.get("tag")
            tag_s = str(tag).strip() if tag is not None else None
            if tag_s == "":
                tag_s = None
            ing_after = call.args.get("ingested_after")
            ing_before = call.args.get("ingested_before")
            pref = call.args.get("prefer_fts")
            prefer_fts = True if pref is None else bool(pref)
            mode_raw = call.args.get("search_mode")
            mode_s = (
                str(mode_raw).strip().lower()
                if mode_raw is not None
                else "hybrid"
            )
            if mode_s not in ("lexical", "semantic", "hybrid"):
                mode_s = "hybrid"

            min_rs_raw = call.args.get("min_relevance_score")
            min_rs: float | None = None
            if min_rs_raw is not None:
                try:
                    min_rs = float(min_rs_raw)
                except (TypeError, ValueError):
                    min_rs = None
            vo = call.args.get("valid_only")
            valid_at_now = True if vo is None else bool(vo)

            ptc_raw = call.args.get("primary_triage_category")
            primary_triage_category: str | None = None
            if ptc_raw is not None:
                s = str(ptc_raw).strip()
                primary_triage_category = s if s else None

            qe_vec: list[float] | None = None
            if (
                knowledge_embeddings_enabled
                and api_key.strip()
                and mode_s in ("semantic", "hybrid")
            ):
                try:
                    qe_vec = await embed_query_text(
                        api_key,
                        q,
                        model=knowledge_embedding_model,
                        output_dimensionality=knowledge_embedding_dim,
                    )
                except Exception as e:
                    log.warning("knowledge query embedding failed: %s", e)

            items = await qe.search_knowledge_items(
                q,
                limit=lim,
                tag=tag_s,
                ingested_after=str(ing_after) if ing_after is not None else None,
                ingested_before=str(ing_before) if ing_before is not None else None,
                prefer_fts=prefer_fts,
                search_mode=mode_s,
                query_embedding=qe_vec,
                embedding_model=knowledge_embedding_model
                if knowledge_embeddings_enabled
                else None,
                embedding_min_cosine=knowledge_embedding_min_cosine,
                min_relevance_score=min_rs,
                valid_at_now=valid_at_now,
                primary_triage_category=primary_triage_category,
                mission_scope=knowledge_mission_scope,
            )
            slim: list[dict[str, Any]] = []
            for it in items[:response_cap]:
                ex = it.get("content_excerpt") or ""
                if len(ex) > knowledge_tool_excerpt_chars:
                    ex = ex[: max(1, knowledge_tool_excerpt_chars - 1)] + "…"
                pl = it.get("payload") if isinstance(it.get("payload"), dict) else {}
                slim.append(
                    {
                        "id": it["id"],
                        "source_id": it["source_id"],
                        "title": pl.get("title"),
                        "link": pl.get("link"),
                        "feed_url": pl.get("feed_url"),
                        "content_excerpt": ex,
                        "tags": it.get("tags"),
                        "ingested_at": it.get("ingested_at"),
                        "published_at": it.get("published_at"),
                        "relevance_score": it.get("relevance_score"),
                        "expires_at": it.get("expires_at"),
                        "triage_primary_category": it.get("triage_primary_category"),
                        "triage_secondary_categories": it.get(
                            "triage_secondary_categories"
                        ),
                    }
                )
            return {
                "items": slim,
                "count": len(items),
                "returned_count": len(slim),
                "truncated": len(items) > len(slim),
            }

        async def _knowledge_record_bound(
            call: CompletedFunctionCall,
        ) -> dict[str, Any]:
            body = str(call.args.get("body") or "").strip()
            if not body:
                return {"error": "body required"}
            raw_ids = call.args.get("ref_item_ids")
            if not isinstance(raw_ids, list) or not raw_ids:
                return {"error": "ref_item_ids must be a non-empty list"}
            refs: list[int] = []
            for x in raw_ids:
                try:
                    refs.append(int(x))
                except (TypeError, ValueError):
                    return {"error": "ref_item_ids must be integers"}
            if knowledge_mission_scope is not None:
                for rid in refs:
                    try:
                        await qe.get_knowledge_item(
                            rid, mission_scope=knowledge_mission_scope
                        )
                    except LookupError:
                        return {
                            "error": (
                                f"ref_item_ids: knowledge item id={rid} is not visible "
                                "for this mission (or missing)"
                            )
                        }
            tid_raw = call.args.get("task_id")
            if tid_raw is None:
                task_id = session_id
            else:
                try:
                    task_id = int(tid_raw)
                except (TypeError, ValueError):
                    return {"error": "task_id must be integer"}
            sid = await qe.insert_knowledge_synthesis(body, refs, task_id=task_id)
            return {"synthesis_id": sid, "task_id": task_id}

        async def _knowledge_add_bound(
            call: CompletedFunctionCall,
        ) -> dict[str, Any]:
            kind = str(call.args.get("kind") or "").strip().lower()
            if kind not in ("rss", "web"):
                return {"error": "kind must be rss or web"}
            base_url = str(call.args.get("base_url") or "").strip()
            label = call.args.get("label")
            label_s = str(label).strip() if label is not None else None
            if label_s == "":
                label_s = None
            try:
                validate_knowledge_feed_url(base_url, host_allowlist=hosts)
            except ValueError as e:
                return {"error": str(e)}
            kid = await qe.insert_knowledge_source(
                "rss" if kind == "rss" else "web",
                label=label_s,
                base_url=base_url,
                mission_id=knowledge_mission_scope,
            )
            return {"source_id": kid, "kind": kind, "base_url": base_url}

        async def _knowledge_record_market_edge_bound(
            call: CompletedFunctionCall,
        ) -> dict[str, Any]:
            try:
                knowledge_id = int(call.args.get("knowledge_id"))
            except (TypeError, ValueError):
                return {"error": "knowledge_id must be integer"}
            metric_name = str(call.args.get("metric_name") or "").strip()
            if not metric_name:
                return {"error": "metric_name required"}
            try:
                metric_value = float(call.args.get("metric_value"))
            except (TypeError, ValueError):
                return {"error": "metric_value must be numeric"}
            recorded_at_raw = call.args.get("recorded_at")
            recorded_at = (
                str(recorded_at_raw).strip() if recorded_at_raw is not None else None
            )
            if recorded_at == "":
                recorded_at = None
            api_source_raw = call.args.get("api_source")
            api_source = (
                str(api_source_raw).strip() if api_source_raw is not None else ""
            )
            notes_raw = call.args.get("causality_notes")
            causality_notes = str(notes_raw).strip() if notes_raw is not None else ""

            if knowledge_mission_scope is not None:
                try:
                    await qe.get_knowledge_item(
                        knowledge_id, mission_scope=knowledge_mission_scope
                    )
                except LookupError:
                    return {
                        "error": (
                            "knowledge_id is not visible for this mission "
                            "(or missing)"
                        )
                    }
            try:
                metric_id = await qe.insert_market_metric(
                    metric_name,
                    metric_value,
                    recorded_at=recorded_at,
                    api_source=api_source,
                )
                edge_id = await qe.insert_synthesis_edge(
                    knowledge_id,
                    metric_id,
                    causality_notes=causality_notes,
                )
            except LookupError as e:
                return {"error": str(e)}
            except Exception as e:
                return {"error": str(e)}
            return {
                "knowledge_id": knowledge_id,
                "metric_id": metric_id,
                "edge_id": edge_id,
            }

        async def _knowledge_record_entity_bound(
            call: CompletedFunctionCall,
        ) -> dict[str, Any]:
            name = str(call.args.get("name") or "").strip()
            etype = str(call.args.get("type") or "").strip().lower()
            if not name or not etype:
                return {"error": "name and type are required"}
            aliases_raw = call.args.get("aliases")
            aliases: list[str] | None = None
            if isinstance(aliases_raw, list):
                aliases = [str(a).strip() for a in aliases_raw if str(a).strip()]
            external_ids_raw = call.args.get("external_ids")
            external_ids: dict[str, str] | None = None
            if isinstance(external_ids_raw, dict):
                external_ids = {
                    str(k): str(v)
                    for k, v in external_ids_raw.items()
                    if str(k).strip()
                }
            payload = call.args.get("payload")
            payload_json = payload if isinstance(payload, dict) else None
            out = await qe.upsert_entity(
                type=etype,
                name=name,
                aliases=aliases,
                external_ids=external_ids,
                payload_json=payload_json,
                mission_id=knowledge_mission_scope,
            )
            return out

        async def _knowledge_record_edge_bound(
            call: CompletedFunctionCall,
        ) -> dict[str, Any]:
            try:
                src_entity_id = int(call.args.get("src_entity_id"))
                dst_entity_id = int(call.args.get("dst_entity_id"))
            except (TypeError, ValueError):
                return {"error": "src_entity_id and dst_entity_id must be integers"}
            if enrich_subject_entity_id is not None and src_entity_id != int(
                enrich_subject_entity_id
            ):
                return {"error": "src_entity_id must match enrich subject"}
            edge_type = str(call.args.get("edge_type") or "").strip().lower()
            if not edge_type:
                return {"error": "edge_type required"}
            try:
                confidence = float(call.args.get("confidence"))
            except (TypeError, ValueError):
                return {"error": "confidence must be numeric"}
            if confidence < 0 or confidence > 1:
                return {"error": "confidence must be between 0 and 1"}
            evidence_raw = call.args.get("evidence_item_ids")
            if not isinstance(evidence_raw, list):
                return {"error": "evidence_item_ids must be a list"}
            evidence_item_ids: list[int] = []
            for x in evidence_raw:
                try:
                    evidence_item_ids.append(int(x))
                except (TypeError, ValueError):
                    return {"error": "evidence_item_ids must contain integers"}
            if knowledge_mission_scope is not None and evidence_item_ids:
                for kid in evidence_item_ids:
                    try:
                        await qe.get_knowledge_item(
                            kid, mission_scope=knowledge_mission_scope
                        )
                    except LookupError:
                        return {
                            "error": (
                                f"evidence_item_ids: knowledge id={kid} is not visible "
                                "for this mission (or missing)"
                            )
                        }
            is_hypothesis = bool(call.args.get("is_hypothesis", False))
            if not is_hypothesis and len(evidence_item_ids) == 0:
                return {"error": "evidence_item_ids required for non-hypothesis edges"}
            source_url_val: str | None = None
            if not is_hypothesis:
                raw_su = call.args.get("source_url")
                su_s = str(raw_su).strip() if raw_su is not None else ""
                if not su_s:
                    return {
                        "error": (
                            "source_url is required for non-hypothesis edges "
                            "(canonical https page URL for GATE provenance)"
                        )
                    }
                norm, v_err = validate_https_url(su_s)
                if v_err or norm is None:
                    return {
                        "error": (
                            f"source_url must be a valid https URL for fact edges: {v_err or 'invalid'}"
                        )
                    }
                source_url_val = norm
            status_raw = call.args.get("status")
            status = str(status_raw).strip().lower() if status_raw is not None else "active"
            superseded_by_raw = call.args.get("superseded_by")
            superseded_by = None
            if superseded_by_raw is not None:
                try:
                    superseded_by = int(superseded_by_raw)
                except (TypeError, ValueError):
                    return {"error": "superseded_by must be integer"}
            if confidence < 0.45:
                return {"error": "confidence below minimum threshold"}
            if confidence < 0.60 and len(evidence_item_ids) < 2:
                return {"error": "confidence < 0.60 requires at least 2 evidence items"}
            edge_id = await qe.insert_graph_edge(
                src_entity_id=src_entity_id,
                dst_entity_id=dst_entity_id,
                edge_type=edge_type,
                confidence=confidence,
                status=status,
                superseded_by=superseded_by,
                source_url=source_url_val,
            )
            linked = 0
            for kid in evidence_item_ids:
                rec = await qe.link_edge_evidence_upsert(edge_id=edge_id, knowledge_id=kid)
                if rec.get("upserted") is True:
                    linked += 1
            return {"edge_id": edge_id, "status": status, "evidence_linked": linked}

        async def _knowledge_link_evidence_bound(
            call: CompletedFunctionCall,
        ) -> dict[str, Any]:
            try:
                edge_id = int(call.args.get("edge_id"))
                knowledge_id = int(call.args.get("knowledge_id"))
            except (TypeError, ValueError):
                return {"error": "edge_id and knowledge_id must be integers"}
            if knowledge_mission_scope is not None:
                try:
                    await qe.get_knowledge_item(
                        knowledge_id, mission_scope=knowledge_mission_scope
                    )
                except LookupError:
                    return {
                        "error": (
                            "knowledge_id is not visible for this mission "
                            "(or missing)"
                        )
                    }
            quote_span = call.args.get("quote_span")
            if quote_span is not None and not isinstance(quote_span, dict):
                return {"error": "quote_span must be an object"}
            rec = await qe.link_edge_evidence_upsert(
                edge_id=edge_id,
                knowledge_id=knowledge_id,
                span_json=quote_span if isinstance(quote_span, dict) else None,
            )
            return {
                "edge_evidence_id": rec["edge_evidence_id"],
                "edge_id": edge_id,
                "knowledge_id": knowledge_id,
                "upserted": rec["upserted"],
            }

        async def _knowledge_graph_context_bound(
            call: CompletedFunctionCall,
        ) -> dict[str, Any]:
            try:
                eid_arg = int(call.args.get("entity_id"))
            except (TypeError, ValueError):
                return {"error": "entity_id must be an integer"}
            if enrich_subject_entity_id is not None and eid_arg != int(
                enrich_subject_entity_id
            ):
                return {"error": "entity_id must match enrich subject"}
            pack = await qe.load_subject_subgraph_context_pack(
                eid_arg, mission_scope=knowledge_mission_scope
            )
            if pack.get("subject") is None:
                return {"error": f"unknown entity_id={eid_arg}"}
            return pack

        knowledge_search_fn = _knowledge_search_bound
        knowledge_record_fn = _knowledge_record_bound
        knowledge_record_market_edge_fn = _knowledge_record_market_edge_bound
        knowledge_add_fn = _knowledge_add_bound
        knowledge_record_entity_fn = _knowledge_record_entity_bound
        knowledge_record_edge_fn = _knowledge_record_edge_bound
        knowledge_link_evidence_fn = _knowledge_link_evidence_bound
        knowledge_graph_context_fn = _knowledge_graph_context_bound

        if knowledge_tool_subset is not None:
            if "search_knowledge" not in knowledge_tool_subset:
                knowledge_search_fn = None
            if "record_synthesis" not in knowledge_tool_subset:
                knowledge_record_fn = None
            if "record_market_edge" not in knowledge_tool_subset:
                knowledge_record_market_edge_fn = None
            if "add_knowledge_source" not in knowledge_tool_subset:
                knowledge_add_fn = None
            if "record_entity" not in knowledge_tool_subset:
                knowledge_record_entity_fn = None
            if "record_edge" not in knowledge_tool_subset:
                knowledge_record_edge_fn = None
            if "link_evidence" not in knowledge_tool_subset:
                knowledge_link_evidence_fn = None
            if "get_entity_graph_context" not in knowledge_tool_subset:
                knowledge_graph_context_fn = None

    async def _workflow_status_bound(
        call: CompletedFunctionCall,
    ) -> dict[str, Any]:
        raw = call.args.get("workflow_id")
        try:
            wf_id = int(raw)
        except (TypeError, ValueError):
            return {"error": "workflow_id must be integer"}
        return await get_workflow_status_via_tool(qe, workflow_id=wf_id)

    wf_enqueue_h = None
    wf_status_h = _workflow_status_bound if include_workflow_tools else None

    mot_settings = motor_settings
    mot_slug = (chat_mission_slug or "").strip() or None

    async def _run_skill_bound(call: CompletedFunctionCall) -> dict[str, Any]:
        if mot_settings is None:
            return {"error": "run_skill not configured"}
        from ada.motor import MotorRequest, execute

        raw_params = call.args.get("params_json")
        params: dict[str, Any] = {}
        if raw_params is not None:
            if isinstance(raw_params, str):
                try:
                    params = json.loads(raw_params)
                except json.JSONDecodeError as e:
                    return {"error": f"params_json invalid: {e}"}
            elif isinstance(raw_params, dict):
                params = raw_params
            else:
                return {"error": "params_json must be string or object"}
        slug = str(call.args.get("mission_slug") or mot_slug or "").strip() or None
        req = MotorRequest(
            layer="skill",
            id=str(call.args.get("skill_id") or "").strip(),
            params=params,
            mission_slug=slug,
            session_id=session_id,
            approved=bool(call.args.get("approved")),
        )
        result = await execute(req, settings=mot_settings, qe=qe)
        if result.pending_approval:
            return {
                "pending_approval": True,
                "error": result.error,
                "skill_id": req.id,
            }
        if not result.ok:
            return {"error": result.error or "motor failed"}
        return {"ok": True, "output": result.output, "action_log_id": result.action_log_id}

    async def _propose_programme_bound(call: CompletedFunctionCall) -> dict[str, Any]:
        from ada.programme.propose import propose_packet

        raw = call.args.get("packet_json")
        if raw is None:
            return {"error": "packet_json required"}
        if isinstance(raw, dict):
            return propose_packet(raw)
        return propose_packet(str(raw))

    async def _apply_programme_bound(call: CompletedFunctionCall) -> dict[str, Any]:
        from ada.programme.apply import confirm_and_apply
        from ada.programme.packet import validate_packet_dict

        if mot_settings is None:
            return {"error": "apply_programme not configured"}
        approved = bool(call.args.get("approved"))
        raw = call.args.get("packet_json")
        if raw is None:
            return {"error": "packet_json required"}
        if isinstance(raw, str):
            import json

            try:
                data = json.loads(raw)
            except json.JSONDecodeError as e:
                return {"error": f"invalid JSON: {e}"}
        elif isinstance(raw, dict):
            data = raw
        else:
            return {"error": "packet_json must be string or object"}
        try:
            packet = validate_packet_dict(data)
        except Exception as e:
            return {"error": str(e)}
        return await confirm_and_apply(
            qe,
            mot_settings,
            packet,
            approved=approved,
            session_id=session_id,
        )

    run_skill_h = _run_skill_bound if include_run_skill else None
    propose_h = _propose_programme_bound if include_propose_programme else None
    apply_h = _apply_programme_bound if include_apply_programme else None

    last_err: Exception | None = None
    for attempt in range(max_retries + 1):
        tools_were_persisted = [False]

        async def _token_usage_bound() -> dict[str, Any]:
            return await qe.get_session_token_usage(session_id)

        async def _web_sources_list_bound(lim: int) -> list[dict[str, Any]]:
            return await qe.list_web_sources(session_id, limit=lim)

        executor = StreamingToolExecutor(
            allowlist_exact=eff_shell,
            max_output_bytes=shell_max_output_bytes,
            timeout_sec=shell_timeout_sec,
            memory=memory,
            plan_hooks=plan_hooks,
            token_usage=_token_usage_bound,
            file_config=eff_file_cfg,
            web=eff_web_cfg,
            web_sources_reader=_web_sources_list_bound if eff_ws_list else None,
            goal_recall_reader=goal_recall_reader,
            on_file_guard_violation=None if wf_strict else on_file_guard_violation,
            knowledge_search=knowledge_search_fn,
            knowledge_record_synthesis=knowledge_record_fn,
            knowledge_record_market_edge=knowledge_record_market_edge_fn,
            knowledge_add_source=knowledge_add_fn,
            knowledge_record_entity=knowledge_record_entity_fn,
            knowledge_record_edge=knowledge_record_edge_fn,
            knowledge_link_evidence=knowledge_link_evidence_fn,
            knowledge_graph_context=knowledge_graph_context_fn,
            dispatch_allowlist=dispatch_allowlist,
            workflow_enqueue=wf_enqueue_h,
            workflow_get_status=wf_status_h,
            gsc_read=gsc_read_fn,
            mission_control_snapshot=mission_control_snapshot_fn,
            run_skill_handler=run_skill_h,
            propose_programme_handler=propose_h,
            apply_programme_handler=apply_h,
        )
        try:
            return await _agentic_loop(
                qe,
                session_id=session_id,
                user_parent_uuid=user_uuid,
                system_instruction=system_instruction,
                api_key=api_key,
                model=model,
                gemini_tool=gemini_tool,
                on_delta=on_delta,
                legs_cap=legs_cap,
                shell_allowlist=eff_shell,
                executor=executor,
                tools_were_persisted=tools_were_persisted,
                stream_chunk_idle_timeout_sec=stream_chunk_idle_timeout_sec,
                stream_leg_max_wall_sec=stream_leg_max_wall_sec,
                rewire_after_tombstone=rewire_after_tombstone,
                plan_tools_configured=plan_hooks is not None,
                file_tools_configured=eff_file_cfg is not None,
                web_search_configured=eff_web_cfg is not None
                and bool(eff_web_cfg.serper_api_key),
                web_fetch_configured=eff_web_cfg is not None,
                web_sources_list_configured=eff_ws_list,
                goal_recall_configured=goal_recall_reader is not None,
                gsc_read_configured=gsc_read_fn is not None,
                knowledge_tools_configured=need_knowledge,
                workflow_tools_configured=include_workflow_tools,
                max_session_tokens=max_session_tokens,
                debug_stream=dbg,
                turn_harness_appendix=turn_harness_appendix,
            )
        except SessionTokenLimitExceeded:
            executor.discard()
            raise
        except Exception as e:
            last_err = e
            executor.discard()
            await qe.state_set("turn.fallback_generation", str(attempt + 1))
            if tools_were_persisted[0]:
                break
            if attempt >= max_retries:
                break
            await asyncio.sleep(0.25 * (attempt + 1))
    assert last_err is not None
    raise last_err


async def _agentic_loop(
    qe: QueryEngine,
    *,
    session_id: int,
    user_parent_uuid: str,
    system_instruction: str,
    api_key: str,
    model: str,
    gemini_tool: Any,
    on_delta: Callable[[str], Coroutine[Any, Any, None]] | None,
    legs_cap: int,
    shell_allowlist: frozenset[str],
    executor: StreamingToolExecutor,
    tools_were_persisted: list[bool],
    stream_chunk_idle_timeout_sec: float | None,
    stream_leg_max_wall_sec: float | None,
    rewire_after_tombstone: bool,
    plan_tools_configured: bool,
    file_tools_configured: bool,
    web_search_configured: bool,
    web_fetch_configured: bool,
    web_sources_list_configured: bool,
    goal_recall_configured: bool,
    gsc_read_configured: bool,
    knowledge_tools_configured: bool,
    workflow_tools_configured: bool,
    max_session_tokens: int,
    debug_stream: bool,
    turn_harness_appendix: str | None = None,
) -> str:
    parent = user_parent_uuid

    async def _gemini_transient_retry_log(payload: dict[str, Any]) -> None:
        await qe.append_action_log(
            "gemini_stream_transient_retry",
            payload,
            session_id=session_id,
        )

    for _ in range(legs_cap):
        tool_rows_this_leg: list[str] = []
        leg: Any = None
        assistant_uuid: str | None = None
        for empty_try in range(_EMPTY_MODEL_STREAM_RETRIES):
            chain = await qe.load_chain_for_api(session_id)
            gemini_contents = chain_rows_to_contents(chain)
            if turn_harness_appendix:
                gemini_contents = apply_turn_harness_appendix_to_contents(
                    gemini_contents, turn_harness_appendix
                )
            assistant_uuid = await qe.persist_assistant_begin(session_id, parent)

            async def _td(s: str) -> None:
                if on_delta:
                    await on_delta(s)

            try:
                leg = await stream_one_model_leg(
                    api_key=api_key,
                    model=model,
                    system_instruction=system_instruction,
                    contents=gemini_contents,
                    tool=gemini_tool,
                    on_text_delta=_td if on_delta else None,
                    chunk_idle_timeout_sec=stream_chunk_idle_timeout_sec,
                    leg_max_wall_sec=stream_leg_max_wall_sec,
                    debug_stream=debug_stream,
                    on_transient_gemini_retry=_gemini_transient_retry_log,
                )
            except asyncio.CancelledError:
                await qe.tombstone(
                    [assistant_uuid, *tool_rows_this_leg],
                    session_id,
                    rewire_orphans=rewire_after_tombstone,
                )
                raise
            except Exception:
                await qe.tombstone(
                    [assistant_uuid, *tool_rows_this_leg],
                    session_id,
                    rewire_orphans=rewire_after_tombstone,
                )
                raise

            if leg.function_calls or (leg.text or "").strip():
                break

            log_stream(
                debug_stream,
                "orchestrator",
                "empty_model_output",
                f"finish_reason={leg.finish_reason!r}",
                f"usage={leg.usage!r}",
                f"function_calls={leg.function_calls!r}",
                f"text_len={len(leg.text)}",
            )
            log.info(
                "orchestrator: empty text from model, retrying stream (attempt %s/%s, finish=%r)",
                empty_try + 1,
                _EMPTY_MODEL_STREAM_RETRIES,
                leg.finish_reason,
            )
            await qe.tombstone(
                [assistant_uuid, *tool_rows_this_leg],
                session_id,
                rewire_orphans=rewire_after_tombstone,
            )
            assistant_uuid = None
            if empty_try < _EMPTY_MODEL_STREAM_RETRIES - 1:
                await asyncio.sleep(0.25 * (empty_try + 1))
        else:
            raise StreamFailed("empty model output after stream retries")
        if leg is None or assistant_uuid is None:
            raise StreamFailed("empty model output after stream retries")
        # Persist only after a non-empty stream (or tool call path).
        try:
            fc_payload = (
                [{"name": c.name, "args": c.args, "id": c.id} for c in leg.function_calls]
                if leg.function_calls
                else None
            )
            meta: dict[str, Any] = {
                "model": model,
                "finish_reason": leg.finish_reason,
                "usage": leg.usage,
            }
            await qe.persist_assistant_finalize(
                assistant_uuid,
                leg.text,
                meta,
                function_calls=fc_payload,
            )
            usage_extras = json.dumps(leg.usage, default=str) if leg.usage else None
            await qe.record_usage(
                session_id,
                model=model,
                input_tokens=leg.usage.get("input_tokens")
                if isinstance(leg.usage.get("input_tokens"), int)
                else None,
                output_tokens=leg.usage.get("output_tokens")
                if isinstance(leg.usage.get("output_tokens"), int)
                else None,
                usage_extras_json=usage_extras,
            )
            usage_totals = await qe.get_session_token_usage(session_id)
            if usage_totals["total"] > max_session_tokens:
                await qe.append_action_log(
                    "session_token_limit_exceeded",
                    {
                        "message": "Session token limit exceeded",
                        "input_tokens": usage_totals["input_tokens"],
                        "output_tokens": usage_totals["output_tokens"],
                        "total": usage_totals["total"],
                        "limit": max_session_tokens,
                    },
                    session_id=session_id,
                )
                await qe.update_task(session_id, status="failed")
                raise SessionTokenLimitExceeded("Session token limit exceeded")
        except asyncio.CancelledError:
            await qe.tombstone(
                [assistant_uuid, *tool_rows_this_leg],
                session_id,
                rewire_orphans=rewire_after_tombstone,
            )
            raise
        except SessionTokenLimitExceeded:
            raise
        except Exception:
            await qe.tombstone(
                [assistant_uuid, *tool_rows_this_leg],
                session_id,
                rewire_orphans=rewire_after_tombstone,
            )
            raise

        if not leg.function_calls:
            await qe.state_set("session.active_model", model)
            if leg.finish_reason:
                await qe.state_set("session.last_finish_reason", leg.finish_reason)
            return leg.text

        needs_shell = any(
            c.name == "run_allowlisted_shell" for c in leg.function_calls
        )
        if needs_shell and not shell_allowlist:
            raise StreamFailed("model requested shell but allowlist is empty")

        needs_plan = any(
            c.name in ("read_task_plan", "write_task_plan")
            for c in leg.function_calls
        )
        if needs_plan and not plan_tools_configured:
            raise StreamFailed(
                "model requested plan tools but plan tools are not configured"
            )

        needs_file = any(
            c.name
            in (
                "read_workspace_file",
                "write_workspace_file",
                "list_workspace_directory",
            )
            for c in leg.function_calls
        )
        if needs_file and not file_tools_configured:
            raise StreamFailed(
                "model requested file tools but file tools are not configured"
            )

        needs_web_search = any(c.name == "web_search" for c in leg.function_calls)
        if needs_web_search and not web_search_configured:
            raise StreamFailed(
                "model requested web_search but web search is not configured"
            )

        needs_web_fetch = any(c.name == "fetch_url_text" for c in leg.function_calls)
        if needs_web_fetch and not web_fetch_configured:
            raise StreamFailed(
                "model requested fetch_url_text but web fetch is not configured"
            )

        needs_ws_list = any(
            c.name == "list_session_web_sources" for c in leg.function_calls
        )
        if needs_ws_list and not web_sources_list_configured:
            raise StreamFailed(
                "model requested list_session_web_sources but it is not configured"
            )

        needs_goal_recall = any(
            c.name == "read_goal_task_view" for c in leg.function_calls
        )
        if needs_goal_recall and not goal_recall_configured:
            raise StreamFailed(
                "model requested read_goal_task_view but it is not configured"
            )
        needs_gsc_read = any(
            c.name == "get_gsc_opportunities" for c in leg.function_calls
        )
        if needs_gsc_read and not gsc_read_configured:
            raise StreamFailed(
                "model requested get_gsc_opportunities but it is not configured"
            )

        needs_workflow_tool = any(
            c.name == "get_workflow_status" for c in leg.function_calls
        )
        if needs_workflow_tool and not workflow_tools_configured:
            raise StreamFailed(
                "model requested workflow tools but they are not configured"
            )

        needs_knowledge = any(
            c.name
            in (
                "search_knowledge",
                "get_entity_graph_context",
                "record_synthesis",
                "record_market_edge",
                "add_knowledge_source",
                "record_entity",
                "record_edge",
                "link_evidence",
            )
            for c in leg.function_calls
        )
        if needs_knowledge and not knowledge_tools_configured:
            raise StreamFailed(
                "model requested knowledge tools but knowledge tools are not configured"
            )

        results = await executor.run_ordered(leg.function_calls)
        for tr in results:
            tid = await qe.persist_tool_result(
                session_id,
                parent_assistant_uuid=assistant_uuid,
                name=tr.call.name,
                tool_call_id=tr.call.id,
                response=tr.response,
            )
            tool_rows_this_leg.append(tid)
            await qe.record_web_tool_artifacts(
                session_id,
                tr.call.name,
                tr.call.args,
                tr.response,
            )
        tools_were_persisted[0] = True

        head = await qe.chain_head_uuid(session_id)
        if not head:
            raise StreamFailed("chain head missing after tool results")
        parent = head

    raise StreamFailed("max tool/model legs exceeded")
