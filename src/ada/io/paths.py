"""Resolve durable data paths under ADA_DATA_ROOT.

Default production root is /mnt/ada-data (HDD autobiography substrate).
Tests override via ADA_DATA_ROOT so they never touch the real mount.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_ADA_DATA_ROOT = "/mnt/ada-data"
ENV_ADA_DATA_ROOT = "ADA_DATA_ROOT"


class BodyFault(Exception):
    """Hard body fault — refuse durable writes; do not fake success."""

    def __init__(self, message: str, *, code: int = 3) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class DataPaths:
    """Canonical layout under the durable substrate."""

    root: Path

    @property
    def memory(self) -> Path:
        return self.root / "memory"

    @property
    def facts(self) -> Path:
        return self.memory / "facts"

    @property
    def identity_yaml(self) -> Path:
        return self.facts / "identity.yaml"

    @property
    def prefs_yaml(self) -> Path:
        return self.facts / "prefs.yaml"

    @property
    def hud_devices_yaml(self) -> Path:
        """Thin named-window list (M19b). Not a Dream-whitelist prefs key."""
        return self.facts / "hud_devices.yaml"

    @property
    def open_loops_yaml(self) -> Path:
        return self.facts / "open_loops.yaml"

    @property
    def people(self) -> Path:
        return self.facts / "people"

    @property
    def aryan_yaml(self) -> Path:
        return self.people / "aryan.yaml"

    @property
    def worldview(self) -> Path:
        return self.memory / "worldview"

    @property
    def dreams(self) -> Path:
        """Dream-produced WORLDVIEW digests under memory/."""
        return self.memory / "dreams"

    @property
    def memory_staging(self) -> Path:
        """Dream FACT candidates awaiting confirm."""
        return self.memory / "staging"

    @property
    def cites(self) -> Path:
        """Durable web cite library (M07)."""
        return self.memory / "cites"

    @property
    def scratch(self) -> Path:
        """Disposable scratch (not default-backed-up)."""
        return self.root / "scratch"

    @property
    def scratch_web(self) -> Path:
        """Optional raw HTML bodies for web fetch (never boot)."""
        return self.scratch / "web"

    @property
    def artifacts(self) -> Path:
        """Durable user-facing outputs (M16 Pi-doer)."""
        return self.root / "artifacts"

    @property
    def syllabus(self) -> Path:
        """Birth syllabus heads (SELF / OPERATOR) under ada-data."""
        return self.root / "syllabus"

    @property
    def syllabus_self(self) -> Path:
        return self.syllabus / "SELF.md"

    @property
    def syllabus_operator(self) -> Path:
        return self.syllabus / "OPERATOR.md"

    @property
    def secrets(self) -> Path:
        """Local secrets tree (never in git / never to cortex dumps)."""
        return self.root / "secrets"

    @property
    def lifecycle_jsonl(self) -> Path:
        return self.memory / "lifecycle.jsonl"

    @property
    def runs(self) -> Path:
        """Episodic chat transcripts / tool receipts (M02)."""
        return self.root / "runs"

    @property
    def logs(self) -> Path:
        """Life capture SQLite logs (M19a)."""
        return self.root / "logs"

    @property
    def life_logs_db(self) -> Path:
        return self.logs / "life_logs.db"

    @property
    def food_reference_db(self) -> Path:
        return self.logs / "food_reference.db"

    @property
    def dream(self) -> Path:
        """Sealed Dream packages tree (staging / outbox / sent)."""
        return self.root / "dream"

    @property
    def dream_staging(self) -> Path:
        return self.dream / "staging"

    @property
    def dream_outbox(self) -> Path:
        return self.dream / "outbox"

    @property
    def dream_sent(self) -> Path:
        return self.dream / "sent"

    @property
    def models(self) -> Path:
        """Organ weights on the HDD — not autobiography, not git."""
        return self.root / "models"

    @property
    def models_voice(self) -> Path:
        return self.models / "voice"

    @property
    def models_voice_whisper(self) -> Path:
        """faster-whisper download_root (never ~/.cache/huggingface)."""
        return self.models_voice / "faster-whisper"

    @property
    def models_voice_piper(self) -> Path:
        return self.models_voice / "piper"

    def ensure_voice_model_dirs(self) -> None:
        """Create models/voice/{faster-whisper,piper} lazily. Not a memory dir."""
        self.models_voice_whisper.mkdir(parents=True, exist_ok=True)
        self.models_voice_piper.mkdir(parents=True, exist_ok=True)

    def ensure_memory_dirs(self) -> None:
        """Create memory layout dirs lazily (facts, worldview, dreams, staging)."""
        for d in (
            self.facts,
            self.people,
            self.worldview,
            self.dreams,
            self.memory_staging,
        ):
            d.mkdir(parents=True, exist_ok=True)

    def ensure_cite_dirs(self) -> None:
        """Create memory/cites + scratch/web lazily on first web_fetch."""
        self.cites.mkdir(parents=True, exist_ok=True)
        self.scratch_web.mkdir(parents=True, exist_ok=True)

    def ensure_artifact_dirs(self) -> None:
        """Create artifacts/ lazily on first artifact_write."""
        self.artifacts.mkdir(parents=True, exist_ok=True)

    def ensure_syllabus_dirs(self) -> None:
        """Create syllabus/ for birth pack SELF/OPERATOR."""
        self.syllabus.mkdir(parents=True, exist_ok=True)

    def ensure_dream_dirs(self) -> None:
        """Create dream/{staging,outbox,sent} lazily on first dream.run."""
        for d in (self.dream_staging, self.dream_outbox, self.dream_sent):
            d.mkdir(parents=True, exist_ok=True)

    def ensure_logs_dirs(self) -> None:
        """Create logs/ for life capture SQLite (M19a)."""
        self.logs.mkdir(parents=True, exist_ok=True)


def get_data_root() -> Path:
    raw = os.environ.get(ENV_ADA_DATA_ROOT, DEFAULT_ADA_DATA_ROOT)
    return Path(raw).expanduser().resolve()


def get_paths(root: Path | None = None) -> DataPaths:
    return DataPaths(root=root if root is not None else get_data_root())


def ada_data_mounted(root: Path | None = None) -> bool:
    """Honesty gate: durable substrate present and acceptable for writes.

    Production (default root): directory must exist and be a mount point.
    Override via ADA_DATA_ROOT or an explicit non-default *root*: existence
    of the directory is enough (pytest tmp_path sandboxes are not mounts).
    """
    path = (root if root is not None else get_data_root()).resolve()
    if not path.is_dir():
        return False

    default = Path(DEFAULT_ADA_DATA_ROOT).resolve()
    sandbox = ENV_ADA_DATA_ROOT in os.environ or path != default
    if sandbox:
        return True

    try:
        return path.is_mount()
    except OSError:
        return False


def require_ada_data(root: Path | None = None) -> DataPaths:
    """Return paths or raise BodyFault when substrate is missing."""
    paths = get_paths(root)
    if not ada_data_mounted(paths.root):
        raise BodyFault(
            f"ada-data not mounted or missing at {paths.root}; refusing durable writes"
        )
    return paths
