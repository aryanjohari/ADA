# M03 — HUD / Control-plane Web UI (Tailscale Serve)

**Status:** module research card (**complete for coding** — **metal shipped:** `src/ada/hud/` ASGI + Serve path; presentation evolved in [`M13_HUD_UX.md`](./M13_HUD_UX.md))  
**Date:** 2026-08-12  
**Host:** `ada-pi5` (Raspberry Pi 5 Model B Rev 1.1, Debian trixie, ~8 GiB RAM)  
**Branch:** `rewrite/v1-body`  
**Depends on:** [`../00_ASSISTANT_RESEARCH.md`](../00_ASSISTANT_RESEARCH.md) §§1–4 & §7–8, [`../01_BODY.md`](../01_BODY.md) §7 & §10.8–9, [`../02_CONSTITUTION.md`](../02_CONSTITUTION.md) §§6, 11, 13–14, [`M00_BODY_SENSE.md`](./M00_BODY_SENSE.md), [`M01_NETWORK_ACCESS.md`](./M01_NETWORK_ACCESS.md), [`M02_CHAT_HARNESS.md`](./M02_CHAT_HARNESS.md)  

**Slice rule:** this card admits **design** of the Tier A control-plane HUD — localhost-bound web app, Tailscale Serve exposure, five locked panes, chat that drives the **existing** harness, and auth stance. It does **not** admit Funnel, pretext face, Dream manage UI, WORLDVIEW editor, voice, sandboxed shell, or a second cortex implementation.

**Living surface / UX (presentation + IA + phased polish):** [`M13_HUD_UX.md`](./M13_HUD_UX.md) — M03 stays architecture authority.  
**Access / session / Mac packaging / agent-feel:** [`M14_AGENT_SURFACE.md`](./M14_AGENT_SURFACE.md).

**Operator locks carried forward:** Tailscale-only control plane; Serve OK / Funnel NO; bind `127.0.0.1`; body §7.2 panes frozen; harness `stream_events` + `runs/` JSONL are the stream of truth; CLI `ada chat` remains valid; body numbers must match `ada body doctor` / organs.

**METAL (shipped):** `src/ada/hud/` FastAPI ASGI (`ada hud serve` → `127.0.0.1:8787`); Tailscale Serve path; chat → harness `run_turn`. Presentation / IA: [`M13_HUD_UX.md`](./M13_HUD_UX.md).

---

## 1. Question / goal / slice admission boundary

**Question.** How does Aryan get a **mobile-usable, truthful control plane** on the phone/laptop — stream + vitals + lifecycle + mode + raw receipts — over the private Tailnet, without opening the LAN/WAN, without forking a second chat brain, and without cosplaying a product design system?

**Goal (M03 HUD design).**

1. Specify a **local web app** bound to `127.0.0.1` (or equivalent loopback), reached via **Tailscale Serve** + MagicDNS HTTPS.  
2. Lock rendering to body **§7.2 panes** (stream, vitals, lifecycle, mode+perms, raw run tail).  
3. Wire UI to M02 **`StreamSink` callbacks** and/or **`runs/` JSONL** — same receipts as CLI.  
4. Chat input calls existing **`run_turn` / `ChatSession`** — one cortex, two channels.  
5. State **auth stance**: Tailnet presence minimum; recommend whether an **app session secret** is required in v1.  
6. Prefer a **boring Pi-feasible stack** (one ASGI choice + SSE + plain HTML).  
7. Name acceptance smokes that falsify LAN expose, Funnel, and vitals drift vs doctor.

**Admission boundary (in / out)**

