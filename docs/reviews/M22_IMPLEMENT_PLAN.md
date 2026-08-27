# M22 Teach-in-flow — Implement Plan

**Status:** plan only — **not METAL**  
**Date:** 2026-08-26  
**Authority:** [`docs/modules/M22_LIFE_TEACH_IN_FLOW.md`](../modules/M22_LIFE_TEACH_IN_FLOW.md) v1.0 (design lock — do not reopen)  
**Also read:** [`M21_RESOLVE_CLARIFY.md`](../modules/M21_RESOLVE_CLARIFY.md) · [`M20_V1_PRODUCT.md`](../modules/M20_V1_PRODUCT.md) · [`M19a_P0_LIFE_CAPTURE.md`](../modules/M19a_P0_LIFE_CAPTURE.md) · [`M19a_P1_HABITS_PEOPLE.md`](../modules/M19a_P1_HABITS_PEOPLE.md)  
**Parallel note:** phone bugfix ([`2026-08-26_phone_c369f86f.md`](./2026-08-26_phone_c369f86f.md) — coffee Gott, `cortex.empty`, gym muscles) may land separately. **Do not rewrite those fixes**; cite touch-points below if you edit the same files.

**Naming:** this card lives under `docs/reviews/` as `M22_IMPLEMENT_PLAN.md` to match [`M19a_IMPLEMENT_PLAN.md`](./M19a_IMPLEMENT_PLAN.md) / [`M19a_P1_IMPLEMENT_PLAN.md`](./M19a_P1_IMPLEMENT_PLAN.md) — implement plans are receipts/checklists; design locks stay under `docs/modules/`. Not `M22a_*` (would look like another sequence sibling).

---

## One-liner

Teach-in-flow = first-time ask → Confirm on ingress → sticky into **existing** stores (gym split FACT, habit SQL, prefs `brief_include`, last closed `gym_sets` read). Four implement slices; no package, no new prefs DB, no silent auto-learn.

---

## Gap map (METAL vs NEW)

