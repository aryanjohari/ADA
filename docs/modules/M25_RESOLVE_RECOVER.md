# M25 — Pack-fenced resolve recover (hard-case half · recover loop)

**Status:** design lock — **not code**  
**Date:** 2026-08-27 (v1.0)  
**Host:** `ada-pi5` (Raspberry Pi 5, 8 GiB) · windows: Mac / phone via Tailscale Serve  
**Branch:** `rewrite/v1-body`  
**Kind:** M20 **skill-spine / resolve delta** — when fast spine hits `empty_macros` / miss / weak candidates, run a **bounded recover loop** (retry queries → refresh detail → Confirm). Not decompose. Not feel. Not package. Not analysis.  
**Depends on:** [`M20_V1_PRODUCT.md`](./M20_V1_PRODUCT.md) (sequence; this card sits **after M24, still before phase-4 package**) · [`M24_MULTI_INTENT_CAPTURE.md`](./M24_MULTI_INTENT_CAPTURE.md) (decompose + empty-macro **guard**; this card owns **recover**) · M21 Confirm-bind / favorites (**METAL** in [`life_tools.py`](../../src/ada/tools/life_tools.py) + [`favorites.py`](../../src/ada/logs/favorites.py) + [`resolve_gate.py`](../../src/ada/harness/resolve_gate.py); design card `M21_RESOLVE_CLARIFY.md` **not in tree** — cite M20 · M19a · phone reviews) · [`M22_LIFE_TEACH_IN_FLOW.md`](./M22_LIFE_TEACH_IN_FLOW.md) (sticky after Yes) · [`M23_FRIEND_MOUTH.md`](./M23_FRIEND_MOUTH.md) (mouth = register pass — **do not reopen feel**) · [`M19a_P0_LIFE_CAPTURE.md`](./M19a_P0_LIFE_CAPTURE.md) · [`../19_JARVIS_JUSTINE_AGENT_RESEARCH.md`](../19_JARVIS_JUSTINE_AGENT_RESEARCH.md) (Verb→Pack→fill; skills = packs) · [`../00_ASSISTANT_RESEARCH.md`](../00_ASSISTANT_RESEARCH.md) §8 · METAL [`meal_spine.py`](../../src/ada/harness/meal_spine.py) · [`loop.py`](../../src/ada/harness/loop.py) `_fast_path_meal` · [`food.py`](../../src/ada/logs/food.py) (`search_foods_resolved`, `fetch_usda_detail`)

**Name stays `M25_RESOLVE_RECOVER.md`:** this is a **sequence insert** after M24 — **pack-fenced recover when resolve data is incomplete** — the **hard-case half** of life capture skills. Alternate slug `M25_HARD_CASE_RESOLVE.md` rejected as less precise (hard-case is the product pain; recover loop is the mechanism).

**Name collision:**

| Candidate | Verdict |
|-----------|---------|
| **`M25_RESOLVE_RECOVER.md` (this card)** | **PICK.** Phase-1 hard-case half: bounded retry / detail refresh / Confirm when empty macros, miss, or weak candidates. After M24, before package. |
| Append-only **M24** | **Reject as home.** M24 owns **decompose + fail-closed empty write**. This card owns the **recover loop** after that guard — different failure. Thin pointer on M24 OK. |
| Stuff into **M21** | **Reject as home.** M21 owns Confirm-bind for an **already-built** candidate set. Recover **builds better candidates** then feeds that gate. Pointer OK. |
| Stuff into **M23** | **Reject.** Feel ≠ resolve recovery. |
| Stuff into **M22** / retrieval sibling | **Reject.** Stores / later retrieve are not the egg-null-CORE hole. |
| “Make ADA into Cursor” mega-agent | **Reject.** Steal **tools + receipts + ask** *inside packs* — not freestyle coding AGI as daily path. |
| Analysis / graphs / package card | **Reject.** P4 and phase-4 stay OUT. |
| `M20e` / phase renumber | **Reject.** Do **not** renumber M20 1→5. |

