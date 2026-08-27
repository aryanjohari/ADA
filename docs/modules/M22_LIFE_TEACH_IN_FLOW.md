# M22 — Life teach-in-flow (research · pick)

**Status:** design lock — **not code**  
**Date:** 2026-08-26 (v1.0)  
**Host:** `ada-pi5` (Raspberry Pi 5, 8 GiB) · windows: Mac / phone via Tailscale Serve  
**Branch:** `rewrite/v1-body`  
**Kind:** M20 **life-vision / personalization delta** — how ADA gets personal *while talking*. Not a second cortex. Not retrieval. Not package. Not mail. Not food ML.  
**Depends on:** [`M20_V1_PRODUCT.md`](./M20_V1_PRODUCT.md) (sequence; this card sits **after M21, still before phase-4 package**) · [`M21_RESOLVE_CLARIFY.md`](./M21_RESOLVE_CLARIFY.md) (Confirm-bind; favorites METAL) · [`M19_TIER_B_LIFE_ADMIN.md`](./M19_TIER_B_LIFE_ADMIN.md) · [`M19a_P0_LIFE_CAPTURE.md`](./M19a_P0_LIFE_CAPTURE.md) · [`M19a_P1_HABITS_PEOPLE.md`](./M19a_P1_HABITS_PEOPLE.md) · [`M19b_DAILY_SURFACE_VOICE.md`](./M19b_DAILY_SURFACE_VOICE.md) / [`M20a_VOICE_PATH.md`](./M20a_VOICE_PATH.md) / [`M20b_PHONE_FACE.md`](./M20b_PHONE_FACE.md) / [`M20c_MAC_DISPLAY_FACE.md`](./M20c_MAC_DISPLAY_FACE.md) (mouth / Confirm-on-ingress) · [`../02_CONSTITUTION.md`](../02_CONSTITUTION.md) · [`../00_ASSISTANT_RESEARCH.md`](../00_ASSISTANT_RESEARCH.md) §8 · [`../19_JARVIS_JUSTINE_AGENT_RESEARCH.md`](../19_JARVIS_JUSTINE_AGENT_RESEARCH.md) (**Ask Once**; Verb→Pack→fill)

**Name stays `M22_LIFE_TEACH_IN_FLOW.md`:** this is a **product-posture slice** in the M20 sequence (how personal facts enter existing stores), not another M21 Confirm-gate addendum and not an M19a implement rewrite. M21 already shipped **write-path honesty** (candidates + Confirm; code binds ids; favorites after Yes). The remaining failure is architectural in a different direction: docs still read as **“hand-seed YAML / CLI seed or ADA is empty if/else.”** That contradicts the locked Life vision (learn-while-talking). Rejected: stuffing into M21 (would bury vision under resolve METAL history; M21’s IN is id-bind, not bootstrap posture). Not `M19c` (would hide a sequence insert under catalog children). Not `M20d` (M20 children are face/voice polish).

**M21 name collision:** M21 § sibling suggested `M22_RETRIEVE_NEEDLIST.md` for NL-read retrieval. **This card takes M22.** Retrieval stays a **later unnamed sibling** (do not start it here). Pointer updated on M21.

**Supersedes:** any reading that **pre-seed / hand-edit FACTS is the primary personalization path** (M16 empty-stub story as *the* way to know you; M19a P1 “ship empty + operator seed” as *the* habit door; package onboarding as a gate to living). **Does not supersede:** M20 sequence 1→5; M21 resolve locks; Gemini-only cortex; Confirm on ingress; no ear Yes; Verb→Pack→fill; Dream must not auto-merge favorites/people; package-later; work campaigns later.

### Changelog

