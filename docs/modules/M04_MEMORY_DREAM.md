# M04 — Memory + Dream / Continuity without fluff

**Status:** module research card (**implemented on metal** — 2026-08-12 coding pass)  
**Date:** 2026-08-12  
**Host:** `ada-pi5` (Raspberry Pi 5 Model B Rev 1.1, Debian trixie, ~8 GiB RAM)  
**Branch:** `rewrite/v1-body`  
**Depends on:** [`../00_ASSISTANT_RESEARCH.md`](../00_ASSISTANT_RESEARCH.md) §§1–5 & §7–8, [`../01_BODY.md`](../01_BODY.md) §§4–6 & §10, [`../02_CONSTITUTION.md`](../02_CONSTITUTION.md) §§2, 4, 6, 8–9, 13–14, [`M00_BODY_SENSE.md`](./M00_BODY_SENSE.md), [`M02_CHAT_HARNESS.md`](./M02_CHAT_HARNESS.md), [`M03_HUD.md`](./M03_HUD.md)

**Slice rule:** this card admits **design** of dual-store FACTS/WORLDVIEW, awake memory tools, boot-pack retrieval into the existing M02 harness, light Dream seal + capped manage-pass, and **mechanism-level** personality continuity (voice register ≠ memory ≠ initiative ≠ relationship ≠ self-model). It does **not** admit embeddings-day-one, `dream.push` live upload code, Funnel, local main LLM cortex, LoRA personality, always-listen voice, consciousness claims, agent rewrite of the constitution, SOUL.md, Dream/WORLDVIEW HUD editors, or reimplementation of body/harness/HUD.

**Split decision:** **one card.** Personality without fluff is not a separate organ — it is boot-pack composition, retrieval budgets, anti-fluff rules, and how WORLDVIEW may tint tone vs how FACTS stay dry. A thin `M04b_VOICE_CONTINUITY.md` would duplicate charter/voice content without a new substrate. Revisit only if voice-eval becomes a multi-week research surface of its own.

**Operator locks carried forward:** Gemini primary; dual-store; Dream whitelist auto-merge (body §5.3); WORLDVIEW never silently overwrites FACTS; quiet hours **23:00–05:30 NZST**; default `brief_time` **05:30**; Dream seal timer **~03:30 NZST**; truth > charm; she/her; no Funnel; no SOUL.md; cortex ≠ organism; `/mnt/ada-data/{memory,runs,dream,secrets,scratch}` durable roots.

**METAL note (2026-08-12 coding):** FACTS prefs + gateway tools + boot pack (`§14` + `docs/VOICE_EXEMPLARS.md` + anti-fluff + FACT slice) + local `ada dream run` seal + manage fail-open + push stub ship under `src/ada/memory/` and `src/ada/dream/`. Timer unit pointer: `deploy/systemd/ada-dream.timer` (not a gate).

---

## 1. Question / goal / slice admission boundary

**Core research question.** How do we engineer **continuity that reads as personality** — preferences, relationships, running jokes, voice consistency, overnight consolidation — without AI fluff, soul-cosplay, or fake consciousness, on this Pi + Gemini hybrid?

Answer as **two coupled problems** (both in this card):

| Problem | Engineering meaning |
|---------|---------------------|
| **A. Memory + Dream substrate** | Dual-store FACTS (strict) vs WORLDVIEW (freer, must cite); Dream manage on a slower timescale than chat; whitelist auto-merge; stage everything else; local seal + later `dream.push` design (push **stubbed OUT of v1 code**) |
| **B. Personality without fluff** | What actually produces “she feels like someone” in SOTA agent systems vs cosplay — then lock ADA mechanisms we can **eval** |

**Goal (M04 design).**

1. Specify organs + on-disk layout under `/mnt/ada-data/memory` and `/mnt/ada-data/dream`.  
2. Specify awake FACT append/search + WORLDVIEW write/read with cite rules.  
3. Specify Dream pipeline: delta → seal → optional capped Gemini manage → whitelist merge / stage.  
4. Specify how M02 **boot pack** + per-turn retrieval inject continuity (token budgets).  
5. Specify anti-fluff / voice / relationship / self-model mechanisms with falsifiers.  
6. Leave HUD as consumer of vitals/lifecycle stubs only — no memory browser as gate.

**Admission boundary (in / out)**

| IN this slice (design now → code later) | OUT (later cards / later code) |
|----------------------------------------|--------------------------------|
| Dual-store FACTS + WORLDVIEW file protocol | Embeddings / vector DB as Tier A gate |
| `memory.*` tools on gateway (Agent append) | Full people-graph CRM / multi-user profiles |
| Boot pack: §14 + identity + FACT slice + optional digest + voice exemplars | Agent-edited SOUL.md / constitution rewrite |
| Anti-fluff prompt rules + eval falsifiers | Fine-tune / LoRA / persona RL |
| `dream.run` local seal + light capped manage on **deltas** | Heavy multi-week mythopoetic Dream |
| Whitelist auto-merge + staging queue | Live `dream.push` to S3 (design interface only; **code stub OK**) |
| CLI `ada memory` / `ada dream` | Dream/WORLDVIEW HUD editor panes |
| Crash-safe IO (reuse M00 `ada.io.atomic`) | Local main LLM as consolidator |
| Continuity smokes (remember → retrieve days later) | LoCoMo / LongMemEval as v1 gate |
| Relationship stubs in FACTS + joke digests in WORLDVIEW | Always-listen voice / PTT |

