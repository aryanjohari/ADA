"""Matrix router: scan graph → enqueue `publish_entity_v1` with ISR params (idempotent)."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from typing import Any

from ada.config import Settings
from ada.query_engine import QueryEngine
from ada.workflow.enqueue import enqueue_workflow_via_tool

log = logging.getLogger("ada.publish.matrix")

DEFAULT_KIND = "publish_entity_v1"


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
    r = await enqueue_workflow_via_tool(
        qe,
        kind=prof.workflow_kind,
        goal_text=f"Publish entity {eid} ({row.get('name')}) to pSEO",
        params_json=json.dumps(params, ensure_ascii=False),
        idempotency_key=idem,
        max_steps=settings.ada_max_task_steps,
        require_approval=settings.require_approval_for_enqueue,
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
) -> dict[str, Any]:
    if not settings.ada_matrix_enable and not dry_run:
        return {"enqueued": 0, "skipped": "ADA_MATRIX_ENABLE=0"}

    project_id = os.environ.get("ADA_PROJECT_ID", "default").strip() or "default"
    campaign_id = os.environ.get("ADA_CAMPAIGN_ID", "main").strip() or "main"

    if dry_run:
        registry = PageProfileRegistry(project_id=project_id, campaign_id=campaign_id)
        rows = []
        meta = ""
        types_f = settings.ada_matrix_entity_types
        limit = int(settings.ada_matrix_max_enqueues)
        if settings.ada_matrix_planner:
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
            "mode": ("matrix_planner" if settings.ada_matrix_planner else "matrix_legacy"),
        }

    if settings.ada_matrix_planner:
        from ada.publish.matrix_planner import run_matrix_plan_and_enqueue

        return await run_matrix_plan_and_enqueue(
            qe,
            settings,
            project_id=project_id,
            campaign_id=campaign_id,
        )

    return await run_matrix_legacy_scan(
        qe,
        settings,
        project_id=project_id,
        campaign_id=campaign_id,
        dry_run=False,
        use_recent_order=False,
    )
