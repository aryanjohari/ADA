# M13 — HUD UX / living agent surface

**Status:** living surface doc — **metal P0–P2 shipped** (2026-08-15). **Packaged wave P0′/P1′ shipped** (2026-08-16): chat = home; Body `<dialog>` drawer; moss CSS modules; session welcome; Plan Accept + Agent Confirm (with M14).  
**Date:** 2026-08-15 (IA + packaged metal 2026-08-16)  
**Host:** `ada-pi5` (Raspberry Pi 5 Model B Rev 1.1, Debian trixie, ~8 GiB RAM)  
**Branch:** `rewrite/v1-body`  
**Depends on:** [`M03_HUD.md`](./M03_HUD.md) (**architecture authority** — panes, bind, Serve, auth, harness wiring), [`M02_CHAT_HARNESS.md`](./M02_CHAT_HARNESS.md) (stream events + `run_turn`), [`M00_BODY_SENSE.md`](./M00_BODY_SENSE.md) + [`M12_BODY_PROPRIOCEPTION.md`](./M12_BODY_PROPRIOCEPTION.md) (vitals fields / doctor parity), [`M11_DREAM_CONSOLIDATION.md`](./M11_DREAM_CONSOLIDATION.md) (**pointer only** — last dream / campaign digests for P3 stubs)  
**Access / session / Mac packaging / agent ask→accept:** [`M14_AGENT_SURFACE.md`](./M14_AGENT_SURFACE.md) — **co-implement**; M13 owns chrome + Body drawer + CSS pack.  
**METAL present (2026-08-15/16):** `src/ada/hud/` ASGI on `127.0.0.1:8787`; Serve → `https://ada-pi5.tailbc896a.ts.net`; chat-first shell but organism still a **peer column** (gap vs new IA); moss CSS vars live in `app.css`.  
**OUT of implement gate unless explicitly phased later (or earned in M14):** Dream manage editor, WORLDVIEW editor, sandboxed shell, vendor search UI, full brief product, Funnel, unrestricted FS, Node/Next **on Pi**, holographic face / consciousness FANFICTION. Voice / Mac hybrid / pretext: see M14 tiers.

**Name justification:** **`M13_HUD_UX.md`** next to other modules (not `docs/HUD_SURFACE.md`). M03 locked control-plane **truth**; M13 owns **presentation + IA + phased UI**. Keeping the module number makes implement chats find it beside M03/M12.

---

## 1. Slice rule + won’t-chase

**Slice rule:** inventory metal HUD honestly → lock a **chat-first AI agent control plane** that still feels like a **Pi organism** (readable body + honest receipts) → specify stream cards, vitals cards, read-only ADA x-ray, and doc/cite/dream preview tightly enough that a later implement chat can ship **P0 → P2** without inventing IA. This card does **not** rewrite M03 architecture, fork the cortex, or implement UI.

**Won’t-chase**

| Out | Why |
|-----|-----|
| Funnel / public URL | POLICY — Tailscale Serve only |
| Next / React / Node product rewrite | Pi-feasible stack stays Python ASGI + static HTML/CSS/JS |
| Second cortex / web-only agent | Chat = `channel.web` → existing M02 harness |
| Dream manage / WORLDVIEW editors | Separate cards; x-ray is **read-only** |
| Voice, sandboxed shell, vendor search, full brief | Later / other modules |
| Purple-glow “generic AI”, holographic face | Taste + FANFICTION |
| Unrestricted filesystem browser | Secrets + blast radius |
| Replacing organ JSON with decorative gauges that drift from doctor | Body §10.2 / M12 |

```text
  Aryan phone (Tailscale ON)
        |
        | HTTPS MagicDNS Serve
        v
  127.0.0.1:8787  ada.hud  (channel.web)
        |
        +-- chat → harness.run_turn (M02)
        +-- vitals → collect_vitals / doctor (M00/M12)
        +-- x-ray → allowlisted read under ada-data (P2)
        x Funnel  x second brain  x secrets trees
```

---

## 2. Taste locks

