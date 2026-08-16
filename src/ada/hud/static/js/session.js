/** Session welcome + login/logout chrome (M17). */

import { postLogin, postLogout } from "./api.js";
import { esc } from "./util.js";

export const sessionState = {
  auth: "mesh",
  agentArmed: false,
  tailscaleUser: null,
  mode: "observe",
};

/**
 * @param {object} data — /api/mode payload
 */
export function applyModePayload(data) {
  sessionState.auth = data.auth || "mesh";
  sessionState.agentArmed = !!data.agent_armed;
  sessionState.tailscaleUser = data.tailscale_user || null;
  if (data.mode) sessionState.mode = data.mode;

  const crumb = document.getElementById("session-crumb");
  if (crumb) {
    crumb.textContent = sessionState.agentArmed ? "session" : "mesh";
    crumb.classList.toggle("armed", sessionState.agentArmed);
  }

  const welcome = document.getElementById("welcome-line");
  if (welcome) {
    const ts = sessionState.tailscaleUser
      ? " · ts=" + sessionState.tailscaleUser
      : "";
    if (sessionState.agentArmed) {
      welcome.textContent = "session armed · it’s you" + ts;
      welcome.classList.add("armed");
    } else {
      welcome.textContent = "mesh · Observe free · login for Plan/Agent" + ts;
      welcome.classList.remove("armed");
    }
  }

  const loginForm = document.getElementById("login-form");
  const sessionMenu = document.getElementById("session-menu");
  if (sessionState.agentArmed) {
    if (loginForm) loginForm.classList.add("hidden");
    if (sessionMenu) {
      sessionMenu.hidden = false;
      sessionMenu.open = false;
    }
  } else {
    if (sessionMenu) {
      sessionMenu.hidden = true;
      sessionMenu.open = false;
    }
    // Keep login hidden until Plan/Agent gate (requireSessionForMode).
  }

  // Chrome #mode-select is operator-owned (mode.js). Do not reset it from
  // GET /api/mode — that snaps Plan/Agent back to server last-session mode
  // after login or each chat refreshMode(). Body #mode-chips still show
  // server truth below. Logout alone forces Observe (wireSession).

  const chips = document.getElementById("mode-chips");
  if (chips) {
    chips.innerHTML =
      '<span class="chip">mode=' +
      esc(data.mode || "—") +
      "</span>" +
      '<span class="chip">auth=' +
      esc(data.auth || "—") +
      "</span>" +
      '<span class="chip">agent_armed=' +
      esc(String(sessionState.agentArmed)) +
      "</span>" +
      (sessionState.tailscaleUser
        ? '<span class="chip muted">ts=' +
          esc(sessionState.tailscaleUser) +
          "</span>"
        : "");
  }

  const denials = data.last_denials || [];
  const line = document.getElementById("denial-line");
  if (line) {
    if (denials.length) {
      const last = denials[denials.length - 1];
      line.textContent =
        typeof last === "string" ? last : JSON.stringify(last).slice(0, 160);
    } else {
      line.textContent = "";
    }
  }
}

export function requireSessionForMode(mode) {
  const m = (mode || "observe").toLowerCase();
  if (m === "observe") return true;
  if (sessionState.agentArmed) return true;
  const form = document.getElementById("login-form");
  const pw = document.getElementById("password");
  const msg = document.getElementById("auth-msg");
  if (form) form.classList.remove("hidden");
  if (msg) msg.textContent = m + " requires session login";
  if (pw) pw.focus();
  return false;
}

export function wireSession({ refreshMode }) {
  document.getElementById("login-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const password = document.getElementById("password").value;
    const msg = document.getElementById("auth-msg");
    msg.textContent = "";
    const { ok, data } = await postLogin(password);
    if (!ok) {
      msg.textContent = data.message || "login failed";
      return;
    }
    document.getElementById("password").value = "";
    msg.textContent = "session armed";
    await refreshMode();
  });

  document.getElementById("logout-btn").addEventListener("click", async () => {
    await postLogout();
    document.getElementById("auth-msg").textContent = "logged out";
    const modeSelect = document.getElementById("mode-select");
    if (modeSelect) modeSelect.value = "observe";
    sessionState.mode = "observe";
    const form = document.getElementById("login-form");
    if (form) form.classList.add("hidden");
    await refreshMode();
  });
}
