# M27 ranking audit — inventory table

**Date:** 2026-09-02  
**Scope:** Step 1 audit + **Step 2 complete** — policy module at `src/ada/harness/catalog_rank.py`. Full card: [`M27_CATALOG_RANKING.md`](../modules/M27_CATALOG_RANKING.md).

## Bind / rank rule inventory

| # | Rule | File | Function |
|---|------|------|----------|
| 1 | Token overlap search | `src/ada/logs/food.py` | `search_foods` |
| 2 | Foundation / brand tier sort | `src/ada/harness/catalog_rank.py` | `foundation_boost` (+ ice-cream demote in sort key) |
| 3 | Composite resolved sort | `src/ada/logs/food.py` → `catalog_rank.py` | `search_foods_resolved` → `rank_catalog_candidates` |
| 4 | Head-noun stem gate | `src/ada/harness/resolve_gate.py` | `candidate_matches_query`, `extract_food_stems` |
| 5 | Brand vs query fight | `src/ada/harness/resolve_gate.py` | `brand_vs_query_fight` |
| 6 | Implausible branded junk | `src/ada/harness/catalog_rank.py` | `macro_implausible` (wrapper: `resolve_gate.implausible_branded_junk`) |
| 7 | Form mismatch | `src/ada/harness/catalog_rank.py` | `catalog_form_mismatch` (wrapper: `resolve_gate.processed_food_mismatch`) |
| 8 | Null-macro gate | `src/ada/harness/resolve_gate.py` | `macros_all_null` |
| 9 | Viable local pool | `src/ada/harness/catalog_rank.py` | `has_viable_local_candidate` |
| 10 | Bind decision + sort | `src/ada/harness/catalog_rank.py` | `rank_catalog_bind` (wrapper: `resolve_gate.decide_food_bind`) |
| 11 | Favorites lookup / sticky | `src/ada/logs/favorites.py` | `get_favorite`, `set_favorite` |
| 12 | Recover alt queries | `src/ada/harness/meal_spine.py` | `build_alt_queries`, `recover_food_slot` |
| 13 | Remote fetch trigger | `src/ada/logs/food.py` | `search_foods_resolved` (thin-custom / branded-only / no viable local) |
| 14 | FDC detail refresh | `src/ada/harness/meal_spine.py` | `_refresh_fdc_detail` |
| 15 | Habit bind (sibling) | `src/ada/harness/resolve_gate.py` | `decide_habit_bind` |

## Known gaps (not covered today)

| Gap | Run cite | Status |
|-----|----------|--------|
| Skin-on / braised thigh | `867c54ee…` | **Fixed** — `catalog_form_mismatch` markers |
| Glutinous vs white rice | deferred | **Fixed** — `glutinous` marker |
| Agent spine bypass | path integrity (M26), not rank | OPEN |

## Freeze

Step 2 complete. No new per-food ranking patches — extend `catalog_form_mismatch` instead.