**Supersedes:** any reading that (a) honest `empty_macros` ack is “done” for breakfast, (b) freestyle Gemini tool-call-until-it-works is the recover path, (c) null CORE may be written as 0 kcal, (d) cortex may sole-pick `ref_id` / invent kcal during recovery, (e) unbounded ReAct replaces Verb→Pack. **Does not supersede:** M24 decompose / fail-closed guard; M21 Confirm Integrity; M22 stores; M23 friend register; one Gemini cortex; mouth = register pass; fast spine first; truth > charm; package-later; no food ML.

### Changelog

| Ver | Date | Delta |
|-----|------|-------|
| **v1.0.2** | 2026-08-27 | Patch note — recover drops off-query hits (`candidate_matches_query`); phone `dcce958…` Banana↔eggs via shared `raw`. |
| **v1.0.1** | 2026-08-27 | Pointer only — implement plan → [`../reviews/M25_IMPLEMENT_PLAN.md`](../reviews/M25_IMPLEMENT_PLAN.md) (gap map; not METAL). |
| **v1.0** | 2026-08-27 | Design lock: pack-fenced resolve recover — bounded alternate queries + detail refresh + Confirm; spine owns triggers/caps; cortex may propose query list only (default OFF). |

---

## One-liner

When life-capture resolve returns **empty macros, no usable hit, or weak/brand-fight-only candidates**, ADA runs a **bounded recover loop** inside the meal pack — retry smarter queries, refresh FDC detail, drop null-CORE rows, then Confirm or ask — never invent nutrients, never freestyle ReAct, never leave the operator stuck on honest-but-empty.

---

## Core research question

When life-capture resolve returns **empty macros, no usable hit, or weak/brand-fight candidates**, how should ADA run a **bounded recover loop** (alternate queries, detail refresh, capped retries, then Confirm) in the **Cursor/Claude agent pattern** — tools + receipts + ask — without freestyle process AGI, without inventing nutrients, and without leaving the operator stuck on honest-but-empty?

Secondary lenses:

| Sub-question | Where answered |
|--------------|----------------|
| Why not “Gemini tool-calls until it works”? | Exec pick · harder-but-correct |
| Recover recipe (trigger → retries → Confirm / ask) | §G |
| Who owns triggers, caps, query list, bind? | Exec pick · §G |
| M24 fail-closed vs recover (METAL) | §F |
| Skills framing (hard-case half) | Skills framing |
| Falsifiers / OPEN / sequence | §H–§J |

---

## Skills framing (Phase 1 = capture + recover)

In ADA, a **skill** is **pack spine + FACTS + receipts** — not a domain essay in the cortex prompt. **M24 = capture decompose** (one utterance → N honest slot fills). **M25 = resolve recover** when data is incomplete (empty macros / miss / weak set). Together they are Cursor-like **“try tools, then ask” inside ADA packs** — not a general coding agent, not analysis, not graphs. Phase 2–3 teach-in-flow stays M22; Phase 4 progression stays M19 P4 — **OUT**.

---

## Scope fence

| IN (this card) | OUT (explicit) |
|----------------|----------------|
| Food hard-case recover: `empty_macros` / zero usable candidates / optional weak-only set | P4 analysis · charts/graphs · package |
| Alternate queries + `fetch_usda_detail` / nutrient refresh | Retrieval · mail · food ML · M23 feel |
| Caps (retries / searches / wall) → clear mouth line | Unbounded agent · freestyle ReAct as daily path |
| Confirm integration after recover builds honest candidates | M24 reopen decompose · Gemini sole `ref_id` |
| Meal fast-path hook **after** M24 miss | Habit multi-intent · work campaigns |
| Optional later: lift catalog miss recover (thin note only) | Invented kcal · mark empty as 0 · second cortex |

**Stack lock (reaffirm):** one Gemini cortex; mouth = register pass (M23); Confirm on **ingress**; **no ear Yes**; no chat-Yes bind; code binds `ref_id`; no Gemini sole-pick after search; Verb→Pack→fill; fast spine stays first — recover is **escalation**, not replacement; Favorites / M22 same stores; truth > charm; no food ML; no package.

---

## §8 gate fields ([`00_ASSISTANT_RESEARCH.md`](../00_ASSISTANT_RESEARCH.md))

