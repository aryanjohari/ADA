"""system_jobs handlers (workflow.start, ingest.run, tick slices, matrix)."""

from __future__ import annotations

import json
import logging
from datetime import date
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ada.config import Settings
    from ada.query_engine import QueryEngine

log = logging.getLogger("ada.jobs.handlers")


async def handle_workflow_start(
    job: dict[str, Any],
    qe: QueryEngine,
    settings: Settings,
    *,
    worker_id: str,
) -> None:
    _ = worker_id
    from ada.workflow.enqueue import enqueue_workflow_via_tool

    p = job.get("payload_json") or {}
    kind = str(p.get("kind") or "").strip()
    goal_text = str(p.get("goal_text") or "").strip()
    if not kind or not goal_text:
        raise ValueError("workflow.start requires kind and goal_text in payload_json")
    params = p.get("params")
    params_json = (
        json.dumps(params, ensure_ascii=False)
        if isinstance(params, dict)
        else str(p.get("params_json") or "{}")
    )
    out = await enqueue_workflow_via_tool(
        qe,
        kind=kind,
        goal_text=goal_text,
        params_json=params_json,
        idempotency_key=str(p["idempotency_key"]).strip()
        if p.get("idempotency_key")
        else None,
        max_steps=p.get("max_steps") or settings.ada_max_task_steps,
        require_approval=bool(p.get("require_approval", False)),
        playbook_id=str(p["playbook_id"]).strip() if p.get("playbook_id") else None,
        mission_slug=str(p["mission_slug"]).strip() if p.get("mission_slug") else None,
        source_task_id=int(p["source_task_id"]) if p.get("source_task_id") else None,
        mission_tag_id=int(p["mission_tag_id"]) if p.get("mission_tag_id") else None,
    )
    if out.get("error"):
        raise RuntimeError(str(out["error"]))


async def handle_ingest_run(
    job: dict[str, Any],
    qe: QueryEngine,
    settings: Settings,
    *,
    worker_id: str,
) -> None:
    _ = worker_id
    p = job.get("payload_json") or {}
    iid = p.get("ingest_job_id")
    if iid is None:
        raise ValueError("ingest.run requires payload_json.ingest_job_id")
    row = await qe.get_ingest_job_row(int(iid))
    if row is None:
        raise LookupError(f"no ingest_jobs row id={iid}")
    if str(row.get("status") or "") == "completed":
        log.info("ingest.run skip already completed job_id=%s", iid)
        return
    kind = str(row.get("kind") or "")
    if kind == "gsc_search_analytics_v1":
        from ada.ingest.gsc_service import ingest_gsc_search_analytics

        params = row.get("params_json") or {}
        site_url = str(params.get("site_url") or "").strip()
        sd = date.fromisoformat(str(params.get("start_date") or ""))
        ed = date.fromisoformat(str(params.get("end_date") or ""))
        dims = params.get("dimensions")
        if not isinstance(dims, list):
            dims = ["date", "query", "page", "country", "device"]
        row_limit = int(params.get("row_limit") or 25000)
        dry_run = bool(params.get("dry_run", False))
        idem = row.get("idempotency_key")
        res = await ingest_gsc_search_analytics(
            qe,
            settings,
            site_url=site_url,
            start_date=sd,
            end_date=ed,
            dimensions=[str(x) for x in dims],
            row_limit=row_limit,
            dry_run=dry_run,
            idempotency_key=str(idem) if idem else None,
        )
        if res.error:
            raise RuntimeError(res.error)
        return
    raise NotImplementedError(f"ingest.run unsupported ingest kind: {kind!r}")


async def handle_tick_gsc_keyword_publish(
    job: dict[str, Any],
    qe: QueryEngine,
    settings: Settings,
    *,
    worker_id: str,
) -> None:
    _ = worker_id
    from ada.mission_tick import _tick_gsc_keyword_publish

    p = job.get("payload_json") or {}
    slug = str(p.get("mission_slug") or "").strip()
    jid = str(p.get("tick_job_id") or "").strip()
    merged = p.get("merged")
    if not slug or not jid or not isinstance(merged, dict):
        raise ValueError("tick.gsc_keyword_publish payload incomplete")
    rc, bump = await _tick_gsc_keyword_publish(
        qe,
        settings,
        mission_slug=slug,
        job_id=jid,
        merged=merged,
        dry_run=False,
    )
    if rc != 0:
        raise RuntimeError(f"tick.gsc_keyword_publish exited rc={rc}")
    if bump and p.get("tick_state_key"):
        from ada.mission_tick import _format_last_run_iso, utc_now

        await qe.state_set(str(p["tick_state_key"]), _format_last_run_iso(utc_now()))


async def handle_matrix_scan(
    job: dict[str, Any],
    qe: QueryEngine,
    settings: Settings,
    *,
    worker_id: str,
) -> None:
    _ = worker_id
    from ada.publish.matrix import run_matrix_scan

    p = job.get("payload_json") or {}
    ms = str(p.get("mission_slug") or "").strip() or None
    dry_run = bool(p.get("dry_run", False))
    deterministic = bool(p.get("deterministic", False))
    out = await run_matrix_scan(
        qe, settings, dry_run=dry_run, deterministic=deterministic, mission_slug=ms
    )
    if isinstance(out, dict) and out.get("skipped"):
        log.info("matrix.scan skipped: %s", out.get("skipped"))
    if p.get("tick_state_key") and not dry_run:
        skipped = str(out.get("skipped") or "") if isinstance(out, dict) else ""
        if skipped.startswith("unknown_mission_slug:"):
            raise RuntimeError(skipped)
        if skipped == "ADA_MATRIX_ENABLE=0":
            log.info("matrix.scan matrix disabled")
        else:
            from ada.mission_tick import _format_last_run_iso, utc_now

            await qe.state_set(str(p["tick_state_key"]), _format_last_run_iso(utc_now()))
