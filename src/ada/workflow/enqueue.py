"""enqueue_workflow tool and CLI helpers."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from ada.policy.load import PolicyConfig, load_merged_policy
from ada.query_engine import TASK_KIND_GOAL, QueryEngine
from ada.workflow.playbook_resolve import resolve_for_kind, resolve_playbook
from ada.workflow.templates import expand_workflow_template, parse_params_json_object


async def enqueue_workflow_via_tool(
    qe: QueryEngine,
    *,
    kind: str,
    goal_text: str,
    params_json: str | None,
    idempotency_key: str | None,
    max_steps: int | None,
    require_approval: bool = False,
    playbook_id: str | None = None,
    mission_slug: str | None = None,
    source_task_id: int | None = None,
    mission_tag_id: int | None = None,
    policy: PolicyConfig | None = None,
) -> dict[str, Any]:
    """
    Insert pending goal task + workflow + steps. Returns workflow_id, task_id, created_new.
    Params are merged via the playbook registry (policy → mission.defaults_json → params_json).
    Mission tagging: ``mission_slug`` wins; else optional ``mission_tag_id`` (e.g. duplicate-run);
    else ``source_task_id`` inherits that goal task's mission_id.
    """
    params_delta = parse_params_json_object(params_json)
    mission_defaults: dict[str, Any] = {}
    mid: int | None = None
    slug_trim = str(mission_slug).strip() if mission_slug is not None else ""
    if slug_trim:
        row = await qe.get_mission_by_slug(slug_trim)
        if row is None:
            return {"error": f"no mission with slug {slug_trim!r}"}
        raw = row.get("defaults_json")
        mission_defaults = dict(raw) if isinstance(raw, dict) else {}
        mid = int(row["id"])
    elif mission_tag_id is not None:
        mid = int(mission_tag_id)
    elif source_task_id is not None:
        try:
            src = await qe.get_goal_task(int(source_task_id))
        except (LookupError, ValueError) as e:
            return {"error": str(e)}
        m = src.get("mission_id")
        mid = int(m) if m is not None else None

    pol = policy if policy is not None else load_merged_policy()
    pid = str(playbook_id).strip() if playbook_id is not None else ""
    try:
        if pid:
            resolved = resolve_playbook(
                pid,
                policy=pol,
                mission_defaults=mission_defaults,
                params_delta=params_delta,
            )
        else:
            resolved = resolve_for_kind(
                kind,
                policy=pol,
                mission_defaults=mission_defaults,
                params_delta=params_delta,
            )
    except ValueError as e:
        return {"error": str(e)}

    wf_kind = resolved.workflow_kind
    params = resolved.params
    steps = expand_workflow_template(wf_kind, params, max_steps=max_steps)
    goal = str(goal_text).strip()
    if not goal:
        return {"error": "goal_text required"}
    key_s = idempotency_key.strip() if idempotency_key else ""
    artifact_ref = key_s
    if not artifact_ref:
        artifact_ref = hashlib.sha256(
            json.dumps(
                {
                    "kind": wf_kind,
                    "playbook_id": resolved.playbook_id,
                    "goal": goal,
                    "params": params,
                },
                sort_keys=True,
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()[:24]
    if require_approval:
        rec = await qe.get_approval_record(
            artifact_type="workflow_enqueue",
            artifact_ref=artifact_ref,
        )
        if rec is None or rec.get("status") != "approved":
            await qe.append_action_log(
                "workflow_enqueue_blocked_no_approval",
                {
                    "kind": wf_kind,
                    "artifact_type": "workflow_enqueue",
                    "artifact_ref": artifact_ref,
                    "idempotency_key": key_s,
                    "target_keyword_cluster": params.get("target_keyword_cluster"),
                    "keyword_source": params.get("keyword_source"),
                },
                session_id=None,
            )
            return {
                "error": "workflow enqueue requires approval record with status=approved",
                "artifact_type": "workflow_enqueue",
                "artifact_ref": artifact_ref,
            }
    if key_s:
        existing = await qe.find_workflow_by_idempotency(wf_kind, key_s)
        if existing is not None:
            ptask = existing.get("parent_task_id")
            return {
                "workflow_id": int(existing["id"]),
                "task_id": int(ptask) if ptask is not None else None,
                "created_new": False,
                "kind": wf_kind,
                "playbook_id": resolved.playbook_id,
                "steps": len(await qe.list_workflow_steps(int(existing["id"]))),
            }
    tid = await qe.insert_task(
        goal, status="pending", task_kind=TASK_KIND_GOAL, mission_id=mid
    )
    try:
        wf_id, created = await qe.enqueue_workflow(
            kind=wf_kind,
            goal_text=goal,
            params_json=params,
            parent_task_id=tid,
            idempotency_key=idempotency_key,
            steps=steps,
            mission_id=mid,
        )
    except ValueError as e:
        await qe.update_task(tid, status="failed", current_output=str(e))
        return {"error": str(e)}
    except Exception as e:
        await qe.update_task(tid, status="failed", current_output=str(e))
        return {"error": str(e)}
    return {
        "workflow_id": wf_id,
        "task_id": tid,
        "created_new": created,
        "kind": wf_kind,
        "playbook_id": resolved.playbook_id,
        "steps": len(steps),
        "artifact_ref": artifact_ref,
    }


async def get_workflow_status_via_tool(
    qe: QueryEngine,
    *,
    workflow_id: int,
) -> dict[str, Any]:
    wf = await qe.get_workflow_by_id(workflow_id)
    if wf is None:
        return {"error": f"no workflow with id={workflow_id}"}
    steps = await qe.list_workflow_steps(workflow_id)
    return {"workflow": wf, "steps": steps}
