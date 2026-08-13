# M06 — Campaigns / Long-Horizon Continuity (status on disk, not immortal chat)

**Status:** **METAL skeleton** (2026-08-13) — `open_loops` extended with `kind: campaign|todo`, STATUS/stages/gates/wake fields, budgeted boot heads, `ada campaigns status|check`, Dream stages proposals (never auto-done), optional `deploy/systemd/ada-brief.{timer,service}` pointer. Design card remains authoritative for horizon; no fetch/GSC/actuators.  
**Date:** 2026-08-13  
**Host:** `ada-pi5` (Raspberry Pi 5 Model B Rev 1.1, Debian trixie, ~8 GiB RAM)  
**Branch:** `rewrite/v1-body`  
**Depends on:** [`../00_ASSISTANT_RESEARCH.md`](../00_ASSISTANT_RESEARCH.md) §§1–5 & §8, [`../01_BODY.md`](../01_BODY.md) §§3–6 & §8–10, [`../02_CONSTITUTION.md`](../02_CONSTITUTION.md) §§6–10 & §16, [`M02_CHAT_HARNESS.md`](./M02_CHAT_HARNESS.md), [`M04_MEMORY_DREAM.md`](./M04_MEMORY_DREAM.md), [`M03_HUD.md`](./M03_HUD.md), [`M05_VOICE_PERSONALITY_CONTROL.md`](./M05_VOICE_PERSONALITY_CONTROL.md)  
**METAL already present:** chat+tools (M02), FACTS/WORLDVIEW + `open_loops.yaml` (M04), `runs/` receipts, Dream seal/manage, HUD, Gemini cortex. **No Funnel.** No local main-LLM cortex as default.

**METAL (this slice):** [`src/ada/memory/open_loops.py`](../../src/ada/memory/open_loops.py), [`proactivity.py`](../../src/ada/memory/proactivity.py), boot in `facts.boot_fact_slice`, CLI `ada campaigns`, tools `memory_open_loops_*`, Dream merge stages `open_loops[]`, timer pointer `ada-brief.timer`. Tests: `tests/test_campaigns_open_loops.py` (F1–F8).

**Slice rule:** this card admits **design** of durable multi-session **campaigns** (minutes → hours → days) with STATUS, stages, resume, and attributable nudges — reusing `open_loops` + Dream + optional timers. It does **not** admit: multi-agent swarms, unsupervised multi-day AGI missions, always-on worker “daemon cosplay,” complex in-process job frameworks, Funnel, local main cortex, consciousness/soul claims, or inventing a second runtime beside the existing harness.

**Won’t-chase this slice:** n8n as ADA’s brain; Celery/RQ/Redis job queues; multi-agent orchestrator-workers as default; always-running cortex loop; stuffing full campaign history into every chat turn; SOUL.md; embedding CRM; email/HA actuators (confirm-gated later cards).

**Name justification:** **Campaigns** (not “adaemon,” “job ticks,” or “workflows engine”). A campaign is a **named durable goal with stages and STATUS on disk**. Wake is rare and attributable. The confusing prior mental model (immortal process + tick cosmology) is explicitly retired for v1.

---

## Operator locks (hard)

