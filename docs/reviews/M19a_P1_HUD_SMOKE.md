# M19a P1.x — HUD smoke (habits + people + birthday)

**Date:** 2026-08-18  
**Parent:** [`docs/modules/M19a_P1_HABITS_PEOPLE.md`](../modules/M19a_P1_HABITS_PEOPLE.md) **v1.0**  
**Code (target):** `tests/test_m19a_p1_hud_smoke.py` (`run_turn` + `ChatSession`)

Same path as P0 HUD chat (M15 `run_turn` / ChatSession). No live Gemini required for pytest. Success = `life_habit_*` / `life_people_*` / `memory_open_loops_*` receipts + SQLite/YAML rows — never chat-only claims.

**Prereq:** P0 pytest green (`tests/test_m19a_*.py` excluding P1).

## How to run (pytest)

```bash
pytest tests/test_m19a_p1_hud_smoke.py -q
pytest tests/test_m19a_p1_*.py -q
pytest tests/test_m19a_*.py -q
pytest -m tier_a -q
```

Utterance table lives in the test file (`P1_HUD_SMOKE`) — not unused pack YAML.

## How to run (live HUD — operator)

1. Restart HUD after code change:

```bash
pid=$(ss -ltnp 'sport = :8787' | sed -n 's/.*pid=\([0-9]*\).*/\1/p' | head -1)
[ -n "$pid" ] && kill "$pid"
ada hud serve --host 127.0.0.1 --port 8787
```

2. Open HUD, **Agent** mode, logged in. Seed habits (example):

```bash
# after P1.1 ships — placeholder until CLI exists
ada life habit-seed --json
```

3. Utterance table:

| # | Say / run | Mode | Pass |
|---|-----------|------|------|
| 1 | `habit done: skincare` | Agent | `life_habit_do` + `life_habit_status`; `stop=pack_fast_path`; `habit_events` row |
| 2 | `habits today` / `how are my habits` | Observe or Agent | `life_habit_status`; continuity speak; no shame streak copy |
| 3 | `who is Mama` | Observe or Agent | `life_who_is`; 0/1/many honest; no `memory_facts_append` |
| 4 | `met Ravi at dinner, kid starts school` | Agent | `life_person_capture`; `people/*.yaml` + interaction note |
| 5 | `set birthday: Ravi 1990-05-20` | Agent | `life_birthday_set`; open_loop + `people_ids`; Today `birthday_soon` |
| 6 | `remind me to call Ravi Friday` | Agent | `memory_open_loops_upsert` with `people_ids` when resolve 1:1 |
| 7 | `habit done: flurmble glorp` | Agent | `missing_life_receipt`; no fake tick |
| 8 | `routine run: evening` (if seeded) | Agent | `life_routine_run`; `routine_runs` row |
| 9 | Alias clash scenario → bind `Dad` | Agent + Confirm | Confirm sheet; F-P1.2a — no silent bind |

## Falsifiers (this slice)

| ID | Check |
|----|-------|
| F-P1.xa | `pack_hint` reaches charter same turn |
| F-P1.xb | No standalone Habits/People dashboard route added |
| F-P1.1b | habit tick ⇒ SQLite row |
| F-P1.2a | kin alias clash ⇒ Confirm |
| F-P1.3a | birthday ⇒ open_loop + `people_ids` |

## METAL notes

- Fast-path writes **Agent-only**; reads **Observe+Agent** — same as P0.
- People path jail: `facts/people/` only.
- Dream never auto-merges people — overwrites Confirm-bound.
- Notify: budget + quiet hours ([`notify.py`](../../src/ada/memory/notify.py)); ping claims need receipt or honest skip.
- Continuity rate in speak — not “streak broken” guilt copy.

## PARK (not this slice)

- Mail / jobs / analysis packs
- Learned habit ML schedules
- CRM / LinkedIn sync
- M19b PTT/camera
- People/Habits dashboard soup
- systemd timers for EOD (optional CLI only in P1)
