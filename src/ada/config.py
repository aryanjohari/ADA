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
    wakeup_path: Path
    allowlist_path: Path
    gemini_api_key: str
    gemini_model: str
    max_tool_rounds: int
    persist_debounce_ms: int
    shell_max_output_bytes: int
    shell_timeout_sec: float
    stream_chunk_idle_timeout_sec: float
    stream_leg_max_wall_sec: float
    rewire_after_tombstone: bool
    enable_memory_tools: bool
    memory_backups_dir: Path
    memory_max_append_bytes: int
    memory_max_file_bytes: int
    dream_max_soul_bytes: int
    dream_default_max_messages: int

    @classmethod
    def load(cls) -> "Settings":
        root = _find_project_root()
        data_dir = Path(
            os.environ.get("ADA_DATA_DIR", str(root / "data"))
        ).expanduser()
        memory_dir = root / "memory"
        key = os.environ.get("GEMINI_API_KEY", "").strip()
        model = os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip()
        max_rounds = int(os.environ.get("ADA_MAX_TOOL_ROUNDS", "12"))
        debounce = int(os.environ.get("ADA_PERSIST_DEBOUNCE_MS", "100"))
        shell_max = int(os.environ.get("ADA_SHELL_MAX_OUTPUT_BYTES", "65536"))
        shell_timeout = float(os.environ.get("ADA_SHELL_TIMEOUT_SEC", "60"))
        stream_idle = float(os.environ.get("ADA_STREAM_CHUNK_IDLE_SEC", "120"))
        stream_wall = float(os.environ.get("ADA_STREAM_LEG_MAX_SEC", "600"))
        rewire = os.environ.get("ADA_REWIRE_AFTER_TOMBSTONE", "1").strip().lower() not in (
            "0",
            "false",
            "no",
        )
        mem_tools = os.environ.get("ADA_ENABLE_MEMORY_TOOLS", "1").strip().lower() not in (
            "0",
            "false",
            "no",
        )
        mem_append = int(os.environ.get("ADA_MEMORY_MAX_APPEND_BYTES", "8192"))
        mem_file = int(os.environ.get("ADA_MEMORY_MAX_FILE_BYTES", str(512 * 1024)))
        dream_soul = int(os.environ.get("ADA_DREAM_MAX_SOUL_BYTES", "1024"))
        dream_msgs = int(os.environ.get("ADA_DREAM_MAX_MESSAGES", "60"))
        return cls(
            project_root=root,
            data_dir=data_dir,
            state_db_path=data_dir / "state.db",
            memory_dir=memory_dir,
            soul_path=memory_dir / "soul.md",
            master_path=memory_dir / "master.md",
            wakeup_path=memory_dir / "wakeup.md",
            allowlist_path=memory_dir / "shell_allowlist.txt",
            gemini_api_key=key,
            gemini_model=model or DEFAULT_GEMINI_MODEL,
            max_tool_rounds=max_rounds,
            persist_debounce_ms=debounce,
            shell_max_output_bytes=shell_max,
            shell_timeout_sec=shell_timeout,
            stream_chunk_idle_timeout_sec=stream_idle,
            stream_leg_max_wall_sec=stream_wall,
            rewire_after_tombstone=rewire,
            enable_memory_tools=mem_tools,
            memory_backups_dir=memory_dir / "backups",
            memory_max_append_bytes=mem_append,
            memory_max_file_bytes=mem_file,
            dream_max_soul_bytes=dream_soul,
            dream_default_max_messages=dream_msgs,
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
