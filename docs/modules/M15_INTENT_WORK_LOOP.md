# M15 — Intent → Work Loop (plan · todos · execute · receipts)

**Status:** module research card — **P0+P1 metal shipped** (2026-08-16). Structured plan artifacts (SSE+JSONL), Accept→`kind:todo`, Plan↔Agent history preserve, charter clarify/done-receipt, soft mode-suggest, confirm `pending_id`. P2 deferred.  
**Date:** 2026-08-16 (v2 implement)  
**Host:** `ada-pi5` (Raspberry Pi 5 Model B Rev 1.1, Debian trixie, ~8 GiB RAM)  
**Client:** Aryan’s Mac over Tailscale Serve (control plane)  
**Branch:** `rewrite/v1-body`  
**Depends on:** [`M02_CHAT_HARNESS.md`](./M02_CHAT_HARNESS.md) (ReAct, gateway, stream events), [`M03_HUD.md`](./M03_HUD.md) + [`M13_HUD_UX.md`](./M13_HUD_UX.md) + [`M14_AGENT_SURFACE.md`](./M14_AGENT_SURFACE.md) (session, Plan Accept, `/api/confirm`), [`M06_CAMPAIGNS_LONG_HORIZON.md`](./M06_CAMPAIGNS_LONG_HORIZON.md) (STATUS/stages — **related, not the same**), [`../02_CONSTITUTION.md`](../02_CONSTITUTION.md) §§3–4, 6–8, 11, 14–15  

**Name justification:** **`M15_INTENT_WORK_LOOP.md`**. The research question is how a **user utterance** becomes **steerable work** — interpret → optional plan → bind consent → execute under policy → receipts — not “campaigns,” not “HUD chrome,” not “memory understanding.”  
- **Not M06:** campaigns are multi-session STATUS/stages on disk; this card is the **per-turn / short-horizon control loop** that *feeds* campaigns/todos.  
- **Not M14:** M14 shipped ask/accept/confirm *surfaces*; this card owns the **interaction model + structured work objects** those surfaces should serve.  
- Rejected titles: `M15_PLAN_EXECUTE` (misses clarify/receipts/policy), `M15_WORK_OBJECTS` (jargon), `M15_AUTONOMY` (**FANFICTION** smell).

**METAL present (2026-08-16 P0+P1):** `harness/plan_artifact.py`; Plan-mode `plan_artifact` SSE + JSONL; `POST /api/plan/accept` → `open_loops` todos; Plan↔Agent history preserve; charter clarify≤2 + done-cites-receipt; confirm `pending_id` bind; soft `#mode-suggest` chip. Tests: `tests/test_m15_intent_work_loop.py`.

**OUT unless EVIDENCE+FEASIBLE force rethink:** Funnel; replacing Gemini; deleting gateway; multi-agent swarms as default; unsupervised multi-day missions; life-ops product buildout; vendor search; voice wake as gate; n8n-as-brain; Celery queues; UI-only “autonomy”; Cursor-parity coding actuators ADA does not have.

---

## 1. Slice rule + won’t-chase

**Research question.** How do SOTA papers and shipping agent products turn a **user utterance** into **accurate, steerable work** (interpret intent → optional plan → tools/actions → verify) — and what should ADA adopt so chat is not “dropdown modes + hope,” while **policy stays outside the model** (gateway / confirm / receipts)?

**Slice rule:** admit **design** of ADA’s intent→work control loop: utterance understanding, clarification, plan artifacts, todo/checklist materialization, mode/policy selection, accept/confirm, execution under gateway, receipt/feedback into next turn. Map onto existing metal; propose Tier A/B/C upgrades. **Default: research only** — thin P0 only if OPEN locks it.

**Won’t-chase**

| Out | Why |
|-----|-----|
| Funnel / public ingress | **POLICY** |
| Model self-authorizes writes | **POLICY** — gateway + session auth |
| Second cortex / client-side agent loop | UI is `channel.web` → M02 harness |
| n8n / Celery as brain | Wrong control plane; ops tax on Pi |
| Chat history as only plan store | Horizon gap / false completion (**EVIDENCE**) |
| Multi-agent swarm default | Constitution / M06 lock |
| Life-ops feature packaging | Later consumer of this card |
| Claiming Cursor/Claude IDE actuator parity | ADA actuators = body/memory/web (+ future) — map **analogues** |
| LangGraph as required runtime | Steal patterns; keep thin Python harness (**FEASIBLE**) |

