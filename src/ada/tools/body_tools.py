"""Thin wrappers → ada.body.* organs. No second vitals stack."""

from __future__ import annotations

import re
from typing import Any

from ada.body import identity as identity_mod
from ada.body import lifecycle as lifecycle_mod
from ada.body import narrative
from ada.body.readonly_cmd import result_to_dict, run_readonly_cmd
from ada.body.vitals import collect_vitals, urgent_faults
from ada.io.paths import BodyFault, ada_data_mounted, get_paths

# Question-class keywords for body_explain (thin router — not a second probe stack).
_CLASS_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "refuse_secret",
        re.compile(
            r"(ssh\s*keys?|~/?\.ssh|/etc/shadow|api[_\s-]?keys?|auth[_\s-]?keys?|"
            r"tailscale\s+auth|password|secrets?|credentials?)",
            re.I,
        ),
    ),
    (
        "refuse_admin",
        re.compile(
            r"\b(apt(-get)?|sudo|systemctl\s+(start|stop|restart|enable|disable)|"
            r"install\s+package|rewrite\s+(the\s+)?system|mount\s+/|dd\s+if=)\b",
            re.I,
        ),
    ),
    (
        "story",
        re.compile(
            r"\b(born|birth|wake|woke|autobiograph|lifecycle|story|"
            r"recent\s+(events?|history)|when\s+were\s+you\s+born)\b",
            re.I,
        ),
    ),
    (
        "identity",
        re.compile(
            r"\b(whoami|who\s+are\s+you|what\s+are\s+you|board|model|os\b|"
            r"operating\s+system|hostname|identity|kernel)\b",
            re.I,
        ),
    ),
    (
        "network",
        re.compile(
            r"\b(tailscale|ip\s*address|network|iface|wlan|eth0|ipv4)\b",
            re.I,
        ),
    ),
    (
        "capacity",
        re.compile(
            r"\b(cores?|cpus?|nproc|arch|ram|memory|mem_total|disks?|ada-?data|"
            r"how\s+much\s+(free|ram)|capacity|uptime)\b",
            re.I,
        ),
    ),
    (
        "health",
        re.compile(
            r"\b(health|healthy|throttl\w*|temp|temperature|doctor|"
            r"urgent|under.?voltage|fault|ok\?|are\s+you\s+(ok|healthy|fine))\b",
            re.I,
        ),
    ),
]


