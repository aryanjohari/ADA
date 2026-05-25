"""J1 primitive handlers — async store touchpoints on base_ops / ada_ops hats."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from ada.boot import ADA_OPS_SLUG
from ada.config import Settings
from ada.mission_control.digest import brief_artifact_path
from ada.observability.queries import (
    mission_tick_state_rows,
    missions_overview_list,
    open_readonly_connection,
)
from ada.primitives.catalog import PRIMITIVES, get_primitive_spec
from ada.primitives.scope import resolve_kernel
from ada.query_engine import TASK_KIND_GOAL, TASK_KIND_SYSTEM, QueryEngine

UTC = timezone.utc


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _require_str(args: dict[str, Any], key: str) -> str:
    raw = args.get(key)
    if raw is None or not str(raw).strip():
        raise ValueError(f"primitive arg {key!r} is required")
    return str(raw).strip()


def _optional_int(args: dict[str, Any], key: str, default: int) -> int:
    raw = args.get(key)
    if raw is None:
        return default
    try:
        return max(1, min(int(raw), 500))
    except (TypeError, ValueError) as e:
        raise ValueError(f"primitive arg {key!r} must be an integer") from e


_ARG_ALIASES: dict[str, dict[str, str]] = {
    "log_memory": {"text": "content", "memory": "content", "note": "content"},
    "add_task": {"task": "goal", "title": "goal", "text": "goal", "todo": "goal"},
    "recall_memory": {"q": "query", "question": "query"},
}

_OPERATOR_SUMMARY_MAX_LEN = 4000
_OPERATOR_LINE_MAX_LEN = 500
_OPERATOR_LIST_MAX_ITEMS = 8


def _sanitize_operator_text(text: str, *, max_len: int = _OPERATOR_LINE_MAX_LEN) -> str:
    """Strip control chars and bound length for operator-facing fallback prose."""
    cleaned = "".join(
        ch for ch in text if ch in ("\n", "\t") or (ord(ch) >= 32 and ord(ch) != 127)
    )
    cleaned = cleaned.strip()
    if len(cleaned) > max_len:
        return cleaned[: max(1, max_len - 1)] + "…"
    return cleaned


def _sanitize_operator_summary(text: str) -> str:
    out = _sanitize_operator_text(text, max_len=_OPERATOR_SUMMARY_MAX_LEN)
    return out if out else "Done."


def _coerce_run_primitive_args(raw: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Normalize ``run_primitive`` tool args (``args_json`` wrapper or flat keys)."""
    src = dict(raw or {})
    primitive_id = str(src.pop("primitive_id", "") or "").strip()

    inner: dict[str, Any] = {}
    raw_json = src.pop("args_json", None)
    if raw_json is not None:
        if isinstance(raw_json, str):
            try:
                parsed = json.loads(raw_json)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, dict):
                inner = dict(parsed)
        elif isinstance(raw_json, dict):
            inner = dict(raw_json)

    for key, val in src.items():
        if key not in inner or inner.get(key) is None or not str(inner.get(key, "")).strip():
            inner[key] = val

    if primitive_id:
        inner = _coerce_args(primitive_id, inner)
    return primitive_id, inner


