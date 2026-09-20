# M28 — Work-loop case studies (CV drafts · portfolio publish)

**Status:** research start — **design note v1.0** (no Python this card)  
**Date:** 2026-09-20  
**Host:** `ada-pi5` (Raspberry Pi 5, 8 GiB) · windows: Mac / phone via Tailscale Serve  
**Branch:** `rewrite/v1-body`  
**Kind:** **work-organ research** — two named long-running containers as the first case studies. Not life. Not old-`main` pSEO/GSC/S3. Not package.  
**Depends on:** [`M15_INTENT_WORK_LOOP.md`](./M15_INTENT_WORK_LOOP.md) (Plan → Accept → todos; **P2 still deferred**) · [`M06_CAMPAIGNS_LONG_HORIZON.md`](./M06_CAMPAIGNS_LONG_HORIZON.md) (STATUS / stages / `waiting_on_aryan`) · [`M16_FIRST_PACKAGE.md`](./M16_FIRST_PACKAGE.md) (`artifact_write`) · [`M07_WEB.md`](./M07_WEB.md) (fetch + cites; no LinkedIn/Seek scrape) · [`../00_ASSISTANT_RESEARCH.md`](../00_ASSISTANT_RESEARCH.md) §8 · [`../19_JARVIS_JUSTINE_AGENT_RESEARCH.md`](../19_JARVIS_JUSTINE_AGENT_RESEARCH.md) (workflows over tool soup) · operator lock 2026-09-20 (this chat): life = Study A (fast path); work = Study B

**Feeds:** later implement of M15 P2 pieces **only as needed by these two containers**. Does **not** reorder [`M20_V1_PRODUCT.md`](./M20_V1_PRODUCT.md) 1→5. Does **not** start mail, GSC ingest, S3 ISR, or LinkedIn API.

**Name stays `M28_WORK_LOOP_CASE_STUDIES.md`:** the research object is the **loop + two cases**, not a CV SaaS and not a blog CMS. Rejected: stuffing into M15 P2 (too harness-generic); stuffing into M06 (campaigns substrate, not the first jobs); stuffing into M26 (life).

**Supersedes:** any reading that (a) ADA should transplant `main` `publish_keyword_v1` / `isr.md` / GSC ingest as this organ, (b) auto-apply or auto-post is the first work product, (c) life join/Dream is the long-running bet, (d) “rank the portfolio” via a page farm is the publish container. **Does not supersede:** M15 Plan/Accept; M06 STATUS; Confirm Integrity; Verb→Pack for **life**; one Gemini cortex.

### Changelog

| Ver | Date | Delta |
|-----|------|-------|
| **v1.0** | 2026-09-20 | Operator split: Study A = life (M19a–M26, use + later join). Study B = this card. Short market pass. Two cases locked: CV/cover **drafts**; **one** portfolio `/blog` post + LinkedIn **cut** (you ship). |

---

## Two lab studies (don’t mix)

| Study | Organ | What’s true now | This card |
|-------|--------|-----------------|-----------|
| **A — Life** | Diary: capture → retrieve → later analysis | Capture **closed enough** to live on. Join/Dream/SQL = later *read* layer. Miss-path hygiene while using. | **OUT.** Pointer only: [`M26_DOMAIN_KNOWLEDGE.md`](./M26_DOMAIN_KNOWLEDGE.md) |
| **B — Work** | Pause → plan → Accept → one act → STATUS → sleep | Skeleton **METAL** (Plan card, Accept→todos, campaigns YAML, `artifact_write`). Not a product loop yet. | **IN.** Two case studies below |

Life does not become planning. Work does not eat meal/gym packs. Life Dream stays life-only.

---

## Core research question

How should ADA run **two named, multi-session work containers** — (1) **CV/cover drafts** from a source-of-truth corpus + a pasted JD, (2) **one** portfolio-blog post (canonical URL on the portfolio site) plus a LinkedIn **cut** — as **Plan → operator Accept → `artifact_write` on the Pi → `waiting_on_aryan` until the human ships → campaign STATUS**, so the organism **pauses, thinks, and acts across days**, without auto-apply, auto-post, pSEO/GSC page farms, Playwright ATS, or a second runtime?

