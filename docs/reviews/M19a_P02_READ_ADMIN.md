# M19a P0.2 — Read packs + admin fast-loops

**Date:** 2026-08-17  
**Parent:** [`docs/modules/M19a_P0_LIFE_CAPTURE.md`](../modules/M19a_P0_LIFE_CAPTURE.md) **v1.5**  
**Code:** `tests/test_m19a_hud_edge_smoke.py`, `tests/test_m19a_pack_router.py`, `tests/test_m19a_due_spine.py`, `tests/test_m19a_food_reference.py`

Same path as HUD chat (`run_turn` / ChatSession). No live Gemini. Live HUD still **operator**.

## How to run (pytest)

```bash
pytest tests/test_m19a_hud_edge_smoke.py -q
pytest tests/test_m19a_*.py -q
pytest -m tier_a -q
```

## Utterance table (automated)

| Say | Pack | Mode | Pass |
|-----|------|------|------|
| `what did i eat` / `macros` | `nutrition_day` | Observe + Agent | `life_nutrition_day`; `stop=pack_fast_path`; no `memory_facts_append` |
| `what's running` / `am i tracking` | `time_status` | Observe + Agent | `life_time_status` |
| `what's due` / `on my plate` | `due_list` | Observe + Agent | `memory_open_loops_list` kind=todo open |
| `what did i lift` / `split today` | `gym_status` | Observe + Agent | `life_gym_status` |
| `how's my day` / `today summary` | `life_status` | Observe + Agent | concat of nutrition + time + dues receipts |
| `add due: finish thesis by Friday` | `due_add` | Agent | `memory_open_loops_upsert` + list; `due_at` set |
| `gotta finish X by Thursday` | `due_add` | Agent | YAML alias → due_spine |
| `remind me to X at 7` | `remind` | Agent | `remind_at` |
| `done: flurmble glorp` | `due_done` | Agent | `missing_life_receipt` (0 matches; do not guess) |
| `good morning` | `time_start` | Agent | kind=`wake` |
| due chip | `due_add` | — | `resolve_chip("due")` → tool `memory_open_loops_upsert`, prefill `add due: ` |

Observe **writes** (meal / due_add) still do **not** fast-path.

## Banana class-fix (CLI · operator)

Tests use tmp `ADA_DATA_ROOT` — they never touch `/mnt/ada-data` sqlite.

```bash
ada life food-forget --name banana --json
ada life food-search banana --json
# then re-log meal in HUD Agent: log meal: one medium banana for breakfast
```

Thin `source=custom` macros-only hits count as a search miss → USDA when key present. Do not expand the FDC map. `honest_partial` stays true if Ca/Fe/C/D are null.

## Live HUD (operator)

Restart `:8787` after code change, Agent + login, then the ask/due rows above. See [`M19a_P01g_HUD_SMOKE.md`](./M19a_P01g_HUD_SMOKE.md) for meal/lift/sleep restart commands.

## PARK (not this slice)

- USDA FDC 90-slot map / Cronometer completeness
- PTT / camera (M19b)
- systemd `ada-hud.service`
- habits / people
- parallel timers
- live Gemini in CI
