"""Prioritized matrix planner: Gemini proposes entity IDs; server validates; then enqueue."""

from __future__ import annotations

import json
import logging
from typing import Any

from google import genai
from google.genai import types

from ada.config import Settings
from ada.llm_context import build_llm_context
from ada.policy.load import load_intent_md, load_merged_policy_for
from ada.query_engine import QueryEngine

from ada.publish.matrix import PageProfileRegistry, enqueue_publish_entity_for_row

log = logging.getLogger("ada.publish.matrix_planner")


def validate_planner_entity_ids(
    *,
    body: dict[str, Any] | None,
    allowed_ids: set[int],
    cap_k: int,
) -> tuple[list[int] | None, str]:
    """Subset + dedupe in order → truncate to ``cap-K``. Fail closed when any id invalid or empty."""
    cap = max(1, min(10_000, int(cap_k)))
    if body is None or not isinstance(body, dict):
        return None, "body_not_object"
    raw = body.get("entity_ids")
    if raw is None:
        return None, "missing_entity_ids"
    if not isinstance(raw, list):
        return None, "entity_ids_not_list"
    out: list[int] = []
    seen: set[int] = set()
    for item in raw:
        if isinstance(item, bool):
            return None, "invalid_scalar"
        try:
            n = int(item)
        except (TypeError, ValueError):
            return None, "non_integral_id"
        if n <= 0:
            return None, "non_positive_id"
        if n not in allowed_ids:
            return None, f"disallowed_entity_id:{n}"
        if n in seen:
            continue
        seen.add(n)
        out.append(n)
    if not out:
        return None, "empty_entity_ids"
    trimmed = out[:cap]
    return trimmed, ""


async def propose_entity_ids_via_planner_llm(
    *,
    google_client: Any,
    model: str,
    system_instruction: str,
    candidate_summary: str,
) -> tuple[dict[str, Any] | None, str | None]:
    """Return parsed JSON dict or ``(None, raw_preview)`` on parse failure."""
    resp = await google_client.aio.models.generate_content(
        model=model,
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=candidate_summary),
                ],
            )
        ],
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            temperature=0.1,
            max_output_tokens=2048,
        ),
    )
    raw_text = (getattr(resp, "text", None) or "").strip()
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        return None, raw_text[:4000]
    if isinstance(data, dict):
        return data, None
    return None, raw_text[:4000]


