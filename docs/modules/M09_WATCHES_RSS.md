# M09 — Watches / RSS ingest + campaign wake

**Status:** living research card — **metal shipped** (2026-08-14+): `src/ada/watch/`, campaign watches, tests. Phase B harness digest / systemd timers still deferred.  
**Date:** 2026-08-14  
**Host:** `ada-pi5` (Raspberry Pi 5 Model B Rev 1.1, Debian trixie, ~8 GiB RAM)  
**Branch:** `rewrite/v1-body`  
**Depends on:** [`M07_WEB.md`](./M07_WEB.md) (fetch + cites + TTL/ETag + `web_cite_search`; RSS design hook §5.4 / §7.1), [`M08_WEB_ALLOWLIST_BASEPACK.md`](./M08_WEB_ALLOWLIST_BASEPACK.md) (layer-3 watches on pack doors; no crawl), [`M06_CAMPAIGNS_LONG_HORIZON.md`](./M06_CAMPAIGNS_LONG_HORIZON.md) (`open_loops` campaigns, `last_receipt`, `ada campaigns check`, `ada-brief.timer` pointer), [`M04_MEMORY_DREAM.md`](./M04_MEMORY_DREAM.md) (Dream manage on cite deltas; quiet hours), [`../02_CONSTITUTION.md`](../02_CONSTITUTION.md) §§8–11 & §16 (web egress; confirm ladder; heal-first quiet hours), charter **WEB CONTRACT** (`src/ada/cortex/charter.py`).  
**METAL already present:** `web_fetch` / `web_cite_get` / `web_cite_search`; `prefs.web_allowlist` + packs (`src/ada/web/packs/`); campaign schema v2 on `open_loops.yaml` (`kind`, `stages`, `next_wake_at`, `last_receipt`, `cadence`); local `ada campaigns status|check` (no LLM); optional `deploy/systemd/ada-brief.{timer,service}`; Dream timer ~03:30 NZST. **OUT:** vendor `web_search`, Playwright, Pretext HUD, automations/n8n brain, multi-agent, timer-on-whole-allowlist.

**Slice rule:** this card admits **design** of **scheduled watches** — RSS/Atom (or fixed URL lists) on **already-allowlisted hosts** → triage new item URLs → `web_fetch` → durable cites → campaign `last_receipt` → optional capped Gemini digest — waking **one campaign/watch per timer tick**, not the internet. It does **not** admit: implementation code; Funnel; crawl-all-allowlist daemon; vendor search as required; browser automation; consciousness/soul; a second fetch path; n8n as ingest brain; embeddings-day-one dedupe; LinkedIn/Seek scrape organ.

**Won’t-chase this slice:** polling every host in `prefs.web_allowlist`; “RSS product” with 500 sources; semantic-dedup pgvector on Pi day one; LLM-scoring every feed title; always-on ingest worker; Tor-as-ingest; Playwright for WAF hosts; Pretext HUD watch UI; multi-agent “newsroom”; vendor Tavily/Serper as the watch engine; deleting cites on TTL expiry.

**Name justification:** **`M09_WATCHES_RSS.md`** — not `M07c` (hands stay closed), not `M08b` (packs are doors, not clocks). **Watch** = recurring pull on a **named feed or fixed URL list** attached to a **campaign**. **RSS** is the default ingest shape (M07/M08 taste lock); fixed-URL checklist is the same organ with a thinner parser. The deliverable is **one timer → one campaign wake → bounded fetches → cites**, not a crawler.

**Taste locks (this card):**

| Lock | Decision |
|------|----------|
| Scope | **One campaign / one watch cluster per wake** — never timer-poll the whole allowlist. |
| Ingest | **RSS/Atom first**; fixed `watch_urls[]` second; vendor search **not** for watches. |
| Doors | Feed/article hosts must already be in `prefs.web_allowlist` (M08) — campaigns do not mint hosts. |
| Hands | **Same M07 gateway** (`web_fetch`, cite side effects) for chat and watch wakes. |
| Triage | **Deterministic first** (guid/URL/cite-index/TTL); optional cheap title filter later — not LLM-on-every-item v1. |
| Cortex | **Intermittent:** feed parse + triage can be **no-Gemini**; one capped harness turn for digest optional per wake. |
| Storage | Cites → `memory/cites/`; audit → `runs/`; watch cursor state → campaign fields or thin sidecar — **not** a second cite store. |
| Quiet hours | **Heal-first:** unattended feed pull + cite write OK (like Dream); **user-facing nudges** wait for brief / open. |
| Idle | Between wakes: **idle** — no immortal ingest loop (M06 lock). |

```text
  ada-brief.timer  OR  ada-watch.timer  OR  user opens HUD/CLI
           |
           v
  [pick ONE due campaign — M06 due_campaigns / watch cadence]
           |
           +--> deterministic: GET feed(s) on allowlisted host(s)
           |         parse RSS/Atom → item {url, guid, pubDate, title}
           |         triage: seen guid? cite-index URL hit? TTL fresh?
           |
           +--> gateway web_fetch (≤K new article URLs per wake)
           |         → memory/cites/ + runs/ tool_result
           |
           +--> optional: ONE M02 harness turn (same tools as chat)
           |         WORLDVIEW digest with cite-ids; upsert last_receipt
           |
           v
  idle until next_wake_at / cadence / user open

  x  not crawl-all-allowlist   x  not Funnel   x  not vendor web_search
```

