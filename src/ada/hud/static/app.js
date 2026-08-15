/* ADA HUD — chat-first surface (M13). Escape all untrusted text (XSS). */

function esc(s) {
  const d = document.createElement("div");
  d.textContent = s == null ? "" : String(s);
  return d.innerHTML;
}

async function getJson(url) {
  const r = await fetch(url, { credentials: "same-origin" });
  if (!r.ok) {
    let detail = "";
    try {
      const body = await r.json();
      detail = body.message || body.error || "";
    } catch (_) {
      /* ignore */
    }
    const err = new Error(url + " " + r.status + (detail ? " " + detail : ""));
    err.status = r.status;
    err.detail = detail;
    throw err;
  }
  return r.json();
}

function bytesGiB(n) {
  if (n == null || Number.isNaN(Number(n))) return "—";
  return (Number(n) / 1073741824).toFixed(1) + " GiB";
}

function truncJson(obj, max) {
  const s = JSON.stringify(obj ?? {});
  if (s.length <= max) return s;
  return s.slice(0, max - 1) + "…";
}

function setAuthBadge(auth) {
  const el = document.getElementById("auth-badge");
  el.textContent = "auth=" + auth;
  el.className = "badge " + (auth === "session" ? "session" : "mesh");
}

function metricCard(label, value, sub) {
  return (
    '<div class="metric-card"><div class="label">' +
    esc(label) +
    '</div><div class="value">' +
    esc(value) +
    "</div>" +
    (sub
      ? '<div class="sub">' + esc(sub) + "</div>"
      : "") +
    "</div>"
  );
}

function metricPill(label, value) {
  return (
    '<div class="metric-pill"><span class="v">' +
    esc(value) +
    '</span><span class="k">' +
    esc(label) +
    "</span></div>"
  );
}

function diskByLabel(disks, label) {
  if (!Array.isArray(disks)) return null;
  return disks.find((d) => d.label === label) || null;
}

function renderVitals(data, doctor) {
  const v = data.vitals || {};
  const t = v.thermal || {};
  const load = v.load || {};
  const mem = v.memory || {};
  const mounts = v.mounts || {};
  const extras = v.extras || {};
  const urgent = data.urgent_faults || [];
  const root = diskByLabel(v.disks, "rootfs");
  const ada = diskByLabel(v.disks, "ada-data");
  const cores =
    extras.cpu_count != null
      ? String(extras.cpu_count) + (extras.arch ? " · " + extras.arch : "")
      : extras.arch || "—";

  const cards =
    metricCard("Temp", t.temp_c != null ? t.temp_c + "°C" : "—", t.temp_source || "") +
    metricCard("Throttle", t.throttled_hex || "—", "") +
    metricCard("Cores / arch", cores, extras.os_pretty || "") +
    metricCard(
      "Load",
      load.load1 != null ? String(load.load1) : "—",
      load.load5 != null
        ? "5=" + load.load5 + " · 15=" + load.load15
        : ""
    ) +
    metricCard(
      "Memory",
      bytesGiB(mem.mem_available_bytes),
      "avail / " + bytesGiB(mem.mem_total_bytes) + " total"
    ) +
    metricCard(
      "Disk /",
      root ? bytesGiB(root.avail_bytes) : "—",
      root ? "avail / " + bytesGiB(root.total_bytes) : ""
    ) +
    metricCard(
      "Disk ada-data",
      ada ? bytesGiB(ada.avail_bytes) : "—",
      (ada ? "avail / " + bytesGiB(ada.total_bytes) + " · " : "") +
        "mount " +
        (mounts.ada_data_ok === true
          ? "OK"
          : mounts.ada_data_ok === false
            ? "BAD"
            : "—")
    ) +
    metricCard(
      "Tailscale",
      extras.tailscale_ipv4 || "—",
      extras.tailscale_ipv4 ? "IPv4" : "optional"
    );

  document.getElementById("vitals-cards").innerHTML = cards;

  const strip =
    metricPill("temp", t.temp_c != null ? t.temp_c + "°" : "—") +
    metricPill("thr", t.throttled_hex || "—") +
    metricPill(
      "mnt",
      mounts.ada_data_ok === true ? "OK" : mounts.ada_data_ok === false ? "BAD" : "—"
    ) +
    metricPill("cpu", extras.cpu_count != null ? extras.cpu_count + "c" : "—") +
    metricPill("load", load.load1 != null ? String(load.load1) : "—") +
    metricPill("mem", bytesGiB(mem.mem_available_bytes));
  document.getElementById("vitals-strip").innerHTML = strip;

  const badge = document.getElementById("doctor-badge");
  const probeN = (v.probe_errors || []).length;
  const urgentN = urgent.length;
  if (doctor && Array.isArray(doctor.urgent)) {
    const dUrgent = doctor.urgent.length;
    const dProbe = (doctor.probe_errors || []).length;
    if (dUrgent === 0 && dProbe === 0 && doctor.ada_data_ok) {
      badge.textContent = "doctor: all clear";
      badge.className = "doctor-badge clear";
    } else {
      badge.textContent =
        "doctor: urgent=" +
        dUrgent +
        " · probes=" +
        dProbe +
        " · ada_data_ok=" +
        doctor.ada_data_ok;
      badge.className = "doctor-badge" + (dUrgent ? " urgent" : "");
    }
  } else if (urgentN === 0 && probeN === 0 && mounts.ada_data_ok) {
    badge.textContent = "doctor: all clear";
    badge.className = "doctor-badge clear";
  } else {
    badge.textContent =
      "doctor: urgent=" + urgentN + " · probes=" + probeN;
    badge.className = "doctor-badge" + (urgentN ? " urgent" : "");
  }

  document.getElementById("vitals-meta").textContent =
    "ts=" +
    (v.ts || "—") +
    " · probe_errors=" +
    probeN +
    (urgentN ? " · urgent=" + urgent.join(",") : "");
}

