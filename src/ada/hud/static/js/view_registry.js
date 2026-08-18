/** Deterministic panel registry for HUD view_open events. */

import { openBody, refreshLifeDay, showBodyTab } from "./body.js";
import { currentFace } from "./face.js";
import { esc } from "./util.js";

function mealRows(meals) {
  if (!Array.isArray(meals) || !meals.length) {
    return '<p class="view-panel-empty">No meal rows logged.</p>';
  }
  return (
    '<ul class="view-panel-meals">' +
    meals
      .map((meal) => {
        const slot = meal.meal_slot || "meal";
        const foods = Array.isArray(meal.foods) && meal.foods.length
          ? meal.foods.join(", ")
          : "logged meal";
        const meta = [];
        if (meal.kcal != null) meta.push(String(meal.kcal) + " kcal");
        if (meal.protein_g != null) meta.push(String(meal.protein_g) + "g P");
        return (
          '<li class="view-panel-meal">' +
          '<div class="view-panel-meal-head"><span class="view-panel-label">' +
          esc(slot) +
          "</span><span class=\"view-panel-meta\">" +
          esc(meta.join(" · ")) +
          "</span></div>" +
          '<div class="view-panel-foods">' +
          esc(foods) +
          "</div></li>"
        );
      })
      .join("") +
    "</ul>"
  );
}

function renderNutritionDay(data) {
  const totals = (data && data.totals) || {};
  const meals = Array.isArray(data && data.meals) ? data.meals : [];
  const empty = !Object.keys(totals).length && !meals.length;
  return (
    '<section class="view-panel" data-panel-kind="nutrition_day">' +
    '<div class="view-panel-head"><div><p class="view-panel-kicker">view</p><h2>Nutrition day</h2></div>' +
    '<button type="button" class="ghost" data-view-open-body="nutrition">Body</button></div>' +
    (empty
      ? '<p class="view-panel-empty">No nutrition day data yet.</p>'
      : '<dl class="view-panel-stats">' +
          '<div><dt>Date</dt><dd>' +
          esc(data.date || "—") +
          '</dd></div><div><dt>kcal</dt><dd>' +
          esc(totals.energy_kcal != null ? String(totals.energy_kcal) : "—") +
          '</dd></div><div><dt>Protein</dt><dd>' +
          esc(totals.protein_g != null ? String(totals.protein_g) + "g" : "—") +
          "</dd></div></dl>") +
    (data && data.honest_partial
      ? '<p class="view-panel-note">honest_partial — partial day, no invented totals.</p>'
      : "") +
    mealRows(meals) +
    "</section>"
  );
}

const REGISTRY = {
  nutrition_day: renderNutritionDay,
};

function bindPanelActions(root, payload) {
  root.querySelectorAll("[data-view-open-body]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      openBody();
      showBodyTab("life");
      await refreshLifeDay(payload.data && payload.data.date ? payload.data.date : null);
    });
  });
}

export async function applyViewOpen(payload) {
  const panelKind = payload && payload.panel_kind;
  const render = REGISTRY[panelKind];
  if (!render) return false;
  const face = currentFace();
  if (face === "phone") return false;
  const slot = document.getElementById("view-slot");
  if (!slot) return false;
  slot.innerHTML = render(payload.data || {});
  slot.dataset.panelKind = panelKind;
  bindPanelActions(slot, payload);
  return true;
}