| Lock | Decision |
|------|----------|
| Exposure | Tailscale-only; **Serve OK**; **Funnel NO**; bind **`127.0.0.1`** |
| Cortex | Chat drives existing M02 harness — UI is a **channel**, not ADA herself |
| Body numbers | M00/M12 organs; parity with `ada body doctor` / vitals; **library ≠ body** |
| Stack | Python ASGI + Jinja + static CSS/JS (no Next/React default path) |
| **Home** | **Chat is the product.** First viewport = brand + session/mode + stream + composer |
| **Body HUD** | Vitals / lifecycle / x-ray / audit behind **[Body]** button → drawer/panel — **not** peer home column |
| **CSS pack** | Fixed moss palette + Plex (self-host) + packaged density in next P0 — cool app, not ops dump |
| Voice in copy | she/her; witty/roast OK in **chat stream**, not in chrome that lies |
| Secrets | Never-to-cloud / never in x-ray: `secrets/`, `~/.ssh`, env key files, Tailscale auth material, full machine-id dumps |
| Auth | Observe = mesh; Agent/Plan = session password (M14); after login stay on chat |
| Ask / accept | Plan card + Accept; Agent Confirm — owned with M14, rendered in this chrome |
| Raw honesty | Audit escape inside Body drawer; never owns first viewport |
| Pasted-path honesty | Unchanged — host must appear in user text for `user_pasted` (M12 harden) |

---

## 3. METAL inventory (2026-08-15)

**Today (post P0–P2):** chat-first shell — stream owns the first viewport; organism **vitals cards** + compact mode/lifecycle chips; optional read-only **x-ray** (md/cite/dream preview). Not five equal JSON panes.

### 3.1 Live reachability

| Check | Result | Tag |
|-------|--------|-----|
| Process | `ada hud serve --host 127.0.0.1 --port 8787` (pid observed) | **METAL** |
| Listen | `127.0.0.1:8787` only | **METAL** |
| Serve | `https://ada-pi5.tailbc896a.ts.net` → `http://127.0.0.1:8787` (tailnet only) | **METAL** |
| Funnel as HUD path | Not used for this control plane | **POLICY** / **METAL** |
| `GET /` | HTTP 200 | **METAL** |
| Note | Long-lived HUD process may lag code (e.g. `/api/vitals` extras missing M12 `cpu_count` until restart); CLI `ada body vitals` is source of field truth | **METAL** ops |

### 3.2 Package layout

| Path | Role |
|------|------|
| `src/ada/hud/app.py` | FastAPI factory; mounts static; `app.state.chat = ChatService()` |
| `src/ada/hud/routes_pages.py` | `GET /` → Jinja `index.html` |
| `src/ada/hud/routes_api.py` | `/api/vitals`, `/lifecycle`, `/doctor`, `/mode`, `/run/tail`, `/chat`, `/login`, `/logout` |
| `src/ada/hud/auth.py` | Mesh vs session; `hud.env` secrets; Agent/Plan gate |
| `src/ada/hud/chat_service.py` | One `ChatSession`; calls `harness.loop.run_turn` only |
| `src/ada/hud/stream_bridge.py` | `CallbackSink` → queue → SSE (`text/event-stream`) |
| `src/ada/hud/templates/index.html` | Five equal panes + chat form |
| `src/ada/hud/static/app.css` | Dark ops chrome; 2-col ≥720px |
| `src/ada/hud/static/app.js` | Polls + SSE chat; XSS escape via `textContent` / `esc()` |
| `src/ada/cli/main.py` `hud serve` | Loopback assert; uvicorn |

### 3.3 Panes ↔ APIs ↔ refresh

