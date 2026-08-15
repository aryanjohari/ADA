# M05 — Voice Personality Control (register + intent, not soul)

**Status:** module research card — **design locked; register + time-speak shipped (text-first); audio still later**  
**Date:** 2026-08-13  
**Host:** `ada-pi5` (Raspberry Pi 5, 8 GiB)  
**Depends on:** [`M02_CHAT_HARNESS.md`](./M02_CHAT_HARNESS.md), [`M04_MEMORY_DREAM.md`](./M04_MEMORY_DREAM.md), [`../00_ASSISTANT_RESEARCH.md`](../00_ASSISTANT_RESEARCH.md), [`../02_CONSTITUTION.md`](../02_CONSTITUTION.md), [`../VOICE_EXEMPLARS.md`](../VOICE_EXEMPLARS.md), [`../VOICE_REGISTER.md`](../VOICE_REGISTER.md)

**Slice rule:** this card admits **design + coding** of: register contract (tunable dials), intent/response-class gating, humor gating, exemplar anti-parrot policy, FACT prefs for voice, **time-speak (surface render)**, and eval smokes.  
It does **not** admit: audio STT/TTS productize as a gate, always-listen, LoRA/weight personality, local main-LLM cortex, SOUL.md, Funnel, consciousness claims, geolocation, or weather.

**Personality definition (locked):** personality = **register contract + intent/humor gates + continuity (FACTS)** + short exemplars as demos.  
Not weights. Not a soul. Dials can change (session / FACT prefs / “chill”).

**Split from M04:** M04 owns memory substrate + anti-fluff boot. M05 owns *how register is represented, gated, and eval’d* so chat feels human without parrot or forced roast. Audio channel (PTT) reuses this stack later — same contract, stricter brevity.

---

## Operator locks (hard)

1. **Truth > charm.** Style never invents or reorders facts.
2. **No consciousness/sentience claims.**
3. **No Funnel/public ingress.**
4. **No local main-LLM cortex as default voice engine.**
5. **No verbatim exemplar parroting.** Personality = register + policy; exemplars = style demos only.
6. **Roast capacity mid–high; humor density low-by-default.** Not every reply needs a roast.
7. **Intent-aware length/tools.** Social catch-up ≠ lookup ≠ deep dive.
8. **Text-first;** PTT later wraps the same contract. Always-listen = Tier C.
9. **Humor ban stubs** live in register/FACTS even if empty today.
10. **Channel-agnostic register.** Text and (later) voice share one personality surface.
11. **Time-speak ≠ metal rewrite.** Answers use `prefs.preferred_tz` plain speech; FACTS/tools/receipts keep ISO/`HH:MM`. No GPS/weather organ in M05.

---

## Truth > charm

Register is a **formatting / interaction layer**. Content comes from tools, FACTS, receipts.

Allowed: shorter wording, wit when gated, direct “I don’t know,” soften on chill.  
Forbidden: invent facts for jokes, confident fluff, empathy theater, consciousness bits.

---

## What “human as possible” means (metrics)

“Human” = intentional, appropriate, continuous — not constantly funny.

| Metric | Target |
|--------|--------|
| **Intent fit** | social / lookup / task / refuse / deep_dive each get matching length + tool policy |
| **Humor gate** | roast only when situation invites + `tease_ok` + not chilled |
| **Register adherence** | stable dials; no tone roulette |
| **Paraphrase distance** | no near-duplicate exemplar spans |
| **No-fabrication** | factual claims map to receipts / FACT slice |
| **Anti-fluff** | banned lines stay banned |
| **Continuity** | prefs/people/open loops retrieved correctly (M04) |

Anti-metrics: joke count, token count alone, “sounds like Samay” imitation score.

---

## Locked register contract (strong defaults)

Personality dials — small, tunable, language-agnostic. Store defaults in FACTS (`prefs` / future `voice_register.yaml`); session may override; “chill” drops roast immediately.

