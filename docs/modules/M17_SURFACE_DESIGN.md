# M17 — Surface design (clean · minimal · controllable)

**Status:** design-lock card — **P0 + quiet stream shipped** (2026-08-16). Markdown renderer still **P1**.  
**Date:** 2026-08-16  
**Host:** `ada-pi5` · Client: Mac via Tailscale Serve  
**Branch:** `rewrite/v1-body`  
**Depends on:** [`M14_AGENT_SURFACE.md`](./M14_AGENT_SURFACE.md) (chat-home, Body drawer, ASGI+static), [`M13_HUD_UX.md`](./M13_HUD_UX.md) (presentation history), [`M15_INTENT_WORK_LOOP.md`](./M15_INTENT_WORK_LOOP.md) + [`M16_FIRST_PACKAGE.md`](./M16_FIRST_PACKAGE.md) (Plan/Confirm, Today strip, shelf — must stay findable), live `src/ada/hud/`  
**Feeds / sibling:** [`M19b_DAILY_SURFACE_VOICE.md`](./M19b_DAILY_SURFACE_VOICE.md) **v1.6** — life sheets + view registry + PTT preview-then-Send; **device faces** (phone thin / one Mac assistant face / display) over the same ASGI HUD. Does **not** rewrite M17 locks: the Mac assistant face still has a **visible transcript/stream** (chat-home, not dashboard home); companion-as-separate-named-face is retired; density may shift within that one Mac face. Moss tokens and ≤3 motions still bind. Canonical “ADA face” and Iron Man HUD remain OUT.  

**Name justification:** **`M17_SURFACE_DESIGN.md`**. M13/M14 shipped the shell; M16 added daily controls. This card locks **taste + density** so polish chats stop vibe-coding. Not a new organ; not a stack rewrite.

**Product one-liner (LOCKED unless research overturns):** ADA on Mac via Tailscale is a **remote agent home** — calm chat-first control surface. **Not** a fake desktop OS, **not** holographic Jarvis, **not** an ops NOC wall.

**OUT:** Funnel; Next/React on Pi unless EVIDENCE+FEASIBLE+OPEN; voice/wake UI as P0; Pretext face as gate; purple-glow SaaS; Today as peer dashboard column.

```text
  first viewport
  ├─ brand + thin chrome (mode · session crumb · Body)
  ├─ Today strip (0–2 lines; hidden if empty)
  ├─ stream (chat owns height)
  └─ composer (sticky)
  Body drawer → vitals / life / shelf / x-ray / audit
```

---

## 1. METAL inventory (screenshot-level · 2026-08-16)

| Layer | What it is now | Visual / IA problem |
|-------|----------------|---------------------|
| **IA** | Chat-home + `#today-strip` + Body `<dialog>` — correct skeleton (M14/M16) | Chrome still **ops-dense**; first glance can feel like a lab toolbar over chat |
| **Header** | `ADA` + welcome; mode dial; `#mode-suggest`; `auth=` badge; `armed=` chip; password+Login+Logout; Body | **Too many peer controls**; login fields fight brand; mono badges read NOC |
| **Today** | Bordered strip, kind labels, wrap chips | Findable (good). Box + uppercase label still a bit “panel”; must stay **strip**, not grow |
| **Stream** | Left-rail turns; tool/plan/confirm cards; usage footer | Rails + bordered cards + glow on Plan = **dashboard card farm**; assistant is **plain `textContent`** (no calm markdown) |
| **Composer** | Sticky textarea + Send | OK hierarchy; focus glow + accent buttons slightly loud |
| **Body** | Right drawer, tabs, vitals grid, x-ray 3-col | Drawer pattern correct; vitals grid still lab-card dense (OK *inside* drawer) |
| **Tokens** | Moss dark; IBM Plex Sans/Mono self-host; `--max-chat: 44rem`; dual radial bg; `--accent-glow` | Palette family is right; **glow + multi-surface ladder + accent-on-every-button** = glare / vibe-AI |
| **Motion** | `stream-in`, `drawer-in`; `prefers-reduced-motion` present | Count is fine; keep ≤3 intentional |

**Stack conflict:** none required. **Stay** Python ASGI + static (M14 lock). M17 **refines** the moss CSS pack; does not fork framework.

---

## 2. Reference set (steal / adapt / reject)

| Ref | Steal | Adapt | Reject for ADA |
|-----|-------|-------|----------------|
| **Apple HIG** (clarity / deference / depth) | Content first; chrome defers; one primary action | Soft dark “depth” via quiet surfaces, not glass stacks | Literal macOS chrome clone; translucency theater |
| **iMessage / Messages** | Chat owns the field; composer always obvious; minimal chrome | Agent cards (Plan/Confirm/tool) as *exceptions*, not every bubble | Stickers, effects, playful bubbles |
| **Cursor Agent** | Mode/control always reachable; diffs/tools secondary to dialogue | Plan Accept / Confirm as explicit consent affordances | IDE density, file tree as home, neon accents |
| **Claude.ai** | Calm type; wide readable column; restrained chrome | Soft dark moss (our identity) instead of their light default | Marketing hero; purple-glow SaaS; feature walls |

