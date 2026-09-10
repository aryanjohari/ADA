# M27 — Cross-domain catalog ranking (research · design lock)

**Status:** v1.6 — **FREEZE** — no new rank patches until M26 food restart checklist item **#1** (white rice ≠ Beans-and-rice)  
**Date:** 2026-09-11 (v1.6)  
**Host:** `ada-pi5` (Raspberry Pi 5, 8 GiB) · windows: Mac / phone via Tailscale Serve  
**Branch:** `rewrite/v1-body`  
**Kind:** **unified catalog bind ranking policy** — food now (`food_reference.db` + FDC), gym later (`exercise_catalog`). Not ML. Not rip-out of working gates until Step 2 ships replacement.  
**Depends on:** [`M25_RESOLVE_RECOVER.md`](./M25_RESOLVE_RECOVER.md) (recover alt queries · caps) · [`M26_DOMAIN_KNOWLEDGE.md`](./M26_DOMAIN_KNOWLEDGE.md) (organ vs reference · capture grammar) · [`M26_FOOD_DOMAIN.md`](./M26_FOOD_DOMAIN.md) (food resolve chain · **FREEZE v1.12**) · [`M19a_P0_LIFE_CAPTURE.md`](./M19a_P0_LIFE_CAPTURE.md) (catalog shapes · FDC) · [`M22_LIFE_TEACH_IN_FLOW.md`](./M22_LIFE_TEACH_IN_FLOW.md) (favorites sticky) · [`../00_ASSISTANT_RESEARCH.md`](../00_ASSISTANT_RESEARCH.md) §8 · [`../19_JARVIS_JUSTINE_AGENT_RESEARCH.md`](../19_JARVIS_JUSTINE_AGENT_RESEARCH.md) (B-before-search)

**Feeds:** Step 2 implement — `src/ada/harness/catalog_rank.py` shared policy; migrate food gates from [`resolve_gate.py`](../../src/ada/harness/resolve_gate.py); gym `exercise_catalog` bind parity — **paused** until food restart #1.

**Name stays `M27_CATALOG_RANKING.md`:** cross-domain **ranking policy** card. M26 owns *what knowing means*; M25 owns *recover escalation*; M27 owns *how candidates are scored and gated before bind* — one module, two catalogs.

### Changelog

| Ver | Date | Delta |
|-----|------|-------|
| **v1.6** | 2026-09-11 | **FREEZE:** no new rank patches until food restart checklist item **#1** ([`M26_FOOD_DOMAIN.md`](./M26_FOOD_DOMAIN.md) v1.12) — phone `e3ab8d20…` white rice → Beans-and-rice still OPEN. |
| **v1.5** | 2026-09-06 | **Breaded-default falsifier closed:** USDA multi-hit (`pageSize`>1) + form propose-pool — plain cooked chicken breast must not propose breaded tenders when plain exists (phone fail [`1c509c18…`](../../../runs/2026-09-06/1c509c183a6846818d81b7627d06d198.jsonl)). |
| **v1.4** | 2026-09-06 | **Propose-pool rule:** honest null-CORE may remain in the ranked list, but **must not** become `proposed_ref_id` / default Confirm bind when any macro-complete candidate exists (null ≠ proposed). Sort demotion alone was insufficient — enforce on propose. Ties to M26 v1.10 Confirm→write handoff (`55378c77…`). |
| **v1.3** | 2026-09-03 | **M26 v1.9 rank rules:** null-macro branded demoted below generic with macros (`_null_macro_tier`); dry/raw demoted when query says cooked/boiled (`_dry_when_cooked_demote`); rank output feeds Confirm picker (top 5 previews per resolve row). |
| **v1.2** | 2026-09-02 | `rank_catalog_bind` outputs `candidates[]`; HUD meal Confirm picker consumes them (`selected_ref_ids` validated server-side). Bind commit only via spine resolve (`bind_authority=meal_spine`, M26 v1.8). |
| **v1.1** | 2026-09-02 | **Step 2 implemented:** `src/ada/harness/catalog_rank.py` — unified pipeline (`rank_catalog_candidates`, `rank_catalog_bind`, `catalog_form_mismatch`, `macro_implausible`); extended form markers (`skin`, `braised`, `candied`, `glutinous`); food gates migrated from `resolve_gate.py` (thin wrappers remain); falsifier tests in `tests/test_m27_catalog_rank.py`. |
| **v1.0** | 2026-09-02 | Step 1 research card: METAL audit, cross-domain abstraction, proposed unified policy, falsifiers, Step 2 backlog. **Freeze:** no new per-food ranking patches until Step 2. |

