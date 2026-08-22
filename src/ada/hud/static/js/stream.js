/** Chat stream — turns, tools, plan accept, confirm cards, SSE. */

import { openChatStream, postConfirm, postPlanAccept } from "./api.js";
import { renderMarkdownSafe } from "./markdown.js";
import { getSelectedMode, setSelectedMode } from "./mode.js";
import { requireSessionForMode } from "./session.js";
import { esc, truncJson } from "./util.js";
import { applyViewOpen } from "./view_registry.js";
import {
  composerInputKind,
  resetComposerInputKind,
  setVoiceState,
  speakFinal,
  syncComposerChrome,
  ttsEnabled,
  voiceState,
} from "./voice.js";

/** Set by wireChat — avoids circular import with body.js */
let _refreshTail = async () => {};
let _refreshMode = async () => {};


const CONFIRMABLE = new Set([
  "memory_facts_propose_edit",
  "memory_facts_append",
  "memory_open_loops_upsert",
  "artifact_write",
]);

/** Cortex/config faults — do not TTS the dump. Confirm-pending skip stays. */
const SKIP_TTS_STOPS = new Set(["error", "no_key"]);

export const streamState = {
  lastUsage: null,
  lastToolCardId: null,
  lastPlanText: null,
  lastPlan: null,
  busy: false,
  sawConfirm: false,
  pendingInput: "typed",
};

function appendNode(node) {
  const root = document.getElementById("stream");
  root.appendChild(node);
  root.scrollTop = root.scrollHeight;
}

export function appendUserTurn(text) {
  const div = document.createElement("div");
  div.className = "turn-user";
  div.innerHTML = '<span class="who">You</span>' + esc(text);
  appendNode(div);
}

function appendAssistantDelta(text) {
  const root = document.getElementById("stream");
  let el = root.querySelector(".turn-assistant.open");
  if (!el) {
    el = document.createElement("div");
    el.className = "turn-assistant open";
    el.innerHTML = '<span class="who">ADA</span><span class="body"></span>';
    appendNode(el);
  }
  const body = el.querySelector(".body");
  const raw = (body.dataset.rawText || "") + (text || "");
  body.dataset.rawText = raw;
  body.innerHTML = renderMarkdownSafe(raw, { headings: false });
  root.scrollTop = root.scrollHeight;
}

function closeAssistantTurn() {
  const el = document
    .getElementById("stream")
    .querySelector(".turn-assistant.open");
  if (el) el.classList.remove("open");
}

function appendFault(payload) {
  const div = document.createElement("div");
  div.className = "turn-fault";
  div.textContent =
    payload.message || payload.error || JSON.stringify(payload);
  appendNode(div);
}

function formatUsageCrumb(u) {
  if (!u || typeof u !== "object") return "";
  const parts = [];
  const prompt =
    u.prompt_token_count != null ? u.prompt_token_count : u.prompt_tokens;
  const cand =
    u.candidates_token_count != null
      ? u.candidates_token_count
      : u.candidates_tokens;
  if (prompt != null || cand != null) {
    parts.push(
      "tok=" +
        (prompt != null ? prompt : "?") +
        "+" +
        (cand != null ? cand : "?")
    );
  } else {
    const total = u.total_token_count != null ? u.total_token_count : u.total;
    if (total != null) parts.push("tokens=" + total);
  }
  if (u.usd_estimate != null && u.usd_estimate !== "") {
    const n = Number(u.usd_estimate);
    if (!Number.isNaN(n)) parts.push("~$" + n.toFixed(6));
  }
  return parts.join(" · ");
}

function planBodyText(plan) {
  if (!plan) return "";
  if (plan.steps && plan.steps.length) {
    return plan.steps
      .map((s, i) => {
        const t = typeof s === "string" ? s : s.text || "";
        return i + 1 + ". " + t;
      })
      .join("\n");
  }
  return plan.raw_text || streamState.lastPlanText || "";
}

