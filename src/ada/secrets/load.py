"""Load GEMINI_API_KEY from env override or ada-data secrets file.

POLICY (M02 §8):
  - Process env GEMINI_API_KEY wins if set (tests/CI).
  - Else read /mnt/ada-data/secrets/gemini.env (or ADA_SECRETS_DIR).
  - Fail closed on missing key — never half-chat with invented tools.
  - Key must never appear in prompts, tool observations, or runs JSONL.
"""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_SECRETS_DIR = "/mnt/ada-data/secrets"
ENV_SECRETS_DIR = "ADA_SECRETS_DIR"
ENV_API_KEY = "GEMINI_API_KEY"
GEMINI_ENV_FILENAME = "gemini.env"


class MissingSecret(Exception):
    """API key unavailable — harness must fail closed."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def secrets_dir() -> Path:
    raw = os.environ.get(ENV_SECRETS_DIR, DEFAULT_SECRETS_DIR)
    return Path(raw).expanduser().resolve()


def _parse_dotenv(text: str) -> dict[str, str]:
    """Minimal dotenv parser: KEY=VALUE lines; # comments; ignore blanks."""
    out: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key:
            out[key] = value
    return out


def load_gemini_api_key() -> str:
    """Return GEMINI_API_KEY or raise MissingSecret.

    Never logs or returns partial key material in exception text beyond path hints.
    """
    env_key = os.environ.get(ENV_API_KEY, "").strip()
    if env_key:
        return env_key

    path = secrets_dir() / GEMINI_ENV_FILENAME
    if not path.is_file():
        raise MissingSecret(
            f"{ENV_API_KEY} not set and secrets file missing at {path}"
        )
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise MissingSecret(f"cannot read secrets file at {path}") from exc

    parsed = _parse_dotenv(raw)
    key = (parsed.get(ENV_API_KEY) or "").strip()
    if not key:
        raise MissingSecret(f"{ENV_API_KEY} empty or absent in {path}")
    return key