| Field | Answer |
|-------|--------|
| **Question / capability** | Bounded pack-fenced recover when resolve returns empty macros / miss / weak candidates — then Confirm or human ask |
| **Lens tags** | **FEASIBLE** (extend meal_spine + food detail; no new model) · **EVIDENCE** (doc-19 Verb→Pack; Agent Skills / scripts-as-tools; AskToAct / Consent Integrity) · **FANFICTION** (omniscient food AGI / freestyle Cursor-as-organism) · **POLICY** (truth > charm; code binds ids; caps; no invent kcal) · **METAL** (phone `2be4966…` empty-nutrients ack; egg FDC null CORE; `_parse_piece` strips “boiled”) |
| **Citations** | ≥2: doc-19 Verb→Pack→fill; [Anthropic Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills); Consent Integrity / LITL · AskToAct; live METAL §F |
| **Pi 5 8GB feasibility** | **Yes** — capped extra FDC searches + detail GETs. No second cortex. No food ML. |
| **Learning objective** | Implement chat can wire recover escalation after M24 miss without reopening freestyle ReAct, feel, package, or “prompt nutrition knowledge” |
| **Harder-but-correct vs shortcut** | **Correct:** pack-fenced recover loop + Confirm + code bind. **Shortcut rejected:** “just let Gemini tool-call until it works”; prompt nutrition knowledge; mark empty as 0 kcal; analysis-as-fix; graphs; unbounded ReAct. |
| **Won’t-chase (this slice)** | Package · retrieval · mail · P4 analysis · charts · food ML · M23 feel · M24 decompose reopen · systemd · work campaigns · habit multi-intent · second cortex · ear Confirm |
| **Acceptance falsifiers** | F-M25-* in §H |
| **Egress impact** | **Control plane:** Confirm on Tailscale HUD (unchanged). **Cortex:** optional pack-fenced **query list only** (default OFF); **never** sole bind of `ref_id`/kcal. **Backup:** same meal logs + favorites FACTS. Extra USDA/FDC GETs under existing food API key. |

---

## Executive summary — the pick

**Do this:** keep **fast spine first** (M24). On hard miss, run a **bounded recover loop inside the meal pack** — deterministic alternate queries + detail refresh + drop null-CORE → existing Confirm gate or human ask. Cortex may propose a **query list only** inside the fence (default **OFF**).

```text
utterance (life meal)
   │
   ├─ pack_router → meal_log (Verb→Pack)
   ├─ fast spine (M24) → resolve each slot
   │         │
   │    ok + honest? ──────────────────────────► write / Confirm (existing)
   │         │
   │    empty_macros | food_search_miss | weak-only?
   │         ▼
   │    RECOVER (this card)  ← escalation, capped
   │         │
   │    alt queries → search → fetch_usda_detail / refresh
   │         │
   │    drop null-CORE · re-run decide_food_bind
   │         │
   │    ≥1 honest candidate? ──yes──► Confirm (or sticky favorite if unique)
   │         │ no (cap hit)
   │         ▼
   │    human ask (clear mouth) — never silent Gott / invent kcal
   └─ mouth (M23) → speaks from receipt / fail line only
```

| Keep | Drop |
|------|------|
| Fast spine first; recover = escalation | Freestyle ReAct as daily recover |
| M21 Confirm; code binds `ref_id` | Gemini sole-pick / invent kcal |
| M24 empty-macro **guard** | Writing null CORE as success or as 0 |
| Caps + clear mouth on give-up | Unbounded retries / silent stuck |
| Mouth = register pass (M23) | Analysis / graphs as “fix” |

**Why this is the organism move:** M24 METAL stopped silent Gott + empty egg **writes**. Live phone still fails breakfast because eggs resolve to **null CORE** — guard correct; **recovery missing**. Operator lock: Cursor/Claude **recover-and-clarify** *inside the pack*.

---

## §F — METAL vs GAP

