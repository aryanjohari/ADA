# M14 — Agent Surface (access · session · Mac packaging · agent feel)

**Status:** module research card — **P0′/P1′ metal shipped** (2026-08-16). Chat-home + Body drawer + CSS pack + session chrome + Plan Accept + `/api/confirm` + SSE enrichment. Smart intent-routing research still later.  
**Date:** 2026-08-16 (v2 locks + implement)  
**Host:** `ada-pi5` (Raspberry Pi 5 Model B Rev 1.1, Debian trixie, ~8 GiB RAM)  
**Client:** Aryan’s Mac (`aryans-macbook-air` on same Tailnet — **METAL** 2026-08-16)  
**Branch:** `rewrite/v1-body`  
**Depends on:** [`M03_HUD.md`](./M03_HUD.md) (architecture authority — bind, Serve, auth stance, harness wiring), [`M13_HUD_UX.md`](./M13_HUD_UX.md) (presentation / IA / CSS pack / Body drawer — co-implement), [`M02_CHAT_HARNESS.md`](./M02_CHAT_HARNESS.md) (modes, stream events, gateway), [`M05_VOICE_PERSONALITY_CONTROL.md`](./M05_VOICE_PERSONALITY_CONTROL.md) (register + text-first; audio later), [`../02_CONSTITUTION.md`](../02_CONSTITUTION.md) §§3–4, 11, 15  

**Name justification:** **`M14_AGENT_SURFACE.md`**. M03 owns control-plane **truth**; M13 owns **chrome + Body HUD drawer + CSS pack**; M14 owns **getting there as Aryan**, **session feel (“it’s me”)**, **Mac packaging**, and **chat that behaves like an agent** (intent → ask/plan → accept → execute).

**Why not fold into M13:** access packaging, session welcome, Plan→accept productization, stack fork, and voice/wake/pretext tiering are not presentation-only. Cross-link both ways; **one implement chat ships M13 shell + M14 interaction together (P0+P1)**.

**METAL present (2026-08-16):** `src/ada/hud/` ASGI on `127.0.0.1:8787`; Serve → `https://ada-pi5.tailbc896a.ts.net`; M13 chat-first shell still shows organism as **peer column** (gap); Plan stub; session cookie; moss CSS vars exist but product still reads as ops site.

**OUT unless research-earned as FEASIBLE Tier A:** Funnel / public ingress; replacing cortex; ignoring receipts; consciousness cosplay; second agent loop in the client; secrets-to-cloud; Next-on-Pi.

---

## 1. Slice rule + won’t-chase

**Slice rule:** inventory metal access/session honestly → survey real agent surfaces + 2025–26 agent UX patterns → lock a **Mac-reachable agent surface** (fast open + “it’s me” + intent→plan→execute) that still treats M00–M12 / gateway as authority → decide stack fork from survey (no predetermined Next win) → tier voice/wake/pretext honestly → leave ≤7 OPEN + ordered implement-next. This card does **not** rewrite organs, Funnel the HUD, or ship a large UI rewrite unless OPEN locks say code P0.

**Won’t-chase**

| Out | Why |
|-----|-----|
| Funnel / public URL | **POLICY** — Tailscale Serve only |
| Second cortex / client-side agent loop | UI is `channel.web` (+ optional Mac shell) → existing M02 harness |
| Replacing gateway modes with UI-only “autonomy” | Dial **maps to** Observe/Plan/Agent; enforcement stays in gateway |
| Secrets / SSH / Tailscale auth in x-ray or client logs | Never-to-cloud / never in UI dumps |
| Consciousness / holographic “she’s awake” theater | **FANFICTION** — presence ≠ soul |
| Forcing Next.js on the Pi because “apps feel cool” | **FEASIBLE** fail — no Node on host; RAM/ops tax |
| Always-listen wake as P0 | **POLICY** + **FEASIBLE** — Tier C until earned |

