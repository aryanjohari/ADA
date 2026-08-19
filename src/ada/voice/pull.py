"""One-shot weight pull onto the HDD voice tree. Never called from PTT."""

from __future__ import annotations

from pathlib import Path

import httpx

from ada.voice.paths import PIPER_VOICE_STEM, pin_hf_cache, piper_onnx, voice_paths
from ada.voice.stt import load_whisper
from ada.voice.tts import load_piper

PIPER_REMOTE = (
    "https://huggingface.co/rhasspy/piper-voices/resolve/main/"
    f"en/en_US/lessac/medium/{PIPER_VOICE_STEM}"
)


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with httpx.stream("GET", url, follow_redirects=True, timeout=120.0) as resp:
        resp.raise_for_status()
        with tmp.open("wb") as fh:
            for chunk in resp.iter_bytes():
                fh.write(chunk)
    tmp.replace(dest)


def pull_piper_voice() -> Path:
    paths = voice_paths()
    paths.ensure_voice_model_dirs()
    onnx = piper_onnx(paths)
    cfg = paths.models_voice_piper / f"{PIPER_VOICE_STEM}.onnx.json"
    if not onnx.is_file():
        _download(f"{PIPER_REMOTE}.onnx", onnx)
    if not cfg.is_file():
        _download(f"{PIPER_REMOTE}.onnx.json", cfg)
    return onnx


def pull_whisper_model() -> None:
    paths = voice_paths()
    paths.ensure_voice_model_dirs()
    pin_hf_cache(paths)
    model = load_whisper(download=True)
    if model is None:
        raise RuntimeError("faster-whisper tiny.en pull failed (install ada[voice])")


def pull_voice_models() -> dict[str, str]:
    """Download tiny.en + Piper lessac-medium into models/voice/. Idempotent."""
    pull_whisper_model()
    onnx = pull_piper_voice()
    load_piper(download=False)
    paths = voice_paths()
    return {
        "whisper": str(paths.models_voice_whisper),
        "piper": str(onnx),
    }
