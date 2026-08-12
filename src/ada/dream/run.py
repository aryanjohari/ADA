"""Orchestrate dream.run: delta → seal → manage → merge → push stub → lifecycle."""

from __future__ import annotations

from typing import Any

from ada.body.lifecycle import append_event, last_of_type
from ada.dream.delta import build_delta, last_dream_ok
from ada.dream.manage import manage_delta
from ada.dream.merge import apply_manage_result
from ada.dream.push import push_outbox
from ada.dream.seal import seal_package
from ada.io.paths import DataPaths, require_ada_data
from ada.memory.staging import list_staged


def dream_status(*, paths: DataPaths | None = None) -> dict[str, Any]:
    p = paths or require_ada_data()
    last_ok = last_dream_ok(p)
    last_fail = last_of_type("dream_fail", p)
    outbox = []
    if p.dream_outbox.is_dir():
        outbox = sorted(d.name for d in p.dream_outbox.iterdir() if d.is_dir())
    return {
        "last_dream_ok": last_ok.model_dump() if last_ok else None,
        "last_dream_fail": last_fail.model_dump() if last_fail else None,
        "outbox_pending": outbox,
        "outbox_count": len(outbox),
        "staging_pending": len(list_staged(paths=p)),
        "push": "skipped",  # v1 stub posture
    }


def dream_run(
    *,
    paths: DataPaths | None = None,
    skip_manage: bool = False,
    api_key: str | None = None,
    manage_client: Any | None = None,
) -> dict[str, Any]:
    """Full local Dream pipeline. Manage failure must not block seal."""
    p = paths or require_ada_data()
    p.ensure_memory_dirs()
    p.ensure_dream_dirs()

    # Ensure prefs exist so seal has something durable.
    from ada.memory.facts import ensure_prefs
    from ada.memory.open_loops import ensure_open_loops

    ensure_prefs(p)
    ensure_open_loops(p)

    delta = build_delta(paths=p)
    seal = seal_package(delta, paths=p)
    dream_id = seal["dream_id"]

    manage = manage_delta(
        delta,
        api_key=api_key,
        client=manage_client,
        skip=skip_manage,
    )
    merge_info = apply_manage_result(
        manage.get("result"),
        paths=p,
        dream_id=dream_id,
    )
    push = push_outbox(dream_id=dream_id, outbox_path=seal.get("outbox_path"))

    receipts = {
        "dream_id": dream_id,
        "package_sha256": seal.get("package_sha256"),
        "outbox_path": seal.get("outbox_path"),
        "manage_ok": bool(manage.get("ok")),
        "manage_skipped": bool(manage.get("skipped")),
        "manage_reason": manage.get("reason"),
        "merged_count": len(merge_info.get("merged") or []),
        "staged_count": len(merge_info.get("staged") or []),
        "digest_path": merge_info.get("digest_path"),
        "push": push.get("push"),
        "push_reason": push.get("reason"),
        "delta_since": delta.get("since"),
        "lifecycle_delta_count": delta.get("lifecycle_count"),
    }

    # Local seal succeeded → dream_ok even if manage skipped/failed.
    event = append_event(
        "dream_ok",
        summary=f"dream sealed {dream_id} push={push.get('push')}",
        details={
            "dream_id": dream_id,
            "manage_skipped": receipts["manage_skipped"],
            "manage_reason": receipts.get("manage_reason"),
            "merged_count": receipts["merged_count"],
            "staged_count": receipts["staged_count"],
        },
        receipts=receipts,
        paths=p,
    )

    return {
        "ok": True,
        "status": "dream_ok",
        "dream_id": dream_id,
        "seal": seal,
        "manage": manage,
        "merge": merge_info,
        "push": push,
        "lifecycle_event_id": event.id,
        "receipts": receipts,
    }
