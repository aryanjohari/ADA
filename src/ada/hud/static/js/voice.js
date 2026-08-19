/** PTT wedge — MediaRecorder fills composer; never auto-Send. Simplex vs TTS. */

import { postVoiceStt, postVoiceTts } from "./api.js";
import { currentFace } from "./face.js";

let _recorder = null;
let _chunks = [];
let _stream = null;
let _audio = null;
let _objectUrl = null;
let _analyserCtx = null;
let _state = "idle";
let _isBusy = () => false;
let _sawConfirm = () => false;

function micBtn() {
  return document.getElementById("chat-mic");
}

function speakChip() {
  return document.getElementById("voice-speak-chip");
}

function orb() {
  return document.getElementById("ada-orb");
}

function composer() {
  return document.getElementById("chat-input");
}

function sendBtn() {
  return document.getElementById("chat-send");
}

export function composerInputKind() {
  const el = composer();
  return el && el.dataset.inputKind === "stt" ? "stt" : "typed";
}

export function resetComposerInputKind() {
  const el = composer();
  if (el) el.dataset.inputKind = "typed";
}

export function voiceState() {
  return _state;
}

export function setVoiceState(next) {
  _state = next || "idle";
  const mic = micBtn();
  if (mic) {
    mic.dataset.state = _state;
    mic.disabled = _state === "busy" || _state === "speaking";
    mic.setAttribute("aria-label", _labelFor(_state));
  }
  const o = orb();
  if (o) o.dataset.state = _state;
  const chip = speakChip();
  if (chip) chip.hidden = _state !== "speaking";
  const send = sendBtn();
  if (send) {
    if (_state === "busy") send.disabled = true;
    else if (!_isBusy()) send.disabled = false;
  }
}

function _labelFor(state) {
  if (state === "listening") return "Release to stop";
  if (state === "busy") return "Mic busy";
  if (state === "speaking") return "ADA speaking";
  if (state === "confirm-pending") return "Confirm on screen";
  return "Hold to talk";
}

function pickMime() {
  const types = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"];
  if (!window.MediaRecorder) return "";
  for (const t of types) {
    if (MediaRecorder.isTypeSupported(t)) return t;
  }
  return "";
}

function stopAnalyser() {
  if (_analyserCtx) {
    try {
      _analyserCtx.close();
    } catch (_) {
      /* ignore */
    }
    _analyserCtx = null;
  }
}

function maybeAnalyser(mediaStream) {
  if (currentFace() !== "mac") return;
  if (!window.AudioContext && !window.webkitAudioContext) return;
  try {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    _analyserCtx = new Ctx();
    const src = _analyserCtx.createMediaStreamSource(mediaStream);
    const analyser = _analyserCtx.createAnalyser();
    analyser.fftSize = 32;
    src.connect(analyser);
  } catch (_) {
    _analyserCtx = null;
  }
}

function stopPlayback() {
  if (_audio) {
    try {
      _audio.pause();
    } catch (_) {
      /* ignore */
    }
    _audio = null;
  }
  if (_objectUrl) {
    URL.revokeObjectURL(_objectUrl);
    _objectUrl = null;
  }
}

export function stopSpeaking() {
  stopPlayback();
  if (_state === "speaking") setVoiceState("idle");
}

async function startListen(ev) {
  ev.preventDefault();
  if (_isBusy()) return;
  if (_state === "speaking" || _state === "busy") return;
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return;
  try {
    _stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true },
    });
  } catch (_) {
    return;
  }
  _chunks = [];
  const mime = pickMime();
  try {
    _recorder = mime
      ? new MediaRecorder(_stream, { mimeType: mime })
      : new MediaRecorder(_stream);
  } catch (_) {
    _stream.getTracks().forEach((t) => t.stop());
    _stream = null;
    return;
  }
  _recorder.ondataavailable = (e) => {
    if (e.data && e.data.size) _chunks.push(e.data);
  };
  _recorder.start();
  maybeAnalyser(_stream);
  setVoiceState("listening");
}

async function endListen(ev) {
  ev.preventDefault();
  if (!_recorder || _state !== "listening") return;
  const rec = _recorder;
  _recorder = null;
  await new Promise((resolve) => {
    rec.onstop = resolve;
    try {
      rec.stop();
    } catch (_) {
      resolve();
    }
  });
  stopAnalyser();
  if (_stream) {
    _stream.getTracks().forEach((t) => t.stop());
    _stream = null;
  }
  const blob = new Blob(_chunks, { type: rec.mimeType || "audio/webm" });
  _chunks = [];
  setVoiceState("busy");
  const input = composer();
  try {
    const { data } = await postVoiceStt(blob);
    const text = (data && data.transcript) || "";
    if (input && text) {
      input.value = text;
      input.dataset.inputKind = "stt";
      input.focus();
    }
  } catch (_) {
    /* fail closed — composer unchanged */
  }
  setVoiceState("idle");
}

export async function speakFinal(text) {
  const line = (text || "").trim();
  if (!line) return;
  if (_sawConfirm()) {
    setVoiceState("confirm-pending");
    return;
  }
  stopPlayback();
  setVoiceState("speaking");
  try {
    const resp = await postVoiceTts(line);
    if (!resp.ok) {
      setVoiceState(_sawConfirm() ? "confirm-pending" : "idle");
      return;
    }
    const blob = await resp.blob();
    if (!blob || blob.size < 44) {
      setVoiceState("idle");
      return;
    }
    _objectUrl = URL.createObjectURL(blob);
    _audio = new Audio(_objectUrl);
    _audio.onended = () => {
      stopPlayback();
      setVoiceState("idle");
    };
    _audio.onerror = () => {
      stopPlayback();
      setVoiceState("idle");
    };
    await _audio.play();
  } catch (_) {
    stopPlayback();
    setVoiceState("idle");
  }
}

export function wireVoice({ isBusy, sawConfirm } = {}) {
  if (typeof isBusy === "function") _isBusy = isBusy;
  if (typeof sawConfirm === "function") _sawConfirm = sawConfirm;
  const mic = micBtn();
  const input = composer();
  const stop = document.getElementById("voice-stop");
  if (!mic || !input) return;
  input.dataset.inputKind = "typed";
  input.addEventListener("input", () => {
    if (!input.value.trim()) input.dataset.inputKind = "typed";
  });
  mic.addEventListener("pointerdown", startListen);
  mic.addEventListener("pointerup", endListen);
  mic.addEventListener("pointercancel", endListen);
  mic.addEventListener("contextmenu", (ev) => ev.preventDefault());
  if (stop) stop.addEventListener("click", stopSpeaking);
  setVoiceState("idle");
}
