# M10 — Memory as knowledge (learn / connect / retrieve+cite)

**Status:** living research card — **design only** (2026-08-14): next organ after M07 hands + M08 doors + M09 clocks. Ingest works. Intelligence does not yet. No implementation in this slice.  
**Date:** 2026-08-14  
**Host:** `ada-pi5` (Raspberry Pi 5 Model B Rev 1.1, Debian trixie, ~8 GiB RAM)  
**Branch:** `rewrite/v1-body`  
**Depends on:** [`M04_MEMORY_DREAM.md`](./M04_MEMORY_DREAM.md) (dual-store FACTS/WORLDVIEW; Dream write–manage–read; boot slice; `dream.push` stub), [`M07_WEB.md`](./M07_WEB.md) (fetch + cites + TTL/ETag + `web_cite_search`; observation caps), [`M08_WEB_ALLOWLIST_BASEPACK.md`](./M08_WEB_ALLOWLIST_BASEPACK.md) (doors; WAF/JS honesty), [`M09_WATCHES_RSS.md`](./M09_WATCHES_RSS.md) (campaign watches; RSS ≠ document; one wake), [`M06_CAMPAIGNS_LONG_HORIZON.md`](./M06_CAMPAIGNS_LONG_HORIZON.md) (`open_loops` campaigns, `last_receipt`), [`../02_CONSTITUTION.md`](../02_CONSTITUTION.md) §§8–11 & §16 (dual-store; web egress; quiet hours; `dream.push` ring), [`../01_BODY.md`](../01_BODY.md) §5 hybrid stores.  
**METAL already present:** FACTS YAML; WORLDVIEW/dreams MD; `memory/cites/` + `index.jsonl`; `web_fetch` / `web_cite_get` / `web_cite_search`; watches on `field-papers` / `nz-civic`; `runs/` watch receipts; Dream seal + 12k delta manage; `dream.push` stub. **OUT:** Funnel; local main-LLM cortex; soul/SOUL.md; vendor search as brain; Neo4j day one; Playwright as v1 gate; embeddings as Tier A.

**Slice rule:** this card admits **design** of ADA’s **knowledge / learning organ** — how fetched pages become a **connected, retrievable, citable library** that chat and Dream can *work with*, not a pile of RSS cuts or empty JS shells. It **extends** dual-store (M04) + cites (M07) + watches (M09). It does **not** admit: rewriting M04 personality/Dream ethics; replacing M09 watches; implementation code; Funnel; consciousness; a graph-as-brain; Mem0-as-product; stuffing full HTML into Gemini; deleting `runs/` to “make memory.”

**Won’t-chase this slice:** Neo4j / Zep / GraphRAG as cortex; pgvector embeddings as a coding gate; Mem0/Letta server; Playwright-to-unblock every NZ host; LLM entity-extract on every fetch; collapsing receipts/library/FACTS/WORLDVIEW into one mush file; live `dream.push` S3 (pointer only); training a consolidator; second cite root.

**Name justification:** **`M10_MEMORY_KNOWLEDGE.md`** — not `M04b` (M04 closed dual-store + personality substrate), not `M07b` (hands stay closed), not a second constitution. **Knowledge** = the organ that turns **library pages** into **records you can retrieve and cite**. M04 remains FACTS vs WORLDVIEW ethics. M07 remains fetch. M09 remains clocks. This card is **learn → connect → retrieve**.

**Taste locks (this card):**

| Lock | Decision |
|------|----------|
| Four stores | **Receipts (`runs/`) ≠ library (`cites/`) ≠ FACTS ≠ WORLDVIEW.** Do not collapse. |
| Observation vs disk | Gemini sees a **cap**. Disk may keep **full extract + chunks**. Same 12k for both is the current bug. |
| Empty shells | Challenge/JS pages are **fetch receipts**, not knowledge. Do not index them as documents. |
| Feed XML | **Watch cursor + item URLs** — not a document cite. M09 path is correct; early `web fetch` of RSS is the wrong path. |
| Connections | WORLDVIEW **cite-ids** first; optional **mentions index** (SQLite/files). Graph is not the brain. |
| Retrieval | Boot slice stays tiny. Tools page: `web_cite_search` + cite get + FACT get + WORLDVIEW search. Embeddings only if that fails at lab scale. |
| Dream | Manage **per-watch cite heads/chunks**, not one global prefs mush. |
| Campaigns | **Stay.** This card does not replace M09. |
| Playwright | **Not a v1 gate** unless fetch-only is proven insufficient for *all* NZ HTML (Beehive articles fail; RSS text often exists). |
| Archive | Local HDD first. S3-compatible cold store is a **`dream.push` pointer**, not a gate. |

```text
  Aryan asks  OR  Dream/brief wakes
           |
           v
  [retrieve the RIGHT records + cite-ids — not Gemini weights, not a news dump]
           |
           +--> FACTS get/search          (standing prefs / identity / loops)
           +--> WORLDVIEW search          (interpretive; must already cite)
           +--> web_cite_search → get     (library: page heads + chunks)
           +--> runs/ only if audit       (receipts — not the library)
           |
           v
  answer / digest WITH cite:c_… ids

  write path (learn):
    watch/chat fetch → classify body → full extract on disk → chunks
         → observation cap to cortex → WORLDVIEW may connect (cite-ids)

  x  not Funnel   x  not graph-as-brain   x  not 12k = the document
  x  not RSS XML as a paper   x  not Incapsula as Beehive policy
```

---

## Operator locks (hard)

1. **No Funnel / public ingress** — knowledge is outbound reads + local store (M01).  
2. **Gemini primary, intermittent** — cortex reads **capped observations**; the Pi **owns** the library.  
3. **No local main-LLM as default cortex.** Extract/chunk is deterministic. Dream manage stays one capped Gemini pass.  
4. **No soul / SOUL.md / consciousness.** Learning is write–manage–read on disk.  
5. **Dual-store ethics stand** — WORLDVIEW never silently overwrites FACTS; digests **must cite** (constitution §9).  
6. **Same tools** — chat, watch, Dream consume the **same** cite library. No private RAG runtime.  
7. **Campaigns/watches stay** — M09 clocks still wake ingest. This organ makes those cites *usable*.  
8. **Tailscale-only control plane.**  
9. **Secrets never-to-cloud.** Page excerpts that ride Gemini are already a named cortex-egress cost (M07); don’t fetch operator-secret URLs.  
10. **Dream must not auto-add hosts, watches, or “knowledge graph ontologies.”**