| Pane (DOM) | Shows today | Data source | Refresh | Auth |
|------------|-------------|-------------|---------|------|
| **Stream** `#pane-stream` | Bubbles + crude tool cards; chat form | SSE from `POST /api/chat` → `run_with_bridge` → harness events | Live during turn | Observe free; Agent/Plan need session |
| **Body vitals** `#pane-vitals` | Hand-built `key=value` lines in `<pre>` (subset) | `GET /api/vitals` → `collect_vitals()` + `urgent_faults` | Poll **3s** | Mesh |
| **Lifecycle** `#pane-lifecycle` | `born_at`, wake/fault chips, last dream + push | `GET /api/lifecycle` → identity + ledger via `dream_status()`; `last_dream_*` from `dream_ok`/`dream_fail`; `push` usually `skipped` (stub) | Poll **10s** | Mesh |
| **Mode + perms** `#pane-mode` | Mode `<select>`, login form, auth badge, **full mode JSON `<pre>`** | `GET /api/mode`; `POST /api/login|logout` | Poll **5s** + after chat | Mesh read; login for Agent |
| **Raw run tail** `#pane-raw` | Path + wall of `JSON.stringify` lines | `GET /api/run/tail?n=80` → latest `/mnt/ada-data/runs/<day>/*.jsonl` | Poll **2s** | Mesh |

**Also shipped, unused by UI chrome:** `GET /api/doctor` → `run_body_doctor()` (parity smoke / future badge).

### 3.4 Stream events (harness → UI)

| Event | Emitted by | UI today |
|-------|------------|----------|
| `mode_info` | `loop.py` | Not rendered in stream (mode pane polls) |
| `session_receipt_path` | `loop.py` | Updates `#run-path` |
| `token_delta` | whole assistant text after generate round | Green-border bubble (not true token drip) |
| `tool_call_started` | gateway tool + args | Mono “tool card” with full `JSON.stringify(args)` |
| `tool_call_finished` | `ok`, `receipt_id` (no observation body in SSE) | Mutates last card class ok/fail |
| `usage_update` | loop | Retained → one-line turn footer crumb (tok + optional `$` estimate) |
| `fault` | no_key / bridge errors | Red-border bubble |
| `turn_done` | stream_bridge after worker | Dim stop/steps + usage crumb when retained |

User message is painted client-side only (`you: …` bubble) — not an SSE event.

### 3.5 Auth (metal matches M03)

| Mode | Gate |
|------|------|
| `observe` | Tailnet + Serve + localhost (no password) |
| `agent` / `plan` | Session cookie from `POST /api/login` vs `ADA_HUD_PASSWORD` + `ADA_HUD_SESSION_SECRET` in `secrets/hud.env` |
| Soft display | `Tailscale-User-Login` header → `mode.tailscale_user` (not Agent authority) |

### 3.6 Mobile behavior (metal)

- Viewport meta present; single-column panes below 720px; two-column grid above with stream spanning full width.
- Chat textarea usable; panes stack → **long scroll**; vitals/lifecycle/raw compete equally with chat.
- No dedicated mobile chrome (no collapsible “organism” drawer; raw tail always visible).

### 3.7 Data roots on this host (for later x-ray)

| Root | Live contents (sample) |
|------|------------------------|
| `/mnt/ada-data/memory/` | `dreams/`, `worldview/` (+ `campaigns/`), `cites/`, `facts/`, `staging/`, `lifecycle.jsonl` |
| `/mnt/ada-data/runs/` | `YYYY-MM-DD/*.jsonl` |
| `/mnt/ada-data/dream/outbox/` | seal packages `dream-…/` |
| `/mnt/ada-data/secrets/` | **DENY** (mode `0700`) |
| `/mnt/ada-data/dreams/` | **does not exist** — dreams live under `memory/dreams/` |

### 3.8 M12 fields the UI must surface (not invent)

From organs / CLI truth (`ada body vitals` / doctor):

| Bucket | Fields |
|--------|--------|
| Capacity | `extras.cpu_count`, `extras.arch`, `extras.os_pretty`, memory total/available |
| Health | `thermal.temp_c`, `throttled_hex` / bits, `load.load1`, disks avail (`/` + `ada-data`), `mounts.ada_data_ok`, `probe_errors`, `urgent_faults` |
| Posture | `extras.tailscale_ipv4` (optional card) |
| Identity (lifecycle pane) | `born_at`, board/os via identity card when shown |
| Doctor parity | mount ok, probe_errors count, urgent none/flags — same spirit as `ada body doctor` |

