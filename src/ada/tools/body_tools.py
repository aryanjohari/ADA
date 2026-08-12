"""Thin wrappers → ada.body.* organs. No second vitals stack."""

from __future__ import annotations

from typing import Any

from ada.body import identity as identity_mod
from ada.body import lifecycle as lifecycle_mod
from ada.body import narrative
from ada.body.vitals import collect_vitals, urgent_faults
from ada.io.paths import BodyFault, ada_data_mounted, get_paths


def _vitals_summary(snap_dict: dict[str, Any]) -> dict[str, Any]:
    """Compact subset for section=summary — glue only; organs own probes."""
    host = snap_dict.get("host") or {}
    thermal = snap_dict.get("thermal") or {}
    memory = snap_dict.get("memory") or {}
    mounts = snap_dict.get("mounts") or {}
    disks = snap_dict.get("disks") or []
    return {
        "ts": snap_dict.get("ts"),
        "hostname": host.get("hostname"),
        "temp_c": thermal.get("temp_c"),
        "throttled_hex": thermal.get("throttled_hex"),
        "mem_available_bytes": memory.get("mem_available_bytes"),
        "ada_data_ok": mounts.get("ada_data_ok"),
        "disks": [
            {
                "label": d.get("label"),
                "mount": d.get("mount"),
                "avail_bytes": d.get("avail_bytes"),
                "total_bytes": d.get("total_bytes"),
            }
            for d in disks
        ],
        "probe_error_count": len(snap_dict.get("probe_errors") or []),
    }


def run_body_vitals(*, section: str = "summary") -> dict[str, Any]:
    snap = collect_vitals()
    dumped = snap.model_dump()
    sec = (section or "summary").lower()
    if sec == "full":
        return dumped
    return _vitals_summary(dumped)


def run_body_whoami() -> dict[str, Any]:
    try:
        card = identity_mod.load_identity()
    except BodyFault as exc:
        raise BodyFault(exc.message, code=exc.code) from exc
    return card.model_dump()


def run_body_story(*, n: int = 20) -> dict[str, Any]:
    n = int(n) if n is not None else 20
    if n < 0:
        n = 0
    events = lifecycle_mod.tail(n)
    text = narrative.story(events, n=n)
    return {
        "n": n,
        "event_count": len(events),
        "story": text,
        "events": [ev.model_dump() for ev in events],
    }


def run_body_doctor() -> dict[str, Any]:
    """Mirror CLI doctor checks — structured JSON, no re-probing beyond organs."""
    paths = get_paths()
    mounted = ada_data_mounted(paths.root)
    snap = collect_vitals()
    urgent = urgent_faults(snap)
    return {
        "ADA_DATA_ROOT": str(paths.root),
        "mounted": mounted,
        "ada_data_ok": snap.mounts.ada_data_ok,
        "probe_errors": [e.model_dump() for e in snap.probe_errors],
        "urgent": urgent,
        "vitals_ts": snap.ts,
        "temp_c": snap.thermal.temp_c,
    }


DISPATCH = {
    "body_vitals": lambda args: run_body_vitals(section=args.get("section", "summary")),
    "body_whoami": lambda args: run_body_whoami(),
    "body_story": lambda args: run_body_story(n=args.get("n", 20)),
    "body_doctor": lambda args: run_body_doctor(),
}
