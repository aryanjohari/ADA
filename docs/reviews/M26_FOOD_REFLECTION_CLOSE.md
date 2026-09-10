# M26 food reflection close — review note

**Date:** 2026-09-02  
**Slice:** deterministic week nutrition reflection; food removed from Dream LLM path.

## Architecture (one-liner)

Food numbers = SQLite rollups + FACTS targets via `life_nutrition_day` / `life_nutrition_week` (`food_reflection.nutrition_window`). Dream stays prefs + cite heads + campaigns only.

## Removed from Dream

- `build_food_rollup_summary` (was in `dream/delta.py`)
- `food_rollup_summary` in `build_delta` output and manage prompt food rules

## Smokes

| Command / utterance | Expect |
|---------------------|--------|
| `ada life nutrition-day --today --json` | Day totals vs targets |
| `ada life nutrition-week --days 7 --json` | Window patterns + aggregates |
| `cat /mnt/ada-data/scratch/food_reflection_latest.json` | Last week reflection snapshot |
| `what did i eat` | `life_nutrition_day` fast path (today) |
| `what did i eat yesterday` | `life_nutrition_day` with **local yesterday** `date` arg |
| `tell all macros this week` | `life_nutrition_week`; not `life_nutrition_day` |
| `protein this week` | `life_nutrition_week`; pattern strings; `meal:day:…` cites |
| `Log 5 eggs for breakfast` | Capture spine unchanged |

## Read path fix (2026-09-02)

**Root cause:** pack alias substring match (`"what did i eat"` inside `"what did i eat yesterday"`) with **no `date` arg**; week utterances (`tell all macros this week`) missed `nutrition_week` alias; Agent mode sometimes picked `life_nutrition_day` without args when pack hint was weak.

**Not a rollup bug:** `logged_at` is UTC; `local_day` / `date` is operator TZ (`preferred_tz`) — mouth should speak the **local** date.

**Phone run ids:** `0dc871c…`, `76f0c2b…`, `15e46f…` (2026-09-01 UTC ≈ Sep 2 NZ morning).

**Fix:** `parse_nutrition_date` + structural nutrition read in `pack_router` (week cue → `nutrition_week` + `days: 7`; date cue → `nutrition_day` + `date`); longer aliases first; charter nudge blocks tool substitution.

## Tests

```bash
pytest tests/test_nutrition_read_path.py tests/test_food_reflection.py tests/test_m26_food_ranking.py \
  tests/test_m19a_life_tools.py tests/test_m19a_pack_router.py \
  tests/test_m19a_hud_edge_smoke.py -q
```
