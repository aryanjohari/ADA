# M20b — Phone face (structure · design lock)

**Status:** **3b shipped** + **UI taste pass shipped** (2026-08-22) + **composer row fix METAL** (2026-08-23) — phone ingest face on the live HUD. Phone mic is **tap-to-toggle** (not Mac hold). Taste pass §7 **implemented**; composer one-line row **shipped**. **3c Mac+display** → [`M20c_MAC_DISPLAY_FACE.md`](./M20c_MAC_DISPLAY_FACE.md). Not 3d panel catalog. Not phase 4 package.  
**Date:** 2026-08-23 (v1.4)  
**Host:** `ada-pi5` (Raspberry Pi 5, 8 GiB) · window: phone via Tailscale Serve  
**Branch:** `rewrite/v1-body`  
**Kind:** M20 **phase 3b** child — what the phone window **is**, the **layout map**, and **phone-home taste lock** (§7). Not 3c Mac desk. Not 3d remaining panels. Not phase 4 package.  
**Depends on:** [`M20_V1_PRODUCT.md`](./M20_V1_PRODUCT.md) (sequence; this card **is** 3b design) · [`M19b_DAILY_SURFACE_VOICE.md`](./M19b_DAILY_SURFACE_VOICE.md) (faces, preview-then-Send, Confirm on screen — **cite, do not rewrite**) · [`M17_SURFACE_DESIGN.md`](./M17_SURFACE_DESIGN.md) (shared tokens · steel-blue evolution §10 — **not** cyan Jarvis / Iron Man HUD) · [`M15_INTENT_WORK_LOOP.md`](./M15_INTENT_WORK_LOOP.md) (Confirm; Observe/Plan/Agent = permission gates) · [`M20a_VOICE_PATH.md`](./M20a_VOICE_PATH.md) (Pi STT/TTS organs)

**Name stays `M20b_PHONE_FACE.md`:** M19b already owns faces + wedge POLICY. M17 already owns taste. This card only locks the **phone ingest window** so later implement chats can change pieces without guessing.

**Does not supersede:** one `index.html` / `data-face=phone`; same `run_turn`; PTT fills composer then operator Send; Confirm on this window; `?face=` wins.

### Changelog

| Ver | Date | Delta |
|-----|------|-------|
| **v1.4** | 2026-08-23 | **Composer row (phone):** `.chat-form` `flex-wrap: nowrap` + textarea `flex: 1 1 0; min-width: 0` so mic/Send stay in viewport (F-M20b-11). Taste children already styled; form container was the gap. Mac/display untouched. |
| **v1.3** | 2026-08-22 | **UI taste lock (§7):** steel-blue shared tokens (M17 §10); phone chrome map; hide list + motion; calm-UI refs; explicit OUT. Decisions: global palette · confirm = red · hide chips/Today/welcome · small ADA wordmark · Voice Memos mic + conditional Send. **Implemented** in `tokens.css`, `faces.css`, `chrome.css`, `stream.css`, `index.html`, `mode.js`, `voice.js`, `stream.js`. |
| **v1.2** | 2026-08-20 | **Phone PTT tap-to-toggle:** `#chat-mic` click starts / stops STT (Mac hold unchanged). Guard `listening` + `_arming`; queue `_stopWhenReady` if stop fires before MediaRecorder exists (pointerup-during-`getUserMedia` race). Fill `#chat-input` + `dataset.inputKind=stt` + `input` event; empty blob/transcript fail-closed. Prefer `audio/mp4` on phone. No auto-Send. TTS default still off. |
| **v1.1** | 2026-08-20 | **METAL 3b:** phone CSS hide (Body / tools / Plan cards / usage); Ask label (`value=observe`); TTS off by default + `#tts-toggle` in nav; field `data-field-state`; restore stamped face (`localStorage` + `face_hint`; `?face=` still wins). Confirm stays. |
| **v1.0** | 2026-08-20 | Structure lock: phone = ingest organ; METAL vs 3b target; layout map; hide list; falsifiers. No UI code. |

