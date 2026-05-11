"""Deterministic workflow templates (v1 planner). Kinds are code-defined only."""

from __future__ import annotations

import json
from typing import Any

# Public set of kinds for CLI/help and validation.
WORKFLOW_KINDS: frozenset[str] = frozenset(
    {"rss_fetch_then_graph_then_synth", "publish_entity_v1", "publish_keyword_v1"}
)

_KEYWORD_CLUSTER_MAX_CHARS = 160

_PUBLISH_DELIVERY_MODES = frozenset({"isr_s3", "none", "wordpress_csv_s3"})


def _normalize_publish_delivery(out: dict[str, Any]) -> None:
    """Coalesce ``delivery_targets`` → ``delivery``, validate, replace with normalized dict."""
    targets = out.pop("delivery_targets", None)
    if out.get("delivery") is None and targets is not None:
        out["delivery"] = targets
    raw = out.get("delivery")
    if raw is None:
        return
    if not isinstance(raw, dict):
        raise ValueError("delivery must be a JSON object")
    if not raw:
        del out["delivery"]
        return
    mode_raw = raw.get("mode")
    if not isinstance(mode_raw, str) or not mode_raw.strip():
        raise ValueError("delivery.mode is required when delivery is set")
    mode = mode_raw.strip().lower()
    if mode not in _PUBLISH_DELIVERY_MODES:
        raise ValueError(
            f"delivery.mode must be one of {sorted(_PUBLISH_DELIVERY_MODES)}"
        )
    normalized: dict[str, Any] = {"mode": mode}
    if mode == "wordpress_csv_s3":
        wps = raw.get("wordpress_csv_s3")
        if not isinstance(wps, dict):
            raise ValueError(
                "delivery.wordpress_csv_s3 must be an object when mode is wordpress_csv_s3"
            )
        key_raw = wps.get("key")
        pfx_raw = wps.get("prefix")
        k_tr = str(key_raw).strip() if key_raw is not None else ""
        p_tr = str(pfx_raw).strip() if pfx_raw is not None else ""
        if bool(k_tr) == bool(p_tr):
            raise ValueError(
                "delivery.wordpress_csv_s3 requires exactly one of non-empty key or prefix"
            )
        bucket_raw = wps.get("bucket")
        bucket_tr = str(bucket_raw).strip() if bucket_raw is not None else ""
        sub: dict[str, Any] = {}
        if bucket_tr:
            sub["bucket"] = bucket_tr
        if k_tr:
            if ".." in k_tr or k_tr.startswith("/"):
                raise ValueError("delivery.wordpress_csv_s3.key must be a relative key without '..'")
            sub["key"] = k_tr
        else:
            sub["prefix"] = p_tr.strip().strip("/")
        idem = wps.get("idempotency")
        if idem is not None:
            if not isinstance(idem, str) or not idem.strip():
                raise ValueError(
                    "delivery.wordpress_csv_s3.idempotency must be a non-empty string when set"
                )
            idem_s = idem.strip().lower()
            if idem_s not in ("overwrite", "overwrite_only"):
                raise ValueError(
                    "delivery.wordpress_csv_s3.idempotency must be overwrite or overwrite_only"
                )
            sub["idempotency"] = idem_s
        normalized["wordpress_csv_s3"] = sub
    out["delivery"] = normalized


def validate_target_keyword_cluster(value: Any) -> str:
    """Validate optional publish keyword targeting input."""
    if not isinstance(value, str):
        raise ValueError("target_keyword_cluster must be a string")
    s = value.strip()
    if not s:
        raise ValueError("target_keyword_cluster must not be empty")
    if len(s) > _KEYWORD_CLUSTER_MAX_CHARS:
        raise ValueError(
            f"target_keyword_cluster exceeds max length {_KEYWORD_CLUSTER_MAX_CHARS}"
        )
    # Keep cluster text plain and deterministic in prompts/logs.
    for ch in s:
        if ch.isalnum() or ch in (" ", "-", "_", "/", "&", "+", ",", "."):
            continue
        raise ValueError("target_keyword_cluster has unsupported characters")
    return s


