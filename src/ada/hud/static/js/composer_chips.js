/** Composer quick-capture chips (M19a · M20c Mac + collapse). */

import { currentFace } from "./face.js";

function chipsWrap() {
  return document.getElementById("composer-chips-wrap");
}

function chipsToggle() {
  return document.getElementById("composer-chips-toggle");
}

function chipsRow() {
  return document.getElementById("composer-chips");
}

function chipsOpen() {
  const row = chipsRow();
  return !!(row && row.classList.contains("is-open"));
}

export function setComposerChipsOpen(open) {
  const row = chipsRow();
  const toggle = chipsToggle();
  if (!row || !toggle) return;
  const next = !!open;
  row.hidden = !next;
  row.classList.toggle("is-open", next);
  toggle.setAttribute("aria-expanded", next ? "true" : "false");
  toggle.classList.toggle("is-open", next);
}

export function syncComposerChipsChrome() {
  const wrap = chipsWrap();
  const toggle = chipsToggle();
  const row = chipsRow();
  if (!wrap || !toggle || !row) return;
  const mac = currentFace() === "mac";
  toggle.hidden = !mac;
  if (!mac) {
    setComposerChipsOpen(false);
    return;
  }
  /* Mac: closed by default; preserve open only if already expanded this session */
  if (!row.classList.contains("is-open")) {
    setComposerChipsOpen(false);
  }
}

export function wireComposerChips() {
  const row = chipsRow();
  const input = document.getElementById("chat-input");
  const toggle = chipsToggle();
  const wrap = chipsWrap();
  if (!row || !input) return;

  row.querySelectorAll(".composer-chip").forEach((btn) => {
    btn.addEventListener("click", () => {
      const pre = btn.getAttribute("data-prefill") || "";
      const chip = btn.getAttribute("data-chip") || "";
      input.value = pre;
      input.dataset.packChip = chip;
      input.focus();
      setComposerChipsOpen(false);
    });
  });

  input.addEventListener("input", () => {
    if (!input.value.trim()) {
      input.dataset.packChip = "";
    }
  });

  if (toggle) {
    toggle.addEventListener("click", (ev) => {
      ev.stopPropagation();
      setComposerChipsOpen(!chipsOpen());
    });
  }

  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape" && chipsOpen()) {
      setComposerChipsOpen(false);
    }
  });

  document.addEventListener("click", (ev) => {
    if (!chipsOpen() || !wrap) return;
    if (wrap.contains(ev.target)) return;
    setComposerChipsOpen(false);
  });

  syncComposerChipsChrome();
  document.documentElement.addEventListener("ada-face", syncComposerChipsChrome);
}