### 3.9 M11 pointer (P3 stubs only — not product)

Later UI may **show**:

- Last dream digest path / `written_at` from `memory/dreams/YYYY-MM-DD.md` or lifecycle `dream_ok` when wired.
- Campaign digest links under `memory/worldview/campaigns/<id>/`.
- Due/open-loop **hints** from staging — **not** Dream manage editor, not morning-brief product (M11 OUT).

`GET /api/lifecycle` now wires `last_dream_at` / `last_dream_status` from `ada.dream.run.dream_status` (ledger `dream_ok` / `dream_fail`); no longer hardcodes null/`n/a` when a `dream_ok` exists. `push` stays truthful (`skipped` until remote configured). Campaign-hint / brief UI still OUT.
---

## 4. Current look (honest)

| Aspect | Metal today |
|--------|-------------|
| Layout | Five peer “ops panes”; stream full-width on desktop but still one card among equals on mobile |
| Typography | CSS vars: `--sans` / `--mono` named IBM Plex (no webfont load → system fallback) |
| Color | Dark charcoal (`--bg` `#1a1d21`, `--pane` `#242830`), muted grey labels, green accent `#7cb342`, warn/deny |
| Density | High — four `<pre class="mono">` walls + stream + forms |
| Structured vs raw | Stream has minimal bubbles/cards; **vitals / lifecycle / mode / raw are text or JSON dumps** |
| Hierarchy | Header “ADA” is present but chat is not visually primary; raw tail poll every 2s steals attention |
| Motion | None intentional (scroll-into-view only) |
| Brand | Ops tagline “control plane · Tailscale Serve · she/her” — truthful, not agent-product |

**Verdict:** architecture is correct (M03); surface reads as **lab dashboard**, not a credible chat-first agent UI.

---

## 5. Pain list → product intent

| # | Pain |
|---|------|
| 1 | Five equal panes → crowding; chat not the first-class surface |
| 2 | Walls of `<pre>` / JSON (mode, raw, lifecycle wake objects) |
| 3 | Vitals are scannable only if you already know field names; no cards/units |
| 4 | Tool cards dump full args JSON; finished event omits short result preview |
| 5 | User/assistant hierarchy weak (same bubble family; purple “you” border is the only cue) |
| 6 | ~~`usage_update` ignored~~ → turn footer tok/$ crumb (minimal; not billing pane) |
| 7 | Mobile = long stack of ops panels; organism truth buried |
| 8 | No way to browse dreams/cites/runs without SSH — FS browser still OUT of M12, owed here as **P2 x-ray** |
| 9 | Stale HUD process can show thinner vitals than CLI (ops, not design) |

**Target (one sentence):** a **packaged ADA chat agent** (home = stream after login/session) with organism truth one **Body** click away — not a peer ops dashboard, not a bare Tailscale site.

---

## 6. Target IA + visual principles

### 6.1 Information architecture (2026-08-16 LOCKED with M14)

| Priority | Surface | Role |
|----------|---------|------|
| **Primary / home** | Chat / stream + composer | Full ADA agent conversation after (or without) login — turns, plan cards, tool/receipt/confirm cards |
| **Chrome** | Brand + session welcome + mode dial + **[Body]** | Compact top bar — not a second column of ops |
| **Secondary / on demand** | **Body drawer** | Vitals cards, lifecycle, x-ray, audit/raw — opened by button; closed by default |
| **Tertiary inside Body** | Mode detail denials / doctor badge | Still truthful; not competing with chat |
| **Not home** | Observe mode | Gateway read-only mode — **not** a separate Observe dashboard |

```text
┌─────────────────────────────────────────────┐
│ ADA · session · Plan|Agent|Observe · [Body] │
├─────────────────────────────────────────────┤
│                                             │
│   STREAM  (flex grow — the product)         │
│   … plan card / tool cards / bubbles …      │
│                                             │
├─────────────────────────────────────────────┤
│   composer ………………………… [Send]       │
└─────────────────────────────────────────────┘
         [Body] open →
┌──────────────────────┐
│ Vitals · Lifecycle   │
│ X-ray · Audit        │
└──────────────────────┘
```

