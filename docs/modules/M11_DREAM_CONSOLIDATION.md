# M11 — Dream as consolidation (sleep-time manage)

**Status:** living research card — **M11-B metal shipped** (2026-08-15): per-campaign WORLDVIEW + cite stamp + JSON manage harden + staging CLI. Optional C still gated/off. **METAL follow-up (same day):** smoke showed stamp OK (`cite_heads_by_campaign` had both `bf6e4dadcd50` + `543a7a6c0d35`); gap was merge skipping when a campaign had only `js_shell` heads and manage omitted `campaign_digests` (`not body and not cite_refs`). Fix: still write honest unreadability WORLDVIEW under `worldview/campaigns/<id>/` (no shell `cite:c_…` attach). F10: stamp debt closed for new watches; remaining ungrouped only when `campaign_id` missing on write. Deferred: timer, brief UI, search, deep-pass C, Playwright.  

**Date:** 2026-08-15  
**Host:** `ada-pi5` (Raspberry Pi 5 Model B Rev 1.1, Debian trixie, ~8 GiB RAM)  
**Branch:** `rewrite/v1-body`  
**Depends on:** [`M04_MEMORY_DREAM.md`](./M04_MEMORY_DREAM.md) (dual-store ethics; seal + whitelist merge; `dream.push` stub), [`M10_MEMORY_KNOWLEDGE.md`](./M10_MEMORY_KNOWLEDGE.md) (**metal shipped** classify/chunks/search honesty + Dream cite heads — header still says “design only”; treat code as source of truth), [`M06_CAMPAIGNS_LONG_HORIZON.md`](./M06_CAMPAIGNS_LONG_HORIZON.md) (campaigns / staged open_loops), [`M09_WATCHES_RSS.md`](./M09_WATCHES_RSS.md) (ingest clocks ≠ Dream), [`../02_CONSTITUTION.md`](../02_CONSTITUTION.md) §§8–11 & §16 (`dream.push` ring; dual-store; quiet hours), [`../01_BODY.md`](../01_BODY.md) §5–6 hybrid stores + Dream pipeline.  
**METAL already present:** `src/ada/dream/{delta,seal,manage,merge,run,push}.py`; cite heads in delta (`MAX_CITE_HEADS=20`, `FIRST_CHUNK_CHARS=400`, library ≤8k); manage 12k in / 1024 out; whitelist merge + open_loop staging; `memory/dreams/2026-08-12.md` (prefs-only); outbox seals 2026-08-12; `ada-dream.timer` pointer **not installed**. **OUT:** morning-brief product UI; vendor search; actuators; graph cortex; Mem0/Letta install; training a consolidator; live S3 `dream.push`; Playwright as Dream gate.

**Slice rule:** this card admits **design** of Dream **consolidation architecture** — what manage **reads**, **writes**, **budgets**, **schedules**, and **honesty rules** after M10 made the library usable. It does **not** admit: redoing M04 dual-store ethics; redoing M10 cite schema/chunks; morning-brief productization; Funnel; soul/SOUL.md; Neo4j-as-brain; local main-LLM cortex day one; auto-adding hosts/watches/ontologies.

**Won’t-chase this slice:** continuous Letta/Mem0 memory server; HippoRAG overnight as mind; embeddings as Dream gate; raising manage input to full extracts/PDFs; multi-day mythopoetic Dream; HUD Dream editor; live rclone push; training Auto-Dreamer / GRPO consolidator.

**Name justification:** **`M11_DREAM_CONSOLIDATION.md`** — not `M04b` (M04 closed dual-store + personality substrate + thin Dream *pipeline*), not “second brain” (four stores stay distinct; Dream is **manage**, not consciousness). M10 made shelves searchable. **M11 owns overnight consolidation quality** — digests, conflicts, open-loop staging, per-campaign structure, budgets — so morning surfaces (later) have something honest to show.

**Taste locks (this card):**

| Lock | Decision |
|------|----------|
| Four stores | **Receipts ≠ library ≠ FACTS ≠ WORLDVIEW.** Dream writes WORLDVIEW + stages; never collapses stores. |
| Manage ≠ ingest | **M09 clocks** pull cites. **Dream** digests heads already on disk. Do not re-fetch HTML in Dream. |
| Manage ≠ brief | **03:30 Dream** consolidates. **05:30 brief** (later product) surfaces. Pointer only here. |
| Cite honesty | `extract_ok` / `js_shell` / `empty` / `feed_blob` / `abs_html` — no invent; abs ≠ PDF. |
| FACTS | Whitelist auto-merge only; people/identity always stage. |
| Open loops | **Staged never auto-done.** |
| Graph | Mentions/conflict board = **index / staging**, not mind. |
| Consciousness | Forbidden. Dream = offline write–manage–read. |

```text
  M09 watch wake ──► cites/ (library) + runs/ (receipt)
                           |
  ~03:30 ada dream run     v
  delta: prefs + lifecycle + cite_heads_by_campaign (capped)
                           |
                           v
  ONE capped Gemini manage ──► JSON {digest, fact_candidates[],
        worldview_notes[], open_loops[], conflicts[]}
                           |
           +-- whitelist FACT merge
           +-- stage non-whitelist / people / open_loops / conflicts
           +-- WORLDVIEW / dreams/*.md  (must cite:c_… for web)
           +-- seal outbox; push=skipped
                           |
  ~05:30 brief (NEXT CARD) ── surfaces digests + due campaigns
        x not Funnel  x not soul  x not graph-as-brain
        x not re-fetch  x not auto-done campaigns
```