async function refreshVitals() {
  try {
    const [data, doctor] = await Promise.all([
      getJson("/api/vitals"),
      getJson("/api/doctor").catch(() => null),
    ]);
    renderVitals(data, doctor);
  } catch (e) {
    document.getElementById("vitals-cards").textContent = String(e);
    document.getElementById("doctor-badge").textContent = "doctor: error";
  }
}

function shortWake(obj) {
  if (!obj) return "n/a";
  if (typeof obj === "string") return obj;
  const ts = obj.ts || obj.at || obj.born_at;
  const kind = obj.type || obj.event || "";
  if (ts) return String(ts) + (kind ? " · " + kind : "");
  try {
    return truncJson(obj, 80);
  } catch (_) {
    return "—";
  }
}

async function refreshLifecycle() {
  const root = document.getElementById("lifecycle");
  try {
    const data = await getJson("/api/lifecycle");
    const rows = [
      ["born", data.born_at || "n/a"],
      ["wake", shortWake(data.last_wake)],
      ["fault", shortWake(data.last_fault)],
      ["dream", (data.last_dream_status || "n/a") + " · " + (data.last_dream_at || "n/a")],
      ["push", data.push || "skipped"],
    ];
    root.innerHTML = rows
      .map(
        ([k, v]) =>
          '<div class="life-row"><span class="k">' +
          esc(k) +
          '</span><span class="v">' +
          esc(v) +
          "</span></div>"
      )
      .join("");
  } catch (e) {
    root.textContent = String(e);
  }
}

async function refreshMode() {
  try {
    const data = await getJson("/api/mode");
    setAuthBadge(data.auth || "mesh");
    if (data.mode) {
      document.getElementById("mode-select").value = data.mode;
    }
    const armed = data.agent_armed;
    const armedEl = document.getElementById("armed-chip");
    armedEl.textContent = "agent_armed=" + String(armed ?? "—");
    armedEl.className = "chip " + (armed ? "ok" : "muted");

    const chips = document.getElementById("mode-chips");
    chips.innerHTML =
      '<span class="chip">mode=' +
      esc(data.mode || "—") +
      "</span>" +
      '<span class="chip">auth=' +
      esc(data.auth || "—") +
      "</span>" +
      '<span class="chip">agent_armed=' +
      esc(String(armed ?? "—")) +
      "</span>" +
      (data.tailscale_user
        ? '<span class="chip muted">ts=' + esc(data.tailscale_user) + "</span>"
        : "");

    const denials = data.last_denials || [];
    const line = document.getElementById("denial-line");
    if (denials.length) {
      const last = denials[denials.length - 1];
      line.textContent =
        typeof last === "string" ? last : truncJson(last, 160);
    } else {
      line.textContent = "";
    }
  } catch (e) {
    document.getElementById("mode-chips").textContent = String(e);
  }
}

async function refreshTail() {
  try {
    const data = await getJson("/api/run/tail?n=80");
    document.getElementById("run-path").textContent = data.path || "(no run yet)";
    const lines = (data.records || []).map((r) => JSON.stringify(r));
    document.getElementById("raw-tail").textContent = lines.join("\n");
  } catch (e) {
    document.getElementById("raw-tail").textContent = String(e);
  }
}

