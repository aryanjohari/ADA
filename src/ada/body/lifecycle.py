"""Append-only lifecycle ledger — body autobiography, not enterprise HR."""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from ada import __version__
from ada.body.vitals import utc_now_iso
from ada.io.atomic import append_jsonl_line, recover_torn_jsonl
from ada.io.paths import BodyFault, DataPaths, require_ada_data

EventType = Literal[
    "birth",
    "wake",
    "sleep",
    "fault",
    "heal_retry",
    "heal_ok",
    "heal_give_up",
    "deploy",
    "note",
]

V0_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "birth",
        "wake",
        "sleep",
        "fault",
        "heal_retry",
        "heal_ok",
        "heal_give_up",
        "deploy",
        "note",
    }
)


class LifecycleEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    schema_version: int = 1
    id: str
    ts: str
    type: str
    summary: str
    details: dict[str, Any] = Field(default_factory=dict)
    receipts: dict[str, Any] = Field(default_factory=dict)


def _new_id() -> str:
    return str(uuid.uuid4())


def _boot_id() -> str | None:
    try:
        return Path("/proc/sys/kernel/random/boot_id").read_text(encoding="utf-8").strip()
    except OSError:
        return None


def ensure_ledger_ready(paths: DataPaths) -> bool:
    """Run torn-line recovery; return True if a torn line was truncated."""
    return recover_torn_jsonl(paths.lifecycle_jsonl)


def append_event(
    event_type: str,
    *,
    summary: str,
    details: dict[str, Any] | None = None,
    receipts: dict[str, Any] | None = None,
    paths: DataPaths | None = None,
    ts: str | None = None,
    event_id: str | None = None,
) -> LifecycleEvent:
    """Append one lifecycle event after mount check + torn-line recovery."""
    if event_type not in V0_EVENT_TYPES:
        raise ValueError(f"unsupported lifecycle type for v0: {event_type}")

    p = paths or require_ada_data()
    # require_ada_data already gates mount; double-check for callers passing paths
    from ada.io.paths import ada_data_mounted

    if not ada_data_mounted(p.root):
        raise BodyFault(
            f"ada-data not mounted or missing at {p.root}; refusing durable writes"
        )

    torn = ensure_ledger_ready(p)
    detail = dict(details or {})
    if torn:
        # Record recovery first so the autobiography stays honest.
        fault = LifecycleEvent(
            id=_new_id(),
            ts=utc_now_iso(),
            type="fault",
            summary="lifecycle torn line recovered",
            details={"reason": "torn_line"},
            receipts={},
        )
        append_jsonl_line(p.lifecycle_jsonl, fault.model_dump())

    event = LifecycleEvent(
        id=event_id or _new_id(),
        ts=ts or utc_now_iso(),
        type=event_type,
        summary=summary,
        details=detail,
        receipts=dict(receipts or {}),
    )
    p.memory.mkdir(parents=True, exist_ok=True)
    append_jsonl_line(p.lifecycle_jsonl, event.model_dump())
    return event


def iter_events(paths: DataPaths | None = None) -> Iterator[LifecycleEvent]:
    """Yield parseable events; skip blank lines; skip still-bad lines."""
    p = paths or require_ada_data()
    ensure_ledger_ready(p)
    path = p.lifecycle_jsonl
    if not path.is_file():
        return
    import json

    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            try:
                yield LifecycleEvent.model_validate(obj)
            except Exception:
                continue


def read_events(paths: DataPaths | None = None) -> list[LifecycleEvent]:
    return list(iter_events(paths))


def tail(n: int = 20, paths: DataPaths | None = None) -> list[LifecycleEvent]:
    events = read_events(paths)
    if n <= 0:
        return []
    return events[-n:]


def append_wake(
    *,
    paths: DataPaths | None = None,
    ensure_birth: bool = False,
) -> LifecycleEvent:
    p = paths or require_ada_data()
    if ensure_birth:
        from ada.body.identity import create_identity

        create_identity(paths=p)

    maybe_deploy(paths=p)

    details: dict[str, Any] = {
        "agent_version": __version__,
        "boot_id": _boot_id(),
        "pid": os.getpid(),
    }
    return append_event(
        "wake",
        summary="ada body service start",
        details=details,
        paths=p,
    )


def append_sleep(*, paths: DataPaths | None = None, summary: str = "ada body clean stop") -> LifecycleEvent:
    return append_event(
        "sleep",
        summary=summary,
        details={"agent_version": __version__, "pid": os.getpid()},
        paths=paths,
    )


def append_fault(
    summary: str,
    *,
    details: dict[str, Any] | None = None,
    paths: DataPaths | None = None,
) -> LifecycleEvent:
    return append_event("fault", summary=summary, details=details, paths=paths)


def append_note(summary: str, *, paths: DataPaths | None = None) -> LifecycleEvent:
    return append_event("note", summary=summary, paths=paths)


def maybe_deploy(*, paths: DataPaths | None = None) -> LifecycleEvent | None:
    """Emit deploy if package version differs from identity or last wake."""
    p = paths or require_ada_data()
    from ada.body.identity import identity_exists, load_identity

    previous: str | None = None
    if identity_exists(p):
        try:
            previous = load_identity(p).version
        except BodyFault:
            previous = None

    if previous is None:
        for ev in reversed(read_events(p)):
            if ev.type in {"wake", "deploy", "birth"}:
                previous = (
                    str(ev.details.get("agent_version"))
                    if ev.details.get("agent_version")
                    else None
                )
                if previous:
                    break

    if previous is None or previous == __version__:
        return None

    return append_event(
        "deploy",
        summary=f"agent version {previous} → {__version__}",
        details={"from": previous, "to": __version__},
        paths=p,
    )


def last_of_type(event_type: str, paths: DataPaths | None = None) -> LifecycleEvent | None:
    for ev in reversed(read_events(paths)):
        if ev.type == event_type:
            return ev
    return None
