# M26 gym — Phase 2 cited domain memory (second vertical)

**Status:** **Phase 2 card shipped (2026-09-17)** — gym **organ** (start / lift / end / split packs) is in-tree. **Do not rebuild** `gym_start` / `gym_end` / `life_split_set`. Reflection is **today-only** `life_gym_status` — no gym day/week SQL yet. **Not closed.** **Next = capture smoke gaps → gym_week → food+gym day-join.**  
**Date:** 2026-09-17 (v1.0)  
**Host:** `ada-pi5` (Raspberry Pi 5, 8 GiB) · windows: Mac / phone via Tailscale Serve  
**Branch:** `rewrite/v1-body`  
**Kind:** **Phase 2 cited domain memory** for **gym only** — organ wiring + organism purpose + Dream contract. Not a training textbook. Not cortex prompt stuffing. Not P4 charts. Not a Hevy clone.  
**Depends on:** [`M26_DOMAIN_KNOWLEDGE.md`](./M26_DOMAIN_KNOWLEDGE.md) (organ · reference · reject; purpose lock) · [`M19a_P0_LIFE_CAPTURE.md`](./M19a_P0_LIFE_CAPTURE.md) (gym verbs, `exercise_catalog`, sessions/sets) · [`M22_LIFE_TEACH_IN_FLOW.md`](./M22_LIFE_TEACH_IN_FLOW.md) (split ask-once; last-session **read** — **body stale** on packs, see audit) · [`M24_MULTI_INTENT_CAPTURE.md`](./M24_MULTI_INTENT_CAPTURE.md) (multi-set ladder; fail closed) · [`M10_MEMORY_KNOWLEDGE.md`](./M10_MEMORY_KNOWLEDGE.md) (library ≠ logs) · [`M04_MEMORY_DREAM.md`](./M04_MEMORY_DREAM.md) (WORLDVIEW cites; Dream must not auto-merge `gym_split`)

**Feeds:** gym capture **phone smokes** (gaps below) → **`life_gym_day` / `life_gym_week` SQL** (mirror food) → food+gym `local_day` join (**after** gym week, not this card). Time / habits / people / dues Phase 2 cards copy the **domain close checklist**. M27 gym rank · Hevy import · PR curves · gym HUD sheet stay **OPEN later**.

**Name stays `M26_GYM_DOMAIN.md`:** git-tracked **reference know** for gym. Sibling of [`M26_FOOD_DOMAIN.md`](./M26_FOOD_DOMAIN.md) and the agnostic lock, not a charter dump. Runtime `memory/domain/gym.md` is **not** shipped here — boot/brief cannot load that path (charter injects FACT slice + WORLDVIEW digest only; `paths.py` has no `domain/` dir). Module doc is the source of truth until a later chat wires a capped slice.

**Supersedes:** any reading that (a) “knowing gym” = prompt physiology, (b) this essay belongs in charter, (c) RAG can replace `gym_sets` rows, (d) analysis / coverage charts before honest capture, (e) Dream may invent `load_kg` or auto-merge `gym_split`, (f) [`M22_LIFE_TEACH_IN_FLOW.md`](./M22_LIFE_TEACH_IN_FLOW.md) **body** still saying gym **packs GAP** / last-session **GAP** (tools + packs + `last_closed_*` are in-tree — M22 prose is stale), (g) last-session weights **SHIPPED** = phone-proven (pytest only). **Does not supersede:** M26 three kinds of know; M19a gym schemas; M22 split Confirm + last-closed **design**; M24 fail-closed parse; code binds `exercise_id`.

### Changelog

| Ver | Date | Delta |
|-----|------|-------|
| **v1.0** | 2026-09-17 | First Phase 2 domain card: gym purpose + honest METAL/GAP/PHONE OPEN audit + Dream contract + reject fence. **No Python.** Packs `gym_start`/`gym_end`/`lift_log`/`gym_status` exist (`life_p0.yaml`) — do not rebuild. Next implement = capture smokes, then gym week SQL (mirror food), then food+gym day-join. |

