/** Blog page form — one step at a time, with the current step marked. */

import { requireSessionForMode, sessionState } from "./session.js";
import { esc } from "./util.js";

const RUN_LABEL = {
  store: "Store the row",
  gather: "Gather the card",
  draft: "Draft the file",
  copy: "Confirm copy",
  delete: "Confirm delete",
};

const state = {
  campaignId: null,
  current: "store",
  draftConfirm: false,
  fresh: false,
};

function field(id) {
  return document.getElementById(id);
}

function formValues() {
  return {
    site: field("blog-site").value,
    audience: field("blog-audience").value,
    source: field("blog-source").value,
    question: field("blog-question").value,
    fill: field("blog-fill").value,
    cta_label: field("blog-cta-label").value,
    cta_url: field("blog-cta-url").value,
  };
}

function fillForm(page) {
  if (!page) return;
  field("blog-site").value = page.site || field("blog-site").value;
  field("blog-audience").value = page.audience || "";
  field("blog-source").value = page.source || field("blog-source").value;
  field("blog-question").value = page.question || "";
  if (page.fill) field("blog-fill").value = page.fill;
  field("blog-cta-label").value = page.cta_label || "";
  field("blog-cta-url").value = page.cta_url || "";
}

function setResult(text, kind) {
  const el = field("blog-result");
  if (!el) return;
  el.textContent = text || "";
  el.dataset.state = kind || "";
}

function render(status) {
  const list = field("blog-steps");
  const detail = field("blog-step-detail");
  const button = field("blog-run");
  if (!list || !status) return;
  state.current = status.current || "store";
  if (!state.fresh) state.campaignId = status.campaign_id || null;
  list.innerHTML = (status.steps || [])
    .map((step) => {
      const mark = step.state === "done" ? "done · " : step.state === "current" ? "now · " : "";
      return (
        '<li class="blog-step" data-state="' +
        esc(step.state) +
        '">' +
        esc(mark + step.label) +
        "</li>"
      );
    })
    .join("");
  const current = (status.steps || []).find((step) => step.id === state.current);
  if (detail) detail.textContent = current ? current.detail : "";
  if (button) {
    const label =
      state.current === "draft" && state.draftConfirm
        ? "Confirm draft"
        : RUN_LABEL[state.current] || "Run";
    button.textContent = label;
  }
  if (status.page && !state.fresh) fillForm(status.page);
  const bits = [];
  if (status.loop_status) bits.push("status " + status.loop_status);
  if (status.packet_count) bits.push(status.packet_count + " spans");
  if (status.slug) bits.push("slug " + status.slug);
  if (bits.length && detail && current) {
    detail.textContent = current.detail + " " + bits.join(" · ") + ".";
  }
}

async function loadStatus() {
  const query = state.campaignId ? "?campaign_id=" + encodeURIComponent(state.campaignId) : "";
  const response = await fetch("/api/blog" + query, { credentials: "same-origin" });
  if (!response.ok) {
    setResult("Could not read the blog steps.", "fail");
    return;
  }
  render(await response.json());
}

async function runStep(event) {
  event.preventDefault();
  if (!sessionState.agentArmed) {
    requireSessionForMode("agent");
    setResult("Log in, then run the step.", "fail");
    return;
  }
  const button = field("blog-run");
  const currentChip = document.querySelector('.blog-step[data-state="current"]');
  if (currentChip) currentChip.dataset.state = "running";
  if (button) button.disabled = true;
  setResult(RUN_LABEL[state.current] + "…", "");
  const confirmed =
    state.current === "copy" ||
    state.current === "delete" ||
    (state.current === "draft" && state.draftConfirm);
  try {
    const response = await fetch("/api/blog/step", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        step: state.current,
        campaign_id: state.fresh ? null : state.campaignId,
        confirmed,
        ...formValues(),
      }),
    });
    const data = await response.json().catch(() => ({}));
    state.draftConfirm = !!(data.needs_confirm && state.current === "draft");
    state.fresh = false;
    if (data.status) render(data.status);
    const kind = data.ok ? "ok" : data.needs_confirm ? "" : "fail";
    setResult(data.result_line || data.message || "Done.", kind);
  } catch (err) {
    setResult(String(err), "fail");
  } finally {
    if (button) button.disabled = false;
  }
}

export function wireBlog() {
  const form = field("blog-form");
  const fresh = field("blog-new");
  if (!form) return;
  form.addEventListener("submit", runStep);
  if (fresh) {
    fresh.addEventListener("click", () => {
      state.fresh = true;
      state.campaignId = null;
      state.current = "store";
      state.draftConfirm = false;
      field("blog-audience").value = "";
      field("blog-question").value = "";
      field("blog-cta-label").value = "";
      field("blog-cta-url").value = "";
      render({
        current: "store",
        campaign_id: null,
        steps: [
          { id: "store", label: "Store", state: "current", detail: "Saves site, audience, source, question, and fill on the sidecar." },
          { id: "gather", label: "Gather", state: "later", detail: "" },
          { id: "draft", label: "Draft", state: "later", detail: "" },
          { id: "copy", label: "Copy", state: "later", detail: "" },
          { id: "delete", label: "Delete", state: "later", detail: "" },
        ],
      });
      setResult("New row. Store is the step that can run now.", "");
    });
  }
  loadStatus().catch(() => setResult("Could not read the blog steps.", "fail"));
}