| IN this slice (design now → code later) | OUT (later cards / later code) |
|----------------------------------------|--------------------------------|
| Localhost ASGI HUD + Tailscale Serve | Funnel / public URL |
| Five locked panes (§7.2) | Pretext face / heavy design system |
| SSE (or thin WS) of harness stream events | True Gemini token-by-token if SDK path not ready — whole-turn deltas OK |
| Chat → existing `harness.loop.run_turn` | Second agent / LangGraph / Node SSR product |
| Vitals/lifecycle APIs → M00 organs | Dream manage UI, S3, WORLDVIEW editor |
| Mode + denial display; session auth design | Voice; sandboxed shell |
| Mobile-usable plain UI | Replacing Tailscale with custom VPN |
| Eval: MagicDNS Serve; not `0.0.0.0`; doctor match | systemd polish as **gate** (unit pointer OK) |

```text
  Aryan phone/laptop (Tailscale ON)
        |
        | HTTPS MagicDNS  (Serve — tailnet only)
        v
  [tailscale serve] ----proxy----> 127.0.0.1:<port>
                                        |
                                        v
                                   [ada.hud ASGI]
                                        |
           +----------------------------+----------------------------+
           |                            |                            |
           v                            v                            v
    body organs (M00)          harness.loop (M02)            runs/*.jsonl
    vitals/identity/lifecycle  CallbackSink → SSE            same receipts as CLI
```

---

## 2. Lens tags

| Tag | What it means here |
|-----|--------------------|
| **FANFICTION** | Holographic face, cinematic HUD chrome, “always watching” presence — **deferred skin**. Truth panes first. |
| **EVIDENCE** | Tailscale Serve + localhost bind; mesh-as-auth vs app password; SSE vs WebSocket for agent streams; Consent Integrity for tool cards |
| **FEASIBLE** | Pi 5 8GB: thin Python ASGI + static/Jinja UI; no Node/Next; no GPU UI; HDD for logs |
| **POLICY** | Tailscale-only; Serve OK; Funnel NO; privacy rings; Agent writes need session auth; she/her in copy |
| **METAL** | Existing `src/ada/{body,harness,runs,cli}`; Tailscale present; FastAPI not installed; runs JSONL already written by CLI |

---

## 3. What this slice is *not*

| Concept | Meaning in ADA | This slice |
|---------|----------------|------------|
| **Control-plane HUD** | Operator UI over Tailnet | **IN (design)** |
| **Cortex** | Gemini + tool loop | **CALL** existing M02 — do not reimplement |
| **Body organs** | Metal vitals / birth / lifecycle | **CALL** M00 — HUD is a viewer + chat shell |
| **Delight / pretext face** | Later skin over **same** stream ([body §7.2](../01_BODY.md)) | **OUT** |
| **Dream manage / WORLDVIEW** | Offline consolidate + digests | **OUT** — lifecycle pane may show **stub** `last_dream_*` / `push=skipped` |
| **Public presence** | Funnel / WAN | **Forbidden** |

**FANFICTION trap:** “the web UI *is* ADA.”  
**Engineering rule:** the UI is a **channel** (`channel.web`). Continuity lives in organs + `runs/` + later memory — same as CLI ([research §1](../00_ASSISTANT_RESEARCH.md); constitution §2).

---

## 4. Prior art survey (light) — what practice is telling us

### 4.1 Tailscale Serve + local apps

