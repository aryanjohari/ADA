/** Mode dial + session gate. */

import { requireSessionForMode, sessionState } from "./session.js";

export function getSelectedMode() {
  const el = document.getElementById("mode-select");
  return (el && el.value) || "observe";
}

export function setSelectedMode(mode) {
  const el = document.getElementById("mode-select");
  if (el) el.value = mode;
  sessionState.mode = mode;
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
  });
}
