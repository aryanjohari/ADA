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


def apply_manage_result(
    manage_result: dict[str, Any] | None,
    *,
    paths: DataPaths | None = None,
    dream_id: str | None = None,
    delta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge whitelist FACT candidates; stage rest; write WORLDVIEW digest if any."""
    p = paths or require_ada_data()
    merged: list[dict[str, Any]] = []
    staged: list[dict[str, Any]] = []
    conflicts: list[str] = []
    digest_path = None

    if not manage_result:
        return {
            "merged": merged,
            "staged": staged,
            "conflicts": conflicts,
            "digest_path": digest_path,
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

    digest = (manage_result.get("digest") or "").strip()
    notes = manage_result.get("worldview_notes") or []
    if digest or notes:
        body_parts = []
        if digest:
            body_parts.append(digest)
        if notes:
            body_parts.append("Notes:\n" + "\n".join(f"- {n}" for n in notes))
        if conflicts:
            body_parts.append(
                "Conflicts (staged, not merged):\n"
                + "\n".join(f"- {c}" for c in conflicts)
            )
        cites = [
            "facts/prefs.yaml",
            f"dream:{dream_id}" if dream_id else "dream:local",
            "lifecycle:dream",
        ]
        # M10 F4: web claims from this night's cite heads must cite cite:c_…
        for head in (delta or {}).get("cite_heads") or []:
            cid = head.get("id") or head.get("cite_id")
            if not cid:
                continue
            if head.get("extract_ok") is False:
                continue
            status = str(head.get("extract_status") or "")
            if status in {"js_shell", "empty", "feed_blob"}:
                continue
            ref = f"cite:{cid}" if not str(cid).startswith("cite:") else str(cid)
            if ref not in cites:
                cites.append(ref)
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
        "manage_applied": True,
    }


# Re-export for tests that confirm overwrite path exists.
__all__ = ["apply_manage_result", "propose_edit"]