---

## 1. One-liner + IN / OUT

Phone is the **ingest organ** — talk or type, Send, streamed text back, Confirm when a write needs Yes. Same HUD, same cortex, same gateway. Not a second app. Not an ear-only agent.

| IN (this card / 3b) | OUT (explicit) |
|---------------------|----------------|
| One HTML; `html[data-face="phone"]`; same `POST /api/chat` → `run_turn` | New HTML app · Next/React · native shell |
| Composer = text field + mic; **STT on**; no auto-send | Auto-send-on-release · always-listen |
| TTS **off by default**; small **nav** mute/unmute (not a boxed ops dropdown) | TTS always-on · Session-menu ops box as the TTS home |
| Nav: **Observe \| Agent** only (Plan **hidden** on this face). Label may say **Ask**; **mode value stays `observe`** | Renaming gateway mode `observe` → `ask` · collapsing modes |
| Reply = **streamed text only** (smooth `token_delta`). Confirm cards **stay** | Tool/usage/Plan cards on phone · ear-only Confirm |
| State = quiet **field/gradient** (idle / listen / busy / confirm) | Orb / globe / cyan visualizer on phone |
| Camera/OCR + extra views: **PARK** (slots in the map, not shipped) | Shipping camera · Mac desk (3c) · package (4) |

**Confirm lock:** gateway-rendered args on **this** ingress window (constitution + M15 + M19b). Do not move Yes/Deny to another device or to speech.

---

## 2. METAL vs target 3b (honest)

Live files: `src/ada/hud/templates/index.html` · `static/css/faces.css` · `static/js/face.js` · `device.js` · `voice.js` · `stream.js` · `mode.js`.

| Piece | METAL now | Target 3b |
|-------|-----------|-----------|
| Shell | One `index.html`; `data-face=phone\|mac\|display`; `?face=` applied in `<head>` | Unchanged |
| Phone CSS | Hides `#ada-orb`, `#view-slot`, `.body-theater`, `.week-chrome`, extra Today chips / `.today-more` / `.today-pulse` | Keep those hides; add stream-clutter + chrome hides below |
| Composer | `#chat-input` + `#chat-mic` (PTT) + `#chat-send`; chips `#composer-chips`; `#voice-speak-chip` while TTS plays | Text + mic + Send. Chips OK as ingest shortcuts. Speak-chip only if TTS enabled **and** speaking |
| STT | **Phone:** tap-to-toggle mic (`click`) → `POST /api/voice/stt` → transcript in `#chat-input` → operator Send (`input=stt`). **Mac:** hold (`pointerdown`/`pointerup`). No auto-send. Empty blob/transcript fail-closed. | Same. Do **not** reuse Mac hold on phone (tap `pointerup` races `getUserMedia`) |
| TTS | On after STT turns (`speakFinal` in `stream.js`); skip `stop=error` / `no_key`; skip if confirm pending | **Off by default.** Opt-in from a **small nav control**. Confirm still never spoken as the Yes path |
| Mode | `#mode-select`: Observe / Plan / Agent (`value=observe\|plan\|agent`) | Plan **hidden** on phone. Observe may **label Ask**; value **`observe`**. Agent still needs HUD login |
| Stream | Turns + `.tool-card` + `.plan-card` + `.turn-footer` usage + `.confirm-card` | Streamed assistant **text** + **confirm cards**. Hide tools / usage / Plan cards |
| Presence | Mac orb `#ada-orb[data-state]`; phone already `display:none` | Phone state on the **field** (`idle` / `listen` / `busy` / `confirm`), not an orb |
| Body / slot | `#body-open` still in chrome; slot hidden by CSS | Hide **Body** on this face. Slot stays hidden (PARK extra views) |
| First-open | `#device-name-dialog` must pick face; Save/Skip stamp `/api/device`; `applyFace` unless `?face=` | Confirm **phone** must **apply** `data-face=phone`. Return visit **restores** that face. **`?face=` still wins** |
| Restore | `sessionStorage ada_hud_face` + UA hint. Registry `face_hint` is stored; **not** re-applied on already-prompted visits | Restore from stamped face when no `?face=` |

