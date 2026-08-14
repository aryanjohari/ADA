# M08 — Web allowlist base pack (source library, not a second crawler)

**Status:** living research card — **METAL** (2026-08-14): packs instantiable via `ada web allowlist packs|seed`; day-one rooms seeded on this host into `prefs.web_allowlist` (exact hosts, operator CLI — not Dream). Hands remain M07. This card curates **which doors she may walk through**, and the policy so the pack stays small.  
**Date:** 2026-08-14  
**Host:** `ada-pi5` (Raspberry Pi 5 Model B Rev 1.1, Debian trixie, ~8 GiB RAM)  
**Branch:** `rewrite/v1-body`  
**Depends on:** [`M07_WEB.md`](./M07_WEB.md) (fetch + cites + allowlist/SSRF + paste-this-turn + RSS hook), [`../02_CONSTITUTION.md`](../02_CONSTITUTION.md) §§8.1–8.3 & §11 (web egress ring; confirm-once new host; no Funnel), [`../00_ASSISTANT_RESEARCH.md`](../00_ASSISTANT_RESEARCH.md) §§1–5 & §8, [`../01_BODY.md`](../01_BODY.md) (FACTS prefs; Dream whitelist), [`M06_CAMPAIGNS_LONG_HORIZON.md`](./M06_CAMPAIGNS_LONG_HORIZON.md) (watches idle between wakes).  
**METAL already present:** `web_fetch` / `web_cite_get` / `web_cite_search`; `src/ada/web/allowlist.py` (**exact host** match on `prefs.web_allowlist`); `src/ada/web/packs/` (catalog YAML + seed); `src/ada/web/ssrf.py` (private/link-local/CGNAT/metadata deny; redirect revalidate); constitution v1.3 allowlisted GET. **Current FACTS seed (2026-08-14):** day-one packs (`lab.*` + `nz.law` + `nz.economy` + `nz.place` + `nz.civic` + `nz.data` + `nz.news`) merged into `prefs.web_allowlist` via operator CLI; exact hosts only; §7.2 confirm-later not seeded. Tailscale-only control plane. Gemini primary cortex. No Funnel.

**Slice rule:** this card admits **research + curation of a finite source library** — named host packs, won’t-allow, confirm-once growth, how watches sit on those hosts. It does **not** admit: a second crawler; vendor `web_search` as required; Playwright; Funnel; `*` allow; localhost allow; LinkedIn/Seek scrape; Tor-as-Google; consciousness/soul; implementation dumps; changing M07’s fetch organ.

**Won’t-chase this slice:** always-on crawl daemon; “allow the whole `.govt.nz` zone”; URL-level allowlists of 500 paths; scrape-as-a-service; social login walls; paywall theater; building a private Google; n8n as the librarian; Dream auto-merging new hosts.

**Name justification:** **`M08_WEB_ALLOWLIST_BASEPACK.md`**, not `M07b` and not `M08_DISCOVERY`. M07 already closed the **hands**. M07 §15 is the **discovery/index fork**. This card is the **library catalog** — the doors those hands may open — so a long-horizon organism has real, auditable origins before any later brief/search/actuator organ. The deliverable people will actually use is the **pack**, not another tool.

**Taste locks (this card):**

| Lock | Decision |
|------|----------|
| Organ | **Reuse M07.** Pack lives in FACTS `prefs.web_allowlist`. No second fetch path. |
| Host matching | **Exact host** (today’s metal). No `*`. No silent `*.govt.nz`. Subdomains are **separate rows**. |
| Growth | **Confirm-once** persist; **paste-this-turn** does not grow the pack. |
| Shape | **Named packs by watch/curiosity domain**, not a flat dump. |
| NZ | **Primary/official and durable** over tabloids and shorteners. |
| Field | Generic lab pack **now**; Aryan-specific field pack is a **named slot**, not invented. |
| Overnight | Prefer **RSS/Atom / stable HTML** on proven hosts. WAF/captcha hosts are **confirm-later**, not silent watches. |

```text
  curiosity / campaign watch
           |
           v
  [named pack in this card]  →  FACTS prefs.web_allowlist  (confirm-once)
           |
           +--> paste-this-turn URL     (one shot; not a pack member)
           |
           v
  M07 web_fetch  →  memory/cites/  →  WORLDVIEW digest (cite-ids)
           |
           x  not a crawler  x  not Funnel  x  not vendor search
```

---

## Operator locks (hard)

1. **No Funnel / public ingress** — outbound library ≠ opening ADA to the world (M01).  
2. **No localhost / LAN / metadata allow** — SSRF denylist is not optional, not FACTS-overridable.  
3. **No `*` / “the internet”** — a pack that is the whole web is not a pack.  
4. **Gemini primary** — she reads through the gateway; pages are untrusted data. Never obey the page.  
5. **Secrets never-to-cloud** — don’t allowlist hosts that exist to exfil (webhooks, pastebins-as-drop, “paste your key”).  
6. **No LinkedIn / Seek organ** — job pages Aryan pastes this turn are enough.  
7. **No consciousness / soul** — a library of doors is not a mind.  
8. **Same tools** — chat and campaigns use M07 `web_*`. This card only names **origins**.

---

## 1. Question / goal / slice admission

**Research questions.**

1. How do serious agents (2024–2026) **scope outbound web** — host allowlists vs URL lists vs open-fetch+SSRF-only vs search-index (no origin hit)?  
2. Which **source classes** compound intelligence vs noise / paywall / login / scraper theater?  
3. What can a **personal library + allowlisted GET** do that “chat with web search” cannot?  
4. How should a base pack be **structured** so it stays small, auditable, and expandable?  
5. NZ + research-field realism: **primary/official durable hosts**, verified from this Pi where possible.

