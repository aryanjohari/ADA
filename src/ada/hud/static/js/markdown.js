/** Tiny safe markdown allowlist shared by HUD surfaces. */

import { esc } from "./util.js";

function inlineMd(escaped) {
  return escaped
    .replace(/`([^`]+)`/g, '<code class="md-code">$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
}

export function renderMarkdownSafe(src, opts = {}) {
  const options = {
    headings: true,
  };
  if (opts && Object.prototype.hasOwnProperty.call(opts, "headings")) {
    options.headings = opts.headings;
  }
  const lines = String(src || "").split(/\r?\n/);
  const out = [];
  let inCode = false;
  let codeBuf = [];
  let listItems = [];
  let para = [];

  function flushParagraph() {
    if (!para.length) return;
    out.push("<p>" + inlineMd(esc(para.join(" "))) + "</p>");
    para = [];
  }

  function flushList() {
    if (!listItems.length) return;
    out.push(
      "<ul>" +
        listItems
          .map((item) => "<li>" + inlineMd(esc(item)) + "</li>")
          .join("") +
        "</ul>"
    );
    listItems = [];
  }

  function flushCode() {
    if (!inCode) return;
    out.push("<pre><code>" + esc(codeBuf.join("\n")) + "</code></pre>");
    codeBuf = [];
    inCode = false;
  }

  for (const rawLine of lines) {
    const line = String(rawLine || "");
    if (line.trim().startsWith("```")) {
      flushParagraph();
      flushList();
      if (inCode) {
        flushCode();
      } else {
        inCode = true;
        codeBuf = [];
      }
      continue;
    }
    if (inCode) {
      codeBuf.push(line);
      continue;
    }
    if (/^\s*[-*]\s+/.test(line)) {
      flushParagraph();
      listItems.push(line.replace(/^\s*[-*]\s+/, ""));
      continue;
    }
    if (!line.trim()) {
      flushParagraph();
      flushList();
      continue;
    }
    if (options.headings && /^###\s+/.test(line)) {
      flushParagraph();
      flushList();
      out.push('<div class="md-h3">' + esc(line.replace(/^###\s+/, "")) + "</div>");
      continue;
    }
    if (options.headings && /^##\s+/.test(line)) {
      flushParagraph();
      flushList();
      out.push('<div class="md-h2">' + esc(line.replace(/^##\s+/, "")) + "</div>");
      continue;
    }
    if (options.headings && /^#\s+/.test(line)) {
      flushParagraph();
      flushList();
      out.push('<div class="md-h1">' + esc(line.replace(/^#\s+/, "")) + "</div>");
      continue;
    }
    flushList();
    para.push(line.trim());
  }

  flushParagraph();
  flushList();
  flushCode();
  return out.join("\n");
}