**Anti-references (must not look like):** Grafana/NOC wall; Iron Man HUD / Jarvis OS; Linear-app purple glow; Discord channel list as home; “AI startup” gradient mesh + glassmorphism cards; five equal JSON panes (pre-M14).

---

## 3. Design locks (implementable)

### 3.1 IA

| Lock | Decision |
|------|----------|
| **First viewport** | Brand (quiet) · **thin** chrome · Today strip (if any) · stream · composer. No vitals/x-ray/audit on home. |
| **Collapsed by default** | Password/Login **only when unauthenticated** for Plan/Agent; Logout behind session menu or single ghost control; `auth=` / `armed=` **one crumb** (or Body-only detail) — not three mono pills. |
| **Body** | Button → right drawer only. Never peer column. Tabs stay inside drawer. |
| **Today** | **Strip only** (M16 F12). Max ~2 visual lines; overflow = “+N” / Body→Shelf or chat ask. Hidden when empty. |
| **Controls always findable** | Mode dial · Body · composer · Plan Accept / Confirm in stream · dues/confirm via Today ≤1–2 clicks. |

### 3.2 Hierarchy (z-order + size)

1. **Composer + stream body text** — largest, highest attention  
2. **Today** — secondary situation (small type)  
3. **Brand wordmark** — present, not shouting (`~1.15–1.25rem`, tracking modest)  
4. **Welcome** — one muted line (`~0.75–0.8rem`)  
5. **Chrome controls** — compact; primary accent only on Send / Accept / Confirm  

### 3.3 Type

| Token / rule | Lock |
|--------------|------|
| UI | **IBM Plex Sans** 400/600 (already self-hosted) |
| Mono | **IBM Plex Mono** — **receipts, tool names, args, paths only** — not badges-as-decoration |
| Body / stream | `1rem` (16px) · line-height **1.55** |
| Chrome | `0.8125–0.875rem` |
| Today / crumbs | `0.75–0.8rem` |
| Display | Do **not** add a third display font |

### 3.4 Color (≤10 semantic tokens)

Keep moss family; **restful** soft dark — reduce glow.

| Token | Target | Role |
|-------|--------|------|
| `--bg` | `#0e1210` | Page |
| `--surface` | `#161c18` | Cards / composer field |
| `--line` | `rgba(fg, ~0.12)` | Hairlines only |
| `--fg` | `#e4e9e3` | Body text (WCAG-ish on bg) |
| `--muted` | `#8a938b` | Secondary |
| `--accent` | `#7fad63` | Primary actions + ok state **only** |
| `--user` | `#6d8f9c` | User rail / label |
| `--warn` | `#c4a035` | Due / confirm / pending |
| `--deny` | `#c97070` | Fault / deny |
| `--radius` | `6px` | One radius (drop pill-everything) |

**Drop / demote:** ambient `--accent-glow` fills; Plan card gradient wash; default `button` = accent border (ghost becomes default chrome). Accent reserved for **state + primary CTAs**.

### 3.5 Space

| Lock | Value |
|------|-------|
| Scale | `4 / 8 / 12 / 16 / 24` px (`0.25–1.5rem`) |
| Max chat | **`40rem`** content width (tighten from 44rem) |
| Home pad | `16px` sides; composer bottom + safe-area |
| Stream gap | `12px` between turns; cards share family padding `12×16` |

### 3.6 Chrome (visible vs overflow)

| Always visible | Overflow / conditional |
|----------------|------------------------|
| Mode dial | `#mode-suggest` only when relevant |
| Body | Logout; raw auth detail |
| Session crumb (one) | Full password form when login required |
| Send | Armed/doctor detail → Body → Vitals |

Login density: **one row max** when needed; after session, chrome height targets **~2.75–3.25rem**.

### 3.7 Components (minimal specs)

| Component | Spec |
|-----------|------|
| **User / ADA turn** | Soft surface or transparent; **2px** rail (user/accent); no heavy card chrome; `who` label optional/muted — not shouting uppercase ops |
| **Tool card** | One hairline + left state color; collapsed args one line; expand for full mono |
| **Plan card** | Title + body/steps + Accept/Reject; **no** glow gradient; accent rail only |
| **Confirm card** | Warn rail; tool + args mono; Confirm/Deny primary pair |
| **Today chip** | Kind color + ellipsized text; click → scroll to card / open Body shelf as wired |

### 3.8 Motion (exactly 2–3)