| Source | Claim / practice | ADA takeaway |
|--------|------------------|--------------|
| **Tailscale Serve docs** — [Serve](https://tailscale.com/docs/features/tailscale-serve) | Proxy tailnet HTTPS → local port; injects identity headers; **Funnel ≠ Serve** | Chosen exposure path (M01 already locked) |
| **Serve identity headers tip** | If you trust `Tailscale-User-*`, **bind localhost** — else LAN peers can spoof headers | **Hard rule:** `127.0.0.1` only |
| **datasette-auth-tailscale** — [plugin](https://github.com/datasette/datasette-auth-tailscale) | Pattern: Datasette on `127.0.0.1` + `tailscale serve`; Funnel users lack headers | Same shape for ADA HUD |
| **M01 card** | Serve OK; Funnel NO; DHCP LAN is not identity | Do not bind `0.0.0.0` “for phone convenience” |

**EVIDENCE verdict:** personal lab UIs behind Serve are a solved ops pattern. Security lives in **bind address + Serve ≠ Funnel**, not in inventing a VPN.

### 4.2 Mesh = auth vs app password (zero-trust lite)

| Stance | When it works | Failure mode |
|--------|---------------|--------------|
| **Mesh presence only** | Solo tailnet; ACL = Aryan devices; Observe reads | Stolen laptop still logged into Tailscale; overshared device; “any peer = sovereign” |
| **Mesh + identity header allowlist** | Soft check `Tailscale-User-Login` matches Aryan | Headers only trustworthy via Serve→localhost; tagged nodes may lack headers |
| **Mesh + app session secret** | Agent writes / irreversible tools | Extra friction; secret must live outside git |

Constitution §11 already splits this: **Observe may stay mesh-gated**; **Agent writes require `auth.session`**. Privacy literature treats personal agents as high-permission data paths ([Agents That Know Too Much, 2026](https://arxiv.org/html/2606.26627)) — the control plane is ring 1, not “private enough because WireGuard.”

**Recommendation (locked for this card — see §8):**  
- **v1 Observe (default):** Tailnet presence via Serve + localhost bind is **enough**. Optionally display / soft-check `Tailscale-User-Login` when present.  
- **v1 Agent from HUD:** **yes — require an app session secret** (password → HttpOnly cookie / signed session). Do **not** treat “on my Tailnet” as Agent authority.  
- **Pragmatic alternate (also OK):** HUD v1 is **Observe-only**; Agent remains CLI/SSH (M02 local operator-equivalent) until session secret ships. Prefer this only if coding time is short — **do not** expose Agent mode in the HUD without the secret.

### 4.3 Streaming chat UIs — SSE vs WebSocket

| Pattern | Fit for ADA v1 | Notes |
|---------|----------------|-------|
| **SSE (server → client)** | **Preferred default** | Matches one-way token/tool events; simple through Serve HTTP; mobile-friendlier than always-on WS ([SSE vs WS agent streaming practice](https://tanayshah.dev/blog/sse-vs-websocket-agent-streaming/)) |
| **POST + SSE body** | Common for chat | Browser `EventSource` is GET-only; use `fetch` ReadableStream or `sse-starlette` |
| **WebSocket** | Later / optional | Better when mid-stream confirms need bidirectional pause; auth via query/cookie is fiddlier |
| **Polling JSONL only** | Fallback for raw log pane | Good for audit tail; laggy for live stream |

**Consent Integrity:** tool cards must show gateway `{tool, args}` from `tool_call_started` / JSONL `tool_call`, never model prose alone ([Consent Integrity, 2026](https://arxiv.org/abs/2606.02668); M02 §6.2).

### 4.4 Personal-agent UIs (what to steal / skip)

| Borrow | Skip |
|--------|------|
| Structured event types: text / tool_start / tool_end / usage / fault | ChatGPT clone chrome, sidebar memory browsers |
| Side panes for host truth (vitals) separate from chat | Multi-tenant SaaS auth stacks |
| Degraded mode when cortex down (vitals still live) | SPA frameworks that need a Node build on the Pi |

---

## 5. Options compared → chosen stack

### 5.1 Web framework / process

| Option | Pros | Cons on Pi lab | Verdict |
|--------|------|----------------|---------|
| **FastAPI + uvicorn + Jinja2** | Familiar; OpenAPI optional; ASGI SSE; pydantic already in tree | One new dep family | **Chosen** |
| Starlette alone | Thinner | Less sugar for forms/validation | Acceptable twin; FastAPI preferred for route clarity |
| Flask + sync | Simple | Streaming + concurrent vitals/chat clunkier | Won’t-chase |
| Django | Batteries | Heavy for five panes | Won’t-chase |
| Next.js / React SSR | Polished UI | **No Node** on host; RAM/teach tax; wrong for lab slice | **Won’t-chase** |
| Streamlit / Gradio | Fast demos | Opaque; hard Tailscale/auth story; not pane-locked | Won’t-chase |

### 5.2 Front-end

| Option | Verdict |
|--------|---------|
| **Server-rendered HTML + small vanilla JS (or HTMX)** | **Chosen** — mobile usable, no build step, teachable |
| React/Vite SPA | Won’t-chase for v1 |
| Pretext canvas / WebGL face | Explicitly OUT |

### 5.3 Live stream transport

| Option | Verdict |
|--------|---------|
| **SSE from `CallbackSink` fan-out** | **Chosen** for stream pane + chat progress |
| WebSocket duplex | Defer until confirm-dialog pause needs it |
| Poll-only | OK for vitals (2–5s) and raw log tail; not sole stream path |

### 5.4 Chosen architecture (boring, Pi-hard)

```text
src/ada/hud/                 # NEW — design only in this card
  app.py                     # FastAPI app factory
  routes_api.py              # /api/vitals, /lifecycle, /mode, /run/tail, /chat
  routes_pages.py            # GET /  → Jinja shell
  auth.py                    # mesh gate + optional session secret
  stream_bridge.py           # CallbackSink → asyncio queue → SSE
  templates/index.html       # five panes + chat form
  static/{app.css,app.js}    # plain, mobile-first

CLI:  ada hud serve --host 127.0.0.1 --port 8787
Ops:  tailscale serve --bg 8787   # or current Serve CLI equivalent
```

**Deps to add (when coding):** `fastapi`, `uvicorn[standard]`, `jinja2`; optional `sse-starlette`; **no** Node.

**FEASIBLE:** one uvicorn worker, localhost only, <100 MiB RSS class — negligible next to Gemini egress cost and HDD logs.

**Harder-but-correct vs shortcut**

| Shortcut | Harder-correct (chosen) |
|----------|-------------------------|
| Bind `0.0.0.0` so phone hits LAN IP | Bind `127.0.0.1` + Serve |
| Funnel “so I don’t need Tailscale on phone” | Install Tailscale on phone; Serve private |
| Duplicate chat logic in the web layer | Call `run_turn` / `ChatSession` |
| Pretty dashboard cards without doctor parity | Vitals pane = organ JSON subset; smoke vs `ada body doctor` |
| Agent mode with mesh-only auth | Session secret for Agent (or Observe-only HUD) |

---

## 6. Pane contract (body §7.2 — locked)

| # | Pane | Data source (single truth) | Refresh |
|---|------|----------------------------|---------|
| 1 | **Stream** | Live `StreamSink` events: `token_delta`, `tool_call_started`, `tool_call_finished`, `usage_update` | SSE during turn |
| 2 | **Body vitals** | `collect_vitals()` — temp, throttle, disks (`/`, `/mnt/ada-data`), net, `mounts.ada_data_ok`, `probe_errors` / urgent | Poll 2–5s (or light SSE heartbeat) |
| 3 | **Lifecycle** | `load_identity()` → `born_at`; last `wake` / `fault` from lifecycle ledger; **dream stub OK** (`last_dream_at`/`status` absent → show `n/a` or `push=skipped`) | Poll ~10s |
| 4 | **Mode + perms** | Session `mode`; last `tool_denied` from current run / in-memory denials; **session auth state** (anonymous mesh vs authenticated Agent) | On event + poll |
| 5 | **Raw log tail** | Tail of current session JSONL under `/mnt/ada-data/runs/<date>/<session_id>.jsonl` | Poll 1–2s or SSE mirror |

**Deferred (body §7.2):** memory-hit inspector; full token/egress meter chrome — may show raw `usage_update` lines in stream/mode without inventing a billing product.

**Stream honesty note (METAL):** today’s `loop.py` emits `token_delta` with **whole assistant text** after a generate round (not true partial tokens). HUD must render that as stream text / cards correctly; finer Gemini streaming is a later harness enhancement, not a HUD blocker.

**Chat input:** POST message → same `Gateway` + `GeminiAdapter` + `RunWriter` as `ada chat`. Session id shown in UI; path emitted via `session_receipt_path`.

**Degraded mode:** if Gemini key missing / API down — vitals + lifecycle + raw log still work; chat returns fail-closed with receipt (`no_key` / fault), matching M02 and body §10.9.

---

## 7. Wiring to M02 (do not fork the cortex)

### 7.1 Event map (already sketched in M02 §7.3)

| Event | HUD pane | Notes |
|-------|----------|-------|
| `token_delta` | Stream | Append text bubble / running assistant block |
| `tool_call_started` | Stream tool card | Render **gateway** tool + args |
| `tool_call_finished` | Stream tool card result | `ok`, `receipt_id`; expand observation from JSONL if needed |
| `usage_update` | Stream footer / mode | Labeled estimate OK |
| `mode_info` | Mode pane | observe / agent / plan |
| `session_receipt_path` | Raw log | Open/tail that file |

### 7.2 Bridge sketch

```text
CallbackSink.on(fn)  →  thread-safe queue  →  SSE generator per browser client
RunWriter.append(*)  →  durable audit (always)
JSONL tail endpoint  →  pane 5 independently recoverable after refresh
```

Rules:

1. **JSONL is audit; SSE is UX** — refresh must be able to rebuild cards from the run file.  
2. HUD process may host **one active ChatSession** (v1) or a small session map keyed by cookie — do not spawn silent parallel cortices.  
3. CLI and HUD must not corrupt the same JSONL writer concurrently — **v1 assumption:** one interactive writer (document; optional flock later).  
4. Confirm dialogs (when write tools exist): bind to gateway pending `{tool, args}` (M02 §13).

### 7.3 Body APIs (viewer, not re-probe inventively)

| Endpoint (sketch) | Calls |
|-------------------|-------|
| `GET /api/vitals` | `collect_vitals().model_dump()` (+ optional `urgent_faults`) |
| `GET /api/lifecycle` | identity card + last wake/fault events (+ dream stub fields) |
| `GET /api/doctor` | same checks as `ada body doctor` (for smoke parity) |
| `GET /api/run/tail?n=80` | last N JSONL records of current/latest session |
| `POST /api/chat` | `run_turn(...)` + SSE |

---

## 8. Auth stance (v1 recommendation)

| Layer | v1 Observe | v1 Agent (if exposed in HUD) |
|-------|------------|------------------------------|
| Tailscale ACL / device membership | Required | Required |
| Serve (not Funnel) | Required | Required |
| Bind `127.0.0.1` | Required | Required |
| Trust `Tailscale-User-Login` | Optional soft check / display | Soft check OK; **not sufficient alone** |
| **App session secret** | **Not required** | **Required** (cookie after password) |

**Secret storage (when Agent HUD enabled):** e.g. `/mnt/ada-data/secrets/hud.env` (`ADA_HUD_SESSION_SECRET=…`, optional `ADA_HUD_PASSWORD=…`), mode `0600`, never git — same family as `gemini.env`.

**Mode pane must show:** `auth=mesh` vs `auth=session` so the operator can see whether Agent is actually armed.

**POLICY alignment**

| Doc | How M03 satisfies |
|-----|-------------------|
| Body §7.1 | Localhost + Serve; session auth for Agent |
| Constitution §11 | Control plane Tailscale; Agent needs session |
| M01 §7 | Harden ladder steps 10–14 |
| M02 §13 | Subscribe stream; tail JSONL; no Funnel |

---

## 9. Threat model (control-plane focused)

| Surface | Risk | Mitigation |
|---------|------|------------|
| Public internet | Scan / exploit HUD | No Funnel; no WAN port-forward |
| Home LAN | Hit open bind | Bind loopback only |
| Tailnet peer / stolen device | Read chat / trigger Agent | ACL Aryan devices; session secret for Agent; revoke device drill (M01) |
| Header spoof | Fake `Tailscale-User-*` | Localhost bind so only Serve injects |
| XSS in stream render | Tool args / model text inject | Escape HTML; treat stream as untrusted text |
| Second cortex / dual writers | Divergent receipts | One harness entrypoint; one session writer |

---

## 10. Package / CLI layout proposal

Extends M00/M02 — no second tree.

```text
src/ada/
  hud/                 # NEW
    __init__.py
    app.py
    auth.py
    stream_bridge.py
    routes_api.py
    routes_pages.py
    templates/
    static/
  harness/             # EXISTING — loop, stream_events, session
  body/                # EXISTING
  runs/                # EXISTING
  cli/main.py          # add `ada hud` / `ada hud serve`
tests/
  test_hud_bind_localhost_default.py
  test_hud_vitals_matches_organ_schema.py
  test_hud_chat_uses_run_turn.py
  test_hud_agent_requires_session.py
  test_hud_sse_emits_tool_cards.py
```

**CLI UX (locked intent):**

```text
ada hud serve --host 127.0.0.1 --port 8787
ada hud serve --host 0.0.0.0 …     # must refuse or require explicit unsafe flag that still fails acceptance
```

**Ops companion (not Python):**

```text
# after HTTPS enabled in tailnet DNS (M01)
tailscale serve --bg 8787
tailscale serve status          # expect proxy to 127.0.0.1; funnel off
```

Exact Serve CLI flags evolve with Tailscale versions — verify with `tailscale serve --help` on metal at implement time ([Serve docs](https://tailscale.com/docs/features/tailscale-serve)).

---

## 11. Learning objectives + falsifiers

### Learning objectives (Aryan should explain out loud)

1. Why **Serve ≠ Funnel** and why HUD binds **localhost** even though the phone URL is MagicDNS HTTPS.  
2. Why **mesh presence ≠ Agent authority** (constitution session auth).  
3. How the HUD and `ada chat` share **one** harness and **one** receipt log.  
4. Why tool cards must show **gateway args**, not model summaries.  
5. Why vitals in the pane must match **`ada body doctor` / `df` / `vcgencmd`**, not a decorative gauge.  
6. When SSE is enough and when WebSocket would earn its complexity (mid-stream confirms / voice later).

### Falsifiers (slice not done if…)

- HUD listens on `0.0.0.0` / LAN IP and is reachable without Tailscale.  
- Funnel enabled / public URL works for the control plane.  
- Chat path invents answers without `runs/` receipts (or a parallel “web cortex”).  
- Vitals disagree with `ada body doctor` / metal beyond tolerance (body §10.2).  
- Agent mode available in HUD with **no** session secret (unless HUD is explicitly Observe-only).  
- Pretext face / Dream editor / WORLDVIEW UI shipped as a gate.  
- Only a screenshot demo — **no** pytest for bind default + chat wiring + auth gate.

### Egress impact (research §8 field)

| Ring | Touched by M03? |
|------|-----------------|
| **Control plane (Tailscale)** | **Yes** — Serve HTTPS; identity headers; ACL |
| **Cortex (Gemini)** | **Yes, same as CLI** — chat turns only; no new egress class |
| **Backup (`dream.push`)** | **No** |
| **Local durable** | **Yes** — reads vitals/lifecycle; appends `runs/` via harness |

---

## 12. Acceptance / proof checklist (eval)

Run on **Pi** unless noted.

### 12.1 Reachability & exposure

- [ ] `ada hud serve` defaults to `127.0.0.1`; process listen confirmed via `ss`/`lsof`.  
- [ ] From Tailnet client: MagicDNS Serve URL loads HUD over HTTPS.  
- [ ] From LAN **without** Tailscale: cannot open HUD on Pi’s `192.168.x` (or connection refused).  
- [ ] `tailscale serve status` shows proxy to localhost; **Funnel off**.  
- [ ] Body §10.8 satisfied for UI exposure.

### 12.2 Pane truth

- [ ] Vitals pane temp / disk / throttle / mount agree with `ada body doctor` + `vcgencmd`/`df` within tolerance.  
- [ ] Lifecycle shows real `born_at` and last wake/fault (dream stub OK).  
- [ ] Mode pane shows Observe/Agent/Plan + auth state; denials appear when forced.  
- [ ] Raw log tail matches the session file under `/mnt/ada-data/runs/…`.

### 12.3 Chat = same cortex

- [ ] Send “how is the body?” from HUD → tool cards + answer; JSONL contains matching `tool_call` / `tool_result`.  
- [ ] Same question via `ada chat -q` produces comparable receipt shape (not bit-identical session ids).  
- [ ] Cortex down / no key → vitals panes still live; chat fail-closed with receipt.

### 12.4 Auth

- [ ] Observe works with Tailnet-only (no password) **or** documented Observe-only policy.  
- [ ] If Agent selectable in HUD: blocked until session secret; Mode pane reflects `auth=session`.

### 12.5 Doc / lab gate

- [ ] This card exists under `docs/modules/`.  
- [ ] Implementation follows card; no Funnel “just to demo.”

---

## 13. Won’t-chase vs robust-on-Pi

| Won’t-chase this slice | Why |
|------------------------|-----|
| Funnel / Cloudflare Tunnel as control plane | POLICY; public attack surface |
| Pretext face / design-system spa | Delight later; same stream |
| Next.js / Node toolchain on Pi | Not installed; RAM/teach tax |
| WebSocket-first architecture | SSE covers v1 stream; WS later for confirms/voice |
| Dream manage UI / S3 / WORLDVIEW editor | Separate cards |
| Voice / PTT | Tier B |
| Sandboxed shell / file edit tools | Later actuators |
| Custom WireGuard / Headscale replace Tailscale | M01 chose Tailscale |
| Multi-user household profiles | Constitution later |
| Perfect ambient sensorium inject each paint | Poll organs; force tool receipts for claims |
| Grafana/Prometheus HUD | Homework later; not Tier A gate |
| Concurrent multi-writer sessions / HA HUD | Single-operator lab assumption |

| Robust-on-Pi (do these) | Why |
|-------------------------|-----|
| Localhost bind + Serve | Real privacy boundary |
| Organ-backed vitals | Body §10.2 |
| Shared harness + JSONL | One truth |
| Escape stream HTML | XSS |
| Degraded vitals without Gemini | Body §10.9 |
| Explicit Agent session secret (or Observe-only) | Constitution §11 |
| pytest for bind/auth/wiring | Lab hygiene |

---

## 14. Ordered “do this next” (implement — still no code in *this* pass)

1. **Locks already resolved below (§15)** — proceed when coding.  
2. **Deps:** add `fastapi`, `uvicorn`, `jinja2` (+ optional `sse-starlette`) to `pyproject.toml`.  
3. **`ada.hud.app`** — bind default `127.0.0.1:8787`; refuse casual `0.0.0.0`.  
4. **Read APIs** — vitals / lifecycle / doctor parity; Jinja shell with five panes (plain CSS, mobile width).  
5. **`stream_bridge`** — wrap `CallbackSink` → SSE; render tool cards from gateway payloads.  
6. **`POST /api/chat`** — construct `ChatSession` + call `run_turn` (no fork).  
7. **Auth** — implement chosen lock: Observe mesh-only; Agent requires session secret **or** hide Agent in HUD.  
8. **Ops:** enable tailnet HTTPS if needed; `tailscale serve` → localhost; verify Funnel off.  
9. **pytest + manual §12 smokes** on metal (phone + laptop).  
10. **Do not start** Funnel demos, pretext face, Dream UI, or shell tools as part of “HUD done.”

---

## 15. Operator decisions — **resolved** (2026-08-12 research)

| Topic | Lock |
|-------|------|
| Exposure | `127.0.0.1` + **Tailscale Serve**; **Funnel NO** |
| Panes | Body §7.2 five panes only |
| Stack | **FastAPI + uvicorn + Jinja2 + vanilla JS/HTMX**; SSE for stream |
| Cortex | Existing `harness.loop.run_turn` only |
| Receipts | Same `runs/` JSONL + `stream_events` |
| UI chrome | Plain mobile-usable; **no** pretext face |
| Auth | Mesh enough for **Observe**; **app session secret required if Agent exposed in HUD**; Observe-only HUD alternate OK |
| Dream in lifecycle | Stub fields OK (`n/a` / `push=skipped`) |
| Token streaming | Whole-turn `token_delta` acceptable until harness streams finer |

**True leftovers before coding (ops, not design forks):**

1. Confirm MagicDNS HTTPS certificates enabled when first running Serve.  
2. Choose Agent-in-HUD **with** password **vs** Observe-only HUD for the first coding weekend (both satisfy POLICY; pick one and don’t waffle mid-PR).  
3. Re-read `tailscale serve --help` on this Pi for current `--bg` / port syntax.

No remaining *design* questions block starting M03 implementation once the Agent-vs-Observe-only coding choice is picked.

---

## 16. Remaining operator questions

Only one real fork remains for the **first coding PR** (not a research gap):

1. **Ship Agent mode in HUD v1 with session password, or Observe-only HUD first?**  
   - Both are constitution-compatible.  
   - Prefer **Observe-only** if the goal is “Serve + panes green this weekend.”  
   - Prefer **Agent + secret** if the mode pane should match CLI `--mode agent` immediately.

Everything else in this card is locked for implementation.

---

## 17. References

### Tailscale / access

- Tailscale Serve — https://tailscale.com/docs/features/tailscale-serve  
- Tailscale Funnel — https://tailscale.com/docs/features/tailscale-funnel  
- MagicDNS — https://tailscale.com/docs/features/magicdns  
- datasette-auth-tailscale (Serve + localhost pattern) — https://github.com/datasette/datasette-auth-tailscale  

### Streaming / agent UI practice

- SSE vs WebSocket for agent streaming (2026 practice writeups) — e.g. https://tanayshah.dev/blog/sse-vs-websocket-agent-streaming/  
- MDN EventSource — https://developer.mozilla.org/en-US/docs/Web/API/EventSource  
- Starlette/FastAPI SSE patterns (`StreamingResponse` / `sse-starlette`) — ecosystem docs  

### Privacy / consent

- *Agents That Know Too Much* (2026) — https://arxiv.org/html/2606.26627  
- Consent Integrity / LITL (2026) — https://arxiv.org/abs/2606.02668  

### Internal ADA docs / code

- [`../00_ASSISTANT_RESEARCH.md`](../00_ASSISTANT_RESEARCH.md) — Tier A channel; §8 card gate  
- [`../01_BODY.md`](../01_BODY.md) — §7 ingress/HUD panes; §10 acceptance  
- [`../02_CONSTITUTION.md`](../02_CONSTITUTION.md) — §11 rings; session auth; §14 voice  
- [`M00_BODY_SENSE.md`](./M00_BODY_SENSE.md) — organs the vitals/lifecycle panes call  
- [`M01_NETWORK_ACCESS.md`](./M01_NETWORK_ACCESS.md) — Serve OK / Funnel NO / localhost  
- [`M02_CHAT_HARNESS.md`](./M02_CHAT_HARNESS.md) — stream hooks §7.3 / §13; `ada chat`  
- Code: `src/ada/harness/stream_events.py`, `harness/loop.py`, `body/*`, `cli/main.py`, `runs/`

---

*End of M03 (research complete for coding). Doc admits HUD / Serve control-plane **design**; it does not admit Funnel, pretext face, Dream UI, or HUD implementation code.*
