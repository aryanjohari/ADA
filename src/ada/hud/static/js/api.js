/** Thin API wrappers. */

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

export async function postConfirm(tool, args) {
  const r = await fetch("/api/confirm", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tool, args }),
  });
  const data = await r.json().catch(() => ({}));
  return { ok: r.ok, status: r.status, data };
}

export async function openChatStream(message, mode) {
  return fetch("/api/chat", {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify({ message, mode }),
  });
}