| Ver | Date | Delta |
|-----|------|-------|
| **v1.0.2** | 2026-08-26 | Pointer only — next sequence feel card → [`M23_FRIEND_MOUTH.md`](./M23_FRIEND_MOUTH.md) (spoken friend register; not teach-in-flow stores). |
| **v1.0.1** | 2026-08-26 | Pointer only — implement plan → [`../reviews/M22_IMPLEMENT_PLAN.md`](../reviews/M22_IMPLEMENT_PLAN.md) (gap map + ordered slices; not METAL). |
| **v1.0** | 2026-08-26 | Design lock from Life vision vs seed-first docs. **Pick:** three equivalent doors to the **same stores** — teach-in-flow (default) · optional first-run interview (package) · optional seed/CLI. Same Confirm integrity as M21. |

---

## One-liner

ADA gets personal by **learning while talking**: first-time ask → Confirm on the ingress screen → sticky FACTS / favorites / habits / gym split / brief prefs. Operator YAML and CLI seed remain **optional doors**, never the required path. Empty stores are honest, not a cue to hardcode Aryan’s life in Python.

---

## Core research question

How should ADA **bootstrap and grow personal life state** so a Justine/Jarvis-class companion on this Pi feels taught-in-flow — without making the operator a YAML janitor, without silent auto-learn, and without waiting for the newborn package?

Secondary lenses:

| Sub-question | Where answered |
|--------------|----------------|
| Where do docs still imply seed-first? | §A |
| Three doors, one store | §B · exec pick |
| Explicit rejects | §C |
| Vision features → phase | §D |
| Sequence vs M20 1→5 | §E |
| Recipe / option matrix | §F–§G |
| Falsifiers | §H |

---

## Scope fence

| IN (this card) | OUT (explicit) |
|----------------|----------------|
| **Posture:** teach-in-flow as default personalization | New FACTS/log organs; second prefs database |
| First-time ask → Confirm → sticky write into **existing** stores | Silent auto-learn; Dream-invented favorites/habits/split |
| Optional first-run interview **and** optional seed as **same-store** doors | Package as a gate to daily capture; interview-only onboarding |
| Gym split ask-once; last-session weights **read**; brief **section** prefs; unknown-habit **create-on-Confirm** | Food ML; Gemini re-picking `ref_id`; ear Yes |
| Map remaining Life-vision verbs onto M20/M19 phases | Reorder M20 1→5; start package / mail / retrieval / work lane |
| Charter + pack recipes so cortex *asks once* | Hardcoding operator meals/habits/split in Python `if`s |

**Stack lock (reaffirm):** Python ASGI + static HUD. Gateway renders real `{tool, args}`. Same `run_turn`. Confirm on **this** ingress window ([M20b](./M20b_PHONE_FACE.md) / [M20c](./M20c_MAC_DISPLAY_FACE.md)).

---

## §8 gate fields ([`00_ASSISTANT_RESEARCH.md`](../00_ASSISTANT_RESEARCH.md))

| Field | Answer |
|-------|--------|
| **Question / capability** | Personalization posture: learn-while-talking into existing life stores, with Confirm, without seed-as-primary or silent auto-learn |
| **Lens tags** | **EVIDENCE** (Ask Once / PRELUDE editable prefs / Tiny Habits / Hevy last-set) · **FEASIBLE** (M21 Confirm + FACTS YAML + gym/habit logs already exist) · **FANFICTION** (movie “she just knows”; sentience) · **POLICY** (Confirm Integrity; one cortex; code binds ids; no ear Yes) · **METAL** (favorites after Yes; Dream stages favorites/people; `gym_split` FACT read; habit CLI seed; gym_start/end **tools** without pack doors) |
| **Citations** | §G ≥6 + internal METAL |
| **Pi 5 8GB feasibility** | **Yes** — no new model. Ask-once is one Confirm round-trip the operator already knows from M21. Last-session weights = SQL read on `gym_sets`. |
| **Learning objective** | After this card, implement chats extend **UX on existing stores** without reopening “hand-seed YAML,” second cortex, package-now, or food ML |
| **Harder-but-correct vs shortcut** | **Correct:** first-time Confirm → sticky row in the same file/table a seed would have written. **Shortcut rejected:** Python `if operator:` life; silent lock from one meal; “just edit YAML”; wait for package interview |
| **Won’t-chase (this slice)** | Package/mail/retrieval mega-slice · second cortex · food ML · Mem0 · daily PubMed · work campaigns · hardcoding Aryan’s coffee/split/skincare in Python |
| **Acceptance falsifiers** | F-M22-* in §H |
| **Egress impact** | **Control plane:** Confirm on Tailscale HUD (unchanged). **Cortex:** may see labels in the ask; **never** sole bind authority. **Backup:** same FACTS/logs; Dream **must not** auto-merge favorites, people, gym split, habit defs, or brief *content* lists (whitelist stays clock/mute/register dials) |