---

## 1. Question / goal / slice admission

**Research questions (operator).**

1. What do 2024–2026 papers say a **personal agent knowledge base** should be (write–manage–read, hierarchical memory, usable-scale, sleep-time compute, citation grounding)? What **contradicts** “just RAG / just a graph / just longer excerpts”?  
2. How can ADA **learn properly** from fetched pages: observation cap vs **on-disk full extract + chunks**; empty/JS cites; abs vs PDF; feed XML ≠ document?  
3. How do **connections** form without a graph-as-brain? (WORLDVIEW cite-ids; optional mentions table/SQLite **index**; won’t-chase Neo4j day one unless evidence demands it.)  
4. How does **retrieval** stay fast but detailed: boot slice + `web_cite_search` + FACT get + WORLDVIEW search vs embeddings vs SQL joins — when each earns a place on Pi 8GB?  
5. How should **Dream manage** consume this memory (per-watch cite heads/chunks, not one mush global delta) so briefs can analyse/connect?  
6. Archival: local HDD vs later **S3-compatible** cold store (`dream.push` lineage) — design pointer only, not a gate.

**Goal (M10 design).**

1. Lock a **≤5-concept mental model** that does **not** collapse the four stores.  
2. Honest **METAL inventory** of `/mnt/ada-data/memory/` + fetch/cite/Dream code as of 2026-08-14.  
3. Survey SOTA with **FANFICTION / EVIDENCE / FEASIBLE-on-Pi8GB** (≥8 citations 2024–2026) including **≥1 contradiction**.  
4. Record model: page / chunk / entity-mention / FACT / WORLDVIEW / campaign — **source of truth** per kind.  
5. Retrieval paths for **chat vs Dream vs brief**.  
6. Empty-cite / JS-shell **policy**.  
7. Options matrix + **harder-correct, reversible** recommendation.  
8. Falsifiers, OPEN for Aryan, ordered implement list (**design only**).

**Admission boundary**

| IN this slice (design now → code later) | OUT |
|----------------------------------------|-----|
| Split observation cap from on-disk extract + chunks | Playwright as required v1 organ |
| Classify empty/JS/feed-blob vs document cites | Neo4j / GraphRAG brain |
| Mentions **index** (files or SQLite) as optional | Mem0/Letta/Zep product |
| Dream delta = per-watch cite heads | Global 12k prefs mush as “knowledge” |
| Retrieval: extend grep/index before embeddings | pgvector gate |
| `dream.push` cold-archive **pointer** | Live S3 upload code |
| Feed-item summary as *fallback extract* when HTML is a shell | Replacing M09 watches |
| abs-grade vs PDF-grade honesty | Training a local consolidator |

---

## 2. Simple mental model for Aryan (≤5 concepts)

| # | Concept | Meaning | Must not confuse with |
|---|---------|---------|------------------------|
| **1. Receipt** | `runs/` JSONL — *we did this fetch/tool at this time.* Audit spine. Campaign `last_receipt` points here. | The article text |
| **2. Library page** | `memory/cites/c_….md` — *a URL we were allowed to read*, with extract/chunks + hash. | A FACT; a WORLDVIEW take |
| **3. FACT** | Standing YAML truth (prefs, identity, loops). Dry. Overwrite = confirm. | A digest; a news clip |
| **4. WORLDVIEW** | Interpretive digest that **cites** FACT keys and/or `cite:c_…` / run ids. Connections live here as **prose + ids**, not as a secret graph. | Metal truth; Gemini’s training weights |
| **5. Chunk / mention** | Sub-page retrieve unit (paragraphs) and optional entity→cite **index**. Speed + join, not a brain. | Neo4j ontology; “she knows” |

**One sentence:** *Receipts prove the homework; the library holds the pages; FACTS are standing truth; WORLDVIEW is the cited take; chunks/mentions make the library searchable — Gemini must retrieve+cite, not remember the news.*

**Reject for v1 vocabulary:** “knowledge graph is ADA,” “just RAG the 12k,” “Dream will figure it out from prefs,” “delete runs to declutter memory,” “longer excerpt = she read the paper.”

---

## 3. Lens tags

| Tag | Meaning here |
|-----|----------------|
| **FANFICTION** | Connected consciousness; Neo4j as soul; overnight Dream “understands the field”; stuffing more tokens until she knows |
| **EVIDENCE** | Write–manage–read surveys; usable-scale; Anatomy graph fragility; FRONT quotes; Lost-in-the-middle; sleep-time compute; Mem0/HippoRAG as *patterns* |
| **FEASIBLE-on-Pi8GB** | Files + JSONL + optional SQLite FTS; deterministic chunk; capped Gemini Dream; no embedding server day one |
| **POLICY** | Dual-store; no Funnel; no soul; campaigns idle; WORLDVIEW must cite |
| **METAL** | What is actually on this disk and in `src/ada/web/fetch.py`, `cites.py`, `dream/`, `watch/run.py` today |

---

## 4. Vision — face / body / connected KB

ADA is the **face** of the Pi: a long-horizon companion that can **talk like a friend** and also **run campaigns**. The Pi is the **body**: it reads the public web (allowlisted), **stores learning durably**, and must **retrieve + cite** when Aryan asks — not dump a news aggregator, not hallucinate from Gemini weights.

North star: a **knowledge base that is connected enough to analyse and work with**, not a pile of RSS cuts.

When Aryan asks *“what did Beehive say about visitors?”* or *“how does that relate to that arXiv paper?”*, the honest path is:

1. `web_cite_search` / FACT / WORLDVIEW tools hit **the right records**.  
2. Observations carry **verbatim excerpts or chunks**.  
3. The answer names **`cite:c_…` ids** (FRONT-class grounding).  
4. If the library is empty or a JS shell, she **says she doesn’t have the page** — she does not invent visitor numbers from a 2024 Gemini prior.

**Hard (unchanged):** no Funnel; no local main-LLM as default cortex; no soul/SOUL.md; Gemini primary; Tailscale-only.

This is **not** consciousness. It is **library science on a Pi**: write clean records, manage them overnight, read them on demand.

---

## 5. METAL inventory — what is on disk today (honest)

