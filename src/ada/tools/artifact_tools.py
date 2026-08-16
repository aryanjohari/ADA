"""Artifact + notify tool wrappers (M16)."""

from __future__ import annotations

from typing import Any

from ada.memory import artifacts as art_mod
from ada.memory import notify as notify_mod


def run_artifact_write(args: dict[str, Any]) -> dict[str, Any]:
    title = args.get("title") or "note"
    body = args.get("body")
    if body is None:
        raise ValueError("body required")
    cites = args.get("source_cites") or args.get("cites")
    if cites is not None and not isinstance(cites, list):
        cites = [str(cites)]
    return art_mod.write_artifact(
        title=str(title),
        body=str(body),
        format=str(args.get("format") or "md"),
        source_cites=list(cites) if cites else None,
        overwrite=bool(args.get("overwrite", False)),
        confirmed=bool(args.get("confirmed", False)),
        relative_path=str(args["path"]) if args.get("path") else None,
    )


def run_artifact_list(args: dict[str, Any]) -> dict[str, Any]:
    limit = int(args.get("limit") or 12)
    items = art_mod.list_artifacts(limit=limit)
    return {"ok": True, "outcome": "ok", "artifacts": items, "count": len(items)}


def run_notify_send(args: dict[str, Any]) -> dict[str, Any]:
    message = args.get("message") or args.get("text")
    if not message:
        raise ValueError("message required")
    return notify_mod.notify_send(
        title=str(args["title"]) if args.get("title") else None,
        message=str(message),
        todo_id=str(args["todo_id"]) if args.get("todo_id") else None,
        force=bool(args.get("force", False)),
    )


DISPATCH = {
    "artifact_write": run_artifact_write,
    "artifact_list": run_artifact_list,
    "notify_send": run_notify_send,
}
