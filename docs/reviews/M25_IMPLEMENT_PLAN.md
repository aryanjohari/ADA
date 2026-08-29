# M25 Resolve recover — Implement Plan

**Status:** METAL — slices 1–6 shipped 2026-08-28  
**Date:** 2026-08-27 (slices 1–3) · 2026-08-28 (slices 4–6 phone METAL close)  
**Authority:** [`docs/modules/M25_RESOLVE_RECOVER.md`](../modules/M25_RESOLVE_RECOVER.md) v1.0 (design lock — do not reopen)  
**Also read:** [`M24_MULTI_INTENT_CAPTURE.md`](../modules/M24_MULTI_INTENT_CAPTURE.md) · [`M20_V1_PRODUCT.md`](../modules/M20_V1_PRODUCT.md) · [`M19a_P0_LIFE_CAPTURE.md`](../modules/M19a_P0_LIFE_CAPTURE.md) · [`M23_FRIEND_MOUTH.md`](../modules/M23_FRIEND_MOUTH.md) · phone METAL `runs/2026-08-27/2be4966eb8e3414aa1f24bc0b1f28a72.jsonl` · `runs/2026-08-27/dcce95819f504591a679e1f3e5005635.jsonl` · M24 ship [`M24_IMPLEMENT_PLAN.md`](./M24_IMPLEMENT_PLAN.md)

**Naming:** `docs/reviews/M25_IMPLEMENT_PLAN.md` matches M22/M23/M24 implement-plan pattern — gap map + ordered slices; design lock stays under `docs/modules/`.

**Not this plan:** package · retrieval · mail · P4 analysis · charts · food ML · M23 feel · M24 decompose reopen · second cortex · unbounded ReAct · habit multi-intent · lift catalog miss · systemd.

---

## One-liner

Wire a **bounded recover loop** after meal fast-spine `empty_macros` / search miss — alternate queries + `fetch_usda_detail` refresh + drop null-CORE → existing Confirm — caps then clear ask; no invent kcal, no freestyle ReAct.

---

## Gap map (METAL vs NEW)