---

## Operator locks (hard)

1. **No Funnel / public ingress.**  
2. **Gemini primary, intermittent** — Dream is one (optionally two) capped cortex call(s); Pi owns durable state.  
3. **No local main-LLM consolidator day one.**  
4. **No soul / SOUL.md / consciousness.**  
5. **Dual-store stands** — WORLDVIEW never silently overwrites FACTS (constitution §9).  
6. **Campaigns/watches stay** — Dream does **not** auto-add hosts, watches, or ontologies.  
7. **Same cite library** as chat/watch — no private RAG runtime for Dream.  
8. **Tailscale-only control plane.**  
9. **`dream.push` stays stub** until remote + one-time confirm (constitution §8 / §11).  
10. **Quiet hours 23:00–05:30 NZST** — Dream offline OK; no user-facing Dream pings.

---

## 1. Question / goal / admission

**Research questions.**

1. What does Dream **actually consolidate today** on this Pi vs what operators wish?  
2. What do **2024–2026** sleep-time / manage / consolidation systems ship (mechanisms, not vibes)?  
3. How should ADA lock **read set, write set, budgets, schedule, honesty** without collapsing four stores or building the morning brief?  
4. Which architecture is **harder-correct and reversible** on Pi 8GB — thin heads-only, per-campaign WORLDVIEW, two-pass, product sleeptime, graph overnight, or local model?

**Goal (M11 design).**

1. METAL inventory of Dream code + disk (honest).  
2. SOTA survey with ≥10 citations and ≥2 slogan contradictions.  
3. Record model: delta package + WORLDVIEW artifacts + staged proposals.  
4. Budgets + honesty policy.  
5. Options matrix + **one** recommended architecture.  
6. Falsifiers on `field-papers` / `nz-civic`.  
7. ≤7 OPEN for Aryan; stop = no code until locks.

**Admission boundary**

| IN (design now → code later) | OUT |
|------------------------------|-----|
| Consolidation architecture (read/write/budget/schedule/honesty) | Morning-brief product UI / HUD surfacing |
| Per-campaign / per-watch digests vs global mush | Vendor search; actuators |
| Optional second deep-pass design (extract_ok chunks only) | Mem0/Letta product install |
| Conflict board / staged confirm-once (design) | Graph cortex / HippoRAG overnight mind |
| Dream NER as optional later stage | Training consolidator; live S3 push |
| Pointer: brief consumes Dream outputs | Playwright as Dream requirement |
| | Redo M04 ethics or M10 cite schema |

---

## 2. Mental model (≤5 concepts)

| # | Concept | Meaning | Must not confuse with |
|---|---------|---------|------------------------|
| **1. Delta** | Bounded package since `dream_ok`: prefs snapshot + lifecycle tail + **cite heads by campaign** — not full `runs/` or full extracts. | Chat history dump; “everything she knows” |
| **2. Manage** | One capped Gemini JSON pass (`dream_manage`) that proposes digest / FACT candidates / notes / open_loops / conflicts. | Consciousness; chat REPL; second personality |
| **3. Merge / stage** | Whitelist FACT auto-merge; everything else → `memory/staging/`; open_loops **never auto-done**. | LLM “looks safe” merge; campaign completion |
| **4. WORLDVIEW write** | Interpretive digest(s) that **cite** FACT keys and/or `cite:c_…`. Primary Dream product for web nights. | Metal truth; Gemini training weights |
| **5. Seal** | Local checksummed outbox; manage fail-open; `push=skipped`. | Backup success; “she slept well” |

**One sentence:** *Dream is overnight library maintenance — read capped heads, write cited takes, stage risky proposals, seal the package — not a mind, not a brief UI, not an ingest clock.*

**Reject vocabulary:** “Dream understands the field,” “second brain,” “just RAG overnight,” “longer dream = smarter,” “graph = understanding.”

---

## 3. Lens tags

| Tag | Meaning here |
|-----|----------------|
| **FANFICTION** | REM soul; overnight field theorist; Neo4j as mind; continuous sleeptime “becomes someone” |
| **EVIDENCE** | Write–manage–read surveys; Sleep-time Compute; Letta/Mem0 *patterns*; FRONT; Lost-in-the-middle; usable-scale; Anatomy costs; HippoRAG as index |
| **FEASIBLE-on-Pi8GB** | File delta + one Gemini Flash manage; optional tiny second pass; no embedding server; no second agent runtime |
| **POLICY** | Dual-store; whitelist; no Funnel; no soul; quiet hours; Dream ≠ auto-watch |
| **METAL** | What `src/ada/dream/*` and `/mnt/ada-data/{memory,dream}/` do **today** |

---

## 4. METAL inventory (2026-08-15)

Inspected on `ada-pi5`. Paths cited. Tag every claim.

### 4.1 Doc vs code contradiction (do not paper over)