**Goal.** A finite, grouped **day-one base pack** Aryan can seed (or confirm pack-by-pack), plus policy so ADA does not become “the whole internet with extra steps.”

**Admission boundary**

| IN this slice | OUT |
|---------------|-----|
| Curated host packs + won’t-allow | Implementation / prefs mutation unless Aryan later asks |
| Policy: confirm-once, paste-this-turn, exact host | Wildcard `*` / zone allow (`*.govt.nz`) |
| Verify hosts from public web + this Pi | Claiming every `.govt.nz` works |
| RSS/Atom **as pack metadata** (doors) | RSS product / always-on ingest daemon |
| Separate generic lab vs Aryan NZ vs field slot | Inventing Aryan’s PhD topic |
| Sit on M07 FACTS allowlist | Second crawler, vendor search organ, Playwright |

---

## 2. Simple mental model for Aryan (≤5 concepts)

| # | Concept | Meaning |
|---|---------|---------|
| **1. Door** | A **host** ADA may GET. Not a URL dump. Not “the web.” |
| **2. Pack** | A **named group of doors** for a curiosity domain (lab papers, NZ law, NZ news…). You enable a pack, not 400 random sites. |
| **3. Watch** | Recurring URLs/feeds **on doors already open**. Campaigns list feeds; they do not punch new holes. |
| **4. Paste** | A URL in **this turn** is a guest pass. It does not join the household. |
| **5. Library** | What she **kept** (`memory/cites/`). Intelligence compounds here — not in the search box. |

**One sentence:** *Search finds a door; the allowlist says she may open it; a cite is the book she put on the shelf; packs are the rooms of the house.*

**Reject for this vocabulary:** “crawl NZ,” “allow `*`,” “she’s on the internet now,” “OSINT platform,” “browser agent.”

---

## 3. Lens tags

| Tag | Meaning here |
|-----|----------------|
| **FANFICTION** | Omniscient live web; zone wildcards; overnight scrape of every `.co.nz`; “she understands New Zealand” without receipts |
| **EVIDENCE** | Claude/Cursor allowlists; OWASP SSRF; Progent; RSS-as-ingest; quote-first / usable-scale memory |
| **FEASIBLE-on-Pi8GB** | Exact-host FACTS list + existing GET; no Chromium; no 500-URL crawler |
| **POLICY** | No Funnel; confirm-once; no localhost; web egress named; Dream must not auto-merge hosts |
| **METAL** | `allowlist.py` exact match; `ssrf.py` redirect revalidate; prefs currently `arxiv.org` only |

---

## 4. SOTA landscape (2024–2026) — how serious agents scope outbound web

Every row tagged. Citations are lineage, not homework.

### 4.1 Four scopes (honest split)

| Scope | What it is | Origin hit? | Typical use | Tag | ADA takeaway |
|-------|------------|-------------|-------------|-----|----------------|
| **A. Host allowlist** | Named hostnames; GET only those | Yes, to those hosts | Claude `allowed_domains`; Cursor `WebFetch(domain)`; ADA `prefs.web_allowlist` | **EVIDENCE** | **ADA’s ring.** Default-deny. |
| **B. URL / path list** | Exact URLs or path prefixes | Yes, narrower | Campaign `watch_urls[]`; Claude search allows `example.com/blog` (fetch itself is **domain-only**) | **EVIDENCE** | Watches live **on** allowlisted hosts. Don’t replace the host pack with 500 paths. |
| **C. Open fetch + SSRF-only** | Any public HTTPS; block RFC1918/metadata | Yes, unbounded public | Webhooks, “open browsing” agents | **EVIDENCE** (OWASP: last resort when the set is unknown) | **Reject as ADA default.** Prompt injection + exfil. Confirm-once is the expansion valve, not “public is fine.” |
| **D. Search index (no origin)** | Query a vendor index; snippets | Usually **no** origin hit | Claude `web_search`; Gemini grounding; Serper | **EVIDENCE** | Discovery, not reading. Snippets ≠ cites (M07). Optional v1.1 — **not this card.** |

