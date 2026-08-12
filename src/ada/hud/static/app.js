/* ADA HUD — plain JS; escape all stream text (XSS). */

function esc(s) {
  const d = document.createElement("div");
  d.textContent = s == null ? "" : String(s);
  return d.innerHTML;
}

async function getJson(url) {
  const r = await fetch(url, { credentials: "same-origin" });
  if (!r.ok) throw new Error(url + " " + r.status);
  return r.json();
}

function setAuthBadge(auth) {
  const el = document.getElementById("auth-badge");
  el.textContent = "auth=" + auth;
  el.className = "badge " + (auth === "session" ? "session" : "mesh");
}

async function refreshVitals() {
  try {
    const data = await getJson("/api/vitals");
    const v = data.vitals || {};
    const t = v.thermal || {};
    const m = v.mounts || {};
    const lines = [
      "temp_c=" + (t.temp_c ?? "?"),
      "throttled=" + (t.throttled_hex ?? "?"),
      "ada_data_ok=" + (m.ada_data_ok ?? "?"),
      "urgent=" + JSON.stringify(data.urgent_faults || []),
      "probe_errors=" + (v.probe_errors || []).length,
    ];
    if (v.disks) {
      for (const d of v.disks) {
        lines.push(
          "disk " + d.label + " avail=" + d.avail_bytes + " @" + d.mount
        );
      }
    }
    document.getElementById("vitals").textContent = lines.join("\n");
  } catch (e) {
    document.getElementById("vitals").textContent = String(e);
  }
}

async function refreshLifecycle() {
  try {
    const data = await getJson("/api/lifecycle");
    const lines = [
      "born_at=" + (data.born_at ?? "n/a"),
      "last_wake=" + JSON.stringify(data.last_wake),
      "last_fault=" + JSON.stringify(data.last_fault),
      "last_dream_at=" + (data.last_dream_at ?? "n/a"),
      "last_dream_status=" + (data.last_dream_status ?? "n/a"),
      "push=" + (data.push ?? "skipped"),
    ];
    document.getElementById("lifecycle").textContent = lines.join("\n");
  } catch (e) {
    document.getElementById("lifecycle").textContent = String(e);
  }
}

async function refreshMode() {
  try {
    const data = await getJson("/api/mode");
    setAuthBadge(data.auth || "mesh");
    if (data.mode) {
      document.getElementById("mode-select").value = data.mode;
    }
    document.getElementById("mode-detail").textContent = JSON.stringify(
      {
        mode: data.mode,
        auth: data.auth,
        agent_armed: data.agent_armed,
        tailscale_user: data.tailscale_user,
        last_denials: data.last_denials,
      },
      null,
      2
    );
  } catch (e) {
    document.getElementById("mode-detail").textContent = String(e);
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

function appendStreamHtml(html) {
  const root = document.getElementById("stream");
  const div = document.createElement("div");
  div.innerHTML = html;
  while (div.firstChild) root.appendChild(div.firstChild);
  root.scrollTop = root.scrollHeight;
}

function handleSseEvent(event, payload) {
  if (event === "token_delta") {
    appendStreamHtml(
      '<div class="bubble">' + esc(payload.text || "") + "</div>"
    );
  } else if (event === "tool_call_started") {
    const id = "tool-" + Date.now() + "-" + Math.random().toString(16).slice(2);
    appendStreamHtml(
      '<div class="tool-card" id="' +
        id +
        '"><strong>tool</strong> ' +
        esc(payload.tool) +
        "<br/><strong>args</strong> " +
        esc(JSON.stringify(payload.args || {})) +
        "</div>"
    );
    window.__lastToolCard = id;
  } else if (event === "tool_call_finished") {
    const el = document.getElementById(window.__lastToolCard || "");
    if (el) {
      el.classList.add(payload.ok ? "ok" : "fail");
      el.insertAdjacentHTML(
        "beforeend",
        "<br/><strong>ok</strong>=" +
          esc(String(payload.ok)) +
          " <strong>receipt</strong>=" +
          esc(payload.receipt_id || "")
      );
    }
  } else if (event === "fault") {
    appendStreamHtml(
      '<div class="bubble" style="border-color:var(--deny)">' +
        esc(payload.message || payload.error || JSON.stringify(payload)) +
        "</div>"
    );
  } else if (event === "session_receipt_path") {
    document.getElementById("run-path").textContent = payload.path || "";
  } else if (event === "turn_done") {
    appendStreamHtml(
      '<div class="bubble" style="border-color:var(--muted);color:var(--muted)">stop=' +
        esc(payload.stop_reason || "") +
        " steps=" +
        esc(String(payload.steps ?? "")) +
        "</div>"
    );
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
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify({ message, mode }),
    });
    if (resp.status === 401) {
      const err = await resp.json();
      appendStreamHtml(
        '<div class="bubble" style="border-color:var(--deny)">' +
          esc(err.message || "session required for Agent") +
          "</div>"
      );
      await refreshMode();
      return;
    }
    if (!resp.ok || !resp.body) {
      appendStreamHtml(
        '<div class="bubble" style="border-color:var(--deny)">chat HTTP ' +
          esc(String(resp.status)) +
          "</div>"
      );
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

document.getElementById("chat-form").addEventListener("submit", (ev) => {
  ev.preventDefault();
  const input = document.getElementById("chat-input");
  const msg = input.value.trim();
  if (!msg) return;
  const mode = document.getElementById("mode-select").value;
  appendStreamHtml('<div class="bubble" style="border-color:#5c6bc0">you: ' + esc(msg) + "</div>");
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

refreshVitals();
refreshLifecycle();
refreshMode();
refreshTail();
setInterval(refreshVitals, 3000);
setInterval(refreshLifecycle, 10000);
setInterval(refreshTail, 2000);
setInterval(refreshMode, 5000);