```text
  utterance (HUD / CLI)
        |
        v
  [interpret]  work? chat? underspecified?
        |
        +-- clarify?  (ask ≤N questions)
        |
        v
  [policy]  Observe | Plan | Agent   ← operator dial (+ soft suggest)
        |                              gateway enforces — model proposes only
        +-- Plan: plan artifact → Accept / Revise
        |
        v
  [bind]  Accept plan  OR  Confirm {tool,args}
        |
        v
  [execute]  ReAct under gateway → observations
        |
        v
  [receipt]  runs/ + optional open_loops todo upsert → next turn
```

**Cross-link only:** “understanding the user” (FACTS / people / WORLDVIEW — M04/M10) ≠ “doing the work” (this card). Memory informs interpretation; it does not authorize tools.

---

## 2. Lens tags

| Tag | Meaning here |
|-----|--------------|
| **FANFICTION** | Silent full autonomy; mind-reading intent; “just understand me”; consciousness; UI autonomy that skips gateway |
| **EVIDENCE** | Papers; product docs / shipping UX; measured agent harness patterns |
| **FEASIBLE** | Pi 5 ~8GB; Python ASGI HUD; Gemini cortex; Mac over Tailscale; no Funnel; no Node-on-Pi rewrite |
| **POLICY** | Constitution modes; confirm ladder; Tailscale-only control plane; secrets never-to-cloud; receipts over vibes |
| **METAL** | What exists in this repo today |

---

## 3. METAL inventory (honest — 2026-08-16)

### 3.1 Utterance → tools → outcomes (today)

| Stage | What happens | Tag |
|-------|--------------|-----|
| **Intake** | HUD `POST /api/chat` or `ada chat` with `mode` from dropdown/CLI flag | **METAL** |
| **Session** | `ChatService._ensure_session(mode)` — **mode change ends prior session** (`stop_reason=mode_switch`) and **clears `history`** | **METAL** / gap |
| **Charter** | `build_system_charter(mode=…)` + register intent→class (social/lookup/task/…) for **tone/tool *hints*** | **METAL** |
| **Loop** | `harness.loop.run_turn` — Gemini tool calls → `Gateway.execute` → observation back into history; caps `max_steps` / wall | **METAL** |
| **Policy** | Writes denied in `observe`/`plan`; ToolSpec `modes`; `needs_confirm` from memory/web organs | **METAL** |
| **Plan UX** | After Plan turn, HUD wraps assistant text in **Plan card**; Accept → switch Agent + user cue `Accepted plan — execute:\n…` | **METAL** (M14) |
| **Confirm UX** | SSE `needs_confirm` → Confirm card with gateway `{tool,args}`; `POST /api/confirm` re-executes with `confirmed=true` (**no cortex**) | **METAL** (M14) |
| **Todos / campaigns** | `open_loops.yaml` via `memory_open_loops_*`; `kind:todo` vs `kind:campaign` | **METAL** (M06) |
| **Receipts** | `runs/<date>/<session>.jsonl` + tool `receipt_id` | **METAL** |

### 3.2 Mode selection — not intent routing

| Claim | Truth | Tag |
|-------|-------|-----|
| Operator picks Observe / Plan / Agent | Yes — HUD `<select>` / CLI `--mode` | **METAL** |
| Soft UI hints (M14 §9.3) | Documented suggestions only; not automatic | **METAL** / design |
| Charter `intent→class` selects policy mode | **No** — register / friend-first formatting + when to skip tools | **METAL** |
| Separate intent classifier / router | **Absent** | gap |
| Model can escalate Plan→Agent by itself | **No** — dial + Accept / session; gateway still denies writes in Plan | **POLICY** / **METAL** |

### 3.3 Plan artifact truth

| Claim | Tag |
|-------|-----|
| Plan mode = gateway propose-only (writes denied) | **METAL** |
| Charter: “Plan (stub). Propose only…” | **METAL** (`charter.mode_addendum`) |
| Plan card = **free-text** last assistant body — not JSON steps, not disk object | **METAL** |
| Accept does **not** write todos / open_loops automatically | **METAL** |
| Accept does **not** bypass gateway | **METAL** / **POLICY** |
| Structured plan store (`plans/*.yaml` or run-bound plan id) | **Absent** |

