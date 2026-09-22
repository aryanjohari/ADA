# M19c meal-draft ingress smoke

**Date:** 2026-09-22  
**Host:** `ada-pi5` · branch `rewrite/v1-body`  
**Cards:** [`M19c_MULTI_FACE_SURFACES.md`](../modules/M19c_MULTI_FACE_SURFACES.md) v1.1 · [`M26_FOOD_DOMAIN.md`](../modules/M26_FOOD_DOMAIN.md) v1.29  
**Miss cite:** [`f024fb03…`](../../../runs/2026-09-20/f024fb03bfbb4358a48362039aeea9c3.jsonl) — orphaned `meal_draft_1` → one-shot `life_meal_log`.  
**Phone re-smoke:** [`d99da535…`](../../../runs/2026-09-21/d99da535487c4e83be766bfcc07ec5ae.jsonl) — stickiness **PASS**; oats miss via null-energy Confirm (fixed METAL v1.29).

## METAL (pytest) — PASS

```bash
cd /mnt/ada-data/ADA && .venv/bin/pytest \
  tests/test_m19c_meal_draft_ingress.py \
  tests/test_hud_meal_confirm_selection.py -q
```

| Check | Expect | Status |
|-------|--------|--------|
| Start doors / chat `session_id` stickiness | draft keyed to chat sid | **PASS** |
| Open draft + `Add …` | `life_meal_draft_add` only | **PASS** |
| Null `energy_kcal` write | refuse (no kcal 0) | **PASS** |
| Confirm pick null-kcal when complete exists | remap to proposed energy-complete (`d99da535…` oats) | **PASS** (v1.29) |

Falsifiers held: **F-M19c-1** / **F-M19c-10**.

## PHONE — `d99da535…` audit

| Check | Result |
|-------|--------|
| `Add meal` → draft start with chat sid | **PASS** |
| `100 grams oats` → `life_meal_draft_add` (not one-shot log) | **PASS** |
| Oats line lands in draft | **FAIL then** — Confirm on rolled oats E=null → `empty_macros`; **METAL fixed v1.29** — re-smoke |
| PB + milk → draft; save `my test smoothie` | **PASS** (2 lines; milk bound oat milk) |
| `Log my test smoothie` | **PASS** write `life_5a2b9c…` 879 kcal |

**Paste closed run id when oats land:** _(pending after v1.29)_

## Found OPEN (bound — do not chase here)

| Bug | Cite | Bound |
|-----|------|-------|
| **Milk → oat milk** rank | `d99da535…` `250ml milk` | later catalog prefer; no ranking whack-a-mole now |
| **Preset typo** | `Log my test amoothie` → `preset_unknown` | optional fuzzy later; retype OK |

## Still OPEN (do not mark SHIPPED)

- M26 **#5** typed barcode write · **#6** estimate · vocative #4  

## Won’t-chase

Organ pages · hunt panel · wake-word · Funnel · camera barcode as gate · “chat better” prompts.