**Verdict:** phone is a CSS hide + live PTT wedge on the shared HUD. 3b is **chrome + stream discipline + TTS default + face restore** — not a new organ.

---

## 3. Layout map

Same page. Phone **uses** these regions; later chats restyle in place.

```text
  [nav]     brand · Ask/Observe | Agent · TTS mute · session crumb
            (Plan hidden · Body hidden · no ops dropdown as TTS home)
  [field]   quiet ink-steel gradient — state: idle | listen | busy | confirm
  [stream]  token stream only
  [confirm] .confirm-card in-stream when a write needs Yes  (STAYS)
  [composer] #chat-input · #chat-mic · #chat-send
  [park]    camera / OCR — no node yet; do not ship
```

| Region | Job | METAL ids / classes | 3b |
|--------|-----|---------------------|----|
| **Nav** | Mode + session + TTS mute | `header.top` · `.chrome-bar` · `#mode-select` · `#mode-suggest` · `#session-crumb` · `#login-form` · `#session-menu` / `#face-select` · `#body-open` | Thin. Hide Plan option + `#body-open`. TTS = one small control in this bar (new). Face change stays Session overflow |
| **Field** | Quiet presence | `body` moss gradient in `base.css`; `#home` / `.desk-main` / `.home-stream`. No phone field node | Bind voice/turn state to the field (reuse `data-state` idea from `#ada-orb` / `#chat-mic`, **not** a globe) |
| **Stream** | Reply | `#stream.stream` | Text turns; hide `.tool-card`, `.plan-card`, `.turn-footer` usage |
| **Confirm** | Yes/Deny on this window | `.confirm-card` (`js/stream.js` `makeConfirmCard`) | Keep. Field state `confirm` |
| **Composer** | Ingest | `#chat-form` · `#composer-chips` · `#chat-input` · `#chat-mic.mic-btn` · `#chat-send` · `#voice-speak-chip` | Sticky ingest. Mic PTT. Send explicit |
| **Parked camera** | Future OCR / still | — | Slot in this map only. No markup, no route |

First-open overlay `#device-name-dialog` is **not** daily chrome; it is the stamp that must apply/restore phone.

---

## 4. Controls

| Control | Behavior (LOCKED) |
|---------|-------------------|
| **Mic** `#chat-mic` | **Phone: tap-to-toggle** (idle tap starts listen; listening tap stops + STT). **Mac: hold-to-talk** (unchanged). Never Send. Fail-closed if STT misses or blob is empty. Do not start a second recorder while listening / arming. |
| **Send** `#chat-send` | Operator posts composer text through existing `run_turn` |
| **Mode** | Phone shows **Ask** (or Observe) + **Agent**. Hidden: Plan. `select`/`POST` value for Ask **is `observe`**. Agent writes still `requireSessionForMode` |
| **TTS mute** | Default **muted / off**. Small nav control to enable. Not inside a boxed Session/ops dropdown. When off: no `speakFinal`. When on: existing simplex + skip-error rules |
| **First-open** | Operator confirms face. Choosing **phone** must `applyFace("phone")` (`documentElement.dataset.face` + `ada_hud_face`). Skip still stamps hinted/chosen face. **Return:** restore stamped phone without re-prompt. **`?face=` still wins** (do not override query) |

---

## 5. Hidden on `data-face=phone`

Hide (CSS and/or do not render):

- `#ada-orb` (already)
- `#view-slot` (already)
- `#body-open` + Body as a phone home affordance (drawer may exist in DOM)
- `.body-theater` (already)
- Plan **option** on `#mode-select` (mode `plan` unused on this face)
- `.tool-card` · `.plan-card` · usage `.turn-footer`
- Today extras already listed in `faces.css`; do not grow Today into a dashboard
- `#voice-speak-chip` unless TTS is enabled and actually speaking

