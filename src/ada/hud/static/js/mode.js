/** Mode dial + session gate + soft intent→mode suggest (M15). */

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
  if (!suggested || suggested === current) {
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
        : "Observe";
  chip.hidden = false;
  chip.textContent = "Suggest: " + label;
  chip.dataset.suggest = suggested;
}

export function wireModeDial() {
  const el = document.getElementById("mode-select");
  if (!el) return;
  el.addEventListener("change", () => {
    const mode = el.value;
    sessionState.mode = mode;
    if (!requireSessionForMode(mode)) {
      /* stay on selection so user sees intent; chat will also gate */
    }
    updateModeSuggest(null);
  });

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