---

## 1. Header (summary)

| Field | Value |
|-------|-------|
| **Status** | v1.1 — Step 2 implemented |
| **Date** | 2026-09-02 |
| **Depends on** | M25 · M26 · M19a · M22 |
| **Feeds** | Step 2 implement (`catalog_rank.py`) |

---

## 2. Problem statement

> NL slot query maps to **many valid catalog rows**. Wrong row can have **honest macros** → empty-macro recover and `brand_fight` guards don't fire. Per-food regex patches don't scale.

**Mechanism (not vibes):** Token overlap + FDC search density returns plausible-looking rows whose **name diverges from operator intent** while **nutrients are non-null**. [`decide_food_bind`](../../src/ada/harness/resolve_gate.py) may propose that row; M25 recover filters on `candidate_matches_query`, `implausible_branded_junk`, and `processed_food_mismatch` — but **gaps remain** (skin-on thighs, glutinous rice). Each phone failure drove a **tactical patch** (`implausible_branded_junk` for Mars EGGS, `_PROCESSED_MARKERS` for breaded breast, head-noun gate for emu/salmon). Whack-a-mole is frozen here; Step 2 consolidates into one policy module.

**Phone evidence (same failure class — ambiguous query → wrong honest row → recover skips):**

| Run | Utterance shape | Wrong bind | Why guards missed |
|-----|-----------------|------------|-------------------|
| [`3a38e1a…`](../../../runs/2026-08-28/3a38e1afd622447688828cae5d862924.jsonl) | eggs | Mars Chocolate **EGGS** | Pre-patch; macros null then candy-shaped after detail |
| [`867c54ee…`](../../../runs/2026-09-02/867c54ee…) | chicken thigh | skin-on braised thigh | `skin` / `braised` ∉ `_PROCESSED_MARKERS`; macros honest |
| PASS [`8d90b519…`](../../../runs/2026-08-29/8d90b519fe644aca8991cd96e9bc1bf8.jsonl) | 5 eggs | FDC boiled egg | favorite + Foundation after patches |

---

## 3. Scope

| IN | OUT |
|----|-----|
| Ranking policy for **catalog bind** (food FDC cache, gym `exercise_catalog`) | Food ML / learned ranker |
| Favorites as personal rank boost | Ripping working gates without replacement |
| Confirm vs silent bind rules | Full offline FDC dump (note as optional later) |
| Cache hygiene / poison purge | P4 analysis |
| ≥2 citations + §8 gate fields from [`00_ASSISTANT_RESEARCH.md`](../00_ASSISTANT_RESEARCH.md) | NZ FOODfiles implement |

---

## 4. METAL audit — current rules

*Read from code 2026-09-02. Step 2: ranking policy lives in [`catalog_rank.py`](../../src/ada/harness/catalog_rank.py); `resolve_gate.py` keeps thin wrappers.*

### 4.1 Rule inventory

