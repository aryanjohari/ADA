# M24 — Multi-intent life capture (skill-spine · decompose lock)

**Status:** METAL (slices 1–3) — design lock unchanged  
**Date:** 2026-08-27 (v1.0.2)  
**Host:** `ada-pi5` (Raspberry Pi 5, 8 GiB) · windows: Mac / phone via Tailscale Serve  
**Branch:** `rewrite/v1-body`  
**Kind:** M20 **skill-spine / capture delta** — one utterance → **N honest slot fills** (meal lines + lift sets). Not feel. Not teach-in-flow stores. Not package. Not analysis.  
**Depends on:** [`M20_V1_PRODUCT.md`](./M20_V1_PRODUCT.md) (sequence; this card sits **after M23, still before phase-4 package**) · M21 Confirm-bind / favorites (**METAL** in `life_tools.py` + [`favorites.py`](../../src/ada/logs/favorites.py) + [`resolve_gate.py`](../../src/ada/harness/resolve_gate.py); design card `M21_RESOLVE_CLARIFY.md` **not in tree** — cite M20 · M19a · phone reviews) · [`M22_LIFE_TEACH_IN_FLOW.md`](./M22_LIFE_TEACH_IN_FLOW.md) (same stores; sticky after Yes) · [`M23_FRIEND_MOUTH.md`](./M23_FRIEND_MOUTH.md) (mouth stays register pass — **do not reopen feel**) · [`M19a_P0_LIFE_CAPTURE.md`](./M19a_P0_LIFE_CAPTURE.md) · [`../19_JARVIS_JUSTINE_AGENT_RESEARCH.md`](../19_JARVIS_JUSTINE_AGENT_RESEARCH.md) (Verb→Pack→fill; skills = packs) · [`../00_ASSISTANT_RESEARCH.md`](../00_ASSISTANT_RESEARCH.md) §8 · METAL [`pack_router.py`](../../src/ada/harness/pack_router.py) · [`meal_spine.py`](../../src/ada/harness/meal_spine.py) · [`gym_spine.py`](../../src/ada/harness/gym_spine.py) · [`loop.py`](../../src/ada/harness/loop.py) · [`life_tools.py`](../../src/ada/tools/life_tools.py) · [`mouth.py`](../../src/ada/harness/mouth.py)

**Name stays `M24_MULTI_INTENT_CAPTURE.md`:** this is a **sequence insert** after M23 — **utterance decomposition / N pack-bound writes** — the first **skill-spine** gap after friend-mouth feel. Alternate slug `M24_MULTI_SLOT_LIFE.md` rejected as less precise (slots are the mechanism; multi-intent capture is the product failure).

**Name collision:**

| Candidate | Verdict |
|-----------|---------|
| **`M24_MULTI_INTENT_CAPTURE.md` (this card)** | **PICK.** Phase-1 capture half of life skills: decompose one NL life utterance into N honest fills under Verb→Pack→fill + Confirm-on-ingress + code-bound ids. After M23, before package. |
| Stuff into **M21** (id-bind honesty) | **Reject as home.** M21 owns **Confirm-bind / favorites / no silent top-1** for a *resolved* candidate set. This card owns **splitting one utterance into N slot fills** then feeding each slot through that gate. Related; different failure. Pointer OK. |
| Stuff into **M22** | **Reject.** M22 owns teach-in-flow **stores** (ask-once → sticky). Multi-slot parse is not a store door. |
| Stuff into **M23** | **Reject.** M23 is **feel** only. Live METAL: mouth can sound fine while the write path still lies. |
| **M19a P0** mega-rewrite as home | **Reject as home.** P0 remains implement spine for single-verb packs; this card is the M20 **sequence insert**. Thin pointer on M19a OK — do not bury order under P0 history. |
| Retrieval sibling name (`M22_RETRIEVE…` class) | **Reject.** Retrieval stays **later unnamed** (M22 already took M22 from retrieve). Do not start retrieval here. |
| `M20d` / phase renumber | **Reject.** Do **not** renumber M20 1→5. |

**Supersedes:** any reading that (a) freestyle ReAct “call tools twice” is an honest multi-item meal/gym path, (b) meal_spine / gym_spine may silently drop a second food or set, (c) empty-macro / null-nutrient lines are acceptable durable writes, (d) cortex may sole-pick food `ref_id` after search, (e) chat-Yes / ear Yes binds multi-slot Confirm. **Does not supersede:** M21 Confirm Integrity; M22 teach-in-flow stores; M23 friend register; one Gemini cortex; mouth = register pass on receipts; Verb→Pack→fill; truth > charm; package-later; no food ML.