---

## Operator locks (hard)

1. **No Funnel / public ingress** — watches are outbound pulls on named origins (M01).  
2. **No crawl-all-allowlist** — a timer that hits every pack host is **explicitly rejected**; falsifier F6.  
3. **Allowlist + SSRF** — feed URL and every item URL pass M07 `allowlist.py` + `ssrf.py`; redirect partners co-listed (M08 F4/F5).  
4. **One wake, one campaign** — timer dispatches **at most one** watch cluster per tick (or one campaign with ≤N feeds).  
5. **Same tools** — chat ReAct and campaign watch use **`web_fetch` / `web_cite_get` / `web_cite_search`** via gateway — no private ingest runtime.  
6. **Cites = `memory/cites/`** — watch ingest does not invent a parallel cache CRM.  
7. **Receipts = `runs/`** — every fetch (and feed GET) appends audit lines; campaign `last_receipt` points here (M06).  
8. **Gemini primary, intermittent** — feed parse/triage is deterministic Python; cortex optional for digest only.  
9. **Heal-first quiet hours** — **23:00–05:30 NZST** unattended ingest OK if not user-facing; no “40 new jobs” ping at 02:00 (constitution §10 / M06).  
10. **No consciousness / soul** — a watch is a clocked read, not “she’s watching the world.”  
11. **Dream must not auto-add hosts or watches** — `web_allowlist` and watch URLs stay off Dream auto-merge (M08 F11).

---

## 1. Question / goal / slice admission

**Research questions (operator).**

1. How do serious agents (2024–2026) run **RSS/Atom + allowlisted fetch** pipelines for recurring intel — and what are honest **token/cost** patterns?  
2. **Watch config shape** on a Pi: separate `watches.yaml` vs `feed_url` on campaign stages vs `watches[]` on `open_loops` — what is the **minimal schema**?  
3. **Triage:** which feed items deserve a full `web_fetch` (guid dedupe, URL normalization, cite-index hit, TTL)?  
4. **Quiet hours / heal-first:** what may run unattended vs what waits for morning brief / user open?  
5. How does this **reuse M06 campaigns + M07 gateway** so chat and watch share one organ?  
6. **Falsifiers** that distinguish “one campaign watch” from “poll the whole allowlist.”

**Goal (M09 design).**

1. Lock a **≤5-concept mental model** (watch / cursor / triage / wake / cite).  
2. Survey SOTA with **FANFICTION / EVIDENCE / FEASIBLE-on-Pi8GB** tags (**≥6 citations**, 2024–2026).  
3. Options matrix: campaign fields vs sidecar file vs n8n vs crawl-all vs LLM-every-item.  
4. Recommend **schema**, **wake path**, **CLI/timer hook**, **cite storage pointer**, **token budget**.  
5. Falsifiers, OPEN questions for Aryan, ordered implement list (**design only**).

**Admission boundary**

| IN this slice (design now → code later) | OUT |
|----------------------------------------|-----|
| RSS/Atom + fixed URL watches on allowlisted hosts | Vendor `web_search` as watch engine |
| Deterministic triage + bounded `web_fetch` per wake | LLM score every feed item v1 |
| Campaign-attached watch config + cursor state | Always-on ingest daemon |
| `ada watch run` / extend `ada campaigns wake` + timer pointer | Pretext HUD watch UI |
| One campaign per timer tick | Timer polling all `prefs.web_allowlist` |
| Reuse M07 fetch/cites + M06 `last_receipt` | Second HTTP stack / Playwright |
| Quiet-hours heal-first policy sketch | Multi-agent newsroom |
| Dream consuming **new cite heads** (pointer) | Dream auto-creating watches |

---

## 2. Simple mental model for Aryan (≤5 concepts)

| # | Concept | Meaning |
|---|---------|---------|
| **1. Watch** | A **recurring URL** (usually RSS/Atom) on a door already in the pack — e.g. arXiv cs.AI, Beehive `/rss.xml`. |
| **2. Cursor** | **What we already saw** — last fetch time, last `guid`s or item ids — so we don’t re-fetch the same story. |
| **3. Triage** | **Which items get a full read** — skip if guid seen, URL already in `memory/cites/`, or cite TTL fresh. |
| **4. Wake** | **One campaign tick** — timer or you open ADA → pull feeds → fetch ≤K new pages → write cites → optional digest → **idle**. |
| **5. Cite** | The **shelf entry** (M07) — URL + time + excerpt; WORLDVIEW and brief cite **this**, not the feed XML. |

**One sentence:** *A watch is an alarm on a feed; triage picks unread doors; fetch writes cites; the campaign receipt proves she did the homework.*

**Reject for v1 vocabulary:** “crawler,” “she’s monitoring the internet,” “poll all allowlisted hosts,” “RSS SaaS,” “newsroom swarm,” “embedding dedupe day one.”

---

## 3. Lens tags

| Tag | Meaning here |
|-----|----------------|
| **FANFICTION** | Omniscient live web; 500-source watch tower; LLM reads every headline; always-on ingest consciousness |
| **EVIDENCE** | RSS guid+pubDate pipelines; sleep-time precompute; Anthropic workflows; Progent tool policy; Claude fetch caps; OpenClaw/newsroom cost patterns (map, don’t copy) |
| **FEASIBLE-on-Pi8GB** | `feedparser` + httpx GET; JSONL guid cursor on HDD; ≤5–10 fetches/wake; no pgvector day one |
| **POLICY** | No Funnel; one campaign per wake; heal-first quiet hours; same gateway; no crawl-all |
| **METAL** | M07 fetch+cites shipped; M08 packs seeded; M06 campaigns + `ada campaigns check`; WEB CONTRACT names RSS watches |