Inspected 2026-08-14 on `ada-pi5` under `/mnt/ada-data/`. Code cited from `rewrite/v1-body`.

### 5.1 Four stores (do not collapse)

| Store | Path | What it is **today** | Intelligence? |
|-------|------|----------------------|---------------|
| **Receipts** | `/mnt/ada-data/runs/` (~23 session files; watch JSONL on 2026-08-14) | Episodic audit. `nz-civic` wake `watch_543a7a6c0d35_*.jsonl` shows feed pulled 30 items, 28 `cap_deferred`, 2 `item_fetch` **ok** with cite ids. | Proves *work happened*. Does not hold article text. |
| **Library** | `/mnt/ada-data/memory/cites/` (7 md + `index.jsonl`) | Durable URL records. Mixed quality — see §5.3. | **Shelves.** Search cannot yet answer from excerpts. |
| **FACTS** | `memory/facts/` | `identity.yaml`, `prefs.yaml` (allowlist + voice dials), `people/aryan.yaml`, `open_loops.yaml` schema v2 with campaigns **`field-papers`** / **`nz-civic`** + watch cursors. | Standing config + campaign state. Not web knowledge. |
| **WORLDVIEW** | `memory/worldview/index.md` + `memory/dreams/2026-08-12.md` | One digest. Cites: `facts/prefs.yaml`, `dream:dream-20260812T051248Z-…`, `lifecycle:dream`. **No `cite:c_…`.** Body is prefs (brief 05:30, quiet hours, tease, NZST). | **Prefs, not web.** |

**Operator claim, pressure-tested:** *“We only have shelves / JSON+YAML receipts; Dream can’t be good without proper memory.”*

| Part | Verdict |
|------|---------|
| Shelves exist | **TRUE** — `cites/*.md` + index. |
| JSON+YAML receipts exist | **TRUE** — `runs/` + FACTS YAML + lifecycle. |
| “Only shelves” if that means *no connected KB* | **TRUE enough** — empty Beehive, no chunks, Dream never saw cite heads. |
| Collapse shelves = receipts = FACTS = WORLDVIEW | **FALSE — reject.** Four organs. Dream is weak because **manage reads the wrong slice**, not because receipts should be deleted. |
| Dream can’t be good without proper memory | **TRUE as stated** — current Dream input is a **12k prefs/lifecycle listing**, not the library. Fix the **delta**, don’t invent a fifth mush file. |

### 5.2 Campaigns / watches (M09 on metal — this card does not replace them)

`facts/open_loops.yaml`:

- **`field-papers`** (`bf6e4dadcd50`): RSS `https://rss.arxiv.org/rss/cs.AI`, `max_items_per_wake: 2`, seen guids `oai:arXiv.org:2608.11207v1` / `2608.11210v1`, `last_receipt` → `runs/2026-08-14/watch_bf6e4dadcd50_*.jsonl#…`.  
- **`nz-civic`** (`543a7a6c0d35`): RSS `https://www.beehive.govt.nz/rss.xml`, seen `https://www.beehive.govt.nz/128029` / `128028` (visitor numbers; Foxton solar), same receipt pattern.

Watch code (`src/ada/watch/run.py`) pulls feeds via `ada.web.feeds` (correct — **not** `web_fetch` of XML), triages, then **`web_fetch(item.url)`**. `FeedItem` is `{guid, url, title, published_at}` — **no description/summary**. RSS item bodies are **thrown away**, then article HTML is fetched.

### 5.3 Cite library — row by row

| Cite id | URL | title | truncated | excerpts | hash note |
|---------|-----|-------|-----------|----------|-----------|
| `c_582e3dd1…` | `arxiv.org/abs/2210.03629` ReAct | set | **false** | ~3616 chars (abs + chrome) | document-ish **abstract page** |
| `c_e64127c2…` | `arxiv.org/abs/2608.11207` | set | **false** | ~3563 chars | abs, not PDF |
| `c_240490b4…` | `arxiv.org/abs/2608.11210` | set | **false** | ~3684 chars | abs, not PDF |
| `c_9a7ccc80…` | `beehive…/overseas-visitor-numbers-keep-climbing` | **null** | **false** | **[]** | hash `d0203228…` |
| `c_d72c6127…` | `beehive…/foxton-solar-farm-fast-tracked` | **null** | **false** | **[]** | **identical** `d0203228…` |
| `c_cf877053…` | `rss.arxiv.org/rss/cs.AI` | feed title | **true** | **exactly 12000** | early **`web fetch` of RSS XML** — wrong path |
| `c_aad07276…` | `beehive.govt.nz/rss.xml` | site title | **true** | **exactly 12000** | same wrong path; blob *does* contain visitor/Foxton HTML-in-XML |

**Beehive scratch** `/mnt/ada-data/scratch/web/d0203228….html` (212 bytes):

```html
<META NAME="robots" CONTENT="noindex,nofollow">
<script src="/_Incapsula_Resource?SWJIYLWA=…">
```

That is an **Imperva/Incapsula JS challenge**, not a release. Identical hash on two URLs is expected: both got the **same WAF shell**. `truncated: false` is technically “we didn’t cut 12k of text” and **epistemically false** as “we have the document.”

**arXiv abs:** abstracts are present (`truncated: false` is fair *for the abs HTML extract*). The PDF is not stored. `export.arxiv.org` is already on the allowlist (M08 pack `lab.papers`) — unused as a knowledge path.

**RSS XML cites:** M09 watches do **not** write these. They are leftover **interactive `web_fetch` of feed URLs**. They are truncated blobs, not papers, not releases. Keeping them as “documents” poisons search.

### 5.4 Code — observation cap is also the stored library

`src/ada/web/fetch.py`:

- Download cap **`MAX_BODY_BYTES = 5 MiB`**.  
- **`OBSERVATION_CHAR_CAP = 12_000`**.  
- `_cap_excerpts()` applies that cap; **`write_cite(..., excerpts=excerpts)`** stores **the same list**.  
- Scratch HTML may keep the raw body (`save_raw_html`); **not indexed, not chunked, disposable.**

So: **5 MiB downloaded, ~12k excerpt stored AND observed.** There is no on-disk full extract distinct from the Gemini observation.