```text
  Aryan Mac (Tailscale ON)
        |
        | Dock / ada-open script
        | HTTPS MagicDNS Serve
        v
  127.0.0.1:8787  ada.hud  (channel.web)
        |
        +-- MAIN: ADA chat (session welcome + mode dial + stream)
        +-- plan ask/accept + agent confirm → gateway {tool,args}
        +-- [Body] button → drawer: vitals / lifecycle / x-ray / audit
        x organism as peer home column
        x Funnel  x second brain  x secrets trees
```

---

## 1b. Operator IA locks (2026-08-16) — packaged agent, not ops dashboard

| Lock | Decision | Tag |
|------|----------|-----|
| **Home** | First viewport = **complete ADA chat** (brand, session, mode dial, stream, composer) | **LOCKED** |
| **Body HUD** | Organism / vitals / lifecycle / x-ray / audit live behind a **Body** (or HUD) **button → panel/drawer** — not the main view | **LOCKED** |
| **Observe** | Still a **mode** (read-only gateway). It is **not** a separate “Observe home screen.” Mesh Observe can chat without password; Body drawer still readable | **LOCKED** |
| **Login** | Agent/Plan need session; after login, stay on chat — don’t dump into vitals | **LOCKED** |
| **CSS pack** | Thin **fixed palette + type + density** polish in **P0** (extend M13 moss vars) so Dock install feels like an app | **LOCKED** |
| **Ask → accept** | Plan and Agent get **proper ask / accept / confirm** surfaces in **P1** (not mode dropdown alone) | **LOCKED** |
| **Slice size** | **P0+P1 thin slice is enough** for packaged feel — no Next rewrite, no menu-bar companion required | **LOCKED** |
| **Stack** | Stay Python ASGI + static through this slice | **LOCKED** |

---

## 2. Lens tags

| Tag | What it means here |
|-----|--------------------|
| **FANFICTION** | Always-watching face, cinematic presence, “she knows it’s you” without metal identity — deferred or refused |
| **EVIDENCE** | Real products (Cursor/Claude/ChatGPT/OSS UIs); Tailscale Serve+PWA practice; agent UX pattern libraries 2025–26; Consent Integrity |
| **FEASIBLE** | Pi 5 8GB: keep thin Python ASGI; Mac may host heavier client; no Node on Pi today; voice STT/TTS cost on Mac first |
| **POLICY** | Tailscale-only control plane; Serve OK / Funnel NO; Agent writes need `auth.session`; gateway outside model; secrets never-to-cloud |
| **METAL** | Live `src/ada/hud/` + Serve URL + Mac on tailnet + Plan stub + session cookie + M13 chrome |

---

## 3. METAL inventory (2026-08-16)

### 3.1 Live reachability

| Check | Result | Tag |
|-------|--------|-----|
| Process | `ada hud serve --host 127.0.0.1 --port 8787` via `.venv` | **METAL** |
| Listen | `127.0.0.1:8787` only | **METAL** |
| Serve | `https://ada-pi5.tailbc896a.ts.net` → `http://127.0.0.1:8787` (tailnet only) | **METAL** |
| Funnel | Not used for this control plane | **POLICY** / **METAL** |
| `GET /` | HTTP 200 | **METAL** |
| Mac peer | `aryans-macbook-air` active on same Tailnet | **METAL** |
| RAM headroom | ~7.9 GiB total; ~6.7 GiB available at sample | **METAL** |
| Node on Pi | **absent** (`node` / `npm` not found) | **METAL** / **FEASIBLE** |

### 3.2 Package layout (access-relevant)