def _base_steps(kind: str) -> list[dict[str, Any]]:
    k = str(kind).strip()
    if k == "rss_fetch_then_graph_then_synth":
        return [
            {
                "step_index": 0,
                "step_type": "FETCH",
                "input_json": {},
            },
            {
                "step_index": 1,
                "step_type": "EXTRACT",
                "input_json": {"recent_item_limit": 40},
            },
            {
                "step_index": 2,
                "step_type": "SYNTHESIZE",
                "input_json": {},
            },
        ]
    if k == "publish_entity_v1":
        return [
            {"step_index": 0, "step_type": "ENRICH", "input_json": {}},
            {"step_index": 1, "step_type": "GATE", "input_json": {}},
            {"step_index": 2, "step_type": "DRAFT", "input_json": {}},
            {"step_index": 3, "step_type": "DEPLOY", "input_json": {}},
        ]
    if k == "publish_keyword_v1":
        return [
            {"step_index": 0, "step_type": "ENRICH", "input_json": {}},
            {"step_index": 1, "step_type": "DRAFT", "input_json": {}},
            {"step_index": 2, "step_type": "DEPLOY", "input_json": {}},
        ]
    raise ValueError(f"unknown workflow kind: {kind!r}")


def validate_workflow_step_dependencies(steps: list[dict[str, Any]]) -> None:
    """Public wrapper for tests: ensure depends_on_step_index < step_index for each step."""
    _validate_dependency_graph(steps)


def _validate_dependency_graph(steps: list[dict[str, Any]]) -> None:
    """Reject invalid depends_on_step_index (must be < step_index; acyclic)."""
    for st in steps:
        idx = int(st["step_index"])
        inp = st.get("input_json") if isinstance(st.get("input_json"), dict) else {}
        dep = inp.get("depends_on_step_index")
        if dep is None:
            continue
        try:
            d = int(dep)
        except (TypeError, ValueError) as e:
            raise ValueError("depends_on_step_index must be integer") from e
        if d >= idx:
            raise ValueError(
                f"depends_on_step_index {d} must be < step_index {idx} for DAG safety"
            )


def validate_and_normalize_workflow_params(kind: str, params: dict[str, Any]) -> dict[str, Any]:
    """
    Validate merged workflow params (post-playbook merge). Returns a copy safe for
    ``expand_workflow_template`` (normalized strings / ints).
    """
    k = str(kind).strip()
    out = dict(params)
    if k == "publish_keyword_v1":
        for fld in ("project_id", "campaign_id", "niche"):
            if not str(out.get(fld) or "").strip():
                raise ValueError(f"publish_keyword_v1 requires params_json {fld!r}")
        if out.get("target_keyword_cluster") is None:
            raise ValueError("publish_keyword_v1 requires params_json target_keyword_cluster")
        out["target_keyword_cluster"] = validate_target_keyword_cluster(
            out.get("target_keyword_cluster")
        )
        _normalize_publish_delivery(out)
        return out
    if k == "publish_entity_v1":
        eid = out.get("entity_id")
        if eid is None:
            raise ValueError("publish_entity_v1 requires params_json entity_id (int)")
        try:
            out["entity_id"] = int(eid)
        except (TypeError, ValueError) as e:
            raise ValueError("entity_id must be an integer") from e
        for fld in ("project_id", "campaign_id", "niche"):
            if not str(out.get(fld) or "").strip():
                raise ValueError(f"publish_entity_v1 requires params_json {fld!r}")
        if out.get("target_keyword_cluster") is not None:
            out["target_keyword_cluster"] = validate_target_keyword_cluster(
                out["target_keyword_cluster"]
            )
        _normalize_publish_delivery(out)
        return out
    if k == "rss_fetch_then_graph_then_synth":
        lim_raw = out.get("recent_item_limit")
        if lim_raw is not None:
            try:
                out["recent_item_limit"] = max(1, min(int(lim_raw), 500))
            except (TypeError, ValueError):
                del out["recent_item_limit"]
        return out
    raise ValueError(f"unknown workflow kind: {kind!r}")