def _summarize_candidates(rows: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for row in rows:
        eid = int(row["id"])
        nm = str(row.get("name") or "").strip()
        ty = str(row.get("type") or "").strip()
        cat = str(row.get("category_code") or "").strip()
        le = row.get("last_enriched_at")
        lines.append(
            f"id={eid}; type={ty}; category={cat}; last_enriched_at={le!s}; name={nm!s}"
        )
    instructions = (
        "Pick entity ids ONLY from `id=` values listed below.\n"
        'Return strictly JSON matching { "entity_ids": [ integers ] }, best priority first.'
    )
    return instructions + "\n\n### Candidates\n" + "\n".join(lines)


async def run_matrix_plan_and_enqueue(
    qe: QueryEngine,
    settings: Settings,
    *,
    project_id: str,
    campaign_id: str,
    mission_slug: str | None = None,
) -> dict[str, Any]:
    if not settings.gemini_api_key.strip():
        log.warning("matrix planner: GEMINI_API_KEY not set; cannot plan")
        await qe.append_action_log(
            "matrix_planner_blocked",
            {"reason": "missing_gemini_api_key"},
            session_id=None,
        )
        return await _fallback_or_else_empty(
            qe,
            settings,
            project_id,
            campaign_id,
            "missing_gemini_api_key",
            mission_slug=mission_slug,
        )

    merged = load_merged_policy_for(settings)
    registry = PageProfileRegistry(project_id=project_id, campaign_id=campaign_id)
    types_f = settings.ada_matrix_entity_types
    pool = int(settings.ada_matrix_max_enqueues)
    intent_txt = load_intent_md(settings.memory_dir, max_bytes=merged.intent_max_bytes)

    planner_base = """You prioritize which matrix subject entities should be published next to ISR /
pSEO. You only choose existing entity identifiers from the provided candidate list."""

    invariant = (
        "Output JSON only:\n"
        '{ "entity_ids": [ integer, ... ] }\n'
        "Requirements: IDs must repeat only from candidates; list best-first; "
        f"cap yourself to at most {merged.matrix_planner_top_k} identifiers when oversubscribed."
    )

    system_instruction = build_llm_context(
        "matrix_planner_priority",
        base=planner_base,
        invariants=invariant,
        intent_text=intent_txt,
        policy=merged,
    )

    rows = await qe.list_subjects_with_classified_category_recent_for_planner(
        entity_types=types_f,
        limit=pool,
    )

    allowed = {int(r["id"]) for r in rows}
    by_id = {int(r["id"]): r for r in rows}
    if not allowed:
        return {
            "mode": "matrix_planner",
            "dry_run": False,
            "enqueued": 0,
            "candidates": 0,
            "candidates_pool": 0,
            "skipped": "no_candidates",
            "planned_ids": [],
            "validation_error": "",
        }

    model = settings.ada_matrix_planner_model.strip() if settings.ada_matrix_planner_model else (
        settings.gemini_model
    )

    gc = genai.Client(api_key=settings.gemini_api_key)
    cand_text = _summarize_candidates(rows)
    parsed_json, decode_err_preview = await propose_entity_ids_via_planner_llm(
        google_client=gc,
        model=model,
        system_instruction=system_instruction,
        candidate_summary=cand_text,
    )

    cap_k = min(merged.matrix_planner_top_k, len(allowed))

    if parsed_json is None:
        log.warning("matrix planner: invalid planner JSON decode: %s", decode_err_preview)
        await qe.append_action_log(
            "matrix_planner_validation_failed",
            {"reason": "json_decode", "preview": decode_err_preview},
            session_id=None,
        )
        return await _fallback_or_else_empty(
            qe,
            settings,
            project_id,
            campaign_id,
            decode_err_preview or "",
            mission_slug=mission_slug,
        )

    chosen, verr = validate_planner_entity_ids(
        body=parsed_json,
        allowed_ids=allowed,
        cap_k=cap_k,
    )
    if chosen is None or verr:
        log.warning("matrix planner: validation rejected: %s body=%s", verr, parsed_json)
        await qe.append_action_log(
            "matrix_planner_validation_failed",
            {"reason": verr, "body": parsed_json},
            session_id=None,
        )
        return await _fallback_or_else_empty(
            qe,
            settings,
            project_id,
            campaign_id,
            verr,
            mission_slug=mission_slug,
        )

    enq = 0
    for eid in chosen:
        row = by_id[eid]
        r = await enqueue_publish_entity_for_row(
            qe,
            settings,
            row,
            registry=registry,
            dry_run=False,
            mission_slug=mission_slug,
        )
        if r.get("error"):
            log.warning("matrix enqueue error: %s", r)
        else:
            enq += 1

    return {
        "mode": "matrix_planner",
        "dry_run": False,
        "enqueued": enq,
        "candidates": len(rows),
        "candidates_pool": len(rows),
        "skipped": "",
        "planned_ids": chosen,
        "log": [],
    }


async def _fallback_or_else_empty(
    qe: QueryEngine,
    settings: Settings,
    project_id: str,
    campaign_id: str,
    reason: str,
    *,
    mission_slug: str | None = None,
) -> dict[str, Any]:
    from ada.publish.matrix import run_matrix_legacy_scan

    if settings.ada_matrix_planner_fallback_legacy:
        log.warning("matrix planner: falling back to legacy matrix-scan (%s)", reason)
        return await run_matrix_legacy_scan(
            qe,
            settings,
            project_id=project_id,
            campaign_id=campaign_id,
            dry_run=False,
            use_recent_order=False,
            mission_slug=mission_slug,
        )

    return {
        "mode": "matrix_planner",
        "dry_run": False,
        "enqueued": 0,
        "candidates": 0,
        "candidates_pool": 0,
        "skipped": reason or "planner_validation",
        "planned_ids": [],
        "validation_error": reason,
    }