| Path | Role |
|------|------|
| `src/ada/hud/app.py` | FastAPI factory; static + Jinja |
| `src/ada/hud/auth.py` | Mesh vs session; `hud.env`; 7-day signed cookie `ada_hud_session`; soft `Tailscale-User-Login` |
| `src/ada/hud/routes_api.py` | `/api/login`, `/logout`, `/mode`, `/chat` (SSE), vitals/lifecycle/xray |
| `src/ada/hud/chat_service.py` | One `ChatSession`; `run_turn` only |
| `src/ada/hud/templates/index.html` | Chat-first shell; mode select; login form in chrome |
| `src/ada/hud/static/app.{js,css}` | Polls + SSE; tool cards; **no** confirm/HITL UI; **no** PWA manifest |
| `src/ada/tools/gateway.py` | Mode deny writes in Observe/Plan; `needs_confirm` outcomes exist deeper in memory tools |
| `src/ada/cortex/charter.py` | Plan = **stub** (“Propose only; read tools OK; no side-effect tools”) |

### 3.3 Auth posture (metal matches M03 / M13)

| Mode | Gate today |
|------|------------|
| `observe` | Tailnet + Serve + localhost — **no password** |
| `agent` / `plan` | Session cookie from `POST /api/login` vs `ADA_HUD_PASSWORD` + `ADA_HUD_SESSION_SECRET` in `secrets/hud.env` (never git) |
| Soft display | `Tailscale-User-Login` → `mode.tailscale_user` (**not** Agent authority) |
| Cookie | HttpOnly; `Secure` default true (Serve HTTPS); `SameSite=lax`; max-age **7 days** |
| Fail-closed | Missing `hud.env` keys → login 503 `secrets_missing` |

**Secrets posture (code contract, not contents):** `load_hud_secrets()` reads env override or `secrets_dir()/hud.env`; same family as `gemini.env`. Directory mode expected `0700` per M13 deny rules. **Do not** commit or dump values.

### 3.4 What already exists vs missing (session / agent feel)

| Present | Missing (M14+M13 gap for packaged slice) |
|---------|------------------------------------------|
| Chat-first grid + organism **peer column** | Chat **full-bleed home**; Body behind button/drawer |
| Moss CSS variables in `app.css` | **CSS pack** polish (composer, welcome, dial, packaged density) |
| Password → session cookie; `agent_armed` chip | Session **welcome** (“it’s me”) without ops clutter |
| Mode `<select>` observe/agent/plan | Chat-native dial + **Plan ask card + Accept** + **Agent confirm** |
| Tool cards + receipt_id | HITL confirm for `needs_confirm` (Consent Integrity) |
| Serve HTTPS URL (pasteable) | Dock + `ada-open` + thin manifest |
| Tailscale user soft header | Soft greeting when header present |
| — | Web app manifest / icons for Add to Dock |

### 3.5 Plan mode metal truth

| Claim | Tag |
|-------|-----|
| Gateway denies write tools in `plan` (and `observe`) | **METAL** (`gateway.py`) |
| Charter tells model Plan is stub / propose-only | **METAL** |
| HUD has no plan-card accept / Build affordance | **METAL** |
| Memory overwrite paths can return `needs_confirm` | **METAL** (facts/staging) |
| HUD `app.js` never handles `needs_confirm` | **METAL** |

