/** Thin API wrappers. */

import { currentFace } from "./face.js";
import { getDeviceId } from "./device.js";
import { getJson } from "./util.js";

export function fetchMode() {
  return getJson("/api/mode");
}

export function fetchVitals() {
  return getJson("/api/vitals");
}

export function fetchDoctor() {
  return getJson("/api/doctor");
}

export function fetchLifecycle() {
  return getJson("/api/lifecycle");
}

export function fetchRunTail(n = 80) {
  return getJson("/api/run/tail?n=" + n);
}

export function fetchToday() {
  return getJson("/api/today");
}

export function fetchLifeDay(date = null) {
  const q = date ? "?date=" + encodeURIComponent(date) : "";
  return getJson("/api/life/day" + q);
}

export async function postLogin(password) {
  const r = await fetch("/api/login", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });
  const data = await r.json().catch(() => ({}));
  return { ok: r.ok, status: r.status, data };
}

export async function postLogout() {
  await fetch("/api/logout", { method: "POST", credentials: "same-origin" });
}

export async function postConfirm(tool, args, pendingId) {
  const body = { tool, args };
  if (pendingId) body.pending_id = pendingId;
  const r = await fetch("/api/confirm", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await r.json().catch(() => ({}));
  return { ok: r.ok, status: r.status, data };
}

export async function postPlanAccept(plan) {
  const r = await fetch("/api/plan/accept", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      plan_id: plan.plan_id || null,
      steps: (plan.steps || []).map((s) =>
        typeof s === "string" ? { text: s } : { text: s.text || "", id: s.id || null }
      ),
      raw_text: plan.raw_text || null,
    }),
  });
  const data = await r.json().catch(() => ({}));
  return { ok: r.ok, status: r.status, data };
}

export async function openChatStream(message, mode, chip = null, input = "typed") {
  return fetch("/api/chat", {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify({
      message,
      mode,
      chip,
      input: input === "stt" ? "stt" : "typed",
      face: currentFace(),
      device_id: getDeviceId(),
    }),
  });
}

export async function postVoiceStt(blob) {
  const body = new FormData();
  const type = (blob && blob.type) || "";
  const name =
    type.includes("mp4") || type.includes("aac") || type.includes("m4a")
      ? "utterance.m4a"
      : "utterance.webm";
  body.append("audio", blob, name);
  const r = await fetch("/api/voice/stt", {
    method: "POST",
    credentials: "same-origin",
    body,
  });
  const data = await r.json().catch(() => ({}));
  return { ok: r.ok, status: r.status, data };
}

export async function postVoiceTts(text) {
  return fetch("/api/voice/tts", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
}
