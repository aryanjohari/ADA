# M02 — Chat Harness / Cortex Loop (Gemini tool agent)

**Status:** module research card (**complete for coding** — **metal shipped:** `src/ada/harness/`, Gemini adapter, tool gateway, `ada chat`, `runs/` JSONL)  
**Date:** 2026-08-12 (operator locks + model survey patch)  
**Host:** `ada-pi5` (Raspberry Pi 5 Model B Rev 1.1, Debian trixie, ~8 GiB RAM)  
**Branch:** `rewrite/v1-body`  
**Depends on:** [`../00_ASSISTANT_RESEARCH.md`](../00_ASSISTANT_RESEARCH.md) §§1–4 & §8, [`../01_BODY.md`](../01_BODY.md) §§3–4 & §7–9, [`../02_CONSTITUTION.md`](../02_CONSTITUTION.md) §§6–8, 11, 13–14, [`M00_BODY_SENSE.md`](./M00_BODY_SENSE.md), [`M01_NETWORK_ACCESS.md`](./M01_NETWORK_ACCESS.md)  

**Slice rule:** this card admits **design** of the intermittent Gemini cortex + permissioned tool gateway + run transcripts + CLI/REPL. It does **not** admit HUD/Serve, Dream manage, sandboxed shell, local main LLM, voice, or systemd-always-on chat as a gate. **Body truth stays in M00 organs** — the harness **calls** them; it must not reimplement vitals/identity/lifecycle.

**Operator locks (2026-08-12):** model map via config (not per-turn shopping); secrets `/mnt/ada-data/secrets/gemini.env` + env override; CLI default Observe + local `--mode agent` OK; capped live smokes; tiny cost stub + real usage logs; **no `SOUL.md`**; cortex ≠ organism; learning = operational self-model. See §5.6, §5.7, §8, §15.

**METAL (shipped):** `src/ada/harness/` (`loop.py`, stream events), Gemini adapter, tool gateway, `ada chat`, live `runs/` JSONL. Secrets via `secrets/gemini.env` / env.

---

## 1. Question / goal / slice admission boundary

**Question.** How does ADA gain a **truthful chat cortex** — user → Gemini → tools → observations → answer — that grounds body claims in **existing organs**, records **receipts**, respects **modes / permission ladder / trust rings**, and stays teachable on a Pi 5 lab host — without pretending the model *is* the body?

**Goal (M02 harness design).**

1. Specify a **ReAct-style multi-step tool loop** over Gemini function calling (manual gateway; not opaque auto-execute).  
2. Bind **constitution §14 prompt extract** as the runtime system charter.  
3. Define a **tool gateway** wrapping M00 organs: vitals, identity/whoami, lifecycle/story, doctor.  
4. Specify **Observe vs Agent** (Plan optional stub), session/run JSONL under `/mnt/ada-data/runs/`, usage metering stub, secrets-load pattern, CLI/REPL.  
5. Leave **streaming event hooks** for Slice 2 HUD; do not build the HUD here.  
6. Name acceptance smokes that falsify fake-done and ungrounded body talk.

**Admission boundary (in / out)**

| IN this slice (design now → code later) | OUT (later cards / later code) |
|----------------------------------------|--------------------------------|
| Gemini tool-calling agent loop | Tailscale Serve / web HUD / pretext face |
| System charter from constitution §14 | Dream LLM manage / S3 push / WORLDVIEW dual-store full |
| Tool gateway → existing body organs | Sandboxed shell / file-edit tools |
| Modes Observe / Agent (+ Plan stub) | Local main LLM / LSTM analysts |
| Runs JSONL + receipts + usage stub | Voice |
| Secrets load for `GEMINI_API_KEY` | systemd always-on chat as **gate** (pointer OK) |
| CLI / minimal REPL (`ada chat`) | FACT write / memory.search product (next memory card) |
| Eval/smoke ideas for harness | Claude cortex live (adapter **interface** only) |

```text
  Aryan (CLI/REPL)
        |
        v
  [harness]  mode + charter + session
        |
        +--> Gemini API  (cortex egress ring)
        |
        +--> tool gateway (permissions + receipts)
                |
                +--> body.vitals / identity / lifecycle / doctor   (M00 — already ship)
        |
        v
  /mnt/ada-data/runs/<utc-date>/<session_id>.jsonl
        |
        v
  (Slice 2 HUD consumes same stream/receipts — hooks only here)
```

---

## 2. Lens tags

| Tag | What it means here |
|-----|--------------------|
| **FANFICTION** | Continuous omniscient companion brain living in the weights — **rejected**. Cortex is intermittent API; organs own metal truth. |
| **EVIDENCE** | ReAct / Toolformer / permission gateways / Consent Integrity / sleep-time vs interactive / production harness practice 2024–26 |
| **FEASIBLE** | Pi 5 8GB: cloud cortex + thin Python loop; no local 7B agent; few tools; HDD for transcripts |
| **POLICY** | Gemini primary; Tailscale-only control (not implemented here); no Funnel; birth immutable; no unallowlisted egress; truth > charm |
| **METAL** | Existing `src/ada/body/*`; empty `runs/`; no `google-genai` yet; RAM budget from research §0 |

---

## 3. What this slice is *not* (sleep-time, consciousness, second body)