---

## Metal audit (2026-09-17 — code first; M22 body stale)

**Tags:** **METAL** = in-tree (pytest OK). **PHONE METAL** = live phone run cite. **PHONE OPEN** = code and/or HUD pytest, **no** phone jsonl — do not say SHIPPED. **GAP** = not in tree. Do **not** rebuild start / end / split.

| Item | In-tree | Tag |
|------|---------|-----|
| Pack `gym_start` | [`life_p0.yaml`](../../src/ada/harness/packs/life_p0.yaml) verb + aliases `start gym`; fast path [`loop.py`](../../src/ada/harness/loop.py) `_fast_path_gym_start` | **METAL** (M22 “packs GAP” is **stale**). **PHONE METAL** — [`96a74984…`](../reviews/2026-08-26_phone_96a74984_m22.md) `start gym` → split Confirm |
| Pack `gym_end` | aliases `close gym` / `end gym` / `end workout`; `_fast_path_gym_end` | **METAL**. **PHONE METAL** — [`c369f86f…`](../reviews/2026-08-26_phone_c369f86f.md) B3 close gym → catalog muscles |
| Pack `lift_log` | `log lift:` + `_LIFT_LINE` / ladder; [`gym_spine.py`](../../src/ada/harness/gym_spine.py) `build_lift_log_args` | **METAL** (pytest HUD [`M19a_P01g`](../reviews/M19a_P01g_HUD_SMOKE.md); M24 ladder). **PHONE OPEN** — no dedicated lift jsonl (B3 implies a catalog lift was logged first; not a lift-NL cite) |
| Pack `gym_status` | aliases `what did i lift` / `split today` → `life_gym_status` | **METAL** today-read. **PHONE OPEN** as a named status utterance. Pack does **not** pass `date`/`days` (unlike nutrition) |
| `life_gym_start` / `life_gym_end` / `life_lift_log` / `life_gym_status` | [`life_tools.py`](../../src/ada/tools/life_tools.py) + [`toolspec.py`](../../src/ada/tools/toolspec.py) | **METAL** |
| `life_split_set` | Confirm write [`gym_split.py`](../../src/ada/logs/gym_split.py); empty labels rejected (H3) | **METAL**. **PHONE METAL** — `96a74984…` H3 |
| `gym.py` sessions / sets | `gym_start` · `lift_log` (auto-session on first set) · `gym_end` · `gym_status` | **METAL** |
| Last-session weights | `last_closed_sets` / `last_closed_receipt_fields`; receipt `last_load_kg` / `last_reps`; tests [`test_m22_gym_teach.py`](../../tests/test_m22_gym_teach.py) | **METAL** (pytest). **PHONE OPEN** — no phone cite. M22 body “GAP” is **stale for code** |
| `exercise_catalog` | [`schema.py`](../../src/ada/logs/schema.py) + [`gym_import.py`](../../src/ada/logs/gym_import.py) `ensure_exercise_catalog`; fold/alias; FACTS custom on miss | **METAL**. **PHONE METAL** (indirect) — B3 muscles from catalog. Fetch/seed is boot, not Hevy |
| `life_gym_day` / `life_gym_week` | — | **GAP** (next implement after capture smokes). `gym_status(date=)` exists on the tool; NL/pack still **today-only** |
| Food+gym `local_day` join | — | **GAP** — **after** gym week; named in **Next** only |
| M27 `exercise_catalog` rank | food-only [`catalog_rank.py`](../../src/ada/harness/catalog_rank.py) | **OPEN later** — not this card; do not copy food rank ifs |
| Hevy import / PR curves / gym HUD sheet | catalog seed ≠ Hevy; no `life_lift_fix` tool; Body sheet unbuilt ([`M19b`](./M19b_DAILY_SURFACE_VOICE.md) PARK) | **OPEN later** |

**Do not reopen as this card’s job:** rewrite start/end/split; food features; M27 gym rank implement; food+gym join implement.

---

## One-liner