### Changelog

| Ver | Date | Delta |
|-----|------|-------|
| **v1.0.3** | 2026-08-27 | Pointer only — hard-case resolve recover → [`M25_RESOLVE_RECOVER.md`](./M25_RESOLVE_RECOVER.md) (after this card, before package). Empty-macro **guard** stays here; **recover loop** is M25. |
| **v1.0.2** | 2026-08-27 | METAL ship pointer — implement slices 1–3; phone re-smoke on [`../reviews/M24_IMPLEMENT_PLAN.md`](../reviews/M24_IMPLEMENT_PLAN.md). |
| **v1.0.1** | 2026-08-27 | Pointer only — implement plan → [`../reviews/M24_IMPLEMENT_PLAN.md`](../reviews/M24_IMPLEMENT_PLAN.md) (gap map; not METAL). |
| **v1.0** | 2026-08-27 | Design lock: multi-intent life capture — deterministic multi-slot spine + existing resolve gate; Confirm per ambiguous / brand_fight; fail-closed incomplete lift parse. |

---

## One-liner

One life utterance may mean **N pack-bound slot fills** (meal lines, lift sets). ADA decomposes **deterministically**, resolves each slot through the **existing Confirm gate**, writes only honest macros / complete sets — never silent Gott-coffee brand, empty-egg nutrients, or a dropped lat-pulldown.

---

## Core research question

How should ADA **decompose one life utterance into N pack-bound slot fills** (meal lines, lift sets) so multi-intent capture is honest — Confirm when ambiguous, favorites when sticky, no silent wrong brand, no dropped second exercise — without freestyle ReAct choosing kcal/`ref_id` and without a second cortex?

Secondary lenses:

| Sub-question | Where answered |
|--------------|----------------|
| Why not “Gemini calls tools twice”? | Exec pick · harder-but-correct |
| Meal recipe (split → resolve → Confirm → write) | §G |
| Gym recipe (split exercises/sets; fail closed) | §G |
| Who owns decompose? | Exec pick · §G |
| Skills vs essay-in-prompt | Skills framing |
| METAL vs GAP (live phone) | §F |
| Falsifiers / OPEN / sequence | §H–§J |

---

## Skills framing (Phase 1 = capture half)

In ADA, a **skill** is **pack spine + FACTS + receipts** — not a domain essay stuffed into the cortex prompt. **Phase 1 (this card)** is the **capture half**: decompose + bind so multi-item meals and multi-set / multi-lift NL write honestly. **Hard-case recover** when resolve returns empty macros / miss → [`M25_RESOLVE_RECOVER.md`](./M25_RESOLVE_RECOVER.md) (after this card). **Phase 2–3** (taught gym split / last-session weights / use FACTS while logging) stay under M22 teach-in-flow and later siblings — **OUT of this implement**. **Phase 4** progression / body analysis stays M19 P4 — **OUT / next**, unnamed here. Do not implement 2–4 in the M24 chat.

---

## Scope fence

| IN (this card) | OUT (explicit) |
|----------------|----------------|
| Multi-item meal NL → N resolve → Confirm per ambiguous / brand_fight → one or N honest writes | P4 progression analysis · gym “skill essay” in prompt |
| Multi-lift / multi-set NL → complete `life_lift_log` (or N calls); fail closed if parse incomplete | Package · retrieval · mail · food ML |
| Confirm integrity preserved (ingress Yes only; code binds ids) | M23 feel rewrite · second cortex · ear Yes · chat-Yes bind |
| Empty-nutrient / null-macro **guard** (no silent empty egg write) | Silent auto-favorite · systemd / Phase 0 reopen · **recover loop** (→ [`M25`](./M25_RESOLVE_RECOVER.md)) |
| `pack_router` / meal_spine / gym_spine / loop fast-path **touch plan** | Work campaigns · Invented kcal · mouth choosing tools |

**Stack lock (reaffirm):** one Gemini cortex; mouth = register pass on receipts (M23); Confirm on **ingress screen**; **no ear Yes**; no chat-Yes bind; code binds ids; no Gemini re-picking food `ref_id` after search; Verb→Pack→fill; Favorites / teach-in-flow (M22) same stores.

---

## §8 gate fields ([`00_ASSISTANT_RESEARCH.md`](../00_ASSISTANT_RESEARCH.md))

