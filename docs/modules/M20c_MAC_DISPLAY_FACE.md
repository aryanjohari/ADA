# M20c — Mac + display faces (structure · design lock)

**Status:** **3c METAL** (2026-08-23) — Mac desk + display panel-forward taste on the live HUD. Same family as phone (M20b §7 / M17 §10). Not a second product. Not full 3d panel catalog. Not phase 4 package.  
**Date:** 2026-08-23 (v1.0)  
**Host:** `ada-pi5` (Raspberry Pi 5, 8 GiB) · windows: Mac / display via Tailscale Serve  
**Branch:** `rewrite/v1-body`  
**Kind:** M20 **phase 3c** child (+ display face polish under the same card). Thin lock so implement chats change pieces without guessing.  
**Depends on:** [`M20_V1_PRODUCT.md`](./M20_V1_PRODUCT.md) · [`M20b_PHONE_FACE.md`](./M20b_PHONE_FACE.md) §7 (taste — **inherit**, do not fork) · [`M17_SURFACE_DESIGN.md`](./M17_SURFACE_DESIGN.md) §10 · [`M19b_DAILY_SURFACE_VOICE.md`](./M19b_DAILY_SURFACE_VOICE.md) (one Mac assistant face; display = panels-first)

**Does not supersede:** one `index.html` / `data-face=phone|mac|display`; same `run_turn`; Confirm on this window; Mac hold-to-talk; phone tap; `?face=` wins.

### Changelog

| Ver | Date | Delta |
|-----|------|-------|
| **v1.0** | 2026-08-23 | Lock + ship: Mac chips behind `+`; TTS glyph on Mac; hairline chrome; display panels-first; steel tokens only. |

---

## 1. One-liner + IN / OUT

**Mac** = personal desk — chat-home owns height; thin chrome; small orb; one panel slot; Body 1 click. **Display** = panels-first glance surface; composer/mic off; stream secondary.

| IN (this card / 3c) | OUT (explicit) |
|---------------------|-----------------|
| One HTML; `html[data-face="mac"\|"display"]`; same `POST /api/chat` → `run_turn` | New HTML / Next / React / native shell |
| Shared steel tokens (M17 §10) — **no Mac-only palette** | Moss `#7fad63` as accent · cyan Jarvis · light theme |
| Mac: stream visible · Plan reachable · chips behind `+` · hold mic · Send always visible | Dashboard-home · orb-only · auto-send PTT · always-listen |
| Display: composer hidden · panel slot grows · minimal chrome | Redesigning phone · full gym/habits/people sheet catalog |
| Glyph TTS mute (`#tts-toggle`); persist `ada_hud_tts` | Icon packs · Session threads · clarify-Okay · campaigns · mail |

**Confirm lock:** gateway args on **this** window. TTS never the Yes path.

---

## 2. METAL vs target (honest)

Live: `index.html` · `faces.css` · `chrome.css` · `stream.css` · `voice.js` · `composer_chips.js`.

| Piece | METAL before 3c | Target 3c |
|-------|-----------------|-----------|
| Tokens | Steel `:root` (phone shipped) | Same; Mac/display chrome quieted to match |
| Mac chips | Full `#composer-chips` row always open | Collapse behind `#composer-chips-toggle` (`+`); closed default |
| Mac Send | Accent-filled ops button | Hairline / ghost Send; **always visible** |
| Mac mode | Boxed `#mode-select` | Hairline dial; Observe / Plan / Agent all present |
| Mac TTS | `#tts-toggle` in DOM (phone-styled) | Glyph visible on Mac nav; default off unless `ada_hud_tts=on` |
| Mac brand | ~1.2rem + welcome line | Quiet ADA (~1rem); welcome muted one-liner |
| Mac stream | Soft rails; confirm often `--warn` gold | Soft steel rails; confirm rail = `--deny` |
| Mac tools/plan | Visible | Keep visible — quiet, not NOC |
| Display | Composer/orb hidden; slot ~2fr | Grow slot; hide Body / Today / chips / TTS if they steal height |
| Phone | M20b METAL | **Untouched** |

**Verdict:** 3c is density + chrome discipline on existing faces — not new organs. **3d** = registry pattern only (`nutrition_day` already metal); no new sheet catalog here.

---

## 3. Chrome maps

### Mac