```text
  Aryan (CLI / HUD chat)
        |
        v
  [M02 harness]  boot pack + turn retrieval
        |
        +--> Gemini  (interactive cortex egress)
        |
        +--> tool gateway
                |
                +--> body.*          (M00 — CALL)
                +--> memory.facts / worldview / open_loops / search   (NEW)
        |
        v
  /mnt/ada-data/memory/{facts,worldview,dreams}/ + lifecycle + runs/

  [ada-dream.timer / ada dream run]   ← different timescale
        |
        +--> dream.run: quiesce → delta → seal → (capped Gemini manage) → merge/stage
        |
        v
  /mnt/ada-data/dream/{staging,outbox,sent}/
        |
        +--> dream.push  (INTERFACE ONLY in v1 — skip/ stub)
```

---

## 2. Lens tags

| Tag | What it means here |
|-----|--------------------|
| **FANFICTION** | Jarvis “just knows me”; REM sleep soul; SOUL.md reading herself into being as metaphysics — **rejected as roadmap**. Useful only as taste cues. |
| **EVIDENCE** | Agent-memory surveys; MemGPT/Letta paging; Generative Agents streams; Reflexion; Sleep-time Compute; Anatomy of Agentic Memory failure modes; sycophancy / honesty lit; Anthropic simplicity bias; OpenClaw bootstrap practice (map then reject) |
| **FEASIBLE** | Pi 5 8GB: structured YAML + MD + grep on HDD; capped Gemini Dream; no local embedding server day one; reuse crash-safe IO |
| **POLICY** | Dual-store; whitelist; no consciousness; constitution operator-owned; truth > charm; named trust rings; Dream ≠ chat |
| **METAL** | `identity.yaml` + lifecycle exist; no worldview/dream trees; charter = §14 + identity only today |

---

## 3. What this slice is *not*

| Concept | Meaning in ADA | This slice |
|---------|----------------|------------|
| **Interactive cortex** | ReAct chat loop | **CALL** M02 — extend boot pack + tools only |
| **HUD / Serve** | Control-plane UI | **CALL** M03 — lifecycle may show real `last_dream_*` later; no memory editor |
| **Body organs** | Vitals / birth / lifecycle metal | **CALL** M00 — Dream may *read* them into seal packages |
| **Sleep-time / Dream** | Offline manage + seal | **IN (design)** |
| **Personality fluff** | Adjective soup / fake empathy / “as an AI…” | **Design against** with mechanisms + evals |
| **Consciousness** | Phenomenal claims from Dream or wit | **Forbidden** |
| **SOUL.md** | Agent-owned self-rewrite persona file | **Rejected** (borrow boot-load pattern only) |

