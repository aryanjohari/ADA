/** PTT wedge — MediaRecorder fills composer; never auto-Send. Simplex vs TTS. */

import { postVoiceStt, postVoiceTts } from "./api.js";
import { currentFace } from "./face.js";

const TTS_STORAGE = "ada_hud_tts";

let _recorder = null;
let _chunks = [];
let _stream = null;
let _audio = null;
let _objectUrl = null;
let _analyserCtx = null;
let _state = "idle";
let _arming = false;
let _stopWhenReady = false;
let _ttsOn = false;
let _isBusy = () => false;
let _sawConfirm = () => false;

function phoneFace() {
  return currentFace() === "phone";
}

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

export function ttsEnabled() {
  return _ttsOn;
}

function readTtsPref() {
  try {
    return localStorage.getItem(TTS_STORAGE) === "on";
  } catch (_) {
    return false;
  }
}

function persistTtsPref(on) {
  try {
    localStorage.setItem(TTS_STORAGE, on ? "on" : "off");
  } catch (_) {
    /* private mode */
  }
}

function ttsBtn() {
  return document.getElementById("tts-toggle");
}

function syncTtsButton() {
  const btn = ttsBtn();
  if (!btn) return;
  btn.setAttribute("aria-pressed", _ttsOn ? "true" : "false");
  btn.title = _ttsOn ? "Voice replies on" : "Voice replies off";
  btn.classList.toggle("tts-on", _ttsOn);
  const label = btn.querySelector(".tts-label");
  if (label) label.textContent = _ttsOn ? "TTS on" : "TTS off";
}

export function setTtsEnabled(on) {
  _ttsOn = !!on;
  persistTtsPref(_ttsOn);
  syncTtsButton();
  if (!_ttsOn) stopSpeaking();
}

function fieldStateFor(state) {
  if (state === "listening") return "listen";
  if (state === "confirm-pending") return "confirm";
  if (state === "busy" || state === "speaking") return "busy";
  return "idle";
}

export function syncComposerChrome() {
  const input = composer();
  const send = sendBtn();
  if (!input || !send) return;
  const phone = phoneFace();
  const hasText = !!input.value.trim();
  const busy = _isBusy() || _state === "busy" || _state === "speaking";
  if (phone) {
    send.hidden = !hasText;
    send.disabled = busy || !hasText;
  } else {
    send.hidden = false;
    send.disabled = busy;
  }
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
  document.documentElement.dataset.fieldState = fieldStateFor(_state);
  const chip = speakChip();
  if (chip) chip.hidden = !(_ttsOn && _state === "speaking");
  syncComposerChrome();
}

function _labelFor(state) {
  if (state === "listening") {
    return phoneFace() ? "Tap to stop" : "Release to stop";
  }
  if (state === "busy") return "Mic busy";
  if (state === "speaking") return "ADA speaking";
  if (state === "confirm-pending") return "Confirm on screen";
  return phoneFace() ? "Tap to talk" : "Hold to talk";
}

function pickMime() {
  const types = phoneFace()
    ? ["audio/mp4", "audio/aac", "audio/webm;codecs=opus", "audio/webm"]
    : ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"];
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

function abortArming() {
  _arming = false;
  _stopWhenReady = false;
  if (_stream) {
    _stream.getTracks().forEach((t) => t.stop());
    _stream = null;
  }
  _recorder = null;
}

async function startListen(ev) {
  if (ev) ev.preventDefault();
  if (_isBusy()) return;
  if (_arming || _recorder || _state === "listening") return;
  if (_state === "speaking" || _state === "busy") return;
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return;
  _arming = true;
  _stopWhenReady = false;
  try {
    _stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true },
    });
  } catch (_) {
    abortArming();
    return;
  }
  _chunks = [];
  const mime = pickMime();
  try {
    _recorder = mime
      ? new MediaRecorder(_stream, { mimeType: mime })
      : new MediaRecorder(_stream);
  } catch (_) {
    abortArming();
    return;
  }
  _recorder.ondataavailable = (e) => {
    if (e.data && e.data.size) _chunks.push(e.data);
  };
  _recorder.start();
  maybeAnalyser(_stream);
  _arming = false;
  setVoiceState("listening");
  if (_stopWhenReady) {
    _stopWhenReady = false;
    await endListen(ev);
  }
}

function fillComposerFromStt(text) {
  const input = composer();
  if (!input || !text) return;
  input.value = text;
  input.dataset.inputKind = "stt";
  input.dispatchEvent(new Event("input", { bubbles: true }));
  input.focus();
}

async function endListen(ev) {
  if (ev) ev.preventDefault();
  if (_arming && !_recorder) {
    _stopWhenReady = true;
    return;
  }
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
  if (!blob.size) {
    setVoiceState("idle");
    return;
  }
  setVoiceState("busy");
  try {
    const { data } = await postVoiceStt(blob);
    const text = (data && data.transcript) || "";
    fillComposerFromStt(text);
  } catch (_) {
    /* fail closed — composer unchanged */
  }
  setVoiceState("idle");
}

function onMicPointerDown(ev) {
  if (phoneFace()) return;
  startListen(ev);
}

function onMicPointerUp(ev) {
  if (phoneFace()) return;
  endListen(ev);
}

function onMicClick(ev) {
  if (!phoneFace()) return;
  ev.preventDefault();
  if (_arming || _state === "listening") endListen(ev);
  else startListen(ev);
}

export async function speakFinal(text) {
  if (!_ttsOn) {
    setVoiceState(_sawConfirm() ? "confirm-pending" : "idle");
    return;
  }
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
  _ttsOn = readTtsPref();
  syncTtsButton();
  const toggle = ttsBtn();
  if (toggle) {
    toggle.addEventListener("click", () => setTtsEnabled(!_ttsOn));
  }
  const mic = micBtn();
  const input = composer();
  const stop = document.getElementById("voice-stop");
  if (!mic || !input) return;
  input.dataset.inputKind = "typed";
  input.addEventListener("input", () => {
    if (!input.value.trim()) input.dataset.inputKind = "typed";
    syncComposerChrome();
  });
  document.documentElement.addEventListener("ada-face", syncComposerChrome);
  mic.addEventListener("pointerdown", onMicPointerDown);
  mic.addEventListener("pointerup", onMicPointerUp);
  mic.addEventListener("pointercancel", onMicPointerUp);
  mic.addEventListener("click", onMicClick);
  mic.addEventListener("contextmenu", (ev) => ev.preventDefault());
  if (stop) stop.addEventListener("click", stopSpeaking);
  setVoiceState("idle");
  syncComposerChrome();
}