| Feature | METAL today | GAP / NEW | Confirm tool | Store key | HUD | Falsifiers |
|---------|-------------|-----------|--------------|-----------|-----|------------|
| **Gym start/end packs** | Tools `life_gym_start` / `life_gym_end` in [`life_tools.py`](../../src/ada/tools/life_tools.py) + [`toolspec.py`](../../src/ada/tools/toolspec.py); session SQL in [`gym.py`](../../src/ada/logs/gym.py) (`gym_start`, `gym_end`) | Packs **missing** in [`life_p0.yaml`](../../src/ada/harness/packs/life_p0.yaml) (only `gym_status` + `lift_log`); no aliases/chips; `pack_router` has no `gym_start`/`gym_end` fast path | none for start/end session open/close | `gym_sessions` SQL | Agent chat only; no new dashboard | F-M22-1 (if start/end only via CLI); phone speak from receipt |
| **Gym split ask-once** | `gym_status` **reads** `get_fact("gym_split")` → receipt `gym_split` ([`gym.py:367`](../../src/ada/logs/gym.py)); M19 catalog verb `split_set` unused | No Confirm write path; no `facts/gym_split.yaml` in tree; docs still imply hand-edit | **Prefer** new thin `life_split_set` (mirror `life_food_favorite_set`) **or** `memory_facts_propose_edit` key `gym_split.days` — **taste locked below** | `facts/gym_split.yaml` via `get_fact("gym_split")` (same doc status already reads) | Confirm card on phone ingress; allowlist in [`routes_api.py`](../../src/ada/hud/routes_api.py) `_CONFIRMABLE_TOOLS` + [`stream.js`](../../src/ada/hud/static/js/stream.js) `CONFIRMABLE` | F-M22-1, F-M22-2, F-M22-6 |
| **Last-session weights** | `gym_sets` + closed `gym_sessions`; `lift_log` resolves `exercise_id`; mouth `_speak_gym_status` ([`loop.py`](../../src/ada/harness/loop.py)) | No query for last **closed** session same `exercise_id`; `gym_status` = today’s sets only | none (read) | SQL `gym_sets` ⨝ `gym_sessions` where `status='closed'` | Speak/prefill from receipt JSON only ([`mouth.py`](../../src/ada/harness/mouth.py) register pass) | F-M22-9 (invented loads); numeric fail-closed |
| **Habits resolve (M21 leftover)** | [`resolve_habit`](../../src/ada/logs/habits.py) returns 0/1/many; [`habit_spine.py`](../../src/ada/harness/habit_spine.py) maps 0/many → `missing_life_receipt`; packs in [`life_p1.yaml`](../../src/ada/harness/packs/life_p1.yaml) | Many → Confirm-bind **not** wired (unlike meal/person); HUD Confirm not allowlisted for habit tools | Hold: `life_habit_do` / `life_habit_miss` with `habit_id` + `confirmed=true` (M21 pattern) | `habit_definitions` SQL | Confirm candidates (label/`habit_id`); ingress Yes | F-M21-* bind honesty; F-M22-2 |
| **Unknown habit Confirm-create** | [`upsert_habit_definition`](../../src/ada/logs/habits.py); CLI [`seed_default_habits`](../../src/ada/logs/habits.py) / `ada life habit-seed` | 0 matches → fail (`missing_life_receipt`); seed reads as primary door | New `life_habit_create` **or** extend tick tool with `create_if_missing` + Confirm — **taste locked below** | same `habit_definitions` (`source=teach_in_flow` or `operator`, not required `seed`) | Confirm “save habit X?” then tick once | F-M22-1, F-M22-2, F-M22-6 |
| **Brief section prefs** | Clock keys METAL: `prefs.brief_time`, `brief_enabled` in [`WHITELIST_KEYS`](../../src/ada/memory/facts.py); Today strip [`build_today`](../../src/ada/hud/today.py) always emits dues / overnight / meal_gap / habits / … | No include/exclude list; no Confirm patch for sections | `memory_facts_propose_edit` on `prefs.brief_include` (already Confirmable) | `facts/prefs.yaml` → `brief_include` (**not** Dream whitelist) | Confirm shows proposed list; subsequent `build_today` / brief consumers filter | F-M22-2, F-M22-3, F-M22-9 |
| **Favorites / people / Dream** | Favorites after Yes ([`favorites.py`](../../src/ada/logs/favorites.py)); Dream **stages** favorites/people ([`dream/merge.py`](../../src/ada/dream/merge.py)) | Extend UX only — **do not** invent second prefs store | unchanged | unchanged | unchanged | F-M22-3, F-M22-4 |

**Already locked (reuse, don’t rebuild):** Confirm on ingress; no ear Yes; code binds ids; mouth = register pass on receipts; Gemini never chooses food `ref_id`.

---

## OPEN defaults (locked for implement taste)

| # | M22 OPEN | Lock for implement chats |
|---|----------|--------------------------|
| 1 | Brief section inventory | Key: **`prefs.brief_include`** — list of section ids. Default when absent = **all current Today sections** (backward compatible): `dues`, `overnight`, `meal_gap`, `open_gym`, `habits_due`, `nutrition_headline`, `continuity`. Operator Confirm add/remove. **Never** news/PubMed. **Do not** add to `WHITELIST_KEYS` / Dream auto-merge (F-M22-3). |
| 2 | Gym split schema | `facts/gym_split.yaml`: `{schema_version: 1, days: {mon\|tue\|…\|sun: {label: str, body_parts: [str]}}}`. Confirm card shows the table. Tool: **`life_split_set`** (`confirmed` required; writes whole doc or `days` map). Prefer dedicated tool over raw `propose_edit` so HUD candidate UX can show day rows (same pattern as meal Confirm). Fallback OK: `memory_facts_propose_edit` `gym_split.days` if slice 1 wants zero new toolspec — pick one in slice 1 and stick. |
| 3 | Last-session lookback | Last **closed** session (`gym_sessions.status='closed'`), same `exercise_id`, latest set(s) by `logged_at`/`sort_order`. Receipt fields: `last_load_kg`, `last_reps`, `last_session_id`, `last_logged_at`. Speak/prefill only those. **Not** PR / volume coverage. Lookback unbounded within durable DB (no artificial N-day cut unless perf forces it — then OPEN reopen). |
| 4 | Package interview | **Out of M22 implement** — phase 4 later; same stores. |
| 5 | Unknown habit timing | **After** habits resolve (slice 3a) greens: 0 matches → Confirm-create. Until then keep honest `missing_life_receipt`. CLI seed stays **optional** (`source=seed` labeled). |

