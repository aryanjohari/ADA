"""Versioned playbook registry merge + validation (single enqueue resolution funnel)."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

import yaml

from ada.config import _find_project_root
from ada.policy.load import PolicyConfig
from ada.workflow.templates import WORKFLOW_KINDS, validate_and_normalize_workflow_params

# PolicyConfig attrs allowed in registry policy_bindings (extend when new keys are needed).
POLICY_BINDING_FIELDS: frozenset[str] = frozenset({"graph_lite_max_items_per_job"})

_REGISTRY_REL_PATH = Path("playbooks") / "registry.yaml"


@dataclass(frozen=True)
class ResolvedEnqueue:
    """Output of playbook resolution before template expansion."""

    playbook_id: str
    workflow_kind: str
    params: dict[str, Any]
    description: str
    risk_tier: str | None


def registry_path(project_root: Path | None = None) -> Path:
    root = project_root if project_root is not None else _find_project_root()
    return (root / _REGISTRY_REL_PATH).resolve()


def clear_playbook_registry_cache() -> None:
    """Drop cached registry (tests that rewrite files)."""
    _load_registry_yaml.cache_clear()


@lru_cache(maxsize=8)
def _load_registry_yaml(path_str: str) -> dict[str, Any]:
    path = Path(path_str)
    raw = path.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid playbook registry YAML: {path}: {e}") from e
    if not isinstance(data, dict):
        raise ValueError(f"Playbook registry root must be a mapping: {path}")
    return data


def load_playbook_registry_dict(project_root: Path | None = None) -> dict[str, Any]:
    p = registry_path(project_root)
    if not p.is_file():
        raise ValueError(
            f"Playbook registry not found: {p}. Create playbooks/registry.yaml in the project root."
        )
    return _load_registry_yaml(str(p))


def _playbook_entry(reg: dict[str, Any], playbook_id: str) -> dict[str, Any]:
    playbooks = reg.get("playbooks")
    if not isinstance(playbooks, dict):
        raise ValueError("playbook registry: 'playbooks' must be a mapping")
    entry = playbooks.get(playbook_id)
    if not isinstance(entry, dict):
        return {}
    return entry


def _known_playbook_ids(reg: dict[str, Any]) -> list[str]:
    playbooks = reg.get("playbooks")
    if not isinstance(playbooks, dict):
        return []
    return sorted(str(k) for k in playbooks)


def _policy_defaults_for_playbook(
    entry: dict[str, Any], policy: PolicyConfig
) -> dict[str, Any]:
    bindings = entry.get("policy_bindings") or {}
    if not isinstance(bindings, dict):
        raise ValueError("policy_bindings must be a mapping when present")
    out: dict[str, Any] = {}
    for param_name, field_name in bindings.items():
        if not isinstance(param_name, str) or not isinstance(field_name, str):
            raise ValueError("policy_bindings keys and values must be strings")
        if field_name not in POLICY_BINDING_FIELDS:
            raise ValueError(
                f"Unknown PolicyConfig field in policy_bindings: {field_name!r} "
                f"(playbook entry {entry!r})"
            )
        out[param_name] = getattr(policy, field_name)
    return out


def _merge_layers(
    policy_layer: dict[str, Any],
    mission_defaults: Mapping[str, Any],
    params_delta: Mapping[str, Any],
) -> dict[str, Any]:
    merged: dict[str, Any] = dict(policy_layer)
    merged.update(dict(mission_defaults))
    merged.update(dict(params_delta))
    return merged


def _validate_allowed_and_required(
    *,
    playbook_id: str,
    merged: dict[str, Any],
    allowed: set[str],
    required: list[str],
) -> None:
    unknown = [k for k in sorted(merged) if k not in allowed]
    if unknown:
        raise ValueError(
            f"Playbook {playbook_id!r}: unknown param key(s): {unknown}. "
            f"Allowed: {sorted(allowed)}. Fix mission defaults or params_json."
        )
    missing: list[str] = []
    for key in required:
        if key not in merged:
            missing.append(key)
            continue
        val = merged[key]
        if val is None:
            missing.append(key)
        elif isinstance(val, str) and key in (
            "project_id",
            "campaign_id",
            "niche",
        ):
            if not str(val).strip():
                missing.append(key)
    if missing:
        raise ValueError(
            f"Playbook {playbook_id!r}: missing or empty required param(s): {missing}"
        )


def resolve_playbook(
    playbook_id: str,
    *,
    policy: PolicyConfig,
    mission_defaults: Mapping[str, Any],
    params_delta: Mapping[str, Any],
    project_root: Path | None = None,
) -> ResolvedEnqueue:
    """
    Merge policy bindings → mission defaults → explicit deltas; validate keys and values.
    """
    pid = str(playbook_id).strip()
    if not pid:
        raise ValueError("playbook_id must be non-empty")

    reg = load_playbook_registry_dict(project_root)
    rp = registry_path(project_root)
    entry = _playbook_entry(reg, pid)
    if not entry:
        known = _known_playbook_ids(reg)
        raise ValueError(
            f"Unknown playbook_id {pid!r}. Known playbooks: {known}. "
            f"See {rp}"
        )

    wf_kind = entry.get("workflow_kind")
    if not isinstance(wf_kind, str) or not wf_kind.strip():
        raise ValueError(f"Playbook {pid!r}: invalid workflow_kind")
    wf_kind = wf_kind.strip()
    if wf_kind not in WORKFLOW_KINDS:
        raise ValueError(
            f"Playbook {pid!r}: workflow_kind {wf_kind!r} not in WORKFLOW_KINDS"
        )

    desc = entry.get("description")
    if not isinstance(desc, str):
        desc = ""
    risk = entry.get("risk_tier")
    risk_tier = str(risk).strip() if isinstance(risk, str) and risk.strip() else None

    allowed_raw = entry.get("allowed_params")
    if not isinstance(allowed_raw, list) or not all(
        isinstance(x, str) and x.strip() for x in allowed_raw
    ):
        raise ValueError(f"Playbook {pid!r}: allowed_params must be a list of non-empty strings")
    allowed = {str(x).strip() for x in allowed_raw}

    req_raw = entry.get("required_params")
    if req_raw is None:
        required: list[str] = []
    elif isinstance(req_raw, list) and all(isinstance(x, str) and x.strip() for x in req_raw):
        required = [str(x).strip() for x in req_raw]
    else:
        raise ValueError(f"Playbook {pid!r}: required_params must be a list of strings")
    for r in required:
        if r not in allowed:
            raise ValueError(
                f"Playbook {pid!r}: required param {r!r} must appear in allowed_params"
            )

    policy_layer = _policy_defaults_for_playbook(entry, policy)
    merged = _merge_layers(policy_layer, mission_defaults, params_delta)
    _validate_allowed_and_required(
        playbook_id=pid, merged=merged, allowed=allowed, required=required
    )
    normalized = validate_and_normalize_workflow_params(wf_kind, merged)
    return ResolvedEnqueue(
        playbook_id=pid,
        workflow_kind=wf_kind,
        params=normalized,
        description=desc.strip(),
        risk_tier=risk_tier,
    )


def resolve_for_kind(
    kind: str,
    *,
    policy: PolicyConfig,
    mission_defaults: Mapping[str, Any],
    params_delta: Mapping[str, Any],
    project_root: Path | None = None,
) -> ResolvedEnqueue:
    """Resolve the default playbook for a workflow kind (tool / matrix / legacy CLI)."""
    k = str(kind).strip()
    if not k:
        raise ValueError("workflow kind must be non-empty")

    reg = load_playbook_registry_dict(project_root)
    rp = registry_path(project_root)
    kmap = reg.get("kind_default_playbook")
    if not isinstance(kmap, dict):
        raise ValueError(f"Invalid kind_default_playbook in registry: {rp}")
    pid_raw = kmap.get(k)
    if not isinstance(pid_raw, str) or not pid_raw.strip():
        known_kinds = sorted(str(x) for x in kmap)
        raise ValueError(
            f"No default playbook for workflow kind {k!r}. "
            f"Add it under kind_default_playbook in {rp}. "
            f"Mapped kinds: {known_kinds}"
        )
    return resolve_playbook(
        pid_raw.strip(),
        policy=policy,
        mission_defaults=mission_defaults,
        params_delta=params_delta,
        project_root=project_root,
    )