`src/ada/web/cites.py` `search_cites`: haystack = **`id + title + url + final_url` only**. Excerpts are **not** searched. Empty-title Beehive rows are nearly invisible except via URL slug tokens (`visitor`, `foxton`).

`src/ada/web/extract.py`: trafilatura, then visible-text. Challenge HTML → empty title/text → empty excerpts, still `status: 200`, `truncated: false`.

`src/ada/dream/delta.py`: summary = lifecycle tail + **file listings** + **prefs snapshot**. **No cite heads. No chunks. No campaign watch titles.**

`src/ada/dream/manage.py`: **`MAX_INPUT_CHARS = 12_000`**, output 1024 tokens, JSON digest/fact_candidates/worldview_notes. Merge (`dream/merge.py`) writes WORLDVIEW citing **prefs + dream id + lifecycle** — which matches `dreams/2026-08-12.md`.

`src/ada/cortex/charter.py`: boot = §14 + identity + anti-fluff + WEB CONTRACT + FACT slice + **optional last WORLDVIEW summary (≤1600 chars)**. **Cites are not in the boot pack** (M04/M07 lock — keep).

`src/ada/dream/push.py`: stub `push=skipped` — local seal only.

`src/ada/memory/search.py`: FACTS grep + WORLDVIEW grep; optional runs grep. **Does not search cites.**

### 5.5 What Aryan’s two example questions would do **today**

| Question | Likely metal path | Failure |
|----------|-------------------|---------|
| “What did Beehive say about visitors?” | `web_cite_search` might hit URL slug `overseas-visitor-numbers…`; `web_cite_get` returns **title null, excerpts []**. RSS blob cite has the numbers in a 12k XML mush but **search doesn’t read excerpts**. Gemini may **hallucinate** or refuse. | Empty knowledge cite + wrong-path blob |
| “How does that relate to that arXiv paper?” | Abs cites have abstracts; WORLDVIEW has **no** cite-ids linking them. Dream never connected visitor-release ↔ cs.AI papers (nor should it without evidence). | No connection layer; abs ≠ PDF |

**Ingest works. Intelligence does not yet.** That sentence is METAL, not mood.

---

## 6. SOTA 2024–2026 + contradictions

Every row tagged. Citations are **lineage for design**, not training homework. **≥8 from 2024–2026.**

### 6.1 What a personal agent KB should be

