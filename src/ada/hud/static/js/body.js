/** Body drawer — vitals, lifecycle, audit polls + tab switch. */

import {
  fetchDoctor,
  fetchLifeDay,
  fetchLifecycle,
  fetchMode,
  fetchRunTail,
  fetchVitals,
} from "./api.js";
import { applyModePayload } from "./session.js";
import { bytesGiB, esc, truncJson } from "./util.js";

function metricCard(label, value, sub) {
  return (
    '<div class="metric-card"><div class="label">' +
    esc(label) +
    '</div><div class="value">' +
    esc(value) +
    "</div>" +
    (sub ? '<div class="sub">' + esc(sub) + "</div>" : "") +
    "</div>"
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

  const cardsEl = document.getElementById("vitals-cards");
  if (!cardsEl) return;

  cardsEl.innerHTML =
    metricCard("Temp", t.temp_c != null ? t.temp_c + "°C" : "—", t.temp_source || "") +
    metricCard("Throttle", t.throttled_hex || "—", "") +
    metricCard("Cores / arch", cores, extras.os_pretty || "") +
    metricCard(
      "Load",
      load.load1 != null ? String(load.load1) : "—",
      load.load5 != null ? "5=" + load.load5 + " · 15=" + load.load15 : ""
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
    badge.textContent = "doctor: urgent=" + urgentN + " · probes=" + probeN;
    badge.className = "doctor-badge" + (urgentN ? " urgent" : "");
  }

  document.getElementById("vitals-meta").textContent =
    "ts=" +
    (v.ts || "—") +
    " · probe_errors=" +
    probeN +
    (urgentN ? " · urgent=" + urgent.join(",") : "");
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

function renderNutritionSummary(day) {
  const empty =
    '<p class="meta life-empty">No nutrition day data yet.</p>';
  if (!day || day.ok === false) return empty;
  const nutrition = day.nutrition || day;
  const totals = nutrition.totals || {};
  const meals = Array.isArray(nutrition.meals) ? nutrition.meals : [];
  if (!Object.keys(totals).length && !meals.length) return empty;
  const kcal = totals.energy_kcal != null ? String(totals.energy_kcal) : "—";
  const protein = totals.protein_g != null ? String(totals.protein_g) : "—";
  const partial = nutrition.honest_partial
    ? '<p class="meta life-meta">honest_partial — partial day, no invented totals.</p>'
    : "";
  const mealRows = meals.length
    ? '<ul class="nutrition-meals">' +
      meals
        .map((meal) => {
          const slot = meal.meal_slot || "meal";
          const foods = Array.isArray(meal.foods) && meal.foods.length
            ? meal.foods.join(", ")
            : "logged meal";
          const metaBits = [];
          if (meal.kcal != null) metaBits.push(String(meal.kcal) + " kcal");
          if (meal.protein_g != null) metaBits.push(String(meal.protein_g) + "g P");
          return (
            '<li class="nutrition-meal">' +
            '<div class="nutrition-meal-head"><span class="nutrition-meal-slot">' +
            esc(slot) +
            "</span>" +
            '<span class="nutrition-meal-meta">' +
            esc(metaBits.join(" · ")) +
            "</span></div>" +
            '<div class="nutrition-meal-foods">' +
            esc(foods) +
            "</div></li>"
          );
        })
        .join("") +
      "</ul>"
    : '<p class="meta life-meta">No meal rows logged.</p>';
  return (
    '<section class="life-sheet" id="life-sheet-nutrition">' +
    '<div class="life-sheet-head"><h3>Nutrition day</h3>' +
    '<button type="button" class="ghost life-refresh" data-life-refresh="nutrition">Refresh</button></div>' +
    '<div class="life-summary-grid">' +
    metricCard("Date", nutrition.date || "—", "") +
    metricCard("kcal", kcal, "") +
    metricCard("Protein", protein, "grams") +
    "</div>" +
    partial +
    mealRows +
    "</section>"
  );
}

export async function refreshLifeDay(date = null) {
  const root = document.getElementById("life-nutrition");
  if (!root) return;
  try {
    const day = await fetchLifeDay(date);
    root.innerHTML = renderNutritionSummary(day);
    root.querySelectorAll("[data-life-refresh='nutrition']").forEach((btn) => {
      btn.addEventListener("click", () => {
        refreshLifeDay(date);
      });
    });
  } catch (e) {
    root.innerHTML = '<p class="meta life-empty">' + esc(String(e)) + "</p>";
  }
}

export async function refreshVitals() {
  try {
    const [data, doctor] = await Promise.all([
      fetchVitals(),
      fetchDoctor().catch(() => null),
    ]);
    renderVitals(data, doctor);
  } catch (e) {
    const el = document.getElementById("vitals-cards");
    if (el) el.textContent = String(e);
    const badge = document.getElementById("doctor-badge");
    if (badge) badge.textContent = "doctor: error";
  }
}

export async function refreshLifecycle() {
  const root = document.getElementById("lifecycle");
  if (!root) return;
  try {
    const data = await fetchLifecycle();
    const rows = [
      ["born", data.born_at || "n/a"],
      ["wake", shortWake(data.last_wake)],
      ["fault", shortWake(data.last_fault)],
      [
        "dream",
        (data.last_dream_status || "n/a") + " · " + (data.last_dream_at || "n/a"),
      ],
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

export async function refreshMode() {
  try {
    const data = await fetchMode();
    applyModePayload(data);
  } catch (e) {
    const chips = document.getElementById("mode-chips");
    if (chips) chips.textContent = String(e);
  }
}

export async function refreshTail() {
  try {
    const data = await fetchRunTail(80);
    const pathEl = document.getElementById("run-path");
    const raw = document.getElementById("raw-tail");
    if (pathEl) pathEl.textContent = data.path || "(no run yet)";
    if (raw) {
      const lines = (data.records || []).map((r) => JSON.stringify(r));
      raw.textContent = lines.join("\n");
    }
  } catch (e) {
    const raw = document.getElementById("raw-tail");
    if (raw) raw.textContent = String(e);
  }
}

function setBodyTab(name) {
  document.querySelectorAll("[data-body-tab]").forEach((btn) => {
    btn.classList.toggle("active", btn.getAttribute("data-body-tab") === name);
  });
  ["vitals", "life", "shelf", "xray", "audit"].forEach((id) => {
    const panel = document.getElementById("body-panel-" + id);
    if (!panel) return;
    const on = id === name;
    panel.hidden = !on;
    panel.classList.toggle("active", on);
  });
}

export function showBodyTab(name) {
  setBodyTab(name);
  if (name === "life") refreshLifeDay();
  if (name === "audit") refreshTail();
}

export function openBody() {
  const dlg = document.getElementById("body-drawer");
  if (dlg && typeof dlg.showModal === "function") {
    if (!dlg.open) dlg.showModal();
  }
}

export function closeBody() {
  const dlg = document.getElementById("body-drawer");
  if (dlg && dlg.open) dlg.close();
}

export function wireBody({ onXrayShow, onShelfShow } = {}) {
  const dlg = document.getElementById("body-drawer");
  document.getElementById("body-open").addEventListener("click", () => {
    openBody();
    refreshVitals();
    refreshLifecycle();
    refreshLifeDay();
    refreshMode();
    refreshTail();
  });
  document.getElementById("body-close").addEventListener("click", closeBody);
  if (dlg) {
    dlg.addEventListener("click", (ev) => {
      if (ev.target === dlg) closeBody();
    });
  }
  document.querySelectorAll("[data-body-tab]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const name = btn.getAttribute("data-body-tab");
      setBodyTab(name);
      if (name === "life") refreshLifeDay();
      if (name === "xray" && onXrayShow) onXrayShow();
      if (name === "shelf" && onShelfShow) onShelfShow();
      if (name === "audit") refreshTail();
    });
  });
}

export function startBodyPolls() {
  refreshVitals();
  refreshLifecycle();
  refreshLifeDay();
  refreshMode();
  refreshTail();
  setInterval(refreshVitals, 3000);
  setInterval(refreshLifecycle, 10000);
  setInterval(refreshLifeDay, 45000);
  setInterval(refreshTail, 2000);
  setInterval(refreshMode, 5000);
}