**Verdict:** Plan is a **policy + UX stub productized by M14**, not yet a first-class work object. Earning a real plan artifact is **in-scope for this card’s design**, not assumed shipped.

### 3.4 Confirm / Consent Integrity (metal)

| Piece | Location | Tag |
|-------|----------|-----|
| Gateway renders denials / observations with real `{tool,args}` | `gateway.py` | **METAL** |
| Confirm allowlist | `routes_api.py` — facts overwrite + `memory_open_loops_upsert` (+ related) | **METAL** |
| Confirm path | `ChatService.confirm_tool` → `Gateway(mode="agent")` + `confirmed=True` | **METAL** |
| Unwired tools | Confirm button omitted / note — no fake success | **METAL** |

### 3.5 open_loops: todos vs campaigns

| Kind | Role | Horizon | This card |
|------|------|---------|-----------|
| `todo` | Short durable checklist item (`open`/`done`/`cancelled`) | Minutes–days | **Primary materialization** for accepted work steps |
| `campaign` | Named goal + stages + STATUS + wake | Hours–multi-day | **M06 owns**; intent→work may *create/advance* a stage, not redefine campaigns |

**Do not** invent a second todo DB for Tier A. Reuse `kind:todo` (+ optional link to plan id later).

### 3.6 Actuator honesty (analogues, not Cursor)

| Cursor / Claude Code actuator | ADA analogue today | Tag |
|------------------------------|--------------------|-----|
| Read/edit source files | *(none as coding IDE)* — future file tools if earned | gap / OUT claim |
| Shell / tests | `body_readonly_cmd` (narrow); no general shell | **METAL** / **POLICY** |
| Apply/reject diff | Confirm bind on `{tool,args}`; no diff UI | **METAL** |
| Web / research | `web_fetch` / cites (allowlist) | **METAL** |
| Memory write | `memory_facts_*`, `memory_open_loops_*`, worldview | **METAL** |
| Body truth | `body_vitals` / whoami / story / doctor / explain | **METAL** |

### 3.7 Gaps summary (design targets)

| Gap | Severity |
|-----|----------|
| No structured plan artifact (id, steps[], status) | High for steerable multi-step work |
| Intent does not select/suggest mode in metal | Medium — dropdown + hope |
| Mode switch wipes chat history | Medium — breaks Plan→Accept continuity if dial flipped mid-thread |
| Accept → Agent cue is prose-only (no todo upsert) | Medium |
| No clarification protocol (when to ask vs act) | Medium |
| No explicit “work complete?” verify step beyond model stop | Medium (horizon / false-completion) |
| Register intent≠work intent | Low confusion risk if documented |

---

## 4. SOTA / academic survey (≥6)

Every row tagged for ADA. Citations are **design lineage**, not training homework.