def expand_workflow_template(
    kind: str,
    params: dict[str, Any],
    *,
    max_steps: int | None,
) -> list[dict[str, Any]]:
    """
    Return step rows ready for PersistentState.enqueue_workflow (step_index, step_type, input_json).
    Merges ``params`` into SYNTHESIZE step (topic), EXTRACT (recent_item_limit), or
    publisher fields for ``publish_entity_v1`` / ``publish_keyword_v1``.

    Callers must pass params already validated via ``validate_and_normalize_workflow_params``
    (enforced at enqueue time by the playbook resolver).
    """
    steps = [dict(s) for s in _base_steps(kind)]
    k = str(kind).strip()
    if k == "publish_keyword_v1":
        kw = validate_target_keyword_cluster(params.get("target_keyword_cluster"))
        for st in steps:
            inp = dict(st.get("input_json") or {})
            inp["target_keyword_cluster"] = kw
            for key in (
                "project_id",
                "campaign_id",
                "niche",
                "slug",
                "idempotency_key",
                "page_profile",
                "keyword_source",
                "brand_name",
                "vertical",
                "delivery",
            ):
                if key in params and params[key] is not None:
                    inp[key] = params[key]
            wk = params.get("workflow_kind")
            inp["workflow_kind"] = (
                str(wk).strip() if wk is not None and str(wk).strip() else "publish_keyword_v1"
            )
            st["input_json"] = inp
        _validate_dependency_graph(steps)
        if max_steps is not None and len(steps) > max_steps:
            raise ValueError(
                f"workflow has {len(steps)} steps; ADA_MAX_TASK_STEPS allows {max_steps}"
            )
        return steps
    if k == "publish_entity_v1":
        eid = int(params["entity_id"])
        for st in steps:
            inp = dict(st.get("input_json") or {})
            inp["entity_id"] = eid
            for key in (
                "project_id",
                "campaign_id",
                "niche",
                "slug",
                "idempotency_key",
                "page_profile",
                "workflow_kind",
                "keyword_source",
                "delivery",
            ):
                if key in params and params[key] is not None:
                    inp[key] = params[key]
            if "target_keyword_cluster" in params and params["target_keyword_cluster"] is not None:
                inp["target_keyword_cluster"] = validate_target_keyword_cluster(
                    params["target_keyword_cluster"]
                )
            st["input_json"] = inp
        _validate_dependency_graph(steps)
        if max_steps is not None and len(steps) > max_steps:
            raise ValueError(
                f"workflow has {len(steps)} steps; ADA_MAX_TASK_STEPS allows {max_steps}"
            )
        return steps
    topic = str(params.get("topic") or "Summarize recent ingested knowledge.").strip()
    lim_raw = params.get("recent_item_limit")
    recent_lim = 40
    if lim_raw is not None:
        try:
            recent_lim = max(1, min(int(lim_raw), 500))
        except (TypeError, ValueError):
            recent_lim = 40
    for st in steps:
        inp = dict(st.get("input_json") or {})
        if st["step_type"] == "SYNTHESIZE":
            inp["topic"] = topic
        if st["step_type"] == "EXTRACT":
            inp["recent_item_limit"] = recent_lim
        st["input_json"] = inp
    _validate_dependency_graph(steps)
    if max_steps is not None and len(steps) > max_steps:
        raise ValueError(
            f"workflow has {len(steps)} steps; ADA_MAX_TASK_STEPS allows {max_steps}"
        )
    return steps


def parse_params_json_object(raw: str | None) -> dict[str, Any]:
    if raw is None or not str(raw).strip():
        return {}
    try:
        obj = json.loads(str(raw).strip())
    except json.JSONDecodeError as e:
        raise ValueError("params_json must be valid JSON object string") from e
    if not isinstance(obj, dict):
        raise ValueError("params_json must decode to a JSON object")
    return obj