function makePlanCard(plan) {
  const artifact =
    typeof plan === "string"
      ? { steps: [{ text: plan }], raw_text: plan, plan_id: null }
      : plan;
  streamState.lastPlan = artifact;
  streamState.lastPlanText = planBodyText(artifact);
  const card = document.createElement("div");
  card.className = "plan-card";
  const stepsHtml =
    artifact.steps && artifact.steps.length
      ? '<ol class="plan-steps">' +
        artifact.steps
          .map((s) => {
            const t = typeof s === "string" ? s : s.text || "";
            return "<li>" + esc(t) + "</li>";
          })
          .join("") +
        "</ol>"
      : '<div class="plan-body"></div>';
  card.innerHTML =
    '<div class="card-head"><span class="card-title">Plan</span>' +
    '<span class="status-chip">propose</span></div>' +
    stepsHtml +
    '<div class="card-actions">' +
    '<button type="button" class="primary" data-act="accept">Accept</button>' +
    '<button type="button" class="ghost" data-act="revise">Revise</button>' +
    '<button type="button" class="ghost" data-act="stay">Stay</button>' +
    "</div>";
  const bodyEl = card.querySelector(".plan-body");
  if (bodyEl) bodyEl.textContent = streamState.lastPlanText;
  card.querySelector('[data-act="accept"]').addEventListener("click", async () => {
    if (!requireSessionForMode("agent")) return;
    const acceptBtn = card.querySelector('[data-act="accept"]');
    if (acceptBtn) acceptBtn.disabled = true;
    const { ok, data } = await postPlanAccept(artifact);
    if (!ok) {
      appendFault({ message: data.message || "plan accept failed" });
      if (acceptBtn) acceptBtn.disabled = false;
      return;
    }
    setSelectedMode("agent");
    const pid = data.plan_id || artifact.plan_id || "";
    const stepLines = planBodyText(artifact);
    const cue =
      "Accepted plan — execute:\n" +
      (pid ? "plan_id=" + pid + "\n" : "") +
      stepLines;
    appendUserTurn(cue);
    const actions = card.querySelector(".card-actions");
    if (actions) actions.remove();
    const chip = card.querySelector(".status-chip");
    if (chip) chip.textContent = "accepted · todos=" + (data.count != null ? data.count : 0);
    sendChat(cue, "agent");
  });
  card.querySelector('[data-act="revise"]').addEventListener("click", () => {
    setSelectedMode("plan");
    const input = document.getElementById("chat-input");
    input.focus();
    input.placeholder = "Revise the plan…";
  });
  card.querySelector('[data-act="stay"]').addEventListener("click", () => {
    const actions = card.querySelector(".card-actions");
    if (actions) actions.remove();
  });
  appendNode(card);
}

function appendTurnFooter(payload) {
  closeAssistantTurn();
  const root = document.getElementById("stream");
  const lastAssist = [...root.querySelectorAll(".turn-assistant")].pop();
  const planText =
    lastAssist && lastAssist.querySelector(".body")
      ? lastAssist.querySelector(".body").textContent || ""
      : "";

  if (getSelectedMode() === "plan") {
    if (payload.plan && payload.plan.steps) {
      makePlanCard(payload.plan);
    } else if (streamState.lastPlan && streamState.lastPlan._cardShown) {
      /* already rendered from plan_artifact */
    } else if (streamState.lastPlan && streamState.lastPlan.steps) {
      streamState.lastPlan._cardShown = true;
      makePlanCard(streamState.lastPlan);
    } else if (planText.trim()) {
      makePlanCard(planText.trim());
    }
  }

  const div = document.createElement("div");
  div.className = "turn-footer";
  let t =
    "stop=" +
    (payload.stop_reason || "") +
    " · steps=" +
    (payload.steps != null ? payload.steps : "");
  const usage = payload.usage || streamState.lastUsage;
  const crumb = formatUsageCrumb(usage);
  if (crumb) t += " · " + crumb;
  streamState.lastUsage = null;
  div.textContent = t;
  appendNode(div);
  if (streamState.pendingInput === "stt") {
    if (streamState.sawConfirm) {
      setVoiceState("confirm-pending");
    } else if (SKIP_TTS_STOPS.has(payload.stop_reason || "")) {
      setVoiceState("idle");
    } else if (!ttsEnabled()) {
      setVoiceState("idle");
    } else {
      const ack = (payload && payload.text) || "";
      speakFinal(ack);
    }
  } else if (streamState.sawConfirm) {
    setVoiceState("confirm-pending");
  } else {
    setVoiceState("idle");
  }
}

