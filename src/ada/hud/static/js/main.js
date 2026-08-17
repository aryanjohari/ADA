/** ADA HUD entry — wire modules once (M13/M14 packaged surface). */

import {
  refreshMode,
  refreshTail,
  startBodyPolls,
  wireBody,
} from "./body.js";
import { wireComposerChips } from "./composer_chips.js";
import { wireModeDial } from "./mode.js";
import { wireSession } from "./session.js";
import { wireChat } from "./stream.js";
import { startTodayPoll, refreshToday } from "./today.js";
import { wireXray, xrayList } from "./xray.js";

wireSession({ refreshMode });
wireComposerChips();
wireModeDial();
wireChat({
  refreshTail: async () => {
    await refreshTail();
    await refreshToday();
  },
  refreshMode,
});
wireXray();
wireBody({
  onXrayShow: () => {
    xrayList();
  },
  onShelfShow: async () => {
    const { fetchToday } = await import("./api.js");
    const { esc } = await import("./util.js");
    const list = document.getElementById("shelf-list");
    const empty = document.getElementById("shelf-empty");
    if (!list) return;
    let data;
    try {
      data = await fetchToday();
    } catch {
      list.innerHTML = "";
      if (empty) empty.hidden = false;
      return;
    }
    const arts = data.artifacts || [];
    if (!arts.length) {
      list.innerHTML = "";
      if (empty) empty.hidden = false;
      return;
    }
    if (empty) empty.hidden = true;
    list.innerHTML = arts
      .map((a) => {
        const path = a.path || a.rel || "";
        return (
          '<li class="shelf-item">' +
          '<button type="button" class="ghost shelf-open" data-path="' +
          esc(path) +
          '">' +
          esc(a.name || path) +
          "</button>" +
          '<span class="meta">' +
          esc(a.mtime_iso || "") +
          "</span></li>"
        );
      })
      .join("");
    list.querySelectorAll(".shelf-open").forEach((btn) => {
      btn.addEventListener("click", () => {
        const full = btn.getAttribute("data-path") || "";
        const rel = full.replace(/^artifacts\//, "");
        const rootBtn = document.querySelector('.root-btn[data-root="artifacts"]');
        const shelfTab = document.querySelector('[data-body-tab="xray"]');
        if (shelfTab) shelfTab.click();
        if (rootBtn) rootBtn.click();
        // Best-effort: navigate x-ray to parent dir of file.
        import("./xray.js").then((mod) => {
          const parts = rel.split("/");
          const dir = parts.length > 1 ? parts.slice(0, -1).join("/") : "";
          if (typeof mod.xrayList === "function") {
            mod.xrayList("artifacts", dir);
          }
        });
      });
    });
  },
});
startBodyPolls();
startTodayPoll();