| Source | Claim / pattern | Tag | ADA takeaway |
|--------|-----------------|-----|----------------|
| **Zhang et al., 2024** — [arXiv:2404.13501](https://arxiv.org/abs/2404.13501) | Memory survey: write / manage / read; hierarchical working / episodic / semantic / procedural beats stuffing the window. | **EVIDENCE** | Map: working = boot slice; episodic = `runs/`; semantic library = cites+chunks; procedural-ish = campaign stages. Not one file. |
| **Memory for Autonomous LLM Agents, 2026** — [arXiv:2603.07670](https://arxiv.org/abs/2603.07670) | Formal loop **write → manage → read**. Manage (compress, contradict, forget, consolidate) is the under-built phase. Architecture often beats model. | **EVIDENCE** | ADA already *named* Dream as manage (M04) but manage **does not ingest the library**. That is this card. |
| **Lin et al., Sleep-time Compute, 2025** — [arXiv:2504.13171](https://arxiv.org/abs/2504.13171) | Offline precompute helps when future queries are **somewhat predictable**; amortizes test-time cost. | **EVIDENCE** | Predictable: “what did watches ingest?” Morning brief / “what did Beehive say?” Dream should pre-digest **cite heads**, not prefs. |
| **FRONT (Cao et al., 2024)** — [arXiv:2408.04568](https://arxiv.org/abs/2408.04568) | Fine-grained **quotes** before attributed answers; coarse document IDs are hard to verify. | **EVIDENCE** | Observation = verbatim chunks + `cite_id`. WORLDVIEW `cites: [cite:c_…]`. Don’t train FRONT; copy the **shape**. |
| **Anthropic, Building Effective Agents, 2024** — [post](https://www.anthropic.com/engineering/building-effective-agents) | Simple composable loops beat heavy frameworks. | **EVIDENCE** | Thin file organs + optional SQLite index. No Mem0/LangGraph memory product day one (same M04 reject). |
| **Packer et al., MemGPT, 2023** — [arXiv:2310.08560](https://arxiv.org/abs/2310.08560) | OS-inspired paging; self-directed memory ops. | **EVIDENCE** (lineage) | Boot = main memory; tools page cites. Dream = offline maintenance. Already ADA-shaped. |
| **Mem0 (Chhikara et al., 2025)** — [arXiv:2504.19413](https://arxiv.org/abs/2504.19413) | Extract/consolidate/retrieve salient **conversation** facts; graph variant +2% vs base; big win vs full-context dump. | **EVIDENCE** as *pattern*; **FEASIBLE** reject as *product* | Prefer DIY FACTS+cites. Mem0g is not a reason to Neo4j on 8GB. |
| **Letta sleep-time docs** | Background agent edits memory blocks; interactive agent stays latency-clean. | **EVIDENCE** | One organism, two cortex **purposes** (`chat_interactive` vs `dream_manage`) — not two souls. |

### 6.2 Contradictions (must not “just RAG / just a graph / just longer excerpts”)

| Contradiction | Source | What it breaks | ADA rule |
|---------------|--------|----------------|----------|
| **Stored evidence becomes unusable at scale** even when the answer is *in* the store — reliability drops as irrelevant sessions grow; usability is conditional on interface + interaction budget. | **Shao et al., 2026** — [arXiv:2605.07313](https://arxiv.org/abs/2605.07313) *When Stored Evidence Stops Being Usable* | “We’ll just keep all the 12k blobs and grep later.” | **Index + typed records + budgeted tool calls.** Don’t dump the library into Dream or boot. |
| **Graph architectures are empirically fragile** (backbone-sensitive structured writes, silent corruption, maintenance latency). Append-only often more robust. | **Anatomy of Agentic Memory, 2026** — [arXiv:2602.19320](https://arxiv.org/abs/2602.19320) | “Just a knowledge graph and she’ll reason.” | **Won’t-chase Neo4j day one.** Mentions table is an **index**. WORLDVIEW holds the take. |
| **HippoRAG graphs help multi-hop *retrieval*** (KG as hippocampal **index** + PageRank), not as the agent’s mind — and usable-scale still saw HippoRAG lose 16–20 pp as noise sessions grew. | **Gutiérrez et al., 2024** — [arXiv:2405.14831](https://arxiv.org/abs/2405.14831); Shao et al. 2026 again | “Just a graph *or* just RAG.” Both incomplete. | Connections = **cite-ids in WORLDVIEW** + optional mention index. Graph-as-brain = **FANFICTION**. |
| **Verbosity ≠ veracity.** More retrieved tokens / longer context often **hurts**; models miss the middle; performance saturates while retriever recall still climbs. Coarse citations ≠ grounded quotes. | **Liu et al., 2024** *Lost in the Middle* — [TACL](https://aclanthology.org/2024.tacl-1.9/); FRONT 2024 | “Just raise the excerpt cap to 100k.” | Keep **12k (or less) in the prompt**; keep **full extract on disk**; retrieve **the right chunk**. |
| **Flat MEMORY.md / daily mush collapses.** Context truncation, structural blindness (co-occurrence ≠ relation), no attribution from tools back to memory entries. | **MEMTIER, 2026** — [arXiv:2605.03675](https://arxiv.org/abs/2605.03675) | One Dream digest of “everything that happened.” | Dual-store already rejected mush (M04). **Don’t recreate mush as a 12k RSS excerpt or a prefs-only Dream.** |

**EVIDENCE verdict:** a personal KB is **typed records + an explicit manage pass + citation-grained read**. The failure mode on this Pi is not “too few embeddings.” It is **empty writes, uncited (or prefs-cited) digests, and retrieval that cannot see excerpts**.

**FANFICTION rejected:** overnight Dream becomes a field theorist; Neo4j “is” ADA; longer WAF HTML will eventually contain policy.

---

## 7. Record model — source of truth per kind

| Kind | Source of truth | May contain | Must not be treated as |
|------|-----------------|-------------|------------------------|
| **Receipt** | `runs/<date>/*.jsonl` line | tool args, `cite_id`, HTTP status, watch skip reasons | Article body; FACT |
| **Page (cite)** | `memory/cites/<id>.md` + index head | url, ts, hash, `extract_status`, title, **full extract pointer**, receipt_id, campaign/watch ids | WORLDVIEW; “I understood” |
| **Chunk** | Sidecar or sections under the cite (`chunks: [{i, text, char_range}]`) or `cites/chunks.jsonl` | Retrievable spans | The whole paper; a FACT |
| **Feed cursor** | `open_loops` watch `cursor` | seen guids, etag | Document text |
| **Feed item summary** | Optional field on page cite when HTML failed and RSS `<description>` is real prose | Fallback extract, `extract_source: feed_item` | HTML-of-record if we later get a real page |
| **Entity mention** | Optional index `(normalized_name, cite_id, chunk_i, campaign_id)` | Join key | Ontology; people-CRM (M04 still no CRM) |
| **FACT** | `memory/facts/*.yaml` | prefs, identity, people stub, loops | News; Gemini prior |
| **WORLDVIEW** | `worldview/*.md`, `dreams/*.md` | Interpretive synthesis **with cites[]** | Metal; a substitute for missing extracts |
| **Campaign** | `open_loops` campaign row | stages, watches, `last_receipt`, cadence | The library |

**Write rules (design):**

1. Every successful HTTP GET still appends a **receipt**.  
2. A **page cite** is created only if we intend library use. Feed XML GETs stay receipts (+ cursor), not pages (M09 already).  
3. `extract_status`: `ok` | `empty` | `js_shell` | `truncated_download` | `feed_item_fallback` | `abs_html` | `pdf` …  
4. `truncated` means **text was cut**, not “looks complete.” Empty shell → `extract_status=js_shell`, **not** `truncated: false` as success theater.  
5. WORLDVIEW `cites[]` should prefer `cite:c_…` for web claims (M07 already validates on-disk cite ids). Prefs-only cites are legal for **prefs** dreams, illegal as a substitute for web.

**Scratch HTML** stays disposable cache for re-extract. Knowledge path is **extract + chunks**, not raw HTML in boot/Dream.

---

## 8. Learn properly from fetched pages

### 8.1 Observation cap vs on-disk full extract + chunks

| Layer | v1 metal | Recommended |
|-------|----------|-------------|
| Download | 5 MiB | Keep |
| Gemini observation | 12k | Keep **or slightly lower** (Lost-in-the-middle) |
| Stored excerpts | **same 12k** | **Full extract on disk** (char cap e.g. 200k–1M per page, then chunk) |
| Retrieve | whole excerpt or nothing | **chunk by query** / first N chunks + title |

**FEASIBLE-on-Pi8GB:** chunking is string split (paragraph / 800–1200 chars, small overlap). No local embedding model required.

**Reversible:** keep writing `excerpts[0]` as the observation-sized **head** so old `web_cite_get` clients still work; add `extract_path` / `chunks`.

### 8.2 Empty / JS-shell policy (don’t store challenge pages as knowledge)

| Signal | Example on this Pi | Policy |
|--------|--------------------|--------|
| Tiny HTML + Incapsula/Akamai/Cloudflare challenge markers | Beehive release URLs | **`extract_status: js_shell`**. Do **not** present as a document. Index **suppress** for `web_cite_search` knowledge queries (still findable by URL for debug). Receipt stays. |
| HTTP 200 + empty trafilatura | same | Same bucket. `title: null`, `excerpts: []` must not look like success in observations (`ok` for *transport*, `extract_ok: false` for *library*). |
| RSS/Atom XML | `rss.arxiv.org`, `beehive…/rss.xml` | **Not a page cite.** Watch parser only. Existing two XML cites: mark `kind: feed_blob` / exclude from knowledge search (tombstone). |
| Real HTML, JS chrome but article in HTML | many govt pages | Fetch-only **OK**. |
| SPA with no article text | some news | Say empty; **do not** Playwright-the-organ. Per-host later. |

**Playwright:** **not a v1 gate.** Beehive **homepage/article** WAF is known (M08). Beehive **RSS** already contains the release prose (visible in the 12k XML blob and in feed `<description>`). Fetch-only is **not** proven insufficient for *all* NZ HTML — RNZ/Newsroom/legislation were packed as HTML-useful. Browser automation remains M07 won’t-chase until a **pack-wide** empty-extract soak says otherwise.

**Fallback (design):** if article extract is `js_shell` **and** the watch has a feed item summary, write `extract_source: feed_item` with that summary as chunks. Provenance honest. Better than empty Incapsula “documents.”

### 8.3 Abs vs PDF

| Grade | What we have | Honesty line |
|-------|----------------|--------------|
| **abs HTML** | arXiv `/abs/…` extracts ~3.5k, abstract + site chrome | “I read the **abstract page** `cite:c_…`.” Not “I read the paper.” |
| **PDF** | not fetched; `export.arxiv.org` allowlisted | Later: optional `web_fetch` PDF → text extract → chunks. Separate cite or `format: pdf` child. |
| **HTML experimental** | arXiv “View HTML” | Optional; still not a substitute for PDF if equations matter. |

**Don’t** set `truncated: false` on an abs cite and let the model say it read Distribird’s proofs.

### 8.4 Feed XML ≠ document

M09 lock stands. `FeedItem` should grow an **optional `summary`** for fallback extract **without** turning the feed URL into a library page.

Wrong path already on disk: `c_cf877053…`, `c_aad07276…`. Treat as **legacy feed_blob**. Do not let Dream summarize them as “today’s cs.AI papers” without per-item cites.

---

## 9. Connections without a graph-as-brain

**Where connections live (locked order):**

1. **Same campaign** — `field-papers` cites vs `nz-civic` cites are already grouped by watch. Cheap, METAL.  
2. **WORLDVIEW prose + cite-ids** — “Visitor-release `cite:c_9a7…` is *about tourism stats*; paper `cite:c_e641…` is *about multi-agent governance* — **no evidenced relation**.” That *is* a connection (including **non**-connection). Sleep-time compute: Dream writes this when asked to relate **this wake’s** heads.  
3. **Mentions index** (optional, reversible) — table/JSONL: `Beehive`, `Louise Upston`, `cs.AI`, `arxiv:2608.11207` → cite ids. SQLite FTS5 **FEASIBLE** on Pi; files-first is enough at 7 cites and still honest at ~10k.  
4. **Graph product** — HippoRAG-class **index** only if (3) fails multi-hop *and* Anatomy costs are acceptable. **Won’t-chase Neo4j day one.**

**Not connections:** identical `content_hash` on two Beehive URLs (that’s a **shell collision**, not “same policy”). Co-occurrence in a 12k RSS blob (MEMTIER structural blindness).

**Entity CRM:** still out (M04). Mentions are **strings on pages**, not `people/*.yaml` until Aryan confirms.

---

## 10. Retrieval path — chat vs Dream vs brief

### 10.1 Chat (interactive face)

```text
boot (small):  §14 + identity + FACT slice + last WORLDVIEW summary
                 — no cite dump (usable-scale)

turn tools:    memory_facts_get/search
               memory_worldview search
               web_cite_search  →  web_cite_get (chunk-aware)
               web_fetch only on miss/stale/force

runs grep:     opt-in audit (“show the receipt”), not default knowledge
```

**When each extra tech earns a place on 8GB:**

| Tech | Earns a place when | Too early if |
|------|--------------------|--------------|
| Token-AND index (today) | Tens–hundreds of titles/URLs | Excerpts/chunks exist but aren’t in the haystack — **fix this first** |
| SQLite FTS on chunks | Thousands of chunks; grep of md is slow/noisy | 7 cites |
| SQL joins mentions↔cites | “Everything mentioning visitors + Upston” is a real query | Can be a JSONL scan |
| Embeddings / pgvector | FTS systematically misses paraphrase at lab scale | Day-one gate; RAM + ops |
| Vendor `web_search` | Library miss + no URL (M07 v1.1) | As a substitute for cites |

### 10.2 Dream (manage)

**Today:** 12k of prefs + file names → prefs digest.  
**Recommended:** delta package **sections**:

- New/updated **cite heads per watch/campaign** (id, title, url, extract_status, first chunk ≤N chars).  
- Cap: e.g. ≤20 heads, ≤8k chars **library**, plus small prefs/lifecycle.  
- Prompt: connect **within and across those heads** with `cite:c_…`; refuse to invent Beehive numbers if `extract_status ≠ ok|feed_item_fallback`.  
- Still **fail-open** seal if Gemini fails (M04).

Do **not** feed scratch HTML. Do **not** feed full PDFs.

### 10.3 Morning brief / campaign check

Budgeted: due campaigns + `last_receipt` pointers + **new cite titles + extract_status** + last WORLDVIEW. User-facing after quiet hours (M06/M09 heal-first). Empty shells listed as **fetch failed to extract**, not as “2 releases read.”

---

## 11. Empty-cite / JS-shell policy (checklist)

1. Classify before `write_cite` as knowledge.  
2. Observation to the model: `extract_ok: false`, `extract_status: js_shell`, **no fake truncated:false completeness**.  
3. Knowledge search default: **exclude** `js_shell` / `feed_blob` / empty.  
4. Operator/debug search may include them.  
5. Watch: try feed-item fallback once; if still empty, skip promoting to WORLDVIEW.  
6. Never “I read the Foxton release” without a non-empty extract receipt (M09 F1, tightened).

---

## 12. Options matrix

| Option | Write | Manage | Read | Tag | Verdict |
|--------|-------|--------|------|-----|---------|
| **A. Files-only** (today + chunks in md) | Atomic md + jsonl | Dream reads heads | grep / token-AND | **FEASIBLE** | **v1 spine.** Extend, don’t replace. |
| **B. SQLite index** (FTS + mentions) | Files remain SoT; DB is **rebuildable index** | Same | Fast join/search | **FEASIBLE** when files hurt | **v1.1** if grep lags. Reversible: delete DB, files remain. |
| **C. Graph (Neo4j / Zep / GraphRAG)** | LLM-extracted triples | Graph maintenance | Multi-hop traversal | **EVIDENCE** mixed; **Anatomy** fragile | **Won’t-chase day one.** |
| **D. Embeddings** | Chunk vectors | Drift/reindex | Semantic kNN | **EVIDENCE** RAG default elsewhere | **Tier B** if FTS fails paraphrase at *this* scale. |
| **E. Mem0 / Letta server** | Their store | Their consolidator | Their API | **EVIDENCE** product; **POLICY** second runtime | **Reject** as organ. Map extract/retrieve ideas only. |
| **F. Raise excerpt cap only** | Bigger 12k→100k in cite + prompt | Unchanged | Dump more tokens | **FANFICTION** vs Lost-in-the-middle | **Reject** as the intelligence plan. |
| **G. Playwright all NZ HTML** | Rendered DOM | Same | Maybe fewer empty cites | **FEASIBLE** costly; **POLICY** later | **Not v1 gate.** Feed fallback first for Beehive. |

**Chosen default:** **A now (design)**, **B when earned**, C/D/E/F/G as labeled.

---

## 13. Recommended ADA design (harder-correct, reversible)

**Harder-correct:** typed page records with **extract_status**, **full extract + chunks on disk**, Dream on **per-watch heads**, answers with **cite-ids**, four stores uncollapsed.

**Shortcut rejected:** bigger excerpts in the prompt; Neo4j; Mem0; deleting `runs/`; one MEMORY.md; Playwright-first.

**Reversible sequence:**

1. **Classify + honesty flags** on write (js_shell / feed_blob / abs_html) — old clients still parse md.  
2. **Stop capping disk at 12k**; keep observation cap. Store extract + chunks.  
3. **Search haystack += title + first chunk + optional extra**; still no boot dump.  
4. **FeedItem.summary** → fallback extract for shell pages.  
5. **Dream delta** includes new cite heads grouped by campaign/watch. WORLDVIEW must `cite:c_…` for web claims.  
6. **Tombstone** the two RSS XML cites as non-knowledge.  
7. **Optional SQLite FTS** as a cache of the same files.  
8. **PDF abs-vs-full** as a later fetch option on `export.arxiv.org`.  
9. **`dream.push`** remains stub; when a remote exists, sealed packages may include **cite manifests** (ids + hashes), not a second live crawl. Cold store = **pointer**, not a gate.

**Campaigns/watches:** unchanged clocks. This organ sits **downstream** of `ada watch run`.

---

## 14. Archival (pointer only)

| Tier | Where | Role |
|------|-------|------|
| Hot | `/mnt/ada-data/memory/cites/` + FACTS + WORLDVIEW | Working library |
| Episodic hot | `/mnt/ada-data/runs/` | Receipts; may date-rotate **later** (M07) without deleting cites |
| Disposable | `scratch/web/` | Raw HTML; re-extract cache |
| Seal | `/mnt/ada-data/dream/outbox/` | Checksummed Dream packages (already) |
| Cold (later) | S3-compatible via **`dream.push`** (constitution §8.4 / §11 backup ring) | Off-box copy of seals ± cite manifests |

**Not a gate:** coding this card does not require rclone. Stub stays honest (`push=skipped`).

---

## 15. Falsifiers

| # | Falsifier | Pass look |
|---|-----------|-----------|
| F1 | **Empty Beehive as knowledge** | `web_cite_search "visitors"` does not treat Incapsula cites as “I read the release.” Observation `extract_ok: false`. |
| F2 | **Abs ≠ PDF** | Model/WORLDVIEW must not claim paper-body from `/abs/` cite alone. |
| F3 | **12k cut ≠ document** | Disk extract for a long HTML page exceeds 12k while Gemini observation stays capped; `truncated` describes the **observation**, not “library complete.” |
| F4 | **Uncited digest** | Dream/WORLDVIEW web claims include `cite:c_…` that exist on disk — not prefs-only for watch nights. |
| F5 | **Four stores** | A design/code path that writes article text only to `runs/` or only to WORLDVIEW **fails**. |
| F6 | **Feed XML as paper** | Knowledge search excludes `rss.arxiv.org/rss/cs.AI` blob as if it were a cs.AI paper. |
| F7 | **Identical shell hash** | Two Beehive URLs with hash `d0203228…` are classified **shell**, not “same release.” |
| F8 | **Dream mush** | Manage input contains **per-watch cite heads**, not only prefs YAML dump. |
| F9 | **Chat retrieve+cite** | “What did Beehive say about visitors?” either quotes a **non-empty** extract/chunk with cite-id **or** refuses. No Gemini-prior visitor stats. |
| F10 | **M09 still stands** | Watch wake still one campaign; this card adds no crawl-all. |
| F11 | **Playwright not smuggled** | v1 design works with fetch + feed fallback; browser not required to close the card. |
| F12 | **No Funnel / no soul / Gemini primary** | Unchanged. |

Won’t-chase as gates: LoCoMo leaderboard, Neo4j bakeoff, 100k-cite soak.

---

## 16. OPEN questions for Aryan

1. **Beehive v1:** feed-item `<description>` as fallback extract **vs** leave shells empty until a non-JS HTML appears **vs** later Playwright for civic only? (Recommend **feed fallback** — reversible, matches M08 “use the feed.”)  
2. **arXiv depth:** abs-only until a campaign stage says `fetch_pdf` **vs** always PDF for `field-papers`? (Recommend **abs default**; PDF on explicit stage / ask — cost + size.)  
3. **SQLite:** skip until cite count hurts **vs** add FTS early as rebuildable index? (Recommend **files first**; SQLite when grep is the pain.)  
4. **Mentions:** titles-only regex **vs** capped Gemini NER in Dream (not on every fetch)? (Recommend **titles + watch pack keywords first**; Dream NER optional.)  
5. **Tombstone RSS blobs:** hide from search now **vs** delete files? (Recommend **hide/mark**; don’t delete without Aryan — constitution retention.)  
6. **Brief vs Dream:** 03:30 ingest-only (M09) + 03:30 Dream on **new cites** + 05:30 brief surface — confirm this split? (Recommend **yes**.)  
7. **Chunk size:** ~1k chars **vs** paragraph-only **vs** whole extract until 50k? (Recommend **~800–1200 char chunks** + title head.)

Non-questions (locked): no Funnel; no soul; Gemini primary; Tailscale-only; campaigns/watches stay; no Neo4j day one; no Mem0 organ; dual-store ethics; `dream.push` not a gate.

---

## 17. Ordered “research done → implement next” (**design only**)

1. **Cite schema bump** — `extract_status`, `kind` (`page` \| `feed_blob` \| `abs_html` \| …), `extract_ok`; observation vs stored extract split.  
2. **Classifier** — challenge/empty/XML vs HTML/PDF (deterministic).  
3. **Full extract + chunks on disk**; keep 12k **head** for observation.  
4. **`web_cite_search` haystack** — include title + chunk text; default-exclude shells/blobs.  
5. **Tombstone** existing RSS XML cites + Beehive shell cites in index (mark, don’t silently delete).  
6. **`FeedItem.summary`** + watch fallback write when HTML is js_shell.  
7. **Dream delta** — per-watch cite heads; WORLDVIEW `cite:c_…` for web.  
8. **Charter / WEB CONTRACT line** — retrieve+cite; abs ≠ PDF; empty extract = don’t claim read.  
9. **Smokes F1–F12** on this Pi with current `field-papers` / `nz-civic` fixtures.  
10. **Stop** — no Playwright, no embeddings, no Neo4j, no Mem0, no HUD knowledge browser, no live S3.  
11. **v1.1 optional** — SQLite FTS; mentions JSONL; arXiv PDF stage; Dream NER.  
12. **Next card after knowledge works:** morning **brief productization** (M09 already pointed) — surfacing due campaigns + **usable** cite heads, not a third ingest organ.

**v1 module done when:** a Beehive visitor question either quotes a real extract with `cite:c_…` **or** honestly reports shell/empty; Dream on a watch night cites those ids; abs cites are labeled abstract-grade; RSS XML is not a paper; four stores still distinct.

---

## 18. Learning goals (lab)

After this card, Aryan should explain:

1. Why **receipts ≠ library ≠ FACTS ≠ WORLDVIEW**.  
2. Why **12k observation** can stay while **disk extract** grows.  
3. Why **empty 200 + identical hash** is a WAF shell, not two releases.  
4. Why **graphs as brain** contradict Anatomy even if HippoRAG graphs help **indexing**.  
5. Why **Dream on prefs** cannot answer Beehive.  
6. Why this card **does not replace M09**.

---

## 19. References (selected)

### Agent memory / manage / scale (2024–2026)

- Zhang et al., *A Survey on the Memory Mechanism of LLM-based Agents* (2024) — https://arxiv.org/abs/2404.13501  
- *Memory for Autonomous LLM Agents* (2026) — https://arxiv.org/abs/2603.07670  
- *Anatomy of Agentic Memory* (2026) — https://arxiv.org/abs/2602.19320  
- Shao et al., *When Stored Evidence Stops Being Usable* (2026) — https://arxiv.org/abs/2605.07313  
- *MEMTIER* (2026) — https://arxiv.org/abs/2605.03675  
- Lin et al., *Sleep-time Compute* (2025) — https://arxiv.org/abs/2504.13171  
- Chhikara et al., *Mem0* (2025) — https://arxiv.org/abs/2504.19413  
- Packer et al., *MemGPT* (2023) — https://arxiv.org/abs/2310.08560 — lineage  
- Auto-Dreamer (2026) — https://arxiv.org/html/2605.20616 — **shape only**  
- Letta sleep-time — https://docs.letta.com/guides/agents/architectures/sleeptime/

### Grounding / verbosity / graphs as index

- Cao et al., FRONT (2024) — https://arxiv.org/abs/2408.04568  
- Liu et al., *Lost in the Middle* (TACL 2024) — https://aclanthology.org/2024.tacl-1.9/  
- Gutiérrez et al., HippoRAG (NeurIPS 2024) — https://arxiv.org/abs/2405.14831  
- Anthropic, *Building Effective Agents* (2024) — https://www.anthropic.com/engineering/building-effective-agents  

### Privacy / trust (carry forward)

- *Agents That Know Too Much* (2026) — https://arxiv.org/html/2606.26627  
- MemGate / trustworthy memory search (2026) — https://arxiv.org/html/2606.06054v1  

### Internal ADA

- [`M04_MEMORY_DREAM.md`](./M04_MEMORY_DREAM.md) — dual-store, Dream, boot budgets  
- [`M07_WEB.md`](./M07_WEB.md) — fetch, cites, 12k observation  
- [`M08_WEB_ALLOWLIST_BASEPACK.md`](./M08_WEB_ALLOWLIST_BASEPACK.md) — Beehive feed vs WAF home  
- [`M09_WATCHES_RSS.md`](./M09_WATCHES_RSS.md) — watches stay; RSS ≠ document  
- [`M06_CAMPAIGNS_LONG_HORIZON.md`](./M06_CAMPAIGNS_LONG_HORIZON.md) — `last_receipt`, idle  
- [`../02_CONSTITUTION.md`](../02_CONSTITUTION.md) — §9 dual-store; §11 rings; `dream.push`  
- Code: `src/ada/web/fetch.py`, `cites.py`, `extract.py`, `feeds.py`, `watch/run.py`, `memory/facts.py`, `worldview.py`, `search.py`, `dream/delta.py`, `manage.py`, `merge.py`, `push.py`, `cortex/charter.py`

---

### Lens cheat-sheet

| Claim | Lens |
|-------|------|
| Ingest wrote cites + receipts | **METAL** |
| Dream 2026-08-12 is prefs | **METAL** |
| Identical Beehive hash = Incapsula shell | **METAL** |
| 12k stored = 12k observed | **METAL** (bug vs this card) |
| Write–manage–read | **EVIDENCE** |
| Stored evidence unusable at scale | **EVIDENCE** contradiction vs “just keep blobs” |
| Graphs fragile / verbosity ≠ veracity | **EVIDENCE** contradictions |
| SQLite FTS as rebuildable index | **FEASIBLE-on-Pi8GB** |
| Neo4j as ADA’s mind | **FANFICTION** — reject |
| Playwright to fix all NZ HTML in v1 | **Won’t-chase** as gate |
| Feed fallback for Beehive | **FEASIBLE** + M08 taste |
| `dream.push` S3 | **POLICY** pointer, not gate |
| Campaigns/watches replaced by RAG | **Reject** — M09 stands |

---

*End of M10. **Doc-only** 2026-08-14: knowledge/learning organ on top of dual-store + cites + watches. No Funnel; no soul; no implementation in this slice; no commit.*

---

## If Aryan does one thing next

**Ask the two questions on metal, with tools visible:** *“what did Beehive say about visitors?”* and *“how does that relate to the new cs.AI abs cites?”* Treat empty extracts + prefs Dream as the **baseline fail**. Then pick OPEN #1 (feed fallback vs empty-honest) before any coding PR.
