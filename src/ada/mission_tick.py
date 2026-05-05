"""Deterministic mission tick: ``schedule_hint_json`` v1 + SQLite ``state`` last-run keys."""

from __future__ import annotations

import json
import re
from datetime import UTC, date, datetime, timedelta
from typing import Any

from ada.analytics.keyword_select import select_keyword_cluster
from ada.config import Settings
from ada.ingest.gsc_service import ingest_gsc_search_analytics
from ada.publish.matrix import run_matrix_scan
from ada.query_engine import QueryEngine
from ada.workflow.enqueue import enqueue_workflow_via_tool

_SLUG_SAFE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,63}$")


def tick_state_key(mission_slug: str, job_id: str) -> str:
    return f"mission.tick.{mission_slug.strip()}.{job_id.strip()}"


def parse_last_run_iso(value: str | None) -> datetime | None:
    if value is None or not str(value).strip():
        return None
    s = str(value).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def utc_now() -> datetime:
    return datetime.now(UTC)


def job_due(
    now: datetime,
    last: datetime | None,
    min_interval_hours: float,
    *,
    force: bool,
) -> bool:
    if force:
        return True
    if last is None:
        return True
    hours = max(0.0, float(min_interval_hours))
    return (now - last) >= timedelta(hours=hours)


def merge_action_defaults(
    defaults: dict[str, Any], action: dict[str, Any]
) -> dict[str, Any]:
    merged: dict[str, Any] = dict(defaults)
    atype = action.get("type")
    for k, v in action.items():
        if k == "type":
            continue
        merged[k] = v
    merged["type"] = atype
    return merged


def parse_tick_schedule_v1(
    schedule_hint_json: Any,
) -> tuple[list[dict[str, Any]] | None, str]:
    if schedule_hint_json is None:
        return [], ""
    if isinstance(schedule_hint_json, str):
        try:
            schedule_hint_json = json.loads(schedule_hint_json)
        except json.JSONDecodeError as e:
            return None, f"schedule_hint_json: invalid JSON ({e})"
    if not isinstance(schedule_hint_json, dict):
        return None, "schedule_hint_json must be a JSON object"
    ver = schedule_hint_json.get("version")
    if ver != 1:
        return None, f"unsupported schedule_hint_json version: {ver!r}"
    jobs = schedule_hint_json.get("jobs")
    if jobs is None:
        return [], ""
    if not isinstance(jobs, list):
        return None, "schedule_hint_json jobs must be a list"
    out: list[dict[str, Any]] = []
    for j in jobs:
        if not isinstance(j, dict):
            return None, "each job must be an object"
        jid = str(j.get("id") or "").strip()
        if not jid:
            return None, "job missing id"
        out.append(j)
    return out, ""


def _format_last_run_iso(now: datetime) -> str:
    return now.astimezone(UTC).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


async def run_mission_tick(
    qe: QueryEngine,
    settings: Settings,
    *,
    mission_slug: str,
    dry_run: bool = False,
    force: bool = False,
) -> int:
    slug = mission_slug.strip()
    if not slug or not _SLUG_SAFE.fullmatch(slug):
        return 2

    row = await qe.get_mission_by_slug(slug)
    if row is None:
        print(f"mission tick: no mission with slug {slug!r}", flush=True)
        return 2

    jobs, err = parse_tick_schedule_v1(row.get("schedule_hint_json"))
    if err:
        print(f"mission tick: {err}", flush=True)
        return 2
    if not jobs:
        print("mission tick: no jobs in schedule_hint_json (nothing to do)", flush=True)
        return 0

    defaults = row.get("defaults_json")
    base_defaults: dict[str, Any] = dict(defaults) if isinstance(defaults, dict) else {}

    now = utc_now()
    exit_code = 0

    for job in jobs:
        job_id = str(job["id"]).strip()
        key = tick_state_key(slug, job_id)
        try:
            min_h = float(job.get("min_interval_hours", 0))
        except (TypeError, ValueError):
            min_h = 0.0
        action = job.get("action")
        if not isinstance(action, dict):
            print(f"mission tick: job {job_id!r}: missing action object", flush=True)
            exit_code = 1
            continue
        atype = str(action.get("type") or "").strip()
        if not atype:
            print(f"mission tick: job {job_id!r}: action.type required", flush=True)
            exit_code = 1
            continue

        raw_last = await qe.state_get(key)
        last_dt = parse_last_run_iso(raw_last)
        due = job_due(now, last_dt, min_h, force=force)
        print(
            f"mission tick: job={job_id!r} due={due} last_run={raw_last!r}",
            flush=True,
        )
        if not due:
            continue

        merged = merge_action_defaults(base_defaults, action)

        if atype == "gsc_keyword_publish":
            rc, bump = await _tick_gsc_keyword_publish(
                qe,
                settings,
                mission_slug=slug,
                job_id=job_id,
                merged=merged,
                dry_run=dry_run,
            )
            if rc != 0:
                exit_code = rc
                continue
        elif atype == "matrix_entity_legacy_scan":
            rc, bump = await _tick_matrix_legacy(
                qe,
                settings,
                mission_slug=slug,
                job_id=job_id,
                merged=merged,
                dry_run=dry_run,
            )
            if rc != 0:
                exit_code = rc
                continue
        else:
            print(
                f"mission tick: job {job_id!r}: unknown action.type {atype!r}",
                flush=True,
            )
            exit_code = 1
            continue

        if not dry_run and bump:
            await qe.state_set(key, _format_last_run_iso(now))

    return exit_code


