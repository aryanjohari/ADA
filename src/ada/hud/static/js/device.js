/** Thin device registry client — names + cookie/localStorage id (M19b v1.6). */

import { currentFace } from "./face.js";

const STORAGE_ID = "ada_hud_device";
const STORAGE_PROMPTED = "ada_hud_device_prompted";

function readCookie(name) {
  const parts = ("; " + document.cookie).split("; " + name + "=");
  if (parts.length < 2) return null;
  return decodeURIComponent(parts.pop().split(";").shift() || "") || null;
}

function uuidV4() {
  if (crypto.randomUUID) return crypto.randomUUID();
  const b = new Uint8Array(16);
  crypto.getRandomValues(b);
  b[6] = (b[6] & 0x0f) | 0x40;
  b[8] = (b[8] & 0x3f) | 0x80;
  const hex = [...b].map((n) => n.toString(16).padStart(2, "0")).join("");
  return (
    hex.slice(0, 8) +
    "-" +
    hex.slice(8, 12) +
    "-" +
    hex.slice(12, 16) +
    "-" +
    hex.slice(16, 20) +
    "-" +
    hex.slice(20)
  );
}

export function getDeviceId() {
  const cookie = readCookie("ada_hud_device");
  if (cookie) {
    try {
      localStorage.setItem(STORAGE_ID, cookie);
    } catch (_) {
      /* private mode */
    }
    return cookie;
  }
  try {
    let id = localStorage.getItem(STORAGE_ID);
    if (!id) {
      id = uuidV4();
      localStorage.setItem(STORAGE_ID, id);
    }
    return id;
  } catch (_) {
    return uuidV4();
  }
}

export async function fetchDevice() {
  const r = await fetch("/api/device", { credentials: "same-origin" });
  const data = await r.json().catch(() => ({}));
  if (data.device_id) {
    try {
      localStorage.setItem(STORAGE_ID, data.device_id);
    } catch (_) {
      /* private mode */
    }
  }
  return data;
}

export async function postDevice(payload) {
  const r = await fetch("/api/device", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload || {}),
  });
  const data = await r.json().catch(() => ({}));
  if (data.device_id) {
    try {
      localStorage.setItem(STORAGE_ID, data.device_id);
    } catch (_) {
      /* private mode */
    }
  }
  return data;
}

function markPrompted(id) {
  try {
    localStorage.setItem(STORAGE_PROMPTED, id);
  } catch (_) {
    /* private mode */
  }
}

function alreadyPrompted(id) {
  try {
    return localStorage.getItem(STORAGE_PROMPTED) === id;
  } catch (_) {
    return true;
  }
}

async function closePrompt(dialog, { name, id }) {
  if (name) {
    await postDevice({
      name,
      device_id: id,
      face: currentFace(),
    });
  }
  markPrompted(id);
  if (dialog && dialog.open) dialog.close();
}

export async function wireDevice() {
  const localId = getDeviceId();
  let info = {};
  try {
    info = await fetchDevice();
  } catch (_) {
    try {
      info = await postDevice({
        device_id: localId,
        face: currentFace(),
      });
    } catch (__) {
      info = { device_id: localId };
    }
  }
  const id = info.device_id || localId;
  if (info.name || alreadyPrompted(id)) return;

  const dialog = document.getElementById("device-name-dialog");
  const form = document.getElementById("device-name-form");
  const input = document.getElementById("device-name-input");
  const skip = document.getElementById("device-name-skip");
  if (!dialog || !form) {
    await postDevice({ device_id: id, face: currentFace() });
    markPrompted(id);
    return;
  }

  skip?.addEventListener("click", async () => {
    await closePrompt(dialog, { name: null, id });
  });
  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const name = (input && input.value.trim()) || "";
    await closePrompt(dialog, { name, id });
  });
  try {
    dialog.showModal();
  } catch (_) {
    dialog.setAttribute("open", "");
  }
}