def format_run_primitive_operator_summary(response: dict[str, Any]) -> str | None:
    """Operator-facing fallback when the model stream fails after ``run_primitive``."""
    if not isinstance(response, dict):
        return None
    err = response.get("error")
    if err:
        return _sanitize_operator_summary(f"Could not complete that: {err}")
    if response.get("ok") is False:
        return _sanitize_operator_summary(
            f"Could not complete that: {err or 'primitive failed'}"
        )
    if response.get("ok") is not True and "primitive" not in response:
        return None

    pid = str(response.get("primitive") or "")
    if pid == "log_memory":
        if response.get("inserted") is False:
            item = response.get("item_id")
            msg = (
                f"Already in memory (item #{item})."
                if item is not None
                else "Already in memory."
            )
            return _sanitize_operator_summary(msg)
        return _sanitize_operator_summary("Memory logged.")
    if pid == "add_task":
        tid = response.get("task_id")
        goal = _sanitize_operator_text(str(response.get("goal") or ""))
        if tid is not None and goal:
            return _sanitize_operator_summary(f"Saved todo #{tid}: {goal}")
        if tid is not None:
            return _sanitize_operator_summary(f"Saved todo #{tid}.")
        return _sanitize_operator_summary("Todo saved.")
    if pid == "complete_task":
        tid = response.get("task_id")
        msg = (
            f"Marked todo #{tid} complete."
            if tid is not None
            else "Task marked complete."
        )
        return _sanitize_operator_summary(msg)
    if pid == "recall_memory":
        items = response.get("items")
        if not isinstance(items, list) or not items:
            return _sanitize_operator_summary(
                "I don't have anything stored about that yet."
            )
        lines: list[str] = []
        for it in items[:_OPERATOR_LIST_MAX_ITEMS]:
            if not isinstance(it, dict):
                continue
            ex = _sanitize_operator_text(str(it.get("content_excerpt") or ""))
            if ex:
                lines.append(f"- {ex}")
        if not lines:
            return _sanitize_operator_summary(
                "I don't have anything stored about that yet."
            )
        body = "Here's what I remember:\n" + "\n".join(lines)
        extra = int(response.get("count") or 0) - len(lines)
        if extra > 0:
            body += f"\n(+ {extra} more not shown)"
        return _sanitize_operator_summary(body)
    if pid == "list_tasks":
        tasks = response.get("tasks")
        if isinstance(tasks, list) and tasks:
            lines = []
            for t in tasks[:_OPERATOR_LIST_MAX_ITEMS]:
                if not isinstance(t, dict):
                    continue
                goal = _sanitize_operator_text(str(t.get("goal") or ""))
                tid = t.get("id")
                status = _sanitize_operator_text(str(t.get("status") or ""), max_len=40)
                if goal and tid is not None:
                    lines.append(f"- #{tid} [{status}] {goal}")
                elif goal:
                    lines.append(f"- [{status}] {goal}")
            if lines:
                body = "Your todos:\n" + "\n".join(lines)
                extra = int(response.get("count") or 0) - len(lines)
                if extra > 0:
                    body += f"\n(+ {extra} more not shown)"
                return _sanitize_operator_summary(body)
        n = int(response.get("count") or 0)
        if n == 0:
            return _sanitize_operator_summary("No todos found.")
        return _sanitize_operator_summary(f"Listed {n} task(s).")
    if pid == "body_check":
        return _sanitize_operator_summary("Body check complete.")
    if response.get("ok") is True:
        return _sanitize_operator_summary("Done.")
    return None


def _coerce_args(primitive_id: str, args: dict[str, Any]) -> dict[str, Any]:
    """Map common model arg names to catalog keys before validation."""
    aliases = _ARG_ALIASES.get(primitive_id)
    if not aliases:
        return args
    out = dict(args)
    for alias, canonical in aliases.items():
        if alias not in out:
            continue
        canon_val = out.get(canonical)
        if canon_val is None or not str(canon_val).strip():
            if out[alias] is not None and str(out[alias]).strip():
                out[canonical] = out[alias]
        del out[alias]
    return out


def _validate_args(spec_id: str, args: dict[str, Any]) -> None:
    spec = get_primitive_spec(spec_id)
    for key in spec.required_args:
        if key not in args or args[key] is None or str(args[key]).strip() == "":
            raise ValueError(f"primitive {spec_id!r} requires arg {key!r}")
    allowed = spec.required_args | spec.optional_args
    unknown = set(args.keys()) - allowed
    if unknown:
        raise ValueError(
            f"primitive {spec_id!r} unknown arg(s): {sorted(unknown)!r}; "
            f"allowed: {sorted(allowed)!r}"
        )


