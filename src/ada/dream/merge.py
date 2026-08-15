"""Whitelist auto-merge + stage everything else. Never touch born_at."""

from __future__ import annotations

from typing import Any

from ada.io.paths import DataPaths, require_ada_data
from ada.memory.facts import SACRED_IDENTITY_KEYS, WHITELIST_KEYS, append_fact, propose_edit
from ada.memory.staging import stage_candidate
from ada.memory.worldview import write_digest


def _normalize_candidate(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    key = raw.get("key") or raw.get("field")
    if not key:
        return None
    key = str(key).strip()
    if key.startswith("prefs."):
        field = key.split(".", 1)[1]
    else:
        field = key
        key = f"prefs.{field}"
    return {"key": key, "field": field, "value": raw.get("value")}


def _head_cite_ref(head: dict[str, Any]) -> str | None:
    cid = head.get("id") or head.get("cite_id")
    if not cid:
        return None
    if head.get("extract_ok") is False:
        return None
    status = str(head.get("extract_status") or "")
    if status in {"js_shell", "empty", "feed_blob"}:
        return None
    return f"cite:{cid}" if not str(cid).startswith("cite:") else str(cid)


def _group_heads(
    heads: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for h in heads:
        key = str(h.get("campaign_id") or h.get("watch_id") or "ungrouped")
        grouped.setdefault(key, []).append(h)
    return grouped


def _base_dream_cites(dream_id: str | None) -> list[str]:
    return [
        "facts/prefs.yaml",
        f"dream:{dream_id}" if dream_id else "dream:local",
        "lifecycle:dream",
    ]


def apply_manage_result(
    manage_result: dict[str, Any] | None,
    *,
    paths: DataPaths | None = None,
    dream_id: str | None = None,
    delta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge whitelist FACT candidates; stage rest; write WORLDVIEW digests."""
    p = paths or require_ada_data()
    merged: list[dict[str, Any]] = []
    staged: list[dict[str, Any]] = []
    conflicts: list[str] = []
    digest_path = None
    campaign_digest_paths: list[str] = []

    if not manage_result:
        return {
            "merged": merged,
            "staged": staged,
            "conflicts": conflicts,
            "digest_path": digest_path,
            "campaign_digest_paths": campaign_digest_paths,
            "manage_applied": False,
        }

    for raw in manage_result.get("conflicts") or []:
        conflicts.append(str(raw))

    for raw in manage_result.get("fact_candidates") or []:
        cand = _normalize_candidate(raw)
        if cand is None:
            staged.append(
                stage_candidate(
                    {"raw": raw},
                    reason="malformed_fact_candidate",
                    paths=p,
                )
            )
            continue
        field = cand["field"]
        if field in SACRED_IDENTITY_KEYS or field == "born_at":
            staged.append(
                stage_candidate(
                    cand,
                    reason="sacred_identity_denied",
                    paths=p,
                )
            )
            continue
        if field.startswith("people") or "people/" in cand["key"]:
            staged.append(
                stage_candidate(cand, reason="people_always_stage", paths=p)
            )
            continue
        if field not in WHITELIST_KEYS:
            staged.append(
                stage_candidate(cand, reason="non_whitelist", paths=p)
            )
            continue
        # Whitelist — try append without silent overwrite of conflicts.
        try:
            result = append_fact(
                cand["key"], cand["value"], paths=p, allow_prefs_update=False
            )
        except Exception as exc:  # noqa: BLE001
            staged.append(
                stage_candidate(
                    {**cand, "error": str(exc)},
                    reason="append_error",
                    paths=p,
                )
            )
            continue
        if result.get("needs_confirm"):
            staged.append(
                stage_candidate(
                    {
                        **cand,
                        "existing": result.get("existing"),
                        "proposed": result.get("proposed"),
                    },
                    reason="conflict_needs_confirm",
                    paths=p,
                )
            )
            conflicts.append(
                f"{cand['key']}: existing={result.get('existing')!r} "
                f"proposed={result.get('proposed')!r}"
            )
            continue
        if result.get("ok"):
            merged.append(result)
        else:
            staged.append(
                stage_candidate(cand, reason=result.get("reason") or "merge_denied", paths=p)
            )

    # M06: stage all open_loops / campaign proposals — never auto-upsert or auto-done.
    for raw in manage_result.get("open_loops") or []:
        staged.append(
            stage_candidate(
                {"open_loop": raw} if not isinstance(raw, dict) else dict(raw),
                reason="dream_open_loop_proposal",
                paths=p,
            )
        )

    heads = list((delta or {}).get("cite_heads") or [])
    by_campaign = (delta or {}).get("cite_heads_by_campaign") or _group_heads(heads)
    model_campaign: dict[str, dict[str, Any]] = {}
    for raw in manage_result.get("campaign_digests") or []:
        if not isinstance(raw, dict):
            continue
        cid = str(raw.get("campaign_id") or "").strip()
        if not cid or cid == "ungrouped":
            continue
        model_campaign[cid] = raw

    # M11-B: per-campaign WORLDVIEW when heads are grouped by campaign_id.
    # extract_ok → cite:c_…; js_shell/empty/feed_blob-only still get an honest
    # unreadability file (no shell cite: from heads; no invented claims).
    for camp_id, camp_heads in by_campaign.items():
        if not camp_id or camp_id == "ungrouped":
            continue
        if not camp_heads:
            continue
        cite_refs: list[str] = []
        for h in camp_heads:
            ref = _head_cite_ref(h)
            if ref and ref not in cite_refs:
                cite_refs.append(ref)
        cd = model_campaign.get(camp_id) or {}
        for extra in cd.get("cites") or []:
            s = str(extra).strip()
            if not s:
                continue
            ref = s if s.startswith("cite:") else f"cite:{s}"
            if ref not in cite_refs:
                cite_refs.append(ref)
        body = (cd.get("digest") or "").strip()
        if not body:
            if cite_refs:
                body = (
                    f"Cite heads ingested for campaign {camp_id} "
                    f"({len(cite_refs)} citable)."
                )
            else:
                status_counts: dict[str, int] = {}
                for h in camp_heads:
                    st = str(h.get("extract_status") or "unknown")
                    status_counts[st] = status_counts.get(st, 0) + 1
                parts = ", ".join(
                    f"{k}×{v}" for k, v in sorted(status_counts.items())
                )
                body = (
                    f"Campaign {camp_id}: {len(camp_heads)} cite head(s) in window"
                    f" ({parts}); none extract_ok — pages not readable; "
                    f"no claims from shells/blobs."
                )
        cites = _base_dream_cites(dream_id) + cite_refs
        try:
            wv = write_digest(
                body,
                cites=cites,
                title=f"Campaign digest ({camp_id})",
                dream=False,
                campaign_id=camp_id,
                paths=p,
            )
            if wv.get("path"):
                campaign_digest_paths.append(str(wv["path"]))
        except Exception as exc:  # noqa: BLE001
            conflicts.append(f"campaign_worldview_write_fail:{camp_id}: {exc}")

    digest = (manage_result.get("digest") or "").strip()
    notes = manage_result.get("worldview_notes") or []
    # Global prefs / night digest — thin; still attach ungrouped + all extract_ok cites.
    if digest or notes or heads:
        body_parts = []
        if digest:
            body_parts.append(digest)
        elif heads and not notes:
            body_parts.append(
                "Dream night: cite heads present; see per-campaign WORLDVIEW when grouped."
            )
        if notes:
            body_parts.append("Notes:\n" + "\n".join(f"- {n}" for n in notes))
        if conflicts:
            body_parts.append(
                "Conflicts (staged, not merged):\n"
                + "\n".join(f"- {c}" for c in conflicts)
            )
        cites = _base_dream_cites(dream_id)
        for head in heads:
            ref = _head_cite_ref(head)
            if ref and ref not in cites:
                cites.append(ref)
        if body_parts:
            try:
                wv = write_digest(
                    "\n\n".join(body_parts),
                    cites=cites,
                    title="Dream digest",
                    dream=True,
                    paths=p,
                )
                digest_path = wv.get("path")
            except Exception as exc:  # noqa: BLE001
                conflicts.append(f"worldview_write_fail: {exc}")

    return {
        "merged": merged,
        "staged": staged,
        "conflicts": conflicts,
        "digest_path": digest_path,
        "campaign_digest_paths": campaign_digest_paths,
        "manage_applied": True,
    }


# Re-export for tests that confirm overwrite path exists.
__all__ = ["apply_manage_result", "propose_edit"]