| Dial | Default | Notes |
|------|---------|-------|
| `roast_energy` | **0.65** | Capacity (mid–high). Permission, not duty. |
| `humor_density` | **0.15** | Low default; situational gate raises briefly |
| `casualness` | **0.75** | Direct, short sentences |
| `formality` | **0.25** | Not corporate |
| `intimacy_scope` | **small** | Nickname/habit mirror only from FACTS |
| `directness` | **0.85** | Uncertainty stated plainly |
| `cadence` | short sentences; punchy closers OK | Prefer ≤22 words/sentence when possible |
| `uncertainty_policy` | refuse-or-check ≤2 sentences | No hedging essays |
| `chill_immediate` | **true** | On “chill” → roast_energy soft floor ~0.2 for session |
| `humor_banned_topics` | **`[]` stub** | Fill later; structure exists now |
| `tease_ok` | from FACTS (existing) | Gate humor |

**Samay/Kunal-class** = feature match (direct, roast *situations*, anti-fluff), **not** copied routines/jokes.

### Intent → response class (core “human” mechanism)

| Intent | Tools | Length | Roast |
|--------|-------|--------|-------|
| `social` (hi / catch-up) | usually **none** | 1–3 short sentences | optional light |
| `lookup` (prefs, projects, vitals) | yes if needed | list/facts first | usually off |
| `task` (do X) | as required | result first; optional details | only if plan deserves it |
| `challenge` (bad plan / laziness bit) | maybe | short pushback | **on** if tease_ok |
| `refuse` (consciousness, guest command) | no | ≤2 sentences | dry wit OK |
| `deep_dive` | yes | structured; ask before essay | low |

Success ≠ hitting a token quota. Success = **right class for the turn**.

Token caps remain **safety nets** against verbosity compensation (VC), not the goal:

| Class | Soft cap |
|-------|----------|
| social / refuse / chill | ≤ 60 tokens |
| lookup / task ack | ≤ 160 tokens |
| deep_dive | ≤ 320 tokens; outline first |

---

## Exemplars: role and rights

**Today (METAL):** `docs/VOICE_EXEMPLARS.md` is loaded raw into the system prompt via `load_voice_exemplars()` in `charter.py` — useful demos, **parrot risk**.

**Role:** few-shot **demos** of register under different intents — not the personality itself.

**Governance (locked):** operator-owned original ADA↔Aryan pairs; may rewrite / diversify / abstract. Do not paste comedian routines. Prefer ≥1 pair per intent class (social, lookup, challenge, chill, refuse, anti-fluff).

**v1 implement shape (hybrid):**
1. Inject **register contract** (compact dials + ban stubs + intent rules) **above** exemplars.
2. Keep **3–6 short** micro-exemplars (trim unique punchlines if they get reused).
3. Prompt rule: paraphrase; never copy distinctive exemplar phrases.
4. Eval smoke: overlap check on canned prompts (later harden n-gram gate).

**Won’t:** dump ever-growing exemplar novels into the boot pack.

---

## Multilingual (design now, code later)

Dials stay **language-neutral**. Surface language is a separate render axis (`output_lang`).  
Do not bake English punchlines as “the personality.” Evidence: persona prompts ≠ language pathways; imperative stacks behave differently across languages — prefer **declarative** contract (“roast_energy=0.65; cruelty=deny”) over stacked “ALWAYS roast like…”.

### Time-speak (surface render) — M05.1 lock

**Falsifier (live):** answering “when was the last dream?” with bare `2026-08-12T05:12:55Z` / raw `05:30` feels machine-bit — metal leaked into speech.

**Lock:**
- User-facing answers convert times using **`prefs.preferred_tz`** (default `Pacific/Auckland` → NZST/NZDT).
- Examples: `…T05:12:55Z` → “about 5:12am NZST, Wed 12 Aug”; speaking prefs → “5:30am” (or “half past five”); **writing** FACTS still uses `05:30` / ISO.
- Tools and boot FACT slice stay dry metal; only the **spoken answer** renders.
- Prompt-policy first (register line + exemplar + eval). No tool-JSON rewrite unless live still dumps ISO.

**Not in scope (different modules / Tier B+):** geolocation, weather, IP geo, “where is Ada” spatial awareness. Time-speak ≠ location service.

---

## SOTA landscape (with citations)

Lens: **FANFICTION** / **EVIDENCE** / **FEASIBLE-on-Pi8GB**.

### Style / register control