**Do not hide:** `#stream` text turns · `.confirm-card` · composer field/mic/Send · login when Agent needs a session.

---

## 6. Falsifiers

| ID | Fail if… |
|----|----------|
| **F-M20b-1** | Phone stream shows tool cards, usage crumbs, Plan cards, orb, Body, or view-slot as daily chrome |
| **F-M20b-2** | Confirm is ear-only, spoken as the Yes path, or rendered on another window |
| **F-M20b-3** | A second HTML/app/stack is added “for the phone” |
| **F-M20b-4** | Gateway / `run_turn` mode `observe` is renamed to `ask` (label-only is OK) |
| **F-M20b-5** | Auto-send on PTT stop, or TTS on by default with no nav mute |
| **F-M20b-6** | First-open phone does not apply, or return visit loses phone unless `?face=` (query still wins when present) |
| **F-M20b-7** | Phone mic is press-and-hold; tap-to-talk leaves `#chat-input` empty because `endListen` no-ops before the recorder exists, or a second tap starts a new recorder |

M19b F-M19b-* (preview-Send, one HUD, Confirm bind) still apply.

| ID | Fail if… |
|----|----------|
| **F-M20b-8** | Phone home shows composer chips, Today strip, or welcome line as daily chrome |
| **F-M20b-9** | Phone uses moss-green as primary accent or gold warn on confirm-pending field/card |
| **F-M20b-10** | Phone mic/Send read as boxed ops buttons (not glyph + hairline Send) |
| **F-M20b-11** | Composer wraps or overflows viewport (mic/Send drop bottom-left or leave the visible row) |

---

## 7. UI taste lock (phone home · 2026-08-22)

**Status:** **LOCKED · shipped** — implement chat executed §7 against live `tokens.css` / `faces.css` / `chrome.css` / `stream.css` (2026-08-22). **Composer one-line row METAL** (2026-08-23): phone `.chat-form` stays a single flex row (`nowrap`; textarea `min-width: 0`) so mic/Send never wrap or overflow (F-M20b-11). If iOS keyboard still clips the sticky bar, note only — do not add `visualViewport` unless needed.

**Product read:** Calm personal agent **ingest surface** — closer to **Messages + Voice Memos + Timer** than dashboard or Jarvis. One shared token set (M17 §10); phone ships first; Mac 3c inherits same tokens later.

**Locked decisions (from taste brainstorm):**

| # | Decision |
|---|----------|
| 1 | **Palette:** steel-blue replaces moss **globally**; primary `--accent: #6d8f9c`. Phone first; Mac 3c inherits — not a phone-only skin. |
| 2 | **Confirm color:** confirm-pending **field gradient + `.confirm-card` rail** use **`--deny` red**; listen/busy/idle use steel. No gold `--warn` on phone home. |
| 3 | **Composer chips:** **hidden entirely** on phone home (`#composer-chips`). |
| 4 | **Header:** **small quiet ADA** wordmark (`~0.9rem`); hide `#welcome-line` and `#today-strip`. Nav = Ask \| Agent · TTS glyph · Session overflow. |
| 5 | **Mic + Send:** **Voice Memos** pattern — circular **mic glyph**; **Send** = text/hairline control, visible/enabled only when composer is non-empty. |
| 6 | **Composer row:** one line always — `#chat-input` · mic · Send. Shared `.chat-form { flex-wrap: wrap }` must not win on phone; textarea shrinks (`flex: 1 1 0; min-width: 0`); mic/Send `flex: 0 0 auto`. |

### 7.1 Shared tokens (≤10)

Evolve M17 moss pack → **near-black + cool steel-blue**. Same names; phone + Mac share one `:root`.

