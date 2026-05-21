"""Matrix router: scan graph → enqueue `publish_entity_v1` with ISR params (idempotent)."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from typing import Any

from ada.config import Settings
from ada.mission_defaults_resolve import resolve_programme_str
from ada.query_engine import QueryEngine
from ada.workflow.enqueue import enqueue_workflow_via_tool

log = logging.getLogger("ada.publish.matrix")

DEFAULT_KIND = "publish_entity_v1"


async def resolve_matrix_isr_ids(
    qe: QueryEngine, mission_slug: str | None
) -> tuple[str, str]:
    """Prefer mission.defaults_json keys over env ISR IDs."""
    env_pid = os.environ.get("ADA_PROJECT_ID", "default").strip() or "default"
    env_cid = os.environ.get("ADA_CAMPAIGN_ID", "main").strip() or "main"
    ms = str(mission_slug).strip() if mission_slug else ""
    if not ms:
        return env_pid, env_cid
    row = await qe.get_mission_by_slug(ms)
    if row is None:
        return env_pid, env_cid
    raw = row.get("defaults_json")
    d = dict(raw) if isinstance(raw, dict) else {}
    pid = resolve_programme_str(
        mission_defaults=d, key="project_id", env_value=env_pid
    ) or env_pid
    cid = resolve_programme_str(
        mission_defaults=d, key="campaign_id", env_value=env_cid
    ) or env_cid
    return pid, cid


@dataclass(frozen=True)
class PageProfile:
    workflow_kind: str
    project_id: str
    campaign_id: str
    niche: str


class PageProfileRegistry:
    """Maps (entity type, triage category code) to workflow + ISR fields (v1: table in code)."""

    def __init__(self, *, project_id: str, campaign_id: str) -> None:
        self._project_id = project_id
        self._campaign_id = campaign_id

    def resolve(self, entity_type: str, category_code: str) -> PageProfile:
        return profile_for(
            entity_type,
            category_code,
            project_id=self._project_id,
            campaign_id=self._campaign_id,
        )


def profile_for(
    entity_type: str, category_code: str, *, project_id: str, campaign_id: str
) -> PageProfile:
    _ = (entity_type, category_code)
    n = (category_code or "guide").replace("_", "-")
    return PageProfile(
        workflow_kind=DEFAULT_KIND,
        project_id=project_id,
        campaign_id=campaign_id,
        niche=n,
    )


def _slug_hint(name: str) -> str:
    s = " ".join((name or "").lower().split())
    out: list[str] = []
    for ch in s:
        if ch.isalnum() or ch in (" ", "-", "_"):
            out.append(ch)
    x = "".join(out).replace(" ", "-").replace("__", "-").strip("-")
    return x or "page"


def _content_hash_for_entity_row(row: dict[str, Any]) -> str:
    raw = json.dumps(
        {
            "id": row.get("id"),
            "name": row.get("name"),
            "last": row.get("last_enriched_at"),
            "payload": row.get("payload_json"),
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


async def enqueue_publish_entity_for_row(
    qe: QueryEngine,
    settings: Settings,
    row: dict[str, Any],
    *,
    registry: PageProfileRegistry,
    dry_run: bool = False,
    mission_slug: str | None = None,
) -> dict[str, Any]:
    et = str(row.get("type") or "").lower()
    code = str(row.get("category_code") or "").lower()
    eid = int(row["id"])
    prof = registry.resolve(et, code)
    slug = _slug_hint(str(row.get("name") or f"entity-{eid}"))
    h = _content_hash_for_entity_row(row)
    idem = f"publish:{eid}:{h}"
    params: dict[str, Any] = {
        "entity_id": eid,
        "project_id": prof.project_id,
        "campaign_id": prof.campaign_id,
        "niche": prof.niche,
        "slug": slug,
    }
    if dry_run:
        line = (
            f"would enqueue {prof.workflow_kind} {idem!r} params={params!r}"
        )
        return {"dry_run": True, "log_line": line, "error": ""}
    slug_trim = str(mission_slug).strip() if mission_slug else ""
    r = await enqueue_workflow_via_tool(
        qe,
        kind=prof.workflow_kind,
        goal_text=f"Publish entity {eid} ({row.get('name')}) to pSEO",
        params_json=json.dumps(params, ensure_ascii=False),
        idempotency_key=idem,
        max_steps=settings.ada_max_task_steps,
        require_approval=settings.require_approval_for_enqueue,
        mission_slug=slug_trim if slug_trim else None,
    )
    out: dict[str, Any] = {"dry_run": False, "enqueue": r}
    if r.get("error"):
        out["error"] = r["error"]
    else:
        out["error"] = ""
    return out


async def run_matrix_legacy_scan(
    qe: QueryEngine,
    settings: Settings,
    *,
    project_id: str,
    campaign_id: str,
    dry_run: bool,
    use_recent_order: bool,
    mission_slug: str | None = None,
) -> dict[str, Any]:
    """Enumerate candidates (deterministic ordering) → enqueue."""

    registry = PageProfileRegistry(project_id=project_id, campaign_id=campaign_id)
    types_f = settings.ada_matrix_entity_types
    limit = int(settings.ada_matrix_max_enqueues)
    if use_recent_order:
        rows = await qe.list_subjects_with_classified_category_recent_for_planner(
            entity_types=types_f, limit=limit
        )
    else:
        rows = await qe.list_subjects_with_classified_category(
            entity_types=types_f, limit=limit
        )
    log_lines: list[str] = []
    enq = 0
    for row in rows:
        r = await enqueue_publish_entity_for_row(
            qe,
            settings,
            row,
            registry=registry,
            dry_run=dry_run,
            mission_slug=mission_slug,
        )
        if dry_run:
            ln = str(r.get("log_line") or "")
            eid = int(row["id"])
            log_lines.append(ln or f"[legacy] dry scan row entity_id={eid}")
            enq += 1
            continue
        if r.get("error"):
            log.warning("matrix enqueue error: %s", r)
        else:
            enq += 1

    return {
        "enqueued": enq,
        "candidates": len(rows),
        "dry_run": dry_run,
        "mode": "matrix_legacy_scan",
        "order": ("recent_last_enriched" if use_recent_order else "stable_entity_id"),
        "log": log_lines[:50],
        "planned_ids": [],
    }


async def run_matrix_scan(
    qe: QueryEngine,
    settings: Settings,
    *,
    dry_run: bool = False,
    deterministic: bool = False,
    mission_slug: str | None = None,
) -> dict[str, Any]:
    if not settings.ada_matrix_enable and not dry_run:
        return {"enqueued": 0, "skipped": "ADA_MATRIX_ENABLE=0"}

    ms = str(mission_slug).strip() if mission_slug else ""
    if ms and await qe.get_mission_by_slug(ms) is None:
        return {"enqueued": 0, "skipped": f"unknown_mission_slug:{ms}"}

    project_id, campaign_id = await resolve_matrix_isr_ids(qe, mission_slug)
    planner_mode = settings.ada_matrix_planner and not deterministic

    if dry_run:
        registry = PageProfileRegistry(project_id=project_id, campaign_id=campaign_id)
        rows = []
        meta = ""
        types_f = settings.ada_matrix_entity_types
        limit = int(settings.ada_matrix_max_enqueues)
        if planner_mode:
            rows = await qe.list_subjects_with_classified_category_recent_for_planner(
                entity_types=types_f, limit=limit
            )
            meta = "planner_candidate_pool_recent"
        else:
            rows = await qe.list_subjects_with_classified_category(
                entity_types=types_f, limit=limit
            )
            meta = "legacy_stable_id_order"

        log_lines = []
        for row in rows:
            eid = int(row["id"])
            slug = _slug_hint(str(row.get("name") or f"entity-{eid}"))
            prof = registry.resolve(str(row.get("type") or ""), str(row.get("category_code") or ""))
            h = _content_hash_for_entity_row(row)
            idem = f"publish:{eid}:{h}"
            params: dict[str, Any] = {
                "entity_id": eid,
                "project_id": prof.project_id,
                "campaign_id": prof.campaign_id,
                "niche": prof.niche,
                "slug": slug,
            }
            log_lines.append(
                f"[{meta}] dry_run would enqueue {prof.workflow_kind} {idem!r} params={params!r}"
            )
        return {
            "dry_run": True,
            "enqueued": len(rows),
            "candidates": len(rows),
            "skipped": "",
            "log": log_lines[:50],
            "mode": ("matrix_planner" if planner_mode else "matrix_legacy"),
        }

    if planner_mode:
        from ada.publish.matrix_planner import run_matrix_plan_and_enqueue

        return await run_matrix_plan_and_enqueue(
            qe,
            settings,
            project_id=project_id,
            campaign_id=campaign_id,
            mission_slug=mission_slug,
        )

    return await run_matrix_legacy_scan(
        qe,
        settings,
        project_id=project_id,
        campaign_id=campaign_id,
        dry_run=False,
        use_recent_order=False,
        mission_slug=mission_slug,
    )