1. **Stream enter** — opacity + 4px rise ≤180ms  
2. **Drawer** — short slide/fade ≤180ms  
3. **Optional P2:** composer focus border (no pulse loop)  

Honor existing `prefers-reduced-motion: reduce` (zero decorative motion).

### 3.9 Markdown (assistant)

| Lock | Decision |
|------|----------|
| P0 | Keep plain text if needed — **readable** line-length + contrast first |
| P1 | Light render: paragraphs, lists, `strong`, inline `code`, fenced code — **no** giant H1, no nested card chrome, no colored callout boxes |
| Escaping | Stay XSS-safe (`textContent` / sanitizer); never `innerHTML` raw model HTML |

### 3.10 Control recovery

| Need | Affordance |
|------|------------|
| Mode | Dial always in chrome |
| Due / pending Confirm / Plan | Today strip → item; cards also in stream |
| Shelf / organism | Body → Shelf / Vitals |
| Stop *feel* | While streaming: disable Send or swap to visual busy; turn footer shows stop reason. **Abort mid-turn** = OPEN (not P0 theater) |

---

## 4. “Minimal as needed” checklist

If removing **X** does not hurt control or understanding, **X is out.**

| Current chrome | Verdict |
|----------------|---------|
| Separate `auth=` badge + `armed=` chip | **Merge → one crumb** or Body-only |
| Always-visible password field when sessioned | **Out** |
| Plan card accent gradient / glow | **Out** |
| Dual page radial washes | **Simplify to flat/soft single wash** (P0) |
| Uppercase tracking on every label | **Reduce**; keep sparingly (Today ok) |
| Mono on decorative chips | **Out**; mono = receipts |
| Peer vitals on home | Already out (keep out) |
| Today growing into column | **Out** (M16 F12) |
| Extra display font / purple accent | **Out** |

---

## 5. Phased polish

| Phase | Scope | Biggest calm win |
|-------|-------|------------------|
| **P0** | Token pass · density · type scale · header collapse · Today/composer hierarchy · kill glow/default-accent buttons | Home reads **chat**, not toolbar |
| **P1** | Stream markdown · tool/plan/confirm card quieting · turn rails soften · usage footer quieter | Long-read comfort |
| **P2** | Optional presence: focus border / drawer polish only — **still no Jarvis OS** | Quiet confidence |

**Metal (2026-08-16):** P0 tokens/density/chrome + quiet stream cards shipped in `src/ada/hud/static/css/*`, `templates/index.html`, `js/session.js`, `js/today.js`. Markdown still P1. M19b v1.6.1 Mac assistant desk skeleton reuses these moss tokens / IBM Plex / ≤3 motions — no new palette.

---

## 6. Falsifiers

| # | Fail if… |
|---|----------|
| F1 | First viewport reads as **dashboard / NOC** (multi peer panels, chrome > chat) |
| F2 | Due / Plan Accept / Confirm needs **>2 clicks** from home |
| F3 | Body/shelf not reachable in **1 click** from chrome |
| F4 | Body text uncomfortable for **≥10 min** (glare, tiny type, harsh contrast) |
| F5 | `prefers-reduced-motion` still shows decorative motion |
| F6 | Today becomes a **peer column** or steals chat height |
| F7 | Stack forks to Next/React on Pi without EVIDENCE+FEASIBLE+OPEN |

---

## 7. OPEN (≤5)

| # | Question | Default until locked |
|---|----------|----------------------|
| 1 | **Implement P0 polish now?** | **Shipped** — P0 + quiet stream (2026-08-16) |
| 2 | Mid-turn **Abort** control? | Defer; busy/disable Send is enough for P0 |
| 3 | Session overflow = `<details>` vs tiny menu? | **Shipped** — `<details class="session-menu">` |
| 4 | Assistant markdown in P0 or P1? | Still **P1** (plain text + quiet cards for now) |
| 5 | Light theme ever? | **Out** of M17; soft-dark only |

---

## 8. Conflict callouts vs M14 / M16

| Prior lock | M17 stance |
|------------|------------|
| M14 chat-home + Body drawer + ASGI static | **Affirm** — polish CSS/IA density only |
| M14 moss CSS pack | **Extend/tighten tokens**; do not replace identity with purple/SaaS |
| M16 Today strip / shelf / Plan / Confirm | **Preserve findability**; visual quieting only |
| M13 “cool app not ops dump” | M17 is the **taste contract** that finishes that sentence |

---

## 9. Implement-next (when OPEN locks code)

1. P0: `tokens.css` + `base.css` + `chrome.css` — crumb merge, login collapse, bg simplify, button defaults, type/space  
2. P0: Today/composer hierarchy pass (no IA change)  
3. P1: `stream.css` + light markdown render path  
4. P2: optional focus/drawer presence only  

**Done when:** this card exists with locked IA + visual system + P0–P2 list so an implement chat can execute **without inventing taste**.