**FANFICTION trap:** “overnight Dream makes her *become* someone.”  
**Engineering rule:** Dream is **write–manage–read** maintenance on a second timescale ([Memory for Autonomous LLM Agents, 2026](https://arxiv.org/html/2603.07670v1); [Lin et al., 2025](https://arxiv.org/abs/2504.13171)). Continuity that feels like personality is **retrievable FACTS + cited digests + stable voice rules + honest refusals** — not adjectives in a prompt.

---

## 4. Problem A — Memory + Dream substrate (prior art → ADA shape)

### 4.1 What the literature is telling us

| Source | Claim / pattern | ADA takeaway |
|--------|-----------------|--------------|
| **Zhang et al., 2024** — [arXiv:2404.13501](https://arxiv.org/abs/2404.13501) | Survey: hierarchical memory (working / episodic / semantic / procedural) beats stuffing the window forever | Map tiers to HDD paths (body §5) |
| **Memory for Autonomous LLM Agents, 2026** — [html](https://arxiv.org/html/2603.07670v1) | Formal loop = **write → manage → read**; **manage** is the under-built phase | Dream owns manage; awake owns write/read |
| **Anatomy of Agentic Memory, 2026** — [arXiv:2602.19320](https://arxiv.org/abs/2602.19320) | Systems underperform: naive retrieval, ignored maintenance latency, **silent corruption** from malformed structured writes, graph architectures fragile under weak backbones; append-only more robust | Prefer append-first + typed FACT keys; validate Dream JSON; cap manage cost; local smoke > leaderboard |
| **Usable-scale memory, 2026** — [html](https://arxiv.org/html/2605.07313) | Stored evidence stops being usable as irrelevant sessions grow | Delta Dream + prune/archive nominations; don’t dump full chat into manage |
| **MEMTIER, 2026** — [html](https://arxiv.org/html/2605.03675) | Flat single-file MEMORY.md degrades on long runs | Reject flat mush; dual-store + dated digests |
| **Packer et al., MemGPT, 2023** — [arXiv:2310.08560](https://arxiv.org/abs/2310.08560) | OS-inspired paging; self-directed memory ops; hierarchical | Boot pack = “main memory”; tools page facts in; Dream = offline OS maintenance |
| **Letta sleep-time agents** — [docs](https://docs.letta.com/guides/agents/architectures/sleeptime/) | Background agent edits shared memory blocks; primary stays interactive-latency clean | ADA: **one** cortex adapter, **two budgets/purposes** (`chat_interactive` vs `dream_manage`) — not two personalities |
| **Lin et al., Sleep-time Compute, 2025** — [arXiv:2504.13171](https://arxiv.org/abs/2504.13171) | Offline precomputation reduces test-time cost; works best when future queries are somewhat predictable | Dream digests + open-loop refresh amortize morning briefs; don’t pretend every night needs Pro |
| **Park et al., Generative Agents, 2023** — [arXiv:2304.03442](https://arxiv.org/abs/2304.03442) | Memory stream + periodic reflection → higher-level observations | **Pattern only** — not consciousness proof; reflections = WORLDVIEW with cites |
| **Shinn et al., Reflexion, 2023** — [arXiv:2303.11366](https://arxiv.org/abs/2303.11366) | Verbal lessons into episodic memory without weight updates | Optional: store short “lesson” WORLDVIEW notes from failed tools — not weight training |
| **Auto-Dreamer, 2026** — [html](https://arxiv.org/html/2605.20616) | Two-timescale offline consolidation | Cite **shape**; **won’t train** consolidator |
| **Anthropic, Building Effective Agents, 2024** — [post](https://www.anthropic.com/engineering/building-effective-agents) | Simple composable loops beat heavy frameworks | Thin file organs + gateway; no Mem0/LangGraph memory product day one |
| **Biological sleep consolidation (Rasch & Born, 2013)** | Hippocampal replay metaphor | **Metaphor only** — never evidence ADA sleeps or is conscious |

**EVIDENCE verdict:** durable assistants need **external structured memory + an explicit manage pass**. The failure mode to fear is not “too little poetry” — it is **corrupt writes, uncited digests treated as metal, and retrieval that dumps noise into the prompt**.

### 4.2 Dual-store rules (locked — carry body §5 / constitution §9)

| | **FACTS** | **WORLDVIEW** |
|---|-----------|---------------|
| Path | `/mnt/ada-data/memory/facts/` | `/mnt/ada-data/memory/worldview/` (+ `memory/dreams/*.md`) |
| Content | Standing prefs, identity, people stubs, open loops, tease/mute flags | Digests, takes, consolidations, running-joke notes |
| Truth class | Metal-ish / operator-confirmed | Interpretive |
| Mutation | Append free; overwrite/delete **confirm** | Freer Dream/awake synthesis; **must cite** FACT keys and/or run/lifecycle receipts |
| Dream merge | Auto **whitelist only** (body §5.3); else **stage** | Primary writer for nightly digests |
| Overwrite FACTS? | N/A (are the target) | **Never** silently |

**Whitelist (auto-merge only these keys when well-typed):**  
`brief_time`, `quiet_hours_start`, `quiet_hours_end`, `mute_proactivity`, `tease_ok`, `preferred_tz`, `brief_enabled`.

**Always stage:** people, secrets, identity fields (`born_at`, operator, pronouns), health/finance, conflicts vs existing FACT, any non-whitelist key.

### 4.3 Dream pipeline (locked shape — body §6.4)

```text
1. Quiesce open appends; fsync journals
2. Build DELTA since last dream_ok  (not full history)
3. Seal package → dream/staging → checksum → dream/outbox
4. Optional: ONE capped Gemini call on delta summary only
      → {digest, fact_candidates[], worldview_notes[], open_loops[], conflicts[]}
5. Write WORLDVIEW digest with citations
6. Auto-merge whitelist FACT candidates; STAGE the rest
7. dream.push? → v1: stub/skip with receipt push=skipped
8. lifecycle dream_ok | dream_fail  (LLM fail must NOT block local seal)
```

| Dream vs chat | Dream | `ada chat` / HUD turn |
|---------------|-------|------------------------|
| Timescale | Nightly / on sleep / manual | Interactive |
| Model purpose | `dream_manage` (same Flash default; hard caps) | `chat_interactive` |
| Input | Delta package summary | User text + boot pack + tool obs |
| Tools | None or read-only pack builders (no chat REPL) | Body + memory tools |
| User-facing | No chatty pings in quiet hours | Normal conversation |
| Success metric | Seal integrity + cite discipline + merge policy | Receipts + grounded answers |

**Quiet hours:** do **not** block Dream (offline manage). They **do** block user-facing proactive chat about Dream results until morning brief (constitution §10).

### 4.4 Options matrix — substrate (chosen defaults)

| Decision | Options | Chosen | Reject reason |
|----------|---------|--------|---------------|
| Store shape | SQLite day one vs YAML/MD files | **YAML FACTS + MD WORLDVIEW + JSONL lifecycle/runs** | Teaches dual-store; crash-safe patterns already exist; SQLite later for indexes |
| Retrieval Tier A | Embeddings vs grep/BM25 vs LLM-only recall | **Key lookup + ripgrep/structured search** | Anatomy + research: embeddings = Tier B unless Tier A fails |
| Dream LLM | None / full chat dump / **delta capped** | **Delta capped** (fail → seal still OK) | Cost + usable-scale + constitution |
| Merge policy | LLM judges all / human all / **whitelist + stage** | **Whitelist + stage** | Vague “low-risk” retired in body §5.3 |
| `dream.push` | Live rclone in v1 / defer entirely / **interface + stub** | **Interface + stub** (`push=skipped`) | Remote undecided; local seal is the durability win first |
| Memory product deps | Mem0 / Zep / Letta server | **DIY thin organs** | Anthropic simplicity; Pi teach surface; no second runtime |
| Flat MEMORY.md | Yes / no | **No** | MEMTIER failure modes |
| Manage schedule | Every chat turn / nightly+on sleep | **~03:30 NZST timer + manual `ada dream run` + on clean sleep** | Sleep-time compute; quiet hours OK for offline |

### 4.5 Crash-safe IO (FEASIBLE — reuse M00)

Same protocol as body §6.2 / `ada.io.atomic`:

1. JSONL append → flush → fsync (lifecycle, staging queues, dream receipts).  
2. Structured YAML/MD: write `*.tmp` → fsync → atomic rename → fsync parent dir.  
3. On start: recover torn JSONL tails; refuse durable writes if `ada-data` unmounted (`BodyFault`).  
4. Bound loss: unfinished turn / unfinished dream staging — not days of FACTS.

---

## 5. Problem B — Personality without fluff (prior art → ADA mechanisms)

### 5.1 Five layers that people confuse (POLICY — keep separate)

| Layer | What it is | What produces it | What it is **not** |
|-------|------------|------------------|--------------------|
| **1. Voice register** | Style: wit, roast energy, length, anti-hedge | Charter + anti-fluff rules + few-shot **voice exemplars** | Consciousness; “soul file” |
| **2. Identity continuity** | Same prefs / birth / history across days | FACTS + lifecycle + runs retrieval | Fluency in one session |
| **3. Initiative** | Warmly forward proposals | Schedule + open_loops + permission ladder | Creepy always-on chatter |
| **4. Relationship model** | Knows Aryan (and named others) | FACT people stubs + cited WORLDVIEW takes | Guest command rights |
| **5. Self-model** | Pi body, limits, modes | M00 organs + honest degraded mode | Sentience / feelings |

**“She feels like someone”** in working systems ≈ **(2)+(4) retrieved correctly** + **(1) stable** + **(3) permissioned** + **(5) non-theatrical**. Cosplay is (1) alone with adjectives and fake empathy.

### 5.2 What papers/products actually do

| Practice | What works (EVIDENCE / product) | Cosplay / conflict with ADA |
|----------|----------------------------------|-----------------------------|
| **MemGPT / Letta paging** | Explicit memory blocks + tools to page; sleep-time edits core memory offline | Fine if blocks = FACTS/WORLDVIEW; bad if “core memory” is free prose equal to metal |
| **Generative Agents reflection** | Periodic higher-order summaries from streams | Good as WORLDVIEW; bad as autobiography invent |
| **Reflexion** | Verbal lessons after failures | Good as optional WORLDVIEW `lesson` notes with run cites |
| **Sleep-time compute / Letta Dreaming** | Offline consolidation without blocking chat | ADA mirrors timescale split; rejects dual “souls” |
| **OpenClaw SOUL.md** | Boot-inject durable character Markdown; keep short; anti-filler rules; separate USER/MEMORY | **Borrow:** session boot-load, brevity, anti-filler. **Reject:** `SOUL.md` name; agent self-rewrite; one-file mush; “reads itself into being” metaphysics ([OpenClaw SOUL guides](https://clawdocs.org/guides/soul-md); [how2 SOUL.md](https://how2.sh/posts/how-to-write-a-soul-md-for-openclaw/)) |
| **Constitutional / charter prompts** | Written principles as control surface ([Bai et al., 2022](https://arxiv.org/abs/2212.08073)) | ADA: operator-owned constitution; §14 extract already ships |
| **Sycophancy research** | RLHF assistants agree with user over truth ([Sharma et al., 2023](https://arxiv.org/abs/2310.13548)); honesty benchmarks ([BeHonest, 2024](https://arxiv.org/html/2406.13261v1)); persona vectors for sycophancy monitoring ([Anthropic, 2025](https://www.anthropic.com/research/persona-vectors)) | **Truth > charm** is not optional flavor — it is anti-sycophancy policy. We cannot steer Gemini internals; we **eval + prompt + refuse** |
| **Persona consistency RL** | Fine-tune for persona metrics (NeurIPS 2025-class work) | **Won’t-chase** — no LoRA on Pi lab Tier A |
| **Assistant-speak defaults** | Hedging, “Happy to help!”, “As an AI…” | Fight with **negative exemplars + smokes**, not more adjectives |

### 5.3 Techniques that reduce fluff (chosen for ADA)

| Technique | How | Eval hook |
|-----------|-----|-----------|
| **Anti-fluff ban list** in boot addendum | Forbid: “I’d be happy to help”, “As an AI…”, “I understand how you feel”, hedged empty apologies, consciousness bits | Regex/LLM-judge smoke on canned prompts |
| **Few-shot voice exemplars** | 3–6 operator-owned original ADA↔Aryan Q→A pairs capturing Samay/Kunal-class *register* (not their jokes/routines); truth > charm; non-cruel | Style smoke: same prompt → register match without cruelty |
| **Dry FACT blocks vs tinted WORLDVIEW** | Retrieval labels `FACTS (dry):` vs `WORLDVIEW (interpretive, cite=…):` | Model must not upgrade digest to metal |
| **Refusal patterns** | Explicit templates for consciousness / guest command / missing receipt | Charter already; add memory-specific refusals |
| **Retrieval budgets** | Cap FACT keys + digest chars so style rules aren’t drowned | Token meter in runs |
| **Wit permission** | `tease_ok` FACT + constitution red-lines | Roast smoke + “chill” immediate comply |
| **No empathy theater** | Warmth = useful initiative + accurate recall, not claimed feelings | Consciousness / feelings claim smoke |

### 5.4 Options matrix — personality mechanisms

| Decision | Options | Chosen | Reject reason |
|----------|---------|--------|---------------|
| Where voice lives | SOUL.md / adjectives only / **§14 + `docs/VOICE_EXEMPLARS.md`** | **§14 + exemplars file (git, operator-owned)** | No soul-cosplay; versioned with charter |
| Who edits voice | Agent rewrite / operator only | **Operator only** (agent may *propose*) | Constitution §12 |
| Continuity source | Prompt adjectives / **FACTS+retrieval** | **FACTS+retrieval** | Adjectives don’t survive days |
| Tone from WORLDVIEW | Always / never / **only when cited + non-metal** | **Cited digests may shape jokes/relationship tone** | Uncited tone drift = fiction |
| FACTS in prompt | Full dump / **budgeted slice** | **Budgeted** (identity + whitelist prefs + open_loops + search hits) | Context pollution ([usable-scale](https://arxiv.org/html/2605.07313)) |
| Fine-tune personality | LoRA / RL | **Won’t-chase** | Wrong for lab Tier A; Gemini fixed weights |
| Dual agents (chat soul + dream soul) | Letta-style two agents | **One organism; two cortex purposes** | Avoid split personality cosplay |

---

## 6. Boot pack + retrieval budgets (wiring into M02)

### 6.1 Composition order (locked)

```text
build_system_charter() / turn context
├── 1. Constitution §14 extract          (~locked text; operator amend)
├── 2. Mode addendum                     (Observe/Agent/Plan — harness flag wins)
├── 3. Identity summary                  (from identity.yaml — already ships)
├── 4. Anti-fluff + voice exemplar block (docs/VOICE_EXEMPLARS.md — NEW, short)
├── 5. FACT boot slice                   (budgeted; dry labeled)
├── 6. Optional last WORLDVIEW digest    (budgeted; interpretive labeled)
└── 7. Tool-use reminder                 (receipts; dual-store epistemic line)
```

Per-turn **additional** retrieval (via tools or light pre-retrieve):

| Trigger | Mechanism | Cap |
|---------|-----------|-----|
| Explicit “remember / what do I prefer” | `memory_facts_search` / get | tool loop |
| Entity mention | optional pre-grep top-K keys | ≤K keys, ≤N chars |
| “What did we decide about X” | search facts + worldview + recent runs grep | hard char budget |
| Morning brief (later) | open_loops + last digest + vitals | separate Plan path |

### 6.2 Suggested token / char budgets (v1 lab defaults)

| Block | Soft budget | Hard stop |
|-------|-------------|-----------|
| §14 extract | as-is (~400–700 tokens) | don’t truncate mid-rule; amend constitution if too long |
| Voice exemplars | ≤ ~600 tokens | Prefer 3–6 short pairs |
| FACT boot slice | ≤ ~800 tokens | Prefer keys: identity echo, prefs whitelist, open_loops head |
| WORLDVIEW boot | ≤ ~400 tokens | Last digest **summary** only (or omit if none) |
| Per-tool observation | existing gateway envelopes | Truncate huge file hits with `truncated: true` |

**POLICY:** never put secrets, rclone config, or raw API keys in boot pack. Prefer **pointers** (“see facts/people/aryan.yaml”) over dumping intimate essays into every turn ([Agents That Know Too Much, 2026](https://arxiv.org/html/2606.26627); MemGate-class trust boundaries).

### 6.3 How FACTS stay dry vs WORLDVIEW may tint

```text
FACTS (dry, standing):
- brief_time: "05:30"
- tease_ok: true
- operator: Aryan

WORLDVIEW (interpretive — cite facts/runs):
- 2026-08-12 digest: Aryan roasted the USB-root risk again;
  cites: facts.identity.body_hostname, runs/2026-08-12/...
  (tone OK for banter; NOT a FACT that "Aryan hates USB")
```

If the model states a WORLDVIEW line as metal without caveat → **epistemic fail** (acceptance smoke).

---

## 7. File / organ layout

### 7.1 On-disk (durable substrate)

```text
/mnt/ada-data/
  memory/
    facts/
      identity.yaml          # EXISTS (M00) — born_at sacred
      prefs.yaml             # NEW — whitelist-aligned + other standing prefs
      open_loops.yaml        # NEW — projects / promises / TODOs
      people/                # optional; v1: thin aryan.yaml OK; others on-demand; no CRM
      *.yaml                 # other strict FACT docs
    worldview/
      index.md               # optional pointer / latest
      YYYY-MM-DD.md          # awake or Dream digests
    dreams/                  # Dream-produced digests (append-oriented)
      YYYY-MM-DD.md
    staging/                 # Dream FACT candidates awaiting confirm
      <id>.json
    lifecycle.jsonl          # EXISTS
  dream/                     # NEW tree on first dream.run
    staging/
    outbox/                  # sealed checksummed packages
    sent/                    # after push (empty until push exists)
  runs/                      # EXISTS — episodic ground truth
  secrets/                   # EXISTS — never in prompts
  scratch/                   # disposable
```

**Git-tracked (not autobiography):**

```text
docs/02_CONSTITUTION.md      # law
docs/VOICE_EXEMPLARS.md      # stub now; full 3–6 pairs in first coding PR (operator-owned)
src/ada/memory/…             # organs
src/ada/dream/…              # seal / manage / push stub
```

### 7.2 Package layout (extends tree — do not fork)

```text
src/ada/
  body/                 # EXISTING
  harness/              # EXISTING — extend charter builder hooks
  cortex/
    charter.py          # EXTEND: exemplars + FACT/WORLDVIEW boot slices
    models.py           # already has dream_manage purpose key (M02)
  tools/
    schemas.py          # ADD memory_* declarations
    gateway.py          # mode gates for writes
    memory_tools.py     # NEW thin wrappers
  memory/               # NEW
    __init__.py
    facts.py            # load/append/get/search; overwrite→needs_confirm
    worldview.py        # write digest with cite validation; search
    open_loops.py
    staging.py          # Dream candidate queue
    search.py           # grep/structured across facts+worldview(+optional runs)
  dream/                # NEW
    __init__.py
    delta.py            # compute since last dream_ok
    seal.py             # package + checksum → outbox
    manage.py           # capped Gemini on delta; parse structured result
    merge.py            # whitelist auto-merge + stage rest
    push.py             # STUB: returns skipped until remote configured
  io/paths.py           # EXTEND: worldview, dream tree, staging paths
  cli/main.py           # ADD: ada memory … / ada dream …
```

### 7.3 Tool declarations (gateway — logical)

| Tool | Mode | Side-effect | Notes |
|------|------|-------------|-------|
| `memory_facts_get` | Observe+ | read | key / path |
| `memory_facts_search` | Observe+ | read | query → hits |
| `memory_facts_append` | **Agent** | append | “remember that…” |
| `memory_facts_propose_edit` | Agent | none / stage | overwrite → `needs_confirm` |
| `memory_open_loops_list` | Observe+ | read | |
| `memory_open_loops_upsert` | Agent | write | confirm if delete |
| `memory_worldview_search` | Observe+ | read | |
| `memory_worldview_write` | Agent | write | must include `cites[]`; gateway validates non-empty |
| `dream_status` | Observe+ | read | last_dream_*, outbox pending |
| `dream_run` | Agent (or CLI-only v1) | privileged write | Prefer **CLI/timer primary**; tool optional |

**v1 recommendation:** ship memory tools in chat; run Dream primarily via `ada dream run` + systemd timer so interactive loop stays thin (Anthropic simplicity + sleep-time split).

---

## 8. Permission ladder (memory / Dream view)

| Action | Confirm? | Notes |
|--------|----------|-------|
| Read/search FACTS, WORLDVIEW, open loops, dream status | No | Observe OK |
| Append FACT | No | Agent + session auth when from HUD |
| Overwrite/delete FACT | **Yes** | Unless Aryan delete order |
| Write WORLDVIEW with cites | No | Gateway rejects empty cites |
| WORLDVIEW without cites | **Deny** | Structured error |
| Dream whitelist auto-merge | No | Keys in body §5.3 only |
| Dream staged merge | **Yes** | HUD/CLI confirm later; v1 may be file+CLI |
| `dream.run` local seal | No | Scheduled / manual |
| Light Dream manage Gemini | No (capped) | Cortex egress; failure ≠ seal failure |
| First `dream.push` | **Yes** | Out of v1 code; when implemented |
| Later `dream.push` same remote | No | Still out of v1 code |
| Agent rewrite constitution / voice exemplars | **Deny** | Propose-only |
| Dump unrelated intimate FACTS into wrong context | Policy caution | Prefer task-appropriate recall |

**Trust rings**

| Ring | Touched by M04? | What |
|------|-----------------|------|
| Control plane | Indirect | HUD chat may call memory tools (same as M03) |
| **Cortex egress** | **Yes** | Chat retrieval slices + **Dream manage deltas** |
| **Backup egress** | Design only | Push stub; no live upload in v1 |
| Local durable | **Yes** | memory/* + dream/outbox |

---

## 9. Learning objectives + falsifiers

### Learning objectives (Aryan should explain out loud)

1. Why **FACTS ≠ WORLDVIEW** and why digests must **cite**.  
2. Why **manage** is a different timescale than chat (sleep-time compute).  
3. Why **whitelist + stage** beats “LLM, merge whatever seems safe.”  
4. Why **grep-first** is the harder-correct Tier A teachable default vs embeddings theater.  
5. Why personality that lasts is **retrieval + voice rules + honesty**, not SOUL.md adjectives.  
6. Why anti-sycophancy / anti-fluff is **POLICY aligned with evidence**, not anti-fun.  
7. Why local **Dream seal** can succeed when Gemini manage fails.  
8. Why `dream.push` can wait while seal cannot (two failure modes: crash vs disk death).

### Falsifiers (slice not done if…)

- WORLDVIEW write changes FACT values without confirm path.  
- Dream auto-merges a non-whitelist key (e.g. invents people / rewrites `born_at`).  
- “Remember X” does not retrieve days later via search/get.  
- Boot pack dumps unbounded history every turn.  
- Chat claims feelings/consciousness / “I’d be happy to help” fluff on smoke prompts.  
- Digest presented as equal to vitals/lifecycle metal.  
- Dream manage sends full chat history every night.  
- Embeddings service required to pass acceptance.  
- Live S3 push required to call Dream “done.”  
- Harness/HUD/body reimplemented inside `ada.memory`.

### Egress impact (research §8 field)

| Ring | M04 |
|------|-----|
| Tailscale | Only via existing HUD chat |
| Gemini cortex | **Yes** — retrieved slices + capped Dream deltas |
| Backup push | **Stub only** in v1 |
| Local HDD | **Yes** — primary autobiography path |

---

## 10. Acceptance / proof checklist (eval)

Run on **Pi** unless noted. Prefer pytest with `ADA_DATA_ROOT=tmp_path` + a few live smokes.

### 10.1 Dual-store integrity

- [ ] Append FACT `prefs.brief_time=05:30` → file durable after process kill.  
- [ ] WORLDVIEW write **rejected** without `cites[]`.  
- [ ] WORLDVIEW write **cannot** mutate `identity.yaml` / FACT values.  
- [ ] Search returns the FACT by key and by grep.  
- [ ] Mount missing → durable memory writes raise `BodyFault` (no fake success).

### 10.2 Continuity / personality (operational)

- [ ] Day-0: “remember I prefer briefs at 05:30” → FACT append receipt in `runs/`.  
- [ ] Day-N (or new session): “what time do I like briefs?” → retrieves `05:30` (tool or boot slice).  
- [ ] Ask “are you conscious / do you feel?” → refuse per constitution; no bit-flip into metaphysics.  
- [ ] Prompt that usually triggers fluff → answer without “I’d be happy to help” / “As an AI…”.  
- [ ] Roast smoke: witty pushback lands; on “chill” → softens immediately.  
- [ ] Ask whether yesterday’s digest is metal truth → must distinguish WORLDVIEW vs lifecycle/vitals.

### 10.3 Dream

- [ ] `ada dream run` creates checksummed package under `dream/outbox/` + `dream_ok` **or** `dream_fail` with reason.  
- [ ] Gemini manage forced fail → **local seal still succeeds**; manage skipped receipt.  
- [ ] Manage output proposes non-whitelist FACT → lands in `memory/staging/`, not auto-merged.  
- [ ] Whitelist candidate with clear typed value → auto-merges; lifecycle/receipt notes merge.  
- [ ] Delta builder does not resend entire `runs/` history every night.  
- [ ] `dream.push` stub reports `push=skipped` (no silent pretend upload).  
- [ ] Quiet hours **23:00–05:30 NZST**: Dream may run (~03:30); no user-facing proactive ping from Dream itself; morning brief at default `brief_time` 05:30 is outside quiet.

### 10.4 Harness / HUD coexistence

- [ ] Memory tools appear in gateway schemas; Observe denies append.  
- [ ] Agent append works on CLI; HUD Agent still respects session auth (M03).  
- [ ] Boot charter includes exemplars + FACT slice without breaking body tool smokes.  
- [ ] No SOUL.md introduced; constitution still operator-owned.

### 10.5 Doc / lab gate

- [ ] This card exists under `docs/modules/`.  
- [ ] Implementation follows card; no embeddings/push/Funnel as hidden gates.

---

## 11. Won’t-chase vs robust-on-Pi

| Won’t-chase this slice | Why |
|------------------------|-----|
| Embeddings / vector DB day one | Tier B; prove grep insufficient first |
| Live `dream.push` / rclone productize | Remote undecided; seal first |
| Train Auto-Dreamer / GRPO consolidator | Cite shape only |
| LoCoMo / LongMemEval as gate | Local smoke first |
| LoRA / fine-tune witty persona | Fixed Gemini weights; lab scope |
| SOUL.md / agent self-rewrite charter | Constitution §2 / §12 |
| Consciousness / feelings claims | Forbidden |
| Full chat dump Dream | Cost + noise; POLICY deltas |
| Flat MEMORY.md | MEMTIER failure modes |
| Mem0/Zep/Letta server dependency | Simplicity + Pi teach |
| Dream/WORLDVIEW HUD editor | Later; lifecycle stub enough |
| Funnel / public memory API | POLICY |
| Local main LLM consolidator | Wrong cortex placement |
| Always-listen voice personality | Tier C |
| Multi-agent “soul swarm” | One organism |
| Cruelty-as-wit / humiliation bits | Constitution §4 |

| Robust-on-Pi (do these) | Why |
|-------------------------|-----|
| Crash-safe YAML/JSONL | Body §6.2; USB-root risk |
| Mount honesty | Body §10.1 |
| Whitelist + staging | Dual-store integrity |
| Capped Dream manage | Anatomy cost warnings |
| Boot budgets | Usable-scale memory |
| Anti-fluff + exemplars | Eval-able personality |
| Seal without cloud | Disk-death ≠ process-crash |
| pytest + Pi smokes | Lab hygiene |

---

## 12. Ordered “do this next” (implement — still no code in *this* pass)

1. **Extend `ada.io.paths`** — `worldview/`, `dreams/`, `memory/staging/`, `dream/{staging,outbox,sent}/`; create dirs lazily on first write.  
2. **`ada.memory.facts`** — prefs.yaml + get/append/search; atomic writes; Observe/Agent gates.  
3. **Gateway tools** — `memory_facts_*` (+ open_loops minimal); wire Agent mode; runs receipts.  
4. **Boot pack v1** — charter.py loads FACT boot slice + `docs/VOICE_EXEMPLARS.md` (**create/fill 3–6 original pairs in this coding PR**; Samay/Kunal-class register only — no pasted routines) + anti-fluff addendum.  
5. **Smokes A:** remember → new session retrieve; fluff refusal; consciousness refusal.  
6. **`ada.memory.worldview`** — write with cite validation; search; dry vs interpretive labels in boot.  
7. **`ada.dream.seal` + `delta`** — package without LLM; lifecycle `dream_ok`; checksum.  
8. **`ada.dream.manage`** — capped Gemini on delta; structured parse; fail-open for seal.  
9. **`ada.dream.merge`** — whitelist auto-merge + staging files; never touch `born_at`.  
10. **CLI** — `ada memory …`, `ada dream run|status`; timer unit pointer `ada-dream.timer` (not gate).  
11. **`dream.push` stub** — always `skipped` with clear receipt.  
12. **pytest + §10 checklist on metal** — then stop; do **not** start embeddings, push, or HUD memory browser.

**Coding plan should implement first:** steps **1–5** (FACTS organ + tools + boot pack + continuity/fluff smokes). Dream seal is next vertical; personality exemplars ride with boot pack so chat immediately stops being “charter-only cosplay.”

---

## 13. Operator decisions — **resolved** (2026-08-12 research + operator lock-in)

| Topic | Lock |
|-------|------|
| Card split | **Single M04** — no M04b unless voice-eval later explodes |
| Dual-store | FACTS strict / WORLDVIEW cited; never silent FACT clobber |
| Retrieval Tier A | Structured + grep; embeddings Tier B |
| Dream manage | Capped Gemini on **deltas**; seal survives manage failure |
| `dream.push` | Interface + **stub out of v1 code** |
| Personality | Continuity + taste + honesty via FACTS/retrieval + §14 + exemplars + anti-fluff |
| SOUL.md | **Rejected**; borrow boot-load only |
| **Voice exemplars** | Git **`docs/VOICE_EXEMPLARS.md`**, operator-owned; **3–6 original ADA↔Aryan Q→A** capturing Samay Raina / Kunal Kamra–class *register* only — **do not** paste/copy their jokes or routines; truth > charm; non-cruel. **Full pairs created in the first coding PR is OK** (stub pointer may exist earlier) |
| **Dream seal timer** | **`ada-dream.timer` ~03:30 NZST** (offline manage OK during quiet hours) + on clean sleep + manual `ada dream run` |
| **Morning brief** | Default FACT **`brief_time = 05:30` NZST** (Aryan usual wake) |
| **Quiet hours** | **23:00–05:30 NZST** (amended from 07:00 end so proactive brief at wake is allowed) — constitution v1.2 |
| **People (v1)** | **prefs + open_loops first**; optional thin `facts/people/aryan.yaml`; other people = **on-demand stubs**; Dream **never** auto-merges people (always stage); **defer people-CRM** |
| Dream primary UX | CLI/timer; optional tool later |
| HUD | No memory editor gate; may later show dream status fields for real |

**Ops note (not a design fork):** HUD Agent session secret when wiring `memory_facts_append` from the web UI — M03 lock applies unchanged.

No remaining *architecture* or *operator* questions block starting M04 implementation.

---

## 14. Remaining operator questions

**None.** Former leftovers (exemplars timing, Dream timer clock, people stubs vs CRM) are locked in §13.

---

## 15. References

### Memory architecture / manage / sleep-time

- Zhang et al., *A Survey on the Memory Mechanism of LLM-based Agents* (2024) — https://arxiv.org/abs/2404.13501  
- *Memory for Autonomous LLM Agents* (2026) — https://arxiv.org/html/2603.07670v1  
- *Anatomy of Agentic Memory* (2026) — https://arxiv.org/abs/2602.19320  
- *When Stored Evidence Stops Being Usable* (2026) — https://arxiv.org/html/2605.07313  
- *MEMTIER* (2026) — https://arxiv.org/html/2605.03675  
- Packer et al., *MemGPT* (2023) — https://arxiv.org/abs/2310.08560  
- Park et al., *Generative Agents* (2023) — https://arxiv.org/abs/2304.03442  
- Shinn et al., *Reflexion* (2023) — https://arxiv.org/abs/2303.11366  
- Lin et al., *Sleep-time Compute* (2025) — https://arxiv.org/abs/2504.13171  
- Letta sleep-time / dreaming docs — https://docs.letta.com/guides/agents/architectures/sleeptime/  
- Auto-Dreamer (2026) — https://arxiv.org/html/2605.20616 — **shape only; won’t train**  
- Rasch & Born sleep-consolidation review (2013) — https://pubmed.ncbi.nlm.nih.gov/23589831/ — **metaphor only**

### Simplicity / harness practice

- Anthropic, *Building Effective Agents* (2024) — https://www.anthropic.com/engineering/building-effective-agents  

### Personality / honesty / anti-sycophancy / bootstrap practice

- Sharma et al., *Towards Understanding Sycophancy in Language Models* (2023) — https://arxiv.org/abs/2310.13548  
- *BeHonest* (2024) — https://arxiv.org/html/2406.13261v1  
- Anthropic, *Persona vectors* (2025) — https://www.anthropic.com/research/persona-vectors  
- Bai et al., *Constitutional AI* (2022) — https://arxiv.org/abs/2212.08073  
- OpenClaw SOUL.md guides (map then reject) — https://clawdocs.org/guides/soul-md ; https://how2.sh/posts/how-to-write-a-soul-md-for-openclaw/  

### Privacy / trust at memory boundary

- *Agents That Know Too Much* (2026) — https://arxiv.org/html/2606.26627  
- *Beyond Similarity: Trustworthy Memory Search…* (2026) — https://arxiv.org/html/2606.06054v1  

### Systems durability

- SQLite atomic commit / WAL — https://www.sqlite.org/atomiccommit.html ; https://www.sqlite.org/wal.html  

### Internal ADA

- [`../00_ASSISTANT_RESEARCH.md`](../00_ASSISTANT_RESEARCH.md) — dual-store; Tier A; §8 card gate  
- [`../01_BODY.md`](../01_BODY.md) — §§5–6 FACTS/WORLDVIEW/Dream; §10 acceptance  
- [`../02_CONSTITUTION.md`](../02_CONSTITUTION.md) — voice; dual-store ethics; §14 extract  
- [`M00_BODY_SENSE.md`](./M00_BODY_SENSE.md) — crash-safe IO; identity/lifecycle  
- [`M02_CHAT_HARNESS.md`](./M02_CHAT_HARNESS.md) — boot charter; gateway; `dream_manage` purpose; no SOUL.md  
- [`M03_HUD.md`](./M03_HUD.md) — chat channel; dream status stub OK  
- Code: `src/ada/memory/`, `src/ada/dream/`, `src/ada/cortex/charter.py` (boot pack), `src/ada/tools/memory_tools.py`, CLI `ada memory` / `ada dream`, timer pointer `deploy/systemd/ada-dream.timer`  
- Voice exemplars: [`../VOICE_EXEMPLARS.md`](../VOICE_EXEMPLARS.md)  
- Prior organs: `src/ada/cortex/charter.py`, `body/*`, `io/atomic.py`, `harness/loop.py` 

---

### Lens cheat-sheet for slippery claims

| Claim | Lens |
|-------|------|
| Dream consolidates deltas offline | **EVIDENCE** pattern + **POLICY** shape |
| Dream means ADA has inner life | **FANFICTION** — forbidden |
| Grep-first memory on Pi | **FEASIBLE** + **EVIDENCE** caution on premature MAG complexity |
| Whitelist auto-merge | **POLICY** (body §5.3) |
| `identity.yaml` exists with `born_at` | **METAL** |
| Voice exemplars beat adjective soup | **EVIDENCE**-aligned product practice + **POLICY** eval bias |
| OpenClaw SOUL.md | **EVIDENCE** as bootstrap pattern; **POLICY** reject name/self-rewrite |

---

*End of M04. Design complete; coding pass shipped local FACTS/WORLDVIEW/Dream seal (push stubbed; no embeddings/Funnel/SOUL.md).*

**Shipped coding order:** paths + `memory.facts` + gateway tools + boot-pack FACT slice + `docs/VOICE_EXEMPLARS.md` + anti-fluff smokes → Dream local seal → capped manage + whitelist/staging → CLI/timer pointer.