| Field | Answer |
|-------|--------|
| **Question / capability** | Decompose one life utterance into N pack-bound honest slot fills (meals + lifts) under Confirm Integrity |
| **Lens tags** | **FEASIBLE** (extend existing spines + M21 resolve; no new model) · **EVIDENCE** (doc-19 Verb→Pack; agent skills = scripts-as-tools; AskToAct / LITL Confirm) · **FANFICTION** (omniscient multi-intent magic without Confirm) · **POLICY** (truth > charm; code binds ids; no freestyle process AGI) · **METAL** (phone `runs/2026-08-27/` Gott coffee + empty eggs + lat pulldown no-tool) |
| **Citations** | ≥2: doc-19 Verb→Pack→fill; Anthropic Agent Skills (skills ≠ freestyle); Consent Integrity / LITL; live METAL §F |
| **Pi 5 8GB feasibility** | **Yes** — deterministic parse + existing search/Confirm/write. No second cortex. No food ML. |
| **Learning objective** | Implement chat can wire multi-slot spine + resolve gate without reopening feel, package, retrieval, or “just let Gemini tool-call twice” |
| **Harder-but-correct vs shortcut** | **Correct:** deterministic multi-slot spine + existing M21 resolve gate; cortex may propose a **line list only inside pack fence** — **never** sole `ref_id` authority. **Shortcut rejected:** “just let Gemini call tools twice”; prompt-only nutrition/gym knowledge; analysis-as-fix; freestyle ReAct as multi-intent. |
| **Won’t-chase (this slice)** | Package · retrieval · mail · P4 analysis · food ML · M23 feel · systemd · work campaigns · silent auto-favorite · second cortex · ear Confirm |
| **Acceptance falsifiers** | F-M24-* in §H |
| **Egress impact** | **Control plane:** Confirm on Tailscale HUD (unchanged). **Cortex:** may see pack-fenced line proposals / labels; **never** sole bind of `ref_id`. **Backup:** same meal/gym logs + favorites FACTS. |

---

## Executive summary — the pick

**Do this:** **deterministic multi-slot spine** that owns decompose, then **existing resolve / Confirm gate** per slot; one Gemini cortex stays fill-assist inside the pack fence only.

```text
utterance (multi-intent life)
   │
   ├─ pack_router          → meal_log | lift_log (still Verb→Pack)
   ├─ multi-slot spine     → lines[] / sets[]   ← NEW: decompose owns here
   │         │
   │    each meal line: favorite → local → USDA
   │         │
   │    unique sticky? / brand_fight? / empty nutrients?
   │         │ yes unique+honest          ambiguous / fight / empty
   │         ▼                             ▼
   │    bind id (code)              needs_confirm (ingress)
   │         │                             │
   │         └──────────┬──────────────────┘
   │                    ▼
   │              write N honest fills (or hold all until Yes policy — OPEN #1)
   └─ mouth (M23)  → speaks from receipt(s) only
```

| Keep | Drop |
|------|------|
| Verb→Pack→fill; pack_router meal/lift doors | Freestyle ReAct as the multi-item path |
| M21 Confirm-on-ambiguity; code binds ids | Silent top-1 Gott; Gemini-chosen `ref_id` |
| Favorites after Yes (M22 stores) | Silent auto-favorite |
| Gym parse fail → ask / Confirm | Drop second set silently; no-tool on typed lift |
| Empty-nutrient guard | Write eggs with null macros as “ok” |
| Mouth = register pass (M23) | Mouth invents kcal / chooses tools |

**Why this is the organism move:** live phone (`2026-08-27`) shows M23 mouth can be fine while capture still **lies** — Gott Ice Cream COFFEE silent bind, eggs with empty macros, lat pulldown typed twice with **no tool**. Multi-intent is a **spine** gap, not a feel gap and not a second brain.

---

## §F — METAL vs GAP

