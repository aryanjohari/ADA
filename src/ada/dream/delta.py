"""Delta since last dream_ok — not full history replay.

M10: include per-watch/campaign cite heads (not prefs-only mush).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ada.body.lifecycle import LifecycleEvent, read_events
from ada.io.paths import DataPaths, require_ada_data

# Library section budget inside the manage input (prefs/lifecycle stay small).
MAX_CITE_HEADS = 20
MAX_LIBRARY_SUMMARY_CHARS = 8_000
FIRST_CHUNK_CHARS = 400


def last_dream_ok(paths: DataPaths | None = None) -> LifecycleEvent | None:
    for ev in reversed(read_events(paths)):
        if ev.type == "dream_ok":
            return ev
    return None


def _mtime_iso(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def _group_cite_heads(heads: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for h in heads:
        key = str(h.get("campaign_id") or h.get("watch_id") or "ungrouped")
        grouped.setdefault(key, []).append(h)
    return grouped


def build_delta(
    *,
    paths: DataPaths | None = None,
    since_ts: str | None = None,
) -> dict[str, Any]:
    """Collect a bounded delta package summary since last dream_ok (or *since_ts*).

    Caps: recent lifecycle events, recent run files by mtime, FACT/WORLDVIEW
    file listing, per-campaign cite heads — never dumps entire runs/ or full
    extracts into manage.
    """
    p = paths or require_ada_data()
    last = last_dream_ok(p)
    since = since_ts or (last.ts if last else None)

    lifecycle_new: list[dict[str, Any]] = []
    for ev in read_events(p):
        if since and ev.ts <= since:
            continue
        if ev.type in {"dream_ok", "dream_fail"}:
            continue
        lifecycle_new.append(
            {"id": ev.id, "ts": ev.ts, "type": ev.type, "summary": ev.summary}
        )
    # Cap lifecycle delta.
    lifecycle_new = lifecycle_new[-100:]

    fact_files: list[dict[str, Any]] = []
    if p.facts.is_dir():
        for path in sorted(p.facts.rglob("*.yaml")):
            fact_files.append(
                {
                    "path": str(path.relative_to(p.memory)),
                    "mtime": _mtime_iso(path),
                    "bytes": path.stat().st_size if path.is_file() else 0,
                }
            )

    worldview_files: list[dict[str, Any]] = []
    for root_name, root in (("worldview", p.worldview), ("dreams", p.dreams)):
        if not root.is_dir():
            continue
        for path in sorted(root.glob("*.md")):
            worldview_files.append(
                {
                    "path": f"{root_name}/{path.name}",
                    "mtime": _mtime_iso(path),
                    "bytes": path.stat().st_size,
                }
            )

    run_files: list[dict[str, Any]] = []
    if p.runs.is_dir():
        all_runs = sorted(p.runs.rglob("*.jsonl"), key=_mtime_iso, reverse=True)
        for path in all_runs[:20]:  # newest 20 only
            run_files.append(
                {
                    "path": str(path.relative_to(p.runs)),
                    "mtime": _mtime_iso(path),
                    "bytes": path.stat().st_size,
                }
            )

    # Prefs snapshot (small; always include for manage context).
    prefs_snapshot: dict[str, Any] = {}
    if p.prefs_yaml.is_file():
        try:
            import yaml

            raw = yaml.safe_load(p.prefs_yaml.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                prefs_snapshot = {
                    k: raw[k]
                    for k in (
                        "brief_time",
                        "quiet_hours_start",
                        "quiet_hours_end",
                        "mute_proactivity",
                        "tease_ok",
                        "preferred_tz",
                        "brief_enabled",
                        "roast_energy",
                        "humor_density",
                        "chill_immediate",
                        "humor_banned_topics",
                    )
                    if k in raw
                }
        except Exception:  # noqa: BLE001
            prefs_snapshot = {}

    cite_heads: list[dict[str, Any]] = []
    try:
        from ada.web.cites import cite_heads_since

        cite_heads = cite_heads_since(
            paths=p,
            since=since,
            max_heads=MAX_CITE_HEADS,
            first_chunk_chars=FIRST_CHUNK_CHARS,
        )
    except Exception:  # noqa: BLE001 — delta must not fail closed on cites
        cite_heads = []

    cite_heads_by_campaign = _group_cite_heads(cite_heads)

    return {
        "since": since,
        "last_dream_ok_id": last.id if last else None,
        "lifecycle_events": lifecycle_new,
        "lifecycle_count": len(lifecycle_new),
        "fact_files": fact_files,
        "worldview_files": worldview_files,
        "run_files": run_files,
        "prefs_snapshot": prefs_snapshot,
        "cite_heads": cite_heads,
        "cite_heads_by_campaign": cite_heads_by_campaign,
        "cite_head_count": len(cite_heads),
        "summary_text": _summary_text(
            since=since,
            lifecycle_count=len(lifecycle_new),
            fact_n=len(fact_files),
            wv_n=len(worldview_files),
            run_n=len(run_files),
            prefs=prefs_snapshot,
            lifecycle_tail=lifecycle_new[-10:],
            cite_heads_by_campaign=cite_heads_by_campaign,
        ),
    }


def _format_cite_library_section(
    cite_heads_by_campaign: dict[str, list[dict[str, Any]]],
    *,
    max_chars: int = MAX_LIBRARY_SUMMARY_CHARS,
) -> str:
    if not cite_heads_by_campaign:
        return "cite_heads: (none since last dream)"
    lines = ["cite_heads_by_campaign:"]
    used = 0
    for camp, heads in cite_heads_by_campaign.items():
        header = f"  campaign/watch={camp}:"
        lines.append(header)
        used += len(header) + 1
        for h in heads:
            status = h.get("extract_status") or "?"
            ok = h.get("extract_ok")
            chunk = (h.get("first_chunk") or "").replace("\n", " ")
            row = (
                f"    - cite:{h.get('id')} status={status} extract_ok={ok} "
                f"title={h.get('title')!r} url={h.get('url')} "
                f"chunk={chunk!r}"
            )
            if used + len(row) + 1 > max_chars:
                lines.append("    - …(cite heads truncated)")
                return "\n".join(lines)
            lines.append(row)
            used += len(row) + 1
    return "\n".join(lines)


def _summary_text(
    *,
    since: str | None,
    lifecycle_count: int,
    fact_n: int,
    wv_n: int,
    run_n: int,
    prefs: dict[str, Any],
    lifecycle_tail: list[dict[str, Any]],
    cite_heads_by_campaign: dict[str, list[dict[str, Any]]] | None = None,
) -> str:
    lines = [
        f"Dream delta since={since or 'BEGINNING'}",
        f"lifecycle_new={lifecycle_count} fact_yaml={fact_n} worldview_md={wv_n} run_files_capped={run_n}",
        f"prefs={json.dumps(prefs, ensure_ascii=False)}",
        "recent_lifecycle:",
    ]
    for ev in lifecycle_tail:
        lines.append(f"  - {ev.get('ts')} {ev.get('type')}: {ev.get('summary')}")
    lines.append(
        _format_cite_library_section(cite_heads_by_campaign or {})
    )
    lines.append(
        "Rules: web claims in digest/notes MUST cite cite:c_… ids from cite_heads; "
        "do not invent numbers when extract_ok is false; abs_html = abstract page not PDF; "
        "keep digests short — never paste full page text."
    )
    return "\n".join(lines)
