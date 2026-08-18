# M19a P0.5 — Hardening operator smoke

**Date:** 2026-08-18  
**Parent:** [`M19a_P0_LIFE_CAPTURE.md`](../modules/M19a_P0_LIFE_CAPTURE.md) v1.7  
**Automated:** `pytest tests/test_m19a_food_reference.py tests/test_m19a_hud_edge_smoke.py tests/test_m19a_gym_catalog_init.py -q`

## What shipped (P0.5)

| Slice | METAL |
|-------|-------|
| FDC detail fetch + expanded nutrient map | `src/ada/logs/food.py` — search for discovery, `GET /fdc/v1/food/{fdcId}` before `insert_food` |
| Bodyweight gym NL | `src/ada/harness/gym_spine.py` — `pull-ups x8`, `10 pull-ups`, `3x10 pull-ups`; `load_kg: null` |
| Optional gym catalog import | `ada life gym-import-seed --path /path/to/wger-or-exercisedb.json` |
| **Gym catalog auto-init (boot)** | `open_life_db` → `ensure_exercise_catalog`; **remote fetch default**; `ADA_GYM_CATALOG_FETCH=off` → bundled |
| **Gym NL ↔ catalog** | fold/alias match (`pull-ups`→`Pullups`); bundled merge for `flat bench`; movement/muscles/equipment tags |
| HUD fast-path speak | `loop.py` emits `token_delta` on fast-path completion; no Gemini (`steps=0`) |

## Operator smoke (live HUD)

**Prereqs:** Agent session + login; exercise catalog auto-inits on first DB open (or `ada life gym-init --json` after manual delete); USDA key in `secrets/usda_fdc.env` for banana detail test.

**Restart HUD after code change:**

```bash
pid=$(ss -ltnp 'sport = :8787' | sed -n 's/.*pid=\([0-9]*\).*/\1/p' | head -1)
[ -n "$pid" ] && kill "$pid"
ada hud serve --host 127.0.0.1 --port 8787
```

| Step | Action | Pass |
|------|--------|------|
| 1 | `ada life food-forget --name banana --json` | Custom stub removed |
| 2 | `ada life food-search banana --json` | USDA hit; `calcium_mg` / `iron_mg` populated when API returns them |
| 3 | HUD Agent: `log meal: one medium banana for breakfast` | Tool cards + **assistant bubble** “Logged meal — receipt on file.” |
| 4 | HUD Observe or Agent: `what did i eat` | Nutrition speak line; `honest_partial` suffix only if CORE gaps remain |
| 5 | HUD Agent: `log lift: pull-ups x8` | `life_lift_log` receipt; set row `load_kg` null; catalog hit (`Pull-up` or `Pullups`) |
| 6 | Any fast-path read/write | One ADA chat line appears (canned); footer `steps=0` |

## CLI checks (headless)

```bash
ada life food-forget --name banana --json
ada life food-search banana --json
ada life gym-import-seed --json
ada life gym-init --json   # manual re-run after DELETE FROM exercise_catalog
ada life gym-import-seed --path /path/to/wger.json --json   # optional
```

## Locks (unchanged)

- Verb→Pack→Cortex-fill; P0.2 packs/aliases unchanged  
- Snapshot at write time — re-fetching cache does not alter logged meals  
- `honest_partial`: never invent Ca/Fe/C/D  
- Fast-path writes Agent-only; reads Observe+Agent  
- No P1 habits/people, no Gemini narrate pass on HUD writes

## Out of scope

P1, full Cronometer 90-slot parity, week UI P4, commit unless operator asks.
