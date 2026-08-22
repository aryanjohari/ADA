/** Face selection — phone | mac | display (M19b v1.6). */

const FACES = ["phone", "mac", "display"];
const ALIASES = { "mac-chat": "mac", "mac-companion": "mac" };
const STORAGE_KEY = "ada_hud_face";

export function normalizeFace(raw) {
  if (!raw) return null;
  const v = String(raw).toLowerCase().trim();
  if (ALIASES[v]) return ALIASES[v];
  if (FACES.includes(v)) return v;
  return null;
}

export function hintFace() {
  try {
    const fullscreen = window.matchMedia("(display-mode: fullscreen)").matches;
    const wide = window.matchMedia("(min-width: 900px)").matches;
    if (fullscreen && wide) return "display";
  } catch (_) {
    /* matchMedia missing */
  }
  const mobile =
    (navigator.userAgentData && navigator.userAgentData.mobile) ||
    /Mobi|Android|iPhone/i.test(navigator.userAgent || "");
  if (mobile || window.innerWidth < 640) return "phone";
  return "mac";
}

export function urlFace() {
  return normalizeFace(new URLSearchParams(location.search).get("face"));
}

export function currentFace() {
  return (
    urlFace() ||
    normalizeFace(document.documentElement.dataset.face) ||
    hintFace()
  );
}

function persistFace(face) {
  try {
    sessionStorage.setItem(STORAGE_KEY, face);
  } catch (_) {
    /* private mode */
  }
  try {
    localStorage.setItem(STORAGE_KEY, face);
  } catch (_) {
    /* private mode */
  }
}

function notifyFace(face) {
  document.documentElement.dispatchEvent(
    new CustomEvent("ada-face", { detail: { face } })
  );
}

export function applyFace(face) {
  const f = normalizeFace(face) || "mac";
  document.documentElement.dataset.face = f;
  persistFace(f);
  const sel = document.getElementById("face-select");
  if (sel && sel.value !== f) sel.value = f;
  notifyFace(f);
  return f;
}

export function resolveFace() {
  const fromQ = urlFace();
  if (fromQ) return fromQ;
  try {
    const session = normalizeFace(sessionStorage.getItem(STORAGE_KEY));
    if (session) return session;
  } catch (_) {
    /* private mode */
  }
  try {
    const lasting = normalizeFace(localStorage.getItem(STORAGE_KEY));
    if (lasting) return lasting;
  } catch (_) {
    /* private mode */
  }
  return hintFace();
}

export function wireFace() {
  applyFace(resolveFace());
  const sel = document.getElementById("face-select");
  if (!sel) return;
  sel.addEventListener("change", () => {
    const f = applyFace(sel.value);
    try {
      const url = new URL(location.href);
      url.searchParams.set("face", f);
      history.replaceState(null, "", url);
    } catch (_) {
      /* ignore */
    }
  });
}
