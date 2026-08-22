/** Mode dial + session gate + soft intent→mode suggest (M15). */

import { currentFace } from "./face.js";
import { requireSessionForMode, sessionState } from "./session.js";

const _PLAN_RE =
  /\b(how should|plan|design|approach|propose|outline|strategy)\b/i;
const _AGENT_RE =
  /\b(remember|do it|go ahead|execute|upsert|write|save|apply|confirm)\b/i;
const _OBSERVE_RE =
  /\b(vitals|status|doctor|whoami|what('s| is) (wrong|up)|health|temp)\b/i;

export function getSelectedMode() {
  const el = document.getElementById("mode-select");
  return (el && el.value) || "observe";
}

export function setSelectedMode(mode) {
  const el = document.getElementById("mode-select");
  if (el) el.value = mode;
  sessionState.mode = mode;
  syncModeSegment();
  updateModeSuggest(null);
}

/** Soft suggest only — never grants write authority. */
export function suggestModeFromText(text) {
  const t = (text || "").trim();
  if (!t) return null;
  if (_OBSERVE_RE.test(t)) return "observe";
  if (_PLAN_RE.test(t)) return "plan";
  if (_AGENT_RE.test(t)) return "agent";
  return null;
}

export function updateModeSuggest(forced) {
  const chip = document.getElementById("mode-suggest");
  if (!chip) return;
  const suggested =
    forced !== undefined
      ? forced
      : suggestModeFromText(
          (document.getElementById("chat-input") || {}).value || ""
        );
  const current = getSelectedMode();
  const phone = currentFace() === "phone";
  if (!suggested || suggested === current || (phone && suggested === "plan")) {
    chip.hidden = true;
    chip.textContent = "";
    chip.dataset.suggest = "";
    return;
  }
  const label =
    suggested === "plan"
      ? "Plan"
      : suggested === "agent"
        ? "Agent"
        : phone
          ? "Ask"
          : "Observe";
  chip.hidden = false;
  chip.textContent = "Suggest: " + label;
  chip.dataset.suggest = suggested;
}

/** Phone: Ask label, hide Plan. Value stays observe|agent|plan. */
export function syncFaceModeDial() {
  const el = document.getElementById("mode-select");
  if (!el) return;
  const phone = currentFace() === "phone";
  const observeOpt = el.querySelector('option[value="observe"]');
  const planOpt = el.querySelector('option[value="plan"]');
  if (observeOpt) observeOpt.textContent = phone ? "Ask" : "Observe";
  if (planOpt) {
    planOpt.hidden = phone;
    planOpt.disabled = phone;
  }
  if (phone && el.value === "plan") {
    el.value = "observe";
    sessionState.mode = "observe";
  }
  syncModeSegment();
  updateModeSuggest(null);
}

function syncModeSegment() {
  const seg = document.getElementById("mode-segment");
  const el = document.getElementById("mode-select");
  if (!seg || !el) return;
  const phone = currentFace() === "phone";
  seg.hidden = !phone;
  if (!phone) return;
  seg.querySelectorAll(".mode-segment-btn").forEach((btn) => {
    const active = btn.dataset.mode === el.value;
    btn.classList.toggle("active", active);
    btn.setAttribute("aria-pressed", active ? "true" : "false");
  });
}

export function wireModeDial() {
  const el = document.getElementById("mode-select");
  if (!el) return;
  syncFaceModeDial();
  document.documentElement.addEventListener("ada-face", syncFaceModeDial);
  el.addEventListener("change", () => {
    const mode = el.value;
    sessionState.mode = mode;
    if (!requireSessionForMode(mode)) {
      /* stay on selection so user sees intent; chat will also gate */
    }
    syncModeSegment();
    updateModeSuggest(null);
  });

  const seg = document.getElementById("mode-segment");
  if (seg) {
    seg.querySelectorAll(".mode-segment-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const mode = btn.dataset.mode;
        if (!mode) return;
        setSelectedMode(mode);
        syncModeSegment();
        requireSessionForMode(mode);
      });
    });
  }

  const chip = document.getElementById("mode-suggest");
  if (chip) {
    chip.addEventListener("click", () => {
      const mode = chip.dataset.suggest;
      if (!mode) return;
      setSelectedMode(mode);
      requireSessionForMode(mode);
      /* never auto-send */
    });
  }

  const input = document.getElementById("chat-input");
  if (input) {
    input.addEventListener("input", () => updateModeSuggest(null));
  }
}