function appendNode(node) {
  const root = document.getElementById("stream");
  root.appendChild(node);
  root.scrollTop = root.scrollHeight;
}

function appendUserTurn(text) {
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
  body.textContent = (body.textContent || "") + (text || "");
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
  const msg = payload.message || payload.error || JSON.stringify(payload);
  div.textContent = msg;
  appendNode(div);
}

/** Retained from last usage_update SSE (turn_done often omits usage). */
let lastUsage = null;

function formatUsageCrumb(u) {
  if (!u || typeof u !== "object") return "";
  const parts = [];
  const prompt = u.prompt_token_count ?? u.prompt_tokens;
  const cand = u.candidates_token_count ?? u.candidates_tokens;
  if (prompt != null || cand != null) {
    parts.push("tok=" + (prompt != null ? prompt : "?") + "+" + (cand != null ? cand : "?"));
  } else {
    const total = u.total_token_count ?? u.total;
    if (total != null) parts.push("tokens=" + total);
  }
  if (u.usd_estimate != null && u.usd_estimate !== "") {
    const n = Number(u.usd_estimate);
    if (!Number.isNaN(n)) parts.push("~$" + n.toFixed(6));
  }
  return parts.join(" · ");
}

function appendTurnFooter(payload) {
  closeAssistantTurn();
  const div = document.createElement("div");
  div.className = "turn-footer";
  let t =
    "stop=" +
    (payload.stop_reason || "") +
    " · steps=" +
    (payload.steps ?? "");
  const usage = payload.usage || lastUsage;
  const crumb = formatUsageCrumb(usage);
  if (crumb) t += " · " + crumb;
  lastUsage = null;
  div.textContent = t;
  appendNode(div);
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
  window.__lastToolCard = id;
}

