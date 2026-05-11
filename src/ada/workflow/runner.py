"""Run Phase 3 workflows for a parent goal task (daemon)."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from typing import Any

from ada.config import Settings
from ada.ingest.rss import ingest_rss_feeds
from ada.orchestrator import orchestrate_turn
from ada.analytics.keyword_select import select_keyword_cluster
from ada.publish.draft import run_publish_draft
from ada.publish.keyword_workflow import provision_keyword_stub_entity
from ada.publish.facts import count_unique_local_facts
from ada.workflow.publish_enrich_step import run_publish_entity_enrich
from ada.workflow.templates import validate_target_keyword_cluster
from ada.publish.page_schema_v1 import PageJsonV1
from ada.publish.s3_publish import CSV_UTF8, deploy_page_and_manifest, put_s3_object_bytes
from ada.publish.wordpress_csv import (
    page_to_wordpress_row,
    resolve_focus_keyword,
    wordpress_csv_single_row_bytes,
    wordpress_csv_s3_object_key,
)
from ada.query_engine import QueryEngine
from ada.tools.registry import KNOWLEDGE_TOOLS_EXTRACT, KNOWLEDGE_TOOLS_SYNTHESIZE
log = logging.getLogger("ada.workflow.runner")


def _publish_delivery_mode(merged: dict[str, Any]) -> str:
    d = merged.get("delivery")
    if not isinstance(d, dict):
        return "isr_s3"
    m = d.get("mode")
    if isinstance(m, str) and m.strip().lower() in ("isr_s3", "none", "wordpress_csv_s3"):
        return m.strip().lower()
    return "isr_s3"


async def _resolve_workflow_keyword_target(
    qe: QueryEngine, merged_params: dict[str, Any]
) -> tuple[str | None, dict[str, Any] | None, str | None]:
    raw = merged_params.get("target_keyword_cluster")
    if raw is not None:
        return (
            validate_target_keyword_cluster(raw),
            merged_params.get("keyword_source")
            if isinstance(merged_params.get("keyword_source"), dict)
            else None,
            None,
        )
    src = merged_params.get("keyword_source")
    if not isinstance(src, dict):
        return None, None, "keyword_missing"
    if str(src.get("kind") or "").strip().lower() != "gsc":
        return None, src, "keyword_missing"
    site = str(src.get("site") or "").strip()
    start = str(src.get("start_date") or "").strip()
    end = str(src.get("end_date") or "").strip()
    if not (site and start and end):
        return None, src, "gsc_window_missing"
    pick = await select_keyword_cluster(
        qe, site=site, start_date=start, end_date=end, limit=20
    )
    return pick.keyword_cluster, pick.keyword_source, pick.fallback_reason


def _build_extract_user_text(
    *,
    goal_text: str,
    item_ids: list[int],
    params: dict[str, Any],
) -> str:
    lines = [
        "[WORKFLOW_STEP:EXTRACT]",
        f"Parent goal: {goal_text}",
        "Extract graph-lite entities and edges grounded in the following knowledge_items ids.",
        f"item_ids: {json.dumps(item_ids)}",
        "Use only record_entity, record_edge, and link_evidence. Cite evidence_item_ids from these items.",
        "For each non-hypothesis record_edge, set source_url to a canonical https URL "
        "(prefer the article link from the cited knowledge item payload, e.g. link/title URL).",
        f"Extra params: {json.dumps(params, ensure_ascii=False)}",
    ]
    return "\n".join(lines)


def _build_synthesize_user_text(
    *,
    goal_text: str,
    params: dict[str, Any],
    prior_summary: str,
) -> str:
    topic = str(params.get("topic") or "Summarize recent ingested knowledge.").strip()
    lines = [
        "[WORKFLOW_STEP:SYNTHESIZE]",
        f"Parent goal: {goal_text}",
        f"Topic: {topic}",
        "Use search_knowledge then record_synthesis with ref_item_ids from search results.",
        f"Prior step summary: {prior_summary}",
    ]
    return "\n".join(lines)


async def run_workflow_for_parent_task(
    qe: QueryEngine,
    *,
    settings: Settings,
    parent_task_id: int,
    goal: str,
    system_instruction: str,
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
) -> str:
    """
    Execute workflow steps for workflows.parent_task_id == parent_task_id.
    Caller must verify a workflow row exists for this task.
    """
    wf = await qe.get_workflow_by_parent_task_id(parent_task_id)
    if wf is None:
        raise RuntimeError("run_workflow_for_parent_task called without workflow row")

    wf_id = int(wf["id"])
    await qe.update_workflow_row(wf_id, status="running")
    steps = await qe.list_workflow_steps(wf_id)
    params = wf.get("params_json") if isinstance(wf.get("params_json"), dict) else {}
    wf_mid = wf.get("mission_id")
    wf_mission_scope = int(wf_mid) if wf_mid is not None else None
    prior_bits: list[str] = []
    last_final = ""
    draft_page_dict: dict[str, Any] | None = None
    draft_output_json: dict[str, Any] | None = None
    draft_merged_for_focus: dict[str, Any] | None = None

    for st in steps:
        sid = int(st["id"])
        stype = str(st["step_type"]).upper()
        if str(st["status"]) == "completed":
            if stype == "DRAFT":
                oj = st.get("output_json") or {}
                if isinstance(oj, dict):
                    draft_output_json = dict(oj)
                    p = oj.get("page")
                    if isinstance(p, dict):
                        draft_page_dict = p
                merged_d = {**params, **(st.get("input_json") or {})}
                draft_merged_for_focus = merged_d
            prior_bits.append(f"{stype}: skipped (already completed)")
            continue
        await qe.update_workflow_step_row(sid, status="running", increment_attempt=True)
        try:
            if stype == "FETCH":
                res = await ingest_rss_feeds(
                    qe, settings=settings, ingest_mission_id=wf_mission_scope
                )
                out = {
                    "feeds_attempted": res.feeds_attempted,
                    "feeds_ok": res.feeds_ok,
                    "items_inserted": res.items_inserted,
                    "items_deduped": res.items_deduped,
                    "errors": res.errors[:12],
                }
                await qe.update_workflow_step_row(
                    sid, status="completed", output_json=out, error=""
                )
                prior_bits.append(f"FETCH: {out}")
            elif stype == "EXTRACT":
                inp = st.get("input_json") or {}
                lim = int(inp.get("recent_item_limit") or 40)
                item_ids = await qe.list_recent_knowledge_item_ids(
                    limit=lim, mission_scope=wf_mission_scope
                )
                user_txt = _build_extract_user_text(
                    goal_text=str(wf.get("goal_text") or goal),
                    item_ids=item_ids,
                    params=params,
                )
                final = await orchestrate_turn(
                    qe,
                    session_id=parent_task_id,
                    user_text=user_txt,
                    system_instruction=system_instruction,
                    api_key=settings.gemini_api_key,
                    model=settings.gemini_model,
                    shell_allowlist=frozenset(),
                    max_tool_rounds=max_tool_rounds,
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
                    knowledge_tool_subset=KNOWLEDGE_TOOLS_EXTRACT,
                    workflow_strict=True,
                    include_workflow_tools=False,
                    workflow_max_steps=None,
                )
                await qe.update_workflow_step_row(
                    sid,
                    status="completed",
                    output_json={"assistant_excerpt": final[:4000]},
                    error="",
                )
                prior_bits.append(f"EXTRACT: model completed ({len(final)} chars)")
                last_final = final
            elif stype == "ENRICH":
                merged = {**params, **(st.get("input_json") or {})}
                wf_kind = str(wf.get("kind") or "").strip()
                if wf_kind == "publish_keyword_v1" and merged.get("entity_id") is None:
                    eid_stub = await provision_keyword_stub_entity(qe, merged)
                    await qe.merge_workflow_params_json(
                        wf_id, {"entity_id": eid_stub, "keyword_stub": True}
                    )
                    params["entity_id"] = eid_stub
                    params["keyword_stub"] = True
                    merged = {**params, **(st.get("input_json") or {})}
                eid = merged.get("entity_id")
                if eid is None:
                    raise ValueError("ENRICH step requires entity_id in params_json")
                eid_int = int(eid)
                ent = await qe.get_entity_by_id(eid_int)
                if ent is None:
                    raise ValueError(f"ENRICH: unknown entity_id={eid_int}")
                out = await run_publish_entity_enrich(
                    qe,
                    settings,
                    entity_id=eid_int,
                    entity=ent,
                    merged_params=merged,
                    goal_text=str(wf.get("goal_text") or goal),
                    system_instruction=system_instruction,
                    session_id=parent_task_id,
                    max_tool_rounds=max_tool_rounds,
                    shell_max_output_bytes=shell_max_output_bytes,
                    shell_timeout_sec=shell_timeout_sec,
                    stream_chunk_idle_timeout_sec=stream_chunk_idle_timeout_sec,
                    stream_leg_max_wall_sec=stream_leg_max_wall_sec,
                    rewire_after_tombstone=rewire_after_tombstone,
                    max_session_tokens=max_session_tokens,
                    debug_stream=debug_stream,
                    knowledge_feed_host_allowlist=knowledge_feed_host_allowlist,
                    knowledge_embeddings_enabled=knowledge_embeddings_enabled,
                    knowledge_embedding_model=knowledge_embedding_model,
                    knowledge_embedding_dim=knowledge_embedding_dim,
                    knowledge_embedding_min_cosine=knowledge_embedding_min_cosine,
                    knowledge_tool_max_results=knowledge_tool_max_results,
                    knowledge_tool_excerpt_chars=knowledge_tool_excerpt_chars,
                    enrich_tool_rounds_cap=None,
                )
                await qe.update_workflow_step_row(
                    sid, status="completed", output_json=out, error=""
                )
                prior_bits.append(f"ENRICH: {out}")
            elif stype == "GATE":
                merged = {**params, **(st.get("input_json") or {})}
                eid = merged.get("entity_id")
                if eid is None:
                    raise ValueError("GATE step requires entity_id in params_json")
                n = await count_unique_local_facts(qe, int(eid))
                need = int(settings.ada_publish_min_unique_facts)
                if n < need:
                    raise ValueError(
                        f"GATE: unique_local_facts {n} < minimum {need} (ADA_PUBLISH_MIN_UNIQUE_FACTS)"
                    )
                gout = {"unique_local_facts": n, "min_required": need}
                await qe.update_workflow_step_row(
                    sid, status="completed", output_json=gout, error=""
                )
                prior_bits.append(f"GATE: {gout}")
            elif stype == "DRAFT":
                merged = {**params, **(st.get("input_json") or {})}
                keyword_cluster, keyword_source, fallback_reason = (
                    await _resolve_workflow_keyword_target(qe, merged)
                )
                if keyword_cluster:
                    merged["target_keyword_cluster"] = keyword_cluster
                    if keyword_source is not None:
                        merged["keyword_source"] = keyword_source
                out = await run_publish_draft(
                    qe,
                    settings,
                    goal_text=str(wf.get("goal_text") or goal),
                    params=merged,
                )
                out["keyword_cluster_used"] = bool(keyword_cluster)
                out["keyword_source"] = keyword_source
                out["fallback_reason"] = fallback_reason
                draft_output_json = dict(out)
                draft_merged_for_focus = dict(merged)
                draft_page_dict = out.get("page")
                if not isinstance(draft_page_dict, dict):
                    raise ValueError("DRAFT: missing page in output")
                if settings.require_approval_for_publish:
                    draft_hash = hashlib.sha256(
                        json.dumps(draft_page_dict, sort_keys=True, ensure_ascii=False).encode("utf-8")
                    ).hexdigest()[:24]
                    out["publish_deploy_artifact_ref"] = f"workflow:{wf_id}:draft:{draft_hash}"
                await qe.update_workflow_step_row(
                    sid, status="completed", output_json=out, error=""
                )
                await qe.append_action_log(
                    "publish_keyword_targeting",
                    {
                        "workflow_id": wf_id,
                        "step_id": sid,
                        "keyword_cluster_used": bool(keyword_cluster),
                        "target_keyword_cluster": keyword_cluster,
                        "keyword_source": keyword_source,
                        "fallback_reason": fallback_reason,
                    },
                    session_id=parent_task_id,
                )
                prior_bits.append("DRAFT: PageJsonV1 ok")
            elif stype == "DEPLOY":
                merged = {**params, **(st.get("input_json") or {})}
                if draft_page_dict is None:
                    raise ValueError("DEPLOY: no DRAFT page in memory (run DRAFT first)")
                if settings.require_approval_for_publish:
                    draft_hash = hashlib.sha256(
                        json.dumps(draft_page_dict, sort_keys=True, ensure_ascii=False).encode("utf-8")
                    ).hexdigest()[:24]
                    artifact_ref = f"workflow:{wf_id}:draft:{draft_hash}"
                    rec = await qe.get_approval_record(
                        artifact_type="publish_deploy",
                        artifact_ref=artifact_ref,
                    )
                    if rec is None or rec.get("status") != "approved":
                        await qe.append_action_log(
                            "publish_deploy_blocked_no_approval",
                            {
                                "workflow_id": wf_id,
                                "artifact_type": "publish_deploy",
                                "artifact_ref": artifact_ref,
                                "target_keyword_cluster": merged.get(
                                    "target_keyword_cluster"
                                ),
                                "keyword_source": merged.get("keyword_source"),
                            },
                            session_id=parent_task_id,
                        )
                        raise ValueError(
                            "DEPLOY blocked: approval status=approved required for publish_deploy artifact"
                        )
                page = PageJsonV1.model_validate(draft_page_dict)
                nich = str(merged.get("niche") or "").strip()
                pr = str(merged.get("project_id") or "").strip()
                camp = str(merged.get("campaign_id") or "").strip()
                if not (nich and pr and camp):
                    raise ValueError("DEPLOY requires project_id, campaign_id, niche in params")
                mode = _publish_delivery_mode(merged)
                if mode == "none":
                    await qe.append_action_log(
                        "publish_delivery_skipped",
                        {
                            "workflow_id": wf_id,
                            "step_id": sid,
                            "delivery": "none",
                        },
                        session_id=parent_task_id,
                    )
                    dep_none: dict[str, Any] = {
                        "delivery": "none",
                        "skipped_remote": True,
                    }
                    await qe.update_workflow_step_row(
                        sid, status="completed", output_json=dep_none, error=""
                    )
                    prior_bits.append("DEPLOY: skipped remote (delivery none)")
                elif mode == "wordpress_csv_s3":
                    dcfg = merged.get("delivery")
                    wps = (
                        dcfg.get("wordpress_csv_s3")
                        if isinstance(dcfg, dict) and isinstance(dcfg.get("wordpress_csv_s3"), dict)
                        else {}
                    )
                    bucket = str(wps.get("bucket") or "").strip() or str(
                        settings.wordpress_csv_s3_bucket_default or ""
                    ).strip()
                    if not bucket:
                        raise ValueError(
                            "DEPLOY wordpress_csv_s3: bucket is required "
                            "(delivery.wordpress_csv_s3.bucket or ADA_WORDPRESS_CSV_S3_BUCKET)"
                        )
                    oj_f = draft_output_json if isinstance(draft_output_json, dict) else {}
                    sinp_f = (
                        draft_merged_for_focus
                        if isinstance(draft_merged_for_focus, dict)
                        else {}
                    )
                    focus = resolve_focus_keyword(oj_f, sinp_f, params)
                    row = page_to_wordpress_row(draft_page_dict, focus)
                    body = wordpress_csv_single_row_bytes(row)
                    ek = wps.get("key")
                    ek_str = str(ek).strip() if ek is not None else None
                    pfx = wps.get("prefix")
                    obj_key = wordpress_csv_s3_object_key(
                        slug=page.slug,
                        explicit_key=ek_str if ek_str else None,
                        prefix=str(pfx).strip() if pfx is not None else None,
                    )
                    try:
                        dep_csv = await asyncio.to_thread(
                            put_s3_object_bytes,
                            settings,
                            bucket=bucket,
                            key=obj_key,
                            body=body,
                            content_type=CSV_UTF8,
                        )
                    except Exception as e:
                        await qe.append_action_log(
                            "publish_delivery_csv_s3_failed",
                            {
                                "workflow_id": wf_id,
                                "step_id": sid,
                                "bucket": bucket,
                                "key": obj_key,
                                "error": str(e)[:2000],
                            },
                            session_id=parent_task_id,
                        )
                        raise
                    dep_out = {**dep_csv, "delivery": "wordpress_csv_s3"}
                    await qe.update_workflow_step_row(
                        sid, status="completed", output_json=dep_out, error=""
                    )
                    prior_bits.append(f"DEPLOY: wordpress_csv_s3 {dep_out}")
                else:
                    if not str(page.og_image or "").strip():
                        raise ValueError("DEPLOY: missing og_image on draft page")
                    dep = await asyncio.to_thread(
                        deploy_page_and_manifest,
                        settings,
                        page=page,
                        project_id=pr,
                        campaign_id=camp,
                        niche=nich,
                    )
                    await qe.update_workflow_step_row(
                        sid, status="completed", output_json=dep, error=""
                    )
                    prior_bits.append(f"DEPLOY: {dep}")
            elif stype == "SYNTHESIZE":
                user_txt = _build_synthesize_user_text(
                    goal_text=str(wf.get("goal_text") or goal),
                    params=params,
                    prior_summary="; ".join(prior_bits)[-6000:],
                )
                final = await orchestrate_turn(
                    qe,
                    session_id=parent_task_id,
                    user_text=user_txt,
                    system_instruction=system_instruction,
                    api_key=settings.gemini_api_key,
                    model=settings.gemini_model,
                    shell_allowlist=frozenset(),
                    max_tool_rounds=max_tool_rounds,
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
                    knowledge_tool_subset=KNOWLEDGE_TOOLS_SYNTHESIZE,
                    workflow_strict=True,
                    include_workflow_tools=False,
                    workflow_max_steps=None,
                )
                await qe.update_workflow_step_row(
                    sid,
                    status="completed",
                    output_json={"assistant_excerpt": final[:4000]},
                    error="",
                )
                prior_bits.append(f"SYNTHESIZE: model completed ({len(final)} chars)")
                last_final = final
            else:
                raise RuntimeError(f"unsupported step_type {stype!r}")
        except Exception as e:
            log.exception("workflow step failed wf=%s step=%s", wf_id, sid)
            await qe.update_workflow_step_row(
                sid, status="failed", error=str(e)[:2000]
            )
            await qe.update_workflow_row(wf_id, status="failed")
            raise

    await qe.update_workflow_row(wf_id, status="completed")
    return last_final if last_final else "\n".join(prior_bits)