Gym domain = **honest load × volume for personal adaptation research**. SQLite `gym_sets` (`load_kg`, `reps`, `exercise_id`) are **truth**; this doc is a **lens** for briefs/Dream later — never a source of invented kilograms, never a substitute for the catalog.

---

## Signal / organism purpose (reference know, cited)

Humans are signal-driven organisms. Gym capture exists so ADA can later read **load × volume → adaptation** and **coverage vs the operator’s split** — not so the cortex can role-play a coach on every `lift_log`.

| Why log | What the signal is **for** |
|---------|----------------------------|
| Load (`load_kg`) | Stimulus intensity. Bodyweight = honest **null**, not invented 0. Never guess kg. |
| Volume (load × reps, session tonnage) | Dose. Sum from **logged** sets only. |
| Sets / reps | Repeatable units inside a session. Ladder = N rows, one tool (M24). |
| Catalog bind | Movement + body_parts for later coverage vs `gym_split` — **ids code-bound**. |
| Split FACT | What the operator **meant** this week to train — teach-in Confirm, not baked PPL. |
| Session open/close | Bout boundaries so “last closed” is a real prior, not the open set just logged. |

**Interpretive classes only — no invented set values.** A logged set’s kg/reps come from spine parse (or structured args). This card does not assign “bench = N kg.” Catalog names/muscles come from `exercise_catalog` / custom FACTS — not this prose.