def _vitals_summary(snap_dict: dict[str, Any]) -> dict[str, Any]:
    """Compact subset for section=summary — glue only; organs own probes."""
    host = snap_dict.get("host") or {}
    thermal = snap_dict.get("thermal") or {}
    memory = snap_dict.get("memory") or {}
    mounts = snap_dict.get("mounts") or {}
    load = snap_dict.get("load") or {}
    extras = snap_dict.get("extras") or {}
    disks = snap_dict.get("disks") or []
    bits = thermal.get("throttled_bits") or {}

    out: dict[str, Any] = {
        "ts": snap_dict.get("ts"),
        "hostname": host.get("hostname"),
        "cpu_count": extras.get("cpu_count"),
        "arch": extras.get("arch"),
        "uptime_s": extras.get("uptime_s"),
        "temp_c": thermal.get("temp_c"),
        "throttled_hex": thermal.get("throttled_hex"),
        "under_voltage_now": thermal.get("under_voltage_now"),
        "throttled_now": bits.get("throttled_now") if isinstance(bits, dict) else None,
        "mem_total_bytes": memory.get("mem_total_bytes"),
        "mem_available_bytes": memory.get("mem_available_bytes"),
        "load1": load.get("load1"),
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
    ts_ip = extras.get("tailscale_ipv4")
    if ts_ip:
        out["tailscale_ipv4"] = ts_ip
    # Truncated machine_id stays in full extras only — never promote to summary.
    return out


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


def _doctor_note(urgent: list[str], probe_errors: list[Any]) -> str:
    """Short CLI/tool text — not a prose essay organ."""
    if urgent:
        return "urgent: " + "; ".join(urgent)
    if probe_errors:
        return f"probe issues ({len(probe_errors)}); no urgent faults"
    return "all clear"


def run_body_doctor() -> dict[str, Any]:
    """Mirror CLI doctor checks — structured JSON, no re-probing beyond organs."""
    paths = get_paths()
    mounted = ada_data_mounted(paths.root)
    snap = collect_vitals()
    urgent = urgent_faults(snap)
    probe_errors = [e.model_dump() for e in snap.probe_errors]
    return {
        "ADA_DATA_ROOT": str(paths.root),
        "mounted": mounted,
        "ada_data_ok": snap.mounts.ada_data_ok,
        "probe_errors": probe_errors,
        "urgent": urgent,
        "note": _doctor_note(urgent, probe_errors),
        "vitals_ts": snap.ts,
        "temp_c": snap.thermal.temp_c,
    }


def classify_body_question(question: str) -> str:
    """Map a fuzzy host question to a body_explain class."""
    q = (question or "").strip()
    if not q:
        return "health"
    for cls, pat in _CLASS_PATTERNS:
        if pat.search(q):
            return cls
    # Fuzzy defaults per M12: "what are you?" / "are you healthy?" covered above;
    # bare unknown → capacity+health via health class (doctor + vitals).
    return "health"


def run_body_explain(*, question: str = "") -> dict[str, Any]:
    """Thin router over organs — calls collect_vitals / whoami / doctor / story helpers."""
    cls = classify_body_question(question)
    sources: list[str] = []
    short_facts: dict[str, Any] = {"class": cls}

    if cls == "refuse_secret":
        return {
            "class": cls,
            "short_facts": {
                "refused": True,
                "reason": "secrets never-to-cloud (ssh keys, shadow, API/auth keys)",
            },
            "sources": [],
            "ok": True,
        }
    if cls == "refuse_admin":
        return {
            "class": cls,
            "short_facts": {
                "refused": True,
                "reason": "admin/mutate actions are out of body proprioception scope",
            },
            "sources": [],
            "ok": True,
        }

    if cls in ("capacity", "health", "network", "identity"):
        summary = run_body_vitals(section="summary")
        sources.append("body_vitals:summary")
        if cls == "capacity":
            short_facts.update(
                {
                    "cpu_count": summary.get("cpu_count"),
                    "arch": summary.get("arch"),
                    "mem_total_bytes": summary.get("mem_total_bytes"),
                    "mem_available_bytes": summary.get("mem_available_bytes"),
                    "uptime_s": summary.get("uptime_s"),
                    "disks": summary.get("disks"),
                    "ada_data_ok": summary.get("ada_data_ok"),
                    "probe_error_count": summary.get("probe_error_count"),
                }
            )
        elif cls == "health":
            doctor = run_body_doctor()
            sources.append("body_doctor")
            short_facts.update(
                {
                    "temp_c": summary.get("temp_c"),
                    "throttled_hex": summary.get("throttled_hex"),
                    "under_voltage_now": summary.get("under_voltage_now"),
                    "throttled_now": summary.get("throttled_now"),
                    "load1": summary.get("load1"),
                    "ada_data_ok": summary.get("ada_data_ok"),
                    "urgent": doctor.get("urgent"),
                    "note": doctor.get("note"),
                    "probe_error_count": summary.get("probe_error_count"),
                }
            )
        elif cls == "network":
            short_facts.update(
                {
                    "tailscale_ipv4": summary.get("tailscale_ipv4"),
                    "hostname": summary.get("hostname"),
                }
            )
            full = run_body_vitals(section="full")
            sources.append("body_vitals:full")
            net = full.get("net") or {}
            short_facts["ifaces"] = [
                {
                    "name": i.get("name"),
                    "operstate": i.get("operstate"),
                    "ipv4": i.get("ipv4"),
                }
                for i in (net.get("ifaces") or [])
            ]
        elif cls == "identity":
            try:
                who = run_body_whoami()
                sources.append("body_whoami")
                short_facts.update(
                    {
                        "name": who.get("name"),
                        "board_model": who.get("board_model"),
                        "os": who.get("os"),
                        "kernel": who.get("kernel"),
                        "born_at": who.get("born_at"),
                        "body_hostname": who.get("body_hostname"),
                    }
                )
            except BodyFault as exc:
                short_facts["identity_error"] = exc.message
            # Capacity hints often asked with "what are you?"
            short_facts["cpu_count"] = summary.get("cpu_count")
            short_facts["arch"] = summary.get("arch")

    if cls == "story":
        try:
            who = run_body_whoami()
            sources.append("body_whoami")
            short_facts["born_at"] = who.get("born_at")
            short_facts["name"] = who.get("name")
        except BodyFault as exc:
            short_facts["identity_error"] = exc.message
        story = run_body_story(n=10)
        sources.append("body_story")
        short_facts["story"] = story.get("story")
        short_facts["event_count"] = story.get("event_count")

    return {
        "class": cls,
        "short_facts": short_facts,
        "sources": sources,
        "ok": True,
    }


def run_body_readonly_cmd(*, argv: list[str] | None = None) -> dict[str, Any]:
    """Allowlisted read-only host cmd — fallback when typed vitals insufficient."""
    tokens = list(argv or [])
    result = run_readonly_cmd(tokens)
    return result_to_dict(result)


DISPATCH = {
    "body_vitals": lambda args: run_body_vitals(section=args.get("section", "summary")),
    "body_whoami": lambda args: run_body_whoami(),
    "body_story": lambda args: run_body_story(n=args.get("n", 20)),
    "body_doctor": lambda args: run_body_doctor(),
    "body_explain": lambda args: run_body_explain(question=args.get("question", "")),
    "body_readonly_cmd": lambda args: run_body_readonly_cmd(argv=args.get("argv") or []),
}