function finishToolCard(payload) {
  const el = document.getElementById(window.__lastToolCard || "");
  if (!el) return;
  el.classList.remove("pending");
  el.classList.add(payload.ok ? "ok" : "fail");
  const chip = el.querySelector(".status-chip");
  if (chip) chip.textContent = payload.ok ? "ok" : "fail";
  const receipt = el.querySelector(".receipt");
  if (receipt) {
    receipt.textContent = "receipt=" + (payload.receipt_id || "—");
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
  } else if (event === "fault") {
    closeAssistantTurn();
    appendFault(payload);
  } else if (event === "session_receipt_path") {
    document.getElementById("run-path").textContent = payload.path || "";
  } else if (event === "turn_done") {
    appendTurnFooter(payload);
  } else if (event === "usage_update") {
    lastUsage = payload;
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

async function sendChat(message, mode) {
  const btn = document.getElementById("chat-send");
  btn.disabled = true;
  try {
    const resp = await fetch("/api/chat", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
      body: JSON.stringify({ message, mode }),
    });
    if (resp.status === 401) {
      const err = await resp.json();
      appendFault({
        message: err.message || "session required for Agent",
      });
      await refreshMode();
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
    await refreshTail();
    await refreshMode();
  } finally {
    btn.disabled = false;
  }
}

/* ---------- X-ray (P2) ---------- */

const xrayState = {
  root: "memory",
  path: "",
  previewMode: "rendered",
  content: "",
  kind: "",
  name: "",
};

function setView(name) {
  const chat = document.getElementById("view-chat");
  const xray = document.getElementById("view-xray");
  const tabChat = document.getElementById("tab-chat");
  const tabXray = document.getElementById("tab-xray");
  const isChat = name === "chat";
  chat.hidden = !isChat;
  xray.hidden = isChat;
  tabChat.classList.toggle("active", isChat);
  tabXray.classList.toggle("active", !isChat);
}

function relJoin(base, name) {
  if (!base) return name;
  return base.replace(/\/+$/, "") + "/" + name;
}

function parentPath(p) {
  if (!p) return "";
  const parts = p.split("/").filter(Boolean);
  parts.pop();
  return parts.join("/");
}

async function xrayList() {
  const list = document.getElementById("xray-list");
  const pathEl = document.getElementById("xray-path");
  pathEl.textContent = xrayState.root + "/" + (xrayState.path || "");
  list.innerHTML = "";
  try {
    const q =
      "/api/xray/list?root=" +
      encodeURIComponent(xrayState.root) +
      "&path=" +
      encodeURIComponent(xrayState.path || "");
    const data = await getJson(q);
    if (xrayState.path) {
      const up = document.createElement("li");
      up.innerHTML = '<span class="name">..</span><span class="meta-r">up</span>';
      up.addEventListener("click", () => {
        xrayState.path = parentPath(xrayState.path);
        xrayList();
      });
      list.appendChild(up);
    }
    for (const ent of data.entries || []) {
      const li = document.createElement("li");
      const size =
        ent.type === "dir"
          ? "dir"
          : ent.size != null
            ? ent.size + " B"
            : "";
      li.innerHTML =
        '<span class="name">' +
        esc(ent.name) +
        '</span><span class="meta-r">' +
        esc(size) +
        "</span>";
      li.addEventListener("click", () => {
        if (ent.type === "dir") {
          xrayState.path = relJoin(xrayState.path, ent.name);
          xrayList();
        } else {
          xrayRead(relJoin(xrayState.path, ent.name));
        }
      });
      list.appendChild(li);
    }
  } catch (e) {
    list.innerHTML =
      '<li><span class="name">' + esc(String(e)) + "</span></li>";
  }
}

function detectPreviewKind(path, contentType) {
  const p = (path || "").toLowerCase();
  if (p.includes("/dreams/") || p.includes("memory/dreams")) return "dream";
  if (p.includes("/worldview/")) return "worldview";
  if (/\/cites\/c_.*\.md$/.test(p) || /\/cites\//.test(p) && p.endsWith(".md"))
    return "cite";
  if (p.includes("/facts/") && (p.endsWith(".yaml") || p.endsWith(".yml")))
    return "fact";
  if (p.endsWith(".jsonl") || p.includes("/runs/")) return "jsonl";
  if (p.endsWith(".md")) return "md";
  if ((contentType || "").includes("json")) return "json";
  return "text";
}

/** Escape-first lightweight markdown — no raw HTML pass-through. */
function renderMarkdownSafe(src) {
  const lines = String(src || "").split(/\r?\n/);
  const out = [];
  let inCode = false;
  let codeBuf = [];
  for (const line of lines) {
    if (line.trim().startsWith("```")) {
      if (inCode) {
        out.push("<pre><code>" + esc(codeBuf.join("\n")) + "</code></pre>");
        codeBuf = [];
        inCode = false;
      } else {
        inCode = true;
      }
      continue;
    }
    if (inCode) {
      codeBuf.push(line);
      continue;
    }
    let l = esc(line);
    if (/^###\s+/.test(line)) {
      out.push('<div class="md-h3">' + esc(line.replace(/^###\s+/, "")) + "</div>");
      continue;
    }
    if (/^##\s+/.test(line)) {
      out.push('<div class="md-h2">' + esc(line.replace(/^##\s+/, "")) + "</div>");
      continue;
    }
    if (/^#\s+/.test(line)) {
      out.push('<div class="md-h1">' + esc(line.replace(/^#\s+/, "")) + "</div>");
      continue;
    }
    if (/^\s*[-*]\s+/.test(line)) {
      out.push("<ul><li>" + inlineMd(esc(line.replace(/^\s*[-*]\s+/, ""))) + "</li></ul>");
      continue;
    }
    if (!l.trim()) {
      out.push("<br/>");
      continue;
    }
    out.push("<p>" + inlineMd(l) + "</p>");
  }
  if (inCode) {
    out.push("<pre><code>" + esc(codeBuf.join("\n")) + "</code></pre>");
  }
  return out.join("\n");
}

function inlineMd(escaped) {
  return escaped
    .replace(/`([^`]+)`/g, '<code class="md-code">$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
}

function splitCiteFrontmatter(text) {
  const m = String(text || "").match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$/);
  if (!m) return { meta: "", body: text };
  return { meta: m[1], body: m[2] };
}

function renderPreview() {
  const el = document.getElementById("xray-preview");
  const raw = xrayState.content || "";
  if (xrayState.previewMode === "raw") {
    el.className = "xray-preview";
    el.textContent = raw;
    return;
  }
  el.className = "xray-preview";
  const kind = xrayState.kind;
  if (kind === "cite") {
    const { meta, body } = splitCiteFrontmatter(raw);
    el.innerHTML =
      '<div class="cite-meta">' +
      esc(meta || "(no frontmatter)") +
      "</div>" +
      renderMarkdownSafe(body.slice(0, 8000));
    return;
  }
  if (kind === "dream" || kind === "worldview" || kind === "md") {
    el.innerHTML = renderMarkdownSafe(raw);
    return;
  }
  if (kind === "jsonl") {
    const lines = raw.split("\n").filter(Boolean).slice(-12);
    const cards = lines
      .map((ln) => {
        try {
          return (
            "<pre>" + esc(JSON.stringify(JSON.parse(ln), null, 2)) + "</pre>"
          );
        } catch (_) {
          return "<pre>" + esc(ln.slice(0, 400)) + "</pre>";
        }
      })
      .join("");
    el.innerHTML = cards || "<p class='muted-empty'>empty</p>";
    return;
  }
  if (kind === "fact" || kind === "json") {
    el.innerHTML = "<pre>" + esc(raw) + "</pre>";
    return;
  }
  el.innerHTML = "<pre>" + esc(raw) + "</pre>";
}

async function xrayRead(relPath) {
  const fileEl = document.getElementById("xray-file");
  fileEl.textContent = xrayState.root + "/" + relPath;
  try {
    const q =
      "/api/xray/read?root=" +
      encodeURIComponent(xrayState.root) +
      "&path=" +
      encodeURIComponent(relPath) +
      "&max_bytes=262144";
    const data = await getJson(q);
    if (data.binary || data.refused) {
      xrayState.content = "";
      document.getElementById("xray-preview").textContent =
        data.message || "binary / refused";
      return;
    }
    xrayState.content = data.text || "";
    xrayState.name = relPath;
    xrayState.kind = detectPreviewKind(
      xrayState.root + "/" + relPath,
      data.content_type
    );
    renderPreview();
  } catch (e) {
    document.getElementById("xray-preview").textContent = String(e);
  }
}

function wireXray() {
  document.querySelectorAll(".root-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document
        .querySelectorAll(".root-btn")
        .forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      xrayState.root = btn.getAttribute("data-root");
      xrayState.path = "";
      xrayState.content = "";
      document.getElementById("xray-preview").textContent =
        "Choose a file under an allowlisted root.";
      document.getElementById("xray-preview").className =
        "xray-preview muted-empty";
      xrayList();
    });
  });
  document.getElementById("preview-rendered").addEventListener("click", () => {
    xrayState.previewMode = "rendered";
    document.getElementById("preview-rendered").classList.add("active");
    document.getElementById("preview-raw").classList.remove("active");
    if (xrayState.content) renderPreview();
  });
  document.getElementById("preview-raw").addEventListener("click", () => {
    xrayState.previewMode = "raw";
    document.getElementById("preview-raw").classList.add("active");
    document.getElementById("preview-rendered").classList.remove("active");
    if (xrayState.content) renderPreview();
  });
  document.getElementById("tab-chat").addEventListener("click", () => setView("chat"));
  document.getElementById("tab-xray").addEventListener("click", () => {
    setView("xray");
    xrayList();
  });
}

/* ---------- forms / polls ---------- */

document.getElementById("chat-form").addEventListener("submit", (ev) => {
  ev.preventDefault();
  const input = document.getElementById("chat-input");
  const msg = input.value.trim();
  if (!msg) return;
  const mode = document.getElementById("mode-select").value;
  appendUserTurn(msg);
  input.value = "";
  sendChat(msg, mode);
});

document.getElementById("login-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const password = document.getElementById("password").value;
  const msg = document.getElementById("auth-msg");
  msg.textContent = "";
  const r = await fetch("/api/login", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    msg.textContent = data.message || "login failed";
    return;
  }
  document.getElementById("password").value = "";
  msg.textContent = "session armed";
  await refreshMode();
});

document.getElementById("logout-btn").addEventListener("click", async () => {
  await fetch("/api/logout", { method: "POST", credentials: "same-origin" });
  document.getElementById("auth-msg").textContent = "logged out";
  await refreshMode();
});

wireXray();

/** Phone: park lifecycle / mode / audit under More; desktop keeps them in organism. */
function layoutSecondary() {
  const organism = document.getElementById("organism");
  const slot = document.getElementById("more-mobile-slot");
  const life = document.getElementById("pane-lifecycle");
  const mode = document.getElementById("pane-mode-detail");
  const raw = document.getElementById("pane-raw");
  if (!organism || !slot || !life || !mode || !raw) return;
  const mobile = window.matchMedia("(max-width: 719px)").matches;
  const home = mobile ? slot : organism;
  if (life.parentElement !== home) home.appendChild(life);
  if (mode.parentElement !== home) home.appendChild(mode);
  if (raw.parentElement !== home) home.appendChild(raw);
}
layoutSecondary();
window.addEventListener("resize", layoutSecondary);

refreshVitals();
refreshLifecycle();
refreshMode();
refreshTail();
setInterval(refreshVitals, 3000);
setInterval(refreshLifecycle, 10000);
setInterval(refreshTail, 2000);
setInterval(refreshMode, 5000);
