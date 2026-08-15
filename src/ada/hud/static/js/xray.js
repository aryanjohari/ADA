/** Read-only ADA x-ray (Body drawer). */

import { esc, getJson } from "./util.js";

const xrayState = {
  root: "memory",
  path: "",
  previewMode: "rendered",
  content: "",
  kind: "",
  name: "",
};

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

export async function xrayList() {
  const list = document.getElementById("xray-list");
  const pathEl = document.getElementById("xray-path");
  if (!list || !pathEl) return;
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
  if (
    (/\/cites\/c_.*\.md$/.test(p) || /\/cites\//.test(p)) &&
    p.endsWith(".md")
  )
    return "cite";
  if (p.includes("/facts/") && (p.endsWith(".yaml") || p.endsWith(".yml")))
    return "fact";
  if (p.endsWith(".jsonl") || p.includes("/runs/")) return "jsonl";
  if (p.endsWith(".md")) return "md";
  if ((contentType || "").includes("json")) return "json";
  return "text";
}

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
    const l = esc(line);
    if (/^###\s+/.test(line)) {
      out.push(
        '<div class="md-h3">' + esc(line.replace(/^###\s+/, "")) + "</div>"
      );
      continue;
    }
    if (/^##\s+/.test(line)) {
      out.push(
        '<div class="md-h2">' + esc(line.replace(/^##\s+/, "")) + "</div>"
      );
      continue;
    }
    if (/^#\s+/.test(line)) {
      out.push(
        '<div class="md-h1">' + esc(line.replace(/^#\s+/, "")) + "</div>"
      );
      continue;
    }
    if (/^\s*[-*]\s+/.test(line)) {
      out.push(
        "<ul><li>" +
          inlineMd(esc(line.replace(/^\s*[-*]\s+/, ""))) +
          "</li></ul>"
      );
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
  const m = String(text || "").match(
    /^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$/
  );
  if (!m) return { meta: "", body: text };
  return { meta: m[1], body: m[2] };
}

function renderPreview() {
  const el = document.getElementById("xray-preview");
  if (!el) return;
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
  el.innerHTML = "<pre>" + esc(raw) + "</pre>";
}

async function xrayRead(relPath) {
  const fileEl = document.getElementById("xray-file");
  if (fileEl) fileEl.textContent = xrayState.root + "/" + relPath;
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

export function wireXray() {
  document.querySelectorAll(".root-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document
        .querySelectorAll(".root-btn")
        .forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      xrayState.root = btn.getAttribute("data-root");
      xrayState.path = "";
      xrayState.content = "";
      const preview = document.getElementById("xray-preview");
      if (preview) {
        preview.textContent = "Choose a file under an allowlisted root.";
        preview.className = "xray-preview muted-empty";
      }
      xrayList();
    });
  });
  const rendered = document.getElementById("preview-rendered");
  const rawBtn = document.getElementById("preview-raw");
  if (rendered) {
    rendered.addEventListener("click", () => {
      xrayState.previewMode = "rendered";
      rendered.classList.add("active");
      rawBtn?.classList.remove("active");
      if (xrayState.content) renderPreview();
    });
  }
  if (rawBtn) {
    rawBtn.addEventListener("click", () => {
      xrayState.previewMode = "raw";
      rawBtn.classList.add("active");
      rendered?.classList.remove("active");
      if (xrayState.content) renderPreview();
    });
  }
}
