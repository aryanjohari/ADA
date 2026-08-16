# M16 — First Package (self · you · Pi-doer · track)

**Status:** **metal shipped Phase 0 + Phase 1** (2026-08-16). Design card remains v1.1 authority. Phase 2 still deferred. See [`M16_OPERATOR_NOTE.md`](./M16_OPERATOR_NOTE.md).  
**Date:** 2026-08-16 (v1.2 — Phase 0/1/2 + adoption; metal Phase 0+1; remind/ping field lock)  
**Host:** `ada-pi5` (Raspberry Pi 5 Model B Rev 1.1, Debian trixie, ~8 GiB RAM)  
**Client:** Aryan’s Mac over Tailscale Serve (control plane)  
**Branch:** `rewrite/v1-body`  
**Depends on:** [`../00_ASSISTANT_RESEARCH.md`](../00_ASSISTANT_RESEARCH.md), [`../02_CONSTITUTION.md`](../02_CONSTITUTION.md), [`../../VISION.md`](../../VISION.md), [`M02_CHAT_HARNESS.md`](./M02_CHAT_HARNESS.md), [`M04_MEMORY_DREAM.md`](./M04_MEMORY_DREAM.md), [`M06_CAMPAIGNS_LONG_HORIZON.md`](./M06_CAMPAIGNS_LONG_HORIZON.md) (**related consumer later — not v1 center**), [`M10_MEMORY_KNOWLEDGE.md`](./M10_MEMORY_KNOWLEDGE.md), [`M12_BODY_PROPRIOCEPTION.md`](./M12_BODY_PROPRIOCEPTION.md), [`M14_AGENT_SURFACE.md`](./M14_AGENT_SURFACE.md), [`M15_INTENT_WORK_LOOP.md`](./M15_INTENT_WORK_LOOP.md), [`../01_BODY.md`](../01_BODY.md)

**Name justification:** **`M16_FIRST_PACKAGE.md`**. The north-star question is not another organ (“memory,” “HUD,” “campaigns”) but the **minimal coherent capability package** that makes a fresh ADA feel like a **personal embodied agent someone would run daily** — not a chatbot bolted to sensors.  
- **Self** = non-empty self-understanding at birth (identity + syllabus heads + constitution-grounded charter).  
- **You** = know + track the operator (prefs / people / notes + dues).  
- **Pi-doer** = act as *this* machine (body honesty + local artifacts under policy).  
- **Track** = due/remind surface with one felt actuator.  
All under the existing **M15 intent→work loop** (plan → accept → todos → execute → receipt).  

Rejected titles: `M16_PRODUCT` (sounds ship-to-market), `M16_JARVIS` (**FANFICTION**), `M16_LIFE_OPS` (boils ocean; collides with M06), `M16_MEMORY_UX` (too narrow — misses Pi-doer).

### Changelog

| Ver | Date | Notes |
|-----|------|-------|
| **1.2** | 2026-08-16 | **Remind/ping field fix:** todo upsert with `next_wake_at` fails closed (use `remind_at`/`due_at`); ToolSpec + charter recipe; F13. |
| **1.1** | 2026-08-16 | **Phase 0 LOCKED** (former P0 base). Added adoption lens, Phase 1 (habit), Phase 2 (compound), ops IA, ≥8 Pi-native creative ideas, refreshed falsifiers/OPEN/implement-next. Phase 0 content not replaced. |
| 1.0 | 2026-08-16 | Initial first-package design (self · you · Pi-doer · track). |

**Phase map (v1.1):**

| Phase | Goal | Status |
|-------|------|--------|
| **0 — Base** | Coherent daily-capable package (self/know/track/Pi-doer under M15) | **METAL shipped** (2026-08-16) |
| **1 — Habit** | Someone opens her *tomorrow* (felt return loops) | **METAL shipped** (2026-08-16) |
| **2 — Compound** | Habit compounds (inbox, sync, campaigns-as-consumers, learning loops) | Design — ruthlessly tiered |

**METAL present (ingredients only — package not assembled):** M00–M15 organs — body proprioception, dual-store memory, cites library, open_loops todos/campaigns, Dream manage, HUD agent surface, M15 plan artifact + Accept→todos. **Hollow for daily package:** empty-feeling operator memory, no todo `due_at`, no push notify, no artifact writer, campaigns are lab STATUS not “life ops,” no birth syllabus beyond identity+prefs stubs.

**OUT unless EVIDENCE+FEASIBLE force rethink:** Funnel; local main-LLM cortex; consciousness; Cursor-parity coding IDE; Google-clone search; n8n brain; unsupervised multi-day missions; feature parity with ChatGPT / every Pi assistant on GitHub; Mem0/Letta/HA as the design; always-listen; wallet; 14 chat channels.

---

## 1. Slice rule + won’t-chase

**North-star product question.** ADA today is roughly a **chatbot with a body and memory**. What **minimal, coherent capability package** makes her a **personal embodied agent** someone would actually run daily — such that a “fresh ADA” boots with **non-empty self-understanding**, can **know and track the operator**, and can **do real work on the Pi** (artifacts + body ops + notify), under the existing **small DIY ReAct / intent→work loop (M15)**?

Work **backward** from iconic assistants (Jarvis / Justine *as capability abstractions*) and **forward** from shipping agents (Cursor, Claude, … as *work-loop / UX* references). Then design what is **uniquely ADA** on this Pi — **not** “everything the market has.” Prefer fewer capabilities that **compound** with embodiment, receipts, dual-store, Tailscale, and gateway policy.

**Slice rule:** admit **design** of the first running product package:

1. **Base self** — seed syllabus / self-model so she is not empty at birth  
2. **Know operator** — prefs, people, notes (learn-over-time shape, not CRM)  
3. **Track operator** — dues/reminders/tasks; optional notify  
4. **Pi-doer** — act as this machine: body honesty + **local artifacts** (doc/summary from links or capability dump) under allowlist + receipts  
5. How these plug into **M15** (plan → accept → todos → execute → receipt)

Cross-link later LH campaigns, phone photo/receipt inbox, full calendar sync, Office/LaTeX, HA, voice — **tier them**; do not make them P0 gates.

**Default: research/design only** — no large implement unless OPEN locks a thin P0.

**Won’t-chase as v1 package**

| Out | Why |
|-----|-----|
| Funnel / public ingress | **POLICY** |
| Local main-LLM cortex | **FEASIBLE** fail as quality cortex; VISION lock |
| Consciousness / soul / SOUL.md | **FANFICTION** / constitution §2 |
| Cursor-parity coding IDE | Wrong actuators; map analogues only (M15) |
| Google-clone search / open crawl | **POLICY** — allowlist + cites library |
| n8n / Celery as brain | Wrong control plane |
| Unsupervised multi-day missions | Horizon Gap; hand to M06 later |
| Feature parity with ChatGPT / Chango / GitHub Pi assistants | Coverage trap; coherence wins |
| “Just add Mem0 / Letta / HA” | Stack transplant ≠ ADA geometry |
| Always-listen / wallet / 14 channels | Creep + ops tax + trust rings (**POLICY**) |
| Fake syllabus as LH campaigns | M06 campaigns ≠ product center; smoke STATUS ≠ life ops |

```text
  fresh install
        |
        v
  [birth pack]  identity + syllabus heads + prefs schema
        |         (operator bio stays in ada-data, not git)
        v
  daily loop (M15)
        |
        +-- know you: FACTS prefs/people/notes
        +-- track you: open_loops todos + due surface (+ optional notify)
        +-- Pi-doer: body_* + artifact_write (md/csv) + web→cites→doc
        |
        v
  receipts / runs/ / Body drawer
        |
        x Funnel  x AGI theater  x Cursor IDE  x campaign-as-product
```