**Personal informatics:** collection (this organ) is the daily path; integration/reflection (week SQL, P4 charts, food+gym join) wait until logs are honest ([Li et al., CHI 2010](https://doi.org/10.1145/1753326.1753611); [Choe et al., CHI 2014](https://doi.org/10.1145/2556284.2556964)). Last-closed lookback is Hevy-class **read** of prior sets ([M19b](./M19b_DAILY_SURFACE_VOICE.md) · M22) — not a PR wall.

| Claim | Tag | Pointer |
|-------|-----|---------|
| Collection vs reflection stages | **EVIDENCE** | [Li et al., 2010](https://doi.org/10.1145/1753326.1753611) |
| Self-trackers collect first, explore later | **EVIDENCE** | [Choe et al., 2014](https://doi.org/10.1145/2556284.2556964) |
| Purpose: load × volume → adaptation; coverage vs split | **POLICY** | [`M26_DOMAIN_KNOWLEDGE.md`](./M26_DOMAIN_KNOWLEDGE.md) operator domain signals |
| Set numbers from tools/SQLite, not prompt | **METAL** | `gym.py` `gym_sets.load_kg` / `reps` · `gym_spine.py` fail closed |
| Catalog ids code-bound | **METAL** | `gym.py` `_lookup_exercise` · never cortex sole-pick |

---

## Organ know — wiring map (METAL, file paths)

Gym **organ know** lives in pack + code + SQLite — not in this markdown.

### Input

| Channel | Shape |
|---------|--------|
| NL utterance | `log lift: flat bench 50kg x6` · bodyweight `pull-ups x8` / `10 pull-ups` / `3x10 pull-ups` (`load_kg: null`) · ladder `lat pulldown 30kg x12 35kg x12 40kg x8` or `30×12/35×12/40×8` · multi-exercise `,` / `and` / `then` |
| Session | `start gym` → open `gym_sessions`; first `lift_log` **auto-opens** if none |
| Close | `end gym` / `close gym` / `end workout` |
| Status | `what did i lift` / `split today` — **today** local day |
| Split teach-in | missing `gym_split` FACT on `gym_start` → Confirm `life_split_set` (empty labels rejected) |

### Spine

[`src/ada/harness/gym_spine.py`](../../src/ada/harness/gym_spine.py) `build_lift_log_args`:

strip `log lift:` prefix → whole-utterance ladder first → else split `,` / `/` / `and` / `then` → per piece: load×reps · bodyweight · reps-first. **Fail closed** if any piece incomplete (`incomplete_parse` + ask) — never silent no-tool (M24 F-M24-3). kg/lb → `load_kg`; bodyweight keeps `load_kg` **null**.

Fast path: pack `lift_log` → `_fast_path_lift` → `life_lift_log`. `gym_start` / `gym_end` have dedicated fast paths (do **not** rebuild). Mouth speaks from receipt only (M23).

### Tools

| Tool | Role |
|------|------|
| `life_gym_start` | Open session; optional `split_day` |
| `life_lift_log` | Write `sets[]`; catalog bind; attach last-closed fields when a **closed** prior exists |
| `life_gym_end` | Close active session; duration, set_count, tonnage_kg, catalog `muscles` |
| `life_gym_status` | Active session + **today’s** sets + `gym_split` FACT; last-closed on today’s exercises |
| `life_split_set` | Sticky `facts/gym_split.yaml` after Confirm Yes; reject empty-label shell |

Handlers: [`src/ada/tools/life_tools.py`](../../src/ada/tools/life_tools.py). Pack: [`packs/life_p0.yaml`](../../src/ada/harness/packs/life_p0.yaml) verbs `lift_log` · `gym_start` · `gym_end` · `gym_status`.

**Not in tree (do not invent here):** `life_gym_day` · `life_gym_week` · `life_lift_fix`.

### DB / FACTS

| Store / door | Path / host |
|--------------|-------------|
| Session + set truth | `/mnt/ada-data/logs/life_logs.db` — `gym_sessions`, `gym_sets`, `exercise_catalog` |
| Split FACT | `facts/gym_split.yaml` — `{schema_version, days.{mon…sun: {label, body_parts[]}}}` |
| Custom exercises | `facts/gym_custom_exercises.yaml` — miss → persist (P0) |
| Catalog seed | free-exercise-db fetch on empty catalog, else bundled seed (`ADA_GYM_CATALOG_FETCH=off`) |

Code: [`src/ada/logs/gym.py`](../../src/ada/logs/gym.py), [`gym_split.py`](../../src/ada/logs/gym_split.py), [`gym_import.py`](../../src/ada/logs/gym_import.py), [`gym_custom.py`](../../src/ada/logs/gym_custom.py).

### Resolve chain

```text
LIFT INTENT
  pack_router → lift_log  (prefix / kg×reps / ladder)
  gym_spine   → sets[] or fail closed (no invent kg)

BIND (code, not cortex)
  exercise_catalog exact name
    → aliases_json
    → alnum/plural fold (pull-ups ≡ Pullups)
    → FACTS gym_custom_exercises
    → create custom on miss (facts_custom_new)
  exercise_id written on gym_sets — never Gemini sole-pick

SESSION
  open session or auto-open on first lift
  last_closed_* from most recent status='closed' same exercise_id
    (open session ignored — F-M22 last-weights hygiene)

SPLIT (ask-once, not every lift)
  gym_start + no gym_split FACT → life_split_set Confirm
  Deny → session stays open, no FACT file
  empty labels → re-ask (phone H3)

  mouth = receipt / Confirm / refuse only
```

Gym has **no** food-style Confirm picker on catalog ambiguity and **no** M27 rank ifs on this path. Miss → custom FACT, not USDA. Do not copy food rank here.

### Write shape

Per `gym_sets` row:

| Field | Meaning |
|-------|---------|
| `load_kg` | Parsed kg (lb converted) or **null** (bodyweight). Never 0-as-ok for a missed parse. |
| `reps` | Integer from spine |
| `exercise_id` | Catalog or `custom_…` — code-bound |
| `exercise_name_raw` | Operator surface form |
| `session_id` | Open (or auto) session |
| `logged_at` | UTC ISO |

Receipt (`life_lift_log` ok): `{receipt_id, session_id, set_ids[], exercise_names[], resolved[], volume_kg}` + optional `last_load_kg` / `last_reps` / `last_session_id`. End receipt: `{duration_s, set_count, tonnage_kg, exercises[].muscles}`. Gateway **refuses** empty `sets[]`. Spine **asks** instead of writing incomplete pieces.

**Mouth gap (capture smoke):** `_speak_lift_log` reads `load_kg`/`reps` off `resolved[0]`; `lift_log` does **not** copy the just-logged load onto `resolved[]`. Ack may omit “50 kg × 6” even when SQLite is honest. Do not invent kg to fill the sentence — fix in a later capture-smoke chat (no code here).

### ASCII flow

```text
utterance  ("start gym" / "flat bench 50kg x6" / "end gym")
   │
   ├─ pack_router
   │     gym_start  → life_gym_start → maybe life_split_set Confirm
   │     lift_log   → gym_spine → sets[] → life_lift_log
   │     gym_end    → life_gym_end
   │     gym_status → life_gym_status  (today only)
   │
   ├─ gym.py
   │     catalog / custom bind → gym_sets
   │     last_closed_* from closed sessions only
   │
   └─ mouth → receipt / Confirm / ask only
   cortex (agent): speak/clarify only — never commit exercise_id or kg
```

---

## Reject fence

This doc (and any future capped slice) must **never**:

| Never | Why |
|-------|-----|
| Invent `load_kg` / reps when spine miss | Truth > charm; M26 F-M26-1 |
| Domain essay in charter / pack prompt | Unbounded, unverifiable (F-M26-2) |
| RAG / WORLDVIEW as set log | Structured logs > RAG (`00` §3.3) |
| Dream auto-merge `gym_split` | Teach-in Confirm only; Dream **stages** `gym_split` ([`dream/merge.py`](../../src/ada/dream/merge.py)) |
| Coverage / PR charts as a capture gate | F-M26-3; P4 later |
| Food-style rank ifs on `exercise_catalog` | M27 gym rank is **OPEN later**; do not patch bind with meal demote rules |
| Photo / form-check as capture | Not a camera pose organ |
| Cortex sole-pick `exercise_id` after “reading” this card | M21 / F-M26-6 |
| Rebuild `gym_start` / `gym_end` / split packs | Already METAL |
| Mouth claim “Logged” when tool `ok:false` | M23 receipt honesty |

**Falsifiers copied (gym-relevant):**

| ID | Fail if… |
|----|----------|
| **F-M26-1** | Set write uses load/reps **not in the tool receipt** because “domain knowledge” |
| **F-M26-2** | Charter or pack prompt contains a **gym physiology essay** as the daily capture path |
| **F-M26-3** | Analysis/brief charts run on days where capture is **systematically empty/dishonest** without saying so |
| **F-M26-4** | Daily `lift_log` triggers **unbounded web/search** or ReAct for domain facts |
| **F-M26-5** | This prose **overwrites** FACTS (`gym_split`) or SQLite rows without Confirm |
| **F-M26-6** | Cortex **sole-picks** `exercise_id` after reference doc retrieval |

M22/M24 gym falsifiers still bind (empty split sticky; last-weights from an **open** session; incomplete ladder silent-write).

---

## Reflection contract (deterministic)

**Not Dream.** Reflection = SQL + rules on structured logs. No LLM for volume/coverage/week patterns on the read path.

Food already has `life_nutrition_day` + `life_nutrition_week` ([`food_reflection.py`](../../src/ada/logs/food_reflection.py) `nutrition_window`). **Gym today is today-only `life_gym_status`.** This card **names** gym day/week SQL as the **next implement** (mirror food). **Do not code it here.**

### Reads (inputs) — today

| Input | Source |
|-------|--------|
| Today’s sets + active session | `life_gym_status` → `gym_sets` filtered to local today via `logged_at` |
| Split | `facts/gym_split.yaml` if present |
| Last closed | `last_closed_receipt_fields` on today’s `exercise_id`s |

### Named next implement (not this card)

| Tool (name lock) | Mirror of | Shape (design only) |
|------------------|-----------|---------------------|
| `life_gym_day` | `life_nutrition_day` | One **local** calendar day: sets, session(s), tonnage, split label; pack must pass `date` (yesterday / explicit). `gym_status(date=)` is **not** the NL door — alias `what did i lift` does not set `date`. |
| `life_gym_week` | `life_nutrition_week` | Last N local days on `gym_sets` / sessions — deterministic patterns (coverage vs split, volume, rest days); cites `gym:day:YYYY-MM-DD` only; scratch JSON optional. Pack must pass `days`. |

**TZ note (same as food):** `gym_sets.logged_at` / session stamps are UTC ISO; read `date` is operator `preferred_tz`. Mouth must speak **local** date/window — not raw UTC.

### Writes (outputs)

| Output | Path |
|--------|------|
| Today status | tool receipt only (no gym rollup table yet) |
| Week scratch (when gym_week ships) | proposed `/mnt/ada-data/scratch/gym_reflection_latest.json` — atomic overwrite; **not shipped** |

**No** WORLDVIEW gym digests from reflection. **No** FACT auto-merge of `gym_split`.

### Must not

- Invent kg or fill null bodyweight as 0.
- Run LLM for week tonnage on Observe fast path.
- Auto-merge into FACTS (`gym_split`, `gym_custom_exercises`).
- Treat coverage charts as a write gate.

### LLM narrative

On-demand brief narrative = **later slice**. Numbers always from tools/SQL first.

---

## Analysis / brief (P4, later)

Once logs are honest, these become **possible** — they are **forbidden as a gate** for P0 write (F-M26-3).

| Later question | Needs |
|----------------|--------|
| Volume vs last week | `life_gym_week` (GAP) |
| Coverage vs split | week window + `gym_split` + catalog `body_parts` |
| Last-closed vs today | already receipt fields — not PRs |
| Food+gym synergy | **Join protein days to lift volume on `local_day`** — **after gym week**, not this card |
| PR curves | OPEN later — not capture |

Do not ship charts, Hevy clone UI, or “am I doing good?” coaching in this Phase 2 card.

---

## Domain close checklist (copy from M26)

Reusable close order — **path first, ranking last** ([`M26_DOMAIN_KNOWLEDGE.md`](./M26_DOMAIN_KNOWLEDGE.md)):

pack door → resolve gate → Confirm sticky → mouth = receipt → smokes → **reflection (deterministic SQL on logs)** → doc.

**Read path:** pack router must pass **`date` / `days` args** for gym day/week reads — alias substring (`what did i lift`) alone is insufficient. **Lift writes:** spine parse only; `life_lift_log` commit requires complete `sets[]` (M24 fail closed); code binds `exercise_id`. **Confirm:** split is ask-once (`life_split_set`), not a food picker; last-session is **read**, not Confirm. **Vocative (M26 v1.8, later):** strip `hi/hey ada` before verb name scrape; still Verb→Pack, not a chat turn.

Gym status on the seven steps:

1. **Pack door** — NL shapes route Verb→Pack→spine (no freestyle bypass). **METAL** for start / end / lift / today-status. **GAP:** gym day/week verbs + date/days args.
2. **Resolve gate** — code binds `exercise_id`; fail closed on incomplete parse. **METAL** fold/alias/custom. **Not** food Confirm-on-ambiguity. M27 rank **OPEN later**.
3. **Confirm sticky** — Yes writes **labeled** `gym_split` only; empty shell rejected. **PHONE METAL** `96a74984…`. Custom exercise persist is P0 miss-path, not split Confirm.
4. **Mouth = receipt** — ack only from tool outcome. **PHONE METAL** end-session muscles `c369f86f…`. **PHONE OPEN:** last-closed speak; just-logged kg on lift ack (resolved rows omit current load).
5. **Smokes** — phone + pytest with run cites; pytest last-session ≠ phone closed.
6. **Reflection** — **GAP:** `life_gym_day` / `life_gym_week`. Today `life_gym_status` is not week SQL. Dream/LLM not required for numeric patterns.
7. **Doc** — this card **v1.0**; OPEN ≤4 remainders (not rank whack-a-mole).

**Root-cause rank (same as food):** path bypass ≫ sticky poison ≫ rank demote ≫ mouth lie. Gym has not earned a food-style rank fight; do not start one here.

---

## Operator smoke / falsifiers

### Phone smokes (capture — do not skip)

| Utterance | Expect | Evidence |
|-----------|--------|----------|
| `start gym` (no split FACT) | Session open; Confirm named split; Deny = no `gym_split.yaml` | **PHONE METAL** [`96a74984…`](../reviews/2026-08-26_phone_96a74984_m22.md) |
| Split Yes with empty labels | Re-ask; no sticky shell | **PHONE METAL** same (H3) |
| `log lift: flat bench 50kg x6` | `life_lift_log`; set `load_kg=50` `reps=6`; catalog id | **METAL** pytest P01g. **PHONE OPEN** |
| `log lift: pull-ups x8` | `load_kg` **null**; catalog fold hit | **METAL** P05 HUD list. **PHONE OPEN** |
| Ladder `30kg x12 … 40kg x8` | One tool, three `gym_sets` | **METAL** [`test_m24_gym_multi_set.py`](../../tests/test_m24_gym_multi_set.py). **PHONE OPEN** |
| Incomplete lift (name only) | Ask; **no** row; no invented kg | **METAL** M24 fail closed. **PHONE OPEN** |
| `end gym` / close after catalog lift | Muscles from catalog on receipt; mouth from JSON | **PHONE METAL** [`c369f86f…`](../reviews/2026-08-26_phone_c369f86f.md) B3 |
| `what did i lift` | Today set count / open session via `life_gym_status` | **METAL** pack. **PHONE OPEN** |
| Second session same lift after close | Receipt `last_load_kg` × `last_reps` from **closed** prior | **METAL** pytest. **PHONE OPEN** |

### Fail if

| Fail | Anti-pattern |
|------|----------------|
| Invented kg | Incomplete parse written as 0 / guessed load |
| Open-session “last” | Last-closed reads the still-open bout |
| Empty split sticky | All days `label: ''` after Yes |
| Pack bypass | Freestyle `life_lift_log` without spine `sets[]` |
| Lying mouth | Tool `ok:false` but text says “Logged…” |
| Rank-ifs on gym | Food demote rules copied onto `exercise_catalog` |

---

## OPEN (≤4) — later / parked (not this card’s implement)

| # | Question | Default until a later chat locks it |
|---|----------|-------------------------------------|
| 1 | **Hevy import?** | Native `lift_log` stays P0. Catalog seed (`gym_import.py` / free-exercise-db) is **not** Hevy. CSV/API import = LATER ([`M19`](./M19_TIER_B_LIFE_ADMIN.md) `gym_import`). |
| 2 | **PR curves / week charts?** | Deferred until `life_gym_week` exists and logs are honest. Not a capture gate (F-M26-3). |
| 3 | **Gym HUD sheet?** | Chat + Today strip stay. Body/gym sheet = M19b PARK — not a Hevy live table clone. |
| 4 | **M27 exercise rank + vocative filler?** | Gym `exercise_catalog` bind parity **after** this card’s capture/week path — no food-style rank ifs now. Vocative `Hi Ada. Start gym` = food OPEN #4 later: strip `hi/hey ada` like `please`/`yes`; still Verb→Pack, **not** a Gemini chat turn. |

**Active reopen path for next chats:** capture smoke gaps (table above, PHONE OPEN rows) → gym day/week SQL → then food+gym `local_day` join.

**Do not reopen:** invent kg; essay in charter; Dream auto-merge `gym_split`; coverage-charts-as-write-gate; food rank ifs; photo form check; rebuild start/end/split; food features; M27 gym rank **implement** on this card; food+gym join **implement** on this card.

---

**Next:** gym **capture smoke gaps** (lift NL + last-closed + status on phone; mouth kg from receipt) → **`life_gym_week`** (and `life_gym_day`; mirror food; pack `date`/`days`) → **food+gym `local_day` join** (after gym week). No Python in this slice.

*End M26 gym. Phase 2 card 2026-09-17 (v1.0) — packs METAL, do not rebuild start/end/split; reflection today-only; logs are truth; this doc is the lens.*