| Token | Lock | Role |
|-------|------|------|
| `--bg` | `#0a0c0e` | Page — near-black |
| `--surface` | `#12151a` | Composer field surface (hairline, not card box) |
| `--line` | `rgba(220, 228, 236, 0.10)` | Hairlines only |
| `--fg` | `#dde3ea` | Body / stream text |
| `--muted` | `#7a8494` | Secondary, idle glyphs, labels |
| `--accent` | `#6d8f9c` | **Steel-blue** — listen state, focus, primary when needed |
| `--user` | `#5a7a88` | User turn rail (optional; may equal accent mix) |
| `--deny` | `#c45c5c` | Deny + **confirm-pending** (field wash + confirm card rail) |
| `--warn` | demote on phone | Non-destructive pending → `--muted`; no gold panels on phone home |
| `--radius` | `6px` | Single radius |

**Drop on phone home:** moss green (`#7fad63`) as default chrome; `--accent-dim` filled buttons on mic/Send; bordered control boxes on nav; dual radial page washes.

Compat aliases (`--bg1`, `--surface-2`, etc.) may remain for Body/drawer; phone home should not introduce new token names.

### 7.2 Phone chrome map

```text
┌─────────────────────────────────────────┐
│ ADA   Ask|Agent · TTS◌ · Session       │  ~2.5rem · hairline bottom only
├─────────────────────────────────────────┤
│                                         │
│  [field — full-bleed gradient layer]    │
│       idle | listen | busy | confirm    │
│                                         │
│  [stream]  token text · minimal rails   │
│  [confirm] .confirm-card when write Yes │
│                                         │
│  [composer sticky · safe-area]          │
│    textarea (hairline) · mic◌ · send    │
└─────────────────────────────────────────┘
```

| Region | Visible | Hidden / overflow |
|--------|---------|-------------------|
| **Nav** | Small **ADA** wordmark; segmented **Ask \| Agent** (hairline, not boxed `<select>`); **TTS glyph** (off default); **Session** `<details>` (face, logout, login when Agent needs session) | Plan, Body, `#mode-suggest`, `#welcome-line`, `#session-crumb` as peer pill (detail → Session only), `#auth-msg` except transient error |
| **Field** | `html[data-field-state]` → slow gradient on page/home layer | Orb, view-slot, body-theater |
| **Stream** | `#stream` text turns; `.confirm-card` | `.tool-card`, `.plan-card`, `.turn-footer`; heavy card chrome; optional hide `.who` labels |
| **Composer** | `#chat-input`, `#chat-mic`, `#chat-send` | `#composer-chips`; `#voice-speak-chip` unless TTS on + speaking |
| **Today** | — | Entire `#today-strip` |

**Field states (`data-field-state` on `html`):**

| State | Gradient cue | Color family |
|-------|--------------|--------------|
| `idle` | Flat near-black | `--bg` / `--bg1` |
| `listen` | Soft steel wash top → `--bg` | `--accent` mix ~8–10% |
| `busy` | Subtle depth shift (no pulse) | `--bg` / `--surface` |
| `confirm` | Soft red wash top → `--bg` | `--deny` mix ~10–12% |

Transition: **400–600ms** ease (not current 280ms snappy crossfade).

### 7.3 Type (phone)

| Rule | Lock |
|------|------|
| Family | **IBM Plex Sans** 400/600 only — no new display font |
| Stream | `1rem`, line-height **1.55** |
| Chrome | `0.8125rem`, letter-spacing **+0.02–0.04em** — quiet retro-machine |
| Mono | Confirm args, tool names, receipts **only** — not nav decoration |

### 7.4 Components (phone home)