1. **Confirm for side effects** — stage gates that touch the world (apply, send, post, fetch-to-act) require real gateway-rendered confirms ([Consent Integrity](https://arxiv.org/html/2606.02668v1)); Plan-mode proposes, Agent executes only under ladder.
2. **No Funnel / public ingress** — Tailscale control plane only.
3. **Gemini primary cortex** — intermittent; not an always-on local brain.
4. **Heal-first quiet hours** — **23:00–05:30 NZST**; overnight heal/retry OK; user-facing campaign nudges wait for morning brief / user open (constitution §10 / body quiet policy).
5. **Truth > charm** — campaign STATUS from disk + receipts, never from vibes.
6. **No multi-agent swarm as default** — one organism, one harness.
7. **No consciousness / soul** — Dream and overnight work are manage/consolidation, not inner life.
8. **Campaigns ≠ immortal process** — durable state + stage gates + attributable nudges; wake on schedule or when Aryan opens ADA.
9. **Cortex ≠ organism** — Pi owns clocks, YAML, timers, runs/; Gemini sketches next step from a **budgeted** campaign slice.

---

## 1. Question / goal / slice admission

**Research question.** What do 2024–2026 papers and serious agent systems say about long-running / multi-session agent tasks — and what is the **harder-correct, teachable** shape for ADA on this Pi, given Tier A already exists?

Horizons in scope:

| Horizon | Example | ADA pattern |
|---------|---------|-------------|
| **Minutes** | Multi-tool chat task in one session | Existing M02 ReAct harness + receipts |
| **Hours** | “Prep job apps this afternoon”; research digests | Campaign STATUS + stages; resume same day |
| **Multi-day** | Job hunt, research watch, admin backlog | Campaign on disk; wake on timer / user open; Dream refresh; morning brief surfaces |

**Goal (M06 design).**

1. Give Aryan a **≤5-concept mental model** that is not daemon/tick jargon.  
2. Survey SOTA failure modes and harness patterns with lens tags.  
3. Map **what `open_loops` already covers vs what’s missing**.  
4. Recommend a **minimal organ set**: extend open_loops → campaigns, reuse Dream + optional timer, thin Plan/nudge path — **no** new always-on worker.  
5. Specify how STATUS is tracked/resumed **without token bleed**.  
6. Leave ordered “research done → implement next” (design only) + taste-fork OPEN questions.

```text
  Aryan opens HUD / CLI  OR  timer fires (rare)
           |
           v
  [read campaign STATUS from disk — tiny slice]
           |
           +--> Gemini (capped turn)  — Plan or Agent under ladder
           |
           +--> tools → receipts in runs/
           |
           +--> upsert campaign stage / STATUS on disk
           |
           v
  (idle — no immortal cortex process)

  [ada-dream.timer ~03:30]  — manage digests / refresh open campaign heads (existing Dream)
  [optional ada-brief / campaign check timer] — surface nudges outside quiet hours
```

---

## 2. Simple mental model for Aryan (≤5 concepts)

Forget “adaemon,” “job ticks,” “worker pools.” Use these five only:

| # | Concept | Meaning |
|---|---------|---------|
| **1. Campaign** | A named multi-day (or multi-hour) goal you care about — e.g. *job hunt*, *research watch*, *admin*. Lives on disk. |
| **2. STATUS** | One of: `active` / `blocked` / `waiting_on_aryan` / `paused` / `done` / `failed`. Truth comes from the file + receipts, not chat memory. |
| **3. Stages** | Ordered checklist inside the campaign (“research → shortlist → tailor → apply → follow-up”). Current stage is explicit. |
| **4. Wake** | ADA looks at a campaign when **you open** ADA, or on a **scheduled brief/check** (systemd timer — same *shape* as Dream). Between wakes: **idle**. |
| **5. Gate** | Risky next step pauses with `needs_confirm` until you approve (constitution ladder). |

**Explicitly reject for v1 vocabulary:** daemon ticks, job queues, “always running agent,” multi-agent swarms, “mission control AGI.” Those words smuggle complexity ADA does not need yet (**EVIDENCE:** Anthropic simplicity bias; **POLICY:** operator confusion from prior framing).

**One sentence:** *A campaign is a todo with stages and a clock — ADA wakes, advances one honest step (or asks you), writes STATUS, then sleeps.*

---

## 3. Lens tags

| Tag | Meaning here |
|-----|----------------|
| **FANFICTION** | Multi-day unsupervised Jarvis missions; daemon that “thinks all night” as consciousness; swarm of sub-agents running the house |
| **EVIDENCE** | Horizon Gap / Mirage failure modes; externalized goals; sleep-time vs online; Anthropic workflows; file-centric state (InfiAgent); MEA / manager-audit patterns |
| **FEASIBLE-on-Pi8GB** | YAML campaigns on HDD; rare Gemini wakes; systemd timers; no always-on local LLM; no Redis/Celery |
| **POLICY** | Confirm side effects; no Funnel; Gemini primary; quiet hours heal-first; no multi-agent default; no soul claims |
| **METAL** | `open_loops.yaml` = `{id,text,status,created_at,updated_at}` today; Dream timer pointer exists; morning brief *prefs* exist, push brief job does not |

---

## 4. SOTA landscape (2024–2026) — ≥6 citations

Every row tagged. Citations are **lineage for design**, not training homework.

### 4.1 Horizon gap / long-horizon failure modes

| Source | Claim | Tag | ADA takeaway |
|--------|-------|-----|--------------|
| **Horizon Gap survey (2026)** — [arXiv html](https://arxiv.org/html/2608.06663) | Disambiguate **long-horizon** (task steps) vs **long-context** (model window) vs **long-term memory** (system persistence). Outcome-only signals go uninformative as horizon grows. Failures: planning drift, false completion, lost decisions. | **EVIDENCE** | Don’t equate “big context” with “campaign works.” Persist goals outside the window. |
| **Long-Horizon Task Mirage (2026)** — [arXiv:2604.11978](https://arxiv.org/abs/2604.11978) | SOTA agents degrade on interdependent long sequences; taxonomy includes planning error, catastrophic forgetting, history error accumulation, memory limitation, false assumptions. | **EVIDENCE** | Cap autonomy; stage gates; discard bloated interaction history between stages. |
| **Why Reasoning Fails to Plan (2026)** — [arXiv:2601.22311](https://arxiv.org/abs/2601.22311) | Stepwise “reason harder” ≠ durable planning. | **EVIDENCE** | Externalize plan/stages as artifacts; don’t rely on CoT alone. |
| **Goal persistence / drift (2026 practice synthesis)** — e.g. [Zylos note](https://zylos.ai/research/2026-04-03-goal-persistence-drift-long-horizon-ai-agents) | Goals in the context window dilute; externalize goals as first-class artifacts. | **EVIDENCE** (practice) | Campaign goal text + stages live in YAML, re-injected each wake. |

**ADA mapping:** multi-day job hunt in one chat thread **will** drift and false-complete. That is not a Gemini quality bug — it is the horizon gap. **FEASIBLE-on-Pi8GB:** fix with disk STATUS, not a bigger prompt.

### 4.2 Persisted state vs stuffing transcripts

| Source | Claim | Tag | ADA takeaway |
|--------|-------|-----|--------------|
| **InfiAgent (ACL Findings 2026)** — [PDF](https://aclanthology.org/2026.findings-acl.1787.pdf) | File-centric workspace = authoritative progress; bounded “thinking record”; resume from checkpoint, not full dialogue replay. | **EVIDENCE** | Campaign YAML (+ optional `scratch/campaigns/<id>/`) is the workspace; chat is ephemeral UI. |
| **LongHorizon-Harness (2026)** — [arXiv:2608.01964](https://arxiv.org/abs/2608.01964) | Manage–Execute–Audit: keep **verified task state** outside the executor; fresh-context executor; discard interaction history each round. | **EVIDENCE** | Wake loads STATUS + current stage + last receipt pointers — not the week’s chat. |
| **Memory surveys** — [Zhang 2024](https://arxiv.org/abs/2404.13501); [Memory for Autonomous LLM Agents 2026](https://arxiv.org/html/2603.07670v1) | write → **manage** → read; hierarchical stores beat eternal window stuffing. | **EVIDENCE** | Dream already owns manage; campaigns own procedural goal state. |
| **Usable-scale memory (2026)** — [html](https://arxiv.org/html/2605.07313) | Stored evidence becomes unusable as irrelevant sessions grow. | **EVIDENCE** | Budgeted boot slice: campaign **heads** only (≤N active). |

**FANFICTION:** “just keep the whole transcript forever and she’ll remember the campaign.”  
**FEASIBLE-on-Pi8GB:** HDD can store runs forever; **cortex tokens cannot**. STATUS file is the cheap truth.

### 4.3 Sleep-time / offline consolidation vs always-on loops

| Source | Claim | Tag | ADA takeaway |
|--------|-------|-----|--------------|
| **Sleep-time Compute (Lin et al., 2025)** — [arXiv:2504.13171](https://arxiv.org/abs/2504.13171) | Offline precomputation amortizes test-time cost when future queries are somewhat predictable. | **EVIDENCE** | Dream + optional overnight campaign-head refresh; morning brief consumes digests. |
| **Auto-Dreamer (2026)** — [html](https://arxiv.org/html/2605.20616) | Offline consolidation as second timescale. | **EVIDENCE** (shape only; **won’t train**) | Already locked in M04 Dream shape. |
| **ADA body/research POLICY** | Interactive cortex intermittent; Dream on timer ~03:30; quiet hours heal-first. | **POLICY** / **METAL** | Campaigns **idle between wakes** — same organism split. |

**FANFICTION:** always-on loop “so she’s working while you sleep” as continuous cognition.  
**FEASIBLE-on-Pi8GB:** systemd timer + capped Gemini manage already fits RAM; an always-on agent loop fights the 8GB budget and burns tokens (**ANTI-METRIC** in research §2).

### 4.4 Workflow / plan-and-execute / stage gates + human confirm

| Source | Claim | Tag | ADA takeaway |
|--------|-------|-----|--------------|
| **Anthropic — Building Effective Agents (2024)** — [eng blog](https://www.anthropic.com/engineering/building-effective-agents) | Prefer **workflows** (code paths + gates) before autonomous agents; simplicity; pause for human at checkpoints; stop conditions. | **EVIDENCE** | Campaigns = lightweight workflow state; LLM fills *one stage*, not unbounded autonomy. |
| **Constitution / Consent Integrity** | Confirm UI binds real tool args; outcomes `done` / `needs_confirm` / `blocked` / `failed`. | **POLICY** + **EVIDENCE** | Stage gates map onto existing ladder. |
| **ReAct (Yao et al., 2022)** | Ground each claim in tool observations. | **EVIDENCE** | Progress claims cite `runs/` receipts or campaign field updates. |

### 4.5 Scheduler patterns

| Pattern | What it is | Tag | Fit for ADA v1 |
|---------|------------|-----|----------------|
| **systemd timer** (like `ada-dream.timer`) | OS wakes a one-shot process; exits | **FEASIBLE-on-Pi8GB** / **METAL** | **Preferred** for Dream + optional brief/campaign check |
| **cron** | Same idea, thinner | **FEASIBLE-on-Pi8GB** | OK equivalent |
| **In-process job queue** (Celery/RQ/Redis) | Always-ish worker + broker | **EVIDENCE** (ops common) | **Overbuild early** for personal Pi assistant |
| **“Daemon ticks” / adaemon** | Immortal process polling a tick clock | **FANFICTION**-adjacent ops cosplay | **Rejected for v1 vocabulary and architecture** — optional later only if timers prove insufficient |
| **Wake-on-user-open** | Load campaign heads into boot / brief | **FEASIBLE-on-Pi8GB** | **Default free wake** — zero extra process |

**Body already says** ([`01_BODY.md`](../01_BODY.md) §8): systemd-supervised service + Dream timer. That is **wake/supervise**, not “tick cosmology.” Campaigns should **reuse timer shape**, not invent a second runtime religion.

### 4.6 What builders overbuild too early

| Overbuild | Why it tempts | Tag | ADA stance |
|-----------|---------------|-----|------------|
| Multi-agent swarms / orchestrator-workers | Feels “serious” | **EVIDENCE** pattern exists; **POLICY** won’t as default | One harness; later specialist *tools*, not peer agents |
| Always-on workers | Feels “always-on companion” | **FANFICTION** pull | Companion = reachable + durable memory, not 24/7 cortex |
| Complex job frameworks | Feels production | **EVIDENCE** Anthropic: frameworks obscure | YAML + CLI + timer first |
| External n8n as brain | Pretty graphs | **FEASIBLE** as *optional* actuator later | Never primary STATUS store |
| Unsupervised multi-day missions | Horizon Gap denial | **POLICY** non-goal (research §5) | Stage caps + human gates |

---

## 5. Map to ADA metal — what exists vs what’s missing

### 5.1 Citations to living substrate

| Piece | Role today | Doc / code |
|-------|------------|------------|
| Chat harness + tools | Minutes-horizon ReAct; receipts | M02; `src/ada/harness/`, gateway |
| FACTS / WORLDVIEW | Semantic continuity | M04; `src/ada/memory/` |
| **`open_loops.yaml`** | Projects / promises / TODOs | [`open_loops.py`](../../src/ada/memory/open_loops.py): `id`, `text`, `status`, timestamps; list/upsert; delete needs confirm |
| `runs/` | Episodic ground truth | Body §4.3 |
| Dream seal + manage | Offline write–manage–read | M04; `src/ada/dream/`; `ada-dream.timer` pointer |
| HUD | Control-plane chat / later inbox | M03 |
| Gemini cortex | Interactive + capped Dream manage | research + constitution |
| Quiet / brief prefs | `brief_time` 05:30; quiet 23:00–05:30 | FACTS + constitution v1.2 |
| Plan mode | Stub in modes table | Body §3.2; M02 — **not** a workflow engine yet |

### 5.2 What `open_loops` already covers

**Covers (good spine):**

- Durable list of open work items on HDD (crash-safe atomic write).  
- Status field + upsert from tools (`memory_open_loops_*`).  
- Boot-pack head injection (budgeted) — continuity without full dump (M04).  
- Dream manage schema already *can* emit `open_loops[]` candidates (manage prompt).  
- Delete gated by confirm — permission taste matches campaigns.

**Does *not* yet cover (campaign gap):**

| Missing | Why it matters |
|---------|----------------|
| **Named campaign vs flat TODO** | Job hunt ≠ “buy milk”; needs grouping |
| **Stages / checklist** | Horizon Gap: without stages → false completion |
| **`waiting_on_aryan` / blocked reason** | Human-in-the-loop without chat archaeology |
| **`next_wake_at` / cadence** | Hours/days horizon without always-on loop |
| **Last progress + receipt pointer** | Truthful self-report (“I tailored CV”) needs `runs/` link |
| **Stage-gate / side-effect class** | Apply/send ≠ research note |
| **Attribution for nudges** | Research metric: trigger + evidence + permission tier |
| **Token-cheap STATUS view** | HUD/CLI “where is job hunt?” without Gemini |

### 5.3 Why adaemon / job-ticks complexity is optional/wrong for v1

1. **Operator taste (given):** prior framing felt confusing — mental model failed before code failed.  
2. **Literature:** successful systems externalize **state**, not process mythology (InfiAgent, LongHorizon-Harness, Anthropic workflows).  
3. **Body already has the right wake primitive:** systemd timer + intermittent harness (**METAL** / **POLICY**).  
4. **Pi 8GB:** always-on worker + cortex contention is the scarce-resource anti-pattern (**FEASIBLE-on-Pi8GB**).  
5. **Constitution:** warmly forward + quiet hours + heal-first — not continuous autonomous mission theater.  
6. **Lab teach goal:** learn *durable goal state + stage gates*; a tick daemon teaches ops cosplay first.

**Verdict:** treat “adaemon/job-ticks” as a **won’t-chase label** for v1. If someday a long-lived supervisor is needed, it should be a thin `ada-agent.service` wrapping the *same* harness (M02 pointer) — still **not** a tick cosmology.

---

## 6. Options matrix

| Option | How it works | Pros | Cons | Lens | Verdict for ADA v1 |
|--------|--------------|------|------|------|--------------------|
| **A. Transcript-only** | Keep campaign in chat / long `runs/` replay | Zero new schema | Token bleed; drift; false done; unusable at scale | **EVIDENCE** fails Horizon Gap | **Reject** as primary |
| **B. open_loops + stages (campaigns)** | Extend loops or thin `campaigns.yaml`; STATUS + stages; wake on open/timer | Reuses M04; teachable; Pi-cheap; aligns SOTA externalization | Needs schema discipline; not flashy | **EVIDENCE** + **FEASIBLE-on-Pi8GB** + **POLICY** | **Recommend** |
| **C. External n8n / Zapier** | Graphs outside ADA | Nice UI for some automations | Split brain; STATUS not in FACTS; Tailscale/egress complexity; ADA becomes passenger | **FEASIBLE** later actuator | **Defer** — never primary STATUS |
| **D. Multi-agent swarm** | Planner/worker/critic agents | Lit has MEA / orchestrator patterns | Overbuild; debug hell; anti-metric; not lab default | **EVIDENCE** exists; **POLICY** no | **Reject default** (cite MEA as *roles in one process* later if needed) |
| **E. Always-on worker** | Immortal loop polling jobs | Feels “always working” | Tokens/RAM; quiet-hours fights; daemon confusion | **FANFICTION** pull | **Reject v1** |

**Harder-correct vs shortcut:**  
- Shortcut = “just chat about job hunt every day” or “spin n8n.”  
- Harder-correct = **campaign STATUS on disk + stage gates + rare wakes** — teaches the same lesson as SOTA harnesses without their frameworks.

---

## 7. Recommended design for ADA (minimal organs)

### 7.1 Organ set (minimal)

| Organ | Action | Notes |
|-------|--------|-------|
| **`memory.campaigns` (or extended `open_loops`)** | **NEW design** — durable campaign records | Prefer **extend open_loops schema** first (one file, one tool surface); split file only if clutter hurts |
| **M02 harness** | **CALL** — Plan/Agent turns on wake | No second cortex loop |
| **Dream** | **REUSE** — overnight digest may refresh campaign heads / WORLDVIEW notes | Don’t re-read full runs into manage |
| **Timer** | **OPTIONAL** — `ada-brief.timer` or campaign-check at `brief_time` | Same shape as Dream; not a gate for schema |
| **HUD** | **LATER consumer** — STATUS list / inbox nudges | Not a new editor gate for v1 design |
| **Fetch / email / HA** | **OUT of this card** | Campaigns must work as *tracking* before actuators |

### 7.2 Suggested record shape (design — not code)

Illustrative fields (extend loop item or `campaigns:` list):

```yaml
# design sketch — not implemented
id: "c_jobhunt"
kind: campaign          # vs plain todo
title: "Job hunt — NZ ML / systems"
status: active          # active|blocked|waiting_on_aryan|paused|done|failed
stages:
  - id: research
    state: done
  - id: shortlist
    state: active
  - id: tailor
    state: pending
  - id: apply
    state: pending
    gate: confirm       # side-effect class
current_stage: shortlist
blocked_reason: null
next_wake_at: "2026-08-14T05:30:00+12:00"
last_progress_at: "..."
last_receipt: "runs/2026-08-13/sess_....jsonl#evt_.."
nudge_attribution:
  trigger: "brief_time"
  evidence: "3 stages stale >48h"
cadence: daily          # or on_open_only
```

Plain TODOs remain `kind: todo` with no stages — **one mental model, two densities**.

### 7.3 Wake policy (no immortal process)

1. **On user open:** boot / brief path injects ≤K active campaign heads (titles + STATUS + current stage + blocked_reason).  
2. **On schedule:** optional timer runs `ada campaign check` or folds into morning brief — outside quiet hours; heal-first overnight.  
3. **On Dream:** manage may propose stage/STATUS updates into staging or open_loops candidates — whitelist carefully; don’t auto-mark `done` without receipts.  
4. **Never:** continuous Gemini loop advancing campaigns unsupervised for days (**POLICY** non-goal).

### 7.4 How STATUS is tracked/resumed without token bleed

| Do | Don’t |
|----|-------|
| Load **campaign head** (≤~200–400 tokens each, cap K=3–5) | Replay week of chat into every turn |
| Point to `last_receipt` when claiming progress | Claim “I applied” from WORLDVIEW vibes |
| Advance **one stage** per wake unless Aryan asks deep_dive | Autonomously run entire checklist |
| Persist STATUS on tool upsert before answering | Keep STATUS only in model scratchpad |
| Morning brief lists blocked / waiting_on_aryan | Chatter every hour in quiet hours |
| Archive `done` campaigns out of boot slice | Keep finished campaigns in forever-prompt |

This is exactly the LongHorizon-Harness idea (verified state outside executor) and InfiAgent idea (file-centric checkpoint) translated to ADA’s existing dual-store + runs.

---

## 8. Egress / trust rings

| Path | Ring | Campaign impact |
|------|------|-----------------|
| Chat wake / Plan propose | Cortex egress (Gemini) | Budgeted heads only |
| Dream manage refresh | Cortex egress (capped) | Deltas, not full history |
| Timer check with no LLM | Local only | Preferred when possible (staleness rules in code) |
| Future fetch for research-watch | **New** egress — needs allowlist card | **After** campaign STATUS exists |
| Funnel / public | Denied | No |

---

## 9. Learning goals (lab)

After this card (and a thin implement later), Aryan should be able to explain:

1. Why **long-context ≠ long-horizon ≠ long-term memory**.  
2. Why **STATUS on disk** beats transcript stuffing for job-hunt-class work.  
3. Why **sleep-time Dream** and **campaign wakes** are different timescales from chat.  
4. Why **stage gates + confirm** are the adult form of “proactivity.”  
5. Why **systemd timer ≠ daemon tick religion**.  
6. What builders overbuild (swarms, queues, always-on) before STATUS works.

**Harder-correct choice:** extend `open_loops` into campaigns with stages + wakes.  
**Shortcut rejected:** n8n-as-brain, multi-agent, or “just use a longer chat.”

---

## 10. Falsifiers (acceptance when coded — design targets now)

| # | Falsifier | Pass look |
|---|-----------|-----------|
| F1 | Kill process mid-campaign | STATUS/stage intact on disk |
| F2 | New chat session | ADA reports current stage from file, not invented |
| F3 | False completion | Cannot mark `apply=done` without receipt / confirm when gated |
| F4 | Token bleed | Boot/brief campaign slice stays under budget; no full `runs/` dump |
| F5 | Quiet hours | No user-facing campaign nudge 23:00–05:30; Dream/heal OK |
| F6 | Mute / chill | Proactive campaign nudges suppress |
| F7 | “Where’s job hunt?” | Observe-mode STATUS answer without unnecessary tools theater |
| F8 | Multi-day gap | After 48h, wake/brief shows *stale* or blocked honestly |

Won’t-chase as gates: LoCoMo, multi-agent bakeoffs, unsupervised 72h missions.

---

## 11. OPEN questions for Aryan (taste forks only)

Architecture is recommendable without these; they only tune *shape*:

1. **Schema home:** extend `open_loops.yaml` with `kind: campaign|todo` **vs** separate `campaigns.yaml`? (Recommend: extend first.)  
2. **First vertical campaign:** job hunt **vs** research watch **vs** admin — which gets stages first?  
3. **Nudge density:** daily brief line only **vs** also mid-day stale ping (still outside quiet hours)?  
4. **HUD:** STATUS as brief lines first **vs** dedicated campaigns pane later?  
5. **Cadence default:** `on_open_only` until brief timer exists, or design brief timer in the same coding slice?

Non-questions (locked): no swarm default; no Funnel; no local main cortex; no consciousness; confirm for side effects; heal-first quiet hours.

---

## 12. Ordered “research done → implement next” (design only — no code this pass)

1. **Lock schema** — campaign fields on open_loops (or split file); status enum; stages; gates; `next_wake_at`.  
2. **Tools** — `memory_campaigns_list/upsert` (or extend open_loops tools); Observe list; Agent upsert; confirm on delete / dangerous status flips.  
3. **Boot / brief slice** — inject ≤K campaign heads; drop `done` from default boot.  
4. **CLI** — `ada campaigns status` (or `ada memory loops --campaigns`) for metal truth without Gemini.  
5. **Wake path v0** — on chat start / morning brief stub: surface blocked + waiting_on_aryan.  
6. **Optional timer unit pointer** — `ada-brief.timer` at `brief_time` (not gate); reuse Dream’s timer lessons.  
7. **Dream manage hook** — allow staged proposals for campaign notes; never auto-`done` without receipt policy.  
8. **Smokes F1–F8** on Pi.  
9. **Stop** — do **not** build fetch, email, n8n, swarm, or always-on worker in this slice.  
10. **Next card after campaigns substrate:** allowlisted **web fetch / extract** (or morning-brief productization if campaigns already usable as tracking-only).

---

## 13. Fetch vs campaigns — sequencing

| Order | Rationale |
|-------|-----------|
| **Campaigns substrate first** | Teaches STATUS/resume/token discipline with **zero new egress**; job hunt can be manually updated (“I applied to X”) and still beat transcript-only. |
| **Generic web-fetch after** | Fetch without campaigns dumps pages into chat → classic token bleed + false completion. Fetch *into* campaign stages (research-watch digests, job RSS → shortlist) is the point. |

**Exception:** if Aryan refuses any campaign tracking without live web, still implement **schema + STATUS CLI first** (hours), then fetch card immediately after — never fetch-only.

Morning brief can ship in parallel *as a thin surfacer* of existing open_loops/campaign heads; it is not a substitute for campaign stages.

---

## 14. References (selected)

### Long-horizon / harness
- *The Horizon Gap…* (2026) — https://arxiv.org/html/2608.06663  
- *The Long-Horizon Task Mirage?* (2026) — https://arxiv.org/abs/2604.11978  
- *Why Reasoning Fails to Plan* (2026) — https://arxiv.org/abs/2601.22311  
- InfiAgent (2026) — https://aclanthology.org/2026.findings-acl.1787.pdf  
- LongHorizon-Harness (2026) — https://arxiv.org/abs/2608.01964  
- Anthropic, *Building Effective Agents* (2024) — https://www.anthropic.com/engineering/building-effective-agents  
- Awesome-Long-Horizon-Agents (curated index) — https://github.com/RUC-NLPIR/Awesome-Long-Horizon-Agents  

### Memory / sleep-time / dual timescale
- Zhang et al. (2024) — https://arxiv.org/abs/2404.13501  
- *Memory for Autonomous LLM Agents* (2026) — https://arxiv.org/html/2603.07670v1  
- Lin et al., *Sleep-time Compute* (2025) — https://arxiv.org/abs/2504.13171  
- Auto-Dreamer (2026) — https://arxiv.org/html/2605.20616 — **shape only**  
- *When Stored Evidence Stops Being Usable* (2026) — https://arxiv.org/html/2605.07313  

### Grounding / permissions
- Yao et al., ReAct (2022) — https://arxiv.org/abs/2210.03629  
- Consent Integrity (2026) — https://arxiv.org/html/2606.02668v1  

### Internal ADA
- [`../00_ASSISTANT_RESEARCH.md`](../00_ASSISTANT_RESEARCH.md) — horizon gap §3.4; Tier A/B; §8 card gate; anti-metrics  
- [`../01_BODY.md`](../01_BODY.md) — organs; open_loops; Dream timer; modes  
- [`../02_CONSTITUTION.md`](../02_CONSTITUTION.md) — ladder; quiet hours; epistemics outcomes  
- [`M02_CHAT_HARNESS.md`](./M02_CHAT_HARNESS.md) — intermittent cortex; runs/  
- [`M04_MEMORY_DREAM.md`](./M04_MEMORY_DREAM.md) — open_loops; Dream; boot budgets  
- Code: `src/ada/memory/open_loops.py`, `src/ada/dream/`, `src/ada/harness/`, `deploy/systemd/ada-dream.timer`

---

### Lens cheat-sheet

| Claim | Lens |
|-------|------|
| Campaign STATUS on YAML beats chat memory | **EVIDENCE** + **FEASIBLE-on-Pi8GB** |
| Always-on daemon “is” the companion | **FANFICTION** — reject for v1 |
| systemd timer wake ≈ Dream shape | **METAL** / **POLICY** |
| Multi-agent default for job hunt | **Overbuild** — reject |
| n8n as primary campaign store | **Defer** — wrong brain |
| Dream refreshes campaign digests overnight | **EVIDENCE** sleep-time pattern + **POLICY** existing Dream |
| Unsupervised multi-day apply-spam | **POLICY** denied / confirm gates |

---

*End of M06. Design complete; METAL skeleton landed (STATUS/stages/boot/CLI/check timer pointer). Fetch/actuators still next card.*

---

## If Aryan does one thing next

**Do this:** treat **campaigns as durable STATUS + stages on (extended) `open_loops`**, with wake-on-open + optional brief timer — and **retire adaemon/job-tick vocabulary** for v1.

**Fetch sequencing:** implement **campaigns substrate before generic web-fetch**. Fetch comes next so it writes into stages/digests instead of bleeding tokens into immortal chat.