| Rule | File | What it does | Example failure fixed |
|------|------|--------------|------------------------|
| **Token overlap search** | [`food.py`](../../src/ada/logs/food.py) `search_foods` | Split query on non-word chars; score = matching tokens / total tokens on `name + brand`; sort desc | Baseline local cache hit; fails when short query matches many branded names |
| **Foundation / brand tier sort** | [`food.py`](../../src/ada/logs/food.py) `_foundation_boost` (+ `_ice_cream_demote`) | Sort key: Foundation/SR Legacy/raw-generic (0) < unbranded (1) < branded (2); demote ice-cream rows for generic queries | Gott **COFFEE** ice cream vs coffee beverage |
| **`candidate_matches_query`** | [`resolve_gate.py`](../../src/ada/harness/resolve_gate.py) | Extract head-noun stems (strip prep/modifier stoplists); require `q_stems ⊆ name_stems` | emu for salmon query; white-rice modifier without head noun sole-bind |
| **`brand_vs_query_fight`** | [`resolve_gate.py`](../../src/ada/harness/resolve_gate.py) | Branded row: query tokens hit name but brand tokens disjoint from query → Confirm | Gott Ice Cream **COFFEE** |
| **`implausible_branded_junk`** | [`catalog_rank.py`](../../src/ada/harness/catalog_rank.py) `macro_implausible` (wrapper in `resolve_gate.py`) | Branded + egg query + candy-like macros (carb >30, kcal >400, low protein + high carb) → drop/demote | Mars **EGGS** |
| **`processed_food_mismatch`** | [`catalog_rank.py`](../../src/ada/harness/catalog_rank.py) `catalog_form_mismatch` (wrapper in `resolve_gate.py`) | Candidate name contains form markers ({breaded, tender, fried, skin, braised, candied, glutinous, …}) not in query → demote | breaded chicken **tenders**; skin-on thigh; glutinous rice |
| **`decide_food_bind` sort keys** | [`catalog_rank.py`](../../src/ada/harness/catalog_rank.py) `rank_catalog_bind` (wrapper in `resolve_gate.py`) | Pool = name-matched only; M27 sort pipeline; favorite ref hoisted; **silent bind only** on `favorite_hit` + no brand_fight + macros present; else Confirm | Prevents sole-pick `candidates[0]` on ambiguity |
| **`search_foods_resolved` composite sort** | [`food.py`](../../src/ada/logs/food.py) → `rank_catalog_candidates` | After remote fetch: M27 pipeline (name-match, thin-custom/null-CORE, ice-cream, form mismatch, macro plausibility, Foundation boost, token score) | Foundation egg above Mars in search list |
| **`has_viable_local_candidate`** | [`catalog_rank.py`](../../src/ada/harness/catalog_rank.py) (wrapper in `resolve_gate.py`) | Local pool with macros + no brand_fight + no junk + name match + no form mismatch → skip USDA | Processed-only local must not block FDC fetch |
| **`macros_all_null`** | [`resolve_gate.py`](../../src/ada/harness/resolve_gate.py) | All four macros null → not silent-bind; triggers recover | null-CORE FDC rows |
| **Favorites sticky** | [`favorites.py`](../../src/ada/logs/favorites.py) + M22 | `nutrition_favorites.yaml` keyed by `normalize_query`; inject into candidate pool when name matches; Confirm Yes → `set_favorite(confirmed=True)` | 2nd `5 eggs` silent (~31g P) |
| **Recover alt queries** | [`meal_spine.py`](../../src/ada/harness/meal_spine.py) M25 | `build_alt_queries` (egg/chicken/salmon/rice tables) → `search_foods_resolved` → detail refresh → filter → `decide_food_bind`; caps 3 rounds · 5 searches · ~8s | Stripped `boiled` restored; Foundation egg after miss |

### 4.2 Gaps table

| Gap | Run / note | Why current rules miss |
|-----|------------|------------------------|
| **Skin-on thighs** | `867c54ee…` | **Fixed v1.1** — `skin` / `braised` in `catalog_form_mismatch` |
| **Glutinous vs white rice** | deferred | **Fixed v1.1** — `glutinous` in `catalog_form_mismatch` |
| **Agent bypassing spine** | M26 read-path runs (`0dc871c…`, etc.) | Path integrity ≠ rank — pack fence issue, not sort key |
| **FDC `pageSize: 1` on remote search** | [`food.py`](../../src/ada/logs/food.py) `fetch_usda_search` | First API hit may be branded before local sort sees alternatives |
| **Per-food alt-query rows** | [`meal_spine.py`](../../src/ada/harness/meal_spine.py) `build_alt_queries` | Same whack-a-mole shape as rank patches — Step 2 generalizes or keeps as recover-only |

---

## 5. Cross-domain abstraction

One pipeline for food **and** gym:

```text
query → local cache search → remote fetch (if miss) → score candidates → policy gates → bind decision → Confirm?
```