---

## Executive summary — the pick

**Do this:** **Option D — three equivalent doors, one store.** Daily default is **teach-in-flow** (doc-19 **Ask Once** as a closed loop, not omniscience). Package interview and CLI/YAML seed are **optional** and must write the **same** keys/tables.

```text
utterance (first time this entity / pref)
   │
   ├─ pack / spine          → slots (habit name, split days, brief keys, …)
   ├─ resolve organ (M21)   → 0 / 1 / many  (code owns ids)
   │         │
   │    unique + already sticky?     unknown / new pref / no split
   │         │ yes                         │
   │         ▼                             ▼
   │    write / speak from receipt    needs_confirm (gateway args)
   │                                  “save as usual / remember this?”
   │                                       │
   │                         Yes ─────────┼─── same store a seed would hit
   │                         No  ─────────┼─── proceed once, do not sticky
   └─ mouth (register pass)  → speaks from receipt only
```

| Keep | Drop |
|------|------|
| M21 Confirm-on-ambiguity; code binds ids | Silent top-1; Gemini-chosen `ref_id` |
| `facts/nutrition_favorites.yaml` after Yes (**METAL**) | Invent a second prefs store |
| FACTS `gym_split`, habit defs SQL, people YAML, prefs keys | Operator **must** hand-edit those files to live |
| Optional `ada life habit-seed` / YAML | Seed as the **primary** door; skincare hardcoded as *the* life |
| Package onboarding as a **later optional interview** | Package as a gate before meals/gym work |
| Empty = honest unknown | Empty = “ADA is just if/else until you seed” |

**Why this is the organism move:** Justine/Jarvis **FEASIBLE** closed loops are **ask once, remember, brief from receipts** — not a smarter LLM and not a YAML CMS. METAL already does this for **coffee after Confirm**. Docs still tell the next implementer to **seed habits** and **edit `gym_split.yaml`**. That teaches the wrong product.

---

## Vision lock (north star — do not reopen)

ADA is a Justine/Jarvis-class **life companion** on the Pi: mostly voice; honest day capture; gets personal by **learning while talking**. Operator can add/remove what appears in morning/EOD brief via prefs. Awareness = **state + briefs from receipts**, not vibes or daily PubMed. **Life closes first;** work campaigns later. Durable data root; new organs **add on** — no re-birth to keep living. Cortex parses NL; **code binds ids**; **no ear-only Yes**; **no Gemini re-picking food `ref_id`s after search.**

Fiction is a **jobs lens**. Engineering is Verb→Pack→fill + Confirm Integrity. Not sentience. Not movie omniscience.

---

## §A — Where docs imply seed-first (honest)

These are **doc/product gravity**, not always false metal. Tag the implied *primary path*.