### 6.2 Visual direction — CSS pack (LOCKED for next P0)

Moss variables already **METAL** in `app.css` (`--bg0` … `--accent` leaf green). Next pack **polishes**, does not invent a new theme:

| Rule | Spec |
|------|------|
| Palette | Keep moss-black / leaf accent; **no** purple→indigo SaaS clone |
| Type | IBM Plex (self-host `/static/fonts/`); display weight for **ADA** |
| Density | Chat-first; generous stream; compact chrome; Body drawer denser OK |
| Composer | Sticky, clear focus ring, packaged height |
| Cards | Plan / tool / confirm share one card family; radius `--radius` |
| Motion | Keep 2–3 intentional motions; honor `prefers-reduced-motion` |

```css
:root {
  --bg0: #0f1210;
  --bg1: #171b18;
  --surface: #1e2420;
  --surface-2: #262d28;
  --line: #343c36;
  --fg: #e6ebe4;
  --muted: #8b968c;
  --accent: #8fbc6b;
  --accent-dim: #4a6340;
  --warn: #c9a227;
  --deny: #c97070;
  --user: #6a8f9e;
  --radius: 6px;
  /* … spaces + fonts as already in app.css … */
}
```

**Spacing / density (updated)**

- First viewport: **only** brand/session/mode/Body + stream + composer.  
- No always-visible vitals strip competing with chat (strip may move into Body or become a one-line fault badge when urgent).  
- Body drawer: vitals grid + lifecycle + x-ray tabs + audit disclosure.

**2–3 intentional motions** — unchanged (stream append, tool settle, urgent vitals pulse in Body).

**Mobile** — sticky composer; Body = full-screen sheet; stream fills rest.

---

## 7. Detailed specs

### 7.1 Stream — tool / receipt cards

**Turn model**

| Element | Spec |
|---------|------|
| User turn | Distinct `.turn-user` — label “You”, slate left rule; escaped text |
| Assistant turn | `.turn-assistant` — accumulates `token_delta` text into **one** running block per generate round (whole-turn OK) |
| Tool card | Inserted **inline** in stream order between turns |
| Fault | Deny-colored; show `error` + message; no fake recovery theater |
| Turn footer | Optional dim line: `stop_reason`, `steps`, usage if present |
| Forbidden | Fake “thinking…” spinner theater; inventing tool names; model-prose-as-args |

**Tool card fields**

| Field | Source | Display |
|-------|--------|---------|
| Name | `tool_call_started.tool` | Bold mono |
| Status | pending → `tool_call_finished.ok` | Chip: `…` / `ok` / `fail` |
| Args (short) | `args` | Truncate JSON to ~120 chars; expand on click |
| Result (short) | Prefer observation from JSONL rebuild; SSE today only has `ok` + `receipt_id` | Show receipt_id always; if API enriched later, 1–3 line summary |
| Receipt | `receipt_id` | Mono link-style text (copyable) |

**Honesty:** gateway args only (Consent Integrity). Same harness as `ada chat`. Rebuild-from-JSONL after refresh remains the durability rule (M03).

**API delta (thin, prefer reuse):** P1 may enrich `tool_call_finished` payload with a **capped** `summary` string from gateway observation (≤240 chars) — still one harness, no second brain. If deferred, cards show name/args/ok/receipt only (metal-compatible).

### 7.2 Vitals UI — cards (doctor parity)

Render from `/api/vitals` (+ optional `/api/doctor` badge), **not** a JSON wall.

| Card | Primary value | Secondary | Source |
|------|---------------|-----------|--------|
| Temp | `temp_c` °C | — | `thermal.temp_c` |
| Throttle | `throttled_hex` | bits now/sticky icons | `thermal.*` |
| Cores / arch | `cpu_count` · `arch` | `os_pretty` | `extras.*` |
| Load | `load1` | load5/15 muted | `load` |
| Memory | avail GiB | total GiB | `memory` |
| Disk `/` | avail | total | `disks[]` label root |
| Disk ada-data | avail | total; **mount badge** | `disks[]` + `mounts.ada_data_ok` |
| Tailscale | IPv4 | optional | `extras.tailscale_ipv4` |
| Doctor | `all clear` / urgent count | probe_errors | `/api/doctor` or derived |