---

## Ordered implement slices

### Slice 1 — Gym packs + split ask-once  
**Scope:** ~1 focused PR/chat · **est. M–L**  
**Depends on:** nothing from M22; may touch files also touched by bugfix B3 (gym muscles) — **merge carefully, don’t revert muscles on receipt**.

| Work | Paths / symbols |
|------|-----------------|
| Pack doors | [`life_p0.yaml`](../../src/ada/harness/packs/life_p0.yaml): packs `gym_start` → `life_gym_start`, `gym_end` → `life_gym_end`; aliases (“start gym”, “close gym”, “end workout”); optional chip |
| Router / fast path | [`pack_router.py`](../../src/ada/harness/pack_router.py); [`loop.py`](../../src/ada/harness/loop.py) — execute start/end; speak from receipt (extend `_speak_gym_status` or small `_speak_gym_end`) |
| Split ask-once | On `gym_start` (and optionally first `lift_log` when no split): if `get_fact("gym_split")` missing → `needs_confirm` with proposed `days` slots (cortex/operator-filled); Yes → write FACT; No → open session **without** sticky split |
| Confirm wire | Add `life_split_set` (preferred) to toolspec + `life_tools` + `_CONFIRMABLE_TOOLS` + `CONFIRMABLE` in stream.js |
| Dream | Ensure `gym_split` / non-whitelist stays staged — already non-whitelist; add explicit stage guard in [`merge.py`](../../src/ada/dream/merge.py) if any path could auto-merge whole-doc facts (belt-and-suspenders for F-M22-3) |

**Acceptance**
- [ ] Empty data root: “start gym” opens session via pack **without** editing YAML first (F-M22-1).
- [ ] Missing split → Confirm card on phone; Deny → session open, **no** `facts/gym_split.yaml` (F-M22-2).
- [ ] Yes → `get_fact("gym_split")` found; `gym_status` receipt includes it.
- [ ] No hardcoded PPL/coffee/split in Python (F-M22-6).
- [ ] Mouth speaks start/end from receipt; muscles still present if B3 landed (overlap).

**Tests to add:** `tests/test_m22_gym_teach.py` (or extend `test_m19a_pack_router.py` + new falsifier file)  
- Pack routes `gym_start` / `gym_end`  
- Missing split → `needs_confirm`; confirmed write; deny no file  
- `gym_status` reads written FACT  

**Parallel with:** none of slices 2–4 (2 depends on closed sessions from packs; 3–4 independent of gym but keep PRs serial for review clarity — **3 and 4 can parallel after 1** if staffing allows).

---

### Slice 2 — Last-session weights  
**Scope:** ~S–M · **est. S**  
**Depends on:** Slice 1 optional (works off any closed session); safer after packs so phone can close sessions.

| Work | Paths / symbols |
|------|-----------------|
| Query | New helper in [`gym.py`](../../src/ada/logs/gym.py) e.g. `last_closed_sets(exercise_id)` — join closed session |
| Surface | Attach on `lift_log` receipt and/or `gym_status` when exercise_ids known; optional pack hint for “what did I last use for bench” |
| Mouth | Template/speak from receipt fields only; numeric guard ([`mouth.py`](../../src/ada/harness/mouth.py)) |

**Acceptance**
- [ ] Closed session A, same `exercise_id` in B → receipt shows prior load×reps.
- [ ] Open-only prior session **ignored** (hygiene: old open sessions — see Risks).
- [ ] No invented kg (F-M22-9 / mouth fail-closed).

**Tests:** unit on SQL helper + receipt shape; no Gemini in CI.

