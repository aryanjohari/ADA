# M19a P0.1g — HUD edge smoke

**Date:** 2026-08-17  
**Parent:** [`docs/modules/M19a_P0_LIFE_CAPTURE.md`](../modules/M19a_P0_LIFE_CAPTURE.md) **v1.5**  
**Code:** `tests/test_m19a_hud_edge_smoke.py` (`run_turn` + `ChatSession(mode="agent")`)

This is the **same path as HUD chat** (M15 `run_turn` / ChatSession Agent). It does **not** require live Gemini or a live HUD HTTP round-trip. Success = `life_*` receipts + SQLite rows — never chat-only “logged it”, never `memory_facts_append` ok on life packs.

## How to run (pytest)

```bash
pytest tests/test_m19a_hud_edge_smoke.py -q
pytest tests/test_m19a_*.py -q
pytest -m tier_a -q
```

Utterance table lives in the test file (`HUD_EDGE_SMOKE`) — not unused pack YAML.

## How to run (live HUD — operator)

1. Restart HUD after code change (stale pid on `:8787` will not load this tree):

```bash
pid=$(ss -ltnp 'sport = :8787' | sed -n 's/.*pid=\([0-9]*\).*/\1/p' | head -1)
[ -n "$pid" ] && kill "$pid"
ada hud serve --host 127.0.0.1 --port 8787
```

2. Open HUD, **Agent** mode, logged in. Seed gym + food cache (or USDA key):

```bash
ada life gym-import-seed --json
```

3. Five utterances (plus CLI check):

| # | Say / run | Pass |
|---|-----------|------|
| 1 | `log meal: one medium banana for breakfast` | `life_food_search` + `life_meal_log` + `life_nutrition_day`; `stop=pack_fast_path` |
| 2 | `going to sleep` | `life_time_start` + Today running timer |
| 3 | `log lift: flat bench 50kg x6` | `life_lift_log`; gym set 50kg × 6 |
| 4 | `ada life nutrition-day --today --json` | Totals match Today strip; `honest_partial` if custom/thin food |
| 5 | `log meal: flurmble glorp` | `missing_life_receipt`; **no** new meals row |

Edges covered in pytest only: `add one banana to breakfast`, `I woke up` / `going to sleep.`, `stop focus`, `capture: buy oat milk`, Observe-mode no write, meal search strips slot words (`banana` not `banana breakfast`), custom Banana macros-only (no invented Ca/Fe/D). P0.2 ask/due/food-forget: [`M19a_P02_READ_ADMIN.md`](./M19a_P02_READ_ADMIN.md).

## METAL notes

- Custom Banana cache = **macros only**. Thin custom-only hits count as a **miss** → USDA when key present. Operator: `ada life food-forget --name banana --json` then `ada life food-search banana --json`.
- CORE nutrient slots + incomplete FDC map ⇒ `nutrition_day.honest_partial is True`. Do not invent Ca/Fe/D.
- Gateway owns writes. Fast-path writes are Agent + complete args only. **Reads** (nutrition/time/dues/gym/life_status) fast-path in Observe + Agent. Observe/Plan deny writes unchanged.

## PARK (not this slice)

- Expanding USDA FDC nutrient map / Cronometer 90 slots
- systemd `ada-hud.service`
- M19b PTT/camera
- habits / people / parallel timers