**Falsifier:** side-by-side with `ada body doctor` + `vcgencmd`/`df` within body tolerance. Library/WORLDVIEW never appears in vitals cards.

**Format helpers (UI-only):** bytes → GiB; uptime_s → human; never invent missing probes — show `—` + probe_error count.

### 7.3 Read-only ADA x-ray (P2)

**Purpose:** browse allowlisted durable artifacts so phone ops don’t need SSH — **not** a shell, not an editor.

**Allowlisted roots (metal-adjusted)**

| Root | Why |
|------|-----|
| `/mnt/ada-data/memory/` | dreams, worldview, cites, facts, staging, lifecycle |
| `/mnt/ada-data/runs/` | JSONL receipts |
| `/mnt/ada-data/dream/outbox/` | seal packages |

**Optional later (still read-only):** `/mnt/ada-data/dream/staging/`, `/mnt/ada-data/scratch/` — only if OPEN locks.

**Denylist (hard — path check before read)**

| Deny | Examples |
|------|----------|
| Secrets trees | `/mnt/ada-data/secrets/**`, any `**/hud.env`, `**/gemini.env` |
| SSH / keys | `~/.ssh/**`, `**/id_rsa*`, `**/*.pem` with key material |
| Tailscale auth | `tailscaled.state`, auth keys, full ACL dumps as files if under browse |
| System identity dumps | full `/etc/machine-id` (extras already truncates — don’t re-expose full) |
| Escape | Symlink / `..` resolution must stay inside allowlisted realpath roots |
| Repo secrets | Refuse if resolved path exits allowlist even via symlink |

**UX flow:** root picker → directory list (name, type, size, mtime) → file preview pane.

**API deltas (thin additive)**

| Endpoint | Behavior |
|----------|----------|
| `GET /api/xray/list?root=memory&path=` | List relative to allowlisted root; 404 outside |
| `GET /api/xray/read?root=memory&path=&max_bytes=` | Cap ~256 KiB default; content-type sniff; binary → refuse with metadata |

Observe-only OK for read; do **not** require Agent for x-ray. Still Tailnet-gated by Serve.

### 7.4 Doc / cite / dream preview

| Type | Detect | Default view | Opt-in |
|------|--------|--------------|--------|
| Dream / WORLDVIEW `.md` | path under `memory/dreams`, `memory/worldview` | Markdown render (headings, lists, code); show cite lines | Raw source toggle |
| Cite `.md` | `memory/cites/c_*.md` | Frontmatter / header fields + excerpt body | Raw |
| FACT yaml | `memory/facts/**` | Structured key highlight or fenced yaml | Raw |
| Run JSONL | `runs/**` | Last N pretty records as compact cards | Raw lines |
| Outbox | `dream/outbox/**` | File list + text/json preview when safe | Raw |
| Unknown text | — | Monospace truncated | — |
| Binary | — | “binary / refused” | — |

**Cite honesty:** show `cite:c_…` ids as text; linking to x-ray cite file OK; do not fetch remote URLs from preview.

**Markdown:** client-side lightweight renderer or server-sanitized HTML — **escape unsanitized HTML** in sources; no script execution.

---

## 8. ASCII wireframes (P0–P2)

### P0 — desktop (chat-first + vitals cards)