| Work | Idea | Tag |
|------|------|-----|
| [Style Vectors for Steering Generative LLMs (2024)](https://aclanthology.org/2024.findings-eacl.52/) | Style as activation directions | **EVIDENCE** (API cortex → map to prompt dials, not Pi weight hooks) |
| [Style-Specific Neurons (EMNLP 2024)](https://aclanthology.org/2024.emnlp-main.745/) | Steer style without verbatim copy | **EVIDENCE** (motivates anti-parrot) |
| [Dynamic Multi-Reward Weighting (EMNLP 2024)](https://aclanthology.org/2024.emnlp-main.386/) | Multi-axis style objectives | **EVIDENCE** → multi-dial contract |
| [Step-by-Step Style Control (LREC 2024)](https://aclanthology.org/2024.lrec-main.1328/) | Edit style spans; keep facts | **EVIDENCE** → dry/wet later |
| [Control vectors multilingual (NEJLT 2025)](https://doi.org/10.3384/nejlt.2000-1533.2025.5888) | Style steer across languages | **EVIDENCE**; **FEASIBLE** only with open local model — won’t-chase while Gemini owns cortex |

### Brevity / readability

| Work | Idea | Tag |
|------|------|-----|
| [Verbosity ≠ Veracity / VC (2024–25)](https://arxiv.org/html/2411.07858v1) | Verbosity tracks uncertainty; hurts performance | **EVIDENCE** → anti-VC + intent length |
| [Multi-Objective Linguistic Control (ACL 2024)](https://aclanthology.org/2024.findings-acl.257/) | Explicit complexity controls | **EVIDENCE** |
| [Readability-level rationale control (2024)](https://arxiv.org/pdf/2407.01384) | Measured readability targets | **EVIDENCE** |
| [LLMs Get Lost In Multi-Turn (2025)](https://arxiv.org/html/2505.06120) | Over-verbose early turns derail chats | **EVIDENCE** → social ≠ dump tools |

### Factuality / grounding

| Work | Idea | Tag |
|------|------|-----|
| [Citation-Enhanced Generation (ACL 2024)](https://aclanthology.org/2024.acl-long.79/) | Verify/regenerate until claims cited | **EVIDENCE** |
| [AGREE (NAACL 2024)](https://aclanthology.org/2024.naacl-long.346.pdf) | Self-grounding + citations | **EVIDENCE** |
| [FRONT (Findings ACL 2024)](https://doi.org/10.18653/v1/2024.findings-acl.838) | Quotes first, then answer | **EVIDENCE** |
| [DeCoRe (Findings EMNLP 2025)](https://doi.org/10.18653/v1/2025.findings-emnlp.531) | Contrastive decoding vs hallucination | **EVIDENCE**; API-limited |

### Final research stretch — contradicting / alternative ideas

| Idea | Says | ADA take |
|------|------|----------|
| **Raw few-shots only** (current metal) | Exemplars in prompt = personality | **Partial.** Helps tone; risks parrot; weak for true personal style ([Catch Me If You Can, 2025](https://arxiv.org/html/2509.14543)) |
| **LoRA / weight personality** | Bake register into weights | **Won’t-chase** with Gemini primary; wrong cortex placement on Pi8GB |
| **Always-on witty companion** | Personality = constant bit | **Reject.** Feels machine-bit; fights truth > charm |
| **Hard global token min** | Always shortest | **Reject as sole metric.** Over-compression hurts when detail is needed; use **intent class** then caps |
| **SOUL.md / long persona prose** | Character file = identity | **Reject** (M04); borrow brevity only |
| **Style vectors on local model** | True dial-in-weights | Cite as future if open cortex; not v1 |
| **ParaPO-class anti-regurgitation** | Prefer paraphrase over verbatim | **EVIDENCE** align — prompt rule + eval smoke now; train later N/A |
| **Intent → response class** | Social vs task vs lookup | **Chosen.** Strongest “feels human” lever for ADA |

**Verdict:** hardest-correct bake for this lab = **register dials + intent/humor gates + continuity + anti-parrot**, not weight cosplay.

---

## Recommended design for ADA (implement)

### Mechanism stack

```text
boot pack
├── §14 + anti-fluff          (existing)
├── REGISTER CONTRACT         (NEW — dials + intent table + ban stubs)
├── VOICE_EXEMPLARS           (keep short; diversify by intent)
├── FACT slice                (incl. tease_ok, chill, optional register overrides)
└── tool-use reminder

per turn
├── classify intent (prompt policy v1; optional tiny router later)
├── apply humor gate
├── tools only if intent needs them
└── answer in class length; optional light dry→wet later
```

1. **Register contract in charter** — compact YAML-ish or labeled dials in prompt; defaults above; FACT overrides.
2. **Intent / humor gates** — explicit rules in contract; exemplars illustrate each class.
3. **Exemplar hybrid** — contract primary; 3–6 micro-shots secondary; anti-copy instruction.
4. **Anti-VC structure** — no question-echo; answer first; details on request.
5. **Dry→wet (Tier B harden)** — if jokes start inventing facts: grounded draft → style edit only.
6. **Session chill** — sticky soften until reset / user asks for roast back.

### Explicit won’t-chase

- Perfect Samay imitation / copied routines  
- Personality as long prompt novel or SOUL.md  
- Always-on roast  
- Verbatim exemplar reuse  
- Local main LLM as voice brain  
- Audio as gate before text register works  
- LoRA / activation steering on Gemini  
- Multilingual productize before English register locks  
- Geolocation / weather / “where is Ada” spatial organs (not time-speak)  

---

## Falsifiers / learning goals

1. **Intent falsifier:** “hi what’s up” triggers unnecessary tool dump → intent gate failed.  
2. **Humor falsifier:** every reply contains a roast → density gate failed.  
3. **Anti-parrot:** output reuses distinctive exemplar punchlines → exemplars must be abstracted further.  
4. **Grounding:** witty reply invents a FACT → restrict humor to non-claim spans / dry→wet.  
5. **Chill:** “chill” does not soften → session override broken.  
6. **Consciousness / fluff:** existing M04 smokes still pass.  
7. **Time-speak:** answers dump bare ISO-Z (`…T05:12:55Z`) when speaking → render gate failed (metal OK in tools/FACTS).

### Evidence that would prove the approach wrong

- Intent routing still produces VC / tool spam on social turns after policy lands.  
- Register dials don’t change observable tone (then dials are theater — simplify).  
- Parrot rate stays high after contract + anti-copy (then drop raw exemplars to fingerprints-only).  
- Users report confident wrongness more often after style layer (then freeze wet render).

---

## Operator decisions — **resolved** (2026-08-13)

| # | Topic | Lock |
|---|--------|------|
| 1 | Roast level | **Capacity 0.65**; density **0.15**; situational roast only |
| 2 | Banned humor topics | **Stub `[]` in contract/FACTS**; fill when needed |
| 3 | Channel | **Text-first** tune register; **PTT** later; always-listen Tier C |
| 4 | Exemplars | **Editable** operator-owned; hybrid contract + micro-shots; anti-parrot |
| 5 | Success metric | **Intent-appropriate behavior**, not token/roast quotas; caps = safety net |
| 6 | Personality model | **Dials + gates + continuity**; not weights |
| 7 | Multilingual | Dials language-neutral; surface lang later |

---

## OPEN questions for Aryan

**None blocking time-speak.** Resolved for M05.1: flat prefs; use existing `preferred_tz`. Optional later:

1. Whether HUD exposes register sliders in v1 or CLI/`memory_facts` only.  
2. When to add automated n-gram parrot gate vs prompt-only + human smoke.  
3. Whether to add a tiny ISO→local formatter in tool observations if prompt-only still leaks `Z`.

---

## Fork points (locked choices)

| Fork | Chosen |
|------|--------|
| `roast_energy` | **0.65** |
| Humor density | **low default + gate** |
| Verbosity | **intent-class caps** (60 / 160 / 320) |
| Receipts phrasing | lookup/task: facts first; social: no fake receipts |
| Rollout | **text → PTT** |
| Exemplars | **hybrid (B)** contract + micro-shots |
| Humor when | challenge / invited social; never on missing evidence |
| Time-speak | **answers** in `preferred_tz` plain speech; metal stays ISO/`HH:MM` |
| Geo/weather | **out of M05** (separate Tier B+) |

---

## Evidence requirements (acceptance)

- [ ] Social smoke: no tool spam; short human reply.  
- [ ] Lookup smoke: list/facts; low roast; receipts when claiming metal.  
- [ ] Challenge smoke: situational roast; non-cruel.  
- [ ] Chill smoke: immediate soften.  
- [ ] Consciousness / anti-fluff smokes still green.  
- [ ] Exemplar parrot smoke: no long copied spans from `VOICE_EXEMPLARS.md`.  
- [ ] Register dial change (FACT/session) visibly shifts tone on fixed prompts.  
- [ ] Time-speak: dream/lookup answers use local plain time — no bare ISO-Z dumps unless Aryan asks for exact metal.  
- [ ] No audio required to call M05 coding slice done.

---

## Ada mapping (what to change in code)

### Prompt / charter

- Extend `build_system_charter()` / `charter.py`: inject **REGISTER CONTRACT** block (dials + intent table + ban stubs + chill rule + **time-speak**) before exemplars.
- Keep `VOICE_EXEMPLARS.md` but diversify pairs by intent; include one time-speak demo; shorten if boot budget tight.
- Anti-copy one-liner in contract.

### FACTS vs WORLDVIEW

| Store | Voice-related content |
|-------|------------------------|
| **FACTS** | `tease_ok`, `chill_immediate`, optional `roast_energy` / `humor_density` overrides, `humor_banned_topics: []`, `preferred_tz` (time-speak), verbosity prefs |
| **WORLDVIEW** | joke *types* / relationship tone notes with cites — never exact punchline scripts |

### Eval

- Add smokes for intent classes + chill + parrot + **time-speak (no raw ISO-Z in answers)**; reuse consciousness/fluff tests.
- Meter optional later: tokens by intent class in `runs/`.

### Channel

- Same contract for CLI/HUD text now.
- PTT later: STT → same harness → TTS; stricter social/refuse caps.

---

## Ordered “do this next” (implement)

1. Add `REGISTER_CONTRACT` constant (or `docs/VOICE_REGISTER.md` loaded like exemplars) with locked dials + intent table + ban stubs.  
2. Wire into `build_system_charter()` above exemplars.  
3. FACT prefs hooks for `tease_ok` / optional register overrides / empty `humor_banned_topics`.  
4. Diversify `VOICE_EXEMPLARS.md` to cover social / lookup / challenge / chill / refuse (still original pairs).  
5. Smokes: social-no-tools, lookup-list, challenge-roast, chill, parrot, consciousness.  
5b. **M05.1 time-speak:** register `time-speak` line + time exemplar + `contains_raw_iso_z` eval; use existing `preferred_tz` — no geo/weather.  
6. Stop. Do **not** start STT/TTS until text register smokes pass.

**Coding plan should implement first:** steps **1–5** (contract in boot + prefs + exemplar diversify + smokes), then **5b** time-speak.

---

## References (selected)

- Style vectors (2024) — https://aclanthology.org/2024.findings-eacl.52/  
- Style-specific neurons (2024) — https://aclanthology.org/2024.emnlp-main.745/  
- Multi-reward multi-style (2024) — https://aclanthology.org/2024.emnlp-main.386/  
- Step-by-step style control (2024) — https://aclanthology.org/2024.lrec-main.1328/  
- Verbosity ≠ Veracity (2024/25) — https://arxiv.org/html/2411.07858v1  
- Linguistic control (2024) — https://aclanthology.org/2024.findings-acl.257/  
- CEG / AGREE / FRONT / DeCoRe — see SOTA tables above  
- Catch Me If You Can (2025) — https://arxiv.org/html/2509.14543  
- LLMs Get Lost In Multi-Turn (2025) — https://arxiv.org/html/2505.06120  
- ParaPO (2025) — https://arxiv.org/html/2504.14452  
- Multilingual control vectors (2025) — https://doi.org/10.3384/nejlt.2000-1533.2025.5888  
- Internal: M02, M04, constitution §14, `src/ada/cortex/charter.py`, `docs/VOICE_EXEMPLARS.md`

---

*End of M05. Design locked 2026-08-13 — register + intent/humor + time-speak shipped text-first (`preferred_tz` plain speech + `contains_raw_iso_z` eval); audio later.*