| Source | What it implies | Tag |
|--------|-----------------|-----|
| [M16](./M16_FIRST_PACKAGE.md) §3.2 | Fresh ADA ≈ **empty prefs + stub `people/aryan.yaml`**; birth pack = **seed syllabus** so she is not empty | **METAL** hollow + **seed-as-self** story |
| M16 Phase 0 “Base self” | “seed syllabus / self-model so she is not empty at birth” as package job | **POLICY**-adjacent; **interview later** is fine; **not** daily teach-in-flow |
| [M19a P1](./M19a_P1_HABITS_PEOPLE.md) OPEN #4 | “Ship **empty** + **operator seed**; bundled `habits_seed.yaml` optional” | **Seed-as-habit-door** |
| M19a P1 HUD prereq | “at least one habit def **seeded**” before smoke | **Seed-before-use** |
| [`ada life habit-seed`](../../src/ada/cli/main.py) + [`seed_default_habits`](../../src/ada/logs/habits.py) | **METAL** CLI writes `habit_skincare` / evening routine in Python | **Optional door** that reads as **the** door; **borderline operator-life-in-code** |
| [M19a P0](./M19a_P0_LIFE_CAPTURE.md) §4.5 | `nutrition_targets.yaml`, `nutrition_presets.yaml`, **`facts/gym_split.yaml`** as files the operator maintains | **Store METAL**; **path implied = edit YAML** |
| M19 `split_set` / `targets_set` | SHOULD verbs; Confirm soft — **catalog has teach-in-flow**, implement gravity is files | **FEASIBLE** unused as chat loop |
| [M20](./M20_V1_PRODUCT.md) phase 4 | First-boot **onboarding** as the product moment for a newborn | **Correct for install**; **wrong if read as “can’t get personal until package”** |
| [seeds/syllabus/OPERATOR.md](../../seeds/syllabus/OPERATOR.md) | Empty slots + “say remember…” | **Already teach-in-flow copy** — under-cited vs CLI seed |
| Constitution §8.1 | Append FACT notes always allowed; overwrite Confirm | **Already teach-in-flow law** — under-cited vs seed docs |

**Already the right loop (do not reinvent):**

| Piece | State |
|-------|--------|
| Food favorites after Confirm Yes | **METAL** — [`favorites.py`](../../src/ada/logs/favorites.py), M21 §F |
| Dream stages `nutrition_favorites` / people | **METAL** — [`dream/merge.py`](../../src/ada/dream/merge.py) |
| People capture-first (“met X”) | **METAL** packs in [`life_p1.yaml`](../../src/ada/harness/packs/life_p1.yaml); M21 honesty on bind |
| `life_gym_start` / `life_gym_end` / `life_gym_status` tools | **METAL** — status **reads** `gym_split` FACT if present |
| Gym **packs** for start/end | **GAP** — [`life_p0.yaml`](../../src/ada/harness/packs/life_p0.yaml) has `gym_status` + `lift_log` only |
| Register-pass mouth | **METAL** — [`mouth.py`](../../src/ada/harness/mouth.py); receipt JSON; numeric fail-closed |
| Last-session weights | **GAP** — `gym_sets` exist; `gym_status` is **today’s sets**, not prior load |

---

## §B — Reframe without breaking locks

**Bootstrap = three doors, same stores.** Not three memory systems.

| Door | When | Writes | Confirm |
|------|------|--------|---------|
| **Teach-in-flow** (default) | First time the entity/pref appears in chat/voice | Same as seed | Yes on ingress (M21 class) |
| **First-run interview** | Optional; **phase 4 package** — short, skippable | Same keys | Same gateway args; not a unique schema |
| **Optional seed** | Power-user / tests / restore | Same keys | CLI may set `confirmed=true` only as **operator-at-keyboard** (already trusted); HUD still Confirm |

**Same stores (do not fork):**

| Life object | Store (already named) | Teach-in-flow verb |
|-------------|----------------------|--------------------|
| Food “my coffee” | `facts/nutrition_favorites.yaml` | **METAL** meal Confirm Yes / `life_food_favorite_set` |
| Named meal recipe | `facts/nutrition_presets.yaml` | **METAL** `food_preset_save` (soft clash) — extend UX |
| Nutrition targets | `facts/nutrition_targets.yaml` | `targets_set` (M19 SHOULD) — Confirm soft |
| Gym split | `facts/gym_split` / `gym_split.yaml` | **NEW UX** on **METAL** read in `gym_status` |
| Custom exercise | `facts/gym_custom_exercises.yaml` | P0 catalog miss → persist — already sketched |
| Habit / routine defs | `habit_definitions` / `routine_definitions` SQL | **NEW:** unknown name → Confirm-create (today: `missing_life_receipt` or CLI seed) |
| People | `facts/people/*.yaml` | **METAL** capture + M21 name honesty |
| Brief *clock* | prefs `brief_time`, `brief_enabled` | **METAL** whitelist (constitution) |
| Brief *sections* | prefs keys **NEW** (e.g. `brief_include`) | Operator add/remove; **not** Dream-whitelist junk |
| Register dials | prefs roast/humor/chill | **METAL** whitelist; “chill” already session+optional FACT |