**Claude API (2025–26)** — [web fetch](https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-fetch-tool), [web search](https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool), [server tools / domain filtering](https://platform.claude.com/docs/en/agents-and-tools/tool-use/server-tools): `allowed_domains` **or** `blocked_domains` (not both). Bare `example.com` **includes subdomains**; `docs.example.com` is that host only. Fetch **does not run JS**. Extra exfil control: model may only fetch URLs that **already appeared** in the conversation (user / prior search / prior fetch) — cannot freely mint URLs. **EVIDENCE.**

**Claude Code** — [WebFetch/WebSearch playbook](https://engineering-playbook.vercel.app/claude-code/webfetch-and-websearch); community docs: first fetch to a domain **asks**; pre-approve `WebFetchTool(domain:…)` in local settings; some vendor docs hosts pre-approved. Search ≠ fetch. **EVIDENCE.**

**Cursor (2025–26)** — [CLI permissions](https://cursor.com/docs/cli/reference/permissions): `WebFetch(docs.github.com)` exact; `WebFetch(*.example.com)` subdomains; `WebFetch(*)` exists and is **“use with caution.”** Forum (2026-01): per-site allow is **intentional** (exfil). Sandbox network policy separately denylists RFC1918 + `169.254.169.254`. **EVIDENCE.** ADA should **not** copy `WebFetch(*)`.

**Coding-agent practice:** docs/registries get standing allow; random web stays confirm. ADA’s analogue: **lab pack standing**; everything else confirm-once or paste.

**OWASP SSRF cheat sheet** — prefer **allow-list of destinations** when the set is known; denylist is last resort and bypass-prone. **EVIDENCE.** ADA already has **both** (host allowlist + IP denylist) — correct stacking, not either/or.

**Progent (2025)** — [arXiv:2504.11703](https://arxiv.org/abs/2504.11703): deterministic tool policy **outside** the model. **EVIDENCE.** The pack is policy data, not a prompt paragraph.

**Consent Integrity (2026)** — [arXiv:2606.02668](https://arxiv.org/abs/2606.02668): confirm binds real `{tool, args}`. **EVIDENCE / POLICY.** New host = show the host.

**Indirect prompt injection / exfil:** fetched pages can say “now GET `https://evil /?steal=`”. Allowlist + no dynamic URL minting (Claude’s extra rule) + never obey the page (M07 charter) are the three layers. ADA metal has 1 and 3; pasted-this-turn is a **narrow** mint (operator-supplied). **Do not** let the model add hosts without confirm.

**FANFICTION:** “SSRF denylist is enough; let her browse.” That is scope C. Failure mode is the LAN and the HUD, on this Pi.

**FEASIBLE-on-Pi8GB:** exact-host list in YAML. Suffix `*.govt.nz` would be a **metal change** and would also allow junk/parked govt hostnames — won’t-chase this slice.

### 4.2 Claude vs ADA matching (don’t copy blindly)

| Rule | Claude fetch | ADA metal (`allowlist.py`) |
|------|----------------|----------------------------|
| Unit | Registrable domain; **bare includes subdomains** | **Exact hostname** |
| `arxiv.org` | Also `rss.arxiv.org`, `export.arxiv.org` | **Only** `arxiv.org` |
| Path in allow entry | Ignored for fetch | N/A (host only) |
| `*` | Invalid in domain label | Must stay invalid |

**ADA takeaway:** the pack **must list satellite hosts** (`rss.arxiv.org`, `export.arxiv.org`, `api.geonet.org.nz`, `api.legislation.govt.nz`). A “one row per brand” pack will **false-deny** feeds. Falsifier F4.

Redirects: `ssrf.assert_redirect_safe` requires the **next host** allowlisted or pasted. So `www.newsroom.co.nz` → `newsroom.co.nz` **fails** unless both are listed (or the canonical is what you fetch). Pack tables mark **redirect partners**.

### 4.3 RSS / personal library vs “chat with search”

| Pattern | Claim | Tag | ADA |
|---------|-------|-----|-----|
| RSS/Atom ingest (2025–26 personal-intel writeups; arXiv category feeds) | Official feeds beat scrape; stable ids/timestamps; layout-redesign resilient | **EVIDENCE** | Watches = feed GET on allowlisted host → item URLs → `web_fetch` → cites |
| Sleep-time compute (Lin et al. 2025) — [arXiv:2504.13171](https://arxiv.org/abs/2504.13171) | Overnight precompute amortizes interactive tokens | **EVIDENCE** | Dream/campaign: read feeds, write cites, digest cite-ids |
| Usable-scale evidence (2026) — [html](https://arxiv.org/html/2605.07313) | Stored evidence dies if you can’t retrieve it | **EVIDENCE** | Library-first `web_cite_search` (M07) **is** the compounding surface |
| “Deep research” vendor loops | Many search queries + live fetches, no durable personal shelf | **EVIDENCE** (product) | Fine as a *cloud product*; not ADA’s years-long organism |
| Search-index only | Fast, no origin, no receipt of the page | **EVIDENCE** | Cannot honestly say “I read the Act” |

**What the personal library uniquely does** (this is the organism pitch, without a soul):

| Chat + web search | Allowlisted GET + cites on disk |
|-------------------|-------------------------------|
| Ranking of the day; forgotten tomorrow | **Re-open the same cite in 2028** |
| Snippet theater | **Receipt:** URL, time, hash, excerpt |
| One-domain answer | **Cross-pack synthesis later** (NZBORA cite + Treasury feed cite + arXiv cite in one WORLDVIEW digest) |
| Vendor saw the query | Origin hit is **named** (web egress ring) |
| No overnight | Campaign/Dream can **re-read watches while idle** (M06), still not a crawler |

**FANFICTION:** “if she can search, she knows NZ.”  
**FEASIBLE:** she knows the pages she was allowed to fetch and kept.

### 4.4 Source classes that compound vs that rot

| Class | Intelligence unlocked | Failure mode | Pack stance |
|-------|----------------------|--------------|-------------|
| **Official statistics / fiscal / central bank** | “How money and the real economy move here” with primary numbers | WAF 403; JS dashboards | Stats + Treasury **in**. RBNZ **watch-later** (this Pi: **403**) |
| **Legislation / Hansard / Gazette** | Law as it is, not as a blog summarised it | Classic-site feed rot; captcha on Parliament | Legislation HTML **in**. Parliament **WAF**. Gazette RSS is **API-key** — out of day-one GET |
| **Registers / filings** | Firms, directors, “who actually exists” | Login for filing; JS search | Companies Register **public HTML in**; RealMe filing **won’t-allow** |
| **Encyclopedias (Te Ara, NZHistory, Wikipedia)** | Durable “why people here are like this” / geography / history | Stale wiki vandalism; Te Ara RSS undocumented | Fetch-on-demand **in**; don’t RSS-watch Wikipedia recentchanges (noise) |
| **Papers (arXiv, ACL, PMLR)** | Field current + ADA’s own lab literature | PDF-only; OpenReview SPA | arXiv+ACL+PMLR **in**; OpenReview **later** (JS) |
| **Feeds (RSS/Atom)** | Overnight delta without search vendor | Dead `/rss.xml`; homepage WAF but feed OK | Prefer **probed XML 200** |
| **Public-service news** | Current events with fewer paywalls | RNZ ToS: **personal use**; don’t republish | RNZ + Newsroom + Spinoff feeds **in** as *finite* news lens |
| **Standards / engineering docs** | How to build (RFCs, MDN, CPython, GitHub docs) | SPA docs shells | Probed HTML **in** |
| **Tabloid / SEO mill / aggregator** | Noise, rage, duplicate | Hallucinated NZ | **Won’t-allow** day-one |
| **Paywall / login wall** | Scraper theater | “I read it” lies | Herald/Stuff **out**; paste if Aryan has a URL and extract is empty → say so |
| **Shorteners** | Hide destination; open redirect | SSRF/exfil adjacent | **Won’t-allow** |
| **Scrape farms / browser SaaS** | Someone else’s crawl | Extra egress + ToS | **Won’t-allow** as origins |

---

## 5. Recommended pack structure (small, auditable, expandable)

Four layers. Only layer 2 is “the pack.”

```text
Layer 0  WON’T-ALLOW + SSRF     hard; not FACTS-overridable
Layer 1  GENERIC POLICY         exact host; confirm-once; paste-this-turn; TTL vibe
Layer 2  NAMED PACKS            this card — lab / nz-* / field-*
Layer 3  WATCH URLS             campaign feeds on doors already open
Layer 4  PASTE-THIS-TURN        guest; does not persist
```

| Layer | Who edits | How it grows | How it stays small |
|-------|-----------|--------------|-------------------|
| 0 | Constitution + `ssrf.py` | It doesn’t | LAN/metadata forever out |
| 1 | This card + charter | Rare | No `*` |
| 2 | Aryan confirms a **pack** (or host) | Pack-at-a-time | Budget: day-one **~45 hosts**; pause at **~80** for a review, don’t creep to 500 |
| 3 | Campaign stage fields | New **paths** on old hosts | Host already paid the confirm |
| 4 | The chat turn | Ephemeral | Next turn: confirm if it should join a pack |

**Generic policy (locked sketch):**

1. **Exact host** as metal today. Want suffix include? That’s a **future metal** OPEN — not smuggled as `*` in FACTS.  
2. **Confirm-once** → append `{host, ttl_seconds, note: "pack:<id>"}`. `note` already exists on metal.  
3. **Paste-this-turn** → fetch OK; **do not** `add_host`. Operator can later say “keep this door.”  
4. **Redirect partners** listed together (F11).  
5. **ASCII hosts only** (Claude homograph warning).  
6. **Dream must not auto-merge `web_allowlist`** — not on the body §5.3 whitelist. Correct. Keep it that way.  
7. **Campaigns cannot invent hosts.** Stage `feed_url` whose host isn’t allowlisted → confirm or skip.  
8. **TTL is freshness, not delete** (M07). Pack only suggests a **vibe**.

**TTL vibes**

| Vibe | `ttl_seconds` (sketch) | Use |
|------|------------------------|-----|
| `interactive` | 900 | Default metal; news HTML |
| `feed` | 3600 | RSS/Atom polls |
| `release` | 14400 | Stats/Treasury release pages |
| `stable` | 86400 | Legislation, encyclopedia, RFCs, arXiv abs, docs |

**How a new host gets in (without becoming the internet):**

```text
need a URL
  → already in pack / prefs? fetch
  → pasted this turn? fetch; receipt flags pasted; do not persist
  → else gateway needs_confirm (real host in args)
        → Aryan yes: add_host + note pack id
        → Aryan no: deny
  → if allowlist length > ~80: ask which pack to retire, don’t only add
```

**Won’t-allow (layer 0 — explicit)**

| Class | Examples | Why |
|-------|----------|-----|
| Loopback / HUD | `localhost`, `127.0.0.1`, `::1`, `ada-pi5`, `.local` | SSRF; she must not fetch herself as “the web” |
| LAN / CGNAT | `10/8`, `172.16/12`, `192.168/16`, `100.64/10` (Tailscale) | Same |
| Metadata | `169.254.169.254`, `metadata.google.internal` | Credential theft |
| Wildcards | `*`, `*.govt.nz`, `*.co.nz` | Pack becomes the internet |
| Shorteners | `bit.ly`, `t.co`, `tinyurl.com`, `lnkd.in` | Hide destination |
| Login / scrape organs | `linkedin.com`, `www.seek.co.nz`, RealMe filing apps | POLICY + theater |
| Search HTML | `www.google.com`, `news.google.com` | That’s vendor search, not fetch |
| Scrape farms | Firecrawl/Jina/ScrapingBee **as required origins** | Extra egress; M07 already rejected as organ |
| Secret drops | Random pastebins, webhook.site-class | Exfil |
| Social login walls | Facebook / X as default news | Login + noise |

IP denylist is **already** in `ssrf.py`. This table is the **named-host** complement so nobody “helpfully” allowlists `localhost` in FACTS.

---

## 6. Vision (organism / library — no soul)

ADA is meant to feel like a **small digital intelligence organism** on one Pi: companion + research aide, **years of shelves**, not a SaaS chatbot with a search plugin.

Design toward:

- She has **rooms** (packs): lab bench, Aotearoa civic/economic/cultural, a field desk.  
- She **re-reads** what she was allowed to read (cites), and can connect NZ law to money-movement to a paper — **with receipts**.  
- She stays **current** via a few honest feeds, not by pretending to watch the whole web.  
- She is **witty and sharp** in voice; the library is still **primary sources**.

Do **not** invent: sentience, a soul, “she understands Kiwis,” AGI, or public ingress so the world can talk to her shelves.

**METAL honesty:** today the house has **one door** (`arxiv.org`). This card is the floor plan. Seeding FACTS is an **operator confirm**, not this file executing.

---

## 7. Curated base pack

**Verification (METAL):** HTTPS GET probes from `ada-pi5` on **2026-08-14** with a research UA (not a crawl). DNS resolved for all listed hosts unless noted. Status is **this Pi’s egress**, not a global SLA.

**Legend:** Fetch = static HTML/XML useful to M07 extract. RSS/API = probed or vendor-documented. Risk = JS/WAF/paywall/ToS. TTL = vibe.

### 7.1 Day-one seed (enable these)

Grouped. **~48 host rows** including redirect partners. Finite on purpose.

#### Pack `lab.papers` — generic research bench

| Host | Why | Fetch / RSS / API | Risk | TTL |
|------|-----|-------------------|------|-----|
| `arxiv.org` | Abs pages; already in prefs | HTML abs **200** (`/abs/2210.03629`) | Low | `stable` |
| `export.arxiv.org` | Atom query API ([manual](https://info.arxiv.org/help/api/user-manual.html)); **not** covered by exact `arxiv.org` | Atom **200** | Rate-limit ToS (~3s) | `feed` |
| `rss.arxiv.org` | Category RSS/Atom ([help](https://info.arxiv.org/help/rss.html)) | ` /rss/cs.AI` RSS **200**; `/atom/cs.LG` Atom **200** | Same ToS | `feed` |
| `info.arxiv.org` | API/RSS docs | HTML **200** | Low | `stable` |
| `aclanthology.org` | ACL venue HTML (NLP/agents-adjacent literature) | HTML **200** | Some JS chrome | `stable` |
| `proceedings.mlr.press` | PMLR open proceedings | HTML **200** | Low | `stable` |

**Watch examples (layer 3, not extra hosts):** `https://rss.arxiv.org/rss/cs.AI`, `https://rss.arxiv.org/atom/cs.LG`, `https://rss.arxiv.org/rss/cs.MA` — Aryan picks categories when the field name is known.

#### Pack `lab.code` — engineering docs (ADA’s own body language)

| Host | Why | Fetch / RSS / API | Risk | TTL |
|------|-----|-------------------|------|-----|
| `github.com` | Public READMEs / issues HTML | HTML **200** | Heavy JS chrome; login walls on private | `stable` |
| `docs.github.com` | Product docs | HTML **200** | Low–medium JS | `stable` |
| `docs.python.org` | CPython docs | HTML **200** | Low | `stable` |
| `pypi.org` | Package pages | HTML **200** | Low | `release` |
| `peps.python.org` | PEPs | HTML **200** | Low | `stable` |
| `developer.mozilla.org` | HTTP/web platform (M07 already cites ETag docs) | HTML **200** | Low | `stable` |

**Out of day-one:** `raw.githubusercontent.com` (huge blobs; paste if needed).

#### Pack `lab.standards`

| Host | Why | Fetch / RSS / API | Risk | TTL |
|------|-----|-------------------|------|-----|
| `www.rfc-editor.org` | RFCs | HTML **200** (path may redirect **same host**) | Low | `stable` |
| `datatracker.ietf.org` | RFC HTML + IETF process | HTML **200** | Low | `stable` |

#### Pack `lab.encyclopedia` (global context; NZ encyclopedias are in `nz.place`)

| Host | Why | Fetch / RSS / API | Risk | TTL |
|------|-----|-------------------|------|-----|
| `en.wikipedia.org` | Background; **fetch named articles**, don’t watch recentchanges | HTML **200**; Atom recentchanges exists (**noise** — not a watch) | Vandalism; treat as secondary to NZ official | `stable` |
| `www.wikidata.org` | Stable entity ids (e.g. NZ `Q664`) | HTML **200** | Low | `stable` |

#### Pack `lab.cortex-docs` — how *her* vendors actually work

| Host | Why | Fetch / RSS / API | Risk | TTL |
|------|-----|-------------------|------|-----|
| `ai.google.dev` | Gemini API docs (URL context vs FC — M07) | HTML **200** | Low–medium | `stable` |
| `www.anthropic.com` | Engineering posts (agents, MCP) | HTML **200** | Medium JS | `stable` |
| `platform.claude.com` | Fetch/search tool docs (this card’s SOTA) | HTML **200** | Medium JS | `stable` |

These are **lab hygiene**, not a personality cult. She should be able to re-read the rules of the tools she is compared to.

#### Pack `nz.law`

| Host | Why | Fetch / RSS / API | Risk | TTL |
|------|-----|-------------------|------|-----|
| `www.legislation.govt.nz` | **Primary law** (Acts HTML). NZBORA path **200** | HTML **200**; site documents RSS + [API](https://api.legislation.govt.nz/docs/) | Classic feeds: rebuild after **2026-03-08** (PCO notice) — use **current** site/API | `stable` |
| `legislation.govt.nz` | Apex DNS exists; redirect partner | Don’t assume content | List so F11 doesn’t bite | `stable` |
| `api.legislation.govt.nz` | v0 developer API (docs HTML **200**) | API GET later; docs now | v0 / changing | `stable` |
| `waitangitribunal.govt.nz` | Treaty jurisprudence / reports | HTML **200** (`www.` also 200, same) | Low–medium | `stable` |
| `www.justice.govt.nz` | Justice / courts orientation | HTML **200** | Medium | `stable` |

**Out of day-one watches:** `www.parliament.nz` / `hansard.parliament.nz` — probe **Radware captcha** (perfdrive). Official, but **JS/WAF shell from this Pi**. Confirm-later. Gazette RSS needs an **API key** ([gazette.govt.nz](https://gazette.govt.nz/find-a-notice)) — not anonymous GET.

#### Pack `nz.civic`

| Host | Why | Fetch / RSS / API | Risk | TTL |
|------|-----|-------------------|------|-----|
| `www.beehive.govt.nz` | Executive releases | **RSS ` /rss.xml` 200** ([feeds](https://www.beehive.govt.nz/feeds)) | **Homepage Imperva/JS challenge**; **use the feed**, not the home HTML | `feed` |
| `www.tpk.govt.nz` | Te Puni Kōkiri — Māori Crown policy | HTML **200** (`/en`) | Medium | `stable` |

#### Pack `nz.economy`

| Host | Why | Fetch / RSS / API | Risk | TTL |
|------|-----|-------------------|------|-----|
| `www.treasury.govt.nz` | Fiscal / economic publications | **RSS `/feeds/news` 200**; also publications / RIS / data-charts feeds | Low on feeds | `feed` / `release` |
| `treasury.govt.nz` | Redirects **→ www** | Partner | Must co-list | `feed` |
| `www.stats.govt.nz` | Official statistics HTML (releases, calendar) | HTML **200**. **No public RSS** found — email/ICS instead | Fetch release pages; don’t invent a feed | `release` |
| `stats.govt.nz` | Apex also resolves | Partner | Co-list | `release` |
| `www.companiesoffice.govt.nz` | How registers work / data-services docs | HTML **200** | Low | `stable` |
| `companies-register.companiesoffice.govt.nz` | **Public** company search / extracts (no RealMe for read) | HTML **200** | Search UI may be JS-heavy; still a real door | `release` |
| `www.fma.govt.nz` | Conduct regulator | HTML **200** | Medium | `release` |
| `www.comcom.govt.nz` | Commerce Commission | HTML **200** | Medium | `release` |
| `comcom.govt.nz` | Redirects **→ www** | Partner | Co-list | `release` |
| `www.interest.co.nz` | NZ wholesale/rates/housing **specialist** (not a tabloid) | HTML **200**; **`/rss` 200**. `/rss.xml` is **410** — don’t use it | ToS/media | `feed` |

**Out of day-one:** `www.rbnz.govt.nz` — **403** from this Pi even with a browser-like UA. Central bank still **belongs intellectually**; it does not belong on an overnight watch until GET succeeds. Confirm-later + falsifier F7.

#### Pack `nz.data`

| Host | Why | Fetch / RSS / API | Risk | TTL |
|------|-----|-------------------|------|-----|
| `www.data.govt.nz` | Catalogue front door | HTML **200** (CDN interstitial possible) | Medium WAF | `release` |
| `catalogue.data.govt.nz` | CKAN-style dataset records | DNS+site live | Medium | `release` |

#### Pack `nz.place` — geography, hazards, “what this land is”

| Host | Why | Fetch / RSS / API | Risk | TTL |
|------|-----|-------------------|------|-----|
| `teara.govt.nz` | **Te Ara** — encyclopedia of Aotearoa (culture, economy, environment, biographies) | HTML **200** | RSS mentioned in copyright, **no durable public index URL found** — fetch articles | `stable` |
| `nzhistory.govt.nz` | MCH NZ History | HTML **200** | Same | `stable` |
| `www.mch.govt.nz` | Manatū Taonga — parent / pointers | HTML (MCH pages live) | Medium | `stable` |
| `www.linz.govt.nz` | Toitū Te Whenua — place, property, geodetic | HTML **200** | Medium | `stable` |
| `www.geonet.org.nz` | GNS GeoNet explainers | HTML **200** | Medium JS | `release` |
| `api.geonet.org.nz` | **JSON/CAP** quakes (`/quake?MMI=4` **200** geojson; CAP Atom documented) | API **200** | Separate host! | `feed` |

**Out of day-one:** `www.metservice.com` HTML looks SPA-ish; weather alerts live on **`alerts.metservice.com`** (separate host, CAP RSS documented by NEMA). Add when Aryan wants a weather watch — don’t pretend the homepage is the feed.

#### Pack `nz.news` — finite current-events lens (not a content mill)

| Host | Why | Fetch / RSS / API | Risk | TTL |
|------|-----|-------------------|------|-----|
| `www.rnz.co.nz` | Public-service news; **personal-use RSS** ([index](https://www.rnz.co.nz/rss)) | `/rss/national.xml`, `political.xml`, `business.xml` **200 XML** | **ToS: personal use, no republish**. Index `/rss` is HTML. | `interactive` / `feed` |
| `newsroom.co.nz` | Independent NZ journalism | `/feed` RSS **200**; www **redirects → apex** | Medium; possible subscribe walls on some articles | `feed` |
| `www.newsroom.co.nz` | Redirect partner | Co-list | — | `feed` |
| `thespinoff.co.nz` | Culture / politics context | `/feed` **Atom 200** | **Next-ish HTML** — article fetch may be JS-thin; feed still useful | `feed` |

**Out of day-one:** `www.nzherald.co.nz`, `www.stuff.co.nz` — paywall / meter theater. Paste-this-turn if Aryan needs a specific URL; empty extract → say so (M07 F1).

#### Pack `field.agents` — **starter field desk** (lab-adjacent, not Aryan’s CV)

ADA’s documented intent is **PhD-prep + agent/physical-AI lab**. Memory does **not** name a professional field. This pack is the **doors she already thinks in** (ReAct, memory surveys, tool policy). It is **not** a claim that Aryan’s career is “AI papers.”

| Host | Why | Notes |
|------|-----|-------|
| *(inherits `lab.papers` + `lab.cortex-docs`)* | Enough for overnight cs.AI / cs.LG / cs.MA | Don’t duplicate hosts |

**Empty on purpose:** `field.primary` — wait for OPEN Q1 (economics? software? SEO/GSC? something else). When named, add **3–8 primary hosts**, not 80 blogs.

### 7.2 Confirm-later (official or useful — not overnight)

Do **not** seed these until a **this-Pi GET** is honest.

| Host | Why it belongs | Why not day-one (METAL 2026-08-14) |
|------|----------------|-------------------------------------|
| `www.rbnz.govt.nz` | Central bank / money | **403** |
| `www.parliament.nz` | Hansard / bills progress | **Radware captcha** |
| `hansard.parliament.nz` | Hansard app | Captcha + **JS SPA error** in public snippets |
| `gazette.govt.nz` | Official notices | Homepage bot-interstitial; RSS **keyed** |
| `www.mbie.govt.nz` | Business / immigration policy | Imperva-style home |
| `www.ird.govt.nz` | Tax system | Portal-shaped; login gravity |
| `huggingface.co` | Models/papers hub | JS-heavy; not required if arXiv exists |
| `openreview.net` | Peer review | SPA risk |
| `www.nist.gov` / `csrc.nist.gov` | Standards (probed **200**) | Generic lab overflow — add if a watch needs them |
| `alerts.metservice.com` | CAP weather | Separate host; add with a weather campaign |
| `raw.githubusercontent.com` | Raw files | Paste / confirm per need |

### 7.3 FACTS seed sketch (design — not executed)

Illustrative `prefs.web_allowlist` items. Operator confirm still required. `note` carries the pack id for audit.

```yaml
# design sketch — do not treat as applied
web_allowlist:
  - {host: arxiv.org, ttl_seconds: 86400, note: "pack:lab.papers"}
  - {host: export.arxiv.org, ttl_seconds: 3600, note: "pack:lab.papers"}
  - {host: rss.arxiv.org, ttl_seconds: 3600, note: "pack:lab.papers"}
  # …remainder of §7.1, including redirect partners
```

**Current metal:** only `arxiv.org` @ 900s. Seeding is an **option after this card**, not a silent Dream merge.

### 7.4 Suggested first watches (layer 3 — still not a crawler)

When campaigns grow RSS (M07 hook / M06 stage), start **tiny**:

| Watch | Feed / page | Pack |
|-------|-------------|------|
| Agents literature | `https://rss.arxiv.org/rss/cs.AI` | lab.papers |
| NZ executive | `https://www.beehive.govt.nz/rss.xml` | nz.civic |
| Fiscal | `https://www.treasury.govt.nz/feeds/news` | nz.economy |
| NZ politics news | `https://www.rnz.co.nz/rss/political.xml` | nz.news |
| Quakes (optional) | `https://api.geonet.org.nz/quake?MMI=4` | nz.place |

Idle between wakes. Honor robots on unattended pulls (M07). RNZ: personal library, **not** a republishing organ.

---

## 8. How this sits on M07 metal

| Piece | Role | Not |
|-------|------|-----|
| `prefs.web_allowlist` | **The pack, instantiated** | A second config file / crawler DB |
| `allowlist.py` exact host | Pack rows | Claude-style implicit subdomains |
| `ssrf.py` | Layer 0 | Replacing the allowlist |
| Paste-this-turn | Layer 4 | A way to smuggle persist |
| `web_fetch` → `memory/cites/` | Library compounding | Search snippets as cites |
| `web_cite_search` | Find what she already read | Open-web search |
| M06 campaign `watch_urls` / feeds | Layer 3 | New organ |
| M07 §15 fork | Personal index / Tor **later** | This card |

**Constitution:** already allows allowlisted GET; first new host confirms. **No amend required** to *hold* a pack. Seeding many hosts at once should still be an **operator “yes to pack X”**, not 48 silent confirms in a loop.

**Egress rings:** unchanged. Pack members are **web egress** origins. Cortex still sees capped extracts.

**Pi 8GB:** YAML of ~50 hosts is nothing. The cost is **overnight fetch volume**. Cap watches (M07 `max_uses` analogue), not host count.

---

## 9. Learning goals (lab)

After this card, Aryan should be able to explain:

1. Why **allowlist ≠ SSRF-only ≠ search-index**, and why ADA stacks allowlist **plus** SSRF.  
2. Why **exact host** means `rss.arxiv.org` is a different door from `arxiv.org`.  
3. Why a **personal cite library** compounds across NZ + field in a way chat-search does not.  
4. Why **feeds on official hosts** beat tabloids and scrape farms.  
5. Why **WAF 403 / captcha** is an honest “not yet,” not a Playwright day-one.  
6. How new doors enter (**confirm-once**) without `*`.

**Harder-correct:** named packs + exact hosts + confirm-once + library cites.  
**Shortcut rejected:** `*` ; Gemini grounding as the library; “allow all `.govt.nz`.”

---

## 10. Falsifiers

| # | Falsifier | Pass look |
|---|-----------|-----------|
| F1 | Pack is the internet | No `*`; day-one **≤ ~50** hosts; pause review ~80 |
| F2 | Localhost / LAN in FACTS | `ssrf` still denies even if someone types it; card won’t-allow |
| F3 | Fake NZ literacy | WORLDVIEW NZ claims cite **legislation/stats/Te Ara/RNZ** cite-ids, not vibes |
| F4 | Subdomain miss | Feed fetch to `rss.arxiv.org` works **only if that host is listed** |
| F5 | Redirect trap | `treasury.govt.nz` and `www.newsroom.co.nz` partners co-listed or fetch uses canonical |
| F6 | JS shell claimed as read | Parliament/captcha / empty SPA → no “I read Hansard”; F1 from M07 |
| F7 | RBNZ overnight theater | Don’t schedule RBNZ until GET ≠ 403 from this Pi |
| F8 | Dead host | Probe 2026-08-14 hosts still resolve; retire on persistent fail |
| F9 | News mill | Herald/Stuff not in day-one; RNZ ToS respected (no republish actuator) |
| F10 | Funnel | Pack does not bind public ingress |
| F11 | Dream sneaks hosts | `web_allowlist` stays off auto-merge whitelist |
| F12 | Second crawler | No new daemon; campaigns still idle |

---

## 11. Egress / trust rings

| Ring | This card |
|------|-----------|
| Tailscale control | Unchanged; **no Funnel** |
| Gemini cortex | Capped extracts from pack hosts (same as M07) |
| Backup | No |
| **Web** | **Yes** — only pack / pasted / confirmed hosts |
| Local cites | **Yes** — this is the organism’s shelf |

---

## 12. OPEN questions for Aryan

1. **Field name?** What should `field.primary` be (papers + 3–8 industry/official hosts)? Agents/systems is only the **lab starter**.  
2. **News appetite?** RNZ-only vs RNZ+Newsroom+Spinoff. More is not automatically smarter.  
3. **Which NZ lens first?** Law (legislation/Te Ara) vs economy (Treasury/Stats/register) vs culture (Te Ara/NZHistory/TPK) vs news. Recommend **law + economy + Te Ara**, news as a small feed.  
4. **Seed now?** Copy §7.1 into `prefs.web_allowlist` in one confirm-per-pack vs keep paste-only until a watch exists.  
5. **Exact vs suffix hosts?** Stay exact (teachable, current metal) vs later `example.com` includes subdomains (Claude-like). Recommend **stay exact** until satellite hosts hurt.  
6. **RBNZ:** wait for 403 to lift vs drop the host from even confirm-later until a human browser on the Pi works. Recommend **keep on confirm-later**, don’t spoof UA as a product.

Non-questions: no Funnel; no `*`; no localhost; no LinkedIn organ; no Playwright-to-unblock Parliament as this card’s job; no soul; Gemini primary.

---

## 13. Ordered “after this card” — **options**, not a locked next module

1. **Operator seed** — confirm pack `lab.*` then `nz.law` + `nz.economy` + `nz.place` (Te Ara) into FACTS.  
2. **One campaign watch** — e.g. arXiv cs.AI **or** Beehive RSS — using M07 fetch + M06 idle (RSS helper still a hook).  
3. **Prove F4/F5** — fetch `rss.arxiv.org` and a Treasury feed; confirm cites land.  
4. **Fill `field.primary`** when Q1 is answered.  
5. **Confirm-later hosts** only after a successful GET from this Pi (RBNZ, Parliament).  
6. **M07 v1.1 vendor search** if open-web discovery without URLs hurts — still not a library replacement.  
7. **M07 §15 fork** (personal index / Tor) — still after the shelf is real.  
8. **Metal optional:** suffix matching / pack-id field richer than `note` — only if exact-host pain is measured.

Do **not** treat this list as a roadmap ADA must walk. The card’s job is the **pack + policy**. Later organs may *use* it.

---

## 14. References (selected)

### Allowlists / fetch policy
- Anthropic, web fetch — https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-fetch-tool  
- Anthropic, web search — https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool  
- Anthropic, server tools (domain filtering) — https://platform.claude.com/docs/en/agents-and-tools/tool-use/server-tools  
- Cursor CLI permissions (WebFetch) — https://cursor.com/docs/cli/reference/permissions  
- OWASP SSRF Prevention Cheat Sheet — https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html  
- Shi et al., Progent (2025) — https://arxiv.org/abs/2504.11703  
- Consent Integrity (2026) — https://arxiv.org/abs/2606.02668  

### Library vs search
- Lin et al., Sleep-time Compute (2025) — https://arxiv.org/abs/2504.13171  
- *When Stored Evidence Stops Being Usable* (2026) — https://arxiv.org/html/2605.07313  
- arXiv RSS — https://info.arxiv.org/help/rss.html  
- arXiv API — https://info.arxiv.org/help/api/user-manual.html  

### NZ primary (docs + probed)
- NZ Legislation — https://www.legislation.govt.nz/ ; API docs — https://api.legislation.govt.nz/docs/  
- Beehive feeds — https://www.beehive.govt.nz/feeds  
- Treasury RSS — https://www.treasury.govt.nz/rss-news-feeds  
- Stats NZ releases — https://www.stats.govt.nz/information-releases  
- RNZ RSS — https://www.rnz.co.nz/rss  
- Te Ara — https://teara.govt.nz/en  
- GeoNet API — https://api.geonet.org.nz/  
- Companies Register — https://companies-register.companiesoffice.govt.nz/  

### Internal
- [`M07_WEB.md`](./M07_WEB.md) — hands, cites, paste-this-turn, RSS hook  
- [`../02_CONSTITUTION.md`](../02_CONSTITUTION.md) — web ring; confirm new host  
- Code: `src/ada/web/allowlist.py`, `src/ada/web/ssrf.py`  
- FACTS: `/mnt/ada-data/memory/facts/prefs.yaml` (`web_allowlist`)

---

### Lens cheat-sheet

| Claim | Lens |
|-------|------|
| Host allowlist + SSRF denylist is the serious default | **EVIDENCE** (OWASP, Claude, Cursor, Progent) |
| Exact host ⇒ list `rss.` / `api.` satellites | **METAL** |
| Personal cites compound; chat-search forgets | **EVIDENCE** + organism vision |
| `*` / whole `.govt.nz` | **FANFICTION** / POLICY reject |
| RBNZ/Parliament in overnight watches today | **Falsified on this Pi** |
| Playwright to “fix” WAF in this card | **Won’t-chase** |
| Funnel so the library is public | **Denied** |
| Seeding FACTS without Aryan | **POLICY** reject |

---

*End of M08. **Doc-only** 2026-08-14: source library + policy on top of M07 metal. No Funnel; no `*`; no localhost; no second crawler.*

---

## If Aryan does one thing next

**Pick a pack to open** — `lab.papers` satellites (`rss.arxiv.org`, `export.arxiv.org`) so the one existing door actually reaches feeds, **or** `nz.law` + Te Ara so NZ claims can grow receipts. Confirm-once. Don’t enable news mills to feel “current.”