async def handle_add_task(
    qe: QueryEngine,
    settings: Settings,
    args: dict[str, Any],
    *,
    kernel=None,
) -> dict[str, Any]:
    _validate_args("add_task", args)
    k = await resolve_kernel(qe, settings, kernel=kernel)
    goal = _require_str(args, "goal")
    status = str(args.get("status") or "pending").strip() or "pending"
    tid = await qe.insert_task(
        goal,
        status=status,
        task_kind=TASK_KIND_SYSTEM,
        mission_id=k.base_ops_id,
    )
    return {"ok": True, "primitive": "add_task", "task_id": tid, "goal": goal, "status": status}


async def handle_list_tasks(
    qe: QueryEngine,
    settings: Settings,
    args: dict[str, Any],
    *,
    kernel=None,
) -> dict[str, Any]:
    _validate_args("list_tasks", args)
    k = await resolve_kernel(qe, settings, kernel=kernel)
    status_raw = args.get("status")
    status = str(status_raw).strip() if status_raw is not None else None
    if status == "":
        status = None
    limit = _optional_int(args, "limit", 50)
    rows = await qe.list_system_tasks(k.base_ops_id, limit=limit, status=status)
    tasks = [
        {
            "id": r["id"],
            "goal": r["goal"],
            "status": r["status"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        }
        for r in rows
    ]
    return {"ok": True, "primitive": "list_tasks", "tasks": tasks, "count": len(tasks)}


async def handle_complete_task(
    qe: QueryEngine,
    settings: Settings,
    args: dict[str, Any],
    *,
    kernel=None,
) -> dict[str, Any]:
    _validate_args("complete_task", args)
    k = await resolve_kernel(qe, settings, kernel=kernel)
    try:
        task_id = int(args["task_id"])
    except (TypeError, ValueError) as e:
        raise ValueError("primitive arg 'task_id' must be an integer") from e
    row = await qe.get_system_task(task_id)
    if row["mission_id"] != k.base_ops_id:
        raise ValueError(
            f"task {task_id} mission_id={row['mission_id']!r} "
            f"does not belong to base_ops ({k.base_ops_id})"
        )
    await qe.update_task(task_id, status="completed")
    return {
        "ok": True,
        "primitive": "complete_task",
        "task_id": task_id,
        "status": "completed",
    }


async def handle_log_memory(
    qe: QueryEngine,
    settings: Settings,
    args: dict[str, Any],
    *,
    kernel=None,
) -> dict[str, Any]:
    _validate_args("log_memory", args)
    k = await resolve_kernel(qe, settings, kernel=kernel)
    content = _require_str(args, "content")
    tags_raw = args.get("tags")
    tags: list[str] | None = None
    if tags_raw is not None:
        if not isinstance(tags_raw, list):
            raise ValueError("primitive arg 'tags' must be a list of strings")
        tags = [str(t).strip() for t in tags_raw if str(t).strip()]
    chash = _content_hash(content)
    result = await qe.insert_knowledge_item(
        k.memory_source_id,
        chash,
        tags=tags,
        content_excerpt=content,
    )
    return {
        "ok": True,
        "primitive": "log_memory",
        "item_id": result.id,
        "inserted": result.inserted,
        "source_id": k.memory_source_id,
    }


async def handle_recall_memory(
    qe: QueryEngine,
    settings: Settings,
    args: dict[str, Any],
    *,
    kernel=None,
) -> dict[str, Any]:
    _validate_args("recall_memory", args)
    k = await resolve_kernel(qe, settings, kernel=kernel)
    limit = _optional_int(args, "limit", 20)
    query_raw = args.get("query")
    query = str(query_raw).strip().lower() if query_raw is not None else ""
    rows = await qe.list_knowledge_items(source_id=k.memory_source_id, limit=limit)
    if query:
        rows = [
            r
            for r in rows
            if query in str(r.get("content_excerpt") or "").lower()
        ]
    items = [
        {
            "id": r["id"],
            "content_excerpt": r.get("content_excerpt") or "",
            "tags": r.get("tags") or [],
            "ingested_at": r.get("ingested_at"),
        }
        for r in rows
    ]
    return {
        "ok": True,
        "primitive": "recall_memory",
        "items": items,
        "count": len(items),
        "source_id": k.memory_source_id,
    }


async def handle_body_check(
    qe: QueryEngine,
    settings: Settings,
    args: dict[str, Any],
    *,
    kernel=None,
) -> dict[str, Any]:
    _validate_args("body_check", args)
    k = await resolve_kernel(qe, settings, kernel=kernel)
    conn = open_readonly_connection(settings.state_db_path)
    try:
        tick_state = mission_tick_state_rows(conn, mission_slug=ADA_OPS_SLUG)
        overview = missions_overview_list(conn, slug_filter=None)
        pending_goal_count = sum(int(r.get("pending_goals") or 0) for r in overview)
        ada_rows = [r for r in overview if int(r["id"]) == k.ada_ops_id]
        ada_ops = ada_rows[0] if ada_rows else {}
    finally:
        conn.close()

    brief_path = brief_artifact_path(settings)
    last_brief: dict[str, Any] = {
        "path": str(brief_path),
        "exists": brief_path.is_file(),
    }
    if brief_path.is_file():
        mtime = brief_path.stat().st_mtime
        last_brief["modified_at"] = datetime.fromtimestamp(mtime, UTC).replace(
            microsecond=0
        ).isoformat().replace("+00:00", "Z")

    pending_goals = await qe.list_goal_tasks(limit=500, status="pending")
    return {
        "ok": True,
        "primitive": "body_check",
        "kernel": k.as_summary(),
        "pending_goal_count": pending_goal_count,
        "pending_goals_sample": [
            {"id": r["id"], "goal": r["goal"], "mission_slug": r.get("mission_slug")}
            for r in pending_goals[:10]
        ],
        "ada_ops": {
            "slug": ADA_OPS_SLUG,
            "id": k.ada_ops_id,
            "tick_state": tick_state,
            "pending_goals": int(ada_ops.get("pending_goals") or 0),
            "pending_workflows": int(ada_ops.get("pending_workflows") or 0),
            "pending_system_jobs": int(ada_ops.get("pending_system_jobs") or 0),
        },
        "daemon": {
            "job_queue": settings.ada_job_queue,
            "kill_switch": settings.ada_kill_switch,
            "gemini_configured": bool(settings.gemini_api_key),
        },
        "profile_paths": {
            "memory_dir": str(settings.memory_dir),
            "soul_path": str(settings.soul_path),
            "master_path": str(settings.master_path),
            "wakeup_path": str(settings.wakeup_path),
            "state_db_path": str(settings.state_db_path),
        },
        "last_brief": last_brief,
    }


_HANDLERS = {
    "add_task": handle_add_task,
    "list_tasks": handle_list_tasks,
    "complete_task": handle_complete_task,
    "log_memory": handle_log_memory,
    "recall_memory": handle_recall_memory,
    "body_check": handle_body_check,
}


async def execute_primitive(
    qe: QueryEngine,
    settings: Settings,
    primitive_id: str,
    args: dict[str, Any] | None = None,
    *,
    kernel=None,
) -> dict[str, Any]:
    """Dispatch a closed-list primitive by id."""
    if primitive_id not in PRIMITIVES:
        known = sorted(PRIMITIVES)
        raise ValueError(f"unknown primitive {primitive_id!r}; known: {known}")
    handler = _HANDLERS.get(primitive_id)
    if handler is None:
        raise RuntimeError(f"no handler registered for primitive {primitive_id!r}")
    payload = _coerce_args(primitive_id, dict(args or {}))
    return await handler(qe, settings, payload, kernel=kernel)
