"""Single source of truth for programme-shaped env vars deprecated in favour of ``missions.defaults_json``.

See docs/ENV_MIGRATION.md. Phase A read-path preference (tick/matrix only): mission_defaults_resolve.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Any, Final, Literal

ValueKind = Literal["scalar:str", "scalar:int", "csv:str"]


@dataclass(frozen=True)
class DeprecatedEnv:
    """One deprecated environment variable → ``missions.defaults_json`` key."""

    env_var: str
    mission_json_key: str
    value_kind: ValueKind
    # ``Settings`` attribute name when this env is loaded into ``Settings`` (else ``None``).
    settings_field: str | None


DEPRECATED_ENVS: Final[tuple[DeprecatedEnv, ...]] = (
    DeprecatedEnv("ADA_PROJECT_ID", "project_id", "scalar:str", None),
    DeprecatedEnv("ADA_CAMPAIGN_ID", "campaign_id", "scalar:str", None),
    DeprecatedEnv("ADA_BRAND_SITE_URL", "brand_site_url", "scalar:str", "brand_site_url"),
    DeprecatedEnv("GSC_SITE_URL", "gsc_site_url", "scalar:str", "gsc_site_url"),
    DeprecatedEnv("ADA_KEYWORD_TERMS", "keyword_terms", "scalar:str", "ada_keyword_terms"),
    DeprecatedEnv(
        "ADA_KEYWORD_LOCATION_CODE",
        "keyword_location_code",
        "scalar:int",
        "ada_keyword_location_code",
    ),
    DeprecatedEnv(
        "ADA_KEYWORD_LANGUAGE_CODE",
        "keyword_language_code",
        "scalar:str",
        "ada_keyword_language_code",
    ),
    DeprecatedEnv(
        "ADA_KEYWORD_MAX_TERMS_PER_RUN",
        "keyword_max_terms_per_run",
        "scalar:int",
        "ada_keyword_max_terms_per_run",
    ),
    DeprecatedEnv("ADA_GETS_POLL_URL", "gets_poll_url", "scalar:str", "ada_gets_poll_url"),
    DeprecatedEnv(
        "ADA_MATRIX_ENTITY_TYPES",
        "matrix_entity_types",
        "csv:str",
        "ada_matrix_entity_types",
    ),
    DeprecatedEnv(
        "ADA_MATRIX_MAX_ENQUEUES",
        "matrix_max_enqueues",
        "scalar:int",
        "ada_matrix_max_enqueues",
    ),
    DeprecatedEnv(
        "ADA_PUBLISH_MIN_UNIQUE_FACTS",
        "publish_min_unique_facts",
        "scalar:int",
        "ada_publish_min_unique_facts",
    ),
    DeprecatedEnv(
        "ADA_TRIAGE_LEAD_DAILY_CAP",
        "triage_lead_daily_cap",
        "scalar:int",
        "triage_lead_daily_cap",
    ),
)

_WARN_EMITTED = False
_PENDING_AUDIT_ENVS: list[str] | None = None
_AUDIT_LOGGED = False


def _env_nonempty(name: str) -> bool:
    return bool(os.environ.get(name, "").strip())


def _parse_env_value(d: DeprecatedEnv, raw: str) -> Any:
    raw = raw.strip()
    if d.value_kind == "scalar:str":
        return raw
    if d.value_kind == "scalar:int":
        return int(raw)
    # csv:str → list of non-empty lowercased tokens (matrix entity types)
    parts = [p.strip().lower() for p in raw.split(",") if p.strip()]
    return parts


def env_patch_from_current_process(
    *, only_env_vars: frozenset[str] | None = None
) -> dict[str, Any]:
    """Build ``missions.defaults_json`` patch from ``os.environ`` (migrate-env helper)."""
    out: dict[str, Any] = {}
    for d in DEPRECATED_ENVS:
        if only_env_vars is not None and d.env_var not in only_env_vars:
            continue
        raw = os.environ.get(d.env_var, "").strip()
        if not raw:
            continue
        try:
            out[d.mission_json_key] = _parse_env_value(d, raw)
        except ValueError:
            continue
    return out


def _warn_deprecated_envs() -> None:
    """Emit one stderr line per set deprecated env; idempotent per process."""
    global _WARN_EMITTED, _PENDING_AUDIT_ENVS
    if os.environ.get("ADA_DEPRECATED_ENV_SUPPRESS", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    ):
        _WARN_EMITTED = True
        _PENDING_AUDIT_ENVS = []
        return
    if _WARN_EMITTED:
        return
    _WARN_EMITTED = True
    pending: list[str] = []
    for d in DEPRECATED_ENVS:
        if not _env_nonempty(d.env_var):
            continue
        pending.append(d.env_var)
        print(
            "ada: deprecated env "
            f"{d.env_var} -> set mission.defaults_json.{d.mission_json_key}; "
            "migrate with: ada mission migrate-env <slug>",
            file=sys.stderr,
        )
    _PENDING_AUDIT_ENVS = pending


def pending_deprecated_audit_envs() -> list[str] | None:
    """Env var names that triggered deprecation warnings this process (copy)."""
    if _PENDING_AUDIT_ENVS is None:
        return None
    return list(_PENDING_AUDIT_ENVS)


def mark_deprecated_audit_logged() -> None:
    global _AUDIT_LOGGED
    _AUDIT_LOGGED = True


def deprecated_audit_already_logged() -> bool:
    return _AUDIT_LOGGED


def reset_deprecation_state_for_tests() -> None:
    """Test-only: clear process globals."""
    global _WARN_EMITTED, _PENDING_AUDIT_ENVS, _AUDIT_LOGGED
    _WARN_EMITTED = False
    _PENDING_AUDIT_ENVS = None
    _AUDIT_LOGGED = False