---

## 4. SOTA landscape (2024–2026) — ≥6 citations

Every row tagged. Citations are **lineage for design**, not training homework.

### 4.1 Why RSS/Atom for agent watches (not scrape-all)

| Source | Claim | Tag | ADA takeaway |
|--------|-------|-----|--------------|
| **RSS spec practice** — [W3C RSS 2.0](https://www.rssboard.org/rss-specification); [Atom RFC 4287](https://www.rfc-editor.org/rfc/rfc4287) | Items carry **`guid` / `id`**, **`link`**, **`pubDate` / `updated`** — stable dedupe and freshness without HTML scrape. | **EVIDENCE** (systems) | Triage layer 0: **guid + URL**, not LLM. |
| **Why RSS for AI agents (2026 practice)** — [RSS.app blog](https://rss.app/blog/why-rss-is-the-best-format-for-ai-agents-in-2026-qpvXyf) | Feeds give **structured deltas**; guid persists across syndication; wide official coverage; no per-site scrape selectors. | **EVIDENCE** (practice) | Matches M07/M08 “feeds before search vendor.” Vendor feed generators are **optional**, not the organ. |
| **arXiv RSS/API docs** — [RSS help](https://info.arxiv.org/help/rss.html); [API manual](https://info.arxiv.org/help/api/user-manual.html) | Category feeds on **`rss.arxiv.org`** / Atom API on **`export.arxiv.org`** — separate hosts (M08 F4). | **EVIDENCE** + **METAL** | Watch URLs must match **exact-host** pack rows. |
| **M07 §4.4b** | Recurring discovery = **RSS + allowlisted fetch**, not scrape farms. | **METAL** / **POLICY** | This card **implements** that hook. |
| **Firecrawl / SPA gap (2025–26)** | Fetch fails on JS shells; feeds often survive layout changes. | **EVIDENCE** | Prefer **feed → article URL** over homepage HTML watch (Beehive: feed OK, home WAF — M08 §7.1). |

**FANFICTION:** “poll every allowlisted host’s homepage on a timer.”  
**FEASIBLE-on-Pi8GB:** 3–8 feeds, not 500.

### 4.2 Pipelines: ingest → dedupe → triage → fetch → digest

| Source | Claim | Tag | ADA takeaway |
|--------|-------|-----|--------------|
| **OpenClaw newsroom (2025–26)** — [GitHub](https://github.com/jacob-bd/openclaw-newsroom); [Starlog writeup](https://starlog.is/articles/automation/jacob-bd-openclaw-newsroom) | Multi-source scan → **SQLite dedupe** → cheap **Gemini Flash Lite** curation → full text only for top stories; **~$5/mo** with tiered LLM failover. | **EVIDENCE** (practice) | **Map, don’t copy:** ADA uses **deterministic triage first**, one cortex turn for digest — not 7 LLM calls/day on titles. Reject OpenClaw-as-brain (M06). |
| **Telo Watch Tower (2026)** — [GitHub](https://github.com/Knight-Panther/Telo-watch-tower) | 7-stage pipeline: date filter → URL dedup → **embedding** semantic dedup → LLM score → translate → publish. | **EVIDENCE** | Stages 1–2 are **FEASIBLE** on Pi; embedding pgvector stage is **won’t-chase v1** (Tier B). |
| **ai-news-agent / LangGraph (2025–26)** — [GitHub](https://github.com/wyh0626/ai-news-agent) | RSS + ArXiv + HN; **title dedup + pgvector**; caps `MAX_ITEMS_PER_RUN`; GitHub Actions cron. | **EVIDENCE** | **Reject LangGraph organ** (M02); **borrow caps** (`≤K items/wake`, `≤K fetches/wake`). |
| **Anthropic — Building Effective Agents (2024)** — [eng blog](https://www.anthropic.com/engineering/building-effective-agents) | **Workflows** (code + gates) before unbounded agents; human checkpoints. | **EVIDENCE** | Watch wake = **workflow**: parse → triage → fetch → optional one LLM digest — not ReAct forever. |
| **Sleep-time Compute (Lin et al., 2025)** — [arXiv:2504.13171](https://arxiv.org/abs/2504.13171) | Offline precompute when future queries predictable. | **EVIDENCE** | Overnight watch + Dream digest **amortizes** morning chat tokens (M04). |
| **Usable-scale memory (2026)** — [html](https://arxiv.org/html/2605.07313) | Stored evidence dies if irretrievable or unbounded. | **EVIDENCE** | Cite-index + `web_cite_search` before refetch; cap items per wake. |

**Honest token/cost pattern (locked sketch for ADA):**

| Stage | Cortex? | Cost driver |
|-------|---------|-------------|
| GET feed XML | No | Bytes; 1–3 HTTP GETs/wake |
| Parse + guid/URL dedupe | No | CPU |
| `web_cite_search` / index grep for URL | No | Local |
| `web_fetch` per new item | No* | Network + extract; observation capped (*Gemini only if harness digest runs) |
| One digest harness turn | Yes | **One** capped turn/wake — cite-ids in WORLDVIEW |

**FANFICTION:** LLM reads every `<title>` in the feed.  
**FEASIBLE:** 0 Gemini tokens for ingest-only wakes; add digest when Aryan wants prose.

### 4.3 Dedupe / triage strategies (what to fetch)

| Strategy | Mechanism | Tag | ADA v1 |
|----------|-----------|-----|--------|
| **Feed guid/id** | Store seen guids per watch (7–30 day window) | **EVIDENCE** | **Yes** — primary cursor |
| **Canonical URL** | Normalize URL (strip utm, http→https) before cite lookup | **EVIDENCE** (practice) | **Yes** |
| **Cite index hit** | URL in `memory/cites/index.jsonl` + TTL fresh → skip fetch | **EVIDENCE** + **METAL** | **Yes** — library-first |
| **pubDate cutoff** | Ignore items older than watch `max_age_hours` | **EVIDENCE** | **Yes** — default 48–168h |
| **Title fuzzy / embedding** | 80–85% similarity collapse | **EVIDENCE** (Watch Tower, ai-news-agent) | **Won’t-chase v1** |
| **LLM relevance score** | Cheap model on title/snippet | **EVIDENCE** (newsroom) | **Optional v1.1** — keyword/`must_match` first |

**Triage decision table (design):**

| Condition | Action |
|-----------|--------|
| `guid` (or stable id) in watch cursor | **Skip** — no fetch |
| URL normalized match in cite index + TTL fresh | **Skip fetch** — optionally refresh cursor |
| URL in cite index + TTL stale | **Conditional GET** via `web_fetch` (ETag path — M07) |
| New URL, allowlisted, under per-wake cap | **`web_fetch`** → new cite |
| URL host not allowlisted | **Deny** — do not confirm from unattended timer |
| Over per-wake cap | **Queue** remainder to next wake — don’t burst |

### 4.4 Scheduling: one wake vs crawl-all vs multi-agent

| Pattern | What it does | Tag | ADA verdict |
|---------|--------------|-----|-------------|
| **Campaign timer → one watch** | systemd oneshot → `ada watch run --campaign id` | **FEASIBLE-on-Pi8GB** / **METAL** | **Recommend** |
| **Poll entire allowlist** | Every host every N minutes | **FANFICTION** / ops smell | **Reject** — F6 |
| **Cron per feed (20 timers)** | One systemd unit per RSS | **EVIDENCE** (common) | **Defer** — use **one dispatcher** + campaign `next_wake_at` |
| **Always-on worker** | Immortal loop polling feeds | **FANFICTION** pull | **Reject** (M06) |
| **n8n / Zapier RSS nodes** | External graph | **EVIDENCE** exists | **Reject as organ** — split brain |
| **Multi-agent newsroom** | Collector + curator + publisher agents | **EVIDENCE** (repos above) | **Reject default** — one harness |

**M06 / M08 alignment:** watches are **layer 3** (URLs on open doors). M09 adds the **clock** and **cursor**, not new doors.

### 4.5 Policy: quiet hours, robots, unattended fetch

| Source | Claim | Tag | ADA takeaway |
|--------|-------|-----|--------------|
| **M06 operator lock §4** | **Heal-first quiet hours** — overnight heal/retry OK; user-facing nudges wait. | **POLICY** / **METAL** | Feed pull + cite write = **heal** (like Dream ~03:30). Brief surfaces results at **05:30**. |
| **M07 §4.5 robots** | Honor robots for **campaign/timer** fetches; identify as `ADA-User`. | **EVIDENCE** / **POLICY** | Unattended watch = timer class — **robots honored**. |
| **Progent (2025)** — [arXiv:2504.11703](https://arxiv.org/abs/2504.11703) | Tool policy outside model; least privilege. | **EVIDENCE** | Unattended wake **cannot** `memory_facts_append` or expand allowlist without confirm. |
| **Consent Integrity (2026)** — [arXiv:2606.02668](https://arxiv.org/abs/2606.02668) | Confirm binds real args. | **EVIDENCE** | Timer ingest **never** confirms new hosts — skip or mark campaign `blocked`. |
| **RNZ RSS ToS (M08)** | Personal use; don’t republish. | **POLICY** | Cites for **personal library**; no auto-post to world. |

**Quiet hours matrix (locked sketch):**

| Action | 23:00–05:30 NZST | Outside quiet |
|--------|------------------|---------------|
| GET allowlisted feed | **OK** (heal) | OK |
| `web_fetch` new items (≤K) | **OK** (heal) | OK |
| Write cites / runs | **OK** | OK |
| Gemini digest harness turn | **OK** if capped (heal) | OK |
| HUD push / proactive “N new items” | **No** | Brief / on-open |
| Expand `web_allowlist` | **No** | Confirm-once only |

### 4.6 Same gateway for chat and watch (M07 §7.3)

| | Chat ReAct | Watch wake |
|--|------------|------------|
| Trigger | User turn | Timer / `ada watch run` / user opens campaign |
| Feed GET | Rare (user asks) | **Deterministic pre-step** (may be CLI code, not a named tool v1) |
| Article read | `web_fetch` / `web_cite_get` | **Same** |
| Library search | `web_cite_search` | **Same** (triage before network) |
| Persist | `runs/` + cites | **Same** + campaign `last_receipt` |
| LLM | Multi-step ReAct | **0–1** digest turns recommended |

**Design choice:** RSS parse may live in `ada.web.feeds` (deterministic module) invoked by CLI/harness **before** tools — analogous to M07 “RSS pull may be CLI/campaign code before a named tool.” Optional later: `web_feed_pull` ToolSpec if the model must choose feeds in chat.

---

## 5. Map to ADA METAL

| Piece | Role for M09 | Pointer |
|-------|----------------|---------|
| `web_fetch` + cites | Article ingest after triage | `src/ada/web/fetch.py`, `cites.py` |
| Allowlist + SSRF | Feed + item URLs | `src/ada/web/allowlist.py`, `ssrf.py` |
| Packs | Doors for watch URLs | `src/ada/web/packs/catalog.yaml` |
| Campaigns | STATUS, stages, `last_receipt`, `next_wake_at` | `src/ada/memory/open_loops.py` |
| `ada campaigns check` | Local due list (no LLM) | CLI; `ada-brief.timer` |
| WEB CONTRACT | RSS watches named | `src/ada/cortex/charter.py` |
| Dream | Digest **new cite heads** overnight | M04 — don’t re-fetch HTML |
| **`watches` organ** | **Not coded** — this card | — |

**Sequencing (locked):** M07 hands → M08 doors → **M09 clocks** → later brief/HUD productization.

---

## 6. Options matrix

| Option | How it works | Pros | Cons | Lens | Verdict |
|--------|--------------|------|------|------|---------|
| **A. Campaign `watches[]` on `open_loops`** | Extend campaign record with feeds + cursor | One file; M06 spine; CLI already there | YAML clutter if many feeds | **FEASIBLE** + **METAL** | **Recommend v1** |
| **B. Sidecar `memory/watches.yaml`** | `watch_id → campaign_id, feed_url, cursor` | Cleaner separation | Second file + sync | **FEASIBLE** | **Optional** if A hurts |
| **C. Stage-only `feed_url`** | Single feed on active stage | Minimal | Hard multi-feed; cursor awkward | **METAL**-friendly | **OK for one-feed campaigns** |
| **D. Poll all allowlist hosts** | Timer hits every pack host | “Complete coverage” | SSRF/exfil theater; token/firehose | **FANFICTION** | **Reject** |
| **E. n8n RSS → webhook** | External automation | Pretty | Split brain; STATUS not in ADA | **EVIDENCE** exists | **Reject organ** |
| **F. LLM triage every item** | Flash on each title | “Smart filter” | Cost; drift | **EVIDENCE** newsroom | **Defer v1.1** |
| **G. Embedding semantic dedup** | pgvector on Pi | Catches duplicate stories | RAM/ops; Tier B | **EVIDENCE** Watch Tower | **Won’t-chase v1** |
| **H. Vendor search watch** | Serper every wake | Finds “everything” | Not RSS; $$; snippets≠cites | **EVIDENCE** | **Out of scope** |

**Harder-correct vs shortcut:**  
- Shortcut = cron-scrape 48 hosts + Gemini summarizer.  
- Harder-correct = **campaign-scoped feeds + guid cursor + cite-index triage + bounded `web_fetch` + one receipt.**

---

## 7. Recommended ADA design

### 7.1 Watch schema (minimal — extend campaign)

Prefer **`watches[]` on campaign items** in `open_loops.yaml` (schema_version bump when coded). Plain TODOs omit the field.

```yaml
# design sketch — not implemented
id: c_agents_lit
kind: campaign
title: "Agents literature watch"
status: active
current_stage: ingest
cadence: daily                    # M06 existing
next_wake_at: "2026-08-15T05:30:00+12:00"
stages:
  - id: ingest
    state: active
  - id: digest
    state: pending
watches:
  - id: arxiv_cs_ai
    kind: rss                       # rss | atom | fixed_urls
    url: "https://rss.arxiv.org/rss/cs.AI"
    pack: lab.papers                # audit only — host must be allowlisted
    max_items_per_wake: 5           # triage survivors, not fetch burst
    max_age_hours: 168              # ignore ancient pubDate on first run
    cursor:
      last_checked_at: "2026-08-14T06:00:00Z"
      seen_guids:                   # ring buffer cap ~500–2000 ids
        - "oai:arXiv.org:2608:12345"
      etag: "W/\"abc\""             # optional conditional GET on feed itself
      last_error: null
last_receipt: "runs/2026-08-14/watch_sess.jsonl#evt_01"
last_progress_at: "2026-08-14T06:05:00Z"
```

**Fixed URL watch (same organ):**

```yaml
  - id: treasury_releases
    kind: fixed_urls
    urls:
      - "https://www.stats.govt.nz/information-releases/..."
    refresh_hours: 24               # refetch these specific pages on cadence
```

**Field glossary (minimal):**

| Field | Required | Purpose |
|-------|----------|---------|
| `watches[].id` | yes | Stable id within campaign |
| `watches[].kind` | yes | `rss` \| `atom` \| `fixed_urls` |
| `watches[].url` / `urls` | yes | Feed or checklist |
| `watches[].max_items_per_wake` | yes | **Cap** — default 5 |
| `watches[].cursor` | auto | Operator doesn’t hand-edit guids |
| `watches[].pack` | no | Traceability to M08 pack id |

**Do not add yet:** keyword filters, embedding flags, per-watch systemd timers, LLM `relevance_prompt` (OPEN v1.1).

### 7.2 Triage module (deterministic — design)

```text
pull_feed(watch) → list[FeedItem{guid, url, title, published_at}]
for item in newest_first(items):
    if len(selected) >= max_items_per_wake: break
    if item.guid in cursor.seen_guids: continue
    if item.published_at < now - max_age_hours: continue
    url = normalize_url(item.url)
    if not allowlist_allows(url): log deny; continue
    if cite_index_fresh(url): cursor.mark_seen; continue
    selected.append(item)
for item in selected:
    web_fetch(url)  → cite_id, receipt
    cursor.mark_seen(item.guid)
upsert campaign cursor + last_receipt
```

**Feed GET:** httpx GET with allowlist/SSRF; optional `If-None-Match` on feed URL (separate from article TTL). Parse with **`feedparser`** (Pi-feasible; stdlib xml.etree fallback for strict Atom if needed).

**Cite lookup:** grep `memory/cites/index.jsonl` by URL + honor per-host TTL from allowlist entry (`ttl_seconds` — M08 vibes: `feed` 3600, news `interactive` 900).

### 7.3 Wake path (one campaign per tick)

```text
1. Entry: ada watch run [--campaign ID]  OR  timer dispatcher
2. If no ID: due_campaigns(limit=1) preferring campaigns with watches[] + due cadence
3. proactivity_suppressed()? → exit 0 quiet (same as ada campaigns check)
4. Phase A — deterministic ingest (no Gemini):
       for each watch on campaign: pull → triage → web_fetch new URLs
       append runs/ session watch_sess.jsonl with structured events
5. Phase B — optional harness (Agent, max_steps low):
       boot: campaign head + new cite ids only
       charter: WEB CONTRACT + "one digest cluster then stop"
       tools: web_cite_get, memory_worldview_write, memory_open_loops_upsert
6. Upsert: last_receipt, last_progress_at, next_wake_at (+cadence), stage advance
7. Exit — idle
```

**Timer hook (design pointer — not acceptance gate):**

| Unit | Role |
|------|------|
| `deploy/systemd/ada-brief.timer` | Existing ~05:30 — may call **`ada watch run`** then **`ada campaigns check`** |
| `deploy/systemd/ada-watch.timer` | **Optional** separate pointer if brief stays LLM-free |
| `ada-dream.timer` ~03:30 | Dream may **digest new cite heads** — does **not** replace watch pull |

Recommend **one dispatcher script** `ada watch run` that respects quiet for **nudges** but allows **Phase A ingest** during heal window (policy flag `--ingest-only` for 03:30 slot vs `--digest` at 05:30).

### 7.4 CLI surface (design)

| Command | Purpose |
|---------|---------|
| `ada watch list` | Campaigns with non-empty `watches[]` |
| `ada watch run [--campaign ID] [--ingest-only] [--dry-run]` | Execute one wake |
| `ada watch status [--campaign ID]` | Cursors, last_error, last_receipt |
| `ada campaigns status` | **Existing** — shows campaign + stages |
| `ada campaigns check` | **Existing** — due list for brief |

**Dry-run:** parse + triage printout; **no** `web_fetch` — falsifier testing.

### 7.5 Cite storage + receipts (pointer — no second store)

| Artifact | Path | Notes |
|----------|------|-------|
| Cite bodies | `/mnt/ada-data/memory/cites/<cite_id>.md` | M07 |
| Cite index | `/mnt/ada-data/memory/cites/index.jsonl` | URL grep for triage |
| Raw HTML (optional) | `/mnt/ada-data/scratch/web/<hash>.html` | Disposable |
| Watch session audit | `/mnt/ada-data/runs/<utc-date>/watch_<campaign>_<ts>.jsonl` | `feed_pulled`, `item_skipped`, `tool_result` |
| Campaign pointer | `open_loops.last_receipt` | M06 — must reference runs line |

**WORLDVIEW / Dream:** digest cites **`cite:c_…`** ids — M04 manage pass may fold overnight watch cites into morning brief context **without** re-reading HTML.

### 7.6 Token / egress budget (recommended defaults)

| Knob | Default | Rationale |
|------|---------|-----------|
| Campaigns per timer tick | **1** | Core lock |
| Watches per campaign | **≤3** day-one | M08 §7.4 examples |
| `max_items_per_wake` | **5** | ai-news-agent caps class |
| `web_fetch` parallel | **1** (serial) | Pi politeness; arXiv ToS ~3s |
| Harness `max_steps` (digest) | **6–10** | One cluster |
| Gemini digest | **0–1 turns/wake** | Ingest-only wakes = **zero** cortex |
| Feed XML max bytes | **2 MiB** | M07 download cap class |

### 7.7 Egress / trust rings

| Ring | M09 |
|------|-----|
| Tailscale control | Unchanged; **no Funnel** |
| Gemini cortex | **Optional** digest only |
| **Web egress** | Feed GET + article GET on allowlisted hosts |
| Local cites / runs | **Yes** — primary outputs |
| Backup | No |

---

## 8. Won’t-chase (this slice)

| Topic | Why |
|-------|-----|
| Poll-all-allowlist timer | Not a watch — it’s a crawler (F6) |
| Vendor `web_search` as watch | Snippets ≠ cites; wrong organ |
| Playwright for WAF feeds | M08 confirm-later hosts stay out of unattended |
| pgvector / embedding dedup v1 | Tier B; guid+URL enough for personal scale |
| LLM on every feed item | Cost + injection surface |
| n8n / Zapier ingest brain | M06 split-brain reject |
| Multi-agent newsroom | One harness |
| Pretext HUD watch dashboard | Later consumer |
| Always-on ingest service | M06 idle lock |
| Dream auto-creating watches | Operator + campaign upsert only |
| Cite store other than `memory/cites/` | M07 lock |
| Tor egress for feeds | M07 §15 fork |

---

## 9. Learning goals (lab)

After this card, Aryan should explain:

1. Why **RSS guid + cite-index** triage beats LLM-on-every-title for a Pi lab.  
2. Why **one campaign per wake** beats polling the whole pack.  
3. How **heal-first quiet hours** allow 03:30 ingest but not 02:00 HUD spam.  
4. Why watch ingest **reuses `web_fetch`** instead of a second HTTP stack.  
5. How **`last_receipt`** on a campaign differs from “I saw headlines in XML.”  
6. What **F6** falsifies (crawl-all-allowlist).

**Harder-correct:** campaign-scoped watches + deterministic triage + bounded fetch + runs receipt.  
**Shortcut rejected:** allowlist-wide cron, vendor search watch, embedding tower on day one.

---

## 10. Falsifiers

| # | Falsifier | Pass look |
|---|-----------|-----------|
| F1 | **Fake-read headline** | Cannot claim article body without `web_fetch` / `web_cite_get` receipt |
| F2 | **Duplicate fetch** | Same guid/URL within TTL → skip; second wake doesn’t re-download |
| F3 | **Allowlist** | Feed or item on non-allowlisted host → deny/skip; unattended never confirms new host |
| F4 | **SSRF** | Item link to `127.0.0.1` / metadata → deny |
| F5 | **Cap burst** | 50-item feed → ≤`max_items_per_wake` fetches; rest deferred |
| F6 | **Not crawl-all** | Timer code path never iterates `prefs.web_allowlist` as fetch targets |
| F7 | **One campaign** | Single timer tick processes **one** campaign id (log proves) |
| F8 | **Quiet nudge** | No user-facing push 23:00–05:30; ingest may still run with `--ingest-only` |
| F9 | **Receipt truth** | `last_receipt` points to `runs/…watch…jsonl` with fetch events |
| F10 | **WORLDVIEW** | Digest uses `cite:c_…` ids — no feed XML pasted |
| F11 | **Chat parity** | Manual `web_fetch` in chat and watch wake share gateway observations |
| F12 | **Dream safety** | Dream does not append hosts or watches without operator confirm |
| F13 | **Dry-run** | `--dry-run` lists would-fetch URLs without network |

Won’t-chase as gates: 500-source soak, embedding dedup bakeoff, 72h unsupervised publish.

---

## 11. OPEN questions for Aryan (taste forks)

1. **First watch:** arXiv **cs.AI** vs Beehive RSS vs RNZ **political.xml**? (Recommend **cs.AI** — lowest WAF risk; proves pack satellites.)  
2. **Digest phase:** **ingest-only** overnight + brief digest at 05:30 **vs** single wake with harness? (Recommend **split**: 03:30 ingest-only heal, 05:30 optional digest.)  
3. **Schema home:** campaign `watches[]` **vs** sidecar `memory/watches.yaml`? (Recommend **campaign fields first**.)  
4. **Keyword filter v1.1:** stage `must_include: ["agent", "robot"]` on titles **vs** pure guid dedupe? (Recommend **dedupe only** until noise hurts.)  
5. **Timer ownership:** extend **`ada-brief.timer`** **vs** new **`ada-watch.timer`**? (Recommend **one dispatcher** command; timer unit is ops preference.)  
6. **RNZ ToS:** keep RNZ watch **personal** — OK to cite in WORLDVIEW for self, never republish? (Recommend **yes** — M08 stance.)  
7. **GeoNet JSON watch:** treat **`api.geonet.org.nz/quake?MMI=4`** as `fixed_urls`/API poll **vs** RSS-only purity? (Recommend **allow JSON poll** as `kind: fixed_urls` — same triage organ.)

Non-questions (locked): no Funnel; no crawl-all; no vendor search required; no Playwright unattended; no second cite root; Gemini primary; same gateway; idle between wakes.

---

## 12. Ordered “research done → implement next” (design only)

1. **Schema bump** — `watches[]` + `cursor` on campaign in `open_loops.py` validation (optional sidecar if YAML noisy).  
2. **`ada.web.feeds`** — allowlisted GET + feedparser + normalize FeedItem (no Gemini).  
3. **Triage helper** — guid ring buffer + cite-index URL freshness (`cites.py` lookup by URL).  
4. **`ada watch run`** — Phase A ingest; `--dry-run`; structured `runs/` JSONL.  
5. **Wire `web_fetch`** — reuse gateway from CLI (same caps, SSRF, cite write).  
6. **Campaign upsert** — `last_receipt`, cursor persist, `next_wake_at` advance on cadence.  
7. **Phase B harness hook** — optional digest turn; `max_steps` low; WORLDVIEW cite ids.  
8. **Timer pointer** — document `ada-brief.service` → `ada watch run --ingest-only` then `ada campaigns check` (or dedicated unit).  
9. **Smokes F1–F13** on Pi with **one** arXiv watch campaign.  
10. **Stop** — no poll-all, no embeddings, no vendor search, no HUD, no n8n.  
11. **v1.1 optional** — title keyword filter; cheap LLM triage; `web_feed_pull` ToolSpec for chat-driven pulls.  
12. **Next card after watches work:** morning **brief productization** (HUD/CLI surfacing due campaigns + new cite heads) — not a duplicate ingest organ.

**v1 module done when:** one campaign, one feed, deterministic triage, bounded fetch, cites on disk, runs receipt, F6 passes, quiet-hours behavior documented on metal.

---

## 13. References (selected)

### RSS / ingest practice
- RSS 2.0 spec — https://www.rssboard.org/rss-specification  
- Atom RFC 4287 — https://www.rfc-editor.org/rfc/rfc4287  
- arXiv RSS — https://info.arxiv.org/help/rss.html  
- RSS for AI agents (2026 practice) — https://rss.app/blog/why-rss-is-the-best-format-for-ai-agents-in-2026-qpvXyf  
- OpenClaw newsroom (cost/tier pattern — map only) — https://github.com/jacob-bd/openclaw-newsroom  
- Telo Watch Tower (staged pipeline — map only) — https://github.com/Knight-Panther/Telo-watch-tower  
- ai-news-agent (caps/dedup — map only) — https://github.com/wyh0626/ai-news-agent  

### Agents / memory / policy
- Anthropic, *Building Effective Agents* (2024) — https://www.anthropic.com/engineering/building-effective-agents  
- Lin et al., *Sleep-time Compute* (2025) — https://arxiv.org/abs/2504.13171  
- *When Stored Evidence Stops Being Usable* (2026) — https://arxiv.org/html/2605.07313  
- Shi et al., Progent (2025) — https://arxiv.org/abs/2504.11703  
- Consent Integrity (2026) — https://arxiv.org/abs/2606.02668  
- Mikhail Shilkov, Claude fetch/search split (2025) — https://mikhail.io/2025/10/claude-code-web-tools/  

### Internal ADA
- [`M07_WEB.md`](./M07_WEB.md) — fetch, cites, RSS hook, campaign same-tools  
- [`M08_WEB_ALLOWLIST_BASEPACK.md`](./M08_WEB_ALLOWLIST_BASEPACK.md) — layer 3 watches, first feed examples  
- [`M06_CAMPAIGNS_LONG_HORIZON.md`](./M06_CAMPAIGNS_LONG_HORIZON.md) — wake, idle, `last_receipt`, brief timer  
- [`M04_MEMORY_DREAM.md`](./M04_MEMORY_DREAM.md) — quiet hours, Dream deltas  
- Code: `src/ada/web/`, `src/ada/memory/open_loops.py`, `src/ada/cortex/charter.py`, `deploy/systemd/ada-brief.*`  

---

### Lens cheat-sheet

| Claim | Lens |
|-------|------|
| RSS guid + pubDate for dedupe | **EVIDENCE** |
| Campaign-scoped watch, one wake | **FEASIBLE-on-Pi8GB** + **POLICY** |
| Poll all allowlist hosts | **FANFICTION** — reject |
| Same `web_fetch` for chat and watch | **METAL** + M07 |
| 03:30 ingest during quiet hours | **POLICY** heal-first |
| pgvector semantic dedup day one | **Won’t-chase** |
| OpenClaw newsroom as ADA brain | **Reject** — map cost pattern only |
| Cites in `memory/cites/` only | **METAL** lock |

---

*End of M09. **Doc-only** 2026-08-14: watches/RSS ingest + campaign wake design on top of M07+M08+M06. No Funnel; no crawl-all-allowlist; no code in this slice.*

---

## If Aryan does one thing next

**Pick one feed + one campaign** — e.g. `c_agents_lit` watching `https://rss.arxiv.org/rss/cs.AI` with `max_items_per_wake: 5`. Confirm **`rss.arxiv.org`** is in the pack. Run a **paper design walkthrough**: timer → triage → fetch → cite → `last_receipt` — before asking for code.

### Operator quickstart (Phase A — after code lands)

1. **Seed doors** (once): `ada web pack seed lab.papers` — confirms `rss.arxiv.org` + `arxiv.org` on allowlist.
2. **Create campaign** — append to `memory/facts/open_loops.yaml` or upsert via harness:

```yaml
- id: c_agents_lit          # or omit — upsert assigns id
  kind: campaign
  title: "Agents literature watch"
  status: active
  cadence: daily
  next_wake_at: "2026-08-15T05:30:00+12:00"
  current_stage: ingest
  stages:
    - {id: ingest, state: active}
  watches:
    - id: arxiv_cs_ai
      kind: rss
      url: "https://rss.arxiv.org/rss/cs.AI"
      pack: lab.papers
      max_items_per_wake: 5
      max_age_hours: 168
```

3. **Dry-run triage** (no article fetch): `ada watch run --campaign <id> --dry-run`
4. **Live ingest** (writes cites + `runs/watch_*.jsonl`): `ada watch run --campaign <id> --ingest-only`
5. **Status**: `ada watch status --campaign <id>` — cursors, `last_receipt`, `seen_guids` count.
6. **Timer** (optional): see `deploy/systemd/ada-brief.service` comment — `ada watch run --ingest-only` before `ada campaigns check`, or a separate `ada-watch.timer`.