| Component | Spec |
|-----------|------|
| **Mode** | Segmented Ask \| Agent; values `observe` \| `agent`; Plan option hidden |
| **TTS** | Nav **glyph** (speaker off/on); default off; not uppercase text chip in a box |
| **Mic** `#chat-mic` | **Circular glyph** (inline SVG or existing ada-icon derivative); tap-to-toggle unchanged; listen = steel accent on glyph + field state — **no pulsing ring loop** |
| **Send** `#chat-send` | Hairline / ghost text; **hidden or inert when empty**; steel or fg when actionable — not green filled primary |
| **Stream turns** | Plain text; left rail **optional hairline** or none; demote green assistant rail |
| **Confirm card** | Keep in stream; **left rail + title cue = `--deny`**; Confirm/Deny button pair unchanged in behavior |

### 7.5 Motion (≤3 · phone)

1. **Stream enter** — opacity + 4px rise, ≤180ms (keep M17).
2. **Field state** — background gradient crossfade **400–600ms** `var(--ease)`.
3. **Composer focus** — hairline border color only; **no pulse loop**.

Honor `prefers-reduced-motion: reduce` — instant state snap; no decorative loops.

### 7.6 Calm UI references (steal / reject)

| Ref | Steal | Reject |
|-----|-------|--------|
| **Messages** | Composer owns bottom; stream scrolls; chrome defers | Stickers, bubble theater, channel list home |
| **Voice Memos** | Dark field, round record control, state on canvas not chrome | Waveform visualizer, scrubber UI |
| **Clock / Timer** | Slow active-state wash | Countdown animation, ticking loops |
| **Iron Man / NOC / cyan HUD** | — | Orbs, globes, glass stacks, dashboard columns |

### 7.7 Hidden on phone home (extends §5)

Already hidden per §5, plus for taste pass:

- `#welcome-line`
- `#today-strip` (entire strip, not only extras)
- `#composer-chips`
- Box borders on mode dial / TTS — replace with segmented hairline + glyphs
- Moss green listen/assistant accents — steel only except confirm red

**Do not hide:** `#stream` text · `.confirm-card` · composer field/mic/Send · login when Agent requires session.

### 7.8 Explicit OUT (this taste pass)

- New HTML / second app / Next/React on Pi
- Icon packs / component libraries (inline SVG glyphs or existing `ada-icon.svg` only)
- Session threads UI
- clarify-Okay halt flow
- Campaigns / Today dashboard on phone
- Orb / waveform / cyan visualizer
- Auto-send PTT · TTS on by default · light theme
- Camera/OCR (PARK)

### 7.9 Implement-next (taste pass code)

1. `tokens.css` — M17 §10 steel-blue values; retire moss as `--accent`.
2. `faces.css` — phone field gradients (steel listen, red confirm, slow transition); phone hides (welcome, Today, chips).
3. `chrome.css` — phone nav: small brand, segmented mode, TTS glyph styling.
4. `stream.css` — phone composer: circular mic, conditional Send, hairline textarea; quiet stream rails.
5. `mode.js` / minimal markup — only if segmented control cannot be pure CSS on existing `#mode-select`.

**Done when:** phone home reads as **ingest organ** (F-M20b-8–10); Mac can adopt same tokens in 3c without a second palette.

---

## Changelog + implement-next

This card is **phase 3b design**. Code is a later chat.

1. **This card (done):** lock ingest organ + layout map vs live METAL.  
2. **Implement chat (3b code):** **done** — phone CSS/JS on the existing HUD.  
3. **Phone PTT tap-to-toggle (v1.2):** **done** — `voice.js` click path + `_arming` / `_stopWhenReady`; Mac hold unchanged.  
4. **UI taste pass (v1.3):** **shipped** §7 — tokens + phone CSS/JS on live HUD.  
5. **Composer row (v1.4):** **METAL** — phone `.chat-form` nowrap + textarea `min-width: 0` (F-M20b-11).  
6. **Not this slice:** 3c Mac desk · 3d remaining life panels · phase 4 package · campaigns · clarify-Okay halt.

**Do not start here:** camera/OCR, new `index`, mode-collapse, always-listen, cyan Jarvis presence.

---

*End M20b phone-face structure + taste lock. M17 §10 shared tokens; M19b unchanged; cite them.*
