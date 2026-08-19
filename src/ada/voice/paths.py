"""Resolve the isolated voice-weights tree. Never memory/, never home cache."""

from __future__ import annotations

import os
from pathlib import Path

from ada.io.paths import DataPaths, get_paths

ENV_VOICE_MODELS_ROOT = "ADA_VOICE_MODELS_ROOT"
ENV_VOICE_WARMUP = "ADA_VOICE_WARMUP"

STT_MODEL_ID = "tiny.en"
PIPER_VOICE_STEM = "en_US-lessac-medium"


def voice_paths(root: Path | None = None) -> DataPaths:
    override = os.environ.get(ENV_VOICE_MODELS_ROOT, "").strip()
    if override:
        # Lab pin: treat override as ADA_DATA_ROOT-equivalent models parent.
        return DataPaths(root=Path(override).expanduser().resolve())
    return get_paths(root)


def pin_hf_cache(paths: DataPaths) -> None:
    """Force HuggingFace/CTranslate2 caches onto the HDD voice tree, not ~."""
    hf = paths.models_voice / "hf"
    hub = paths.models_voice_whisper / "hub"
    hf.mkdir(parents=True, exist_ok=True)
    hub.mkdir(parents=True, exist_ok=True)
    os.environ["HF_HOME"] = str(hf)
    os.environ["HF_HUB_CACHE"] = str(hub)
    os.environ["HUGGINGFACE_HUB_CACHE"] = str(hub)


def warmup_enabled() -> bool:
    raw = os.environ.get(ENV_VOICE_WARMUP, "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def piper_onnx(paths: DataPaths) -> Path:
    return paths.models_voice_piper / f"{PIPER_VOICE_STEM}.onnx"


def piper_config(paths: DataPaths) -> Path:
    return paths.models_voice_piper / f"{PIPER_VOICE_STEM}.onnx.json"


def whisper_ready(paths: DataPaths) -> bool:
    d = paths.models_voice_whisper
    if not d.is_dir():
        return False
    return any(d.rglob("model.bin")) or any(d.rglob("config.json"))


def piper_ready(paths: DataPaths) -> bool:
    return piper_onnx(paths).is_file() and piper_config(paths).is_file()