Secondary (same card, later slices):

| Sub-question | Default until locked |
|--------------|----------------------|
| Where does the blog live? | **`/blog` on the portfolio origin** — not `blog.` subdomain, not demo subdomains |
| Is LinkedIn required? | **Distribution**, not the store. ADA drafts a cut; **you** paste. No LinkedIn API this slice |
| Is GSC required? | **Read later** after ≥1 live URL. Not an ingest organ here |
| CV PDF / LaTeX on Pi? | **Closer, not teacher.** Draft md first; `pdflatex` later if earned |
| Pause-think model? | Same Gemini cortex + **disk plan/STATUS**. No Cowork transplant; no local 7B worker |

---

## §8 gate

| Field | Answer |
|-------|--------|
| **Question / capability** | Durable HITL work loop, proven on two real operator jobs, on existing metal |
| **Lens tags** | **EVIDENCE** (Cowork / ChatGPT Plan / OpenAI HITL serialize; job-hunt HITL vs auto-apply; PR-as-publish) · **FEASIBLE** (Plan + campaign YAML + artifacts on Pi; no new vendor) · **FANFICTION** (unsupervised apply/post; ADA controls GitHub/Vercel) · **POLICY** (Confirm; you ship public; no Seek/LinkedIn scrape) · **METAL** (M15 P0+P1; M06 skeleton; `artifact_write`) |
| **Citations** | ≥2 below |
| **Pi 5 8GB** | **Yes** for draft files + rare Gemini wakes. **No** as Claude Desktop Cowork clone (needs Mac awake + desktop app) |
| **Learning objective** | See whether ADA can leave a **file + STATUS** you actually ship — not whether Gemini can write a blog in one flash turn |
| **Harder-but-correct** | Reuse Plan/Accept + campaigns + artifacts. **Shortcut rejected:** one-shot chat compile; `main` ISR daemon; auto-submit ATS; GSC keyword mill |
| **Won’t-chase (this slice)** | Mail OAuth · LinkedIn/Seek scrape · S3/ISR · DataForSEO · n8n · LangGraph · multi-agent job swarm · pSEO doorway clusters · life join as a gate |
| **Acceptance falsifiers** | F-M28-* |
| **Egress** | **Control:** Tailscale Confirm/Accept. **Cortex:** JD text, draft bodies, optional allowlisted fetch. **Public:** only after **you** publish. Secrets never-to-cloud |

---

## What the market already shipped (short)

The **shape is not novel**. People have built this. ADA’s job is to own it **on this body** (receipts, STATUS, Confirm), not to invent “agent that writes CVs.”

### Work loop (pause / plan / act)

