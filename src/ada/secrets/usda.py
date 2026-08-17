"""USDA FDC API key loader (M19a)."""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_SECRETS_DIR = "/mnt/ada-data/secrets"
ENV_SECRETS_DIR = "ADA_SECRETS_DIR"
ENV_API_KEY = "USDA_FDC_API_KEY"
USDA_ENV_FILENAME = "usda_fdc.env"


class MissingSecret(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def secrets_dir() -> Path:
    raw = os.environ.get(ENV_SECRETS_DIR, DEFAULT_SECRETS_DIR)
    return Path(raw).expanduser().resolve()


def _parse_dotenv(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key:
            out[key] = value
    return out


def load_usda_fdc_api_key(*, required: bool = True) -> str | None:
    env_key = os.environ.get(ENV_API_KEY, "").strip()
    if env_key:
        return env_key
    path = secrets_dir() / USDA_ENV_FILENAME
    if not path.is_file():
        if required:
            raise MissingSecret(
                f"{ENV_API_KEY} not set and secrets file missing at {path}"
            )
        return None
    parsed = _parse_dotenv(path.read_text(encoding="utf-8"))
    key = (parsed.get(ENV_API_KEY) or "").strip()
    if not key:
        if required:
            raise MissingSecret(f"{ENV_API_KEY} empty or absent in {path}")
        return None
    return key