function makeToolCard(payload) {
  const id = "tool-" + Date.now() + "-" + Math.random().toString(16).slice(2);
  const argsFull = JSON.stringify(payload.args || {}, null, 2);
  const argsShort = truncJson(payload.args || {}, 120);
  const div = document.createElement("div");
  div.className = "tool-card pending";
  div.id = id;
  div.innerHTML =
    '<div class="tool-head"><span class="tool-name">' +
    esc(payload.tool || "?") +
    '</span><span class="status-chip">…</span></div>' +
    '<div class="args-short">' +
    esc(argsShort) +
    "</div>" +
    '<div class="args-full">' +
    esc(argsFull) +
    "</div>" +
    '<button type="button" class="expand-args">expand args</button>' +
    '<div class="receipt"></div>';
  div.querySelector(".expand-args").addEventListener("click", () => {
    div.classList.toggle("expanded");
    const btn = div.querySelector(".expand-args");
    btn.textContent = div.classList.contains("expanded")
      ? "collapse args"
      : "expand args";
  });
  appendNode(div);
  streamState.lastToolCardId = id;
}

function makeConfirmCard(payload) {
  const tool = payload.tool || "?";
  const args = payload.args || {};
  const pendingId = payload.pending_id || payload.receipt_id || null;
  streamState.sawConfirm = true;
  setVoiceState("confirm-pending");
  const card = document.createElement("div");
  card.className = "confirm-card";
  const wired = CONFIRMABLE.has(tool);
  card.innerHTML =
    '<div class="card-head"><span class="card-title">Confirm</span>' +
    '<span class="status-chip">needs confirm</span></div>' +
    '<div class="confirm-tool">' +
    esc(tool) +
    "</div>" +
    '<pre class="confirm-args">' +
    esc(JSON.stringify(args, null, 2)) +
    "</pre>" +
    (wired
      ? ""
      : '<p class="confirm-note">Confirm path not wired for this tool — Deny only (no fake success).</p>') +
    '<div class="card-actions">' +
    (wired
      ? '<button type="button" class="primary" data-act="confirm">Confirm</button>'
      : "") +
    '<button type="button" class="danger" data-act="deny">Deny</button>' +
    "</div>";

  const actions = card.querySelector(".card-actions");
  const confirmBtn = card.querySelector('[data-act="confirm"]');
  if (confirmBtn) {
    confirmBtn.addEventListener("click", async () => {
      if (!requireSessionForMode("agent")) return;
      confirmBtn.disabled = true;
      const { ok, data } = await postConfirm(tool, args, pendingId);
      if (!ok) {
        appendFault({
          message: data.message || "confirm failed",
        });
        confirmBtn.disabled = false;
        return;
      }
      const obs = data.observation || {};
      actions.remove();
      const chip = card.querySelector(".status-chip");
      if (chip) {
        chip.textContent = obs.ok ? "confirmed ok" : "confirmed fail";
      }
      card.classList.add(obs.ok ? "ok" : "fail");
      appendNode(
        (() => {
          const d = document.createElement("div");
          d.className = "turn-footer";
          d.textContent =
            "confirm receipt=" + (obs.receipt_id || "—") +
            " · outcome=" +
            (obs.outcome || "—");
          return d;
        })()
      );
      await _refreshTail();
      await _refreshMode();
    });
  }
  card.querySelector('[data-act="deny"]').addEventListener("click", () => {
    actions.remove();
    const chip = card.querySelector(".status-chip");
    if (chip) chip.textContent = "denied";
    appendFault({ message: "Denied by operator: " + tool });
  });
  appendNode(card);
}

