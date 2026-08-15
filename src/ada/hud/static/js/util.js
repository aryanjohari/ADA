/** Shared helpers — XSS escape + fetch. */

export function esc(s) {
  const d = document.createElement("div");
  d.textContent = s == null ? "" : String(s);
  return d.innerHTML;
}

export async function getJson(url) {
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

export function bytesGiB(n) {
  if (n == null || Number.isNaN(Number(n))) return "—";
  return (Number(n) / 1073741824).toFixed(1) + " GiB";
}

export function truncJson(obj, max) {
  const s = JSON.stringify(obj ?? {});
  if (s.length <= max) return s;
  return s.slice(0, max - 1) + "…";
}