**Bugfix overlap:** B3 muscles on `gym_status`/`gym_end` — add last-weight fields beside muscles; don’t strip muscles.

---

### Slice 3 — Habits resolve (M21) then Confirm-create (M22)  
**Scope:** ~M · **est. M**  
**Depends on:** M21 food/people pattern (METAL); **3a before 3b**.

#### 3a — Habits resolve (M21 implement-next #5)

| Work | Paths |
|------|-------|
| Spine | [`habit_spine.py`](../../src/ada/harness/habit_spine.py): many → `needs_confirm` + candidates; unique → bind `habit_id` |
| Gate | Reuse / thin-wrap [`resolve_gate.py`](../../src/ada/harness/resolve_gate.py) candidate preview (`habit_id` as id) |
| Loop | [`loop.py`](../../src/ada/harness/loop.py) `_fast_path_habit`: on confirm pending, speak Confirm line (skip register invent) |
| HUD | Allowlist `life_habit_do` / `life_habit_miss` (and routine if needed) in routes_api + stream.js |

**Acceptance:** ambiguous name → Confirm; Yes binds gateway `habit_id`; No fail-closed (F-M21-7 class).

#### 3b — Unknown habit Confirm-create (M22)

| Work | Paths |
|------|-------|
| Create tool | Prefer **`life_habit_create`**: args `display_name`, optional `aliases`/`schedule`, `confirmed`; calls `upsert_habit_definition(..., source="teach_in_flow")` |
| Flow | 0 matches on tick → Confirm-create (proposed name from utterance) → on Yes create then optional same-turn tick |
| Seed | Keep `ada life habit-seed` optional; do **not** require for HUD smoke (F-M22-1). Update any doc that still says “seed before smoke.” |

**Acceptance**
- [ ] Empty habit catalog + Agent: “done skincare” → Confirm-create → sticky def → tick works (F-M22-1).
- [ ] No silent SQL insert (F-M22-2).
- [ ] Skincare not the only working path in Python (F-M22-6) — seed remains test/optional door.

**Tests:** `tests/test_m22_habits_teach.py` + extend `test_m21_resolve_clarify.py` for habit many-bind.

**Parallel:** Slice 4 can run in parallel with 3 once staffing allows (no shared store).

---

### Slice 4 — Brief section prefs  
**Scope:** ~S–M · **est. S**  
**Depends on:** none hard; soft-depends on Today keys being stable.

| Work | Paths |
|------|-------|
| Prefs | `prefs.brief_include` list; coerce in [`facts.py`](../../src/ada/memory/facts.py) `_coerce_pref_value` — **omit** from `WHITELIST_KEYS` |
| Consume | [`today.py`](../../src/ada/hud/today.py) `build_today` (and any wake/EOD brief composer if separate) filters sections by list; absent key = all |
| Teach | Pack/alias or charter assist → `memory_facts_propose_edit` with proposed list; Confirm Yes |
| Dream | Assert merge stages `brief_include` (non-whitelist) — F-M22-3 |

**Acceptance**
- [ ] “Don’t put gym in the morning brief” → Confirm → subsequent Today/brief omits `open_gym` (or agreed key).
- [ ] Brief content still from receipts/named stores only (F-M22-9).
- [ ] Dream does not auto-merge the list (F-M22-3).

**Tests:** prefs coerce + `build_today` filter + Dream stage unit.

**Phone-first:** Confirm card only; **no** new dashboard for section toggles.

---

## Phone-first UX (all slices)

- Confirm Yes/No on **this** ingress window (M20b/c) — extend existing Confirm card; reuse candidate list chrome where useful (split days / habit names).
- Speak from receipts / canned Confirm lines; [`mouth.py`](../../src/ada/harness/mouth.py) already skips register pass on `needs_confirm`.
- No new Body/Habits dashboard; no ear Yes; no TTS-as-Confirm.

---

## Data posture

