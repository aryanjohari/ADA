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

export function fetchToday() {
  return getJson("/api/today");
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