**Verdict:** Plan is a **policy stub**, not an agent UX product yet. Earning real propose/accept is in-scope for M14 implement phases — UI must bind approval to **gateway `{tool, args}`**, never model prose ([Consent Integrity](https://arxiv.org/abs/2606.02668); M02).

---

## 4. Survey — ≥6 real surfaces

| Surface | Session / login | Mac install / open | Tool / receipt UX | Plan → approve → run | Avoids “dumb chatbot site” by… | Steal for ADA | Skip |
|---------|-----------------|--------------------|-------------------|----------------------|--------------------------------|---------------|------|
| **Cursor Agent** | IDE account; local workspace trust | Native app (always there) | Diffs, tool traces, checkpoints | **Plan mode** → edit plan → Build → Agent | Modes (Ask/Plan/Agent/Debug); plan is a first-class object | Mode dial + plan-as-artifact + Build | Multi-tenant SaaS; IDE rewrite |
| **Claude (app / Code)** | Account session | Native / terminal; always one click | Tool permission prompts; plan mode approve switches permission mode | Plan staging → approve options (manual / auto) | Permission modes + explicit approve | Approve exits Plan into execute mode | Cloud identity as Agent authority |
| **ChatGPT** | Account | Web + native apps; Dock-able | Light tool cards; Custom GPTs | Soft “thinking” / canvas — weaker HITL | Product chrome + memory; feels like *an app* | App packaging / Dock habit | Public multi-tenant; Funnel-shaped product |
| **Open WebUI** | Local users / API keys | Docker server + browser; self-host | Model/tools; less receipt-native | Agents/features vary; not gateway-first | Local ownership feel | Self-host + Tailnet pattern | Heavy Docker on Pi; Node stack |
| **LibreChat** | Multi-user auth, agents ACL | Docker Compose ops | Agents + MCP; tool attach | Agent builder / capabilities | Persistent “agent” objects | Named agent + tools panel metaphor | Enterprise auth stack; 5-service Compose |
| **Continue.dev** | IDE / config.yaml keys | VS Code / JetBrains extension | Inline edits; provider config | Config-driven, not full HITL product | Lives *inside* work surface | “Open where you already are” | Requires IDE; not organism vitals |
| **Jan** (extra) | Local desktop | Native Electron install | Local models | Offline desktop | Feels like *software you own* | Native wrapper aspiration (Tier B) | Local LLM cortex default |

**EVIDENCE verdict:** products that feel like agents share (1) **one-click presence**, (2) **explicit modes / permissions**, (3) **plan or approve before irreversible work**, (4) **receipts/diffs/traces**. Chat-only scrolling is necessary but not sufficient ([HatchWorks Agent UX Patterns, 2026](https://hatchworks.com/blog/ai-agents/agent-ux-patterns/)).

**ADA-specific skip:** Open WebUI / LibreChat as *replacements* — wrong trust model (multi-tenant chat SaaS) and ops tax on Pi. Steal patterns; keep M03 metal.

---

## 5. Agent UX literature (2025–26) → ADA mapping

Sources (EVIDENCE): HatchWorks pattern library (2026); Smashing Magazine agentic UX (2026-02); autonomy-dial writeups (UX Collective); Cursor/Claude plan-mode docs; Consent Integrity (arXiv:2606.02668).

| Pattern | Literature claim | ADA map (do not reinvent policy in UI) | Phase |
|---------|------------------|----------------------------------------|-------|
| **Autonomy dial** | Suggest → draft/plan → act-with-confirm → act | **Observe / Plan / Agent** already exist — UI labels + chat-native copy; gateway remains enforcer | P0 |
| **Intent preview / plan preview** | Show steps before side effects | Plan mode proposes; plan card in stream; **Accept** arms Agent turn or single confirmed tool | P1 |
| **HITL checkpoint** | Designed gates, not Slack heroics | Render gateway pending `{tool,args}` + Confirm/Deny; bind to `needs_confirm` / future confirm API | P1 |
| **Tool-call trace** | Streaming tool I/O visibility | M13 tool cards + receipt_id (+ optional summary); audit tail remains escape | P0 reuse |
| **Action receipts** | What changed + undo hook | `runs/` JSONL + receipt_id; undo only where organs support it (don’t fake) | P0–P1 |
| **Start/stop/pause** | User agency mid-flight | Soft: disable Send while turn runs (today); hard cancel = later harness hook | P2 |
| **Evidence panel** | Sources ≠ chain-of-thought dump | Cites / x-ray / dream digests (M13) — not CoT theater | reuse |
| **Memory controls** | What I remember / edit | FACTS tools + future confirm; not a SOUL.md browser | later |
| **Taskboard** | Chat-only fails for long work | **Defer** — personal lab; stream + plan card enough at Tier A | OUT Tier A |
| **Preview theater warning** | Rubber-stamp plans worse than none | Plan cards must be short, gateway-true, editable; no fake 20-step fluff | lock |

**ADA maturity target (Tier A):** literature Level 2 “guided agent” — traces + receipts + HITL gates + mode dial — **not** Level 3 trusted autonomy dashboards.

---

## 6. Mac access packaging — options scored

| Option | EVIDENCE | FEASIBLE (Pi+Mac) | Ops | Agent-app feel | Verdict |
|--------|----------|-------------------|-----|----------------|---------|
| **A. Bookmark / Safari “Add to Dock”** on Serve HTTPS URL | Apple Safari Add to Dock; Tailscale Serve → `*.ts.net` HTTPS enables PWA-class install | High — zero Pi change; Mac already on Tailnet | Lowest | Medium–high (standalone window) | **Recommend P0** |
| **B. Thin `ada-open` script** (`tailscale status` check → `open https://ada-pi5…`) | Common lab pattern; VoiceClaw/Hermes companions use Serve + open | High — shell on Mac only | Low | Medium (Dockable `.command` / Shortcuts) | **Recommend P0 companion** |
| **C. Web app manifest + icons on Pi HUD** | Serve HTTPS + manifest → better install prompts | High — static files only; no Node | Low | Medium+ | **P0/P1 thin add** |
| **D. Custom URL scheme** `ada://` → open Serve URL | Native feel; needs Mac helper registered | Medium — helper required | Medium | High | Runner-up P2 |
| **E. Menu-bar / tiny companion** (Swift/Shortcuts/Electron) | Portico / Tailscale-proxy / VoiceClaw Companion prove pattern | Medium — Mac-only binary; keep API on Pi | Medium | **Highest** | Runner-up Tier B |
| **F. Next/React SPA on Pi** | Familiar product stack | **Low** — no Node on Pi; RAM/ops; fights M03 | High | High chrome, wrong host | **Reject as Pi default** |
| **G. Next/React (or Tauri) on Mac → Pi API** | Hybrid: shell local, organs remote | Medium — Mac build machine; CORS/cookie care over Serve | Medium–high | High | **Tier B if A–C insufficient** |
| **H. Funnel / public tunnel for “easy open”** | — | — | — | — | **POLICY forbid** |

### Recommend (locked for coding default)

1. **P0:** Document + ship Mac **open path**: Safari/Chrome bookmark **and** Safari **Add to Dock** for `https://ada-pi5.tailbc896a.ts.net`.  
2. **P0:** Add Mac-side **`scripts/ada-open-mac.sh`** (or Shortcuts) — verify Tailscale up, ping Serve, `open` URL; fail with plain “Tailscale off / HUD down”.  
3. **P0/P1:** Thin **manifest + icons** on Pi static HUD so Dock install is first-class (still Python ASGI — no SPA rewrite).  
4. **Runners-up:** menu-bar companion or Mac SPA (**G**) only if Dock+script still feel like a website after session/agent UX ships.  
5. **Do not** put Next on the Pi.

**POLICY note:** Serve stays on Pi; Mac never becomes a second cortex. Companion opens / wraps; API authority remains `ada.hud` + gateway.

---

## 7. Voice / wake / pretext — honest tiers

Constitution already: Tier A none; Tier B PTT; Tier C always-listen + voice-ID (§3.4 / §15). M05: text-first register; audio later; always-listen = Tier C.

| Tier | What | FEASIBLE | POLICY | Roadmap |
|------|------|----------|--------|---------|
| **A** | Text chat + session welcome + mode dial + receipts | Yes — metal today + M14 P0–P1 | OK | **Default ship path** |
| **B-voice** | Push-to-talk on **Mac** → STT → `POST /api/chat` (same harness); optional TTS playback of assistant text | Yes — Mac mic/CPU; Pi stays text API; reuse M05 register brevity | Secrets stay on Pi; no Funnel; no always-listen | **Allow in roadmap** — do not OUT by taste. Implement after agent-feel P1 |
| **B-wake-thin** | Explicit wake **phrase only while PTT held** or menu-bar “listen once” | Yes if B-voice exists | Still not always-listen | Optional with B-voice |
| **C-wake** | Always-listen + speaker recognition as authority | Hard on Pi; privacy blast radius | Authority must remain Tailnet ACL + session, not vibes | **Defer** with reasons |
| **C-pretext / richer face** | Delight skin / face over **same** stream (body §7.2 / constitution §15) | UX-heavy; not required for agent feel | OK as skin if receipts stay honest | **Defer** — allowed as aspiration; not P0; not banned by taste alone |
| **C-presence theater** | Fake “she’s watching you” without metal | — | FANFICTION | **OUT** |

**Falsifier for voice Tier B:** STT transcript must appear as normal user turn in `runs/` JSONL; tools still gateway-gated; no silent side effects from audio alone.

---

## 8. Stack fork — decision

| Option | Pros | Cons | Score |
|--------|------|------|-------|
| **Keep Python ASGI + Jinja + static JS on Pi** | Already shipped; Pi-feasible; one process; Serve-simple; M13 chrome live | Caps “native app” chrome | **Winner for control plane** |
| **Next/React on Pi** | Rich UI ecosystem | No Node on host; build RAM; ops second runtime | **Reject** |
| **Hybrid: Mac shell + Pi API** | Best app feel; Pi stays thin | Cookie/CORS; two repos/surfaces; drift risk | **Tier B upgrade path** |
| **Rewrite HUD in React served as static from FastAPI** | Modern components without Node *runtime* on Pi | Needs Mac/CI build step; larger rewrite than earned | Optional later if static bundle only |

### Locked rationale (no predetermined winner — survey decided)

- **EVIDENCE:** agent feel comes from modes + plan/accept + receipts + one-click open — not from React per se (Cursor/Claude prove native *or* careful web).  
- **FEASIBLE:** Pi has no Node; 8GB shared with cortex/tools; ASGI HUD already healthy.  
- **POLICY:** trust ring stays Tailscale → localhost ASGI; don’t multiply attack surface.  
- **METAL:** M13 P0–P2 already delivered chat-first static UI.

**Decision:** **Keep Pi Python ASGI + static as the agent surface host.** Packaged feel comes from CSS pack + chat-home + ask/accept — not from React. Mac hybrid shell stays Tier B after this slice.

---

## 9. Modes packaging — ask / accept without removing gateway

| Mode | Operator meaning (UI copy) | Gateway truth | Chat-native packaging |
|------|----------------------------|---------------|----------------------|
| **Observe** | “Look / ask — no writes” | Reads OK; writes denied | Mode chip; chat still home; Body drawer for vitals |
| **Plan** | “Propose — I’ll Accept” | Writes denied; reads OK | **Ask:** model proposes plan → **Plan card** in stream → **Accept / Revise / Stay** |
| **Agent** | “Act under session” | Writes allowed; overwrite may `needs_confirm` | Session required; **Confirm/Deny** on gateway `{tool,args}` when needed |

### 9.1 Plan — proper ask → accept (LOCKED)

Cursor/Claude pattern adapted to ADA metal:

1. User selects **Plan** (session required) and states intent.  
2. Turn runs in Plan mode — gateway **cannot write** (**POLICY** / **METAL**).  
3. Assistant reply is treated as a **plan artifact**: UI wraps last Plan turn in a **Plan card** (steps from assistant text; honest stub — no fake taskboard).  
4. Affordance row: **Accept** · **Revise** (focus composer with hint) · **Stay in Plan**.  
5. **Accept (locked semantics):**  
   - Require session (already).  
   - Switch mode dial → **Agent**.  
   - Re-send a short execute cue that includes the accepted plan text (e.g. user turn: `Accepted plan — execute:\n…`) so the Agent turn is receipt-backed and visible in JSONL.  
   - Do **not** silently run tools from the Plan card without that Agent turn.  
6. **Revise** = stay in Plan; user edits; no mode switch.

### 9.2 Agent — proper ask → confirm (LOCKED)

1. Agent mode can run tools under gateway ladder.  
2. When gateway / memory returns **`needs_confirm`** (or future pending-confirm SSE): show **inline Confirm card** with gateway-rendered `{tool, args}` — never model prose alone ([Consent Integrity](https://arxiv.org/abs/2606.02668)).  
3. **Confirm** = client sends an explicit confirm turn / API that sets `confirmed=True` for that pending call (implement detail in coding chat — must not invent success).  
4. **Deny** = stay put; record denial in UI + mode denials chip.  
5. Routine Agent tools that do not need confirm still use existing tool cards (start/finish/receipt).

### 9.3 Intent hints (UI only)

| User intent | Suggested mode |
|-------------|----------------|
| Status / vitals / lookup | Observe (open Body for vitals) |
| “How should we…” / multi-step design | Plan → Accept |
| “Do it” / remember / write | Agent (+ Confirm when asked) |

**Do not:** invent a fourth autonomy slider that bypasses Observe/Plan/Agent.

---

## 10. Session / login UX locks

| Lock | Decision | Tag |
|------|----------|-----|
| Observe | Mesh enough; chat home still works | **POLICY** |
| Agent / Plan | Password session required | **POLICY** / **METAL** |
| Tailscale header | Soft identity + welcome only — **never** Agent authority | **POLICY** |
| Soft TS mismatch | **Display-only** (chip / muted warn) — still require password for Agent | **LOCKED** |
| Welcome strip | Compact: brand + “session armed · it’s you” when cookie valid + soft `ts=` | **P0** |
| After login | Remain on **chat**; do not navigate to Body | **LOCKED** |
| Login friction | Password once / 7d cookie; autofocus when Agent/Plan selected without session | **P0** |
| Logout | Clear cookie; drop to Observe mode chip; stay on chat | **METAL** |
| No SSO / OAuth cloud | Keep local `hud.env` | **POLICY** |

---

## 11. OPEN for Aryan — **mostly locked** (≤7 residual)

| # | Question | Resolution |
|---|----------|------------|
| 1 | Mac open P0 | **LOCKED:** Dock **+** in-repo `scripts/ada-open-mac.sh` |
| 2 | Soft Tailscale allowlist | **LOCKED:** display-only |
| 3 | Plan Accept semantics | **LOCKED:** Accept → switch Agent + re-send accepted plan as execute cue (§9.1) |
| 4 | Confirm UI placement | **LOCKED:** **inline** stream cards |
| 5 | Stack revisit | **LOCKED:** ASGI+static through this slice; Mac companion Tier B later |
| 6 | Voice Tier B | **LOCKED:** **park** after this P0+P1 slice (roadmap only) |
| 7 | First implement | **LOCKED:** **P0+P1 together** (packaged feel) |

**Residual (optional, not blocking plan):** Body drawer label — `Body` vs `HUD` vs `Organism`? Default recommend **Body**.

---

## 12. Falsifiers

| # | Falsifier | Pass if |
|---|-----------|---------|
| F1 | Tailnet-only | Mac opens Serve URL; HUD not on Funnel/LAN `0.0.0.0` |
| F2 | Fast connect | ≤2 clicks (Dock or script) to chat composer — no URL paste |
| F3 | Session “it’s me” | After login, welcome on **chat**; Agent works; logout → mesh on chat |
| F4 | Chat is home | First viewport is stream+composer; Body closed by default |
| F5 | Body drawer | Vitals/lifecycle/x-ray/audit only after Body open; doctor parity still holds |
| F6 | Gateway authority | Plan cannot write; Accept does not bypass gateway; Agent confirms show `{tool,args}` |
| F7 | Consent Integrity | Confirm card matches gateway pending call |
| F8 | No second brain | Client only `/api/*`; no client tool executor |
| F9 | Secrets | No secret dumps; x-ray deny unchanged |
| F10 | Packaged CSS | Fixed palette/type; no purple-glow SaaS clone; Dock window feels intentional |

---

## 13. Ordered implement-next — **plan this slice**

**One coding chat ships P0+P1** (M13 shell + M14 interaction). No large rewrite beyond ASGI/static.

### P0 — packaged shell (access + CSS + chat home + Body drawer)

| # | Work | Owner card |
|---|------|------------|
| 1 | Mac: Dock docs + `scripts/ada-open-mac.sh` | M14 |
| 2 | `manifest.webmanifest` + icons; link in `index.html` | M14 |
| 3 | **CSS pack:** lock/polish moss vars; composer; header; welcome; dial; density — app not ops dump | M13 |
| 4 | **IA:** chat full home; **[Body]** toggles drawer/panel (vitals, lifecycle, x-ray, audit) | M13 |
| 5 | Session welcome strip + login CTA when Agent/Plan unarmed | M14 |
| 6 | Mode dial labels (Observe / Plan / Agent) | M14 |
| 7 | Smoke F1–F5 from Mac |

### P1 — agent feel (ask / accept / confirm)

| # | Work | Owner card |
|---|------|------------|
| 1 | Plan card after Plan turns + Accept / Revise / Stay | M14 |
| 2 | Accept → Agent + execute cue turn (§9.1) | M14 |
| 3 | Inline Confirm/Deny for `needs_confirm` (Consent Integrity) | M14 |
| 4 | Optional: tool finished summary crumb | M13 leftover |
| 5 | Smoke F6–F7 vs `ada chat --mode plan|agent` |

### P2 — later (not this packaged slice)

Stop/cancel harness hook; menu-bar companion; voice Tier B; pretext face.

**Stop before:** Funnel, Next-on-Pi, always-listen, consciousness chrome, Dream/WORLDVIEW editors, replacing gateway.

---

## 14. Relationship to M03 / M13 / M05

| Card | Owns |
|------|------|
| **M03** | Architecture: bind, Serve, auth stance, harness channel, pane *truth sources* |
| **M13** | Presentation: **CSS pack**, chat-home IA, **Body drawer**, vitals/x-ray chrome |
| **M14 (this)** | Access packaging, session welcome, Mac open, **ask/accept/confirm**, stack/voice tiers |
| **M05** | Register / personality text contract (**friend-first** social/about-me — not curator dumps); audio reuses later |

**Implement pairing:** ship **M13 P0 shell + M14 P0/P1 interaction** in one coding chat after plan review.

---

## 15. References

| Kind | Cite |
|------|------|
| Architecture | [`M03_HUD.md`](./M03_HUD.md) |
| Presentation / Body drawer | [`M13_HUD_UX.md`](./M13_HUD_UX.md) |
| Harness / Consent | [`M02_CHAT_HARNESS.md`](./M02_CHAT_HARNESS.md); gateway `src/ada/tools/gateway.py` |
| Voice text | [`M05_VOICE_PERSONALITY_CONTROL.md`](./M05_VOICE_PERSONALITY_CONTROL.md) (**M05.2 friend-first**); constitution §§3–4, 15 |
| Code | `src/ada/hud/{app,auth,routes_*,chat_service,stream_bridge}.py`, `templates/index.html`, `static/app.{js,css}` |
| Metal URL | `https://ada-pi5.tailbc896a.ts.net` → `127.0.0.1:8787` (2026-08-16) |
| Pattern lit | [HatchWorks Agent UX Patterns](https://hatchworks.com/blog/ai-agents/agent-ux-patterns/); [Smashing Magazine agentic UX](https://www.smashingmagazine.com/2026/02/designing-agentic-ai-practical-ux-patterns/); [Cursor Plan Mode](https://cursor.com/docs/agent/plan-mode) |
| Serve + Dock/PWA | [Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve); [Safari Add to Dock](https://support.apple.com/guide/safari/add-to-dock-ibrw9e991864/mac) |
| Consent Integrity | [arXiv:2606.02668](https://arxiv.org/abs/2606.02668) |

---

*End of M14 v2. OPEN locked for packaged P0+P1. Ready to plan implementation.*