| Claim | Tag |
|-------|-----|
| M10 card header still says **“design only”** | **METAL** (doc stale) |
| Commits `1c15a40` / `1ccdb0c` shipped classify, chunks, search, feed fallback, Dream cite heads | **METAL** |
| M04 card says Dream **implemented** (2026-08-12) | **METAL** |
| This card (M11) is **design only** — consolidation *quality* next | **POLICY** |

### 4.2 Pipeline on metal

| Step | Code | Behavior today | Tag |
|------|------|----------------|-----|
| Delta | `src/ada/dream/delta.py` | Since last `dream_ok`: lifecycle (−dream events, ≤100), fact/worldview file listings, newest ≤20 run paths, prefs whitelist snapshot, **`cite_heads_since` ≤20 × first chunk ≤400 chars**, library section ≤8k, total summary via manage ≤12k | **METAL** |
| Seal | `seal.py` | Copy identity/prefs/open_loops + `delta.json` → MANIFEST checksums → `dream/outbox/<id>/` | **METAL** |
| Manage | `manage.py` | One Gemini `dream_manage`; system JSON schema; honesty lines for cite heads; fail-open | **METAL** |
| Merge | `merge.py` | Whitelist FACT merge; stage rest; stage all `open_loops[]`; WORLDVIEW digest with `cite:c_…` for **extract_ok** heads (skips shells/blobs) | **METAL** |
| Push | `push.py` | Always `push=skipped` | **METAL** / **POLICY** |
| Orchestrate | `run.py` | delta → seal → manage → merge → push → `dream_ok` even if manage skipped | **METAL** |
| Timer | `deploy/systemd/ada-dream.timer` | OnCalendar 03:30; **unit not installed** (`systemctl` not-found) | **METAL** |

### 4.3 Disk state

| Path | What’s there | Tag |
|------|--------------|-----|
| `/mnt/ada-data/dream/outbox/` | Two seals `20260812T045714Z…`, `20260812T051248Z…`; **pre-M10** deltas (no `cite_heads` key) | **METAL** |
| `/mnt/ada-data/dream/sent/` | Empty | **METAL** |
| `/mnt/ada-data/memory/dreams/2026-08-12.md` | Prefs digest; cites `facts/prefs.yaml`, dream id, lifecycle — **no `cite:c_…`** | **METAL** |
| `/mnt/ada-data/memory/worldview/index.md` | Points at that dream | **METAL** |
| `/mnt/ada-data/memory/staging/` | Empty | **METAL** |
| `/mnt/ada-data/memory/lifecycle.jsonl` | Last `dream_ok` **2026-08-12T05:12:55Z** (manage_ok, merged 7 whitelist prefs) | **METAL** |
| `/mnt/ada-data/memory/cites/` | 7 md + 24 index lines; chunks; `abs_html` / `feed_item_fallback` / `feed_blob` | **METAL** (M10) |

### 4.4 Live delta dry-run (no manage call)

`.venv` `build_delta()` after last `dream_ok`:

| Result | Value | Tag |
|--------|-------|-----|
| `cite_head_count` | **7** | **METAL** |
| Grouping | All under **`ungrouped`** — `campaign_id` / `watch_id` **null** on index rows | **METAL** gap |
| Statuses seen | `abs_html`×3, `feed_item_fallback`×2, `feed_blob`×2 | **METAL** |
| `summary_text` chars | ~4093 (under 12k) | **METAL** |

**Operator wish vs metal:**

| Wish | Today | Verdict |
|------|-------|---------|
| Consolidate prefs overnight | Yes (Aug 12 digest) | **METAL** done once |
| Digest **watch nights** with `cite:c_…` | Code path exists; **no dream_ok since M10 cites landed** | **METAL** — ready, **unexercised** |
| Per-campaign WORLDVIEW files | Single global `dreams/YYYY-MM-DD.md` | **METAL** missing |
| Campaign-tagged heads | Heads exist; **campaign_id not written on cites** | **METAL** gap (watch/write path) |
| Conflict board / confirm-once | Conflicts → list + stage reasons; no board UI | **METAL** thin |
| Auto-done campaigns from Dream | Blocked (stage only) | **POLICY** + **METAL** |
| Timer every night | Pointer only; not enabled | **METAL** |
| Morning brief from Dream | Prefs exist; product OUT | **POLICY** |

**What Dream consolidates today (honest):** whitelist prefs + short interpretive digest from **delta summary**. With M10 code, the **next** `ada dream run` would also see cite heads — but would still write **one** global dream MD and would group all heads as `ungrouped` until campaign ids stick on cites.

**FANFICTION:** “Dream already consolidates the field.”  
**FEASIBLE:** Re-run Dream now → first cite-aware digest (still global, still one pass).

---

## 5. SOTA survey (2024–2026) — mechanisms people ship

Citations are design lineage, not training homework. ≥10 sources.

### 5.1 Pattern tables (what / fail / ADA fit)

#### 1. Write–manage–read / hierarchical memory

