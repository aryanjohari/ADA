"""Local Piper TTS from HDD onnx. Request path never downloads."""

from __future__ import annotations

import io
import wave
from typing import Any

from ada.voice.paths import pin_hf_cache, piper_onnx, piper_ready, voice_paths

_voice: Any = None


def load_piper(*, download: bool = False) -> Any:
    global _voice
    if _voice is not None:
        return _voice
    paths = voice_paths()
    paths.ensure_voice_model_dirs()
    pin_hf_cache(paths)
    onnx = piper_onnx(paths)
    if not download and not piper_ready(paths):
        return None
    if not onnx.is_file():
        return None
    try:
        from piper import PiperVoice
    except ImportError:
        try:
            from piper.voice import PiperVoice  # type: ignore[no-redef]
        except ImportError:
            return None
    try:
        _voice = PiperVoice.load(str(onnx))
    except Exception:  # noqa: BLE001
        _voice = None
        return None
    return _voice


def synthesize_wav(text: str, *, voice: Any | None = None) -> bytes | None:
    line = (text or "").strip()
    if not line:
        return None
    engine = voice if voice is not None else load_piper(download=False)
    if engine is None:
        return None
    buf = io.BytesIO()
    try:
        sample_rate = 22050
        cfg = getattr(engine, "config", None)
        if cfg is not None:
            sample_rate = int(getattr(cfg, "sample_rate", sample_rate) or sample_rate)
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            if hasattr(engine, "synthesize_wav"):
                try:
                    engine.synthesize_wav(line, wf)
                except wave.Error:
                    # Some Piper builds require a fresh wav header they write themselves.
                    buf.seek(0)
                    buf.truncate(0)
                    with wave.open(buf, "wb") as wf2:
                        engine.synthesize_wav(line, wf2)
            else:
                for chunk in engine.synthesize(line):
                    data = getattr(chunk, "audio_int16_bytes", None)
                    if data is None:
                        audio = getattr(chunk, "audio_int16", None)
                        data = bytes(audio) if audio is not None else None
                    if data:
                        wf.writeframes(data)
    except Exception:  # noqa: BLE001
        return None
    raw = buf.getvalue()
    return raw if len(raw) > 44 else None