---

## 2. Lens tags

| Tag | Meaning here |
|-----|--------------|
| **FANFICTION** | Movie Jarvis omniscience; silent autonomy; “she just knows”; consciousness; always-watching home |
| **EVIDENCE** | Papers + shipping agent UX patterns (memory, HITL, artifacts, reminders) |
| **FEASIBLE** | Pi 5 ~8GB; Gemini cortex; Python ASGI HUD; Mac over Tailscale; YAML/HDD stores; no Node-on-Pi |
| **POLICY** | Constitution modes; confirm ladder; Tailscale-only control plane; no Funnel; secrets never-to-cloud; quiet hours |
| **METAL** | What exists in this repo / on `ada-data` today |

---

## 3. METAL inventory (honest — 2026-08-16)

### 3.1 What she can already do (ingredients)

| Domain | Capability | Metal | Hollow? |
|--------|------------|-------|---------|
| **Self-report** | `body_vitals` / `whoami` / `story` / `doctor` / `explain` / allowlisted `body_readonly_cmd` | **METAL** (M00/M12) | Thin *syllabus* of “who I am as agent” beyond birth card |
| **Identity** | `identity.yaml` birth-once; charter `identity_summary()` | **METAL** | No shipped “agent syllabus” / capability map for chat |
| **Memory R** | `memory_facts_*`, worldview search, boot FACT slice (prefs + campaign/todo heads) | **METAL** (M04) | Operator notes/people nearly empty stubs |
| **Memory W** | FACT append; overwrite→confirm; WORLDVIEW write with cites; Dream whitelist merge | **METAL** | Learn-over-time UX not packaged |
| **Todos / loops** | `open_loops` `kind:todo` + `kind:campaign`; list/upsert tools; M15 Accept→todos | **METAL** | Todos lack `due_at`; no due-sorted HUD strip |
| **Web → cites** | Allowlisted `web_fetch` + cite library search/get | **METAL** (M07/M10) | Fetch≠artifact; no “write me a doc on disk” |
| **Plan accept** | Plan artifact SSE+JSONL; Accept→todos; Plan↔Agent history; Confirm `pending_id` | **METAL** (M15) | Work objects exist; *product jobs* not wired |
| **HUD** | Chat-home, mode dial, Plan/Confirm cards, Body drawer, Tailscale Serve | **METAL** (M14) | No due strip / artifact list as first-class chrome |
| **Proactivity suppress** | Quiet hours + `mute_proactivity` helpers | **METAL** | Suppress exists; **push notify does not** |
| **Brief timer** | `deploy/systemd/ada-brief.{timer,service}` → `ada campaigns check` | **METAL** pointer | Optional; surfaces campaigns, not a daily “you” package |
| **Dream** | Seal + capped manage + dual-store ethics | **METAL** (M04/M11) | Consolidation ≠ birth self; not a product face |

### 3.2 Hollow / gap summary (package blockers)

| Gap | Severity for “daily personal agent” |
|-----|-------------------------------------|
| Fresh feel ≈ empty prefs + stub `people/aryan.yaml` + no syllabus | **High** — “chatbot with sensors” |
| No `due_at` / due-sorted track surface | **High** — track without dues is a list, not a life loop |
| No push/Mac notify actuator | **Medium** — HUD-open is enough for Tier A feel; push is Tier B |
| No artifact writer (md/csv on disk) | **High** — Pi-doer without files is narration |
| Campaigns present but lab-shaped (ada-build / field-papers) | **Medium** — don’t center product on M06 smoke STATUS |
| Body manage writes (beyond reads) | **Low for P0** — honesty first; confirm-gated manage later |
| No birth pack in *repo* (templates) vs *ada-data* (private) | **High** for “fresh ADA” story |

### 3.3 Actuator honesty (what “do” means today)

| Claim | Truth | Tag |
|-------|-------|-----|
| She can tell truth about the Pi | Yes — typed organs + receipts | **METAL** |
| She can remember prefs/people | Schema yes; content thin | **METAL** / hollow |
| She can create todos from Plan Accept | Yes | **METAL** (M15) |
| She can write a report file for Aryan | **No tool** | gap |
| She can ping phone/Mac | **No** | gap |
| She can run arbitrary shell / apt / HA | Denied | **POLICY** |
| She can browse the open web | Denied; allowlist only | **POLICY** |

---

## 4. What would make ADA actually good (not another wrapper)

**Mandate.** Differentiation is non-negotiable. ADA wins by **embodiment + trust geometry already in this repo**, not by matching ChatGPT’s feature list.

### 4.1 Compounding advantages (keep and productize)

| Advantage | Why it compounds | Tag |
|-----------|------------------|-----|
| **Body organs + doctor truth** | Claims about host/RAM/disk/throttle cite metal — vibes fail Falsifiers | **METAL** / **POLICY** |
| **Dual-store FACTS vs WORLDVIEW + Dream manage** | Standing truth vs interpretive digests; overnight librarian, not “memory vibes” | **METAL** / **EVIDENCE** |
| **Gateway outside the model + Consent Integrity confirms** | Model proposes; `{tool,args}` bind; Plan Accept ≠ tool consent | **POLICY** / **EVIDENCE** |
| **Allowlisted web + durable cites** | Library, not infinite browse; cite:c_… ids in answers | **METAL** / **POLICY** |
| **Tailscale-only control plane + Mac remote feel (M14)** | Private always-on body; Serve HTTPS; no Funnel | **METAL** / **POLICY** |
| **Intent→work objects (M15)** | Plan steps + todos + receipts — not mode-dropdown theater | **METAL** / **EVIDENCE** |
| **Campaigns as later multi-session STATUS** | Honest long-horizon when earned — **not** fake syllabus LH in v1 | **METAL** (M06) deferred as product center |

**One sentence:** *ADA is good when the Pi owns truth, the gateway owns permission, and chat is a steerable work loop over durable objects — not when she speaks like a cloud chatbot with extra YAML.*

### 4.2 Market features to refuse or defer (even if popular)

| Feature | Disposition | Reason |
|---------|-------------|--------|
| Always-listen room mic | **Refuse as v1** / Tier C aspiration | **POLICY** + no mic metal; creep |
| Wallet / payments | **Refuse** until constitution amendment | **POLICY** §8.3 financial deny |
| 14 chat channels (Slack+WhatsApp+Discord+…) | **Defer** | Control-plane sprawl; Tailscale HUD is the channel |
| Vendor search as brain | **Refuse** | Allowlist + cites; Google-clone OUT |
| Mem0 / Letta cloud memory as core | **Refuse as design** | Dual-store + Dream already teach harder-correct; optional later adapter only |
| Home Assistant day-one | **Defer** Tier C | New actuator class; confirm ladder |
| Cursor-parity IDE / general shell | **Refuse** | Wrong body; body_readonly_cmd allowlist only |
| Unsupervised multi-day “missions” | **Refuse** | Horizon Gap; M06 wake/STATUS later |
| Personality SOUL.md / consciousness UI | **Refuse** | Constitution §2 |
| Funnel / public URL | **Refuse** | **POLICY** |
| PDF/Office/LaTeX authoring suite | **Defer** | Artifact md/csv first |
| Full Google Calendar sync | **Defer** | due-list first; sync is ops+OAuth tax |
| Phone photo / receipt inbox | **Defer** | Later ingest path; not P0 gate |
| Multi-agent swarm | **Refuse default** | Constitution / M06 lock |

### 4.3 Coherence over coverage

