# Life organs (`src/ada/life/`)

Life capture domains live under `src/ada/life/{time,people,gym,habits,food}` behind
`ada.life.registry` ordered fast-path hooks. Kernel stays thin:

- `harness/loop.py` — `run_turn` calls registry / domain fast-paths, then Gemini
- `harness/pack_router.py` — merges YAML packs + priority; imports `is_*_utterance` / parsers from domain packages
- `tools/life_tools.py` — public tool names unchanged; handlers delegate to domain `tools.py`

## Pack YAML choice (thinnest)

**Keep** `harness/packs/life_p0.yaml` and `life_p1.yaml` in place. Domains own
structural parsers / doors / spines; pack_router still merges YAML + chip aliases.
No per-domain YAML split in this extract (doors stay importable; no pack reload churn).

## Shims

Old harness/logs import paths re-export from `ada.life.*` for one transition
(e.g. `ada.harness.meal_spine` → `ada.life.food.spine`).
