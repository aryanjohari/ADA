"""Length/hash summaries for potentially sensitive text (no full content in UI by default)."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

_SHA_PREFIX_LEN = 12
_ERR_PREVIEW = 240


def field_digest(text: str | None) -> dict[str, int | str]:
    """Length + short SHA-256 prefix for opaque summaries."""
    raw = text if text is not None else ""
    b = raw.encode("utf-8", errors="replace")
    h = hashlib.sha256(b).hexdigest()[:_SHA_PREFIX_LEN]
    return {"byte_len": len(b), "sha256_prefix": h}


def truncate_error(text: str | None, max_chars: int = _ERR_PREVIEW) -> str:
    s = (text or "").strip()
    if len(s) <= max_chars:
        return s
    return s[: max_chars - 1] + "…"


def json_blob_digest(blob: str | None) -> dict[str, int | str]:
    raw = blob if blob is not None else ""
    try:
        parsed = json.loads(raw) if raw else {}
        if isinstance(parsed, dict):
            keys = sorted(str(k) for k in parsed.keys())
            key_summary = ",".join(keys[:20])
            if len(keys) > 20:
                key_summary += ",…"
        else:
            key_summary = type(parsed).__name__
    except json.JSONDecodeError:
        key_summary = "(invalid_json)"
    d = field_digest(raw)
    d["json_keys_preview"] = key_summary
    return d


def _redact_unknown(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _redact_unknown(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return ["[omitted]" for _ in obj] if len(obj) > 3 else [_redact_unknown(x) for x in obj]
    if isinstance(obj, (int, float, bool)) or obj is None:
        return obj
    if isinstance(obj, str):
        if len(obj) <= 64 and re.fullmatch(r"[a-zA-Z0-9_:.+-]+", obj):
            return obj
        return "[omitted]"
    return "[omitted]"


def action_payload_safe(kind: str, payload_json: str | None) -> dict[str, Any]:
    """
    Parse action_log.payload_json and return a small operator-safe dict.
    Known kinds get explicit keys; others get redacted structure.
    """
    raw = (payload_json or "").strip() or "{}"
    try:
        payload: Any = json.loads(raw)
    except json.JSONDecodeError:
        return {"_parse_error": True, "preview": truncate_error(raw, 120)}

    if not isinstance(payload, dict):
        return {"kind": kind, "value": _redact_unknown(payload)}

    allow = {
        "global_budget_block": frozenset(
            {"scope", "utc_date", "year_month", "used", "limit"}
        ),
        "kill_switch_skip": frozenset({"reason", "utc_date"}),
        "publish_deploy_blocked_no_approval": frozenset(
            {"workflow_id", "artifact_type", "artifact_ref"}
        ),
        "publish_keyword_targeting": frozenset(
            {
                "workflow_id",
                "step_id",
                "keyword_cluster_used",
                "keyword_source",
                "fallback_reason",
            }
        ),
    }
    keys = allow.get(kind)
    if keys is not None:
        out: dict[str, Any] = {"kind": kind}
        for k in keys:
            if k in payload:
                v = payload[k]
                if isinstance(v, str) and len(v) > 128:
                    out[k] = {"len": len(v), "sha256_prefix": field_digest(v)["sha256_prefix"]}
                else:
                    out[k] = v
        return out

    safe_keys = (
        "workflow_id",
        "step_id",
        "utc_date",
        "scope",
        "used",
        "limit",
        "reason",
        "artifact_type",
        "artifact_ref",
    )
    out2: dict[str, Any] = {"kind": kind}
    for k in safe_keys:
        if k in payload:
            v = payload[k]
            if isinstance(v, str) and len(v) > 128:
                out2[k] = {"len": len(v), "sha256_prefix": field_digest(v)["sha256_prefix"]}
            else:
                out2[k] = v
    if len(out2) <= 1:
        return {"kind": kind, "payload_redacted": _redact_unknown(payload)}
    return out2