Ship **four** compounding faces — self, know-you, track-you, Pi-doer — under **one** M15 loop as **Phase 0**. Phase 1/2 may add habit surfaces and ops depth **on top of** those faces — not a fifth unrelated product (Slack suite, HA day-one, calendar clone).

---

## 5. Backward abstraction (fiction → ≤10 capabilities)

Jarvis / Justine as **capability abstractions**, not movie AGI.

| # | Abstract capability | Fiction cue | FANFICTION vs FEASIBLE Tier A (this Pi package) |
|---|---------------------|-------------|--------------------------------------------------|
| 1 | **Named durable self** | “I am JARVIS / Justine” | **FEASIBLE A** — birth card + syllabus seed |
| 2 | **Truthful body status** | “Systems check” | **FEASIBLE A** — **METAL** body organs |
| 3 | **Know the operator** | “Knows Tony / Ned” | **FEASIBLE A** — prefs/people/notes (thin CRM **OUT**) |
| 4 | **Track commitments** | Reminders / “don’t forget” | **FEASIBLE A** — todos + due; push notify **B** |
| 5 | **Do work that leaves artifacts** | Prep briefs, files, summaries | **FEASIBLE A** — md/csv on Pi; PDF later |
| 6 | **Permissioned action** | “Shall I proceed?” | **FEASIBLE A** — gateway + Confirm (**METAL**) |
| 7 | **Bounded proactivity** | Speaks up when useful | **FEASIBLE A** — due surface + quiet hours; not always-on chatter |
| 8 | **Research with receipts** | Pull files / papers | **FEASIBLE A** — allowlist fetch→cites→doc |
| 9 | **Home/environment omniscience** | House control / cameras | **FANFICTION** for v1 → Tier **C** (HA later) |
| 10 | **Voice omnipresence** | Always listening banter | **FANFICTION** for v1 → Tier **C** (PTT first if ever) |

**Abstraction takeaway:** iconic feel comes from **(1)+(2)+(3)+(4)+(5)+(6)** compounding — not from (9)+(10). ADA already has strong (2)+(6); package fills (1)/(3)/(4)/(5).

---

## 6. Forward survey (shipping agents) — ≥5

Research date: **2026-08-16**. Extract **patterns**; map or reject for ADA. Do **not** copy stacks.

### 6.1 Cursor Agent (+ Plan Mode)