| Piece | State | Note |
|-------|--------|------|
| M24 multi-slot decompose + hold whole meal | **METAL** | coffee+eggs no longer silent-Gott write |
| Empty-macro / null-CORE **guard** | **METAL** | `meal_spine` miss `empty_macros`; `life_meal_log` refuse empty write; `_fast_path_meal` mouth: “nutrients came back empty…” |
| Recover after `empty_macros` | **GAP** | Fast path stops; no alt queries / detail retry |
| `search_foods_resolved("eggs")` | **METAL lie-shape** | FDC rows (e.g. Mars Chocolate **EGGS**) with **null** kcal/protein — hits returned, macros unusable |
| Query normalization | **METAL gap** | `_parse_piece` strips `boiled` / size words → search `"eggs"` loses cooked Foundation cues |
| `fetch_usda_detail` | **METAL** | Exists; search path prefers detail before insert — **spine does not re-try** alts or force refresh on null CORE |
| Confirm after better candidates | **METAL gate** | Ready once recover builds a viable set — not wired from empty miss |
| Freestyle Gemini recover | **Reject** | Not daily path; reopens sole-pick / invent risk |
| Lift catalog miss recover | **OUT / later** | Thin note only — food hard-case first |

**Live evidence (2026-08-27):**  
- [`runs/2026-08-27/2be4966eb8e3414aa1f24bc0b1f28a72.jsonl`](../../../runs/2026-08-27/2be4966eb8e3414aa1f24bc0b1f28a72.jsonl) — coffee+eggs / “Log 7 boiled eggs”; search query **`eggs`**; FDC candidates with **null CORE**; operator saw empty-nutrients ack (matches `_fast_path_meal` hard-coded line)  
- Prior M24 METAL: `355717c…` / `7b8f957…` (Gott + empty eggs before guard)

---

## §G — Recipe (implement chat)

Ordered; **no second cortex as authority**; reuse M21 Confirm + favorites.

### Trigger (after fast spine)

Fire recover when any slot yields:

1. **`empty_macros`** — candidates exist but all usable binds have null CORE (or line build null), **or**  
2. **`food_search_miss` / zero usable candidates**, **or**  
3. **Optional weak-only set** — only low-score / brand_fight / all-null pool (OPEN #3 default: **on for empty+miss; weak-only OFF until measured**)

### Steps (deterministic first)

1. **Build alternate query list** for the slot (preserve qty/serving from original parse):  
   - restore stripped cooks/size if present in utterance (`boiled egg`, `large egg`)  
   - USDA-ish phrases: `egg, whole, cooked`, `egg, whole, raw`, `large egg`  
   - singular / plural flip (`eggs` ↔ `egg`)  
   - drop candy/brand-shaped top hits on next pass when macros null  
2. **For each alt (under caps):** `search_foods_resolved` → for promising FDC ids **force `fetch_usda_detail`** / refresh cached nutrients if CORE still null.  
3. **Drop null-CORE candidates** from the pool; re-run `decide_food_bind`.  
4. **If ≥1 honest candidate:**  
   - unique sticky favorite + macros → silent bind (existing M21)  
   - else → **Confirm on ingress** (code binds `ref_id`)  
5. **If still empty after caps:** human ask — clear mouth line (not silent give-up; not invent kcal). Hold whole meal per M24 OPEN #1.

### Caps (locked defaults — OPEN #2)

| Cap | Default |
|-----|---------|
| Max recover rounds per slot | **3** |
| Max extra searches per slot | **5** |
| Wall clock (recover phase) | **8s** soft — stop, ask |

Fail closed with a clear mouth line when caps hit.

### Who owns what

| Role | Authority |
|------|-----------|
| **Spine** | Triggers, caps, alt-query table, detail refresh calls, drop null-CORE, handoff to Confirm / ask |
| **Cortex** | May propose **query list only** inside pack fence — **OPEN #1 default OFF** for v1.0 |
| **Never cortex alone** | Food `ref_id`, kcal invent, `confirmed=true`, tool choice for bind |
| **Mouth (M23)** | Speaks from receipt / fail template only |

Optional checklist: [`../reviews/M25_IMPLEMENT_PLAN.md`](../reviews/M25_IMPLEMENT_PLAN.md).

---

## §H — Falsifiers

| ID | Fail if… |
|----|----------|
| **F-M25-1** | Recover **invents kcal** / macros not present in FDC/detail/receipt |
| **F-M25-2** | Silent Gott / brand_fight top-1 bind during or after recover (reopens M21/M24) |
| **F-M25-3** | Recover skips Confirm when candidates remain ambiguous / brand_fight |
| **F-M25-4** | Unbounded ReAct / no caps — “tool-call until it works” as the path |
| **F-M25-5** | Eggs (or peer hard-case) stay **forever stuck** with empty ack and **no** retry / ask escalation |
| **F-M25-6** | M24 decompose regresses (coffee+eggs silent drop / partial silent write returns) |
| **F-M25-7** | Gemini sole-picks food `ref_id` after recover search |
| **F-M25-8** | Slice starts package, retrieval, P4 analysis, charts, food ML, or M23 feel rewrite |

M20 / M21 / M22 / M23 / M24 falsifiers still bind.

---

## §I — OPEN (≤5) — locked defaults for implement

| # | Question | Default until a later chat locks it |
|---|----------|-------------------------------------|
| 1 | **Cortex query-list assist** | **Off for v1.0** — deterministic alt-query table only. Optional later: cortex proposes strings **inside pack fence**; spine still owns search/bind/caps. |
| 2 | **Caps** | **3** rounds · **5** extra searches/slot · **~8s** wall → ask. |
| 3 | **Weak-only trigger** | **Off for v1.0** — trigger on `empty_macros` + search miss first; weak/brand_fight-only already has Confirm path. |
| 4 | **Cache write on detail refresh** | **Yes** — update local food row when detail returns honest CORE (same `food.py` insert/update path). |
| 5 | **Lift catalog miss recover** | **OUT of v1.0** — food hard-case only; later sibling may lift the same pattern. |

**Do not reopen as OPEN:** one cortex; Confirm on ingress; no ear Yes; code binds ids; no Gemini `ref_id`/kcal authority; M23 feel; M24 decompose; package-later; truth > charm; fast spine first; favorites same store.

---

## §J — Sequence vs M20 1→5

**Insert after M24, still before phase 4.** Do **not** renumber 1→5.

```text
  … → [3] UI polish
        → [3→4] M21 life-write honesty (Confirm-bind)
        → [3→4] M22 teach-in-flow
        → [3→4] M23 friend mouth / feel
        → [3→4] M24 multi-intent capture   (skill-spine capture half)
        → [3→4] M25 resolve recover        ← this card (hard-case half)
        → [4] first-boot package
        → [5] workflows / P2 mail
```

**Why still before package:** daily phone already captures; hard-case eggs still **honest-empty**. Package is newborn install — not the fix for null-CORE FDC + missing recover.

**Won’t-chase:** P4 analysis · charts · package · retrieval · mail · food ML · M23 feel · M24 reopen · systemd · work campaigns · habit multi-intent · second cortex · unbounded agent.

---

## Citations (thin)

| Claim | Tag | Pointer |
|-------|-----|---------|
| Verb→Pack→fill; skills = packs not freestyle AGI | **EVIDENCE** / **POLICY** | [`../19_JARVIS_JUSTINE_AGENT_RESEARCH.md`](../19_JARVIS_JUSTINE_AGENT_RESEARCH.md) |
| Skills / scripts-as-tools; try tools then ask | **EVIDENCE** | [Anthropic Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) · AskToAct |
| Confirm before risky bind | **EVIDENCE** / **POLICY** | Consent Integrity / LITL |
| Live empty-nutrients / null CORE eggs | **METAL** | `runs/2026-08-27/2be4966…` · M24 guard in `meal_spine` / `loop._fast_path_meal` |
| Confirm-bind / favorites | **METAL** | `life_tools.py` · `favorites.py` · `resolve_gate.py` |

---

## Locks (do not reopen)

| Lock | Source |
|------|--------|
| Pack-fenced recover + Confirm + code bind | **this card** |
| Fast spine first; recover = escalation | M24 · this card |
| Cortex never sole `ref_id` / kcal authority | M21 · this card |
| Confirm on ingress; no ear / chat-Yes bind | M15 · M20 · M21 |
| Mouth = register pass; truth > charm | M23 · M19b |
| After M24, before package; no 1→5 renumber | M20 |
| One Gemini cortex | constitution · M20 |

---

*End M25. Design lock 2026-08-27 — pack-fenced resolve recover / skill-spine hard-case half; implement without freestyle ReAct, inventing nutrients, or reopening feel/package.*