```text
┌──────────────────────────────────────────────────────────────────────┐
│ ADA                          [observe ▾] auth=mesh  [Login]          │
├────────────────────────────────────────────────┬─────────────────────┤
│ STREAM                                         │ ORGANISM            │
│ ┌────────────────────────────────────────────┐ │ ┌────┐┌────┐┌────┐ │
│ │ You: how hot are you?                      │ │ │49°C││0x0 ││4·64│ │
│ │                                            │ │ └────┘└────┘└────┘ │
│ │ ADA: …                                     │ │ ┌────┐┌────┐┌────┐ │
│ │                                            │ │ │load││mem ││disk│ │
│ │                                            │ │ └────┘└────┘└────┘ │
│ │                                            │ │ ada-data OK · TS IP │
│ └────────────────────────────────────────────┘ │ doctor: all clear   │
│ ┌ message ──────────────────────────┐ [Send]   ├─────────────────────┤
│ └───────────────────────────────────┘          │ Lifecycle (compact) │
│                                                │ born · wake · dream │
│                                                │ n/a stubs OK        │
├────────────────────────────────────────────────┴─────────────────────┤
│ ▸ Audit / raw run tail (collapsed)                                    │
└──────────────────────────────────────────────────────────────────────┘
```

### P0 — mobile (rough)

```text
┌─────────────────────┐
│ ADA   observe  mesh │
│ [49°][0x0][OK][4c]→ │  ← swipe vitals strip
├─────────────────────┤
│ STREAM (flex grow)  │
│ …bubbles…           │
├─────────────────────┤
│ [composer……] [Send] │  ← sticky
│ ▸ More (mode/audit) │
└─────────────────────┘
```

### P1 — stream cards + mode readability

```text
│ You: free disk on ada-data?                    │
│ ┌ tool body_vitals ──────── status ok ───────┐ │
│ │ args {section:"summary"}   receipt=…       │ │
│ │ result avail≈870G · ada_data_ok=true       │ │
│ └────────────────────────────────────────────┘ │
│ ADA: About 870 GiB free on ada-data…           │
│ ─ stop=completed steps=1 ─                     │
```

Mode row: clear chips `mode=observe` · `auth=session|mesh` · `agent_armed` · last denial one-liner (not full JSON dump).

### P2 — x-ray + preview

```text
┌──────────────┬──────────────────┬────────────────────────────┐
│ X-RAY roots  │ List             │ Preview                    │
│ • memory     │ dreams/          │ # Dream digest (2026-08-15) │
│ • runs       │ worldview/       │ …markdown…                 │
│ • outbox     │ cites/           │ [Rendered ▾] [Raw]         │
│              │ 2026-08-15.md    │ cites: cite:c_…            │
└──────────────┴──────────────────┴────────────────────────────┘
```

Entry: tab or “X-ray” beside Audit — does **not** replace chat as default home.

---

## 9. Phased roadmap + API deltas

### 9a. Already shipped (2026-08-15 metal)

| Phase | Shipped |
|-------|---------|
| **P0–P2** | Chat-first grid, vitals cards, tool cards, mode chips, x-ray list/read + md preview |
| **P3 partial** | `last_dream_*` from `dream_status`; campaign hints / brief still OUT |

### 9b. Next wave — packaged agent (with M14) — **plan → implement**

| Phase | Ships | Does not ship |
|-------|-------|---------------|
| **P0′** | **CSS pack** polish; **chat = sole home**; **[Body]** drawer (vitals/lifecycle/x-ray/audit); session welcome chrome; manifest/icons hook | Next rewrite; menu-bar app |
| **P1′** | Plan **ask card + Accept/Revise**; Agent **Confirm/Deny** inline (M14); optional tool summary | Voice; Funnel; editors |
| **P2′** | Optional: urgent one-line fault badge when Body closed; stop/cancel if harness allows | Always-listen; pretext face |

**API deltas (prefer reuse)**

| When | Change |
|------|--------|
| P0′ | Mostly client IA/CSS; optional `manifest.webmanifest` static |
| P1′ | May need thin confirm API or confirm-via-chat turn — **must** bind to gateway `{tool,args}` (see M14 §9) |
| Later | SSE `needs_confirm` event if not already derivable from tool_finished |

**Stack stays:** FastAPI + Jinja + `app.css` / `app.js`. No Next/React on Pi.

---

## 10. Falsifiers

