# M24 Multi-intent capture — Implement Plan

**Status:** plan only — **not METAL**  
**Date:** 2026-08-27  
**Authority:** [`docs/modules/M24_MULTI_INTENT_CAPTURE.md`](../modules/M24_MULTI_INTENT_CAPTURE.md) v1.0 (design lock — do not reopen)  
**Also read:** [`M20_V1_PRODUCT.md`](../modules/M20_V1_PRODUCT.md) · [`M19a_P0_LIFE_CAPTURE.md`](../modules/M19a_P0_LIFE_CAPTURE.md) · [`M22_LIFE_TEACH_IN_FLOW.md`](../modules/M22_LIFE_TEACH_IN_FLOW.md) · [`M23_FRIEND_MOUTH.md`](../modules/M23_FRIEND_MOUTH.md) · phone METAL `runs/2026-08-27/355717c65ea34a7c8575f7b7c3698f8e.jsonl` · `7b8f95715dc042d790041c1034993d30.jsonl` · Gott/brand_fight [`2026-08-26_phone_c369f86f.md`](./2026-08-26_phone_c369f86f.md)

**Naming:** `docs/reviews/M24_IMPLEMENT_PLAN.md` matches M22/M23 implement-plan pattern — gap map + ordered slices; design lock stays under `docs/modules/`.

**Not this plan:** package · retrieval · mail · P4 analysis · food ML · M23 feel · second cortex · silent auto-favorite · habit multi-tick · systemd.

---

## One-liner

Wire **deterministic multi-slot** meal + gym decompose into existing pack fast-paths, feed each slot through **Confirm / brand_fight / empty-nutrient guards**, fail closed on incomplete lift parse — no freestyle ReAct as the honesty path.

---

## Gap map (METAL vs NEW)

| Surface | METAL today | GAP / NEW | Touch | Falsifiers |
|---------|-------------|-----------|-------|------------|
| **Meal multi-item split** | [`meal_spine.py`](../../src/ada/harness/meal_spine.py) `_SPLIT` + qty parse | Silent `candidates[0]`; no `resolve` / brand_fight; empty CORE still builds lines | `meal_spine` + fast-path in [`loop.py`](../../src/ada/harness/loop.py) | F-M24-1, F-M24-2 |
| **Meal Confirm gate** | [`life_tools.py`](../../src/ada/tools/life_tools.py) holds when `resolve` present; [`favorites.py`](../../src/ada/logs/favorites.py) after Yes | Spine / freestyle often omit `resolve` → silent write | Pass `resolve` rows per line; HUD Confirm allowlist already meal-aware | F-M24-1, F-M24-4, F-M24-7 |
| **Empty-nutrient guard** | FDC detail + `honest_partial` flags exist in food/meals path | Null-macro egg still written in live Agent turn | Guard before durable write; Confirm or fail closed | F-M24-2 |
| **Pack route meal** | `_ADD_MEAL` / `log meal:` in [`pack_router.py`](../../src/ada/harness/pack_router.py) | Cortex freestyle still used when operator phrasing varies; must prefer pack | Router + charter: pack fence first | F-M24-1, F-M24-7 |
| **Gym multi-set ladder** | [`gym_spine.py`](../../src/ada/harness/gym_spine.py) one `name load×reps` per part | “lat pulldown 30kg x 12 reps 35kg …” → empty sets → no tool | Extend parse for same-exercise ladders + slash `30×12/35×12` | F-M24-3 |
| **Gym fail-closed speech** | Fast-path returns `missing_life_receipt` on empty parse | Operator sees silence / no tool | Ask/Confirm human line (M23 templates); never silent drop | F-M24-3 |
| **Mouth** | M23 register pass **METAL** | Must not invent kcal if receipt partial | Keep numeric guard; no feel reopen | F-M24-5, F-M24-6 |
| **Habits multi-intent** | Single-verb habit packs | OUT v1.0 (M24 OPEN #5) | — | — |

**Already locked (reuse):** Confirm on ingress; code binds ids; `MODEL_STRIP_CONFIRMED`; favorites after Yes; one cortex; Verb→Pack→fill; M22 stores; M23 feel.

---

## OPEN defaults (from M24 — locked for implement)

| # | Lock |
|---|------|
| 1 | One `life_meal_log` with N lines; hold whole meal if any line needs Confirm |
| 2 | One `life_lift_log` with complete `sets[]` |
| 3 | Cortex line-list assist **off** for v1.0 |
| 4 | No partial silent write (good line + drop bad) |
| 5 | Habit multi-tick **OUT** |

---

## Ordered implement slices

### Slice 1 — Meal multi-slot + resolve + empty guard  
**Scope:** M · `meal_spine.py` · `loop._fast_path_meal` · `life_tools` resolve shape  
**Acceptance:** coffee+eggs → Confirm on Gott/brand_fight; no empty-macro write; favorites path unchanged (F-M24-1, F-M24-2, F-M24-7).

### Slice 2 — Gym multi-set / multi-lift parse fail-closed  
**Scope:** M · `gym_spine.py` · lift fast-path speak on miss  
**Acceptance:** lat pulldown ladder logs 3 sets or Confirm/ask — never no-tool silence (F-M24-3).

### Slice 3 — Pack preference + smokes + phone re-smoke  
**Scope:** S · router/charter nudge inside pack fence; tests; Agent phone  
**Acceptance:** multi-item uses spine not freestyle bind; chat-Yes still stripped; mouth numeric (F-M24-4…8).

**Do not start:** package, retrieval, P4 analysis, food ML, M23 feel, habit multi-tick, second cortex.

---

## Tests to add / extend (names only)

- `tests/test_m24_meal_multi_slot.py` — split + resolve Confirm + empty guard  
- `tests/test_m24_gym_multi_set.py` — ladder / slash parse; incomplete → fail closed  
- Extend pack-router / hud-edge smokes for coffee+eggs and lat pulldown utterances  

---

## Phone re-smoke (operator)

1. Agent: `Log a cup of coffee and 7 boiled eggs for breakfast` → Confirm (not silent Gott); eggs not empty-macro success.  
2. Agent: `Log lat pulldown 30kg x 12 reps 35kg x12 reps 40kg x 8 reps` → 3 sets or clear Confirm/ask — **not** no-tool.  
3. Chat `Yes` alone does not bind. Mouth kcal matches receipt.

### METAL note (2026-08-27 implement)

Slices 1–3 landed on `rewrite/v1-body`: meal_spine multi-slot + `decide_food_bind` / brand_fight / empty-macro guard; gym_spine ladders + fail-closed ask; pack fence + Confirm allowlists (`life_meal_log` + M22 habit/split); `MODEL_STRIP_CONFIRMED` on cortex tool path.  
**Operator after ship:** `sudo systemctl restart ada-hud.service` (Phase 0), then phone re-smoke 1–3 above.

---

*End M24 implement plan — gap map + METAL ship note; design lock remains M24 module card.*
