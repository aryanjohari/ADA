/** Today strip — dues / reminds / pending / shelf heads (M16 Phase 1). */

import { fetchToday } from "./api.js";
import { esc } from "./util.js";

function itemLabel(kind, text, when) {
  const whenBit = when ? " · " + esc(String(when).slice(0, 16)) : "";
  return (
    '<li class="today-item today-' +
    esc(kind) +
    '"><span class="today-kind">' +
    esc(kind) +
    "</span> " +
    esc(text) +
    whenBit +
    "</li>"
  );
}

export async function refreshToday() {
  const strip = document.getElementById("today-strip");
  const list = document.getElementById("today-items");
  const pulse = document.getElementById("today-pulse");
  if (!strip || !list) return;

  let data;
  try {
    data = await fetchToday();
  } catch {
    strip.hidden = true;
    return;
  }
  if (!data || data.ok === false) {
    strip.hidden = true;
    return;
  }

  const bits = [];
  for (const t of data.due_todos || []) {
    bits.push(
      itemLabel(
        "due",
        t.title || t.text || t.id || "?",
        t.due_at
      )
    );
  }
  for (const t of data.remind_soon || []) {
    // Skip if already shown as due.
    const id = t.id;
    if ((data.due_todos || []).some((d) => d.id === id)) continue;
    bits.push(itemLabel("remind", t.title || t.text || "?", t.remind_at));
  }
  if (data.plan_sticky) {
    bits.push(
      itemLabel(
        "plan",
        "Unaccepted plan (" + (data.plan_sticky.step_count || 0) + " steps)",
        null
      )
    );
  }
  for (const c of data.pending_confirms || []) {
    bits.push(itemLabel("confirm", c.tool || "pending", null));
  }
  for (const a of (data.artifacts || []).slice(0, 2)) {
    bits.push(itemLabel("artifact", a.name || a.path || "file", null));
  }

  // M17: cap visible chips so the strip stays ≤~2 lines.
  const MAX_VISIBLE = 4;
  let shown = bits;
  if (bits.length > MAX_VISIBLE) {
    const extra = bits.length - MAX_VISIBLE;
    shown = bits.slice(0, MAX_VISIBLE);
    shown.push(
      '<li class="today-item today-more" title="' +
        esc(String(extra)) +
        ' more">+' +
        esc(String(extra)) +
        "</li>"
    );
  }

  list.innerHTML = shown.join("");
  const has = bits.length > 0 || data.continuity;
  strip.hidden = !has;

  if (pulse) {
    if (data.continuity && data.continuity.label) {
      pulse.hidden = false;
      pulse.textContent = data.continuity.label +
        (data.continuity.detail ? " · " + data.continuity.detail : "");
    } else {
      pulse.hidden = true;
      pulse.textContent = "";
    }
  }
}

export function startTodayPoll(ms = 45000) {
  refreshToday();
  window.setInterval(refreshToday, ms);
}