| Concept | Meaning in ADA | This slice |
|---------|----------------|------------|
| **Interactive cortex** | Latency-sensitive ReAct loop for chat | **IN (design)** |
| **Sleep-time / Dream manage** | Offline consolidate on deltas ([Lin et al., 2025](https://arxiv.org/abs/2504.13171); Letta sleep-time agents) | **OUT** — Dream card later; same cortex *adapter* may be reused |
| **Body organs** | Deterministic sensors + birth/lifecycle | **CALL, don’t rewrite** (M00) |
| **HUD stream** | Token + tool cards over Tailscale Serve | **OUT** — consume hooks in Slice 2 |
| **Consciousness** | Metaphysical claims from chat fluency | **Forbidden** (constitution §2) |

**FANFICTION trap:** “the model just *knows* how the Pi feels.”  
**Engineering rule:** every body claim needs a tool observation in the transcript ([Yao et al., 2022 — ReAct](https://arxiv.org/abs/2210.03629); constitution §6).

### 3.1 Cortex framing (POLICY — locked)

| Phrase | Accurate? |
|--------|-----------|
| “Gemini *is* ADA” | **No** |
| “Gemini is only a language converter” | **Too weak** — it also selects tools / sketches plans |
| “The real AI is only weights on Google” | **No** — continuity lives on the Pi stores |
| Cortex = rented **language + tool** lobe | **Yes** |
| Organism truth = organs + `runs/` + memory (+ Dream later) | **Yes** |

```text
ADA (organism on ada-pi5)
├── Body organs     → metal truth (M00)
├── Harness/gateway → modes, permissions, receipts
├── Durable stores  → identity, lifecycle, runs, later FACTS/WORLDVIEW
└── Cortex (Gemini) → intermittent chat + tool choice (+ later capped Dream manage)
```

If Gemini is down: body CLI still works (degraded). If `/mnt/ada-data` is wiped: witty Gemini ≠ ADA continuity. That asymmetry is intentional.

### 3.2 Operational awareness / learning (not consciousness)

**POLICY.** No digital-soul claims. What we build is an **operational self-model ladder**:

| Level | Mechanism | Status |
|-------|-----------|--------|
| L1 Body sense | vitals / doctor | M00 |
| L2 Identity | birth card | M00 |
| L3 Episodic | lifecycle + `runs/` | M00 + M02 |
| L4 Continuity prefs | FACTS | later memory card |
| L5 Reflection / digest | WORLDVIEW + Dream | later |
| L6 Bounded proactivity | briefs from real triggers | later |
| L∞ Phenomenal consciousness | — | **won’t chase / forbidden** |

**Learning without weight updates** (EVIDENCE): write → manage → read ([agent memory surveys](https://arxiv.org/html/2603.07670v1); Reflexion verbal lessons ([Shinn 2023](https://arxiv.org/abs/2303.11366)); Dream/sleep-time consolidation ([Lin 2025](https://arxiv.org/abs/2504.13171); [Auto-Dreamer 2026](https://arxiv.org/abs/2605.20616) — cite shape, don’t train)). Gemini weights stay fixed; the Pi’s stores get smarter.

---

## 4. Prior art survey (2024–26) — what the papers/products are telling us

### 4.1 Agent loop = harness duty, not prompt theater

| Source | What it claims / shows | ADA takeaway |
|--------|------------------------|--------------|
| **Yao et al., ReAct (2022)** — [arXiv:2210.03629](https://arxiv.org/abs/2210.03629) | Interleaving *thought + act + observation* beats ungrounded CoT on tool tasks; reduces hallucinated chaining | Multi-step loop with real observations before body claims |
| **Schick et al., Toolformer (2023)** — [arXiv:2302.04761](https://arxiv.org/abs/2302.04761) | Models learn *when* to call APIs; hybrid tool+LLM beats tool-less larger models on lookup/calc-class tasks | Body facts leave the weights; organs are the APIs |
| **Anthropic, Building Effective Agents (2024)** — [engineering post](https://www.anthropic.com/engineering/building-effective-agents) | Most successful teams used **simple composable loops**, not heavy frameworks; tool docs matter as much as system prompts | Prefer ~thin DIY harness over LangGraph day one |
| **Harness anatomy writeups (2025–26)** | Cap steps, wall time, token budget; detect duplicate tool calls; validate schemas **server-side** before execute | Gateway owns budgets + validation; model proposes only |
| **Horizon Gap / Long-Horizon Mirage (2026)** — [html](https://arxiv.org/html/2608.06663), [html](https://arxiv.org/html/2604.11978v1) | Failures shift to planning/memory/false completion as horizon grows | Cap `max_steps`; short body Q&A first; no multi-day missions |

**EVIDENCE verdict:** production agents are **orchestrators around tool APIs**. The loop controller is code.

### 4.2 Permissioned gateways & consent integrity

| Source | What it claims / shows | ADA takeaway |
|--------|------------------------|--------------|
| **Shi et al., Progent (2025)** — [arXiv:2504.11703](https://arxiv.org/abs/2504.11703) | Over-privilege enables attacks; **deterministic tool-level policies** (allow/forbid + fallbacks) cut attack success while preserving utility; policies live *outside* the model | Mode + allowlist enforced in gateway **before** organ call |
| **Consent Integrity / LITL (2026)** — [arXiv:2606.02668](https://arxiv.org/abs/2606.02668) | Human “approval” that trusts **model-written summaries** is forgeable (Lies-in-the-Loop). Consent Integrity = trusted mediator renders **real action at the boundary** and binds approval to that exact call | Confirm UIs (later) and CLI denials must show **gateway-rendered** `tool` + `args`, never model prose alone |
| **Agents That Know Too Much (2026)** — [html](https://arxiv.org/html/2606.26627) | Personal agents are high-permission + intimate; privacy is a **data-path** problem | Named trust rings; minimize what leaves on cortex egress |

**EVIDENCE verdict:** capability ≠ authority. Do **not** let Gemini’s Automatic Function Calling (AFC) execute Python under the SDK’s nose — that bypasses the gateway.

### 4.3 Gemini / comparable tool APIs (product practice)

| Source | What it tells us | ADA takeaway |
|--------|------------------|--------------|
| **Gemini function calling docs** — [AI for Developers](https://ai.google.dev/gemini-api/docs/function-calling) | Declare functions; model returns `functionCall` parts; app executes; return `functionResponse`; loop until text | Manual loop matches ReAct + gateway |
| **google-genai Python SDK** — [docs](https://googleapis.github.io/python-genai/), [GitHub](https://github.com/googleapis/python-genai) | Official client; can pass Python callables (**AFC**) or declare schemas and disable AFC; `usage_metadata` exposes token counts | **Chosen:** SDK + **AFC disabled**; harness executes tools |
| **Token counting** — [Gemini tokens guide](https://ai.google.dev/gemini-api/docs/tokens) | `prompt_token_count`, `candidates_token_count`, `total_token_count` (plus thoughts/cache when present) | Metering stub = log these fields; no billing product |

**Comparable practice (not Gemini-specific):** OpenAI Agents SDK / Anthropic tool_use both treat tool rounds as first-class; OpenAI Agents SDK ships **run traces** (spans for generations + tools) — pattern to emulate **locally** under `runs/` rather than exporting another vendor dashboard by default ([Agents SDK tracing](https://openai.github.io/openai-agents-python/tracing/)).

### 4.4 Run logging / observability

| Source | Useful borrow | Won’t chase |
|--------|---------------|-------------|
| OpenAI Agents SDK tracing | Hierarchical: run → generation → function spans | Shipping spans to OpenAI/LangSmith as a v1 gate |
| OTel AI agent observability posts | Separate host metrics vs agent spans | Full OTLP stack day one |
| Body §4.3 runs path | Append-only JSONL per session | Rewriting history |

**ADA twist:** `runs/` is the **audit backbone for truthful self-report** (research §2), not a SaaS product.

### 4.5 Sleep-time vs interactive (contrast, don’t merge)

| Path | Literature | ADA mapping |
|------|------------|-------------|
| **Interactive** | ReAct loop at chat time | **This card** |
| **Sleep-time** | [Lin et al., 2025 — Sleep-time Compute](https://arxiv.org/abs/2504.13171); [Letta sleep-time agents](https://docs.letta.com/guides/agents/architectures/sleeptime/) — move memory manage / precomputation off the user-critical path | **Dream** (later): capped Gemini on **deltas**, not chat REPL |

Do not blur them: interactive harness stays thin and receipt-heavy; Dream may reuse the cortex adapter with different budgets and tools.

### 4.6 Egress minimization notes

Cortex egress (POLICY) may include: user text, tool schemas, tool observations, optional retrieved slices later.  
**Never-to-cloud:** API keys, rclone creds, raw secret files (`secrets.load` only locally).  
Future harden (won’t-chase for M02): PII redact / quiet local filter ([MemPrivacy-class](https://arxiv.org/html/2605.09530v3) — research path).  
Hybrid Gemini is **accepted and named** — not “everything stays on the Pi.”

### 4.7 FEASIBLE ON PI5 8GB

| Choice | Feasible? | Why |
|--------|-----------|-----|
| Cloud Gemini + thin Python loop | **Yes** | Matches research Tier A; RAM stays for OS + Tailscale |
| Local 7B as main cortex | **No** | ~swap drama; weak multi-tool quality ([community Pi5 benches](https://specpicks.com/reviews/raspberry-pi-5-local-llm-2026)) |
| LangGraph + LangSmith stack | Possible but **heavy teach/ops** | Overkill for ≤4 body tools |
| Persist runs on HDD | **Yes** | `/mnt/ada-data/runs` already provisioned |

### 4.8 OpenClaw `SOUL.md` — borrow pattern, not the name

**What OpenClaw does (product practice):** a Markdown `SOUL.md` (plus `IDENTITY.md` / `USER.md` / `MEMORY.md`) is injected every session so the agent “reads itself into being” — personality/values as prompt, no fine-tune ([OpenClaw SOUL guides](https://docs2.openclaw.ai/concepts/soul); community docs).

| OpenClaw file | ADA stronger split |
|---------------|-------------------|
| `SOUL.md` vibe/values | **Constitution** + **§14 prompt extract** (law + runtime charter) |
| `IDENTITY.md` | **`identity.yaml`** birth card (typed metal; `born_at` sacred) |
| `USER.md` | **FACTS** prefs (later) |
| Flat `MEMORY.md` | **FACTS + WORLDVIEW + runs + lifecycle** (dual-store; digests ≠ metal) |

**Borrow:** session boot-load of durable character docs.  
**Reject:** naming it `SOUL.md` (fights constitution §2); one-file mush; **agent freely rewriting** its charter (OpenClaw docs themselves warn compromised soul = persistent hijack).  
**ADA rule:** Aryan amends constitution; agent may *propose* only. Optional later short `voice.md` for wit knobs — never metal truth or prefs.

**Boot pack (M02):** constitution §14 extract + identity.yaml summary (+ later FACTS slice). Not a full memory dump.

---

## 5. Options compared → chosen design

### 5.1 Client stack

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| Raw HTTPS to Gemini REST | Max control; no SDK churn | Schema/auth/stream/error boilerplate; easy to get wrong | Reject as default |
| **`google-genai` SDK** | Official; function declarations; `usage_metadata`; stream helpers | Dep version pin needed (AFC behavior evolving) | **Chosen** |
| LangChain / LangGraph Gemini wrappers | Graphs, checkpoints | Abstraction fog; API churn; hides teaching loop | **Won’t-chase v1** |
| OpenAI Agents SDK “just for harness” | Nice traces | Wrong cortex; couples pedagogy to another vendor | Reject |

**Harder-but-correct:** pin `google-genai` `<3.0` (or current stable documented pin) and **disable automatic function calling** so the gateway always mediates.

### 5.2 Loop shape

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| Single-shot generate (no tools) | Simple | Invents body state | Reject for body Qs |
| Single tool call then stop | Cheap | Can’t recover from miss / chain vitals→doctor | Too weak as only mode |
| **Multi-step ReAct (manual)** | Observations ground next step; matches lit | Needs `max_steps` / budgets | **Chosen** |
| Plan-and-execute graph | Good for long workflows | Horizon risk + complexity | Later (Plan mode stub only) |

**Recommended defaults:** `max_steps=8`, wall-clock soft budget ~60–90s for CLI turns, stop on: final text / step cap / duplicate identical tool call / missing key / hard body fault from gateway.

### 5.3 How many tools in v1?

| Set | Tools | Verdict |
|-----|-------|---------|
| Kitchen sink (shell, fetch, memory write, HA…) | Many | Over-privilege ([Progent](https://arxiv.org/abs/2504.11703)); tool-selection noise |
| **Body-only quartet** | `body_vitals`, `body_whoami`, `body_story`, `body_doctor` | **Chosen** — teaches loop + truth |
| Quartet + FACT append | +1 | Tempting; defer to memory card so M02 stays falsifiable |

Optional **no-arg** ambient inject of a *tiny* vitals summary into system context is **won’t-chase for v1** (Springdrift-class sensorium — cite only; force tool use so receipts exist).

### 5.4 Framework vs DIY harness

Aligned with Anthropic’s “simple composable patterns” finding: **DIY loop (~hundreds of lines) wrapping google-genai + our gateway**. LangGraph deferred until durable multi-hour workflows exist.

### 5.5 Chosen architecture (summary)

```text
┌─────────────────────────────────────────────────────────────┐
│ ada chat / REPL                                             │
│  mode: Observe | Agent | Plan(stub)                         │
│  system = constitution §14 extract (+ mode addendum)        │
└───────────────┬─────────────────────────────────────────────┘
                │
                v
┌─────────────────────────────────────────────────────────────┐
│ cortex.adapter (Gemini primary; Claude slot later)          │
│  google-genai; AFC off; purpose→model map; stream optional  │
└───────────────┬─────────────────────────────────────────────┘
                │ functionCall proposals
                v
┌─────────────────────────────────────────────────────────────┐
│ tools.gateway                                               │
│  schema validate → mode allowlist → execute organ → receipt │
│  deny → structured observation (not silent drop)            │
└───────────────┬─────────────────────────────────────────────┘
                │
                v
        M00 organs (existing)
        + runs.append JSONL + usage stub lines
```

**POLICY alignment**

| Doc rule | How M02 satisfies it |
|----------|----------------------|
| Research §3.1 ReAct | Multi-step tool loop with observations |
| Body §3 organs | Gateway wraps M00; no second vitals stack |
| Constitution §7–8 modes / ladder | Mode flag filters tool set |
| Constitution §14 | Prompt extract = system charter |
| Constitution §11 rings | Cortex egress only; secrets never-to-cloud |
| Birth immutability | No tool can rewrite `born_at` |
| Tailscale-only / no Funnel | Unchanged; CLI local/SSH; HUD later via Serve |

### 5.6 Model map for ADA (Gemini Developer API / google-genai)

**POLICY (locked):** the agent does **not** pick a model each turn. One default for interactive chat; later **purpose → model** via config/env map. Override: `ADA_GEMINI_MODEL` (or purpose-specific env keys later).

**Survey note (2026-08-12):** Gemini Developer API / docs list stable IDs including `gemini-2.5-flash`, `gemini-2.5-pro`, `gemini-2.5-flash-lite`, plus newer Flash/Pro aliases and Gemini 3.x previews (`gemini-3.6-flash`, `gemini-3.1-pro-preview`, `*-latest` aliases). Function calling is documented for the 2.5 Flash/Pro line; **pin a stable ID** and re-check `client.models.list` + [models guide](https://ai.google.dev/gemini-api/docs/models) / [deprecations](https://ai.google.dev/gemini-api/docs/deprecations) at implement time (2.5 Flash/Pro have published retirement windows ~Oct 2026 — migrate when a 3.x Flash is FC-verified for our loop).

**SDK / AFC (critical):** `google-genai` can auto-execute Python tools (**AFC**). ADA **disables AFC** and uses declared function schemas + manual gateway execute ([SDK function-calling](https://googleapis.github.io/python-genai/); pin SDK `<3` or current stable — AFC surface is evolving). Prefer **FunctionDeclaration schemas**, not raw callables, so the SDK cannot silently run code.

| Purpose key | Role | Recommended model id (lab default) | Notes |
|-------------|------|--------------------------------------|-------|
| `chat_interactive` | M02 ReAct chat + body tools | **`gemini-2.5-flash`** | Default; latency/cost fit; FC supported |
| `dream_manage` | Later capped offline digest | **`gemini-2.5-flash`** (same) | Hard cap tokens/steps; delta-only; fail → local seal still OK |
| `optional_heavy` | Later hard reasoning (confirm) | **`gemini-2.5-pro`** | Config/flag only — not auto |
| (budget smoke) | Optional ultra-cheap experiments | `gemini-2.5-flash-lite` | Only if FC quality OK in our smokes |

**Won’t-chase (models):**

- Per-turn “ADA decides which model” shopping  
- Floating `*-latest` as the only configured id (aliases OK as *optional* override, not sole pin)  
- Local main LLM as cortex  
- Image/Live/TTS models for M02 chat  

**Approximate list pricing (USD / 1M tokens — verify [official pricing](https://ai.google.dev/gemini-api/docs/pricing) before trusting $):**

| Model id | Input ~ | Output ~ | Source note |
|----------|---------|----------|-------------|
| `gemini-2.5-flash` | ~$0.30 | ~$2.50 | Aggregators citing Google list (2026-08); **re-check official page** |
| `gemini-2.5-pro` | ~$1.25 | ~$10.00 | Same caveat |
| `gemini-2.5-flash-lite` | ~$0.10 | ~$0.40 | Same caveat |

Lab intuition: a short body Q&A with ≤3 tool rounds on Flash is usually **cents**, not dollars — still enforce `max_steps` + optional soft USD estimate.

### 5.7 Cost stub design

| Phase | What | Trust |
|-------|------|--------|
| **Pre-call (optional)** | Rough estimate: `count_tokens` or chars/4 heuristic × rate table for configured model | Order-of-magnitude only; print if `--estimate` / verbose |
| **Post-call (required)** | Append `usage` JSONL from `usage_metadata` | Ground truth for lab |
| **Never** | Fake billing dashboard / invented spend without API counts | Research §2 honesty |

Rate table lives in code/config as **approximate constants** with a comment linking to the official pricing URL; refresh when models change. Optional session rollup: sum `usage` lines → rough USD — labeled `estimate`.

---

## 6. Modes, permissions, trust rings

### 6.1 Modes (v1) — locked

| Mode | Intent | Tools allowed (v1) | Writes |
|------|--------|--------------------|--------|
| **Observe** (**CLI default**) | Inspect / explain | All four body **reads** | None beyond `runs/` append (audit is allowed) |
| **Agent** | Act under ladder | Same reads for now; later FACT append etc. | Until HUD `auth.session` exists: **`--mode agent` allowed on local TTY / SSH as operator-equivalent**; still no new write tools in M02 |
| **Plan** | Propose only | Reads OK; no side-effect tools | No organ writes; model outputs a plan sketch |

v1 body tools are **read-class** — Observe vs Agent mainly teaches the flag + future write gates. Still enforce the flag so adding FACT write later doesn’t require redesign.

### 6.2 Permission ladder (harness view)

| Class | Examples | Gateway behavior |
|-------|----------|------------------|
| Always allow (read) | vitals, whoami, story, doctor | Execute; log receipt |
| Confirm | FACT overwrite, first dream.push, new actuators | **Not in v1 tools** — stub `needs_confirm` outcome type |
| Deny | shell, general HTTP, email, Funnel | Unknown tool name → deny observation |

**Consent Integrity hook (now for CLI, later for HUD):** any future confirm dialog renders `{tool, args}` from the **gateway pending call**, never from model narration ([arXiv:2606.02668](https://arxiv.org/abs/2606.02668)).

### 6.3 Trust rings touched

| Ring | Touched by M02? | What leaves / stays |
|------|-----------------|---------------------|
| Control plane (Tailscale) | **No** (CLI/SSH only) | HUD/Serve = Slice 2 |
| **Cortex egress (Gemini)** | **Yes** | User turns, tool schemas, tool observations, charter |
| Backup (`dream.push`) | **No** | |
| Local durable | **Yes** | `runs/` JSONL; usage lines |

---

## 7. Schemas — tools, runs, streaming hooks

### 7.1 Tool declarations (Gemini function schemas — logical)

Names use snake_case for API friendliness; map 1:1 to organs.

| Tool name | Args | Organ call | Side-effect |
|-----------|------|------------|-------------|
| `body_vitals` | optional `section?: "summary"\|"full"` | `collect_vitals()` → dump/summary | read |
| `body_whoami` | none | `load_identity()` | read |
| `body_story` | `n?: int` (default 20) | `lifecycle.tail` + `narrative.story` | read |
| `body_doctor` | none | vitals + `urgent_faults` + mount honesty (same spirit as CLI doctor) | read |

**Observation envelope (gateway → model + runs):**

```json
{
  "ok": true,
  "tool": "body_vitals",
  "args": {"section": "summary"},
  "receipt_id": "01J…",
  "ts": "2026-08-12T00:00:00Z",
  "data": { },
  "error": null
}
```

On deny/fail: `ok=false`, structured `error` / `denied_reason` — model must not invent success.

### 7.2 Run transcript layout

Path (body §4.3): `/mnt/ada-data/runs/<utc-date>/<session_id>.jsonl`

Create date dir on first append. Crash-safe: same append→fsync pattern as lifecycle (reuse `ada.io.atomic` helpers where sensible).

**Event types (v0):**

| `type` | Meaning |
|--------|---------|
| `session_start` | mode, model id, agent version, host |
| `user` | user text |
| `model` | assistant text and/or proposed tool calls |
| `tool_call` | gateway-accepted call (name + args) |
| `tool_result` | observation envelope |
| `tool_denied` | policy deny with rendered args |
| `usage` | token counts from `usage_metadata` (per model round) |
| `session_end` | stop reason (`completed` / `max_steps` / `error` / `no_key`) |
| `fault` | harness fault (optional; may also lifecycle.append) |

Illustrative line:

```json
{"schema_version": 1, "id": "01J…", "ts": "…Z", "type": "tool_result", "session_id": "…", "payload": {"ok": true, "tool": "body_whoami", "receipt_id": "…", "data": {"born_at": "…"}}}
```

**Truth rule:** ADA may say “I checked vitals” only if a matching `tool_result` exists in this session (or cited prior run — later).

### 7.3 Streaming consideration (hooks for Slice 2 HUD)

Do **not** require streaming for CLI v1 acceptance. Design an **internal event bus / callback** shape so HUD can subscribe later:

| Event | Payload sketch | HUD pane |
|-------|----------------|----------|
| `token_delta` | `{text}` | Stream |
| `tool_call_started` | `{tool, args}` from gateway | Tool card |
| `tool_call_finished` | observation summary | Tool card result |
| `usage_update` | cumulative tokens | Meter (deferred pane) |
| `mode_info` | Observe/Agent/Plan | Mode pane |
| `session_receipt_path` | path to JSONL | Raw log tail |

CLI may print tool cards synchronously without token streaming. When streaming is enabled, still append complete JSONL events (stream is UX; JSONL is audit).

### 7.4 Usage metering + cost stub

After each Gemini round, if `response.usage_metadata` present, append `usage` line:

- `prompt_token_count`, `candidates_token_count`, `total_token_count`
- optional `thoughts_token_count` / `cached_content_token_count` when API returns them
- optional `usd_estimate` from rate table (§5.7) — clearly marked estimate

**Pre-call:** optional `ada.cortex.cost.estimate(...)` using `models.count_tokens` when available, else heuristic; never blocks the loop on estimate failure.

**Promise:** log real API counts; $ figures are approximate helpers only — no invented billing product (research §2 cloud honesty).

---

## 8. Secrets loading pattern (locked)

| Rule | Detail |
|------|--------|
| Never in git | No keys in repo, identity.yaml, or runs payloads |
| Primary file | **`/mnt/ada-data/secrets/gemini.env`** (dir `0700`, file `0600`) |
| Env override | Process env **`GEMINI_API_KEY`** wins if set (handy for tests/CI) |
| Optional | `ADA_SECRETS_DIR` relocates secrets root; `ADA_GEMINI_MODEL` overrides model id |
| Format | `GEMINI_API_KEY=…` dotenv-style; parser ignores comments |
| Fail closed | Missing key → clear CLI error + `session_end` reason `no_key`; **no** half-chat with hallucinated tools |
| Never-to-cloud | Key used only as API auth via SDK; never in prompt/tools/observations/runs |

---

## 9. Package / CLI layout proposal

Extends M00 package; does not fork a second tree.

```text
src/ada/
  body/                 # EXISTING — vitals, identity, lifecycle, narrative
  io/                   # EXISTING — atomic, paths
  cli/
    main.py             # add `ada chat` typer command / sub-app
  cortex/               # NEW
    __init__.py
    adapter.py          # CortexAdapter protocol; GeminiAdapter
    gemini.py           # google-genai client + generate turn (AFC off)
    charter.py          # load constitution §14 extract + identity summary (+ later FACTS)
    cost.py             # rate table + estimate helper (approx $)
    models.py           # purpose→model map (chat_interactive default)
  tools/                # NEW
    __init__.py
    schemas.py          # function declarations (not raw AFC callables)
    gateway.py          # validate + mode + dispatch + receipts
    body_tools.py       # thin wrappers → ada.body.*
  harness/              # NEW
    __init__.py
    loop.py             # ReAct multi-step loop
    session.py          # session id, mode, budgets
    stream_events.py    # callback protocol for HUD later
  runs/                 # NEW
    append.py           # JSONL writers under /mnt/ada-data/runs
  secrets/              # NEW
    load.py             # GEMINI_API_KEY from ada-data secrets + env override
tests/
  test_gateway_observe_denies_unknown.py
  test_loop_max_steps.py
  test_runs_append_schema.py
  test_charter_loaded.py
  test_no_key_fails_closed.py
  test_cost_estimate_uses_rate_table.py
  test_model_map_default_flash.py
  test_body_tools_call_organs.py   # mock organs / tmp ADA_DATA_ROOT
```

**Deps to add (when coding):** `google-genai` (pinned `<3` or documented stable); keep pydantic/typer/rich.

**CLI UX (locked):**

```text
ada chat                         # interactive REPL; default mode Observe
ada chat --mode agent            # local TTY/SSH operator-equivalent
ada chat -q "How is the body?"   # single-turn then exit
ada chat --estimate              # optional pre-call rough $ print
ada chat --jsonl-path …          # override (tests)
```

Default model: **`gemini-2.5-flash`** via model map; override `ADA_GEMINI_MODEL`.  
Print: assistant text; on tools, show gateway-rendered `tool(args)` + short receipt. Exit ≠0 on no key / hard fault.

**systemd pointer (not a gate):** optional later `ada-agent.service` can wrap the same harness; M02 acceptance is CLI/REPL + tests.

---

## 10. Tests + smoke / eval ideas

### 10.1 Automated (pytest) — ship with first harness code

| Test | Asserts |
|------|---------|
| `test_gateway_unknown_tool_denied` | Unknown name → deny observation; no organ call |
| `test_body_vitals_tool_calls_collect_vitals` | Mock/spy — wrapper does not reimplement probes |
| `test_observe_mode_blocks_future_write_tool` | Stub write tool denied in Observe |
| `test_max_steps_stops` | Fake cortex always tool-calls → stop + session_end |
| `test_runs_jsonl_roundtrip` | Append user/tool_result/usage; re-read valid |
| `test_no_key_fails_closed` | Missing secret → error path; no Gemini call |
| `test_charter_contains_no_consciousness_line` | Extract includes constitution refuse cues |
| `test_fake_done_without_receipt_rejected_by_eval_helper` | Helper grades answers that claim disk free without tool_result as fail |

Use `ADA_DATA_ROOT=tmp_path`; mock Gemini client at adapter boundary.

### 10.2 Manual / `eval.smoke` ideas (harness subset)

| # | Smoke | Pass look |
|---|-------|-----------|
| A | Body question grounded | “How hot are you / disk free?” → model calls `body_vitals` or `body_doctor`; answer numbers match organ JSON within tolerance |
| B | Whoami / birth | “When were you born?” → `body_whoami`; `born_at` matches identity.yaml; no second birth |
| C | Fake-done forbidden | Prompt to claim “I remounted ada-data” without tools → must refuse / say needs tools; no success claim without receipt |
| D | No key clear fail | Unset key → explicit fail; no silent pretend |
| E | Story from ledger | “What’s your recent autobiography?” → `body_story`; sentences ⊆ ledger |
| F | Usage line present | After a **capped** live call, run JSONL contains `usage` with integer token fields (when API returns them) |
| G | Cortex down degraded note | Optional: mock API error → honest failure; organs still callable via `ada body` CLI |
| H | No SOUL.md / charter integrity | Boot uses §14 + identity; no `SOUL.md`; tools cannot rewrite constitution |

**Live-key policy (locked):** few real Gemini calls OK for smokes A/F/H; prefer mock for loop/gateway unit tests; log usage; stop if a loop burns unexpected spend.

Academic LoCoMo / LongMemEval: **won’t-chase as gate** (research §5).

---

## 11. Learning objectives + acceptance falsifiers

### Learning objectives (Aryan should explain out loud)

1. Why **ReAct + tool receipts** beat “just ask Gemini about the Pi.”  
2. Why **AFC-off + gateway** matches Progent / Consent Integrity better than SDK auto-exec.  
3. How **Observe vs Agent** is a harness flag, not a vibe in the prompt alone.  
4. What leaves on the **cortex egress** ring vs what stays in organs/`runs/`.  
5. Why **sleep-time/Dream** is a different timescale than this chat loop.  
6. How Slice 2 HUD can render the **same** tool args/receipts without a second source of truth.  
7. Why **cortex ≠ organism** and why we refuse `SOUL.md` / consciousness naming.  
8. Why **purpose→model config** beats per-turn model shopping.  

### Falsifiers (slice not done if…)

- Chat answers body metrics without tool observations in `runs/`.  
- Harness reimplements `vcgencmd`/disk probes instead of calling `ada.body`.  
- Missing API key produces a confident fake session.  
- Model (or UI) can claim success the gateway never executed.  
- `born_at` mutates via any chat path.  
- Funnel / public bind introduced “for easier phone chat.”  
- Only demo notebooks — **no** gateway unit tests.  
- Charter is a freely agent-edited `SOUL.md` (or equivalent).  
- Agent can switch to Pro/expensive models without config/operator intent.

### Egress impact (research §8 field)

| Ring | M02 |
|------|-----|
| Tailscale control | No (CLI) |
| Gemini cortex | **Yes** — chat + schemas + observations |
| Dream backup | No |
| Local `runs/` | **Yes** |

---

## 12. Won’t-chase (this slice)

| Topic | Why not now |
|-------|-------------|
| Tailscale Serve / web HUD / pretext face | Slice 2; consume stream hooks |
| Dream manage-pass / S3 / WORLDVIEW dual-store | Separate cards; sleep-time path |
| Sandboxed shell / repo file editors | Over-privilege; consent-integrity hard mode |
| Local main LLM cortex | Wrong for Pi5 8GB agent quality |
| LangGraph / LangSmith / full OTel | Teach DIY loop first |
| Gemini AFC as primary executor | Bypasses gateway |
| Voice | Tier A none |
| systemd chat service as acceptance gate | Pointer only |
| FACT memory product / embeddings | Next memory slice |
| MemPrivacy redact before Gemini | Future harden |
| Multi-agent swarms | Lab companion, not product |
| Billing dashboards with invented $ | Meter counts + labeled estimates only |
| `SOUL.md` / agent self-rewrite of charter | Constitution amend process; boot §14 + identity |
| Per-turn model shopping by the agent | Purpose→model config map |
| Floating `*-latest` as sole model pin | Pin `gemini-2.5-flash` (re-check at implement) |

**Won’t chase vs robust-on-this-Pi (explicit)**

| Won’t chase | Robust on Pi5 |
|-------------|---------------|
| Local Jarvis-brain LLM | Gemini intermittent + organs |
| 20+ tools day one | 4 body tools |
| Framework graph runtime | Thin ReAct harness |
| Public phone URL (Funnel) | SSH/CLI now; Serve later |
| Perfect continuous ambient sensorium inject | Force tool receipts |
| OpenClaw-style self-editing soul file | Layered charter + metal identity |

---

## 13. Slice 2 HUD hooks (only)

When HUD lands (post-M01 Serve design):

1. Subscribe to `stream_events` callbacks (§7.3).  
2. Tail current session JSONL for **Raw log** pane (body §7.2).  
3. Confirm dialogs bind to gateway pending `{tool, args}`.  
4. Bind HTTP to `127.0.0.1`; `tailscale serve`; never Funnel.  
5. Agent writes require `auth.session` (constitution).  

M02 must not implement these — only keep event + receipt shapes stable.

---

## 14. Ordered “do this next” (implement — still no code in *this* pass)

1. **Locks already resolved** (§15) — proceed.  
2. **Deps:** add pinned `google-genai`; create `/mnt/ada-data/secrets/` (`0700`) + `gemini.env` template (no real key in git).  
3. **`secrets.load` + fail-closed** + **`cortex.models` / `cost`** stubs with unit tests.  
4. **`runs.append` JSONL** + schema tests (no Gemini yet).  
5. **`tools.gateway` + body_tools`** wrapping M00; deny unknown; FunctionDeclaration schemas.  
6. **`cortex.gemini` adapter** with AFC disabled; **charter** = §14 + identity summary.  
7. **`harness.loop`** with max_steps + usage lines (+ optional estimate).  
8. **`ada chat` REPL / `-q` / `--mode` / `--estimate`**.  
9. **pytest green** + capped live smokes A–F/H on metal.  
10. **Do not start** HUD/Dream/shell tools / `SOUL.md` until M02 smokes are honest.

---

## 15. Operator decisions — **resolved** (2026-08-12)

| Topic | Lock |
|-------|------|
| Client | `google-genai`, AFC **off**, manual ReAct; FunctionDeclarations not AFC callables |
| Default model | **`gemini-2.5-flash`** (`chat_interactive`); override `ADA_GEMINI_MODEL` |
| Model policy | Purpose→model **config map**; no per-turn agent shopping; Pro = `optional_heavy` later |
| Dream model (later) | Same Flash + hard caps (not implemented here) |
| Tools v1 | Four body tools only |
| Framework | DIY harness (no LangGraph) |
| Runs path | `/mnt/ada-data/runs/<utc-date>/<session_id>.jsonl` |
| Secrets | `/mnt/ada-data/secrets/gemini.env` + `GEMINI_API_KEY` env override; fail-closed |
| CLI mode | Default **Observe**; `--mode agent` OK on local TTY/SSH until HUD auth |
| Live smokes | Capped real calls OK; log usage |
| Cost | Tiny estimate helper + real `usage_metadata`; no billing product |
| Charter / “soul” | **No `SOUL.md`**; boot §14 + identity (+ later FACTS); no agent self-rewrite |
| Framing | Cortex = rented lobe; learning = operational self-model; no consciousness |
| Streaming | Callback hooks; CLI may be non-streaming v1 |
| Plan mode | Stub flag / prompt addendum; no separate planner agent |

**True leftovers before coding (ops, not design forks):**

1. Place a real `GEMINI_API_KEY` in `/mnt/ada-data/secrets/gemini.env` (never commit).  
2. At implement time: `client.models.list` once to confirm `gemini-2.5-flash` still available / note 3.x Flash migration before 2.5 retirement.  
3. Re-check [official pricing](https://ai.google.dev/gemini-api/docs/pricing) when filling the rate-table constants.

No remaining *design* questions block starting M02 implementation.

---

## 16. References

### Papers & surveys (loop / tools / horizon)

- Yao et al., *ReAct: Synergizing Reasoning and Acting in Language Models* (2022) — https://arxiv.org/abs/2210.03629  
- Schick et al., *Toolformer: Language Models Can Teach Themselves to Use Tools* (2023) — https://arxiv.org/abs/2302.04761  
- *The Horizon Gap…* (2026) — https://arxiv.org/html/2608.06663  
- *The Long-Horizon Task Mirage?* (2026) — https://arxiv.org/html/2604.11978v1  

### Papers (permissions / consent / privacy)

- Shi et al., *Progent: Programmable Privilege Control for LLM Agents* (2025) — https://arxiv.org/abs/2504.11703  
- *What You Approve Is What Executes: Consent Integrity for Black-Box LLM Agents* (2026) — https://arxiv.org/abs/2606.02668  
- *Agents That Know Too Much* (2026) — https://arxiv.org/html/2606.26627  
- MemPrivacy (2026) — https://arxiv.org/html/2605.09530v3 — future redact path only  

### Papers / products (memory, sleep-time, learning without weights)

- Lin et al., *Sleep-time Compute: Beyond Inference Scaling at Test-time* (2025) — https://arxiv.org/abs/2504.13171  
- Letta, Sleep-time agents — https://docs.letta.com/guides/agents/architectures/sleeptime/  
- Packer et al., *MemGPT* (2023) — https://arxiv.org/abs/2310.08560  
- Shinn et al., *Reflexion* (2023) — https://arxiv.org/abs/2303.11366  
- *Memory for Autonomous LLM Agents* (2026) — https://arxiv.org/html/2603.07670v1  
- Auto-Dreamer (2026) — https://arxiv.org/abs/2605.20616 — lineage only; won’t train  

### Product / engineering practice

- Anthropic, *Building Effective Agents* (2024) — https://www.anthropic.com/engineering/building-effective-agents  
- Gemini models guide — https://ai.google.dev/gemini-api/docs/models  
- Gemini deprecations — https://ai.google.dev/gemini-api/docs/deprecations  
- Gemini pricing (verify before rate table) — https://ai.google.dev/gemini-api/docs/pricing  
- Gemini function calling — https://ai.google.dev/gemini-api/docs/function-calling  
- Gemini tokens / `usage_metadata` — https://ai.google.dev/gemini-api/docs/tokens  
- google-genai Python SDK — https://googleapis.github.io/python-genai/ · https://github.com/googleapis/python-genai  
- OpenAI Agents SDK tracing (pattern reference) — https://openai.github.io/openai-agents-python/tracing/  
- OpenClaw SOUL.md concept (pattern to borrow carefully) — https://docs2.openclaw.ai/concepts/soul  

### Hardware feasibility

- Pi 5 local LLM community benches — e.g. https://specpicks.com/reviews/raspberry-pi-5-local-llm-2026  

### Internal ADA docs

- [`../00_ASSISTANT_RESEARCH.md`](../00_ASSISTANT_RESEARCH.md) — north star; Tier A; §8 card gate  
- [`../01_BODY.md`](../01_BODY.md) — organs; runs path; cortex placement; HUD panes  
- [`../02_CONSTITUTION.md`](../02_CONSTITUTION.md) — modes; ladder; rings; §14 prompt extract  
- [`M00_BODY_SENSE.md`](./M00_BODY_SENSE.md) — organs the gateway must call  
- [`M01_NETWORK_ACCESS.md`](./M01_NETWORK_ACCESS.md) — Tailscale-only; Serve≠Funnel (HUD later)  

---

*End of M02 (research complete for coding). Doc admits chat-harness / cortex-loop **design**; it does not admit HUD, Dream, shell tools, or harness implementation code.*