| Piece | State | Note |
|-------|--------|------|
| Single-verb packs (`meal_log`, `lift_log`) | **METAL** | `life_p0.yaml` + `pack_router` prefixes / `_ADD_MEAL` / `_LIFT_LINE` |
| `meal_spine` multi-item **split** (`and` / `+` / `,`) | **METAL partial** | Splits pieces, then **silent `candidates[0]`** — no resolve / brand_fight |
| M21 Confirm when `resolve` passed to `life_meal_log` | **METAL** | Gateway hold; favorites after Yes — **spine often omits `resolve`** |
| `resolve_gate.py` | **METAL thin** | Habit decide today; food brand_fight lives in meal/resolve path (M21 card **absent** from tree) |
| Cortex freestyle multi-item | **GAP / lie** | Session `355717c…`: coffee+eggs → search → silent Gott bind + eggs in foods list with **empty macros**; **no Confirm** |
| Empty-nutrient bind | **GAP** | Boiled-egg USDA hit with null CORE → still written / rolled as 744 kcal coffee-only truth |
| `gym_spine` multi-set | **GAP** | `_SET` is one `name load unit × reps` per part; “lat pulldown 30kg x 12 … 35kg x12 … 40kg x 8” → **parse miss** → no tool (`355717c…` twice) |
| Multi-exercise one message | **GAP** | Splitters exist (`,` `/` `and` `then`) but incomplete parts fail closed poorly / silent drop |
| Mouth register (M23) | **METAL** | Feel ≠ write honesty — do not reopen |
| Invented kcal in speech | **related lie** | Observe session `7b8f957…`: Gott search then “~1 kcal if black brew” — numeric guard / resolve still bind |

**Live evidence (2026-08-27):**  
- [`runs/2026-08-27/355717c65ea34a7c8575f7b7c3698f8e.jsonl`](../../../runs/2026-08-27/355717c65ea34a7c8575f7b7c3698f8e.jsonl) — coffee+eggs silent Gott; lat pulldown no-tool ×2; dips freestyle ok  
- [`runs/2026-08-27/7b8f95715dc042d790041c1034993d30.jsonl`](../../../runs/2026-08-27/7b8f95715dc042d790041c1034993d30.jsonl) — single coffee Gott + invented “1 kcal” speech; eggs Observe-denied  
- Life crumbs: `life_e2540a68…` (meal 744 kcal Gott), `life_48b5008e…` (dips only)

---

## §G — Recipe (implement chat)

Ordered; **no second cortex**; reuse M21 Confirm + favorites.

### Meal