```text
                    ┌─────────────────────────────────────────┐
  NL slot query     │           catalog_rank (Step 2)          │
  ───────────────►  │  personal boost → stem gate → tier sort  │
                    │  → form mismatch → macro plausibility    │
                    └──────────────┬──────────────────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         ▼                         ▼                         ▼
   food_reference.db         exercise_catalog          favorites / FACTS
   + FDC API                 + seed aliases            (personal boost)
```

| Layer | Food | Gym (later) |
|-------|------|-------------|
| **Catalog** | `food_reference.db` + FDC API | `exercise_catalog` (+ bundled seed) |
| **Query** | slot food name + grams | exercise name + sets/reps/load |
| **Search** | token overlap on `foods` table | exact → alias → alnum/plural fold |
| **Policy** | generic > branded; form mismatch demotion | alias > fuzzy; equipment/movement match |
| **Personal boost** | `nutrition_favorites` | custom exercises / last session |
| **Escape** | Confirm, recover alt queries (M25) | Confirm, catalog miss teach-in (M22) |
| **Bind authority** | code `ref_id`; cortex never sole-pick | code `exercise_id` |

**Gym today (METAL):** catalog lookup in M19a — no shared rank module; fold/alias only. Step 2 applies same **bind decision shape** (`needs_confirm`, `reasons[]`, `proposed_id`) without copying food-specific macro rules.

---

## 6. Research survey (short, cited)

### Why token overlap fails on FDC

