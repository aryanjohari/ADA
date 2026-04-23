"""enqueue_workflow tool and CLI helpers."""

from __future__ import annotations

from typing import Any

from ada.query_engine import TASK_KIND_GOAL, QueryEngine
from ada.workflow.templates import expand_workflow_template, parse_params_json_object


async def enqueue_workflow_via_tool(
    qe: QueryEngine,
    *,
    kind: str,
    goal_text: str,
    params_json: str | None,
    idempotency_key: str | None,
    max_steps: int | None,
) -> dict[str, Any]:
    """
    Insert pending goal task + workflow + steps. Returns workflow_id, task_id, created_new.
    """
    params = parse_params_json_object(params_json)
    steps = expand_workflow_template(kind, params, max_steps=max_steps)
    goal = str(goal_text).strip()
    if not goal:
        return {"error": "goal_text required"}
    key_s = idempotency_key.strip() if idempotency_key else ""
    if key_s:
        existing = await qe.find_workflow_by_idempotency(str(kind).strip(), key_s)
        if existing is not None:
            pid = existing.get("parent_task_id")
            return {
                "workflow_id": int(existing["id"]),
                "task_id": int(pid) if pid is not None else None,
                "created_new": False,
                "kind": str(kind).strip(),
                "steps": len(await qe.list_workflow_steps(int(existing["id"]))),
            }
    tid = await qe.insert_task(goal, status="pending", task_kind=TASK_KIND_GOAL)
    try:
        wf_id, created = await qe.enqueue_workflow(
            kind=str(kind).strip(),
            goal_text=goal,
            params_json=params,
            parent_task_id=tid,
            idempotency_key=idempotency_key,
            steps=steps,
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
        "kind": str(kind).strip(),
        "steps": len(steps),
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