```text
┌──────────────────────────────────────────────────────┐
│ ADA · welcome…   Observe|Plan|Agent · TTS◌ · Sess · Body │
├──────────────────────────────────────────────────────┤
│ ○  Today strip (glance)                              │
│ ┌─ stream ──────────────────┐ ┌─ view-slot ───────┐ │
│ │ token text · tool/plan ok │ │ hairline panel    │ │
│ │ confirm = deny red rail   │ │ empty: quiet      │ │
│ └───────────────────────────┘ └───────────────────┘ │
│ [ + ] textarea · mic(hold) · Send                    │
│   └ chips menu (closed default)                      │
└──────────────────────────────────────────────────────┘
```

### Display

```text
┌──────────────────────────────────────────────────────┐
│ ADA · Session                                        │
├──────────────────────────────────────────────────────┤
│ ┌─ stream (secondary) ─┐ ┌─ view-slot (owns height) ┐│
│ │ muted / de-emphasized │ │ hairline · grows        ││
│ └───────────────────────┘ └─────────────────────────┘│
│ (no composer · no mic · no orb · no Body · no Today)  │
└──────────────────────────────────────────────────────┘
```

---

## 4. Decisions (≤10)

| # | Decision |
|---|----------|
| 1 | **Palette:** inherit M17 §10 / M20b — `--accent: #6d8f9c`; confirm = `--deny`; no Mac-only colors. |
| 2 | **Chips:** Mac `#composer-chips-toggle` (`+`) toggles `#composer-chips`; closed default; Escape + outside click close. Phone stays fully hidden. No new chip verbs. |
| 3 | **Send:** always visible on Mac (not conditional). Hairline, not filled accent ops. |
| 4 | **Mic:** Mac hold-to-talk unchanged. Phone tap unchanged. |
| 5 | **TTS:** same `#tts-toggle` glyph; visible on Mac nav; default off; display may hide. |
| 6 | **Mode:** Observe / Plan / Agent on Mac (Plan stays). Hairline dial, not heavy boxed ops. |
| 7 | **Brand:** quiet ADA ~1rem; welcome demoted to muted one-liner (keep). |
| 8 | **Today:** keep glance strip on Mac; do not grow. Hide on display. |
| 9 | **Orb + slot:** small idle orb + one hairline `view-slot` on Mac; orb off / slot grows on display. |
| 10 | **Body:** `#body-open` → drawer on Mac; hide on display. |

---

## 5. Falsifiers

| ID | Fail if… |
|----|----------|
| **F-M20c-1** | Mac invents a second accent palette or restores moss `#7fad63` as `--accent` |
| **F-M20c-2** | Mac shows full chip row open by default (no `+` collapse) |
| **F-M20c-3** | Mac hides Plan, Body, or tool/plan cards as daily chrome |
| **F-M20c-4** | Display shows composer, mic, orb, or Body as daily chrome |
| **F-M20c-5** | Phone chrome/chips/taste re-opened in this slice |
| **F-M20c-6** | New HTML app, icon pack, session threads, clarify-Okay, campaigns, or full life-sheet catalog ships as “3c” |
| **F-M20c-7** | Mac Send is conditional-hidden like phone, or mic becomes tap-to-toggle |
| **F-M20c-8** | Confirm Yes path is TTS / ear-only |

---

## 6. Explicit OUT

- New HTML app / React / native shell  
- Icon packs / component libraries  
- Redesigning phone  
- Full 3d panel catalog (gym / habits / people / …) — registry pattern only if already wired  
- Session threads · clarify-Okay · campaigns · mail  
- Food-match / retrieval / FACTS fill  
- Auto-send PTT · always-listen · light theme · cyan visualizer  

---

## 7. Implement-next (this slice)

1. Markup: `#composer-chips-toggle` + chips wrap (Mac only visible).  
2. `composer_chips.js`: toggle open/close; Escape; outside click.  
3. `faces.css` / `chrome.css` / `stream.css`: Mac hairline chrome; display panel-forward hides.  
4. Tests: `tests/test_m20c_mac_display_face.py`.  
5. Mark M20 phase **3c METAL**; **3d** remains pattern-only (`nutrition_day`).

**Done when:** Mac reads quieter / same family as phone; display is panel-forward; faces trilogy closed for taste.

---

*End M20c. Cite M20b §7 / M17 §10 / M19b; do not rewrite them.*