| # | Falsifier | Pass if |
|---|-----------|---------|
| F1 | Mobile Tailnet | Phone on Tailscale opens Serve URL; usable chat; **no** LAN bind |
| F2 | Doctor parity | Body drawer vitals match `ada body doctor` / organ JSON within tolerance |
| F3 | Funnel impossible | Control plane not on Funnel/public URL |
| F4 | Chat = harness | HUD turn writes same-shaped `runs/` JSONL as `ada chat`; tool cards = gateway args |
| F5 | X-ray deny | Requests under `secrets/` etc. → refuse |
| F6 | Pasted-path honesty | Unchanged vs M12 |
| F7 | No second brain | No parallel agent loop in HUD process |
| F8 | Reduced motion | Motions disable under `prefers-reduced-motion` |
| F9 | Chat is home | Body closed by default; stream+composer own first viewport |
| F10 | Packaged CSS | Moss pack applied; Dock window does not read as bare ops site |

---

## 11. OPEN for Aryan — **resolved for next wave**

| # | Was | Now |
|---|-----|-----|
| 1 | Density strip vs cards | **Body drawer** denser cards; no always-on strip as home |
| 2 | Raw JSON depth | **Inside Body** audit disclosure |
| 3 | X-ray roots | Keep three roots (memory/runs/outbox) unless later card expands |
| 4 | Md vs raw default | Rendered default (existing) |
| 5 | Brand voice | Slightly warmer welcome OK; no consciousness lie — see M14 |
| 6 | First implement | **P0′+P1′ with M14** in one coding chat |
| 7 | Tool summary | Optional in P1′; not blocking |

**Residual:** drawer label `Body` (recommended) vs `HUD` — pick at implement start.

---

## 12. Ordered implement-next (with M14)

**Ready to plan.** After plan review, one coding chat:

1. Restart long-lived `ada hud serve` when measuring.  
2. **P0′:** CSS pack + chat-home layout + Body drawer; session welcome; manifest; Mac open script (M14).  
3. Smoke F1, F9, F10, F2 (Body open), F3.  
4. **P1′:** Plan Accept card + Agent Confirm (M14 §9); smoke F4 + Consent Integrity.  
5. **Stop** before Dream editor, WORLDVIEW editor, voice, Funnel, Next-on-Pi.

Full checklist: [`M14_AGENT_SURFACE.md`](./M14_AGENT_SURFACE.md) §13.

---

## 13. Pointer from M03 / to M14

M03 remains the **architecture** card (bind, Serve, five pane *truth sources*, auth, harness). Presentation/IA/phased polish live here. Access, Mac packaging, session welcome, and agent-feel (intent→plan→execute) live in M14:

→ **[`M13_HUD_UX.md`](./M13_HUD_UX.md)** (living surface / chrome).  
→ **[`M14_AGENT_SURFACE.md`](./M14_AGENT_SURFACE.md)** (access · session · Mac · agent interaction).

---

## 14. References

| Kind | Cite |
|------|------|
| Architecture | [`M03_HUD.md`](./M03_HUD.md) |
| Agent surface | [`M14_AGENT_SURFACE.md`](./M14_AGENT_SURFACE.md) |
| Harness | [`M02_CHAT_HARNESS.md`](./M02_CHAT_HARNESS.md); `src/ada/harness/loop.py`, `stream_events.py` |
| Body | [`M00_BODY_SENSE.md`](./M00_BODY_SENSE.md), [`M12_BODY_PROPRIOCEPTION.md`](./M12_BODY_PROPRIOCEPTION.md); `src/ada/body/vitals.py` |
| Dream stubs | [`M11_DREAM_CONSOLIDATION.md`](./M11_DREAM_CONSOLIDATION.md) — digests under `memory/dreams`, `memory/worldview` |
| Code | `src/ada/hud/{app,routes_*,auth,chat_service,stream_bridge}.py`, `templates/index.html`, `static/app.{css,js}` |
| Metal host | Serve `https://ada-pi5.tailbc896a.ts.net` → `127.0.0.1:8787` (2026-08-15) |

---

*End of M13. Shipped P0–P2 metal remains. Next packaged wave (chat home + Body drawer + CSS pack + M14 ask/accept) is locked and ready to plan.*
