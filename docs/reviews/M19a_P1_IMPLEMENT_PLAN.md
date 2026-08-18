# M19a P1 Habits + People — Implement Receipt

**Date:** 2026-08-18  
**Parent:** [`docs/modules/M19a_P1_HABITS_PEOPLE.md`](../modules/M19a_P1_HABITS_PEOPLE.md) v1.0  
**Pattern:** P0 close loop in [`M19a_IMPLEMENT_PLAN.md`](./M19a_IMPLEMENT_PLAN.md)

## Slices delivered

| Slice | Status | Key paths |
|-------|--------|-----------|
| P1.1 Habits core | **DONE** | `logs/habits.py`, `habit_spine.py`, `life_p1.yaml` (habit packs), `life_habit_*`, Today habit keys |
| P1.2 People | **DONE** | `memory/people.py`, `people_spine.py`, `life_people_*`, due `people_ids`, chips `met`/`who` |
| P1.3 Birthday notify | **DONE** | `life_birthday_set`, `life_people_remind`, Today `birthday_soon`/`people_remind` |
| P1.x HUD smoke | **DONE** | `tests/test_m19a_p1_hud_smoke.py` |

## Test results

```bash
pytest tests/test_m19a_p1_*.py -q          # 31 passed
pytest tests/test_m19a_*.py -q             # 145 passed
pytest -m tier_a -q                        # 85 passed
```

## OPEN resolutions (locked)

1. SQL authoritative for habit ticks; YAML seed only  
2. Interactions YAML notes-only v1  
3. Separate `life_p1.yaml` merged at load  
4. Empty habit catalog + `ada life habit-seed`  
5. Kin inline on card; `kin_link` → `person_update`  
6. EOD manual + `ada life routine-sweep` CLI  
7. Fuzzy threshold 0.85 on display_name  

## Operator smoke (after deploy)

```bash
ada life habit-seed --json
pytest tests/test_m19a_p1_hud_smoke.py -q
# Live HUD: restart :8787, Agent + login, utterance table in M19a_P1_HUD_SMOKE.md
```

## PARK (unchanged)

Mail/jobs/analysis, learned schedules, CRM, People/Habits dashboard, M19b PTT/camera.