| Pattern | What labs/products do | Failure modes | ADA fit |
|---------|----------------------|---------------|---------|
| Hierarchical W/M/R | Surveys split working / episodic / semantic / procedural; **manage** (compress, contradict, forget) is the under-built phase ([Zhang et al., 2024](https://arxiv.org/abs/2404.13501); [Memory for Autonomous LLM Agents, 2026](https://arxiv.org/abs/2603.07670)) | Eternal window stuffing; manage skipped → silent rot | **Keep** — Dream = manage; map stores to paths (runs / cites / FACTS / WORLDVIEW) |

#### 2. Sleep-time compute / Letta sleeptime / MemGPT–Mem0 workers

| Pattern | What labs/products do | Failure modes | ADA fit |
|---------|----------------------|---------------|---------|
| Sleep-time compute | Offline precompute on standing context when future queries are **somewhat predictable**; amortize test-time cost (~5× less TT compute on stateful GSM/AIME; multi-query amortize) ([Lin et al., 2025](https://arxiv.org/abs/2504.13171); [Letta blog](https://www.letta.com/blog/sleep-time-compute/)) | Useless if queries unpredictable; cost if sleep-time unbounded | **Adapt** — predictable: “what did watches ingest?” Not speculative answer-cache product |
| Letta sleeptime agent | Second agent edits shared **memory blocks** async; primary stays latency-clean ([docs](https://docs.letta.com/guides/agents/architectures/sleeptime/)) | Two-agent ops; block overwrite races; product lock-in | **Adapt timescale**; **reject** second runtime / dual “souls” |
| Mem0 extract/consolidate | Conversation → salient facts; retrieve; graph variant ~+2% vs base; big win vs full-context dump ([Chhikara et al., 2025](https://arxiv.org/abs/2504.19413)) | Chat-log bias; second store; graph optional theater | **Reject product**; **map** extract→FACTS candidates, consolidate→WORLDVIEW |

#### 3. Reflection / episodic→semantic

| Pattern | What labs/products do | Failure modes | ADA fit |
|---------|----------------------|---------------|---------|
| Generative Agents reflection | Periodic higher-order observations from memory stream ([Park et al., 2023](https://arxiv.org/abs/2304.03442)) | Autobiography invent; consciousness cosplay | **Adapt** as cited WORLDVIEW only |
| Reflexion | Verbal lessons into episodic memory ([Shinn et al., 2023](https://arxiv.org/abs/2303.11366)) | Lesson spam | **Optional** WORLDVIEW `lesson` notes with run cites |
| Auto-Dreamer two-timescale | Offline consolidation family ([2026](https://arxiv.org/html/2605.20616)) | Train consolidator | **Shape only**; **won’t train** |
| Delete / merge / stage | Mem0 ADD/UPDATE/DELETE; Letta rethink blocks; Anatomy: append-only more robust under weak backbones ([Anatomy, 2026](https://arxiv.org/abs/2602.19320)) | Silent corruption from malformed structured writes | **Keep** append-first + validate JSON + **stage** deletes/overwrites |

#### 4. Citation / grounding during consolidation

| Pattern | What labs/products do | Failure modes | ADA fit |
|---------|----------------------|---------------|---------|
| FRONT-style quotes | Fine-grained quotes before attributed answers ([Cao et al., 2024](https://arxiv.org/abs/2408.04568)) | Coarse doc ids hard to verify | **Keep** `cite:c_…` + chunk heads in manage |
| Lost-in-the-middle | Longer retrieved context often hurts; middle missed ([Liu et al., 2024](https://aclanthology.org/2024.tacl-1.9/)) | “Just raise Dream input to 100k” | **Reject** dump; **keep** 12k manage cap |
| Usable-scale | Stored evidence becomes unusable as noise sessions grow ([Shao et al., 2026](https://arxiv.org/abs/2605.07313)) | Keep-all + hope | **Keep** delta + typed heads; don’t paste library |

#### 5. Conflict / prefs / open-loop HITL

| Pattern | What labs/products do | Failure modes | ADA fit |
|---------|----------------------|---------------|---------|
| Preference extraction | Mem0/Letta write user prefs into core blocks | Prefs mush = metal; overwrite without confirm | **Keep** whitelist auto-merge; else stage |
| Conflict detection | Manage emits conflicts; Consent Integrity–class confirm ([constitution lineage](https://arxiv.org/html/2606.02668v1)) | Silent merge of conflicts | **Keep** stage + conflict strings; optional later **conflict board** |
| Open-loop staging | Horizon systems externalize goals; wake later ([Horizon Gap, 2026](https://arxiv.org/html/2608.06663)) | Auto-done without receipts | **Keep** M06: Dream stages only |

#### 6. Multi-source consolidation vs chat-log summarizers

| Pattern | What labs/products do | Failure modes | ADA fit |
|---------|----------------------|---------------|---------|
| Chat-log Dream | Summarize conversation nightly | Misses web library; invents from priors | **Reject** as primary — ADA Dream is **multi-source**: prefs + lifecycle + **cite heads** |
| Doc sleeptime | Letta: sleep agent parses uploaded docs into blocks | Unbounded doc ingest cost | **Adapt** — docs = cite heads/chunks already fetched by M09, not Dream crawl |

#### 7. Graph / HippoRAG as index vs mind

| Pattern | What labs/products do | Failure modes | ADA fit |
|---------|----------------------|---------------|---------|
| HippoRAG | KG as hippocampal **index** + PageRank for multi-hop retrieval ([Gutiérrez et al., 2024](https://arxiv.org/abs/2405.14831)) | Still loses pp as noise grows (usable-scale); ops cost | **Reject as consolidator mind**; optional **mentions index** later |
| Graph MAG fragility | Graph/episodic updates fail silently under weak structured generation; maintenance latency can dominate ([Anatomy, 2026](https://arxiv.org/abs/2602.19320)) | “Graph = understanding” | **Reject** overnight graph consolidator on Pi |
| Mem0g | Graph memory ~+2% over Mem0 base | Marginal gain ≠ Neo4j on 8GB | **Reject** product graph |

#### 8. Cost / latency budgets on small hardware

| Pattern | What labs/products do | Failure modes | ADA fit |
|---------|----------------------|---------------|---------|
| Cap manage | Anatomy: report construction tokens + latency; some MAG >30s maintenance | Unbounded overnight jobs | **Keep** 12k/1024; one pass default |
| Stronger model at sleep | Letta: sleep agent may use heavier model offline | $$ egress; still needs honesty | **Optional later** — Flash default day one |
| Anthropic simplicity | Composable loops > frameworks ([2024](https://www.anthropic.com/engineering/building-effective-agents)) | Framework soup on Pi | **Keep** thin `ada.dream` organs |

### 5.2 Contradictions (≥2 slogans)

| Slogan | Why it fails | Sources | ADA rule |
|--------|--------------|---------|----------|
| **“Just RAG overnight.”** | Manage ≠ retrieval dump; usable-scale + Lost-in-the-middle: more tokens ≠ better consolidation; stored evidence dies without typed interface | Shao 2026; Liu 2024; Memory Agents 2026 | Cap heads; cite-aware digest; don’t paste library |
| **“Graph = understanding.”** | Graphs help multi-hop **retrieval**; fragile under weak backbones; not a mind; Mem0g +2% ≠ ontology | HippoRAG; Anatomy; Mem0 | WORLDVIEW prose + cite-ids; mentions as index only |
| **“Longer dream = smarter agent.”** | Sleep-time helps when queries predictable; unbounded sleep burns cost without accuracy; Anatomy maintenance latency | Lin 2025; Anatomy | Hard caps; fail-open seal; optional short second pass only |

**EVIDENCE verdict:** ship a **bounded, multi-source manage** that writes **cited interpretive digests** and **stages** risky mutations — not a second brain server.

**FANFICTION rejected:** overnight understanding; continuous sleeptime personality; Neo4j Dream.

---

## 6. Align with ADA prior thinking (Phase C)

| Locked idea | SOTA map | M11 stance |
|-------------|----------|------------|
| Per-watch / per-campaign digests vs global prefs mush | Sleep-time works on **predictable** watch queries; MEMTIER rejects flat mush | **Design per-campaign WORLDVIEW** (or sections); prefs stay small side channel |
| Manage over cite heads + `extract_ok` honesty | FRONT + usable-scale | **METAL already**; enforce in falsifiers |
| WORLDVIEW cited takes; FACTS whitelist; open_loops staged | Dual-store + HITL | **Unchanged** (M04/M06) |
| Optional entity mentions / conflict board / confirm-once | HippoRAG-as-index; Consent Integrity | **Design optional**; not v1 gate |
| M09 ingest ≠ Dream manage ≠ morning brief | Sleep-time vs wake vs surface | **Split locked**; brief = pointer only |
| Proprietary candidates | — | Evaluate in options / OPEN |

**Do not invent new product goals.** Brief UI, search vendors, actuators stay OUT.

---

## 7. Record model — what Dream may read / write

### 7.1 May **read** (delta package)

| Field | Source | Cap (v1 design) | Notes |
|-------|--------|-----------------|-------|
| `since` / `last_dream_ok_id` | lifecycle | — | Anchor |
| `prefs_snapshot` | `facts/prefs.yaml` whitelist keys | small | Always |
| `lifecycle_events` | lifecycle.jsonl | ≤100 new non-dream | Tail in summary |
| `fact_files` / `worldview_files` | path listings | listing only | No file bodies |
| `run_files` | newest paths | ≤20 | Paths/bytes only |
| `cite_heads[]` | `cite_heads_since` | ≤20 heads | id, title, url, status, extract_ok, campaign/watch, first_chunk≤400 |
| `cite_heads_by_campaign` | group of heads | library section ≤8k | Prefer real campaign ids |
| `summary_text` | rendered | ≤12k to manage | Honesty footer |

**Must not read into manage:** scratch HTML; full PDF; secrets; unbounded `runs/` JSONL bodies; full chunk lists beyond first-chunk sample (unless optional deep-pass — §11 C).

### 7.2 Manage JSON (write proposals)

```text
{
  digest: string,                    # short; interpretive
  fact_candidates: [{key, value}], # whitelist preferred
  worldview_notes: [string],         # may include cite:c_…
  open_loops: [{text, status, kind?}],  # STAGED only
  conflicts: [string]
}
```

Optional later (design, not required): `campaign_digests: [{campaign_id, digest, cites[]}]`.

### 7.3 May **write** (after merge)

| Artifact | Path | Rule |
|----------|------|------|
| FACT whitelist | `facts/prefs.yaml` | Auto-merge typed clear values only |
| Staged FACT / people / sacred | `memory/staging/<id>.json` | Confirm later |
| Staged open_loops | same staging | Never auto-upsert done |
| Dream digest | `memory/dreams/YYYY-MM-DD.md` and/or `worldview/campaigns/<id>/YYYY-MM-DD.md` | Must cite; web → `cite:c_…` |
| WORLDVIEW index | `worldview/index.md` | Pointers |
| Seal package | `dream/outbox/<dream_id>/` | Always on success path |
| lifecycle | `dream_ok` / details | Manage fail ≠ seal fail |
| push | receipt only | `skipped` |

**Must not write:** allowlist hosts; watches; ontologies; `born_at`; silent FACT clobber; auto-done campaigns.

### 7.4 Staged proposals (HITL)

| Kind | Reason codes (metal examples) | Operator action |
|------|------------------------------|-----------------|
| Non-whitelist FACT | `non_whitelist` | Confirm / reject |
| People / sacred | `people_always_stage`, `sacred_identity_denied` | Confirm |
| Conflict | `conflict_needs_confirm` | Resolve |
| Open loop / campaign | `dream_open_loop_proposal` | Confirm stage flip with receipt policy |
| Malformed | `malformed_fact_candidate` | Discard |

---

## 8. Budgets

| Budget | Locked v1 default | Rationale |
|--------|-------------------|-----------|
| Cite heads | ≤20 | M10 / usable-scale |
| First chunk | ≤400 chars | Enough for abs/feed; not full page |
| Library section | ≤8k chars | Room for prefs/lifecycle in 12k |
| Manage input | ≤12_000 chars | Anatomy + Lost-in-the-middle |
| Manage output | ≤1024 tokens | Structured JSON only |
| Manage passes | **1** default; optional **+1** deep on ≤2–3 `extract_ok` chunks | Cost / reversibility |
| Deep-pass chunk chars | ≤1_200 each (design) | Only if OPEN locks C |
| Schedule | ~**03:30 NZST** timer + manual `ada dream run` + on clean sleep | Body §6.4 |
| Quiet hours | 23:00–05:30 NZST — offline OK | Constitution |
| Brief surface | **05:30** `brief_time` — **not this card** | Pointer |
| Seal | Always local; manage fail-open | M04 |

---

## 9. Honesty / refusal policy

| Rule | Behavior |
|------|----------|
| `extract_ok: false` / `js_shell` / `empty` / `feed_blob` | Digest may say **unreadable / not a document** — **no invent** Beehive stats or paper claims |
| `feed_item_fallback` | OK to cite as feed-derived prose; not HTML-of-record |
| `abs_html` | “Abstract page `cite:c_…`” — **never** claim PDF/body |
| Web claims in WORLDVIEW | Must include `cite:c_…` that exist; merge already attaches extract_ok heads |
| People | Never invent; never auto-merge |
| Campaigns | Never mark done without receipts; stage only |
| Consciousness / feelings | Forbidden in digest |
| Prefs-only night | Prefs cites OK; must not pretend watch consolidation |
| Shell collision same hash | Not “same release” |
| Dream auto-add hosts/watches | **Deny** |

---

## 10. Options matrix → recommendation

| Opt | Architecture | Pi 8GB cost | Gemini egress | Dual-store safety | Reversibility | Depends on M10 | Ops complexity |
|-----|--------------|-------------|---------------|-------------------|---------------|----------------|----------------|
| **A** | Status quo thin manage (heads already in code; one global digest) | Low | 1× Flash/night | High (existing merge) | High | Yes (heads) | Low |
| **B** | Per-campaign WORLDVIEW + richer delta (still **one** manage); fix campaign_id on cites | Low | 1× | High | High (files) | Yes | Low–med |
| **C** | Two-pass: triage heads → deep sample ≤2–3 extract_ok chunks | Low+ | **2×** | High if deep read-only | Med (feature flag) | Yes | Med |
| **D** | Mem0/Letta-like continuous memory server | High RAM/ops | Continuous | Dual-store fight | Low | Weak | **High** |
| **E** | Graph consolidator / HippoRAG overnight | High | High extract | Fragile writes | Low | Partial | High |
| **F** | Local small-model consolidator on Pi | RAM/CPU heavy | Low cloud | Format-error risk (Anatomy) | Med | Yes | High |

### Recommendation (one)

**Choose B (ADA-shaped), with C as a gated reversible add-on — not D/E/F.**

**Why (evidence, not loyalty):**

1. **METAL:** cite-head delta already ships; the gap is **write shape** (global prefs mush / ungrouped heads) and **unexercised** post-M10 dream, not missing a product server.  
2. **Sleep-time Compute:** gains when future queries are predictable — per-campaign “what did `nz-civic` / `field-papers` ingest?” matches that; continuous sleeptime does not.  
3. **Usable-scale + Lost-in-the-middle + Anatomy:** one capped pass + typed heads beats longer dream / graph maintenance on 8GB.  
4. **Dual-store:** B keeps whitelist + stage; D/E invite mush or fragile structured writes.

**What we do *not* copy from SOTA:**

| SOTA thing | Do not copy |
|------------|-------------|
| Letta dual-agent sleeptime server | Second runtime / shared mutable “persona block” as metal |
| Mem0 as organ | Their store + LoCoMo-as-gate |
| Overnight graph consolidator | Neo4j / HippoRAG-as-mind |
| Full chat-log nightly summary as primary manage input | Prefers multi-source cite heads |
| Unbounded sleep-time scaling | Hard caps stay |
| Local consolidator model | Anatomy silent corruption on weak structured writes |

**B deliverables (design → later code):**

1. Ensure watch/cite writes set `campaign_id` / `watch_id` (else heads stay `ungrouped`).  
2. Manage prompt asks for **per-campaign notes** (or structured `campaign_digests`) with `cite:c_…`.  
3. Write `memory/worldview/campaigns/<campaign_id>/YYYY-MM-DD.md` **or** clearly sectioned single dream file — prefer separate files for brief later.  
4. Keep global prefs digest thin when no prefs delta.  
5. Optional **C**: if heads-only falsifier fails (digest too thin / abs chrome noise), second pass on ≤2–3 `extract_ok` chunks behind a flag — default **off**.

---

## 11. Falsifiers (runnable on this Pi)

Use campaigns **`field-papers`** / **`nz-civic`** and current cites.

| # | Falsifier | Pass look |
|---|-----------|-----------|
| F1 | **Heads reach manage** | After M10 cites, `build_delta` `cite_head_count` ≥1 since last dream; summary contains `cite:c_…` |
| F2 | **Shell honesty** | Digest does not invent visitor numbers from `feed_blob` / historical js_shell; may note unreadable |
| F3 | **Feed fallback OK** | `feed_item_fallback` Beehive cites may be summarized **with** `cite:c_9a7…` / `c_d72c…` |
| F4 | **Abs ≠ PDF** | Digest/notes do not claim paper body from `abs_html` |
| F5 | **Cited web digest** | Post-watch Dream WORLDVIEW includes `cite:c_…` for extract_ok heads — not prefs-only |
| F6 | **Whitelist intact** | Non-whitelist FACT candidate → staging; `born_at` untouched |
| F7 | **Open loops staged** | Campaign “done” proposal → staging; open_loops.yaml not auto-flipped |
| F8 | **Seal fail-open** | Manage forced fail → outbox + `dream_ok` still |
| F9 | **No auto-watch** | Dream output does not append allowlist hosts or watches |
| F10 | **Ungrouped debt** | **Pass (2026-08-15):** new watch cites stamp `campaign_id`; heads group under campaign ids; js_shell-only campaigns still get WORLDVIEW. Residual: pre-stamp / missing-id heads → `ungrouped` (global only) |
| F11 | **Four stores** | Article text remains in cites; Dream writes WORLDVIEW; runs stay receipts |
| F12 | **Budget** | Manage input ≤12k; no full extract dump |

Won’t-chase as gates: LoCoMo, Neo4j bakeoff, timer enablement (ops), brief UI.

---

## 12. OPEN questions for Aryan (≤7)

1. **WORLDVIEW layout:** separate `worldview/campaigns/<id>/*.md` **vs** one `dreams/YYYY-MM-DD.md` with sections? (Recommend **per-campaign files** + thin global prefs note.)  
2. **campaign_id on cites:** fix in watch write path now **vs** Dream-side join via `last_receipt`? (Recommend **write path** — cleaner heads.)  
3. **Two-pass (C):** default off until F5 fails quality **vs** always deep-sample 1 abs + 1 civic? (Recommend **default off**; flag.)  
4. **Conflict board:** staging JSON enough **vs** thin `memory/conflicts/board.md` Dream appends? (Recommend **staging first**; board if confirm UX hurts.)  
5. **Dream NER / mentions:** skip **vs** capped NER on heads only in manage JSON? (Recommend **skip v1**; titles + pack keywords.)  
6. **Timer:** enable `ada-dream.timer` after first cite-aware manual dream **vs** manual-only until brief exists? (Recommend **manual smoke first**, then enable.)  
7. **Confirm-once stages:** CLI-only confirm for staged open_loops **vs** wait for brief card? (Recommend **CLI confirm** now; brief surfaces later.)

**Non-questions (locked):** no Funnel; no soul; Gemini primary; Tailscale-only; campaigns stay; no Mem0/Letta organ; no Neo4j Dream; no Playwright Dream gate; no live S3 push; dual-store ethics; open_loops never auto-done; morning brief product OUT of this card.

---

## 13. Ordered research-done → implement-next (design only)

**Stop condition:** no code until Aryan locks OPEN (or explicitly says “code B defaults”).

1. Lock OPEN #1–#3 (layout, campaign_id, two-pass default).  
2. Spec delta schema freeze (document fields already in `delta.py` + optional `campaign_digests`).  
3. Spec WORLDVIEW write paths + cite validation (reuse `memory.worldview`).  
4. Spec manage prompt deltas (per-campaign; honesty unchanged).  
5. Spec campaign_id propagation from `watch/run.py` → cite index.  
6. Spec falsifier smokes F1–F12 (pytest + one live `ada dream run` dry).  
7. Optional C flag design (`ADA_DREAM_DEEP_PASS=0/1`).  
8. Pointer only: brief card consumes per-campaign digests + staging counts.  
9. **Stop** — no Mem0, no graph, no local LLM, no push, no brief UI, no Playwright.

**Implement-next (after locks, not this chat):** campaign_id → per-campaign WORLDVIEW → manual dream smoke on metal → optional timer → optional deep-pass.

---

## 14. Learning goals

1. Why **manage** is a different organ from **ingest** and **brief**.  
2. Why **cite heads + honesty flags** beat “longer overnight context.”  
3. Why **per-campaign digests** beat one prefs mush for predictable morning questions.  
4. Why **whitelist + stage** beats LLM-judged merge.  
5. Why **graph/HippoRAG** is an index pattern, not a Dream mind.  
6. Why **seal can succeed when Gemini fails**.  
7. Why we **reject** Mem0/Letta as organs while still learning from sleep-time compute.

---

## 15. References

### Manage / sleep-time / memory architecture

- Zhang et al., *A Survey on the Memory Mechanism of LLM-based Agents* (2024) — https://arxiv.org/abs/2404.13501  
- *Memory for Autonomous LLM Agents* (2026) — https://arxiv.org/abs/2603.07670  
- *Anatomy of Agentic Memory* (2026) — https://arxiv.org/abs/2602.19320  
- Shao et al., *When Stored Evidence Stops Being Usable* (2026) — https://arxiv.org/abs/2605.07313  
- *MEMTIER* (2026) — https://arxiv.org/abs/2605.03675  
- Lin et al., *Sleep-time Compute* (2025) — https://arxiv.org/abs/2504.13171  
- Letta sleep-time docs — https://docs.letta.com/guides/agents/architectures/sleeptime/  
- Letta sleep-time compute blog — https://www.letta.com/blog/sleep-time-compute/  
- Packer et al., *MemGPT* (2023) — https://arxiv.org/abs/2310.08560  
- Chhikara et al., *Mem0* (2025) — https://arxiv.org/abs/2504.19413  
- Park et al., *Generative Agents* (2023) — https://arxiv.org/abs/2304.03442  
- Shinn et al., *Reflexion* (2023) — https://arxiv.org/abs/2303.11366  
- Auto-Dreamer (2026) — https://arxiv.org/html/2605.20616 — **shape only**  
- *Horizon Gap* (2026) — https://arxiv.org/html/2608.06663  

### Grounding / retrieval / graph-as-index

- Cao et al., *FRONT* (2024) — https://arxiv.org/abs/2408.04568  
- Liu et al., *Lost in the Middle* (2024) — https://aclanthology.org/2024.tacl-1.9/  
- Gutiérrez et al., *HippoRAG* (2024) — https://arxiv.org/abs/2405.14831  

### Simplicity / privacy / confirm

- Anthropic, *Building Effective Agents* (2024) — https://www.anthropic.com/engineering/building-effective-agents  
- *Consent Integrity* (2026) — https://arxiv.org/html/2606.02668v1  
- *Agents That Know Too Much* (2026) — https://arxiv.org/html/2606.26627  

### Metaphor only

- Rasch & Born sleep-consolidation review (2013) — https://pubmed.ncbi.nlm.nih.gov/23589831/ — **not** evidence ADA sleeps  

### Internal ADA

- [`M04_MEMORY_DREAM.md`](./M04_MEMORY_DREAM.md) — dual-store; seal; whitelist  
- [`M10_MEMORY_KNOWLEDGE.md`](./M10_MEMORY_KNOWLEDGE.md) — library honesty; cite heads (**metal**; doc status stale)  
- [`M06_CAMPAIGNS_LONG_HORIZON.md`](./M06_CAMPAIGNS_LONG_HORIZON.md) — staged open_loops  
- [`M09_WATCHES_RSS.md`](./M09_WATCHES_RSS.md) — ingest clocks  
- [`../01_BODY.md`](../01_BODY.md) §5–6 — hybrid stores; Dream pipeline  
- [`../02_CONSTITUTION.md`](../02_CONSTITUTION.md) §§8–11 — rings; Dream ethics; `dream.push`  
- Code: `src/ada/dream/{delta,seal,manage,merge,run,push}.py`, `src/ada/web/cites.py` (`cite_heads_since`), `deploy/systemd/ada-dream.timer`

---

### Lens cheat-sheet

| Claim | Lens |
|-------|------|
| Next dream can see 7 cite heads since 2026-08-12 | **METAL** |
| Last WORLDVIEW digest is prefs-only | **METAL** |
| M10 header “design only” vs shipped code | **METAL** contradiction |
| Per-campaign digests + one capped manage | **EVIDENCE** + **FEASIBLE** + **POLICY** |
| Mem0/Letta/Neo4j as Dream organ | **Reject** (product / fragile / second runtime) |
| Dream = consciousness | **FANFICTION** — forbidden |
| Whitelist + stage | **POLICY** |
| Two-pass deep chunks | **FEASIBLE** optional; not default |

---

*End of M11. Design complete for consolidation architecture. **No code until Aryan locks OPEN questions.** Morning brief remains a later/adjacent product that consumes these digests — not this slice.*