| Rule | Note |
|------|------|
| Additive only | New FACT fields / SQL rows; no schema re-birth |
| Durable root | Prod: operator `ADA_DATA_ROOT` / ada-data mount |
| Tests | Sandbox via `ADA_DATA_ROOT` fixture (`data_root`) — **do not** move test tree “to protect memory” (M20) |
| Optional seed | CLI/YAML write **same** keys; labeled `source=seed` where applicable |

---

## Out of scope / won’t-chase

| Out | Why |
|-----|-----|
| Package / first-run interview | M20 phase 4; optional same-store door later |
| Mail, retrieval mega-slice, work campaigns | M20 / later sibling |
| Food ML; Gemini `ref_id`; ear Yes | M21 / M22 locks |
| Second cortex; Dream rewrite; mode collapse | POLICY |
| New prefs/life DB | Extend existing FACTS/SQL |
| PR wall / weekly volume / Hevy social | M19 P4 later |
| Hardcoded Aryan biography in Python | F-M22-6 |
| Closing/orphaning all historical open gym sessions as product | Hygiene note only (Risks) |

---

## Risks

| Risk | Mitigation |
|------|------------|
| **Bugfix overlap** (B1 food, B2 cortex.empty / aliases, B3 gym muscles) | Don’t rewrite resolve ranking, meal salvage, or muscle attachment; if editing `gym.py` / `loop.py` / `pack_router.py` / `food.py`, rebase on those commits. Touch-points: `gym.py` (`_exercise_muscle_summary`, `gym_status`/`gym_end`), `loop._speak_gym_status`, `pack_router` meal/due aliases, `meal_spine` / `resolve_gate`. |
| **Habit-seed gravity** | Smokes must pass on empty catalog + Confirm-create; keep seed for fixtures only; update P1 docs that still say “seed before smoke.” |
| **Old open gym sessions** | Phone review noted open session since 2026-08-17. Last-weights ignore non-closed. Slice 1 may optionally surface “open session already” on `gym_start` (honest status) — **do not** auto-close without Confirm. Operator/CLI hygiene out of band. |
| **propose_edit vs life_split_set** | Pick one in slice 1; dual paths confuse HUD allowlist. |
| **brief_include accidentally whitelisted** | Code review checklist: never add to `WHITELIST_KEYS`. |

---

## Suggested first Agent prompt (slice 1 — copy-paste)

```text
Implement M22 Slice 1 only (gym packs + split ask-once). Authority:
docs/modules/M22_LIFE_TEACH_IN_FLOW.md v1.0 + docs/reviews/M22_IMPLEMENT_PLAN.md.

Do:
1. Wire gym_start / gym_end packs + aliases in life_p0.yaml; pack_router + loop fast-path;
   speak from life_gym_start / life_gym_end / life_gym_status receipts (keep B3 muscles if present).
2. Missing get_fact("gym_split") on gym_start → needs_confirm; Yes writes facts/gym_split.yaml
   (schema: days → {label, body_parts[]}). Prefer new life_split_set(confirmed=…) mirror
   favorites; allowlist in routes_api._CONFIRMABLE_TOOLS + stream.js CONFIRMABLE.
3. No → open session without sticky split. No silent FACT write. No hardcoded PPL.
4. Tests: pack route + Confirm write/deny + gym_status reads FACT. Sandbox ADA_DATA_ROOT only.
5. Do not start: last-session weights, habits, brief_include, package, food ML, Dream rewrite.
6. If phone bugfix (coffee/Gott, cortex.empty, gym muscles) already landed, do not revert those.

Out: no commits unless I ask. Phone-first Confirm; no new dashboard.
```

---

## Slice order summary (for chat handoff)

| Order | Slice | Est. | Can parallel? |
|-------|-------|------|----------------|
| 1 | Gym packs + split ask-once | M–L | First |
| 2 | Last-session weights | S | After 1 (or soft-after any closed data) |
| 3a→3b | Habits resolve then Confirm-create | M | After 1; parallel with 4 |
| 4 | Brief `brief_include` | S | Parallel with 3 |

**Recommended sequence for solo implement:** 1 → 2 → 3 → 4.

---

*End M22 implement plan. Plan only — not METAL.*
