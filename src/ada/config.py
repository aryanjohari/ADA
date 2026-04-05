"""Paths and environment configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# Default Gemini model: Flash-Lite tier (verify against current API model list).
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash-lite"


def _find_project_root() -> Path:
    """Directory containing pyproject.toml, or cwd."""
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()


@dataclass(frozen=True)
class Settings:
    project_root: Path
    data_dir: Path
    state_db_path: Path
    memory_dir: Path
    soul_path: Path
    master_path: Path
    gemini_api_key: str
    gemini_model: str
    max_tool_rounds: int
    persist_debounce_ms: int

    @classmethod
    def load(cls) -> "Settings":
        root = _find_project_root()
        data_dir = Path(
            os.environ.get("ADA_DATA_DIR", str(root / "data"))
        ).expanduser()
        memory_dir = root / "memory"
        key = os.environ.get("GEMINI_API_KEY", "").strip()
        model = os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip()
        max_rounds = int(os.environ.get("ADA_MAX_TOOL_ROUNDS", "0"))
        debounce = int(os.environ.get("ADA_PERSIST_DEBOUNCE_MS", "100"))
        return cls(
            project_root=root,
            data_dir=data_dir,
            state_db_path=data_dir / "state.db",
            memory_dir=memory_dir,
            soul_path=memory_dir / "soul.md",
            master_path=memory_dir / "master.md",
            gemini_api_key=key,
            gemini_model=model or DEFAULT_GEMINI_MODEL,
            max_tool_rounds=max_rounds,
            persist_debounce_ms=debounce,
        )

    def ensure_data_dir(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)


def load_dotenv_if_present() -> None:
    """Populate os.environ from .env at project root if file exists."""
    root = _find_project_root()
    env_path = root / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v