| What | Steal | Refuse |
|------|--------|--------|
| [Claude Cowork](https://claude.com/product/cowork) — multi-step files, scheduled tasks, “ask before acting”; projects as persistent workspaces | Named container + come-back-later | Desktop-must-stay-open as ADA’s clock; sub-agent swarm as default |
| ChatGPT **Plan mode** (approve/edit steps before act) | Plan as a **gate**, not a vibe | Collapsing Observe/Plan/Agent into one “intent mode” |
| [OpenAI Agents SDK HITL](https://openai.github.io/openai-agents-python/human_in_the_loop/) — pause, serialize `RunState`, resume | **Persist the pause** (this is M15 P2 #1/#3) | Adopting the SDK as ADA’s harness |
| Horizon Gap / long-horizon mirage (already in M06/M15) | Goals on **disk**; cap autonomy | “Think harder” overnight as the product |

**ADA METAL vs gap:** Plan card + Accept→todos **shipped**. Persist `plan_id`, pause/resume, todo↔campaign bridge = **P2 deferred**. Case studies should **force those gaps into the open**, not hide them in a new daemon.

### Case 1 — CV / cover drafts

| What | Steal | Refuse |
|------|--------|--------|
| [claude-job-slayer](https://github.com/BowennCAI/claude-job-slayer) (already in M19) — local LaTeX versions; **screenshot Confirm before Submit** | Source-of-truth corpus; HITL before send | Chrome/LinkedIn ToS as v1 actuator |
| Career-ops / job-coach skills (2026) — tailor from a CV corpus; **do not auto-submit** | JD in → draft out; log status | 14-skill Playwright spray; silent apply |
| Huntr/Teal-class trackers | Kanban / STATUS | SaaS as ADA’s store |
| LazyApply / `claude-job-auto-apply`-class | — | **Anti-pattern.** Auto-submit |

**Operator truth:** the CV loop is **almost manual already**. First ADA slice = Plan + artifact drafts (md). Pi LaTeX→PDF = later closer.

### Case 2 — Personal publish

| What | Steal | Refuse |
|------|--------|--------|
| Blogging agents with **`APPROVAL_MODE=pr`** (write → PR → **merge = publish**) | Human ship is the gate | GitHub Actions GSC mill as ADA brain |
| Local review-only chains (draft md; never login to WordPress) | File on disk; you paste | CMS API as v1 |
| Auto-blog-from-coding-session plugins | Optional *topic* cue | Unreviewed posts to a public URL |

**Operator truth:** publish is the **immature** case — that’s why it teaches the loop. Canonical post on **portfolio `/blog`**. Demos stay on subdomains. LinkedIn/Reddit = **cuts that link back**. GSC = later **read**. Old `main` `publish_entity_v1` / GSC / S3 ISR = **won’t-chase** (doorway farm you already walked away from).

---

## First loop (context to start — not implement tonight)

```text
  campaign: portfolio-post-1  (or cv-draft-1)
        │
        v
  Plan (M15)  → you Accept
        │
        v
  Agent: web_fetch? → cites? → artifact_write  (md on Pi)
        │
        v
  STATUS = waiting_on_aryan
        │
        v
  you ship  (portfolio /blog  and/or  paste LinkedIn cut  and/or  send CV)
        │
        v
  STATUS = done  + receipt  (path or URL you typed — not Gemini vibes)
```

**Start with publish** (one real post: ADA rewrite or a shipped demo). CV in parallel as the second container once the STATUS handshake is visible.

---

## Falsifiers

| ID | Fail if… |
|----|----------|
| **F-M28-1** | A public post or job apply happens **without** operator ship / Confirm |
| **F-M28-2** | “Published” claimed from chat with **no** artifact path (and later no URL) |
| **F-M28-3** | GSC/S3/ISR/`publish_keyword_v1` from `main` is copied as this organ |
| **F-M28-4** | Life packs are reopened to “help” the blog or CV |
| **F-M28-5** | LinkedIn/Seek scrape or auto-post becomes the v1 actuator |
| **F-M28-6** | One-shot Gemini essay with **no** campaign STATUS / Accept |

---

## Locks

| Lock | Source |
|------|--------|
| Two studies; don’t mix life into work | **this card** |
| Plan → Accept → artifact → waiting_on_aryan | M15 · M06 · **this card** |
| Portfolio origin owns the canonical post | **this card** |
| You ship public; ADA drafts | POLICY · Consent Integrity |
| No `main` pSEO transplant | M07 · NZ anti-doorway · **this card** |
| Research now; implement after this card’s next slice names metal gaps | §8 · M15 P2 |

---

## Citations (thin)

| Claim | Tag | Pointer |
|-------|-----|---------|
| Cowork = files + scheduled + ask-before-act | **EVIDENCE** | https://claude.com/product/cowork |
| HITL pause must serialize | **EVIDENCE** | https://openai.github.io/openai-agents-python/human_in_the_loop/ |
| Job HITL before submit | **EVIDENCE** | https://github.com/BowennCAI/claude-job-slayer · M19 |
| Horizon / false completion | **EVIDENCE** | Horizon Gap · M06 |
| ADA Plan/Accept + artifacts | **METAL** | M15 · `artifact_write` |
| Old publish daemon | **METAL** (other branch) | `main` `docs/c4/3-components/publish-workflows.md` |

---

**Next:** use life (Study A). **This card stays research** until a follow-on slice lists the exact M15 P2 bits required for `portfolio-post-1` (persist plan / STATUS handshake). Do not implement GSC, LinkedIn API, or LaTeX this week.

*End M28 v1.0 — two case studies; drafts on disk; you ship; loop is the product.*