**Package (phase 4) stays:** clean newborn `ADA_DATA_ROOT`, secrets, windows ≠ organism, **add-on organs**. Interview is a **skippable** door into these stores — not a rewrite of birth-once identity.

---

## §C — Explicitly rejected

| Reject | Why | Tag |
|--------|-----|-----|
| **Silent auto-learn** (every meal becomes favorite; every name becomes a person; Dream “notices” gym days) | Accidental permanent lock; prefs drift ([PAMU](https://arxiv.org/abs/2510.09720)); M21 F-M21-5 | **POLICY** |
| **Dream inventing favorites / split / habits** | Dream = overnight **manage**; whitelist is clocks/mute/register — **METAL** already stages favorites + people | **POLICY** / **METAL** |
| **Gemini choosing `ref_id` after search** | M21 lock; coffee/Gott failure class | **POLICY** |
| **Ear-only Yes** | M20b/c; Consent Integrity | **POLICY** |
| **Hardcoding operator life in Python** | `if coffee: …`, baked PPL split, `habit_skincare` as *the* organism default | **POLICY** — **optional** bundled seed for *tests* OK if labeled `source=seed` and not required for HUD |
| **Empty ⇒ ADA is only if/else** | Packs are doors (YAML aliases), not biography. Empty FACTS ⇒ ask once or proceed unsticky | **POLICY** |
| **Second cortex / food ML / Mem0** | M21 won’t-chase | **POLICY** |
| **Awareness from daily PubMed / vibes** | Briefs cite receipts + named stores | **POLICY** |
| **Work campaigns before life closes** | M20 phase 5 | **POLICY** |
| **Re-birth to keep living** | Durable root; organs add on (M20 F-M20-5) | **POLICY** |

**Allowed (not rejects):** pack YAML **aliases** as utterance doors; constitution sovereign name; identity `operator: Aryan`; test fixtures under `ADA_DATA_ROOT`.

---

## §D — Vision features → phase

| Feature | Owner / phase | METAL vs NEW | Note |
|---------|---------------|--------------|------|
| **Teach-in-flow** (generic ask-once) | **This card** — recipe; implement after M21 | **NEW UX**; stores **METAL** | Default personalization |
| **Save-as-usual** (food sticky) | **M21** | **METAL** — **extend UX**, do not invent prefs store | Favorites + presets |
| **Gym split ask-once** | **This card** implement-next | Store **METAL** (`get_fact("gym_split")`); **NEW** Confirm write + pack | First gym week without YAML |
| **Last-session weights** | **This card** (read) · panels stay M20 3d | **NEW** query on **METAL** `gym_sets` | Hevy-class **FEASIBLE**; not PRs (M19 P4) |
| **Morning / EOD brief prefs** | **This card** (section list) · timer already M04/M16 | Clock keys **METAL**; **NEW** include/exclude list | Operator add/remove; receipts not PubMed |
| **Habits resolve** | **M21** implement-next #5 | Gate **NEW** on **METAL** `resolve_habit` 0/1/many | Ambiguous *id* — not create |
| **Unknown habit create** | **This card** after M21 habits resolve | **NEW** Confirm-create; SQL **METAL** | Replaces seed-as-primary |
| **Gym close** (`gym_end`) | **M19a P0 tools METAL** · **this card** pack doors | Tools **METAL**; packs **GAP** | Auto-session on first lift already P0 |
| **Register mouth** | **M20 phase 2** / M19b | **METAL** `mouth.py` | Not this implement; keep numeric guard |
| **Body week brief** | **M19 P4** analysis | Logs **METAL**; week UI **later** | Not this slice |
| **Work lane / mail / campaigns** | **M20 phase 5** / M19 P2–P3 | — | After life closes |

---

## §E — Sequence vs M20 (do not reorder 1→5)

M20 phases **1→5 stay locked.** This card is a **3→4 insert after M21**, same geometry as M21 after 3a–3c.

```text
  [1] voice research     M20a
  [2] wedge + mouth      (register pass METAL; PTT still product gap)
  [3] UI polish + panels
  [3→4] M21 resolve + Confirm-bind     (food+people METAL; habits next)
  [3→4] M22 teach-in-flow              ← this card (not package)
  [4] first-boot package               (optional interview = one door)
  [5] personal workflows / P2 mail
```

**Why still before package:** daily capture already lies less after M21, but **personal gravity** (split, habits, brief sections) still looks like a CMS. Package is **newborn install + secrets + skippable interview**, not the first time ADA may remember coffee or a PPL split. **Do not** pull package forward to “fix” personalization.

**Why not after package:** waiting trains seed-first. Life vision is **live while talking** on the existing data root.

---

## §F — Option matrix → pick

| ID | Path | Trust | Friction | Organism? | Verdict |
|----|------|-------|----------|-----------|---------|
| **A** | Hand-seed YAML / CLI as primary | High (operator typed it) | High; ADA feels empty until homework | No — CMS with a roast | **Reject as primary.** Keep as optional door |
| **B** | First-run interview **required** (package gate) | High | Blocks living until phase 4 | Partial | **Reject as sole path.** Interview optional at [4] |
| **C** | Silent auto-learn from logs | Low | Lowest | Movie; M21 already forbids | **Reject** |
| **D** | **Teach-in-flow default** + optional interview + optional seed, **same stores** | High after Yes | Low after first Confirm | **Yes** | **LOCK** |
| **E** | Prompt-only “please remember” without gateway bind | Forgeable | Ad hoc | No — LITL | **Reject as sole fix** (charter may *assist*) |

**Ask-once predicate (locked defaults until OPEN overturns):**

1. **Unknown habit / routine name** → Confirm-create (after M21 resolve exists); not silent SQL insert; not “seed first.”  
2. **No `gym_split` FACT** on `gym_start` / first lift week → Confirm proposed split (operator-filled slots), then sticky.  
3. **Brief section change** (“don’t put gym in the morning brief”) → Confirm prefs patch; subsequent briefs honor list.  
4. **Food** → unchanged M21 (favorite after Yes).  
5. **People** → unchanged M21 (display_name; clash Confirm).

Proceed **unsticky** if operator says No: log the meal/set **once**; do not write favorite/split/habit def.

---

## §G — Recipe sketch + literature

Not a second cortex. Durable pack recipe the harness already understands (M21 §E).

```yaml
# illustrative — implement chat owns real files
recipe: life.teach_in_flow.gym_split
verb: gym_start   # or first lift_log when no split
stages:
  - parse_slots: [split_label, days]          # cortex
  - load_store:
      fact: gym_split                         # code
  - ask_once:
      confirm_if: [missing_split]
      confirm_tool: memory_facts_propose_edit # or dedicated life_split_set
      hold: pending_id
  - on_yes:
      write: gym_split FACT                   # same doc seed would write
  - on_no:
      action: continue_session_without_split
      fail_closed: no_silent_fact
success: receipt_id
```

| Field | Meaning |
|-------|---------|
| `load_store` | **Code** reads existing FACT/SQL — never invent |
| `ask_once` | Missing personal slot → gateway Confirm, not charter-only |
| `on_yes` | Sticky in the **named** store |
| `on_no` | Episode may proceed; **no** sticky row |

**SOTA / product (steal patterns, refuse transplants):**

| Source | Steal | Refuse | Tag |
|--------|-------|--------|-----|
| Doc-19 **Ask Once** pack | Capture pref/fact; retrieve later; Confirm sensitive | Perfect personal model | **FEASIBLE** / **POLICY** |
| [PRELUDE / CIPHER](https://arxiv.org/abs/2404.15269) | Prefs as **editable text**, not fine-tune | Latent-only prefs | **EVIDENCE** |
| [PAMU](https://arxiv.org/abs/2510.09720) | Prefs drift; update is a mechanism | Silent overwrite | **EVIDENCE** |
| [AskToAct](https://arxiv.org/abs/2503.01940) / [AwN](https://arxiv.org/abs/2409.00557) | Clarify before lock-in | Prompt-only as architecture | **EVIDENCE** |
| [Consent Integrity](https://arxiv.org/abs/2606.02668) | Yes binds gateway args | Model-narrated “I’ll remember” | **EVIDENCE** / **POLICY** |
| [Tiny Habits (Fogg)](https://www.behavioralmodel.org/) | Anchor + tiny behavior; already M19a P1 | Shame streaks; baked skincare-as-soul | **EVIDENCE** |
| Hevy / Strong last-set (M19b §A) | Previous load/reps prefill | Social gym; PR wall as v1 | **EVIDENCE** / **FEASIBLE** |
| Anthropic **Agent Skills** | Procedure in **same** agent | Sub-cortex for “knowing you” | **EVIDENCE** / **POLICY** |

---

## §H — Falsifiers

| ID | Fail if… |
|----|----------|
| **F-M22-1** | Daily personalization **requires** hand-edited YAML or `habit-seed` before a first Confirm-create / split-ask can succeed in HUD Agent |
| **F-M22-2** | Favorite, gym split, habit def, or brief-section list written **without** Confirm Yes (or explicit operator CLI at the keyboard) |
| **F-M22-3** | Dream auto-merges favorites, people, gym split, habit defs, or brief **content** lists |
| **F-M22-4** | Gemini chooses food `ref_id` after search, or Confirm Yes uses model prose instead of gateway `{tool,args}` |
| **F-M22-5** | Ear-only / TTS Confirm as the Yes path |
| **F-M22-6** | Operator life (coffee brand, PPL days, skincare-as-required-default) hardcoded in Python as the only working path |
| **F-M22-7** | Implement starts package, mail, retrieval mega-slice, second cortex, or food ML as a dependency of teach-in-flow |
| **F-M22-8** | Package interview becomes **mandatory** before meal/gym/habit logs work on an existing data root |
| **F-M22-9** | Morning/EOD brief invents content not backed by receipts / named stores (PubMed-of-the-day, vibes) |

M21 F-M21-*, M20 F-M20-2/3/5, M19a F-P1.2c still bind.

---

## OPEN (≤5)

| # | Question | Default until a later chat locks it |
|---|----------|-------------------------------------|
| 1 | **Brief section inventory** (`brief_include` keys) | Dues · overnight heal heads · meal-gap · open gym · habits due. Operator add/remove via Confirm. No news/PubMed. |
| 2 | **Gym split schema** | Days → `{label, body_parts[]}` in existing `gym_split` FACT; Confirm shows the table |
| 3 | **Last-session lookback** | Last **closed** session, same `exercise_id`; speak/prefill load×reps; not PR / coverage |
| 4 | **Package interview depth** | Optional ≤8 slots (split, targets, 1–2 habits, brief sections). **Skip** still allows full capture. Phase **4**, not this slice |
| 5 | **Unknown habit** today vs after M21 | After habits **resolve** lands: 0 matches → Confirm-create. Until then keep `missing_life_receipt` (honest). CLI seed stays **optional** |

**Do not reopen as OPEN:** sequence 1→5; one cortex; code binds ids; Confirm on ingress; no ear Yes; no silent auto-learn; no Dream auto-merge of life prefs; no package in this slice; no food ML.

---

## Implement-next (ordered)

This card is **docs-only**. Executable checklist: [`../reviews/M22_IMPLEMENT_PLAN.md`](../reviews/M22_IMPLEMENT_PLAN.md). Later implement chats, in order:

1. **Gym session packs + split ask-once** — wire `gym_start` / `gym_end` into [`life_p0.yaml`](../../src/ada/harness/packs/life_p0.yaml) (tools **METAL**; packs **GAP**); first missing `gym_split` → Confirm → same FACT `gym_status` already reads.  
2. **Last-session weights** — read last closed `gym_sets` for this `exercise_id`; mouth/template from receipt JSON only.  
3. **M21 habits resolve** (if not yet green) — ambiguous tick still Confirm-bind; **then** unknown-habit Confirm-create (this card OPEN #5). Do not make `habit-seed` required.  
4. **Brief section prefs** — include/exclude list in FACTS prefs; morning/EOD consume it; Dream does not auto-merge the list.  
5. **Phase 4 (later):** skippable interview writes the **same** stores. Not a gate for (1)–(4).

**Do not start:** package, mail, retrieval mega-slice, Dream rewrite, mode collapse, second cortex, food model, work campaigns, thumbs UI as v1 gate.

---

## Won’t-chase

| Out | Why |
|-----|-----|
| Package / P2 mail / campaigns | M20 1→5 |
| Retrieval need-list architecture | Later sibling (not this M22) |
| Custom food / NER model | M21 |
| Gemini Live / sub-cortex “who is Aryan” | One cortex; slots + stores |
| Mem0 / Letta / n8n strategy | Refuse transplants |
| Silent auto-learn | Accidental lock |
| Ear-only Yes | POLICY |
| Daily PubMed / vibe awareness | Receipts |
| Hardcoded operator biography in Python | This card |
| Collapsing Observe/Plan/Agent | Constitution |

---

## Locks (do not reopen)

| Lock | Source |
|------|--------|
| Teach-in-flow is the **default** personalization path | **this card** |
| Interview + seed are **optional same-store** doors | **this card** |
| Favorites / people / split / habit defs / brief *content* — Confirm; Dream stages | **this card** + M21 + M04 |
| Code binds ids; cortex parses slots | M21, doc-19 |
| Confirm on ingress; no ear Yes | M20b/c, Consent Integrity |
| One Gemini cortex; mouth = register pass on receipts | M19b, `mouth.py` |
| After M21, **before package**; do not reorder 1→5 | M20 |
| Life closes first; work later | vision + M20 [5] |
| Durable root; organs add on; no re-birth to keep living | M20 F-M20-5 |

---

## References

1. AskToAct — https://arxiv.org/abs/2503.01940 · **EVIDENCE**  
2. Ask-when-Needed — https://arxiv.org/abs/2409.00557 · **EVIDENCE**  
3. Consent Integrity — https://arxiv.org/abs/2606.02668 · **EVIDENCE** / **POLICY**  
4. PRELUDE (prefs from edits) — https://arxiv.org/abs/2404.15269 · **EVIDENCE**  
5. PAMU preference memory update — https://arxiv.org/abs/2510.09720 · **EVIDENCE**  
6. Anthropic Agent Skills — https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills · **EVIDENCE** / **POLICY**  
7. Tiny Habits / Fogg B=MAP — https://www.behavioralmodel.org/ · **EVIDENCE**  
8. Doc-19 Ask Once + Verb→Pack→fill — [`../19_JARVIS_JUSTINE_AGENT_RESEARCH.md`](../19_JARVIS_JUSTINE_AGENT_RESEARCH.md) · **FEASIBLE** / **POLICY**

### Internal

- [`M20_V1_PRODUCT.md`](./M20_V1_PRODUCT.md) — sequence fence  
- [`M21_RESOLVE_CLARIFY.md`](./M21_RESOLVE_CLARIFY.md) — Confirm-bind; favorites METAL  
- [`M19a_P0_LIFE_CAPTURE.md`](./M19a_P0_LIFE_CAPTURE.md) / [`M19a_P1_HABITS_PEOPLE.md`](./M19a_P1_HABITS_PEOPLE.md) — capture stores  
- [`M16_FIRST_PACKAGE.md`](./M16_FIRST_PACKAGE.md) — birth/onboarding ingredients (interview later, not this gate)

---

*End M22 life teach-in-flow. v1.0 design lock: three doors, one store; teach-in-flow default; still before package.*