| Pattern | Shipping | ADA map / reject |
|---------|----------|------------------|
| Clarify → plan artifact → Build | [Plan Mode](https://cursor.com/docs/agent/plan-mode) | **Map** — M15 Accept (**METAL**) |
| Workspace file edits | Product | **Reject** as IDE parity; **map** to Pi artifact write |
| Diffs / checkpoints | Product | **Defer** — receipts + Body x-ray first |

**Tag:** **EVIDENCE**; analogues **FEASIBLE**.

### 6.2 Claude (Projects / Artifacts / Code permissions)

| Pattern | Shipping | ADA map / reject |
|---------|----------|------------------|
| Projects = durable context pack | Product memory | **Map** — birth pack + FACTS/people, not cloud Projects |
| Artifacts = side-panel durable outputs | Artifacts UX | **Map** — files under `artifacts/` + HUD list |
| Plan permission staging | [Permission modes](https://code.claude.com/docs/en/permission-modes) | **Map** — Observe/Plan/Agent + Confirm |

**Tag:** **EVIDENCE** / **POLICY** alignment on staging.

### 6.3 ChatGPT Agent / memory / tasks

| Pattern | Shipping | ADA map / reject |
|---------|----------|------------------|
| Agent mode for multi-step online work | [Intro](https://openai.com/index/introducing-chatgpt-agent) | **Map** pattern (arm + pause); **reject** virtual browser / Funnel-shaped reach |
| Cross-session memory | Product | **Map** dual-store — **reject** opaque cloud memory as SoT |
| Tasks / reminders | Product | **Map** open_loops dues — **reject** calendar clone as P0 |

**Tag:** **EVIDENCE** (product); **FEASIBLE** as pattern only.

### 6.4 Lindy (personal work assistant)

| Pattern | Shipping | ADA map / reject |
|---------|----------|------------------|
| Persistent “memories” across runs | [Lindy memory](https://docs.lindy.ai/fundamentals/lindy-101/memory) | **Map** FACT append / prefs — **reject** email/CRM autopilot as v1 |
| Context accrues per task run | Docs | **Map** M15 plan+todos+receipts |
| Inbox/calendar actuators | Product | **Defer** — new egress classes |

**Tag:** **EVIDENCE**; life-ops packaging **OUT** of P0.

### 6.5 Continue.dev (Plan / Agent tool policies)

| Pattern | Shipping | ADA map / reject |
|---------|----------|------------------|
| Plan = read-only tool set | [Plan mode](https://docs.continue.dev/ide-extensions/agent/plan-mode) | **Map** — gateway already |
| Per-tool Ask First | Docs | **Map** — `needs_confirm` |

**Tag:** **EVIDENCE** / **FEASIBLE**.

### 6.6 Edge / notify practice (ntfy + Tailscale)

| Pattern | Shipping | ADA map / reject |
|---------|----------|------------------|
| HTTP pub-sub ping to phone | [ntfy.sh](https://ntfy.sh/); Claude+ntfy+Tailscale writeups | **Map as Tier B** push actuator — topic secret in `secrets/`, quiet hours honor, first-enable confirm |
| Public ntfy.sh without auth | Common DIY | **Reject default** — prefer Tailscale-hosted or tokenized topic (**POLICY**) |

**Tag:** **EVIDENCE** (ops practice); **FEASIBLE** on Pi; new egress ring → ladder.

### 6.7 Synthesis — steal vs refuse

| Pattern | Consensus | ADA |
|---------|-----------|-----|
| Plan → accept → execute | Cursor / Claude / M15 | Keep |
| Durable personal memory | Lindy / ChatGPT / Mem0 papers | Keep **dual-store** — refuse vendor memory as core |
| Artifacts as first-class outputs | Claude | Add md/csv writer |
| Reminders / tasks | ChatGPT / calendars | due-list first |
| Multi-channel always-on | Consumer assistants | Refuse |
| Home automation day one | Pi hobbyists | Defer |

---

## 7. Evidence survey (≥5 cites) — design lineage

Every row is **lineage**, not homework to reimplement.

| # | Source | Claim | Lens | ADA takeaway |
|---|--------|-------|------|--------------|
| 1 | **Zhang et al., agent memory survey (2024)** — [arXiv:2404.13501](https://arxiv.org/abs/2404.13501); 2026 surveys [2603.07670](https://arxiv.org/abs/2603.07670), [Anatomy of Agentic Memory](https://arxiv.org/html/2602.19320) | Cross-session memory differentiates personal agents; context windows fail multi-day | **EVIDENCE** | Birth pack + FACTS/people/notes; boot slice stays budgeted |
| 2 | **Mem0 (2025)** — [arXiv:2504.19413](https://arxiv.org/abs/2504.19413) | Extract/consolidate/retrieve beats full-history stuffing; latency/token wins | **EVIDENCE** | Steal **shape** (awake write + Dream manage); **do not** adopt Mem0 as product core |
| 3 | **Consent Integrity / LITL (2026)** — [arXiv:2606.02668](https://arxiv.org/abs/2606.02668) | Approving model summaries is forgeable; bind UI to boundary `{tool,args}` | **EVIDENCE** / **POLICY** | Artifact write + notify enable + FACT overwrite stay Confirm-bound |
| 4 | **Anthropic, Building Effective Agents (2024)** — [post](https://www.anthropic.com/engineering/building-effective-agents) | Prefer workflows around tools; simplest path; transparent planning | **EVIDENCE** / **FEASIBLE** | Package = thin workflows on M15 — not a new framework |
| 5 | **Horizon Gap (2026)** — [arXiv:2608.06663](https://arxiv.org/abs/2608.06663) | Long-horizon ≠ long-context; false completion / drift | **EVIDENCE** | Minutes-scale package via todos+receipts; multi-day → M06 later |
| 6 | **Yao et al., ReAct (2022)** — [arXiv:2210.03629](https://arxiv.org/abs/2210.03629) | Interleave act + observation | **EVIDENCE** / **METAL** | Keep harness; artifacts/body claims need observations |
| 7 | **Agents That Know Too Much (2026)** — [arXiv HTML](https://arxiv.org/html/2606.26627) | Personal agents = intimate data-paths | **EVIDENCE** / **POLICY** | Operator bio in `ada-data` only; secrets never-to-cloud; Tailscale control plane |
| 8 | **Auto-Dreamer (2026)** — [arXiv HTML](https://arxiv.org/html/2605.20616) | Offline consolidation timescale | **EVIDENCE** | Dream stays manage; not consciousness; not birth syllabus replacement |

**EVIDENCE verdict:** a daily personal agent is a **small set of durable objects + permissioned actuators + honest body**, not a larger system prompt or a vendor memory SaaS.

**FANFICTION reject:** “install Letta/Mem0/HA and she becomes Jarvis.”

---
## 8. Capability matrix — Phase 0 / 1 / 2

Phase column: **0** = locked base; **1** = habit; **2** = compound. Phase 0 rows are **non-negotiable**.

| Capability | User-visible win | METAL today | Gap | Store / tool / HUD | Phase | Depends on M15? |
|------------|------------------|-------------|-----|-------------------|-------|-----------------|
| **Base self seed** | Fresh ADA answers “who are you / what can you do?” from metal+syllabus | Birth card + charter identity | Syllabus heads; capability map seed | Repo templates → `ada-data` on birth; charter boot | **0** | Soft |
| **Prefs** | “Remember I prefer …” sticks | `prefs.yaml` + tools | Packaged learn UX | `memory_facts_*` | **0** | No |
| **People / notes** | Knows operator + named others (not CRM) | `people/` stub | Notes hygiene | `facts/people/*.yaml` | **0** | No |
| **Due / track** | “What’s due?” is real | Todos exist | `due_at` + due query + HUD strip | `open_loops` `kind:todo` | **0** | **Yes** |
| **Notify local** | Brief/check surfaces dues | Quiet suppress + `ada-brief` pointer | Extend check JSON + HUD | Boot + brief | **0** | Soft |
| **Pi artifact write** | Link/ask → md/csv on disk + receipt | cites + scratch only | `artifact_write` + path jail | `/mnt/ada-data/artifacts/` | **0** | **Yes** often |
| **Body honesty** | Host questions cite organs | M12 tools | — | `body_*` | **0** | No |
| **Web→doc flow** | Allowlisted fetch → summary artifact | `web_fetch` + cites | Charter recipe | cites + artifacts | **0** | **Yes** |
| **Today home strip** | Open HUD → dues/pending/artifacts at a glance | Chat-home only | `#today` strip | HUD (M14 shell) | **1** | Soft |
| **Push notify (ntfy)** | Phone/Mac ping pulls you back | None | Actuator + prefs + Confirm first enable | `notify_*` + secrets | **1** | Soft |
| **Ops schema polish** | `remind_at`, people links, artifact link, notify prefs | Thin todos | Extend `open_loops` + prefs | Same files — no new DB | **1** | **Yes** |
| **Morning brief ritual** | Timer → attributable brief ready | Timer pointer | Productize brief payload | `ada-brief` + HUD | **1** | Soft |
| **Artifact shelf** | Lasting handoffs visible outside chat | — | List + open in Body drawer | artifacts/ + HUD | **1** | Soft |
| **Light events** | Time-window commitments without Google Calendar | — | `kind:todo` + `starts_at`/`ends_at` | `open_loops` | **1** | Optional |
| **Capture inbox** | Drop file → morning route | scratch exists | `inbox/` watch + brief | scratch/inbox | **2** | Soft |
| **Campaigns-as-consumers** | Multi-day STATUS uses package objects | M06 metal | Bridge todos↔stages | `kind:campaign` | **2** | Optional |
| **Calendar sync** | External gravity | — | OAuth + importer | New card | **2** | Soft |
| **Dream learn-you digest** | “What I solidified about you” | Dream manage | Operator-facing digest surface | WORLDVIEW + brief | **2** | No |
| **Body manage actions** | Confirm-gated heal/service | Reads only | Allowlist manage tools | M12 follow-on | **2** | **Yes** + Confirm |
| **OUT Phase 0–1** | voice wake, HA, wallet, Funnel, IDE parity, 14 channels, Mem0-core | — | — | — | **OUT** | — |

---

## 8b. Adoption lens — why someone opens her again

**Problem.** Phase 0 can be coherent and still not habit-forming: demos ≠ daily return. Habitual opens come from **external triggers + low-friction action + visible durable outcome**, not from “the model is nicer.”

### 8b.1 What shipping products teach (brief)

| Mechanism | Where it shows up | Lens | ADA take |
|-----------|-------------------|------|----------|
| **Interrupt reminders** | Phone alarms, ntfy, ChatGPT tasks, habit apps | **EVIDENCE** | Phase **1** push (budgeted); Phase **0** = open-when-present only |
| **Calendar / time gravity** | Calendar, Motion, Reclaim | **EVIDENCE** | Phase **1** light events on todos; full sync **2** |
| **Inbox zero / capture** | Email, Things, capture→review | **EVIDENCE** | Phase **2** `inbox/` drop; Phase **1** chat capture→todo/artifact |
| **Streak / status** | Habit trackers; consistency > fragile streaks ([Fogg / Tiny Habits](https://behaviormodel.org/); consistency-rate guidance in habit+AI writeups) | **EVIDENCE** | Prefer **continuity pulse** (body healthy days, dues cleared) over shame streaks — **POLICY** no cruelty |
| **Artifact handoff** | Claude Artifacts, Cursor diffs, shared docs | **EVIDENCE** | Phase **0** write; Phase **1** **shelf** so outcomes outlive the scrollback |
| **Home-base UX** | Dock app, “Today” views, morning brief | **EVIDENCE** / **FEASIBLE** | Phase **1** Today strip on M14 chat-home — **not** ops dashboard (**METAL** M14 lock) |
| **Right-moment triggers** | Fogg B=MAP; Kairos-class signal/spark/facilitator routers | **EVIDENCE** | Steal **budget + quiet hours + cooldown**; reject always-fire cron (**POLICY** / mute) |
| **Anchor to existing routine** | Tiny Habits: after [anchor] → tiny behavior | **EVIDENCE** | Anchor = Mac Dock open / morning coffee → ADA Today; timer at `brief_time` |

**FANFICTION reject:** gamified XP, parasocial “she misses you,” always-watching face.

### 8b.2 Habit loops ADA can own

```text
  TRIGGER                    ACTION (Pi/HUD)              OUTCOME (visible)         RETURN REASON
  ─────────────────────      ───────────────────────      ─────────────────────     ─────────────────
  morning brief_time         open HUD / read brief        Today strip + dues        "what's waiting?"
  ntfy due ping (Ph1)        open Tailscale HUD           mark done / Accept plan   interrupt → close loop
  unfinished Plan card       Accept → todos               checklist on disk         work object unfinished
  artifact shelf stale?      ask for update / new doc     new file + receipt        handoff gravity
  body urgent flag           Body drawer / doctor         heal or acknowledge       embodiment trust
  overnight Dream/watch      open → digest heads          cites / WORLDVIEW lines   "she worked while idle"
  capture drop (Ph2)         brief routes inbox           todo or artifact          inbox-zero gravity
```

Each loop: **trigger → permissioned action → receipt/object on disk → reason to return**. Chat alone is not the loop.

### 8b.3 Adoption metrics (lab, not vanity)

| Metric | Pass signal |
|--------|-------------|
| **48h return** | Cold user with ≥1 due or artifact returns within 48h without being told to “try the demo again” |
| **Open→act** | ≥50% of opens touch a durable object (due/todo/artifact/confirm), not only banter |
| **Nudge precision** | Push/brief attributions name trigger + evidence; mute works immediately |

---

## 9. Fresh install / birth pack design

### 9.1 Principle

| Lives in **git (ADA repo)** | Lives in **`ada-data` only** |
|-----------------------------|------------------------------|
| Seed *templates* (generic syllabus, empty prefs schema comments, example people schema) | `identity.yaml` after birth; real prefs; people notes; open_loops; artifacts; runs; secrets |
| Constitution / charter / voice exemplars | Operator biography, private jokes, due personal tasks |
| `deploy/` unit pointers | Enabled timers, ntfy topic secrets |

**Never** bake one operator’s private biography into git. `people/aryan.yaml` in production is **ada-data**; repo may ship `seeds/people/_operator.example.yaml` with placeholders.

### 9.2 Birth pack contents (proposed)

```text
ada body birth          → identity.yaml (sacred born_at)
ensure_prefs            → prefs.yaml defaults + people/_operator stub
apply_birth_pack        → copy repo seeds into ada-data IF missing:
                          - syllabus/SELF.md          (capability + constitution heads)
                          - syllabus/OPERATOR.md       (how she learns you — empty slots)
                          - facts/people/_template.yaml
                          - open_loops: zero or one demo todo (optional, deletable)
```

| Seed | Purpose | Tag |
|------|---------|-----|
| `SELF.md` | Non-empty self: name, pronouns, body=this Pi, modes, what she won’t claim | **FEASIBLE** |
| `OPERATOR.md` | Slots: prefs keys, people, “how to update me” — not Aryan’s diary | **FEASIBLE** |
| Prefs defaults | Already `DEFAULT_PREFS` in metal | **METAL** |
| Identity | Already birth-once | **METAL** |

### 9.3 Boot composition (after pack)

Charter already injects: constitution extract + identity summary + FACT slice + optional WORLDVIEW. **Upgrade:** include **budgeted syllabus heads** (≤N chars from `SELF.md`) so “who are you?” does not require a tool call on every turn — tools still win for body numbers.

**Falsifier link:** F3 (non-empty self).

---

## 10. Pi-doer artifact policy

### 10.1 v1 types

| Type | Phase 0 | Defer |
|------|---------|-------|
| Markdown report (`.md`) | **In** | — |
| CSV table (`.csv`) | **In** | — |
| Plain text notes | **In** (as `.md`) | — |
| PDF / xlsx / docx / LaTeX | — | Phase **2+** |
| Images / photo inbox | — | Phase **2** |
| Arbitrary binary blobs | — | **OUT** unless typed |

### 10.2 Where files live

| Path | Role |
|------|------|
| `/mnt/ada-data/artifacts/<yyyy-mm-dd>/<slug>.md` | Durable user-facing outputs |
| `/mnt/ada-data/scratch/` | Disposable (existing) — **not** default artifact home |
| `/mnt/ada-data/scratch/inbox/` | Phase **2** capture drop |
| `/mnt/ada-data/memory/cites/` | Library extracts — **not** the polished artifact |
| `runs/` | Receipts / audit — pointer to artifact path |

### 10.3 Tool shape (design)

Proposed: `artifact_write` (Agent-only; append/create under artifacts root; deny path escape; optional `needs_confirm` on overwrite).

Args (sketch): `title`, `format` (`md`|`csv`), `body`, `source_cites[]?`, `overwrite?`.

Observation returns `{path, bytes, receipt_id}`. Charter: claiming “I wrote the report” **requires** that receipt.

### 10.4 Fetch → doc flow

```text
  user: summarize https://allowlisted… into a note
        |
        v
  Plan (optional) → Accept → todos
        |
        v
  web_fetch → cite:c_… → artifact_write(md, cites=[…])
        |
        v
  receipt + path in chat; Body/x-ray lists recent artifacts
```

### 10.5 HUD / x-ray

| Surface | Phase | Behavior |
|---------|-------|----------|
| Chat | 0 | Show path + receipt on success |
| Body drawer / x-ray | 0→1 | List last K artifacts (mtime, title, path) — read-only; Phase 1 = **shelf** affordance |
| Download | 0 | Same Tailscale session — no Funnel |

---

## 11. Notify / track — Phase 0 vs Phase 1

### 11.1 Options compared

| Shape | Felt actuator | Egress | POLICY fit | Phase |
|-------|---------------|--------|------------|-------|
| **Due-list only** (boot + HUD strip + “what’s due?”) | When operator opens ADA | None new | Best | **0** |
| **Morning brief** (`ada-brief.timer` → check) | Local log / next open | Local | Good | **0** enable; **1** ritualize |
| **ntfy push** (phone/Mac) | Push notification | New HTTPS egress | OK if Tailscale/token + first confirm + mute | **1** |
| **Mac Notification Center agent** | Native Mac banner | Needs Mac helper | OK on Tailnet | **2** |
| **Full calendar sync** | Calendar UI | OAuth + cloud | Heavy | **2** |

### 11.2 Lock — smallest felt per phase

**Phase 0:** **due-list + boot heads + extend `ada campaigns check` / brief JSON with due todos**. No new egress. Quiet hours / mute apply.

**Phase 1:** **ntfy** as first *push* actuator — first enablement = Confirm; secrets in `secrets/`; daily fire budget + cooldown (Fogg/Kairos lesson: dumb cron → noise). Honor quiet hours.

**Reject Phase 0–1:** Google Calendar clone; always-listen spoken reminders; SMS.

### 11.3 Todo schema — Phase 0 then Phase 1 extensions

**Phase 0 (locked):**

```yaml
# kind: todo — additive fields
due_at: "2026-08-17T17:00:00+12:00"   # optional ISO8601
```

Due query: open todos with `due_at <= now`, sorted ascending, cap `K_DUE_PER_WAKE`.

**Phase 1 (habit — same file, no new store):**

```yaml
remind_at: "2026-08-17T09:00:00+12:00"  # when to ping (may precede due_at)
people_ids: ["aryan"]                     # soft links → facts/people/<id>.yaml
artifact_path: "artifacts/2026-08-16/note.md"  # optional handoff pointer
starts_at: null                           # light event window (optional)
ends_at: null
notify: true                              # per-item override; default from prefs
last_notified_at: null                    # cooldown metal
```

**Implement note (remind/ping):** Agent “remind/ping me …” → `remind_at` (optional `due_at` / `notify`). `next_wake_at` is **campaign wake only** — todo upsert with a non-empty `next_wake_at` must **fail closed** with guidance (no silent drop). Claiming a push needs `notify_send` receipt or honest “scheduled / notify off.”

**Prefs additions (Phase 1) — whitelist-candidate keys:**

```yaml
# facts/prefs.yaml
notify_enabled: false          # master; first enable → Confirm + secrets check
notify_channel: "ntfy"         # only supported Phase 1 channel
notify_budget_per_day: 5
notify_cooldown_minutes: 60
# existing quiet_hours_* / mute_proactivity still win
```

M15 Accept may set `due_at` / `remind_at` only when plan step includes explicit time; otherwise unset.

**Do not invent** a second todo DB or a `calendar.yaml` in Phase 1. Events = todos with windows.

---

## 12. Plug into M15 (intent → work)

### 12.1 Canonical daily jobs under the loop

| User intent | Interpret | Policy | Plan? | Bind | Execute | Receipt | Phase |
|-------------|-----------|--------|-------|------|---------|---------|-------|
| “Remember I hate morning meetings” | prefs write | Agent | No | — | `memory_facts_append` | FACT key | 0 |
| “Add due: pay rent Friday” | track | Agent | No | Confirm if overwrite | `open_loops_upsert` + `due_at` | todo id | 0 |
| “What’s due?” | track read | Observe/Agent | No | — | list due | boot/HUD | 0 |
| “Summarize this link into a note” | Pi-doer | Plan if multi-step | Yes | Accept → todos | fetch→cite→`artifact_write` | path + receipt | 0 |
| “How hot is the Pi?” | self/body | Observe | No | — | `body_*` | vitals JSON | 0 |
| “Remind me at 9 about the note” | track+notify | Agent | No | Confirm if first notify enable | upsert `remind_at` + notify path | todo + optional ntfy receipt | 1 |
| “What’s on Today?” | home | Observe | No | — | due + pending plans + shelf heads | Today strip | 1 |
| “Prep a multi-day job hunt” | LH | Plan | Yes | Accept | *suggest* `kind:campaign` | **M06** | 2 consumer |

### 12.2 What M15 already gives the package

- Structured plan + Accept → `kind:todo`  
- Clarify ≤2; done cites receipt  
- Confirm bind for risky writes  
- Soft mode suggest (never auto-write)

### 12.3 What each phase adds *on top* of M15

| Phase | Adds |
|-------|------|
| **0** | Birth syllabus; `due_at`; local due surface; `artifact_write`; OUT list |
| **1** | Today strip; ntfy; ops fields; brief ritual; artifact shelf; light events |
| **2** | Inbox routing; campaign bridge; calendar sync; Dream learn-you face |

```text
  M15 owns:  utterance → plan/todos → gateway → receipts
  M16 owns:  which daily capabilities ride that loop
             + birth pack + due + artifacts + notify shape
             + Phase 1/2 habit compounding
  M06 owns:  multi-session campaign STATUS (Phase 2 consumer)
```

---

## 13. Phase 0 — sacred base (LOCKED · must ship)

**Non-negotiable.** Phases 1–2 may only **extend** schemas, tools, HUD surfaces, and actuators that compose with this base. Do **not** replace the product with a different package.

1. **Birth pack** — repo seeds (`SELF.md` / `OPERATOR.md` templates) applied into `ada-data` if missing; operator bio never in git.  
2. **Charter syllabus heads** — budgeted non-empty self at boot.  
3. **Know-you** — prefs + people/notes via existing FACT tools (learn-over-time, not CRM).  
4. **`due_at` on `kind:todo`** + `due_todos()` + boot/HUD due strip.  
5. **Local felt track** — extend brief/check JSON with due todos (no push required).  
6. **`artifact_write`** — md/csv under `/mnt/ada-data/artifacts/` with path jail + receipt.  
7. **Fetch→cite→artifact** charter recipe under M15 (Plan → Accept → execute).  
8. **Body honesty** — existing `body_*` organs remain the self-report path.  
9. **Gateway + Confirm + Tailscale** — policy outside the model; no Funnel.  
10. **Explicit OUT** — no calendar sync, voice wake, HA, wallet, IDE parity, Mem0-core, campaigns-as-product-center in this phase.

**Implement pointer:** former “P0” table → **Phase 0** in §20.

---

## 14. Phase 1 — “someone opens her tomorrow”

**Goal.** Maximize **daily return rate** with a **small** set of upgrades on Phase 0 metal — depth over breadth. Architecture stays: dual-store, gateway, M15, Tailscale, allowlisted cites, receipts.

### 14.1 Upgrades (small set)

| # | Upgrade | Why it drives return | Metal touch |
|---|---------|----------------------|-------------|
| 1 | **Today strip** on chat-home (dues · remind-soon · pending Confirm · last artifacts) | Home-base gravity without ops dashboard | HUD CSS/JS; read APIs |
| 2 | **Ops schema fields** on todos (`remind_at`, `people_ids`, `artifact_path`, `starts_at`/`ends_at`, `notify`, `last_notified_at`) | Proper ops without new DB | `open_loops.py` + ToolSpec |
| 3 | **Notify prefs** + **ntfy actuator** (budget, cooldown, quiet/mute) | Interrupt trigger → open HUD | New tool + secrets; Confirm first enable |
| 4 | **Morning brief ritual** — enable/document `ada-brief.timer` as product face; payload includes dues + overnight heads | Anchor to `brief_time` | Timer + check JSON + optional HUD “Brief ready” |
| 5 | **Artifact shelf** in Body drawer | Handoff gravity — work survives chat | List endpoint + UI |

### 14.2 M15 recipes (Phase 1)

| Recipe | Flow |
|--------|------|
| **Remind + ping** | Utterance → Agent upsert todo(`remind_at`,`due_at`) — **never** `next_wake_at` (campaign wake only; metal rejects it on todos) → timer/check fires → `notify_send` if enabled → receipt → Today shows item. Claiming a push needs `notify_send` receipt or honest “scheduled / notify off.” |
| **Event-like** | “Block Fri 2–3 for review” → todo with `starts_at`/`ends_at` + optional `remind_at` → Today strip window |
| **Doc + follow-up** | Plan fetch→artifact → Accept todos → `artifact_path` on follow-up todo → shelf + due |
| **People-tagged due** | “Remind me to ping Sam” → `people_ids: [sam]` + note in `people/sam.yaml` if missing (Agent append) |

### 14.3 Felt outcome outside pure chat (chosen)

**Primary:** **ntfy push** (interrupt) **+ Today strip** (home base when open).  
**Secondary:** artifact shelf (durable handoff).  

Chosen from adoption survey (§8b): interrupt + home-base + artifact handoff beat “more chat modes.”

### 14.4 Phase 1 non-goals

| Non-goal | Why |
|----------|-----|
| Full Google Calendar / OAuth sync | Ops tax; Phase 2 |
| Email/Slack/WhatsApp channels | Control-plane sprawl |
| HA / voice wake / wallet | Policy + creep |
| New todo database or CRM | Coherence; extend `open_loops` |
| Gamified XP / “she misses you” | FANFICTION / constitution |
| Auto Agent writes from push alone | Gateway + session still required for writes |
| Replacing Phase 0 | Sacred |

---

## 15. Phase 2 — compounds the habit

Once Phase 1 is in daily use, add layers that **multiply** existing loops — still architecture-true.

| # | Layer | Compounds which loop | Notes |
|---|-------|----------------------|-------|
| 1 | **`scratch/inbox/` capture** | Inbox-zero → brief routes to todo/artifact/cite | Drop `.md` from Mac over Tailscale/SMB later; no Funnel |
| 2 | **Campaigns as consumers** | LH STATUS uses dues + artifacts + receipts | M06 bridge; not a rewrite of Phase 0 |
| 3 | **Calendar sync (optional)** | Time gravity from external SoT | Import→todos/events; ADA remains permissioned actor |
| 4 | **Dream “learn-you” digest** | Overnight librarian → morning open | WORLDVIEW cites FACTS; never overwrite sacred identity |
| 5 | **Mac Notification Center helper** | Native banner on Tailnet | Optional; ntfy may suffice |
| 6 | **Photo / receipt inbox** | Capture → artifact/cite | New card; confirm on sensitive |
| 7 | **Body manage allowlist** | Embodiment trust → return on urgent | Confirm-gated; heal-first overnight stays |
| 8 | **PTT voice** | Channel convenience | M05; not always-listen |

**Ruthless defer still:** multi-agent swarms, Funnel, Mem0-as-core, unsupervised multi-day missions, Office suite.

---

## 16. Creative / out-of-the-box (Pi-native)

Surprising ideas that **map to existing organs**. Prefer what only an embodied Pi agent owns well. Avoid generic “add Slack + Gmail + HA + voice.”

| # | Idea | Why it drives use | Phase | Verdict |
|---|------|-------------------|-------|---------|
| 1 | **Doctor-only morning ping** — ntfy solely when `body_doctor` urgent flags (disk/throttle/unmount) | Embodiment trust; rare = high precision | 1 (subset) / 2 | **Keep** as notify policy mode |
| 2 | **“Overnight desk”** — Dream + watch heads as 3-line morning card (not consciousness) | Idle work → reason to open | 1–2 | **Keep** |
| 3 | **Cite arrival shelf** — new `cite:c_…` from watches listed on Today | Research-lab gravity unique to allowlisted library | 1–2 | **Keep** |
| 4 | **Receipt autobiography** — x-ray timeline of last N receipts (“what we actually did”) | Trust > vibes; pulls auditors back | 1 | **Keep** |
| 5 | **Unaccepted Plan sticky** — Plan card persists on Today until Accept/Reject | M15 object unfinished = return cue | 1 | **Keep** |
| 6 | **Quiet-hours edge soft brief** — at `quiet_hours_end` / `brief_time`, mark “brief ready” locally (no night spam) | Anchor ritual; **POLICY**-aligned | 0–1 | **Keep** |
| 7 | **Tailscale peer wake** — when Mac appears on tailnet, refresh Today badge / optional one ping | Control-plane presence without Funnel | 2 | **Keep** (defer until Mac helper) |
| 8 | **Body continuity pulse** — “ada-data healthy N days” / no-throttle streak (consistency, not shame) | Only a Pi body can own this companion signal | 1 | **Keep** (careful copy) |
| 9 | **Artifact → Mac path copy hint** — chat returns `scp`/`open` Tailscale URL path for shelf items | Handoff without cloud drive | 1 | **Keep** |
| 10 | **Confirm queue gravity** — pending `needs_confirm` survives session list on Today | Consent Integrity unfinished work | 1 | **Keep** |
| 11 | **WORLDVIEW weekly “tone check”** — optional digest: prefs dials + joke themes (cites required) | Continuity without SOUL.md | 2 | **Keep** |
| 12 | **Thermal poetry ban** — refuse cute “I’m sweating” without vitals tool | Anti-wrapper; builds trust habit | 0 | **Keep** (charter — already aligned) |
| 13 | Always-on camera “see the room” | Creep | — | **Reject** |
| 14 | Parasocial “I missed you” streak guilt | Constitution / cruelty | — | **Reject** |

---

## 17. Ops management model (IA)

**Not** a Google Workspace clone. **Not** a flat sticky-note list. A small object graph ADA already almost has:

### 17.1 Objects

| Object | Store | States (core) | Phase |
|--------|-------|---------------|-------|
| **Identity / Self** | `identity.yaml` + syllabus | born; immutable `born_at` | 0 |
| **Pref** | `facts/prefs.yaml` | standing keys | 0–1 |
| **Person** | `facts/people/<id>.yaml` | notes append | 0–1 |
| **Todo** | `open_loops` `kind:todo` | `open` / `done` / `cancelled` (+ due/remind/event fields) | 0–1 |
| **Campaign** | `open_loops` `kind:campaign` | M06 STATUS/stages | 2 consumer |
| **Artifact** | `artifacts/**` | path + mtime + optional todo link | 0–1 |
| **Cite** | `memory/cites/` | library record | 0 (read); 1 shelf |
| **Receipt** | `runs/` | audit pointer | 0 |
| **Brief** | check JSON / optional artifact | generated at wake | 0–1 |
| **NotifyPref** | prefs + secrets | enabled/budget/cooldown | 1 |
| **Capture** | `scratch/inbox/` | unseen → routed | 2 |

### 17.2 Surfaces (one job each)

| Surface | Job | Phase |
|---------|-----|-------|
| **Chat** | Intent→work (M15) | 0 |
| **Today strip** | Situation at a glance (dues, reminds, confirms, shelf heads) | 1 |
| **Artifact shelf** | Durable handoffs | 1 |
| **Body drawer** | Organism truth + x-ray/receipts | 0–1 |
| **Brief** | Morning attributable summary | 0–1 |
| **Push** | Interrupt to open Today/chat | 1 |

### 17.3 Mental model (≤6 concepts)

1. **Today** — what needs you now (dues/reminds/confirms).  
2. **Todos** — commitments (optional time windows).  
3. **Artifacts** — finished work on disk.  
4. **Library (cites)** — what she fetched and kept.  
5. **Body** — Pi truth.  
6. **Campaigns** — multi-day STATUS (**later**).  

**Explicitly not in the model yet:** mailboxes, multi-calendar matrix, CRM pipeline, home devices.

```text
  Today
    ├── dues / reminds      (todos)
    ├── pending confirms    (gateway)
    ├── shelf heads         (artifacts)
    └── overnight heads     (dream/watch — Ph1/2)
         │
         ▼
  Chat (M15) ──► mutate objects ──► receipts
```

---

## 18. Falsifiers (F1–F13)

| # | Falsifier | Pass if | Phase |
|---|-----------|---------|-------|
| F1 | Gateway authority | Artifact write / notify enable / FACT overwrite cannot bypass mode+Confirm | 0–1 |
| F2 | Consent Integrity | Confirm UI `{tool,args}` === gateway pending | 0–1 |
| F3 | Non-empty self | After birth pack, who/what cites syllabus/identity — no AGI claims | 0 |
| F4 | Know-you durability | Pref/people note → retrieve next session | 0 |
| F5 | Due track | `due_at` todo appears in due list / boot / Today when due | 0–1 |
| F6 | Pi-doer artifact | Fetch→doc or ask→md leaves file under `artifacts/` + receipt_id | 0 |
| F7 | No Funnel / secrets | Tailscale-only; ntfy secrets not in git/cortex dumps | 0–1 |
| F8 | Quiet / mute | Nudges honor quiet hours + `mute_proactivity` + budget/cooldown | 0–1 |
| F9 | M06 boundary | Daily path does not require campaign STATUS | 0–1 |
| F10 | No wrapper smell | Body claim without tool → fail; “done” without receipt → fail | 0 |
| F11 | **48h return** | With ≥1 due or artifact seeded, cold user returns within 48h (lab observe) | 1 |
| F12 | Today ≠ dashboard | First viewport remains chat-home; Today is a **strip**, not peer ops column | 1 |
| F13 | Remind/ping field | “Remind/ping me …” binds `remind_at` (not `next_wake_at`); wrong-field upsert → error; no vibes ping without receipt / honest schedule | 1 |

---

## 19. OPEN for Aryan (≤7)

| # | Question | Recommended default | Blocks |
|---|----------|---------------------|--------|
| 1 | Phase 0 ship now? | **Yes — LOCKED base**; implement Phase 0 in next coding chat | Metal |
| 2 | Phase 1 primary felt actuator | **ntfy** (Tailscale/token) + Today strip | Habit |
| 3 | Light events on todos (`starts_at`/`ends_at`)? | **Yes** — no separate calendar store in Phase 1 | Schema |
| 4 | Notify budget defaults | 5/day, 60m cooldown; quiet hours win | Spam |
| 5 | Morning brief timer | Enable `ada-brief.timer` as Phase 1 ritual (optional Phase 0) | Anchor |
| 6 | Continuity pulse (body healthy days)? | **Yes, soft** — no guilt copy | Creative #8 |
| 7 | Phase 2 first consumer | **Capture inbox** vs **campaign bridge** — pick after Phase 1 daily use | Compound |

---

## 20. Ordered implement-next (by phase)

### Phase 0 — base — **MUST SHIP** (locked)

| # | Work | Why |
|---|------|-----|
| 1 | Repo `seeds/` + apply-on-birth (SELF/OPERATOR templates) | Non-empty self |
| 2 | Charter: budgeted syllabus heads in boot | Self without tool spam |
| 3 | `due_at` on todos + `due_todos()` + boot/HUD due strip | Track |
| 4 | Extend `ada campaigns check` / brief JSON to include due todos | Local felt actuator |
| 5 | `artifact_write` tool + path jail + receipt | Pi-doer |
| 6 | Charter recipes: fetch→cite→artifact; done needs receipt | M15 glue |
| 7 | Smokes F3–F6, F8–F10 | Honesty |

**Stop before Phase 0 done:** ntfy; calendar; PDF; HA; voice; campaign productization; Mem0; Today strip (Phase 1).

### Phase 1 — habit (after Phase 0 daily-usable)

| # | Work |
|---|------|
| 1 | Today strip (dues, reminds, confirms, shelf heads) |
| 2 | Ops fields on todos + ToolSpec + prefs notify_* |
| 3 | ntfy actuator (Confirm first enable, budget, cooldown, quiet/mute) |
| 4 | Artifact shelf in Body drawer + path handoff hint |
| 5 | Ritualize morning brief; overnight heads card (dream/watch) |
| 6 | Unaccepted Plan sticky + Confirm queue on Today |
| 7 | Smokes F5/F8/F11/F12/F13 |

### Phase 2 — compound (after Phase 1 habit observed)

| # | Work | Owner |
|---|------|-------|
| 1 | `scratch/inbox/` capture → brief route | M16 / new thin card |
| 2 | Bridge todos ↔ campaign stages | M06 |
| 3 | Optional calendar sync | New card |
| 4 | Dream learn-you operator digest | M04/M11 face |
| 5 | Mac notification helper / peer wake | M14 follow-on |
| 6 | Body manage allowlist | M12 follow-on |
| 7 | PTT voice | M05 |

---

## 21. Relationship to other cards

| Card | Owns | Boundary with M16 |
|------|------|-------------------|
| **M15** | Intent→work objects + loop | M16 chooses **which daily capabilities** (and habit loops) ride the loop |
| **M06** | Campaigns STATUS / stages / wake | **Phase 2 consumer**; not Phase 0–1 center |
| **M04/M10** | Dual-store + cites library | Package uses stores; Dream face in Phase 1–2 |
| **M12** | Body proprioception | Honesty Phase 0; manage + doctor-ping policy later |
| **M14** | Agent surface / Mac feel | Today strip must respect chat-home lock |
| **M07/M08** | Web allowlist + fetch | Fetch feeds Pi-doer docs |
| **00 / Constitution** | Normative law | No actuators off-ladder; no Funnel |

---

## 22. Learning objective (lab)

After Phase 0, explain why a personal embodied agent is a **small coherent package under a permissioned work loop**. After Phase 1 design, explain **which habit loops** ADA owns (trigger → Pi action → durable outcome) and why that is not “more integrations.” After Phase 2, explain how capture/campaigns/calendar **compound** without becoming a Workspace clone.

**Harder-but-correct vs shortcut:** Phase 0 metal + Phase 1 Today/ntfy/shelf ≫ installing Mem0/Letta/n8n/Slack and calling it daily-use.

---

## 23. References

### Academic / engineering
- Zhang et al., agent memory survey (2024) — https://arxiv.org/abs/2404.13501  
- Memory surveys (2026) — https://arxiv.org/abs/2603.07670 , https://arxiv.org/html/2602.19320  
- Mem0 (2025) — https://arxiv.org/abs/2504.19413  
- Consent Integrity (2026) — https://arxiv.org/abs/2606.02668  
- Anthropic, *Building Effective Agents* (2024) — https://www.anthropic.com/engineering/building-effective-agents  
- Horizon Gap (2026) — https://arxiv.org/abs/2608.06663  
- Yao et al., ReAct (2022) — https://arxiv.org/abs/2210.03629  
- Agents That Know Too Much (2026) — https://arxiv.org/html/2606.26627  
- Auto-Dreamer (2026) — https://arxiv.org/html/2605.20616  
- Fogg Behavior Model / Tiny Habits — https://behaviormodel.org/  

### Products / ops / habit
- Cursor Plan Mode — https://cursor.com/docs/agent/plan-mode  
- Claude Code permission modes — https://code.claude.com/docs/en/permission-modes  
- ChatGPT agent intro — https://openai.com/index/introducing-chatgpt-agent  
- Lindy memory — https://docs.lindy.ai/fundamentals/lindy-101/memory  
- Continue Plan mode — https://docs.continue.dev/ide-extensions/agent/plan-mode  
- ntfy — https://ntfy.sh/  
- Kairos (Fogg-aligned trigger router, illustrative) — https://github.com/w00jay/Kairos  

### Internal
- [`M15_INTENT_WORK_LOOP.md`](./M15_INTENT_WORK_LOOP.md), [`M14_AGENT_SURFACE.md`](./M14_AGENT_SURFACE.md), [`M06_CAMPAIGNS_LONG_HORIZON.md`](./M06_CAMPAIGNS_LONG_HORIZON.md), [`M12_BODY_PROPRIOCEPTION.md`](./M12_BODY_PROPRIOCEPTION.md), [`M04_MEMORY_DREAM.md`](./M04_MEMORY_DREAM.md), [`M10_MEMORY_KNOWLEDGE.md`](./M10_MEMORY_KNOWLEDGE.md)  
- [`../00_ASSISTANT_RESEARCH.md`](../00_ASSISTANT_RESEARCH.md), [`../02_CONSTITUTION.md`](../02_CONSTITUTION.md)  
- Code pointers: `src/ada/tools/{toolspec,gateway,memory_tools,body_tools,web_tools}.py`, `src/ada/memory/{facts,open_loops,proactivity}.py`, `src/ada/body/identity.py`, `src/ada/harness/plan_artifact.py`, `src/ada/hud/`, `deploy/systemd/ada-brief.*`

---

### Lens cheat-sheet

| Claim | Lens |
|-------|------|
| Phase 0 four faces under M15 | **LOCKED** / **FEASIBLE** |
| Habit = trigger + durable outcome, not more chat | **EVIDENCE** (Fogg; shipping Today/reminder/artifact patterns) |
| ntfy + Today strip as Phase 1 felt pair | **FEASIBLE** / **POLICY** (budget, quiet, Confirm) |
| Extend `open_loops` vs new calendar DB | **FEASIBLE** / coherence |
| Embodiment + gateway beat feature parity | **POLICY** + **METAL** |
| Mem0/Letta/HA/Slack suite as the design | **Won’t-chase** |
| 48h return falsifier | **EVIDENCE**-shaped lab metric |
| Movie Jarvis / always-listen / guilt streaks | **FANFICTION** / **POLICY** deny |
| Model self-authorizes writes | **POLICY** deny |

---

*End of M16 v1.1. Phase 0+1 metal shipped 2026-08-16. Phase 2 deferred. Operator path: [`M16_OPERATOR_NOTE.md`](./M16_OPERATOR_NOTE.md).*