1. **Pack-route** multi-item meal NL (`_ADD_MEAL` / `log meal:` / chip) — prefer fast-path over freestyle.  
2. **Decompose** → food pieces (extend `_SPLIT` / qty parse; keep deterministic).  
3. **Per piece resolve:** favorite (sticky) → local cache → USDA; attach `resolve` + candidates.  
4. **Confirm** per ambiguous / `brand_fight` / non-unique brand class (Gott vs brew) — ingress Yes only; code binds `ref_id`.  
5. **Empty-nutrient guard:** if CORE macros null after detail fetch → Confirm or fail closed — **never** silent empty write.  
6. **Write:** one `life_meal_log` with N honest lines **or** N writes (OPEN #1 default: **one meal, N lines** when all resolved).  
7. **Mouth** speaks from receipt only (M23).

### Gym

1. **Pack-route** lift NL (`log lift:` / `_LIFT_LINE` / chip).  
2. **Decompose** → exercises and/or set ladder (same name + `30×12 / 35×12 / 40×8` and `30kg x 12 reps 35kg x12 …`).  
3. Build complete `sets[]` for `life_lift_log` (or N calls if cleaner — OPEN #2 default: **one tool, N sets**).  
4. **Fail closed** if parse incomplete — ask / Confirm for missing load/reps/name; **do not** drop silently; **do not** no-op with empty receipt.  
5. Catalog / custom bind stays code-side (existing lift resolve).

### Who owns decompose

| Role | Authority |
|------|-----------|
| **Deterministic spine** (preferred) | Line/set list, qty, units, set ladders |
| **Cortex** | May propose a **line list only inside pack fence** (assist) — optional later |
| **Never cortex alone** | Food `ref_id`, kcal invent, Confirm `confirmed=true`, tool choice for bind |

Optional checklist: [`../reviews/M24_IMPLEMENT_PLAN.md`](../reviews/M24_IMPLEMENT_PLAN.md).

---

## §H — Falsifiers

| ID | Fail if… |
|----|----------|
| **F-M24-1** | “cup of coffee and 7 boiled eggs” silently binds **Gott Ice Cream COFFEE** (or any brand_fight top-1) without Confirm |
| **F-M24-2** | Egg (or any line) writes with **empty / null CORE macros** as a successful honest meal |
| **F-M24-3** | “lat pulldown 30kg x 12 … 35 … 40 …” (or slash ladder) → **no tool** / silent drop of sets |
| **F-M24-4** | Multi-intent Confirm bound via **chat Yes** or **ear Yes** |
| **F-M24-5** | Cortex / mouth **invents kcal** not in receipt JSON |
| **F-M24-6** | Mouth chooses tools / `ref_id` / panel HTML |
| **F-M24-7** | Gemini sole-picks food `ref_id` after search (reopens M21) |
| **F-M24-8** | Slice starts package, retrieval, P4 analysis, food ML, or M23 feel rewrite as dependency |

M20 / M21 / M22 / M23 falsifiers still bind.

---

## §I — OPEN (≤5) — locked defaults for implement

| # | Question | Default until a later chat locks it |
|---|----------|-------------------------------------|
| 1 | **One meal write vs N meal writes** for multi-item | **One** `life_meal_log` with N lines when all slots resolved; hold whole meal if any line needs Confirm (single card can list N candidates). |
| 2 | **One lift tool vs N calls** | **One** `life_lift_log` with complete `sets[]`. |
| 3 | **Cortex line-list assist** | **Off for v1.0** — deterministic spine only. Optional later: cortex proposes lines **inside pack fence**, spine still owns bind. |
| 4 | **Partial success** (1/2 foods ok) | **Fail closed on the ambiguous/empty line** — do not write the good line silently while dropping the bad; Confirm the fight or ask. **Recover retries** after empty_macros → M25 (not this card). |
| 5 | **Habit multi-intent** (“tick skincare and vitamins”) | **OUT of v1.0** — meal + gym first; habits stay M21/M22 single-verb until a later sibling. |

**Do not reopen as OPEN:** one cortex; Confirm on ingress; no ear Yes; code binds ids; no Gemini `ref_id` authority; M23 feel; package-later; truth > charm; favorites same store.

---

## §J — Sequence vs M20 1→5

**Insert after M23, still before phase 4.** Do **not** renumber 1→5.

```text
  … → [3] UI polish
        → [3→4] M21 life-write honesty (Confirm-bind)
        → [3→4] M22 teach-in-flow
        → [3→4] M23 friend mouth / feel
        → [3→4] M24 multi-intent capture   ← this card (skill-spine capture half)
        → [3→4] M25 resolve recover        (hard-case half — empty_macros / miss)
        → [4] first-boot package
        → [5] workflows / P2 mail
```

**Why still before package:** daily phone already captures; multi-intent **lies** on the live root. Package is newborn install — not the fix for Gott coffee + dropped lifts. Hard-case eggs after the empty guard → M25.

**Won’t-chase:** P4 analysis · gym skill essay · package · retrieval · mail · food ML · M23 feel rewrite · systemd · work campaigns · silent auto-favorite · second cortex.

---

## Citations (thin)

| Claim | Tag | Pointer |
|-------|-----|---------|
| Verb→Pack→fill; skills = packs not freestyle AGI | **EVIDENCE** / **POLICY** | [`../19_JARVIS_JUSTINE_AGENT_RESEARCH.md`](../19_JARVIS_JUSTINE_AGENT_RESEARCH.md) |
| Skills / scripts-as-tools | **EVIDENCE** | [Anthropic Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) |
| Confirm before risky bind | **EVIDENCE** / **POLICY** | Consent Integrity / LITL · AskToAct |
| Live multi-intent failures | **METAL** | `runs/2026-08-27/355717c…`, `7b8f957…` + life crumbs |
| Confirm-bind / favorites | **METAL** | `life_tools.py` · `favorites.py` · phone [`2026-08-26_phone_c369f86f.md`](../reviews/2026-08-26_phone_c369f86f.md) (Gott / brand_fight) |

---

## Locks (do not reopen)

| Lock | Source |
|------|--------|
| Deterministic multi-slot spine + M21 resolve gate | **this card** |
| Cortex never sole `ref_id` / kcal authority | M21 · this card |
| Confirm on ingress; no ear / chat-Yes bind | M15 · M20 · M21 |
| Mouth = register pass; truth > charm | M23 · M19b |
| Favorites / teach-in-flow same stores | M22 |
| After M23, before package; no 1→5 renumber | M20 |
| One Gemini cortex | constitution · M20 |

**Pointer (M26 v1.8):** gateway `spine_required` closes cortex sole-bind gap left from M24 slices — `life_meal_log` commits require meal_spine `resolve.bind_authority`.

---

*End M24. Design lock 2026-08-27 — multi-intent capture / skill-spine capture half; hard-case recover → M25; implement without reopening feel, package, or freestyle ReAct.*
