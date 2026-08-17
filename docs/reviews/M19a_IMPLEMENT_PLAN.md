# M19a P0 Life Capture — Implement Receipt

**Date:** 2026-08-18  
**Baseline Tier A:** 69 passed → **Final:** 76 passed (`pytest -m tier_a -q`)  
**M19a tests:** 99 passed (`pytest tests/test_m19a_*.py -q`, incl. **P0.1g + P0.2 + P0.5**)  

## Slices delivered

| Slice | Status | Key paths |
|-------|--------|-----------|
| 0 Foundation | DONE | `src/ada/logs/`, `paths.py` |
| 1 Food reference | DONE | `logs/food.py`, `secrets/usda.py`, `ada life food-*` |
| 2 Life tools | DONE | `life_tools.py`, toolspec, gateway, charter, `ada life` |
| 3 Gym catalog | DONE | `gym_import.py`, `gym_custom.py`, seed JSON |
| 4 Capture | DONE | `life_capture`, open_loops/facts/artifacts routes |
| 5 Today/HUD | DONE | `today.py`, `today.js`, composer chips, `/api/life/day` |
| 6 Harness | DONE | `pack_router.py`, `time_intent.py`, `life_p0.yaml` |
| 7 Falsifiers | DONE | `tests/test_m19a_life_capture.py` F1–F10 |
| **P0.1g HUD edge smoke** | **DONE** | `tests/test_m19a_hud_edge_smoke.py` — [`M19a_P01g_HUD_SMOKE.md`](./M19a_P01g_HUD_SMOKE.md) |
| **P0.2 read + admin** | **DONE** | YAML aliases; read packs Observe+Agent; `due_spine.py`; `life_gym_status`; `food-forget` — [`M19a_P02_READ_ADMIN.md`](./M19a_P02_READ_ADMIN.md) |
| **P0.5 hardening** | **DONE** | FDC detail nutrients; bodyweight gym NL; HUD `token_delta`; gym import `--path` — [`M19a_P05_HARDENING.md`](./M19a_P05_HARDENING.md) |

## OPEN resolutions (locked)

1. `time_*` verbs shipped; `focus_*` aliased in pack router  
2. Auto-stop prior timer on new `life_time_start`  
3. Two SQLite files: `life_logs.db` + `food_reference.db`  

## Operator smoke (verified)

```bash
ada life gym-import-seed --json
ada life meal-log --json --lines '[...]'
ada life lift-log --json --sets '[...]'
ada life time-start --json --kind focus_deep --label "smoke"
ada life time-stop --json
ada life nutrition-day --json
ada life capture --json --text "..." --kind todo
ada life food-forget --name banana --json
ada life food-search banana --json
```

**P0.1g HUD-path (automated):** `pytest tests/test_m19a_hud_edge_smoke.py -q`  
**P0.2 HUD-path (automated):** same file + `tests/test_m19a_due_spine.py` / food-forget tests — [`M19a_P02_READ_ADMIN.md`](./M19a_P02_READ_ADMIN.md).  
**P0.5 (automated):** `pytest tests/test_m19a_food_reference.py tests/test_m19a_hud_edge_smoke.py -q` — [`M19a_P05_HARDENING.md`](./M19a_P05_HARDENING.md).  
**Live HUD (operator):** restart `:8787` → Agent + login → banana FDC detail + pull-ups + fast-path chat bubble.

## PARK reminder

- **P1:** PTT, HUD camera/barcode, habits product, people aliases  
- **P4:** `time_week`, analysis packs, Cronometer sync, full 90-slot parity  
- **OUT of P0.5:** live Gemini in CI, systemd `ada-hud.service`, parallel timers, Gemini narrate pass  
- **OUT:** mail, Hevy import, embeddings, M15 rewrite  