async def _tick_gsc_keyword_publish(
    qe: QueryEngine,
    settings: Settings,
    *,
    mission_slug: str,
    job_id: str,
    merged: dict[str, Any],
    dry_run: bool,
) -> tuple[int, bool]:
    if dry_run:
        print(
            f"mission tick: [dry-run] would run GSC ingest + keyword-select + "
            f"enqueue for mission={mission_slug!r} job={job_id!r}",
            flush=True,
        )
        return 0, False

    if not settings.enable_gsc_ingest:
        print("mission tick: ADA_ENABLE_GSC_INGEST required for gsc_keyword_publish", flush=True)
        return 1, False

    site = str(merged.get("gsc_site_url") or "").strip()
    if not site:
        print("mission tick: gsc_keyword_publish requires gsc_site_url in defaults/action", flush=True)
        return 1, False

    try:
        ingest_days = max(1, int(merged.get("ingest_days", 28)))
    except (TypeError, ValueError):
        ingest_days = 28
    dims_raw = str(
        merged.get("dimensions") or "date,query,page,country,device"
    ).strip()
    dimensions = [d.strip().lower() for d in dims_raw.split(",") if d.strip()]
    try:
        row_limit = max(1, int(merged.get("row_limit", 25000)))
    except (TypeError, ValueError):
        row_limit = 25000

    end_d = datetime.now(UTC).date()
    start_d = end_d - timedelta(days=ingest_days - 1)
    ks_raw = str(merged.get("keyword_start_date") or "").strip()
    ke_raw = str(merged.get("keyword_end_date") or "").strip()
    if ks_raw and ke_raw:
        start_sel, end_sel = ks_raw, ke_raw
    else:
        start_sel, end_sel = start_d.isoformat(), end_d.isoformat()

    idem_ingest = (
        f"gsc:{site}:{start_d.isoformat()}:{end_d.isoformat()}:"
        f"{','.join(dimensions)}:{row_limit}"
    )

    ingest_res = await ingest_gsc_search_analytics(
        qe,
        settings,
        site_url=site,
        start_date=start_d,
        end_date=end_d,
        dimensions=dimensions,
        row_limit=row_limit,
        dry_run=False,
        idempotency_key=idem_ingest,
    )
    if ingest_res.error:
        print(f"mission tick: GSC ingest failed: {ingest_res.error}", flush=True)
        return 1, False

    sel = await select_keyword_cluster(
        qe,
        site=site,
        start_date=start_sel,
        end_date=end_sel,
        limit=settings.gsc_plan_max_items,
    )
    if not sel.keyword_cluster:
        print(
            f"mission tick: keyword-select empty ({sel.fallback_reason}); "
            "skipping enqueue",
            flush=True,
        )
        return 0, False

    pid = str(merged.get("project_id") or "").strip()
    cid = str(merged.get("campaign_id") or "").strip()
    niche = str(merged.get("niche") or "").strip()
    if not (pid and cid and niche):
        print(
            "mission tick: gsc_keyword_publish requires project_id, campaign_id, niche "
            "in mission defaults_json or action",
            flush=True,
        )
        return 1, False

    params = {
        "target_keyword_cluster": sel.keyword_cluster,
        "keyword_source": sel.keyword_source,
        "project_id": pid,
        "campaign_id": cid,
        "niche": niche,
    }
    idem_wf = f"mission-tick-kw:{mission_slug}:{job_id}:{start_sel}:{end_sel}"
    goal = f"Publish keyword-led page (mission tick {job_id}): {sel.keyword_cluster}"

    wf_out = await enqueue_workflow_via_tool(
        qe,
        kind="publish_keyword_v1",
        goal_text=goal,
        params_json=json.dumps(params, ensure_ascii=False),
        idempotency_key=idem_wf,
        max_steps=settings.ada_max_task_steps,
        require_approval=settings.require_approval_for_enqueue,
        mission_slug=mission_slug,
    )
    if wf_out.get("error"):
        print(f"mission tick: enqueue failed: {wf_out['error']}", flush=True)
        return 1, False
    print(f"mission tick: enqueued workflow_id={wf_out.get('workflow_id')}", flush=True)
    return 0, True


async def _tick_matrix_legacy(
    qe: QueryEngine,
    settings: Settings,
    *,
    mission_slug: str,
    job_id: str,
    merged: dict[str, Any],
    dry_run: bool,
) -> tuple[int, bool]:
    mdry = bool(merged.get("dry_run")) or dry_run
    if dry_run:
        print(
            f"mission tick: [dry-run] would matrix-scan --deterministic "
            f"mission={mission_slug!r} job={job_id!r}",
            flush=True,
        )
        return 0, False

    out = await run_matrix_scan(
        qe,
        settings,
        dry_run=mdry,
        deterministic=True,
        mission_slug=mission_slug,
    )
    skipped = str(out.get("skipped") or "")
    if skipped.startswith("unknown_mission_slug:"):
        print(f"mission tick: matrix scan skipped ({skipped})", flush=True)
        return 1, False
    if skipped == "ADA_MATRIX_ENABLE=0" and not mdry:
        print(
            "mission tick: matrix_entity_legacy_scan skipped (ADA_MATRIX_ENABLE=0)",
            flush=True,
        )
        return 0, False
    print(f"mission tick: matrix scan result={out!r}", flush=True)
    return 0, True