| # | Source | Claim | FANFICTION / EVIDENCE / FEASIBLE | ADA takeaway |
|---|--------|-------|----------------------------------|--------------|
| 1 | **Yao et al., ReAct (2022)** — [arXiv:2210.03629](https://arxiv.org/abs/2210.03629) | Interleave thought + act + **observation**; grounding beats ungrounded CoT | **EVIDENCE**; **FEASIBLE** (already metal) | Keep ReAct harness; never skip observations for body/memory claims |
| 2 | **Anthropic, Building Effective Agents (2024)** — [engineering post](https://www.anthropic.com/engineering/building-effective-agents) | Prefer **workflows** (code-owned paths) vs full agents; simplest solution first; transparency of planning | **EVIDENCE**; **FEASIBLE** | Intent→work = thin workflow **around** ReAct, not LangGraph day one; Plan Accept is a workflow gate |
| 3 | **Plan-and-Execute lineage** — e.g. LangChain [Plan-and-Execute](https://www.langchain.com/blog/planning-agents); Plan-and-Solve prompting | Separate planner from executor; replan on failure; auditability | **EVIDENCE**; **FEASIBLE** as *pattern* (not framework dep) | Structured plan object + Agent execute; avoid stuffing plan only in chat tokens |
| 4 | **Shi et al., Progent (2025)** — [arXiv:2504.11703](https://arxiv.org/abs/2504.11703) | Deterministic **tool-level** policies outside the model; least privilege | **EVIDENCE**; **FEASIBLE** (gateway/ToolSpec already) | Intent may *suggest* mode; **never** replace gateway allows |
| 5 | **Consent Integrity / LITL (2026)** — [arXiv:2606.02668](https://arxiv.org/abs/2606.02668) | Approving model-written summaries is forgeable; bind approval to **boundary** action | **EVIDENCE**; **POLICY**; **FEASIBLE** (HUD confirm metal) | Plan Accept ≠ tool consent; Confirm must stay gateway-rendered `{tool,args}` |
| 6 | **AskToAct / clarification (2025)** — [arXiv:2503.01940](https://arxiv.org/abs/2503.01940); **SAGE / structured uncertainty (2025)** — [arXiv:2511.08798](https://arxiv.org/abs/2511.08798) | Ambiguous intents → wrong tools; clarify missing params before act; prefer structured uncertainty over endless questions | **EVIDENCE**; **FEASIBLE** (prompt + caps; no training) | Charter/protocol: ask ≤2 clarifiers when task args missing; don’t fake confidence |
| 7 | **Horizon Gap (2026)** — [arXiv:2608.06663](https://arxiv.org/abs/2608.06663); false-finish / Terminal-Bench analyses | Long-horizon ≠ long-context; planning drift, lost decisions, **false completion** | **EVIDENCE**; **FEASIBLE** via disk STATUS | Externalize steps (plan + todos); verify with receipts; hand multi-day to M06 campaigns |
| 8 | **Select-Then-Decompose (2025)** — [arXiv:2510.17922](https://arxiv.org/abs/2510.17922) | Decomposition has performance–cost tradeoffs; task shape picks interleave vs upfront plan | **EVIDENCE**; **FEASIBLE** | Route: social/lookup → single ReAct; multi-step novelty → Plan artifact first |

**EVIDENCE verdict:** production-grade “accurate work” is an **orchestrator** (interpret → optional structured plan → permissioned execute → verify), not a smarter system prompt alone.

**FANFICTION reject:** “the model will just know what I meant and do it safely.”

---

## 5. Market / shipping agents survey (≥5)

Primary-source prioritized. Research date: **2026-08-16**. For each: intake → interpretation → plan visibility → permission → execute → verify/undo → failure recovery. Note **chat-native** vs **explicit UI**.

### 5.1 Cursor Agent (+ Plan Mode)

| Stage | Behavior | Source |
|-------|----------|--------|
| Intake | Chat utterance; mode picker / Shift+Tab | [Cursor Plan Mode](https://cursor.com/docs/agent/plan-mode); [Agent help](https://cursor.com/help/ai-features/agent) |
| Interpretation | Clarifying questions in Plan; suggests Plan on complex keywords | Docs |
| Plan visibility | Reviewable plan (markdown); editable; Save to workspace | Docs |
| Permission | Plan researches; **Build** starts Agent execution; Ask = read-only | Docs / help table |
| Execute | Tool use in workspace (edit/shell) | Product |
| Verify / undo | Diffs, checkpoints, revert+refine plan | Docs (“starting over from a plan”) |
| Failure | Refine plan rather than endless fix prompts | Docs |

**Chat-native vs UI:** hybrid — chat + **explicit** Plan artifact + Build.  
**Steal for ADA:** clarify → plan artifact → Accept/Build → execute; plan as object.  
**Skip:** IDE file actuators; assuming ADA has diffs.  
**Tag:** **EVIDENCE**; analogues **FEASIBLE**.

### 5.2 Claude Code (plan + permission modes)

| Stage | Behavior | Source |
|-------|----------|--------|
| Intake | Prompt; Shift+Tab / `/plan` | [Permission modes](https://code.claude.com/docs/en/permission-modes) |
| Interpretation | Explore + AskUserQuestion before finalize | Docs / Agent SDK |
| Plan visibility | Plan file; `ExitPlanMode` presents for approval | [Tools reference](https://code.claude.com/docs/en/tools-reference) |
| Permission | Plan blocks source edits; approve options switch to auto / acceptEdits / manual | Permission modes |
| Execute | Tools under permission mode | Docs |
| Verify | User reviews edits; permissions prompts | Docs |
| Failure | Stay in plan (“No, keep planning”) | Docs |

**Steal:** Plan as **staging permission**, approve **exits** plan into execute mode (matches M14 Accept).  
**Skip:** bypass-permissions advisory plan; cloud identity as Agent authority.  
**Tag:** **EVIDENCE** / **POLICY** alignment.

### 5.3 ChatGPT Agent mode

| Stage | Behavior | Source |
|-------|----------|--------|
| Intake | Tools dropdown → agent mode mid-conversation | [OpenAI intro](https://openai.com/index/introducing-chatgpt-agent); [Help release notes](https://help.openai.com/en/articles/11794368) |
| Interpretation | Task description → multi-step online work | Intro |
| Plan visibility | On-screen narration of what it’s doing | Intro |
| Permission | Pauses for consequential steps (login/pay); user can take over browser | Intro / secondary analyses |
| Execute | Virtual browser, terminal, connectors | Intro |
| Verify | User watches / interrupts | Intro |
| Failure | Supervised project runner — not always-on | Product positioning |

**Steal:** explicit **agent mode** arming; pause-for-consent on side effects; visible progress.  
**Skip:** multi-tenant cloud; Funnel-shaped reach; virtual computer on Pi.  
**Tag:** **EVIDENCE** (product); **FEASIBLE** only as pattern.

### 5.4 OpenAI Agents SDK (HITL)

| Stage | Behavior | Source |
|-------|----------|--------|
| Intake | `Runner.run(agent, input)` | [HITL guide](https://openai.github.io/openai-agents-python/human_in_the_loop/) |
| Interpretation | Agent instructions + tools; optional handoffs | [Orchestration](https://developers.openai.com/api/docs/guides/agents/orchestration) |
| Plan visibility | App-defined (SDK is runtime) | Docs |
| Permission | Tool `needs_approval` → `interruptions`; `state.approve/reject`; resume same run | HITL guide |
| Execute | Continue from serialized `RunState` | Docs |
| Verify | Guardrails + approvals at boundary | [Guardrails](https://developers.openai.com/api/docs/guides/agents/guardrails-approvals) |

**Steal:** **pause/resume same run** on approval (ADA: `/api/confirm` without new cortex turn); bind approval to tool call id/args.  
**Skip:** multi-agent handoffs as default; adopting SDK wholesale.  
**Tag:** **EVIDENCE**; **FEASIBLE** as pattern on existing gateway.

### 5.5 Continue.dev (Plan / Agent)

| Stage | Behavior | Source |
|-------|----------|--------|
| Intake | Mode selector: Chat / Plan / Agent | [Plan mode](https://docs.continue.dev/ide-extensions/agent/plan-mode); [How it works](https://docs.continue.dev/ide-extensions/agent/how-it-works) |
| Interpretation | Model + tools; policies per tool | [Customize](https://docs.continue.dev/ide-extensions/agent/how-to-customize) |
| Plan visibility | Plan = read-only tool set (explore then switch) | Docs |
| Permission | Ask First / Automatic / Excluded per tool | Docs |
| Execute | Agent tools after permission | Docs |
| Verify | Tool results fed back as context | Docs |

**Steal:** Plan = **read-only tool filter** (ADA gateway already); per-tool ask policies map to `needs_confirm`.  
**Skip:** IDE embedding; Automatic writes.  
**Tag:** **EVIDENCE** / **FEASIBLE**.

### 5.6 Synthesis across products

| Pattern | Shipping consensus | ADA |
|---------|-------------------|-----|
| Modes as policy dials | Universal | Keep Observe/Plan/Agent |
| Plan as first-class object | Cursor / Claude | Upgrade beyond free-text card |
| Build/Accept exits Plan | Cursor / Claude / M14 | Keep; deepen bindings |
| HITL on real tool args | Claude / Continue / Agents SDK / Consent Integrity | Keep `/api/confirm` |
| Clarification before act | Cursor Plan | Add protocol (charter + UX) |
| Todos materialize from plan | Cursor (plan todos) | Use `open_loops` `kind:todo` |
| Chat-only hope | Weaker products | Reject as Tier A target |

---

## 6. Best-of-breed: canonical intent→work loop (≤7 steps)

**Target loop for ADA** (minutes-scale work; campaigns hand off to M06):

| Step | Name | Who owns | Chat-only hope | Structured work objects |
|------|------|----------|----------------|-------------------------|
| **1** | **Interpret** | Cortex + charter (+ optional soft router) | Guess forever | Intent class: `social` \| `lookup` \| `task` \| `refuse` (+ work_needed?) |
| **2** | **Clarify?** | Cortex asks; operator answers | Silent assumption | ≤2 questions when required args missing (**AskToAct** shape) |
| **3** | **Select policy** | **Operator dial** (+ soft suggest); never model write-auth | Model “decides it’s Agent” | Observe / Plan / Agent enforced by gateway |
| **4** | **Plan artifact** | Plan mode → durable/reviewable steps | Prose in scrollback | `plan_id` + `steps[]` + status `proposed\|accepted\|rejected` |
| **5** | **Accept / bind** | HUD Accept **or** Confirm | Rubber-stamp vibe | Accept → Agent cue + optional todo upsert; Confirm → `{tool,args,confirmed}` |
| **6** | **Execute** | ReAct under gateway | Ungrounded claims | Observations + receipts; max_steps |
| **7** | **Receipt → update** | Harness + open_loops | “Done!” with no metal | JSONL + todo/campaign stage update; false-completion check |

```text
 chat-only hope:     utterance ──► model vibes ──► maybe tools ──► "done"
 structured loop:    utterance ──► interpret/clarify ──► policy
                         │
                         ├── Plan artifact ──► Accept ──┐
                         │                              ├──► gateway execute
                         └── Agent + Confirm bind ──────┘         │
                                                                   v
                                                              receipts + todos
```

**One sentence:** *ADA should treat multi-step work as objects (plan + todos + receipts) gated by operator policy — not as a longer chat.*

---

## 7. Map to ADA + upgrade plan

### 7.1 Gap → change table

| Gap | METAL today | Proposed change | Core vs HUD vs memory | Tier |
|-----|-------------|-----------------|------------------------|------|
| Plan is free text | Plan card wraps assistant body | **Plan artifact**: structured steps (JSON in SSE and/or `runs/` event + optional YAML); card renders steps | harness emit + HUD | **A** |
| Accept only re-prompts | Accept → Agent + prose cue | Accept also **upserts `kind:todo`** steps (pending) from plan; Agent marks done via tools/receipts | memory + HUD | **A** |
| Mode switch clears history | `_ensure_session` resets history | **Preserve history across Plan↔Agent** for same chat session (still end run writer cleanly); or pin `plan_id` in cookie/session | harness/HUD | **A** |
| No clarify protocol | Model may ask ad hoc | Charter: task underspec → ask ≤2; HUD optional “Needs clarify” chip | charter + light HUD | **A** |
| Intent ≠ mode | Dropdown only | Soft **suggest mode** from heuristics/keywords (UI chip) — operator still confirms; **no auto Agent writes** | HUD (+ tiny helper) | **B** |
| Intent classifier | Register classes only | Optional thin router (rules first; model last) for suggest-only | harness | **B** |
| False completion | Model stops when it wants | Require receipt or todo status for “task done” claims in Agent task class | charter + eval smokes | **A** |
| Confirm coverage | Subset of tools | Expand confirm allowlist as new write tools appear | gateway/HUD | **B** |
| Plan on disk | Absent | Optional `plans/` or open_loops-linked plan for resume after sleep | memory | **B** |
| Smart auto-route to Plan | Absent | Suggest Plan on multi-step novelty (Cursor-like) | HUD | **B** |
| Pause/resume mid-ReAct | Confirm is post-tool | Queue pending tool call id in session (Agents SDK shape) without dropping run | harness | **C** |
| Life-ops packaging | — | Consumer of this loop later | — | **OUT** |

### 7.2 Design locks (proposed — subject to OPEN)

| Topic | Lock proposal | Tag |
|-------|---------------|-----|
| **Plan mode** | Becomes a **real plan artifact** (not stub prose-only). Minimum: ordered `steps[]` with text + optional tool hints; status lifecycle. | **EVIDENCE** + **FEASIBLE** |
| **Todos** | Prefer **`open_loops` `kind:todo`** — no second store in Tier A. Campaigns remain M06. | **METAL** / **FEASIBLE** |
| **Intent → policy** | Intent may **suggest** Observe/Plan/Agent; **operator dial + gateway** authorize. Model never self-arms writes. | **POLICY** |
| **Accept binding** | Plan Accept = policy transition + execute cue (+ todo materialization). **Does not** execute write tools by itself. Tool consent remains Confirm / Agent gateway path. | **POLICY** / Consent Integrity |
| **Confirm binding** | Always gateway `{tool,args}` (+ `confirmed=true` re-drive). Never approve model summary alone. | **POLICY** |
| **Operator-hardcoded vs proposed** | Hardcoded: modes, ToolSpec, confirm ladder, Tailscale/session, quiet hours, secrets. **Proposed then accepted:** plan steps, todo text, FACT content, campaign stages. | **POLICY** |
| **Workflow vs agent** | Default = Anthropic simplicity: **workflow gates** (clarify/plan/accept) wrapping one ReAct agent — not a swarm. | **EVIDENCE** |

### 7.3 What stays outside the model

```text
OPERATOR / CODE                          MODEL (Gemini)
─────────────────────────                ─────────────────────────
mode dial + session auth                 propose plan text/steps
gateway + ToolSpec                       choose tools under allowlist
Confirm bind {tool,args}                 narrate (untrusted for consent)
open_loops / runs/ truth                 suggest todo wording
charter + register contracts             follow contracts (soft)
```

---

## 8. Falsifiers (F1–F10)

| # | Falsifier | Pass if |
|---|-----------|---------|
| F1 | Gateway authority | Plan turn cannot append FACT / upsert write without mode change; Accept alone does not call write tools |
| F2 | Consent Integrity | Confirm UI args === gateway pending args; confirm executes same tool with `confirmed=true` |
| F3 | Plan artifact | After Plan turn, UI (or receipt) shows structured steps — not only undifferentiated prose |
| F4 | Todo materialize | Accept creates/updates `open_loops` `kind:todo` entries matching plan steps (or explicitly records “no todos”) |
| F5 | Mode continuity | Plan→Accept→Agent keeps enough context to execute without “what plan?” amnesia (history pin or plan_id) |
| F6 | Intent ≠ authority | Soft mode suggest never grants write; Observe stays read-only |
| F7 | Clarify budget | Underspecified task asks ≤2 clarifiers before inventing args |
| F8 | Receipts over vibes | Task “done” claim cites receipt_id and/or todo status=done |
| F9 | No second brain | Client never executes tools locally; only `/api/chat` + `/api/confirm` + `/api/plan/accept` |
| F10 | Horizon handoff | Multi-day work creates/updates `kind:campaign` rather than immortal chat plan |

---

## 9. OPEN for Aryan — **LOCKED** (P0+P1 defaults)

| # | Question | Resolution |
|---|----------|------------|
| 1 | Plan storage | **LOCKED:** SSE+JSONL Tier A (no YAML plan store) |
| 2 | Accept → todos | **LOCKED:** auto-upsert `kind:todo` via `POST /api/plan/accept` |
| 3 | Mode switch history | **LOCKED:** preserve history Plan↔Agent; wipe when Observe involved |
| 4 | Soft mode suggest | **LOCKED:** P1 keyword chip (`#mode-suggest`) — never auto-write |
| 5 | Clarification | **LOCKED:** charter-only (≤2); no HUD clarify affordance |
| 6 | `plan_write` tool | **LOCKED:** no — parse assistant JSON/list in harness |
| 7 | First coding slice | **LOCKED:** P0+P1 shipped this implement |

---

## 10. Ordered implement-next

### P0 — structured plan + accept → todos — **SHIPPED**

| # | Work | Status |
|---|------|--------|
| 1 | Plan artifact schema | **METAL** `harness/plan_artifact.py` |
| 2 | Emit on Plan completion | **METAL** loop + charter |
| 3 | HUD Plan card from steps | **METAL** `stream.js` |
| 4 | Accept → todos + Agent cue | **METAL** `/api/plan/accept` |
| 5 | Plan↔Agent history preserve | **METAL** `chat_service._ensure_session` |
| 6 | Smokes F1–F5, F8 | **METAL** `tests/test_m15_intent_work_loop.py` |

### P1 — clarify + verify + confirm + suggest — **SHIPPED**

| # | Work | Status |
|---|------|--------|
| 1 | Charter clarify ≤2 | **METAL** |
| 2 | Done cites receipt | **METAL** charter + `eval.py` |
| 3 | `pending_id` confirm bind | **METAL** |
| 4 | Soft mode-suggest chip | **METAL** |

### P2 — deeper work objects — **deferred**

| # | Work | Owner |
|---|------|-------|
| 1 | Persist plans to ada-data; resume by `plan_id` | memory |
| 2 | Link todos ↔ campaign stages when user says “make this a campaign” | M06 bridge |
| 3 | Mid-loop pause/resume (SDK-like) without dropping session | harness |
| 4 | Intent router beyond heuristics (only if measured need) | harness |

**Stop before:** Funnel; LangGraph rewrite; multi-agent default; life-ops UI; deleting gateway; unsupervised multi-day Agent.

---

## 11. Relationship to other cards

| Card | Owns | Boundary with M15 |
|------|------|-------------------|
| **M02** | ReAct loop, gateway, runs/ | M15 adds **work-object workflow** around the loop |
| **M06** | Campaigns STATUS/stages/wake | M15 feeds short todos; multi-day → campaign |
| **M13/M14** | Chrome + Plan Accept + Confirm surfaces | M15 specifies **what** those surfaces bind to |
| **M04/M10** | FACTS / understanding user | Informs interpret; does not authorize work |
| **M05** | Register intent→class (voice) | Formatting/social gates — **not** policy mode |

---

## 12. References

### Academic / engineering
- Yao et al., ReAct (2022) — https://arxiv.org/abs/2210.03629  
- Anthropic, *Building Effective Agents* (2024) — https://www.anthropic.com/engineering/building-effective-agents  
- LangChain, Plan-and-Execute — https://www.langchain.com/blog/planning-agents  
- Shi et al., Progent (2025) — https://arxiv.org/abs/2504.11703  
- Consent Integrity (2026) — https://arxiv.org/abs/2606.02668  
- AskToAct (2025) — https://arxiv.org/abs/2503.01940  
- Structured Uncertainty / SAGE-Agent (2025) — https://arxiv.org/abs/2511.08798  
- Horizon Gap (2026) — https://arxiv.org/abs/2608.06663  
- Select-Then-Decompose (2025) — https://arxiv.org/abs/2510.17922  

### Products
- Cursor Plan Mode — https://cursor.com/docs/agent/plan-mode  
- Claude Code permission modes — https://code.claude.com/docs/en/permission-modes  
- ChatGPT agent intro — https://openai.com/index/introducing-chatgpt-agent  
- OpenAI Agents SDK HITL — https://openai.github.io/openai-agents-python/human_in_the_loop/  
- Continue Plan / Agent — https://docs.continue.dev/ide-extensions/agent/plan-mode  

### Internal
- [`M02_CHAT_HARNESS.md`](./M02_CHAT_HARNESS.md), [`M06_CAMPAIGNS_LONG_HORIZON.md`](./M06_CAMPAIGNS_LONG_HORIZON.md), [`M14_AGENT_SURFACE.md`](./M14_AGENT_SURFACE.md)  
- [`../02_CONSTITUTION.md`](../02_CONSTITUTION.md)  
- Code: `src/ada/harness/{loop,plan_artifact}.py`, `src/ada/tools/gateway.py`, `src/ada/hud/{chat_service,routes_api}.py`, `src/ada/hud/static/js/{stream,mode,api}.js`, `src/ada/memory/open_loops.py`, `src/ada/cortex/charter.py`, `src/ada/runs/append.py`, `tests/test_m15_intent_work_loop.py`

---

### Lens cheat-sheet

| Claim | Lens |
|-------|------|
| Structured plan + todos beat chat hope | **EVIDENCE** + **FEASIBLE** |
| Model self-selects Agent and writes | **FANFICTION** / **POLICY** deny |
| Gateway + Confirm stay authoritative | **POLICY** + **METAL** |
| Reuse `open_loops` todos | **METAL** / **FEASIBLE** |
| Adopt LangGraph as brain | **Won’t-chase** unless forced |
| Life-ops product in this card | **OUT** — later consumer |
| Cursor file-edit parity | **FANFICTION** for ADA metal |

---

*End of M15 v2. OPEN locked; P0+P1 metal shipped. P2 deferred.*
