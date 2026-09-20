# M28 — Work-loop case studies (CV drafts · portfolio publish)

**Status:** **Layer A metal shipped** (v1.2) — shared work-loop pin / handshake / operator-ship receipt. Layer B (per-container stages) still research.  
**Date:** 2026-09-20  
**Host:** `ada-pi5` (Raspberry Pi 5, 8 GiB) · windows: Mac / phone via Tailscale Serve  
**Branch:** `rewrite/v1-body`  
**Kind:** **work-organ research** — two named long-running containers as the first case studies. Not life. Not old-`main` pSEO/GSC/S3. Not package.  
**Depends on:** [`M15_INTENT_WORK_LOOP.md`](./M15_INTENT_WORK_LOOP.md) (Plan → Accept → todos; **P2 #1/#2 thin metal via Layer A**) · [`M06_CAMPAIGNS_LONG_HORIZON.md`](./M06_CAMPAIGNS_LONG_HORIZON.md) (STATUS / stages / `waiting_on_aryan`) · [`M16_FIRST_PACKAGE.md`](./M16_FIRST_PACKAGE.md) (`artifact_write`) · [`M07_WEB.md`](./M07_WEB.md) (fetch + cites; no LinkedIn/Seek scrape) · [`../00_ASSISTANT_RESEARCH.md`](../00_ASSISTANT_RESEARCH.md) §8 · [`../02_CONSTITUTION.md`](../02_CONSTITUTION.md) (Confirm Integrity, modes, quiet hours, no Funnel) · [`../19_JARVIS_JUSTINE_AGENT_RESEARCH.md`](../19_JARVIS_JUSTINE_AGENT_RESEARCH.md) (workflows over tool soup) · operator lock 2026-09-20: life = Study A (fast path); work = Study B

**Feeds:** later implement of **exactly** the M15 P2 pieces `portfolio-post-1` needs (§8). Does **not** reorder [`M20_V1_PRODUCT.md`](./M20_V1_PRODUCT.md) 1→5. Does **not** start mail, GSC ingest, S3 ISR, or LinkedIn API.

**Name stays `M28_WORK_LOOP_CASE_STUDIES.md`:** the research object is the **loop + two cases**, not a CV SaaS and not a blog CMS. Rejected: stuffing into M15 P2 (too harness-generic); stuffing into M06 (campaigns substrate, not the first jobs); stuffing into M26 (life). **Do not create M29.**

**Supersedes:** any reading that (a) ADA should transplant `main` `publish_keyword_v1` / `isr.md` / GSC ingest as this organ, (b) auto-apply or auto-post is the first work product, (c) life join/Dream is the long-running bet, (d) “rank the portfolio” via a page farm is the publish container. **Does not supersede:** M15 Plan/Accept; M06 STATUS; Confirm Integrity; Verb→Pack for **life**; one Gemini cortex. **Does not reopen v1.0 locks.**

### Changelog

| Ver | Date | Delta |
|-----|------|-------|
| **v1.0** | 2026-09-20 | Operator split: Study A = life (M19a–M26, use + later join). Study B = this card. Short market pass. Two cases locked: CV/cover **drafts**; **one** portfolio `/blog` post + LinkedIn **cut** (you ship). |
| **v1.1** | 2026-09-20 | Full research card: two layers (shared loop vs per-container stages); SOTA ≥8 2025–26 HITL/durable; PICK reuse Plan/Accept + campaign YAML + `artifact_write`; M15 P2 mapped to `portfolio-post-1`; OPEN≤5 with defaults; metal gaps named in order. v1.0 locks held. **Research-only** — no thin P0 in this chat. |
| **v1.2** | 2026-09-20 | **Layer A metal shipped:** persist `plan_id` on campaign; thin todo↔campaign pin; `artifact_write` handshake → `waiting_on_aryan`; operator-typed ship receipt Confirm-gated `done` (F-M28-7/8). Layer B still research. No `portfolio-post-1` / `cv-draft-1` campaigns this slice. |

---

## Two lab studies (don’t mix)

| Study | Organ | What’s true now | This card |
|-------|--------|-----------------|-----------|
| **A — Life** | Diary: capture → retrieve → later analysis | Capture **closed enough** to live on. Join/Dream/SQL = later *read* layer. Miss-path hygiene while using. | **OUT.** Pointer only: [`M26_DOMAIN_KNOWLEDGE.md`](./M26_DOMAIN_KNOWLEDGE.md) |
| **B — Work** | Pause → plan → Accept → one act → STATUS → sleep | Skeleton **METAL** (Plan card, Accept→todos, campaigns YAML, `artifact_write`). Not a product loop yet. | **IN.** Two case studies below |

Life does not become planning. Work does not eat meal/gym packs. Life Dream stays life-only.

---

## Core research question

**(Locked — v1.0. Do not replace.)**

How should ADA run **two named, multi-session work containers** — (1) **CV/cover drafts** from a source-of-truth corpus + a pasted JD, (2) **one** portfolio-blog post (canonical URL on the portfolio site) plus a LinkedIn **cut** — as **Plan → operator Accept → `artifact_write` on the Pi → `waiting_on_aryan` until the human ships → campaign STATUS**, so the organism **pauses, thinks, and acts across days**, without auto-apply, auto-post, pSEO/GSC page farms, Playwright ATS, or a second runtime?

Secondary (same card, later slices — defaults **locked** v1.0):

| Sub-question | Default until locked |
|--------------|----------------------|
| Where does the blog live? | **`/blog` on the portfolio origin** — not `blog.` subdomain, not demo subdomains |
| Is LinkedIn required? | **Distribution**, not the store. ADA drafts a cut; **you** paste. No LinkedIn API this slice |
| Is GSC required? | **Read later** after ≥1 live URL. Not an ingest organ here |
| CV PDF / LaTeX on Pi? | **Closer, not teacher.** Draft md first; `pdflatex` later if earned |
| Pause-think model? | Same Gemini cortex + **disk plan/STATUS**. No Cowork transplant; no local 7B worker |

**Case-study order (locked):** start with **one** portfolio post; CV drafts **second**. Blog lives at `/blog` on the portfolio origin. **You** ship public.

---

## §8 gate

| Field | Answer |
|-------|--------|
| **Question / capability** | Durable HITL work loop, proven on two real operator jobs, on existing metal |
| **Lens tags** | **EVIDENCE** (Horizon Gap / Mirage; Anthropic workflows; OpenAI HITL serialize; Cowork vs Pi clocks; ChatGPT Plan; InfiAgent files; job-hunt HITL vs auto-apply; PR-as-publish vs GSC mill) · **FEASIBLE** (Plan + campaign YAML + artifacts on Pi; no new vendor) · **FANFICTION** (unsupervised apply/post; ADA controls GitHub/Vercel; Cowork-on-Pi) · **POLICY** (Confirm; you ship public; no Seek/LinkedIn scrape; no Funnel) · **METAL** (M15 P0+P1; M06 skeleton; `artifact_write`) |
| **Citations** | ≥8 tagged SOTA rows + internals below |
| **Pi 5 8GB** | **Yes** for draft files + rare Gemini wakes + YAML STATUS. **No** as Claude Desktop Cowork clone (Mac awake + desktop app, or Anthropic cloud session — wrong body). **No** as local 7B overnight worker |
| **Learning objective** | See whether ADA can leave a **file + STATUS** you actually ship across days — not whether Gemini can write a blog in one flash turn. After this card: name Accept vs Confirm vs operator-ship; name which M15 P2 bits `portfolio-post-1` needs; refuse a second runtime |
| **Harder-but-correct** | Reuse Plan/Accept + campaigns + artifacts. **Shortcut rejected:** one-shot chat compile; `main` ISR daemon; auto-submit ATS; GSC keyword mill; Cowork/LangGraph/n8n/Celery as brain |
| **Won’t-chase (this slice)** | Mail OAuth · LinkedIn/Seek scrape · S3/ISR · DataForSEO · n8n · LangGraph · Celery · multi-agent job swarm · pSEO doorway clusters · Playwright ATS · auto-apply · auto-post · GSC ingest · Pi LaTeX as a gate · life join as a gate |
| **Acceptance falsifiers** | F-M28-* |
| **Egress** | **Control:** Tailscale Confirm/Accept. **Cortex:** JD text, draft bodies, optional allowlisted fetch. **Public:** only after **you** publish. Secrets never-to-cloud |

**This card’s Layer A is metal.** Layer B (stage lists / first real campaign) is still a later coding slice. Implement-next (§16) items 1–3 done; 4–6 still later.

---

## Two layers (keep distinct)

| Layer | Owns | Does not own |
|-------|------|----------------|
| **A — Shared work loop** | Persist plan, STATUS lifecycle, `waiting_on_aryan`, when to use Plan **Accept** vs **Confirm** vs **operator-ship**, receipts, wake (user-open vs timer), budgeted campaign slice into Gemini. Research **once**. | CV wording. Blog CMS. Per-job schemas |
| **B — Per container** | **Stages / slots / gates only** on the *same* campaign schema. CV: JD in → draft md → you send. Publish: draft md → you paste `/blog` (+ optional `linkedin.md`) | A second runtime. A new YAML dialect per workflow |

**POLICY:** one shared organ (`kind: campaign` on `open_loops.yaml`). Different **stage lists**. No inventing a schema per job.

```text
  Layer A (shared, across days)
  ─────────────────────────────────────────────────────────
  campaign YAML (STATUS + stages + last_receipt [+ plan_id])
        │
        ├── wake: you open ADA  OR  optional brief timer
        ├── Gemini sees budgeted HEAD only (not week of chat)
        ├── M15 INNER loop (minutes): utterance → Plan → Accept → execute → receipt
        ├── after ADA's act: STATUS = waiting_on_aryan
        └── after YOU ship: operator-typed URL/path → STATUS = done

  Layer B (narrow, per container)
  ─────────────────────────────────────────────────────────
  portfolio-post-1 stages:  draft_md → you_paste_blog → [linkedin_cut]
  cv-draft-1 stages:        jd_in    → draft_md       → you_send
```

M15 is the **INNER** loop. This card is **ACROSS DAYS**. Do not extend M15’s minutes loop here.

---

## ≤5 concepts (work, not daemon)

Same five as M06 — applied to these two jobs. Do not add a sixth.

| # | Concept | Meaning here |
|---|---------|--------------|
| **1. Campaign** | Named container: `portfolio-post-1` or `cv-draft-1`. Lives on disk. |
| **2. STATUS** | `active` / `blocked` / `waiting_on_aryan` / `paused` / `done` / `failed`. Truth = file + receipts, not chat. |
| **3. Stages** | Ordered checklist **inside** that campaign. Layer B only changes this list. |
| **4. Wake** | ADA looks when **you open**, or on a **scheduled brief** (same shape as Dream). Between wakes: **idle**. Pi clocks — not “desktop must stay open.” |
| **5. Gate** | Risky next step pauses. **Accept** ≠ **Confirm** ≠ **you ship.** |

**One sentence:** *ADA drafts a file, writes STATUS, sleeps; you ship; you type the URL; she marks done.*

---

## Lens tags

| Tag | Meaning here |
|-----|----------------|
| **FANFICTION** | Unsupervised multi-day apply/post; ADA owns GitHub/Vercel; Cowork-on-Pi; “think harder overnight”; life join as the work loop |
| **EVIDENCE** | Papers; shipping product docs; honest HITL repos vs auto-apply / GSC mills |
| **FEASIBLE** | Pi 5 8GB; Gemini cortex; YAML + md on HDD; Tailscale HUD; no second runtime |
| **POLICY** | Confirm Integrity; you ship public; no Funnel; quiet hours; no LinkedIn/Seek scrape |
| **METAL** | What exists in *this* repo **today** (2026-09-20 inspect) |

---

## Honest METAL inventory (2026-09-20; Layer A v1.2)

Inspected / shipped: `harness/plan_artifact.py`, `hud/chat_service.py` `accept_plan`, `memory/open_loops.py`, `tools/artifact_tools.py` / `memory/artifacts.py`.

| Piece | Truth | Tag |
|-------|--------|-----|
| Plan card (structured `steps[]`, `plan_id`) after Plan turn | **Shipped** — parse in `plan_artifact.py`; SSE + JSONL | **METAL** |
| `POST /api/plan/accept` → `kind:todo` | **Shipped** — no cortex, no write tools | **METAL** |
| Plan↔Agent history preserve (same session) | **Shipped** (M15 P1) | **METAL** |
| `plan_id` persisted to ada-data / resume after HUD restart | **METAL** — pin on campaign row (`open_loops.upsert_loop` / `memory_open_loops_upsert`); heads via `format_campaign_head`. No `plans/*.yaml` | **METAL** |
| Todo ↔ campaign link (`plan_id` / campaign id on todos) | **METAL (thin)** — Accept + todo upsert pin `campaign_id` and/or `plan_id`; stages remain campaign truth | **METAL** |
| Mid-ReAct pause/serialize (SDK `RunState`) | **ABSENT** — Confirm is post-tool, not a frozen loop | **METAL** gap |
| `kind: campaign` STATUS enum includes `waiting_on_aryan` | **Shipped** — `open_loops.CAMPAIGN_STATUSES`; boot heads prefer it | **METAL** |
| Handshake: after `artifact_write`, STATUS → `waiting_on_aryan` | **METAL** — optional `campaign_id` / `next_stage` / `waiting_reason` on `artifact_write` → `open_loops.handshake_after_artifact` | **METAL** |
| `last_receipt` / `last_progress_at` on campaign | **Shipped** as fields; handshake auto-wires draft path; ship receipt is operator-typed | **METAL** |
| Operator-typed “I shipped” URL/path as the done receipt | **METAL** — `waiting_on_aryan` → `done` needs Confirm + URL or `sent to …`; draft `artifacts/` path is not ship proof (`_ship_pause_done_gate`, F-M28-7) | **METAL** |
| `artifact_write` md/csv under `artifacts/`, overwrite Confirm | **Shipped** (M16) | **METAL** |
| Campaign heads on boot (≤K=3); `due_campaigns` surfaces waiting/blocked | **Shipped** (M06) | **METAL** |
| Quiet hours 23:00–05:30 NZST; heal-first | **Shipped** constitution | **POLICY** / **METAL** |
| Playwright ATS / LinkedIn API / GSC ingest / Pi `pdflatex` | **ABSENT** — and **refuse** as v1 actuators | **POLICY** |

**Verdict:** Plan card + Accept→todos **shipped**. Persist `plan_id`, handshake `waiting_on_aryan`, and operator-typed ship receipt are **Layer A metal** (v1.2). Mid-ReAct serialize and intent router remain **ABSENT**. Case studies (Layer B) still do not exist as real campaigns.

---

## SOTA (2025–2026) — long-running / HITL / durable state

Not CV-SaaS reviews. Every row tagged. Steal/refuse for **this** metal. Contradict slogans where products claim unsupervised multi-day and papers measure false-completion.

| # | Source | Claim | Steal | Refuse | Tag |
|---|--------|-------|-------|--------|-----|
| 1 | **Horizon Gap** (2026) — [arXiv:2608.06663](https://arxiv.org/abs/2608.06663) | Long-horizon ≠ long-context ≠ long-term memory. Failures: planning drift, **false completion** (“declaring a half-finished job done”), lost decisions. Outcome-only signals go uninformative as horizon grows | Goals + STATUS on **disk**; receipts over vibes; cap autonomy per wake | “Bigger Gemini window = multi-day work.” Overnight CoT as the product | **EVIDENCE** |
| 2 | **Long-Horizon Task Mirage** (2026) — [arXiv:2604.11978](https://arxiv.org/abs/2604.11978) | SOTA agents (GPT-5 family, Claude) **nonlinear collapse** as interdependent horizon grows; taxonomy includes planning error, forgetting, history accumulation, **false assumptions** | Stage lists; discard bloated chat between wakes; one honest step | Unsupervised “finish the blog while I sleep” | **EVIDENCE** |
| 3 | **Anthropic, Building Effective Agents** (2024) — [eng post](https://www.anthropic.com/engineering/building-effective-agents) | **Workflows** (code-owned paths + gates) vs **agents** (model directs the loop). Simplest solution first; transparency of planning | Layer A = workflow around one ReAct agent. Plan Accept is a gate. Stages are the path | LangGraph/n8n/Celery as ADA’s runtime; multi-agent swarm as default | **EVIDENCE** · **FEASIBLE** |
| 4 | **OpenAI Agents SDK HITL** — [HITL guide](https://openai.github.io/openai-agents-python/human_in_the_loop/) | Pause on `needs_approval`; serialize `RunState`; resume the **same** run after approve/reject | **Persist the pause.** For ADA: disk STATUS + `plan_id`, not chat hope. Confirm already re-executes without cortex | Adopting the SDK as the harness; serializing mid-ReAct for `portfolio-post-1` (pause is at **stage** boundary, not inside a tool loop) | **EVIDENCE** · **FEASIBLE** as pattern |
| 5 | **Claude Cowork** — [product](https://claude.com/product/cowork) · [projects](https://support.claude.com/en/articles/14116274-organize-your-tasks-with-projects-in-claude-cowork) · [get started](https://support.claude.com/en/articles/13345190-get-started-with-claude-cowork) | Named **projects** (folders, instructions, memory). Scheduled tasks. **Ask before acting**. Marketing: “Close your laptop, it keeps going.” Help text: **local** file/browser tasks still need Desktop **open and the machine awake**; remote cloud sessions are a different product | Named container + come-back-later + ask-before-acting | **Desktop-must-stay-open as ADA’s clock** (**FEASIBLE** fail — Pi is the clock). Sub-agent swarm. Transplanting Cowork as runtime. Treating slogan “unattended laptop-closed local files” as true | **EVIDENCE** (product) · **FANFICTION** if copied onto Pi |
| 6 | **ChatGPT Plan / Work** — [Work](https://chatgpt.com/work/) · [long-running work](https://learn.chatgpt.com/docs/long-running-work.md) | Plan mode: gather context, ask, **approve the plan before work**. Execution still pauses for send/publish. Goal includes **verification** criteria, not just activity | Plan as a **gate**, not a vibe. “Shipped” needs a check you can name (URL/path you typed) | Collapsing Observe/Plan/Agent into one “intent mode.” Cloud Work as ADA’s body | **EVIDENCE** |
| 7 | **InfiAgent** (2026) — [arXiv:2601.03204](https://arxiv.org/abs/2601.03204) · [repo](https://github.com/polyuiislab/infiAgent) | File-centric workspace = **authoritative** progress; bounded thinking record; resume from checkpoint, not full dialogue replay. Repo slogan: “Days-Long Complex Tasks” without compression | `artifacts/` + campaign YAML as the workspace; wake loads snapshot + last receipt, not the week’s chat | Repo’s **unsupervised days-long** claim — papers (rows 1–2) measure **false-completion**. Hierarchical multi-agent stack. `infiagent` as a pip dependency | **EVIDENCE** (files) · **FANFICTION** (unattended days) |
| 8 | **Job-hunt HITL vs auto-apply** — [claude-job-slayer](https://github.com/BowennCAI/claude-job-slayer) vs LazyApply-class (2026 reviews: incomplete submit, bot detection) | Slayer: local CV corpus + tailor + **screenshot Confirm before Submit** (hard-wired). Auto-apply: volume without per-app human gate; delivery lies | Source-of-truth corpus; JD in → draft out; HITL before **send**; tracker STATUS | Chrome/LinkedIn ToS as v1 actuator; Playwright ATS; silent apply; 14-skill spray. **Anti-pattern:** LazyApply / `claude-job-auto-apply` | **EVIDENCE** · **POLICY** refuse auto-apply |
| 9 | **Publish HITL vs GSC mill** — [blogging-agent `APPROVAL_MODE=pr`](https://github.com/vipulawl/blogging-agent) vs `@stayboba/autoblog` / GSC→CMS pipelines | Honest: write md → **PR** (or local file); **merge / paste = publish**. Mill: GSC mines keywords → auto `cmsPublish` on a cadence | Human ship is the gate. File on disk; you paste `/blog` | GitHub Actions GSC mill as ADA brain; doorway farms; `main` `publish_keyword_v1` / ISR. ADA does **not** own merge-to-Vercel on this branch — analogue of merge is **you paste** | **EVIDENCE** · **POLICY** |
| 10 | **LongHorizon-Harness MEA** (2026) — [arXiv:2608.01964](https://arxiv.org/abs/2608.01964) | Manage–Execute–Audit: **verified task state outside** the executor; fresh-context executor; discard interaction history each round; auditor inspects the environment | Wake = manage (read STATUS); Agent turn = execute **one** stage; “audit” = receipt (`artifact_write` path, later operator-typed URL) — **code**, not a second critic-agent | Three-model MEA swarm on Pi 8GB; OSWorld-class computer-use | **EVIDENCE** · **FEASIBLE** as *roles in one harness* |

**EVIDENCE verdict:** production-grade multi-day work is **externalized state + stage gates + a human ship**, not a smarter overnight prompt. Products that advertise unsupervised multi-day still pause for publish/submit — or they fail silently (false-completion, failed ATS delivery).

**FANFICTION reject:** “ADA will apply and post while I sleep, and Gemini will know it’s done.”

---

## PICK — harder-correct on this metal

**Reuse M15 Plan/Accept + M06 campaign YAML + `artifact_write`.** Same Gemini cortex. Plan turn + **disk** state. No second cortex unless a later card shows **EVIDENCE+FEASIBLE** (none today).

| Option | How | Verdict |
|--------|-----|---------|
| **A. One-shot chat** | Gemini writes the post/CV in the thread; you copy | **Reject** — Horizon Gap; no STATUS; false “published” |
| **B. Cowork / ChatGPT Work as ADA** | Desktop/cloud project runner | **Reject** — wrong body; desktop-open or vendor cloud; not Tailscale HUD |
| **C. LangGraph / n8n / Celery / swarm** | Second runtime | **Reject** — constitution; M06 lock; Pi ops tax |
| **D. Transplant `main` publish/GSC/S3/ISR** | Page farm | **Reject** — v1.0 lock; anti-doorway; wrong organ |
| **E. Reuse Plan + campaign + artifacts** | Inner M15 loop; across-days M06 STATUS; files on HDD | **PICK** |

**Missing metal, in order** (what `portfolio-post-1` actually needs):

1. **Persist `plan_id`** on the campaign — **METAL v1.2** (`open_loops` pin; no `plans/*.yaml`).  
2. **STATUS handshake `waiting_on_aryan`** after `artifact_write` — **METAL v1.2**.  
3. **Receipt that “shipped” is operator-typed URL/path** — **METAL v1.2** (Confirm-gated; draft path ≠ ship).

Mid-ReAct `RunState` serialize (M15 P2 #3) and an intent router (P2 #4) are **not** required to start `portfolio-post-1`. Pause across days is a **stage** pause.

Default think-model: **same Gemini**, Plan turn + disk. No local 7B worker. No Cowork.

---

## Layer A — shared work loop (research once)

### A.1 Inner minutes vs across days

| Horizon | Owner | Loop |
|---------|-------|------|
| **Minutes** | M15 | utterance → Plan → Accept → execute → receipt |
| **Hours / days** | **this card** using M06 metal | wake → budgeted head → (optional Plan) → one Agent act → STATUS → idle |

Do not fold days into a longer Plan card. Do not keep an immortal chat as the campaign.

### A.2 Persist plan

**Today:** `plan_id` is minted per Plan turn, shown on the card, written to JSONL, held in `ChatService.last_plan`. Process restart / new session → gone.

**Need:** the campaign record carries `plan_id` (OPEN-1 default) so Observe can answer “where is portfolio-post-1?” from YAML. Steps stay in JSONL / last Plan body; **do not** invent `plans/*.yaml` this slice (M15 OPEN already locked SSE+JSONL for Tier A). Pin, don’t fork a second plan store.

Resume = load campaign head + current stage + `plan_id` + last artifact path. Not replay of the week.

### A.3 STATUS lifecycle (shared)

```text
  [create campaign] → active
        │
        v
  Plan (optional if stages already known) → Accept
        │
        v
  Agent: one stage (fetch? cites? artifact_write)
        │
        v
  STATUS = waiting_on_aryan     ← ADA's act is done; human's is not
        │
        v
  you ship  (paste /blog  ·  paste LinkedIn  ·  send CV)
        │
        v
  you type URL or path  → Confirm-gated upsert
        │
        v
  STATUS = done  + last_receipt = operator string
```

Also: `blocked` (missing JD / missing corpus), `paused` (operator chill), `failed` (abandoned — Confirm).

**False-completion rule (EVIDENCE rows 1–2, POLICY epistemics):** Agent must not mark `you_paste_blog` / `you_send` `done` because the draft “looks finished.” Those stages complete only with an **operator-typed** receipt.

### A.4 `waiting_on_aryan`

**METAL today:** enum + boot priority + `due_campaigns` reason.

**Handshake (design):** after a successful `artifact_write` for the draft stage:

- `current_stage` → the human-ship stage  
- `status` → `waiting_on_aryan`  
- `blocked_reason` → short instruction (“paste `artifacts/work/portfolio-post-1/post.md` to `/blog`”)  
- `last_receipt` → artifact crumb path  

Quiet hours: **no** user-facing nudge 23:00–05:30; the STATUS still sits on disk. Morning brief / user-open surfaces it (**POLICY**).

### A.5 Accept vs Confirm vs operator-ship

Three different binds. Do not collapse them. (**POLICY** / Consent Integrity — [arXiv:2606.02668](https://arxiv.org/abs/2606.02668); M15 lock: Accept ≠ tool consent.)

| Bind | What it authorizes | What it does **not** |
|------|--------------------|----------------------|
| **Plan Accept** | Policy transition Plan→Agent; materialize `kind:todo` steps for **this** inner loop | Write artifacts; publish; apply; flip campaign to `done` |
| **Confirm** | Gateway `{tool, args}` — `artifact_write` overwrite; campaign `done`/`failed` without receipt; gated stage `done` | Rubber-stamp a model summary; invent a public URL |
| **Operator-ship** | The human **does** the public act (paste `/blog`, paste LinkedIn, send the CV). Then **types** the URL or “sent to Acme via email” | ADA fetching the live page as proof; ADA logging into WordPress/GitHub/ATS |

Operator-ship is **not** a fourth mode. It is a **receipt class**: the string comes from Aryan. Agent may upsert it onto the campaign only under Confirm (or a later thin `ship` helper that is still Confirm-bound). Gemini must not autocomplete `https://…` from wishful thinking.

### A.6 Receipts

| Event | Receipt | Tag |
|-------|---------|-----|
| Draft written | `artifact_write` return path + crumb under `runs/` | **METAL** |
| Campaign progress | `last_receipt` pointer (field exists) | **METAL** field / **ABSENT** auto-wire |
| Public ship | **Operator-typed** canonical URL or “sent via …” | design |
| “Published” in chat with neither | **Fail F-M28-2** | **POLICY** |

### A.7 Wake

| Trigger | Use | Not |
|---------|-----|-----|
| **User-open** (default) | Boot injects ≤K campaign heads; `waiting_on_aryan` first | Replay full drafts into every turn |
| **Timer / morning brief** | Same `ada-brief` / campaign-check shape as M06; outside quiet hours | Cowork “Desktop must be open.” Pi is already always-on |
| **Dream ~03:30** | May refresh heads; **never** auto-`done` | Overnight unsupervised write/post |

**FEASIBLE:** YAML wake is cheap. Always-on Gemini loop fights 8GB + token anti-metrics.

### A.8 Budgeted campaign slice into Gemini

Reuse M06: head ≤~200–400 tokens × K=3–5.

Include: `id`, title, STATUS, `current_stage`, `blocked_reason`, `plan_id` (once pinned), `last_receipt` (path or URL).

**Do not** include: full post body, CV corpus, week of `runs/`. Agent **reads the artifact file** only when the turn is a revise/ship-check.

### A.9 M15 P2 → what `portfolio-post-1` needs

| M15 P2 | Needed for `portfolio-post-1`? | Why |
|--------|--------------------------------|-----|
| **#1 Persist plans; resume by `plan_id`** | **Yes — first missing metal → METAL v1.2 (campaign pin)** | Else day-2 session amnesia |
| **#2 Link todos ↔ campaign stages** | **Yes — thin → METAL v1.2** | Accept todos are minutes-work; campaign stages are days-work. Pin `campaign_id` (or `plan_id`) on todos **or** skip todo dual-write and treat stages as truth after first Accept |
| **#3 Mid-loop pause/resume (SDK-like)** | **No for v1 of this container** | Pause is `waiting_on_aryan` after `artifact_write`, not a frozen ReAct stack |
| **#4 Intent router beyond heuristics** | **No** | Operator already knows this is work; dial Plan/Agent |

Do not implement the rest of P2 “while we’re here.”

---

## Layer B — per container (stages / slots / gates only)

Same campaign schema. Different stage lists. **Start with publish.**

### B.1 `portfolio-post-1` (first)

**Slots:** topic (operator names it — ADA rewrite or a shipped demo); draft md; optional LinkedIn cut; canonical URL (empty until you type it).

| Stage id | State machine | Gate | ADA does | You do |
|----------|---------------|------|----------|--------|
| `draft_md` | pending → active → done | Confirm only on **overwrite** of existing artifact | Optional allowlisted `web_fetch` + cites; `artifact_write` `artifacts/work/portfolio-post-1/post.md` | Review the file |
| `you_paste_blog` | pending → active → done | **Operator-ship** then Confirm-upsert | Set `waiting_on_aryan`; remind on wake | Paste to **`/blog` on the portfolio origin**; type the live URL |
| `linkedin_cut` | pending → skipped \| done | Optional; skip allowed | `artifact_write` `…/linkedin.md` (cut that **links back** to canonical URL) | Paste into LinkedIn yourself |

**Won’t:** auto-post; GSC ingest; pSEO clusters; ADA pushing git/Vercel; Reddit bots.

### B.2 `cv-draft-1` (second)

**Slots:** source-of-truth corpus on disk (operator-maintained md/LaTeX *sources*, not a scrape); pasted JD (chat or `jd.md`); draft CV md; draft cover md; send-receipt.

| Stage id | State machine | Gate | ADA does | You do |
|----------|---------------|------|----------|--------|
| `jd_in` | pending → done | none beyond Agent write | Store pasted JD as artifact | Paste the JD (no Seek/LinkedIn scrape) |
| `draft_md` | pending → done | overwrite Confirm | Tailor CV + cover **md** from corpus + JD | Review |
| `you_send` | pending → done | **Operator-ship** | `waiting_on_aryan` | You send (email/ATS UI); type “sent to … on …” |

**Won’t:** auto-apply; Playwright ATS; Chrome ToS; Pi `pdflatex` as a **gate** (closer later). Huntr/Teal-class kanban = STATUS we already have, not a SaaS.

### B.3 Illustrative YAML (design — not code)

Fields that exist today stay. `plan_id` is the only proposed shared pin (OPEN-1).

```yaml
# design sketch — not implemented this chat
id: portfolio-post-1
kind: campaign
title: "Portfolio post 1"
status: waiting_on_aryan
plan_id: plan_ab12cd34ef56          # METAL v1.2 — pin on campaign row
stages:
  - id: draft_md
    state: done
  - id: you_paste_blog
    state: active
    gate: confirm
  - id: linkedin_cut
    state: pending
current_stage: you_paste_blog
blocked_reason: "paste artifacts/work/portfolio-post-1/post.md to /blog"
cadence: on_open_only
last_receipt: "artifacts/work/portfolio-post-1/post.md"
# after ship:
# last_receipt: "https://<portfolio-origin>/blog/<slug>"  # operator-typed
```

---

## Egress / trust rings

| Path | Ring | Notes |
|------|------|--------|
| HUD Accept / Confirm | Control (Tailscale) | Session auth for Agent writes |
| Plan/Agent turns (JD, drafts, heads) | Cortex (Gemini) | Budgeted; drafts may contain career PII — accepted hybrid, not “private” |
| Optional `web_fetch` for post cites | Web GET allowlist | No LinkedIn/Seek scrape (**POLICY** / M07) |
| `dream.push` | Backup | Irrelevant to publish; do not piggyback ISR |
| Public URL | **You** | ADA does not POST the blog or ATS |

---

## Learning objective (lab)

After this card (and a later thin implement):

1. Why **minutes** (M15) and **days** (this card) are different loops sharing organs.  
2. Why **Accept ≠ Confirm ≠ operator-ship**.  
3. Why `waiting_on_aryan` without an operator-typed URL is how false-completion sneaks in.  
4. Why Cowork’s laptop-closed slogan is **not** ADA’s clock (**FEASIBLE** / product vs help-doc split).  
5. Why a GSC mill and an auto-applier are anti-patterns even when they “work.”

---

## OPEN for Aryan — **≤5** (defaults until you override)

Architecture is pickable without these. Taste only. Non-questions are locks.

| # | Question | Default |
|---|---------|---------|
| **1** | Where does `plan_id` live? | **Pin `plan_id` on the campaign record**; keep Plan JSONL as audit. **No** `plans/*.yaml` this slice |
| **2** | How does operator-ship enter the file? | Aryan **types** the live URL or “sent to …” in chat; Agent Confirm-upserts `last_receipt` + `done`. No live-page fetch as a gate |
| **3** | Wake cadence for these two campaigns? | **`on_open_only`** + existing brief heads. No new timer |
| **4** | Artifact layout? | `artifacts/work/<campaign_id>/post.md` (and `linkedin.md` / `cv.md` / `cover.md` / `jd.md`) — not a dated slug salad |
| **5** | LinkedIn cut vs separate campaign? | **Optional stage** on `portfolio-post-1`, skippable. Not a second campaign |

Non-questions: no swarm; no Funnel; no local main cortex; no auto-apply/post; no GSC ingest; no `main` transplant; no life join; no M29; no M15 minutes-loop rewrite; no M06 schema fork per workflow.

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
| **F-M28-7** | Campaign `done` without an **operator-typed** URL/path (Gemini-invented “https://…” counts as fail) |
| **F-M28-8** | HUD restart / new session cannot find `portfolio-post-1` STATUS from disk (plan/STATUS amnesia) |
| **F-M28-9** | Cowork / LangGraph / n8n / Celery / multi-agent swarm adopted as the work runtime |
| **F-M28-10** | Pi LaTeX, GSC ingest, mail OAuth, or Playwright ATS becomes a **gate** for the first post |

F-M28-1…6 are **v1.0** (held). 7–10 close v1.1 gaps.

---

## Locks

| Lock | Source |
|------|--------|
| Two studies; don’t mix life into work | **v1.0** |
| Plan → Accept → artifact → `waiting_on_aryan` | M15 · M06 · **v1.0** |
| Portfolio origin owns the canonical post (`/blog`) | **v1.0** |
| You ship public; ADA drafts | **POLICY** · Consent Integrity · **v1.0** |
| LinkedIn = cut, not store; no LinkedIn API this slice | **v1.0** |
| Start with **one** portfolio post; CV second | **v1.0** |
| No `main` pSEO transplant | M07 · NZ anti-doorway · **v1.0** |
| Shared campaign organ; per-container **stages only** | **v1.1** |
| Same Gemini; no second cortex / Cowork runtime | **v1.1** · constitution |
| Accept ≠ Confirm ≠ operator-ship | M15 · **v1.1** |
| Missing metal order: persist `plan_id` → handshake `waiting_on_aryan` → operator-typed ship receipt | **v1.1** |
| Research now; implement is a **later** slice (no thin P0 this chat) | §8 · M15 P2 — **Layer A implemented v1.2**; Layer B still later |

---

## Ordered “research done → implement next”

**This chat: stop** after Layer A metal. No life-pack edits. No `main` transplant. No Layer B campaigns.

Later coding slice (still not this card’s job), in order:

1. Pin `plan_id` on campaign upsert (OPEN-1). Smoke: HUD restart still reports STATUS from YAML (F-M28-8). **Done (v1.2).**  
2. After draft `artifact_write`, set `waiting_on_aryan` + `blocked_reason` + `last_receipt` (handshake). **Done (v1.2).**  
3. Operator-typed ship string → Confirm-gated `done` (F-M28-7). **Done (v1.2).**  
4. Charter/recipe for the two stage lists (Layer B) — not a new schema.  
5. Create `portfolio-post-1` as the first real campaign; write one post to disk; **you** paste `/blog`.  
6. Only then: `cv-draft-1` with a pasted JD.  
7. **Stop before:** GSC, LinkedIn API, LaTeX-as-gate, mail OAuth, Playwright, second runtime.

---

## Relationship to other cards

| Card | Owns | Boundary with M28 |
|------|------|-------------------|
| **M15** | Inner minutes loop (utterance → Plan → Accept → execute → receipt) | **Do not extend** that loop here. Consume P2 **#1 and thin #2** only as named in §A.9 |
| **M06** | Campaign STATUS / stages / wake organ | **Do not stuff** CV/blog into M06. Same YAML; this card is the first **jobs** |
| **M16** | `artifact_write` | Draft files live here; publish is not an M16 package feature |
| **M07** | Allowlisted fetch + cites | Optional research for the post; **no** scrape |
| **M26 / M19a** | Life | **OUT** (F-M28-4) |
| **`main` publish** | Old pSEO / GSC / S3 ISR | **OUT** (F-M28-3) |

---

## Citations

| Claim | Tag | Pointer |
|-------|-----|---------|
| Horizon gap + false completion | **EVIDENCE** | https://arxiv.org/abs/2608.06663 |
| Long-horizon mirage / collapse | **EVIDENCE** | https://arxiv.org/abs/2604.11978 |
| Workflows vs agents | **EVIDENCE** | https://www.anthropic.com/engineering/building-effective-agents |
| HITL serialize / resume | **EVIDENCE** | https://openai.github.io/openai-agents-python/human_in_the_loop/ |
| Cowork projects + ask-before-act; local vs cloud schedule | **EVIDENCE** | https://claude.com/product/cowork · https://support.claude.com/en/articles/13345190-get-started-with-claude-cowork |
| ChatGPT Plan / Work approve-then-act | **EVIDENCE** | https://chatgpt.com/work/ |
| File-centric workspace | **EVIDENCE** | https://arxiv.org/abs/2601.03204 |
| MEA: state outside executor | **EVIDENCE** | https://arxiv.org/abs/2608.01964 |
| Job HITL before submit | **EVIDENCE** | https://github.com/BowennCAI/claude-job-slayer · M19 |
| PR/paste = publish vs GSC mill | **EVIDENCE** | https://github.com/vipulawl/blogging-agent (`APPROVAL_MODE=pr`) |
| Consent Integrity (bind real args) | **EVIDENCE** / **POLICY** | https://arxiv.org/abs/2606.02668 |
| ADA Plan/Accept + artifacts + campaign enum | **METAL** | M15 · M16 · `open_loops.py` · `artifact_write` |
| Old publish daemon | **METAL** (other branch) | `main` `docs/c4/3-components/publish-workflows.md` |

---

### Lens cheat-sheet

| Claim | Lens |
|-------|------|
| Disk STATUS + you-ship beats chat hope | **EVIDENCE** + **FEASIBLE** |
| Unsupervised apply/post overnight | **FANFICTION** / **POLICY** deny |
| Cowork as ADA’s runtime / clock | **FANFICTION** on this Pi |
| `waiting_on_aryan` enum exists | **METAL** |
| Handshake + persist `plan_id` + typed URL | **METAL** (Layer A v1.2 — `open_loops.py`, `artifact_write`, F-M28-7/8 tests) |
| Accept ≠ Confirm ≠ operator-ship | **POLICY** |
| Same Gemini; no second cortex | **FEASIBLE** + constitution |
| LangGraph / n8n / swarm | **Won’t-chase** |
| Life join as work gate | **OUT** |
| GSC / LaTeX / ATS as first-post gate | **OUT** |

---

**Next:** Layer B later (stage lists + first real `portfolio-post-1`). Do not implement GSC, LinkedIn API, or LaTeX this week.

*End M28 v1.2 — Layer A metal on disk; stages per container still later; drafts on disk; you ship; loop is the product.*
