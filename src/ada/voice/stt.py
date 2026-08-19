"""Local faster-whisper STT. Request path never downloads."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ada.voice.paths import STT_MODEL_ID, pin_hf_cache, voice_paths, whisper_ready

MAX_AUDIO_BYTES = 2 * 1024 * 1024
MAX_AUDIO_SECONDS = 20
MIN_SAMPLES = 1600  # 100 ms at 16 kHz


@dataclass(frozen=True)
class SttResult:
    transcript: str
    refused: bool = False
    reason: str | None = None


def _decode_pcm16k(audio: bytes) -> tuple[Any, float] | None:
    """Decode webm/opus/wav/mp4 to 16 kHz float32 via PyAV (no system ffmpeg)."""
    if not audio:
        return None
    tmp_path: Path | None = None
    try:
        from faster_whisper.audio import decode_audio

        with tempfile.NamedTemporaryFile(suffix=".audio", delete=False) as tmp:
            tmp.write(audio)
            tmp_path = Path(tmp.name)
        arr = decode_audio(str(tmp_path), sampling_rate=16000)
    except Exception:  # noqa: BLE001
        return None
    finally:
        if tmp_path is not None:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
    if arr is None:
        return None
    n = int(getattr(arr, "shape", [0])[0] if hasattr(arr, "shape") else len(arr))
    if n < MIN_SAMPLES:
        return None
    return arr, n / 16000.0


_model: Any = None


def load_whisper(*, download: bool = False) -> Any:
    """Load tiny.en from the HDD tree. download=False on the request path."""
    global _model
    if _model is not None:
        return _model
    paths = voice_paths()
    paths.ensure_voice_model_dirs()
    pin_hf_cache(paths)
    if not download and not whisper_ready(paths):
        return None
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return None
    kwargs: dict[str, Any] = {
        "device": "cpu",
        "compute_type": "int8",
        "download_root": str(paths.models_voice_whisper),
        "local_files_only": not download,
    }
    try:
        _model = WhisperModel(STT_MODEL_ID, **kwargs)
    except Exception:  # noqa: BLE001
        _model = None
        return None
    return _model


def transcribe_bytes(audio: bytes, *, model: Any | None = None) -> SttResult:
    """Audio blob → transcript. Empty / decode-fail / silence → empty string."""
    if not audio:
        return SttResult(transcript="", reason="empty")
    if len(audio) > MAX_AUDIO_BYTES:
        return SttResult(transcript="", refused=True, reason="too_large")
    decoded = _decode_pcm16k(audio)
    if decoded is None:
        return SttResult(transcript="", reason="empty")
    pcm, duration = decoded
    if duration > MAX_AUDIO_SECONDS:
        return SttResult(transcript="", refused=True, reason="too_long")
    engine = model if model is not None else load_whisper(download=False)
    if engine is None:
        return SttResult(transcript="", refused=True, reason="stt_unavailable")
    try:
        segments, info = engine.transcribe(
            pcm,
            language="en",
            vad_filter=True,
            condition_on_previous_text=False,
        )
        parts: list[str] = []
        no_speech = True
        for seg in segments:
            text = (getattr(seg, "text", None) or "").strip()
            prob = getattr(seg, "no_speech_prob", 0.0) or 0.0
            if text and prob < 0.85:
                parts.append(text)
                no_speech = False
        if no_speech:
            return SttResult(transcript="", reason="empty")
        return SttResult(transcript=" ".join(parts).strip(), reason=None)
    except Exception:  # noqa: BLE001
        return SttResult(transcript="", reason="empty")
