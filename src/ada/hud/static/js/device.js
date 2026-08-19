/** Thin device registry client — names + cookie/localStorage id (M19b v1.6 / M20 3a). */

import { applyFace, currentFace, hintFace, urlFace } from "./face.js";

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

function selectedFace(form) {
  const checked = form && form.querySelector('input[name="device-face"]:checked');
  return (checked && checked.value) || currentFace() || hintFace();
}

function hintFirstOpenFace() {
  return urlFace() || currentFace() || hintFace();
}

function applyConfirmedFace(face) {
  if (urlFace()) return;
  applyFace(face);
}

function setFaceRadios(form, face) {
  const radios = form.querySelectorAll('input[name="device-face"]');
  let matched = false;
  radios.forEach((el) => {
    el.checked = el.value === face;
    if (el.checked) matched = true;
  });
  if (!matched && radios[0]) radios[0].checked = true;
}

async function stampWindow(id, { name, face }) {
  const payload = { device_id: id, face };
  if (name) payload.name = name;
  await postDevice(payload);
  applyConfirmedFace(face);
  markPrompted(id);
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
    await stampWindow(id, { name: null, face: currentFace() });
    return;
  }

  setFaceRadios(form, hintFirstOpenFace());

  let finishing = false;
  const finish = async ({ name }) => {
    if (finishing) return;
    finishing = true;
    const face = selectedFace(form);
    try {
      await stampWindow(id, { name, face });
    } catch (_) {
      markPrompted(id);
      applyConfirmedFace(face);
    }
    if (dialog.open) dialog.close();
  };

  skip?.addEventListener("click", () => {
    finish({ name: null });
  });
  dialog.addEventListener("cancel", (ev) => {
    ev.preventDefault();
    finish({ name: null });
  });
  form.addEventListener("submit", (ev) => {
    ev.preventDefault();
    const name = (input && input.value.trim()) || "";
    finish({ name });
  });
  try {
    dialog.showModal();
  } catch (_) {
    dialog.setAttribute("open", "");
  }
}
