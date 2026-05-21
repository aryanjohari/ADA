"""Read-only playbook registry helpers for operator UI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ada.config import _find_project_root
from ada.policy.load import load_merged_policy
from ada.workflow.playbook_resolve import load_playbook_registry_dict, resolve_playbook


def list_playbook_registry_rows(project_root: Path | None = None) -> list[dict[str, Any]]:
    """Safe metadata from playbooks/registry.yaml (no prompt injection)."""
    root = project_root if project_root is not None else _find_project_root()
    reg = load_playbook_registry_dict(root)
    playbooks = reg.get("playbooks")
    if not isinstance(playbooks, dict):
        return []
    rows: list[dict[str, Any]] = []
    for pid in sorted(playbooks.keys()):
        entry = playbooks[pid]
        if not isinstance(entry, dict):
            continue
        wf = entry.get("workflow_kind")
        desc = entry.get("description")
        risk = entry.get("risk_tier")
        allowed = entry.get("allowed_params")
        required = entry.get("required_params")
        rows.append(
            {
                "playbook_id": str(pid),
                "workflow_kind": str(wf) if wf is not None else "",
                "description": str(desc).strip() if isinstance(desc, str) else "",
                "risk_tier": str(risk).strip() if isinstance(risk, str) else "",
                "allowed_params": list(allowed) if isinstance(allowed, list) else [],
                "required_params": list(required) if isinstance(required, list) else [],
            }
        )
    return rows


def validate_mission_defaults_against_playbook(
    *,
    playbook_id: str,
    mission_defaults: dict[str, Any],
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Dry-run resolve_playbook; returns {ok, error?, resolved?}."""
    try:
        resolved = resolve_playbook(
            playbook_id,
            policy=load_merged_policy(),
            mission_defaults=mission_defaults,
            params_delta={},
            project_root=project_root,
        )
        return {
            "ok": True,
            "playbook_id": resolved.playbook_id,
            "workflow_kind": resolved.workflow_kind,
            "params": resolved.params,
            "risk_tier": resolved.risk_tier,
        }
    except ValueError as e:
        return {"ok": False, "error": str(e)}