function finishToolCard(payload) {
  const el = document.getElementById(streamState.lastToolCardId || "");
  const needs =
    payload.needs_confirm === true || payload.outcome === "needs_confirm";
  if (el) {
    el.classList.remove("pending");
    if (needs) {
      el.classList.add("needs-confirm");
      const chip = el.querySelector(".status-chip");
      if (chip) chip.textContent = "needs confirm";
    } else {
      el.classList.add(payload.ok ? "ok" : "fail");
      const chip = el.querySelector(".status-chip");
      if (chip) chip.textContent = payload.ok ? "ok" : "fail";
    }
    const receipt = el.querySelector(".receipt");
    if (receipt) {
      receipt.textContent =
        "receipt=" +
        (payload.receipt_id || "—") +
        (payload.outcome ? " · " + payload.outcome : "");
    }
  }
  if (needs) {
    makeConfirmCard({
      tool: payload.tool,
      args: payload.args || {},
      receipt_id: payload.receipt_id,
      pending_id: payload.pending_id || payload.receipt_id,
    });
  }
}

function handleSseEvent(event, payload) {
  if (event === "token_delta") {
    appendAssistantDelta(payload.text || "");
  } else if (event === "tool_call_started") {
    closeAssistantTurn();
    makeToolCard(payload);
  } else if (event === "tool_call_finished") {
    finishToolCard(payload);
  } else if (event === "plan_artifact") {
    streamState.lastPlan = payload;
    streamState.lastPlanText = planBodyText(payload);
  } else if (event === "fault") {
    closeAssistantTurn();
    appendFault(payload);
  } else if (event === "session_receipt_path") {
    const pathEl = document.getElementById("run-path");
    if (pathEl) pathEl.textContent = payload.path || "";
  } else if (event === "turn_done") {
    appendTurnFooter(payload);
  } else if (event === "usage_update") {
    streamState.lastUsage = payload;
  } else if (event === "view_open") {
    applyViewOpen(payload);
  }
}

function parseSseChunk(buffer, onEvent) {
  const parts = buffer.split("\n\n");
  const rest = parts.pop() || "";
  for (const block of parts) {
    if (!block.trim() || block.startsWith(":")) continue;
    let event = "message";
    const dataLines = [];
    for (const line of block.split("\n")) {
      if (line.startsWith("event:")) event = line.slice(6).trim();
      else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
    }
    if (!dataLines.length) continue;
    try {
      onEvent(event, JSON.parse(dataLines.join("\n")));
    } catch (_) {
      /* ignore malformed */
    }
  }
  return rest;
}

export async function sendChat(message, mode, chip = null, input = "typed") {
  if (!requireSessionForMode(mode)) {
    appendFault({ message: "session required for " + mode });
    return;
  }
  const btn = document.getElementById("chat-send");
  streamState.busy = true;
  streamState.sawConfirm = false;
  streamState.pendingInput = input === "stt" ? "stt" : "typed";
  setVoiceState("busy");
  syncComposerChrome();
  btn.disabled = true;
  try {
    const resp = await openChatStream(message, mode, chip, streamState.pendingInput);
    if (resp.status === 401) {
      const err = await resp.json();
      appendFault({
        message: err.message || "session required for Agent",
      });
      await _refreshMode();
      return;
    }
    if (!resp.ok || !resp.body) {
      appendFault({ message: "chat HTTP " + resp.status });
      return;
    }
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      buf = parseSseChunk(buf, handleSseEvent);
    }
    if (buf) parseSseChunk(buf + "\n\n", handleSseEvent);
    await _refreshTail();
    await _refreshMode();
  } finally {
    streamState.busy = false;
    syncComposerChrome();
    if (voiceState() === "busy") {
      setVoiceState(streamState.sawConfirm ? "confirm-pending" : "idle");
    }
  }
}

export function wireChat({ refreshTail, refreshMode } = {}) {
  if (refreshTail) _refreshTail = refreshTail;
  if (refreshMode) _refreshMode = refreshMode;
  document.getElementById("chat-form").addEventListener("submit", (ev) => {
    ev.preventDefault();
    const input = document.getElementById("chat-input");
    const msg = input.value.trim();
    if (!msg || streamState.busy) return;
    const mode = getSelectedMode();
    const chip = input.dataset.packChip || null;
    const kind = composerInputKind();
    if (!requireSessionForMode(mode)) return;
    appendUserTurn(msg);
    input.value = "";
    input.dataset.packChip = "";
    resetComposerInputKind();
    syncComposerChrome();
    sendChat(msg, mode, chip, kind);
  });
}
