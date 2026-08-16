"""Thin wrappers → ada.memory.* / ada.dream.status (M04)."""

from __future__ import annotations

from typing import Any

from ada.dream.run import dream_status
from ada.memory import facts as facts_mod
from ada.memory import open_loops as loops_mod
from ada.memory import worldview as wv_mod
from ada.memory.worldview import WorldviewError


def run_memory_facts_get(args: dict[str, Any]) -> dict[str, Any]:
    key = args.get("key") or args.get("path")
    if not key:
        raise ValueError("key required")
    return facts_mod.get_fact(str(key))


def run_memory_facts_search(args: dict[str, Any]) -> dict[str, Any]:
    query = args.get("query") or args.get("q") or ""
    max_hits = int(args.get("max_hits") or 20)
    return facts_mod.search_facts(str(query), max_hits=max_hits)


def run_memory_facts_append(args: dict[str, Any]) -> dict[str, Any]:
    key = args.get("key")
    if not key:
        raise ValueError("key required (e.g. prefs.brief_time)")
    if "value" not in args:
        raise ValueError("value required")
    return facts_mod.append_fact(
        str(key),
        args.get("value"),
        note=args.get("note"),
        confirmed=bool(args.get("confirmed", False)),
    )


def run_memory_facts_propose_edit(args: dict[str, Any]) -> dict[str, Any]:
    key = args.get("key")
    if not key:
        raise ValueError("key required")
    if "value" not in args:
        raise ValueError("value required")
    return facts_mod.propose_edit(
        str(key),
        args.get("value"),
        confirmed=bool(args.get("confirmed", False)),
    )


def run_memory_open_loops_list(args: dict[str, Any]) -> dict[str, Any]:
    """List loops/campaigns with kind-aware status defaults.

    When status is omitted: campaign → non-terminal (not todo ``open``);
    todo → open; both → open todos + non-terminal campaigns.
    Pass status=null/"" for no status filter. Explicit status always honored.
    """
    kind = args.get("kind")
    kind_str = str(kind) if kind else None
    limit = int(args.get("limit") or 50)
    if "status" not in args:
        loops = loops_mod.list_loops(kind=kind_str, limit=limit)
    else:
        status = args.get("status")
        status_filter: str | None
        if status is None or status == "":
            status_filter = None
        else:
            status_filter = str(status)
        loops = loops_mod.list_loops(
            status=status_filter,
            kind=kind_str,
            limit=limit,
        )
    return {"loops": loops, "count": len(loops)}


def run_memory_open_loops_upsert(args: dict[str, Any]) -> dict[str, Any]:
    status_arg = args.get("status")
    return loops_mod.upsert_loop(
        text=args.get("text"),
        loop_id=args.get("id") or args.get("loop_id"),
        status=str(status_arg) if status_arg is not None else None,
        kind=str(args["kind"]) if args.get("kind") is not None else None,
        title=args.get("title"),
        stages=args.get("stages"),
        current_stage=args.get("current_stage"),
        blocked_reason=args.get("blocked_reason"),
        next_wake_at=args.get("next_wake_at"),
        last_progress_at=args.get("last_progress_at"),
        last_receipt=args.get("last_receipt"),
        cadence=args.get("cadence"),
        nudge_attribution=args.get("nudge_attribution"),
        due_at=str(args["due_at"]) if args.get("due_at") is not None else None,
        remind_at=str(args["remind_at"]) if args.get("remind_at") is not None else None,
        people_ids=args.get("people_ids"),
        artifact_path=(
            str(args["artifact_path"]) if args.get("artifact_path") is not None else None
        ),
        starts_at=str(args["starts_at"]) if args.get("starts_at") is not None else None,
        ends_at=str(args["ends_at"]) if args.get("ends_at") is not None else None,
        notify=bool(args["notify"]) if args.get("notify") is not None else None,
        last_notified_at=(
            str(args["last_notified_at"])
            if args.get("last_notified_at") is not None
            else None
        ),
        delete=bool(args.get("delete", False)),
        confirmed=bool(args.get("confirmed", False)),
    )


def run_memory_worldview_search(args: dict[str, Any]) -> dict[str, Any]:
    return wv_mod.search_worldview(
        str(args.get("query") or args.get("q") or ""),
        max_hits=int(args.get("max_hits") or 20),
    )


def run_memory_worldview_write(args: dict[str, Any]) -> dict[str, Any]:
    body = args.get("body") or args.get("text")
    if not body:
        raise ValueError("body required")
    cites = args.get("cites")
    try:
        return wv_mod.write_digest(
            str(body),
            cites=cites if isinstance(cites, list) else cites,
            title=args.get("title"),
            dream=bool(args.get("dream", False)),
        )
    except WorldviewError as exc:
        return {
            "ok": False,
            "outcome": "error",
            "error": str(exc),
            "denied_reason": str(exc),
        }


def run_dream_status(_args: dict[str, Any]) -> dict[str, Any]:
    return dream_status()


DISPATCH = {
    "memory_facts_get": run_memory_facts_get,
    "memory_facts_search": run_memory_facts_search,
    "memory_facts_append": run_memory_facts_append,
    "memory_facts_propose_edit": run_memory_facts_propose_edit,
    "memory_open_loops_list": run_memory_open_loops_list,
    "memory_open_loops_upsert": run_memory_open_loops_upsert,
    "memory_worldview_search": run_memory_worldview_search,
    "memory_worldview_write": run_memory_worldview_write,
    "dream_status": run_dream_status,
}