| Surface | State | Note |
|---------|--------|------|
| **Recover loop** | **METAL** | `meal_spine.recover_food_slot` — alt queries, detail refresh, caps → ask |
| **Off-query filter** | **METAL** | `candidate_matches_query` — slot food stems must appear in candidate name (blocks Banana↔eggs via shared `raw`; phone `dcce958…`) |
| **Empty-macro guard** | **METAL** | unchanged; recover runs before fail-closed hold |
| **Detail cache write** | **METAL** | `food.update_food_nutrients` on honest FDC detail (OPEN #4) |
| **Fast-path ask** | **METAL** | `loop._fast_path_meal` surfaces `ask` after recover cap |
| **M24 multi-slot hold** | **METAL** | coffee+eggs hold intact when eggs recover fails |
| **Null-CORE local = miss** | **METAL** | `food.is_null_core_food` — all-null local hits still `fetch_remote`; deprioritized in rank (Gap A) |
| **Fast-path detail refresh** | **METAL** | `build_meal_log_args` refreshes null-CORE FDC before bind/recover (Gap C) |
| **Freestyle meal_log enrich/refuse** | **METAL** | `life_tools._enrich_meal_line_from_ref` + `meals.meal_log` belt — no silent 0-write (Gap B / F-M25-7) |
| **Alt-query dedupe** | **METAL** | `build_alt_queries` — no double modifier / no `rices` (Gap D) |

## Gap map (historical — pre-ship)

| Surface | METAL today | GAP / NEW | Touch | Falsifiers |
|---------|-------------|-----------|-------|------------|
| **Empty-macro guard** | [`meal_spine.py`](../../src/ada/harness/meal_spine.py) miss `empty_macros`; [`life_tools.py`](../../src/ada/tools/life_tools.py) refuse write; [`loop._fast_path_meal`](../../src/ada/harness/loop.py) ack | No retry / alt query / detail refresh | recover hook after miss | F-M25-5 |
| **Query strip** | `_parse_piece` drops `boiled` / size → search `"eggs"` | Lost cooked Foundation cues; candy FDC null CORE wins | alt-query table restores cooks/size + USDA phrases | F-M25-5 |
| **FDC detail** | [`fetch_usda_detail`](../../src/ada/logs/food.py) METAL; search prefers detail once | Spine does not re-fetch / refresh on null CORE pool | force detail + cache update (OPEN #4) | F-M25-1 |
| **Confirm after recover** | [`decide_food_bind`](../../src/ada/harness/resolve_gate.py) + gateway Confirm | Empty miss never reaches Confirm with better set | handoff viable pool → resolve / Confirm | F-M25-2, F-M25-3, F-M25-7 |
| **Caps / ask** | Soft stop = empty mouth line only | No rounds/search/wall; feels stuck | 3 / 5 / ~8s → human ask | F-M25-4, F-M25-5 |
| **M24 multi-slot** | Hold whole meal on any miss | Must not regress decompose / partial write | keep OPEN #1 hold; recover per-slot then reassemble | F-M25-6 |
| **Mouth** | M23 register; empty-nutrients template | Ask line after cap must stay human, no invent | template only | F-M25-1, F-M25-8 |
| **Cortex query assist** | — | OUT v1.0 (M25 OPEN #1 OFF) | — | F-M25-4, F-M25-7 |
| **Lift catalog miss** | — | OUT v1.0 (OPEN #5) | — | — |

**Already locked (reuse):** Confirm on ingress; code binds ids; `MODEL_STRIP_CONFIRMED`; favorites after Yes; one cortex; Verb→Pack→fill; M22 stores; M23 feel; M24 decompose + empty guard.

---

## OPEN defaults (from M25 — locked for implement)

| # | Lock |
|---|------|
| 1 | Cortex query-list assist **off** for v1.0 |
| 2 | Caps: **3** rounds · **5** searches/slot · **~8s** wall → ask |
| 3 | Weak-only trigger **off** — `empty_macros` + search miss first |
| 4 | Detail refresh **writes** honest CORE into local food cache |
| 5 | Lift catalog miss recover **OUT** |

---

## Ordered implement slices

### Slice 1 — Trigger + alt queries + detail refresh  
**Scope:** M · `meal_spine` recover helper · `food.fetch_usda_detail` / cache update · `_fast_path_meal` hook after miss  
**Acceptance:** “7 boiled eggs” retries beyond bare `eggs`; null-CORE candy dropped; Foundation/cooked hit with macros or clear ask (F-M25-1, F-M25-5).

### Slice 2 — Confirm handoff + whole-meal hold  
**Scope:** M · re-enter `decide_food_bind` / resolve rows; preserve M24 hold-all on remaining miss  
**Acceptance:** Recover success → Confirm when ambiguous; unique sticky+honest silent OK; no Gott silent; no Gemini `ref_id` (F-M25-2, F-M25-3, F-M25-6, F-M25-7).

### Slice 3 — Caps + mouth ask + smokes + phone re-smoke  
**Scope:** S · caps; fail mouth line; tests; Agent phone  
**Acceptance:** Cap hit → human ask not silent forever; no unbounded loop; M24 coffee+eggs still honest (F-M25-4…8).

### Slice 4 — Null-CORE = miss + fast-path detail refresh  
**Scope:** M · `food.search_foods_resolved` · `build_meal_log_args` first-pass `_refresh_fdc_detail`  
**Acceptance:** “7 boiled eggs” / “300g boiled white rice” reach honest candidate or Confirm — not cap→ask with only null rows (Gap A, C).

### Slice 5 — Refuse/enrich freestyle meal_log  
**Scope:** M · `life_tools.run_life_meal_log` enrich from `get_food`; `meals.meal_log` refuse all-null  
**Acceptance:** Gemini `ref_id`-only path → enrich or `empty_macros` — never silent 0 protein (Gap B / F-M25-7).

### Slice 6 — Tests + phone checklist  
**Scope:** S · extend `test_m25_resolve_recover.py`; gap map; phone METAL  
**Acceptance:** null-CORE remote; freestyle refuse; M24 green; phone checklist below.

**Do not start:** package, retrieval, P4 analysis, charts, food ML, M23 feel, cortex query assist, lift miss recover, second cortex.

---

## Tests to add / extend (names only)

- `tests/test_m25_resolve_recover.py` — alt queries after empty_macros; detail refresh; caps → ask  
- Extend `tests/test_m24_meal_multi_slot.py` — coffee+eggs still hold; eggs recover path does not regress guard  
- Pack-router / hud-edge smoke: boiled eggs hard-case  

---

## Phone re-smoke (operator)

**Shipped 2026-08-28 — re-verify on phone after `sudo systemctl restart ada-hud.service`:**

1. Agent: `Log 7 boiled eggs for breakfast` → honest macros Confirm/log **or** clear ask after retries — **not** 0 protein / silent empty write.  
2. Agent: `Log 300 grams boiled white rice for lunch` → same — honest macros or clear ask.  
3. Agent: `Log a cup of coffee and 7 boiled eggs for breakfast` → M24 hold/Confirm intact; eggs not silent empty write.  
4. Chat `Yes` alone does not bind. Mouth kcal ⊆ receipt (no invent).

---

*End M25 implement plan — METAL 2026-08-28 (slices 4–6); design lock remains M25 module card.*

**2026-08-29 METAL:** FDC detail `foodNutrients` parse fixed (nested `nutrient.id` + `amount`); recover/detail-refresh now writes honest CORE into local cache. **`harness/__init__.py`** no longer eager-imports `loop` — fixes HUD crash (`gateway → life_tools → resolve_gate` import cycle). **brand_fight recover** + implausible-branded filter + targeted Mars EGGS cache purge for poisoned candy rows.
