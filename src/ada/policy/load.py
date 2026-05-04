"""Load `default.yaml` under the policy root, optional overlays, and `memory/intent.md`."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from ada.config import _find_project_root

if TYPE_CHECKING:
    from ada.config import Settings


DEFAULT_INTENT_MAX_BYTES = 65_536
DEFAULT_MATRIX_PLANNER_TOP_K = 5
# Ceilings aligned with run_graph_lite_extraction (max 200 items) and Settings defaults.
DEFAULT_GRAPH_LITE_MAX_ITEMS_PER_JOB = 200
DEFAULT_GRAPH_LITE_TOKEN_CAP_PER_JOB = 8000
DEFAULT_BATCH_ENRICH_MAX_ENTITIES = 10
DEFAULT_BATCH_ENRICH_MAX_TOOL_ROUNDS = 48


@dataclass(frozen=True)
class PolicyConfig:
    """Merged policy snapshot (YAML + overlays + selective env overrides)."""

    version: int
    intent_max_bytes: int
    matrix_planner_top_k: int
    graph_lite_max_items_per_job: int
    graph_lite_token_cap_per_job: int
    batch_enrich_max_entities: int
    batch_enrich_max_tool_rounds: int


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in overlay.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _load_yaml_file(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return data


def _effective_policy_root(
    project_root: Path | None,
    policy_root: Path | None,
) -> Path:
    """Directory containing `default.yaml`. `policy_root` wins over `project_root`."""
    if policy_root is not None:
        return policy_root.resolve()
    if project_root is not None:
        return (project_root / "policies").resolve()
    return (_find_project_root() / "policies").resolve()


def _merge_policy_pack(policy_root: Path, base: dict[str, Any], pack_raw: str) -> dict[str, Any]:
    expanded = Path(pack_raw).expanduser()
    if not expanded.is_absolute():
        expanded = (policy_root / expanded).resolve()
    if not expanded.exists():
        raise ValueError(f"ADA_POLICY_PACK path does not exist: {expanded}")
    merged = dict(base)
    if expanded.is_file():
        if expanded.suffix.lower() not in (".yaml", ".yml"):
            raise ValueError(f"ADA_POLICY_PACK file must be .yaml/.yml: {expanded}")
        overlay = _load_yaml_file(expanded)
        merged = _deep_merge(merged, overlay)
    elif expanded.is_dir():
        yaml_files = sorted(expanded.glob("*.yaml")) + sorted(expanded.glob("*.yml"))
        for fp in yaml_files:
            overlay = _load_yaml_file(fp)
            merged = _deep_merge(merged, overlay)
    else:
        raise ValueError(f"ADA_POLICY_PACK is not a file or directory: {expanded}")
    return merged


def load_policy_yaml_dict(
    project_root: Path | None = None,
    policy_root: Path | None = None,
) -> dict[str, Any]:
    """Load `default.yaml` under the effective policy root; missing file ⇒ empty mapping."""
    pr = _effective_policy_root(project_root, policy_root)
    path = pr / "default.yaml"
    if not path.is_file():
        return {}

    try:
        return _load_yaml_file(path)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid policy YAML: {path}: {e}") from e


def _optional_env_int(key: str) -> int | None:
    raw = os.environ.get(key, "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _policy_defaults() -> PolicyConfig:
    return PolicyConfig(
        version=1,
        intent_max_bytes=DEFAULT_INTENT_MAX_BYTES,
        matrix_planner_top_k=DEFAULT_MATRIX_PLANNER_TOP_K,
        graph_lite_max_items_per_job=DEFAULT_GRAPH_LITE_MAX_ITEMS_PER_JOB,
        graph_lite_token_cap_per_job=DEFAULT_GRAPH_LITE_TOKEN_CAP_PER_JOB,
        batch_enrich_max_entities=DEFAULT_BATCH_ENRICH_MAX_ENTITIES,
        batch_enrich_max_tool_rounds=DEFAULT_BATCH_ENRICH_MAX_TOOL_ROUNDS,
    )


def load_merged_policy(
    project_root: Path | None = None,
    policy_root: Path | None = None,
) -> PolicyConfig:
    """
    Merge order: ``default.yaml`` under policy root → ADA_POLICY_PACK (file or *.yaml/*.yml in dir)
    → ADA_INTENT_MAX_BYTES / ADA_MATRIX_PLANNER_TOP_K when set.

    When ``policy_root`` is set, it is the directory containing ``default.yaml`` and relative
    ``ADA_POLICY_PACK`` paths resolve against it. When only ``project_root`` is set (tests /
    callers), the effective root is ``project_root / "policies"`` (backward compatible).

    Malformed defaults file when present: raise ValueError (fail closed).
    """
    pr = _effective_policy_root(project_root, policy_root)
    data = load_policy_yaml_dict(project_root=None, policy_root=pr)

    pack = os.environ.get("ADA_POLICY_PACK", "").strip()
    if pack:
        data = _merge_policy_pack(pr, data, pack)

    if not data:
        return _policy_defaults()

    version = data.get("version")
    try:
        v_int = int(version) if version is not None else 1
    except (TypeError, ValueError) as e:
        raise ValueError("policy 'version' must be an integer") from e

    imb = data.get("intent_max_bytes")
    try:
        intent_max = int(imb) if imb is not None else DEFAULT_INTENT_MAX_BYTES
    except (TypeError, ValueError) as e:
        raise ValueError("policy 'intent_max_bytes' must be an integer") from e
    intent_max = max(256, min(2_097_152, intent_max))

    mptk = data.get("matrix_planner_top_k")
    try:
        top_k = int(mptk) if mptk is not None else DEFAULT_MATRIX_PLANNER_TOP_K
    except (TypeError, ValueError) as e:
        raise ValueError("policy 'matrix_planner_top_k' must be an integer") from e
    top_k = max(1, min(10_000, top_k))

    glim = data.get("graph_lite_max_items_per_job")
    try:
        gl_items = (
            int(glim) if glim is not None else DEFAULT_GRAPH_LITE_MAX_ITEMS_PER_JOB
        )
    except (TypeError, ValueError) as e:
        raise ValueError("policy 'graph_lite_max_items_per_job' must be an integer") from e
    gl_items = max(1, min(200, gl_items))

    gltc = data.get("graph_lite_token_cap_per_job")
    try:
        gl_tok = (
            int(gltc) if gltc is not None else DEFAULT_GRAPH_LITE_TOKEN_CAP_PER_JOB
        )
    except (TypeError, ValueError) as e:
        raise ValueError("policy 'graph_lite_token_cap_per_job' must be an integer") from e
    gl_tok = max(256, min(500_000, gl_tok))

    bem = data.get("batch_enrich_max_entities")
    try:
        batch_ent = int(bem) if bem is not None else DEFAULT_BATCH_ENRICH_MAX_ENTITIES
    except (TypeError, ValueError) as e:
        raise ValueError("policy 'batch_enrich_max_entities' must be an integer") from e
    batch_ent = max(1, min(10_000, batch_ent))

    btr = data.get("batch_enrich_max_tool_rounds")
    try:
        batch_tr = (
            int(btr) if btr is not None else DEFAULT_BATCH_ENRICH_MAX_TOOL_ROUNDS
        )
    except (TypeError, ValueError) as e:
        raise ValueError("policy 'batch_enrich_max_tool_rounds' must be an integer") from e
    batch_tr = max(1, min(48, batch_tr))

    env_im = _optional_env_int("ADA_INTENT_MAX_BYTES")
    if env_im is not None:
        intent_max = max(256, min(2_097_152, env_im))
    env_tk = _optional_env_int("ADA_MATRIX_PLANNER_TOP_K")
    if env_tk is not None:
        top_k = max(1, min(10_000, env_tk))
    env_gl_items = _optional_env_int("ADA_GRAPH_LITE_POLICY_MAX_ITEMS")
    if env_gl_items is not None:
        gl_items = max(1, min(200, env_gl_items))
    env_gl_tok = _optional_env_int("ADA_GRAPH_LITE_POLICY_TOKEN_CAP")
    if env_gl_tok is not None:
        gl_tok = max(256, min(500_000, env_gl_tok))
    env_batch_ent = _optional_env_int("ADA_BATCH_ENRICH_MAX_ENTITIES")
    if env_batch_ent is not None:
        batch_ent = max(1, min(10_000, env_batch_ent))
    env_batch_tr = _optional_env_int("ADA_BATCH_ENRICH_MAX_TOOL_ROUNDS")
    if env_batch_tr is not None:
        batch_tr = max(1, min(48, env_batch_tr))

    return PolicyConfig(
        version=v_int,
        intent_max_bytes=intent_max,
        matrix_planner_top_k=top_k,
        graph_lite_max_items_per_job=gl_items,
        graph_lite_token_cap_per_job=gl_tok,
        batch_enrich_max_entities=batch_ent,
        batch_enrich_max_tool_rounds=batch_tr,
    )


def load_merged_policy_for(settings: "Settings") -> PolicyConfig:
    """Load merged policy using ``settings.policy_root`` (per-profile / ADA_POLICY_ROOT)."""
    return load_merged_policy(policy_root=settings.policy_root)


def load_intent_md(memory_dir: Path, *, max_bytes: int | None = None) -> str:
    """
    Plain-text operator goals for data-plane pipelines. Missing file ⇒ empty string.
    Truncates to max_bytes with a UTF-8 safe boundary (best-effort).
    """
    cap = max_bytes if max_bytes is not None else DEFAULT_INTENT_MAX_BYTES
    cap = max(0, cap)
    path = memory_dir / "intent.md"
    if not path.is_file():
        return ""
    try:
        data = path.read_bytes()
    except OSError:
        return ""
    if len(data) <= cap:
        return data.decode("utf-8", errors="replace").strip()

    truncated = data[:cap]
    while truncated and (truncated[-1] & 0xC0) == 0x80:
        truncated = truncated[:-1]
    return truncated.decode("utf-8", errors="replace").strip()


def clamp_graph_lite_job_limits(
    resolved_limit: int,
    resolved_token_cap: int,
    policy: PolicyConfig,
) -> tuple[int, int]:
    """Apply policy ceilings to CLI/env-resolved graph-lite job bounds (backward compatible defaults)."""
    lim = min(max(1, int(resolved_limit)), policy.graph_lite_max_items_per_job)
    cap = min(max(256, int(resolved_token_cap)), policy.graph_lite_token_cap_per_job)
    return lim, cap
