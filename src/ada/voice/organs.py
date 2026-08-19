"""Process-global voice organs + thin RAM/throttle refuse. Not a load-shed loop."""

from __future__ import annotations

import threading
from dataclasses import dataclass

from ada.body.vitals import collect_vitals
from ada.voice.stt import SttResult, load_whisper, transcribe_bytes
from ada.voice.tts import load_piper, synthesize_wav

MEM_MIN_STT_BYTES = 400 * 1024 * 1024
MEM_MIN_TTS_BYTES = 300 * 1024 * 1024

_lock = threading.Lock()
_warmed = False


class VoiceRefuse(Exception):
    """STT/TTS refused this clip — stay local; do not call a speech vendor."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class LoadGate:
    ok: bool
    reason: str | None = None


def _throttled_now() -> bool:
    try:
        snap = collect_vitals()
    except Exception:  # noqa: BLE001
        return False
    bits = snap.thermal.throttled_bits
    return bool(bits and bits.throttled_now)


def _mem_available() -> int:
    try:
        snap = collect_vitals()
    except Exception:  # noqa: BLE001
        return 0
    return int(snap.memory.mem_available_bytes or 0)


def check_voice_load(*, stt: bool = True) -> LoadGate:
    """Thin fail-closed using existing body vitals. Not a control loop."""
    if _throttled_now():
        return LoadGate(ok=False, reason="throttled")
    need = MEM_MIN_STT_BYTES if stt else MEM_MIN_TTS_BYTES
    avail = _mem_available()
    if avail and avail < need:
        return LoadGate(ok=False, reason="low_mem")
    return LoadGate(ok=True)


def warm_voice_organs() -> None:
    """Load tiny.en + Piper if weights are already on disk. Never downloads."""
    global _warmed
    with _lock:
        if _warmed:
            return
        load_whisper(download=False)
        load_piper(download=False)
        _warmed = True


def transcribe_audio(audio: bytes, *, model=None) -> SttResult:
    if not audio:
        return SttResult(transcript="", reason="empty")
    gate = check_voice_load(stt=True)
    if not gate.ok:
        return SttResult(transcript="", refused=True, reason=gate.reason)
    return transcribe_bytes(audio, model=model)


def synthesize_speech(text: str, *, voice=None) -> bytes | None:
    line = (text or "").strip()
    if not line:
        return None
    gate = check_voice_load(stt=False)
    if not gate.ok:
        return None
    return synthesize_wav(line, voice=voice)
