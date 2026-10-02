/** SEO chain — Publish one page queues the first open YAML fact. Repair and publish wakes the current campaign. Not the Blog page form. */

let campaignId = "";

import { requireSessionForMode, sessionState } from "./session.js";
import { esc } from "./util.js";

function field(id) {
  return document.getElementById(id);
}

function setResult(text, kind) {
  const el = field("chain-result");
  if (!el) return;
  el.textContent = text || "";
  el.dataset.state = kind || "";
}

function render(data) {
  const stages = field("chain-stages");
  const queue = field("chain-queue");
  if (stages) {
    stages.innerHTML = (data.stages || [])
      .map((step) => {
        const bits = [step.stage, step.outcome].filter(Boolean);
        if (step.draft_path) bits.push(step.draft_path);
        if (step.reason) bits.push(step.reason);
        return '<li class="blog-step" data-state="' + esc(step.outcome) + '">' + esc(bits.join(" · ")) + "</li>";
      })
      .join("");
  }
  if (!queue) return;
  const published = (data.published || []).map((item) => {
    return (
      '<li data-state="published">published · ' +
      esc(item.source || "") +
      " · " +
      esc(item.question || "") +
      "</li>"
    );
  });
  const waiting = (data.queue || []).map((item) => {
    const mark = item.state || "waiting";
    return (
      '<li data-state="' +
      esc(mark) +
      '">' +
      esc(mark) +
      " · " +
      esc(item.source || "") +
      " · " +
      esc(item.question || "") +
      "</li>"
    );
  });
  const refused = (data.refusals || []).map((item) => {
    return (
      '<li data-state="refused">refused · ' +
      esc(item.reason || "") +
      " · " +
      esc(item.source || "") +
      " · " +
      esc(item.question || "") +
      "</li>"
    );
  });
  queue.innerHTML = published.concat(waiting).concat(refused).join("");
}

async function post(url, body) {
  const response = await fetch(url, {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await response.json().catch(() => ({}));
  return data;
}

function apply(data) {
  if (data && data.campaign_id) campaignId = data.campaign_id;
  render(data || {});
  const line = (data && data.result_line) || "Refused.";
  const draft = data && data.draft_path ? " Draft is " + data.draft_path + "." : "";
  const shown = data && data.draft_path && line.indexOf(data.draft_path) < 0 ? line + draft : line;
  setResult(shown, data && data.ok ? "ok" : "fail");
}

async function publishPage(event) {
  event.preventDefault();
  if (!sessionState.agentArmed) {
    requireSessionForMode("agent");
    setResult("Log in, then publish one page.", "fail");
    return;
  }
  const button = field("chain-publish");
  if (button) button.disabled = true;
  setResult("Publishing one page…", "");
  const stages = field("chain-stages");
  if (stages) stages.innerHTML = "";
  try {
    const data = await post("/api/chain/page", {});
    apply(data);
  } catch (err) {
    setResult(String(err), "fail");
  } finally {
    if (button) button.disabled = false;
  }
}

async function repairPage() {
  if (!sessionState.agentArmed) {
    requireSessionForMode("agent");
    setResult("Log in, then repair and publish.", "fail");
    return;
  }
  const button = field("chain-repair");
  if (button) button.disabled = true;
  setResult("Repairing and publishing…", "");
  const stages = field("chain-stages");
  if (stages) stages.innerHTML = "";
  try {
    const data = await post("/api/chain/repair", { campaign_id: campaignId });
    apply(data);
  } catch (err) {
    setResult(String(err), "fail");
  } finally {
    if (button) button.disabled = false;
  }
}

export function wireChain() {
  const form = field("chain-form");
  if (!form) return;
  form.addEventListener("submit", publishPage);
  const repair = field("chain-repair");
  if (repair) repair.addEventListener("click", repairPage);
}