- FDC **branded density**: short queries (`eggs`, `rice`, `thigh`) match many product names via substring overlap; score ties at 1.0 when all tokens hit ([USDA FDC search API](https://fdc.nal.usda.gov/api-guide.html)).
- **Honest wrong macros**: branded rows carry valid per-100g nutrients — guards keyed on null-CORE or brand_fight never fire.
- **Remote first-hit bias**: `fetch_usda_search` uses `pageSize: 1` — top API row enters cache before local re-rank.

### What personal informatics / calorie apps do

- **Library-first**: recents, favorites, custom foods before global search ([Li et al., personal informatics stages, CHI 2010](https://doi.org/10.1145/1753326.1753611)).
- **Low-friction re-log**: quantified-self practitioners reuse prior entries ([Choe et al., CHI 2014](https://doi.org/10.1145/2556284.2556964)) — maps to M22 favorites sticky.
- **Confirm on ambiguity**: production trackers surface picker UI when multiple matches — Consent Integrity pattern ([Consent Integrity, 2026](https://arxiv.org/html/2606.02668v1)).

### Why won't-chase ML ranker on Pi (M25/M26 lock)

- Pi 8GB: **rules + Confirm + favorites** — no second model, no embedding index over full FDC ([`00_ASSISTANT_RESEARCH.md`](../00_ASSISTANT_RESEARCH.md) §3.6; M26 won't-chase food ML).
- Learned rankers need labeled bind decisions ADA does not have at scale; tactical patches proved faster to audit than opaque scores.

### B-before-search / library-first (M19, doc-19)

- Life capture **before** open-web search wedge ([`19_JARVIS_JUSTINE_AGENT_RESEARCH.md`](../19_JARVIS_JUSTINE_AGENT_RESEARCH.md) — B-before-search).
- Catalog bind = **local cache + operator favorites** before USDA fetch; matches library-first web organ (M07 cite index).

### Consent Integrity — Confirm when ambiguity

- Risky or ambiguous binds must show **real tool args** before write ([Consent Integrity, 2026](https://arxiv.org/html/2606.02668v1)).
- ADA: `needs_confirm` + gateway ingress; silent bind **only** on sticky favorite with honest macros — default posture for catalog rank output.
- **v1.2:** `rank_catalog_bind` outputs `candidates[]`; HUD meal Confirm picker consumes them (`selected_ref_ids` validated server-side). Bind commit only via spine resolve (`bind_authority=meal_spine`, M26 v1.8).

---

## 7. Unified policy (Step 2 — **implemented**)

Single ordered score pipeline in [`catalog_rank.py`](../../src/ada/harness/catalog_rank.py):

```text
def rank_catalog_bind(query, candidates, *, domain, favorite=None):
    # 1. Personal boost
    if favorite_exact_or_norm_hit(candidates, favorite):
        boost(candidates, favorite.ref_id, tier=0)

    # 2. Head-noun / stem gate (drop or heavy demote)
    pool = [c for c in candidates if stem_must_appear(query, c, domain)]

    # 3. Generic tier (Foundation / SR Legacy / unbranded > branded)
    sort_key += generic_tier(c)   # food: _foundation_boost; gym: catalog vs custom

    # 4. Form mismatch demotion — ONE list per domain, not per-food if
    sort_key += form_mismatch(query, c, domain)
    # food markers extend: skin, braised, candied, glutinous (when query implies plain)
    # gym: variant equipment / machine vs barbell when query says "barbell"

    # 5. Macro profile plausibility (food only; light rules)
    if domain == "food" and macro_implausible(query, c):
        demote heavily or drop

    # 6. Bind decision
    if unique_high_score(pool) and not ambiguous(pool):
        return silent_bind(top)
    return needs_confirm(top, reasons=[...])

    # 7. Recover (M25) if pool weak — alt queries, not rank patch
```

### Consolidation (Step 2 — done)

| Today | Home |
|-------|------|
| `processed_food_mismatch` | `catalog_form_mismatch(domain="food")` |
| `implausible_branded_junk` | `macro_implausible` |
| thigh / rice form rules | extended marker list inside `catalog_form_mismatch` — **not** per-food `if` |

**Silent bind rule (unchanged):** favorite hit + honest macros + no brand_fight. High token score alone ≠ silent.

**Propose-pool rule (v1.4):** honest null-CORE ≠ proposed bind. `rank_catalog_bind` builds `propose_pool` from macro-complete candidates first; `proposed_ref_id` must not be null-CORE when any viable macro candidate exists. Sort demotion (`_null_macro_tier`) is necessary but not sufficient — enforce on propose.

---

## 8. Data substrate

| Path | Role |
|------|------|
| `/mnt/ada-data/logs/food_reference.db` | SQLite `foods` — sources `usda_fdc`, `off`, `custom`; grows on search/insert |
| `/mnt/ada-data/logs/life_logs.db` | Meal truth — `meals`, `meal_foods`, `nutrition_day_rollup` |
| `/mnt/ada-data/secrets/usda_fdc.env` | USDA FDC API key |
| `facts/nutrition_favorites.yaml` | Operator sticky binds (M22) |
| `life_logs.db` → `exercise_catalog` | Gym catalog (M19a) — same bind policy target, different schema |

**Not** a full FDC mirror on disk. **OPEN:** optional Foundation subset import for offline bind without API round-trip.

---

## 9. Falsifiers (F-M27-*)

| ID | Fail if… | Test |
|----|----------|------|
| **F-M27-1** | Generic "chicken thigh" query **sole-binds** skin-on braised without Confirm | `tests/test_m27_catalog_rank.py::test_skin_on_braised_thigh_demoted_for_plain_query` |
| **F-M27-2** | New per-food `if "thigh"` (or similar) patch added while M27 Step 2 **open** | Policy: `catalog_form_mismatch` marker list only |
| **F-M27-3** | Gym catalog bind **copies food hacks** instead of shared `catalog_rank` module | `tests/test_m27_catalog_rank.py::test_gym_*` |
| **F-M27-4** | **Silent bind** when head-noun absent from candidate name | `tests/test_m27_catalog_rank.py::test_no_silent_bind_when_head_noun_absent` |
| **F-M27-5** | Rank policy change **deletes** working gate with no test-backed replacement in same PR | M26 + M25 suites still pass |

M21–M26 / M25 falsifiers still bind.

---

## 10. OPEN (≤5)

| # | Question | Default until locked |
|---|----------|----------------------|
| 1 | **Offline Foundation bundle?** | Optional import — API + cache remain primary |
| 2 | **NZ FOODfiles import rank?** | Out of M27; manual CLI when operator drops bundle |
| 3 | **Gym rank parity scope?** | Step 2: bind **shape** + alias/fold; no food macro plausibility |
| 4 | **Cache TTL / poison purge?** | Manual `forget_foods` custom; no auto purge v1 |
| 5 | **Macro-plausibility thresholds?** | Generalize `implausible_branded_junk` rules; egg-shaped first |

---

## 11. Step 2 implement backlog

*Completed in v1.1 — kept for audit trail.*

- [x] `src/ada/harness/catalog_rank.py` — shared policy (`rank_catalog_bind`, `catalog_form_mismatch`)
- [x] Migrate food gates from [`resolve_gate.py`](../../src/ada/harness/resolve_gate.py) (thin wrappers during transition)
- [x] Extend form markers: `skin`, `braised`, `candied`, `glutinous` (when query implies plain)
- [x] Tests: Mars eggs, breaded breast, skin-on thighs, plain breast — `tests/test_m27_catalog_rank.py`
- [x] Gym: bind decision shape stub (`NotImplementedError` on `rank_catalog_bind(domain="gym")`)
- [ ] Consider FDC `pageSize` > 1 or local re-fetch before cache insert

---

## 12. Freeze declaration

> **v1.6 FREEZE (2026-09-11).** Policy module exists (`catalog_rank.py`). **No new rank patches** — one-off or form-marker — until [`M26_FOOD_DOMAIN.md`](./M26_FOOD_DOMAIN.md) restart checklist item **#1** closes on phone (white rice boiled ≠ Beans-and-rice). Then resume: extend `catalog_form_mismatch` / propose-pool only — still no `if "rice"` branches in `resolve_gate.py` / `meal_spine.py`.

Tactical patches consolidated (still bind after unfreeze):

- No new `if "thigh"` / `if "rice"` branches in `resolve_gate.py` or `meal_spine.py`
- No new one-off entries in `build_alt_queries` except **recover escalation** tied to M25 caps (existing pattern)
- Food gates live in [`catalog_rank.py`](../../src/ada/harness/catalog_rank.py); `resolve_gate.py` wrappers retained for backward compat

---

## §8 gate fields ([`00_ASSISTANT_RESEARCH.md`](../00_ASSISTANT_RESEARCH.md))

| Field | Answer |
|-------|--------|
| **Question / capability** | Unified catalog ranking policy for food + gym bind — stop per-food whack-a-mole |
| **Lens tags** | **EVIDENCE** (personal informatics; Consent Integrity) · **FEASIBLE** (rules on Pi; no ML ranker) · **FANFICTION** (omniscient food matcher) · **POLICY** (Confirm on ambiguity; code binds ids) · **METAL** (resolve_gate · food.py · meal_spine recover) |
| **Citations** | ≥2 in §6 |
| **Pi 5 8GB feasibility** | **Yes** — deterministic rules + SQLite cache + capped FDC GETs |
| **Learning objective** | Step 2 implement can consolidate gates once without another Mars/thighs one-off |
| **Harder-but-correct vs shortcut** | **Correct:** shared `catalog_form_mismatch` + favorites + Confirm. **Shortcut rejected:** per-food regex patches; ML ranker; silent high-score without stem gate |
| **Won't-chase** | Food ML · full FDC mirror · NZ import · P4 · gym pose |
| **Acceptance falsifiers** | F-M27-* §9 |
| **Egress impact** | Unchanged — existing USDA key; optional larger `pageSize` is marginal |

---

## Citations (thin)

| Claim | Tag | Pointer |
|-------|-----|---------|
| Collection vs integration stages | **EVIDENCE** | [Li et al., CHI 2010](https://doi.org/10.1145/1753326.1753611) |
| Reuse / recents in self-tracking | **EVIDENCE** | [Choe et al., CHI 2014](https://doi.org/10.1145/2556284.2556964) |
| Confirm binds real args | **EVIDENCE** / **POLICY** | [Consent Integrity, 2026](https://arxiv.org/html/2606.02668v1) |
| B-before-search | **POLICY** | [`19_JARVIS_JUSTINE_AGENT_RESEARCH.md`](../19_JARVIS_JUSTINE_AGENT_RESEARCH.md) |
| Phone rank failures | **METAL** | `3a38e1a…` · `867c54ee…` · PASS `8d90b519…` |

---

*End M27. v1.6 FREEZE 2026-09-11 — no rank patches until food restart #1.*
