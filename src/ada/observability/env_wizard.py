"""Env checklist, merge rules, validation, and snippet generation for the operator UI."""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path

from ada.config import resolve_runtime_paths_from_environ

_KEY_LINE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=")


def keys_from_env_example(path: Path) -> list[str]:
    if not path.is_file():
        return []
    keys: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        m = _KEY_LINE.match(s)
        if m:
            keys.append(m.group(1))
    return keys


def parse_dotenv_file(path: Path) -> dict[str, str]:
    """Best-effort KEY=VALUE parse (no multiline continuation)."""
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if "=" not in s:
            continue
        key, _, val = s.partition("=")
        key = key.strip()
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key):
            continue
        val = val.strip()
        out[key] = val
    return out


def merge_dotenv_into_environ(
    base: Mapping[str, str], file_vars: dict[str, str]
) -> dict[str, str]:
    """Match ``load_dotenv(..., override=False)``: file does not override existing env."""
    out = dict(base)
    for k, v in file_vars.items():
        if k not in out:
            out[k] = v
    return out


# Smoke / required keys for typical operator runs (extend as needed).
SMOKE_REQUIRED_KEYS: tuple[str, ...] = ("GEMINI_API_KEY",)

# When publisher track is enabled, warn if any of these are partially set.
PUBLISHER_ENV_KEYS: tuple[str, ...] = (
    "S3_BUCKET_NAME",
    "ADA_S3_BUCKET",
    "AWS_REGION",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_ENDPOINT_URL",
)


def validate_paths_and_env(
    *,
    repo_root: Path,
    merged_environ: Mapping[str, str],
    publisher_track: bool,
) -> tuple[list[str], list[str]]:
    """
    Return (errors, warnings). Errors block “green” status; warnings are advisory.
    """
    errors: list[str] = []
    warnings: list[str] = []

    gemini = str(merged_environ.get("GEMINI_API_KEY", "")).strip()
    if not gemini:
        warnings.append("GEMINI_API_KEY is empty — LLM features will not run.")

    try:
        rp = resolve_runtime_paths_from_environ(
            project_root=repo_root,
            environ=merged_environ,
            warn_policy_fallback=False,
        )
        data_dir = rp.data_dir
        mem_dir = rp.memory_dir
        pol = rp.policy_root
        if rp.policy_used_repo_fallback and rp.active_profile_slug:
            warnings.append(
                "Policy root fell back to repo policies/ — add profile policies/default.yaml "
                "or set ADA_POLICY_ROOT for full isolation."
            )
    except ValueError as e:
        errors.append(str(e))
        return errors, warnings

    if not data_dir.is_dir() and merged_environ.get("ADA_PROFILE"):
        warnings.append(
            f"Profile data_dir does not exist yet (will be created on first ada run): {data_dir}"
        )

    ddr = str(merged_environ.get("ADA_DATA_DIR", "")).strip()
    if ddr and not Path(ddr).expanduser().is_absolute():
        p = (repo_root / ddr).resolve()
        if not p.is_dir():
            warnings.append(f"Resolved ADA_DATA_DIR path not a directory: {p}")

    prr = str(merged_environ.get("ADA_PROFILE_DATA_ROOT", "")).strip()
    if prr:
        root_p = Path(prr).expanduser()
        if not root_p.is_absolute():
            errors.append("ADA_PROFILE_DATA_ROOT must be an absolute path.")
        elif not root_p.is_dir():
            warnings.append(
                f"ADA_PROFILE_DATA_ROOT is not a directory yet: {root_p} (create it before production)."
            )

    if mem_dir and not mem_dir.is_dir():
        warnings.append(f"ADA_MEMORY_DIR / memory path not a directory yet: {mem_dir}")

    if pol and not pol.is_dir():
        warnings.append(f"ADA_POLICY_ROOT path not a directory: {pol}")

    if publisher_track:
        keys_present = [k for k in PUBLISHER_ENV_KEYS if str(merged_environ.get(k, "")).strip()]
        if keys_present and len(keys_present) < len(PUBLISHER_ENV_KEYS):
            missing = [k for k in PUBLISHER_ENV_KEYS if not str(merged_environ.get(k, "")).strip()]
            warnings.append(
                "Publisher/S3 track: some keys set but others empty — "
                f"review: {', '.join(missing[:8])}"
            )

    return errors, warnings


def build_environment_file_snippet(
    *,
    profile_slug: str,
    profile_data_root: str,
    ada_memory_dir: str = "",
    ada_policy_root: str = "",
    require_isolation: str = "1",
    extra_lines: list[str] | None = None,
) -> str:
    """systemd EnvironmentFile-style lines (no secrets pre-filled)."""
    lines = [
        "# Generated by ADA operator UI — paste into systemd EnvironmentFile= or a sourced file.",
        "# Add secrets (e.g. GEMINI_API_KEY) in your secure editor, not in chat.",
        f"ADA_PROFILE={profile_slug}",
        f"ADA_PROFILE_DATA_ROOT={profile_data_root}",
        f"ADA_REQUIRE_PROFILE_ISOLATION={require_isolation}",
    ]
    if ada_memory_dir.strip():
        lines.append(f"ADA_MEMORY_DIR={ada_memory_dir.strip()}")
    if ada_policy_root.strip():
        lines.append(f"ADA_POLICY_ROOT={ada_policy_root.strip()}")
    if extra_lines:
        lines.extend(extra_lines)
    return "\n".join(lines) + "\n"
