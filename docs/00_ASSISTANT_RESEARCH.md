# ADA — Assistant Research & Design Notes

**Status:** living research notes (v1.1 finalization; decisions feed body + constitution)  
**Date:** 2026-08-12 (finalization patch; prior lock-in 2026-08-11)  
**Machine:** `ada-pi5` (Raspberry Pi 5 Model B Rev 1.1)  
**Branch:** `rewrite/v1-body`  
**North star:** personal always-on assistant in the spirit of Jarvis (Iron Man) / Justine (Why Him) — conversational, situationally aware, proactive under control, useful in daily life. **Not** movie AGI. **Not** claiming consciousness.  
**Depends on / feeds:** [`01_BODY.md`](./01_BODY.md), [`02_CONSTITUTION.md`](./02_CONSTITUTION.md)

### Project intent (lab framing)

ADA on this branch is a **personal lab + daily-use companion + PhD-prep learning surface** — **not** a product to ship. Prefer **harder-but-correct** setups when they teach (typed tools, crash-safe stores, permission gateways, dual-store memory, explicit egress). Before each major capability slice: a **module research card** (§8). Portfolio/factory code stays on `main`.

This document separates three lenses wherever claims get slippery:

| Lens | Meaning |
|------|---------|
| **FANFICTION** | Narrative desire from fiction / UI vibe. Useful as product taste, not an engineering roadmap. |
| **EVIDENCE-BACKED** | Supported by papers, surveys, product patterns, or measured community benchmarks. |
| **FEASIBLE ON PI5 8GB** | Realistic on *this* body as inspected today, given RAM/CPU/IO and blank-slate software. |

Aligned soft constraints from `VISION.md`: LLM as cortex/orchestrator (not the whole organism); no custom distro; prefer evidence from papers + this hardware.

### Cloud trust rings (not “everything stays on the Pi”)

Three distinct trust boundaries — do not collapse them into “private”:

| Ring | What | Counterparty |
|------|------|--------------|
| **Control plane** | HUD / chat ingress | Tailscale (Aryan devices / session auth) |
| **Cortex egress** | Chat turns, tool schemas, retrieved slices for the turn; light Dream manage-pass deltas | Gemini API (primary); future adapters |
| **Backup egress** | Sealed Dream packages | Configured S3-compatible remote (`dream.push`) |

**“No exfil”** means **no unallowlisted egress** — not “Google never sees a word.” Hybrid cortex is deliberate for quality. Future lab path (not Tier A gate): PII redact / quiet local small-model filtering before cloud calls ([MemPrivacy](https://arxiv.org/html/2605.09530v3)-class ideas; research later). Secrets/API keys are never-to-cloud.

### Smoke eval (shared pointer)

Operational falsifiers live in [`01_BODY.md` §10](./01_BODY.md) (body acceptance). Runtime harness organ (when coded): `eval.smoke`. Academic LoCoMo / LongMemEval are **won’t-chase as v1 gates** (§5); use them only as optional graded homework.

---

## 0. The real body (readonly inspection, 2026-08-11)

### Identity & OS
| Fact | Value |
|------|--------|
| Hostname | `ada-pi5` |
| Board | Raspberry Pi 5 Model B Rev 1.1 (`Revision d04171`) |
| Arch | `aarch64` (arm64), 64-bit userspace |
| CPU | 4× ARM Cortex-A76, max 2400 MHz, min 1500 MHz |
| OS | Debian GNU/Linux 13 (trixie), kernel `6.18.39+rpt-rpi-2712` |
| Time | `Pacific/Auckland` (NZST), NTP synchronized, hardware RTC present |

### Memory & thermal
| Fact | Value |
|------|--------|
| RAM | ~7.9 GiB total; ~7.1 GiB available at idle (~830 MiB used) |
| Swap | 2.0 GiB zram (unused at inspect time) |
| Temp | 45.0°C idle; `throttled=0x0` (no thermal/under-voltage flags) |
| Firmware split | `arm=1020M`, `gpu=4M` (headless-leaning) |

### Storage topology
| Device | Role | Size / free | Notes |
|--------|------|-------------|-------|
| `sdb` SanDisk Cruzer Blade USB | boot + root (`bootfs` + `rootfs`) | ~28G root, ~22G free | OS on USB stick (risk accepted; see body) |
| `sda` Seagate Expansion HDD | labeled `ada-data` → `/mnt/ada-data` | ~916G, ~870G free (~empty) | Primary durable substrate |
| Layout under `/mnt/ada-data` | `ADA/`, `memory/`, `runs/`, `dream/` (planned), `scratch/` | durable substrate | See `01_BODY.md`; constitution in `02_CONSTITUTION.md` |

### Network & periphery
| Fact | Value |
|------|--------|
| `wlan0` | UP — `192.168.7.133/22` (+ IPv6) |
| `eth0` | DOWN |
| USB | Seagate HDD + SanDisk stick (no mic/camera observed at inspect) |
| Toolchain present | Python 3.13.5; no Node/Docker/Ollama observed |

**Body verdict:** capable always-on edge host with abundant HDD for memory/logs/models, but **tight interactive RAM budget** once any local LLM + STT/TTS + agent runtime share the box. Cortex should assume **cloud/API models for quality+latency**, with local models as optional offline/ancillary — matching VISION (“LLM is cortex/orchestrator, not the whole organism”).

---

## 1. Iconic assistant traits (Jarvis / Justine → abstract capabilities)

Fiction is useful once abstracted into *capabilities humans recognize*, not into claims of sentience.

### FANFICTION (source material vibes)
- Instant spoken presence; anticipates needs before asked.
- Omniscient of home/lab/status; seamless control of environment and schedule.
- Personality that feels like a trusted companion (wit, loyalty, situational warmth).
- Continuous “always listening / always watching” awareness.

### Abstract capabilities people actually want
Mapped from those vibes to things a real personal assistant must do:

| Fiction cue | Abstract capability | Why it matters |
|-------------|---------------------|----------------|
| “Knows me” | **Durable personal memory** (prefs, projects, people, decisions) | Continuity across days; personalization without re-briefing |
| “Status report” | **Truthful self-report** of system + task state | Trust; reduces hallucinated progress |
| “Run diagnostics / fix it” | **Tool use + actuator permissions** | Results in the world beat eloquent prose |
| “Suggesting before asked” | **Bounded proactivity** (propose → confirm for risk) | Feels attentive without becoming creepy or costly |
| Voice banter | **Low-friction channel** (text now; voice later) | Channel ≠ intelligence; latency dominates feel |
| Situational awareness | **Body + calendar + context sensors** | Grounding; less generic chatbot energy |
| Loyalty / discretion | **Auth, isolation, audit logs** | Personal agent without open internet = liability |

### Product / literature echoes (EVIDENCE-BACKED)
- **Memory across sessions** is a differentiating factor for agents; single context windows fail for multi-day personal assistants — surveys of agent memory ([Zhang et al. 2024 survey](https://arxiv.org/abs/2404.13501); newer surveys through 2026: [Memory for Autonomous LLM Agents](https://arxiv.org/abs/2603.07670), [Anatomy of Agentic Memory](https://arxiv.org/html/2602.19320)).
- **Interleaved reason + act** (ReAct) materially reduces hallucination vs pure CoT when tools can ground claims ([Yao et al. 2022](https://arxiv.org/abs/2210.03629)).
- **Hybrid LLM + tools**: models should offload arithmetic, search, calendars, code execution — Toolformer showed smaller models + APIs beating larger tool-less models ([Schick et al. 2023](https://arxiv.org/abs/2302.04761)).
- **Long-horizon reliability gap**: strong single-step reasoning ≠ durable multi-hour task completion; planning/memory/execution failures dominate as horizon grows ([Horizon Gap survey](https://arxiv.org/html/2608.06663); [Long-Horizon Task Mirage](https://arxiv.org/html/2604.11978v1)).
- **Reflective / episodic memory streams** (generative agents, Park et al. 2023) popularized retrieve → reflect → plan loops; useful pattern, not evidence of consciousness.
- **Offline consolidation as a second timescale** (fast online write / slow manage) — [Auto-Dreamer, 2026](https://arxiv.org/html/2605.20616) strengthens the Dream *shape* (cite as lineage; training the consolidator is won’t-chase).
- **Agent privacy is data-path shaped** — personal assistants are intimate + high-permission ([Agents That Know Too Much, 2026](https://arxiv.org/html/2606.26627)); confirm dialogs must bind to real tool args ([Consent Integrity, 2026](https://arxiv.org/html/2606.02668v1)).

### FEASIBLE ON PI5 8GB (capability realism)
| Capability | Feasible now? | Note |
|------------|---------------|------|
| Text chat loop + tools | Yes | Cloud cortex + local tools |
| Persistent file/DB memory on HDD | Yes | `/mnt/ada-data/memory` already provisioned |
| Body sense (host metrics, mount health) | Yes | Cheap, high trust signal |
| Always-on scheduler / reminders | Yes | systemd timers + agent inbox |
| Full local “Jarvis brain” LLM | No (as *main* cortex) | ~3–6 tok/s for 3–4B Q4; poor agentic tool quality vs API models |
| Always-listening room mics | Deferred | Privacy + no mic observed; also CPU contention |
| Home omniscience / camera fusion | Tier C | Needs sensors + NPU/HAT or offboard compute |

---

## 2. What “effective” means operationally

Film assistants feel effective because they **close loops**. For ADA, effectiveness must be measurable — not “sounds like Jarvis.”

### Success metrics (operational)

1. **Truthful self-report**
   - Claims about body (“disk full?”, “agent running?”, “last backup?”) match sensors.
   - Claims about tasks (“I emailed X”, “reminder set”) match tool receipts / audit log.
   - Explicit **unknown / failed** when tools fail — no invented success.

2. **Task completion (short horizon)**
   - Single-turn or ≤N-step tool tasks succeed at a tracked rate (e.g. reminder created, status summarized, note filed).
   - Prefer graded outcomes: `done` / `needs_confirm` / `blocked` / `failed`.

3. **Latency / snappiness**
   - Text ack < ~1–2s perceived (even if final answer streams later).
   - Interactive tool turns usable on LAN/WAN; avoid multi-minute silent hangs.
   - Voice E2E (if added): community Pi5 local stacks report ~8–25s round-trip offline — treat as **novelty/offline**, not primary UX ([Pi5 voice writeups 2026](https://bmdpat.com/blog/raspberry-pi-5-local-voice-ai-2026)).

4. **Safety & control**
   - Permission ladders: read-only by default → confirm for external/side-effecting → hard deny for high risk.
   - Auth: Tailscale ACL to Aryan devices + session auth for Agent writes (see constitution).
   - Human can stop / mute proactivity quickly (“quiet hours”, kill switch).
   - Overnight: **heal first** (retry + cleanup); wake Aryan only if recovery fails or critical body faults listed in body/constitution.

5. **Memory usefulness (not just storage)**
   - Retrieve correct **FACT** days later; WORLDVIEW digests must cite facts and never overwrite them (dual-store — body §5).
   - Local smoke questions (LoCoMo / LongMemEval-*style*, not academic chase).
   - Write policy: what gets stored, summarized, forgotten (GDPR-ish hygiene without ceremony).

6. **Proactivity quality**
   - Precision over recall: fewer high-value nudges beat constant chatter.
   - Every proactive act should be attributable: trigger rule + evidence + permission tier.

7. **Cloud honesty (lab)**
   - When cortex/Dream/HUD land: meter tokens and egress class in logs/HUD — **promise only now; no fake numbers.**

### Anti-metrics (do not optimize)
- Word count / theatrical personality density.
- Number of autonomous background agents.
- Tokens burned on voice-of-AGI roleplay.
- SEO / content-factory throughput (explicit non-goal).
- Leaderboard chasing before local smoke falsifiers exist.

---

## 3. Architecture patterns that work in 2025–26 agent literature

Patterns below are widely reused in research *and* production agent harnesses. Prefer them over invention.

### 3.1 Agent loop: observe → reason → act → observe
**EVIDENCE-BACKED:** ReAct (Yao et al., 2022) — interleave thoughts with tools so each next step conditions on real observations; lowers hallucinated chaining vs chain-of-thought alone.

**ADA implication:** every “I did X” path goes through a tool that returns a receipt into the transcript.

### 3.2 Hybrid cortex + tools (not all-in-weights)
**EVIDENCE-BACKED:** Toolformer (Schick et al., 2023); modern function-calling APIs (OpenAI/Anthropic/etc.). Strengths of LLMs (language, planning sketches) + strengths of programs (time, files, HTTP, DB).

**ADA implication:** Pi owns deterministic organs (clock, FS, process mgr, home APIs); LLM proposes tool calls with schemas + permissions. Confirm UI must show **gateway-rendered real args**, not model narration ([Consent Integrity, 2026](https://arxiv.org/html/2606.02668v1)).

### 3.3 Memory tiers (write–manage–read) + dual-store
**EVIDENCE-BACKED:** agent memory surveys converge on hierarchical stores rather than stuffing the context window forever ([Zhang 2024](https://arxiv.org/abs/2404.13501); [2026 memory surveys](https://arxiv.org/html/2603.07670v1); MemGPT-style paging [Packer et al. 2023/24](https://arxiv.org/abs/2310.08560); offline region consolidation [Auto-Dreamer, 2026](https://arxiv.org/html/2605.20616)).

Pragmatic tiers for ADA:

| Tier | Contents | Substrate on this Pi |
|------|----------|----------------------|
| Working | current turn, tool obs, short scratch | RAM / session transcript |
| Episodic | dated events, runs, conversations | `/mnt/ada-data/runs`, append-only logs |
| Semantic **FACTS** | durable prefs, people stubs, identity — strict | `/mnt/ada-data/memory/facts/` (structured) |
| Semantic **WORLDVIEW** | digests, takes, consolidations that *cite* facts | `/mnt/ada-data/memory/worldview/` (Dream + awake synthesis) |
| Procedural | skills, playbooks, tool schemas | git-tracked code + skill docs |
| Cold archive | raw dumps, old sessions | HDD; retrieve rarely |

**POLICY:** WORLDVIEW never silently overwrites FACTS. Dream auto-merge only hits an explicit **whitelist** of FACT keys (body §5 / constitution).

**Caution (EVIDENCE-BACKED):** memory systems often underperform their promise when evaluation is weak, retrieval is naive, or maintenance latency is ignored ([Anatomy of Agentic Memory](https://arxiv.org/html/2602.19320)). Start simple: structured notes + timestamps + grep/BM25/embeddings later. Usability can collapse as irrelevant sessions grow ([scale-conditioned memory eval, 2026](https://arxiv.org/html/2605.07313)).

### 3.4 Horizon management (the “horizon gap”)
**EVIDENCE-BACKED:** as task length grows, failures shift toward planning early mistakes, forgetting constraints, and false completion ([Horizon Gap](https://arxiv.org/html/2608.06663); [Long-Horizon Mirage](https://arxiv.org/html/2604.11978v1)). Stepwise “reason harder” is not planning ([Why Reasoning Fails to Plan](https://arxiv.org/abs/2601.22311)).

**ADA implication:**
- Cap autonomy horizon early (checklists, stages, human confirm at stage gates).
- Persist goals/state outside the model context.
- Prefer small vertical slices over “multi-day unsupervised missions.”

### 3.5 Permissions, audit, and human-in-the-loop
**EVIDENCE-BACKED / product pattern:** production agents that email, spend money, or mutate systems use confirmations, sandboxes, and audit trails. Programmable least-privilege tool policies ([Progent, 2025](https://arxiv.org/pdf/2504.11703)) and deny-default gateways fit the lab better than vibe prompts.

**ADA implication:** tool capability ≠ tool authority. Schema includes side-effect class.

### 3.6 Local edge constraints
**FEASIBLE ON PI5 8GB:**
- Quantized ≤~3–4B models: often ~3–7 tok/s decode on Pi5; usable for offline stubs, not snappy multi-tool agents ([community llama.cpp benches 2025–26](https://specpicks.com/reviews/raspberry-pi-5-local-llm-2026)).
- 7–8B Q4 on 8GB: tight/swappy once OS + KV + STT coexist — poor interactive agent host.
- HDD space is not the bottleneck; **RAM + latency + CPU contention** are.
- Prefer: **API cortex** + local organs; optional tiny local model for privacy-sensitive classification / fallback (future research path).

### 3.7 Interaction channel
Voice is a *channel*, not a brain. Text-first preserves auditability and fits current hardware (no mic observed).

**Voice tiers (locked):**
| Tier | Voice |
|------|--------|
| **A** | None (text Tailscale HUD/chat) |
| **B** | Push-to-talk |
| **C** | Always-listen + voice-ID |

---

## 4. Mapped to THIS Pi: Tier A / B / C

### Tier A — now (blank slate → lovable loop on this body)
Ship what this machine already enables without extra silicon (**locks as of body + constitution v1.1**):

- **Body sense organs:** uptime, load, temp/throttle, disk free on `/` and `/mnt/ada-data`, network presence, process heartbeat.
- **Agent runtime skeleton:** one supervised service; session log under `/mnt/ada-data/runs`; dual-store memory under `/mnt/ada-data/memory`; Dream seal under `/mnt/ada-data/dream`.
- **Cortex:** **Gemini** primary with tool calling; cortex adapter for Claude later — not on-device main brain.
- **Tools (read-heavy + memory):** `body.vitals`, FACT append/search, lifecycle; privileged `dream.push` only to allowlisted backup remote after **one-time** operator confirm.
- **Channel:** **Tailscale-only web HUD + chat**; ACL Aryan devices; session auth for Agent writes. No public agent ingress.
- **Proactivity v0:** **warmly forward** briefs/nudges, attributable; quiet hours **23:00–07:00 NZST** with **heal-first** overnight faults; never silent unallowlisted external side effects.
- **Safety:** secrets outside git; deny open anonymous control; never-to-cloud secret class.

### Tier B — next (software + peripherals, still Pi5)
- Richer memory retrieval (embeddings on Pi or API embeddings + local index on HDD).
- More actuators: email draft→confirm send, Home Assistant / smart home, browser-fetch with allowlists.
- Push-to-talk voice (USB mic + cloud or Whisper-tiny + Piper) if desired.
- Multi-step workflows with persisted checklists and stage-gate confirms (attacks horizon gap without claiming AGI autonomy).
- Optional small local LLM for offline mode / intent routing / **future PII redact research** — **ancillary**, not primary cortex.
- Token/egress metering in HUD.

### Tier C — needs more hardware (or offboard compute)
- Always-listening multi-room audio, camera fusion, on-device vision at interactive FPS; voice-ID.
- Comfortable concurrent local 7B+ agent + STT + embeddings without swap drama → prefer **16GB Pi**, NPU/AI HAT, or a nearby mini-PC as organ cluster.
- Heavy browser automation / long coding agents with desktop GUIs.
- Anything requiring GPU-class local generation for “movie latency.”

---

## 5. Explicit non-goals & won’t chase (lab)

Do **not** prioritize in rewrite/v1-body:

1. **Custom Linux distro / from-scratch OS** — Debian/Pi OS host is fine (`VISION.md`).
2. **Full local LLM as main brain for speed/feel** — Pi5 8GB can demo local chat; it cannot credibly replace API-class agentic cortex for the north-star UX.
3. **Open internet without auth** — no public unauthenticated agent endpoint. (Allowlisted `dream.push` to a configured object store is a privileged exception, not “open internet.”)
4. **SEO factory / content mill resurrection** — portfolio/factory stays on `main`; this rewrite is personal assistant, not content ops.
5. **Consciousness claims / AGI cosplay** — personality yes; metaphysical identity no.
6. **Unbounded autonomy** — no multi-day unsupervised missions before short-horizon evals exist.
7. **Force-rewriting `main`** — branch discipline remains.

### Won’t chase (lab) — cite, don’t build as v1 gate

| Topic | Stance | Why |
|-------|--------|-----|
| Train Auto-Dreamer / GRPO consolidator | Won’t chase | Separate research project; Dream *shape* already justified |
| LoCoMo / LongMemEval as Tier A gate | Won’t chase | Local smoke first (`eval.smoke` + body §10) |
| Always-listen + voice-ID | Tier C only | No mic; privacy + CPU |
| Local LLM as main cortex | Won’t chase | Wrong for snappy multi-tool on 8GB |
| Full MemPrivacy-class edge model in Tier A | Research later | Hybrid Gemini accepted; redact is future harden |
| Custom distro / ZFS-before-loop | Won’t chase | VISION + body non-goals |
| Multi-agent swarm productization | Won’t chase | Lab + companion, not product |

---

## 6. Recommended first vertical slice AFTER body sense

**Smallest lovable loop:** *truthful body companion with one durable FACT write and one proactive brief — over Tailscale web UI.*

### Sequence (design intent; not implemented here)
1. **Body sense:** answer “how are you / how is the body?” from real sensors with receipts.
2. **Chat turn + tool loop (Gemini):** user → cortex → tools → observation → answer; transcript in `/mnt/ada-data/runs/...`.
3. **Memory write/read:** “remember that I prefer NZST briefs at 07:30” → FACT store → later retrieve.
4. **Warmly forward brief:** daily status proposal (body + prefs); respect quiet hours; mute available.
5. **Dream seal (local):** fsync + checksummed package; light capped manage-pass optional; WORLDVIEW digest cites FACTS; whitelist auto-merge only; push after one-time remote confirm.
6. **Eval smokes:** disk free accuracy; remember/retrieve FACT; Tailscale-only; no fake success without receipt.

This delivers Jarvis-*feel* ingredients that are **evidence-aligned** on this hardware: grounded status, continuity, controlled initiative — without voice, home automation, or local-AGI theater.

**Before coding networking / agent slices:** research card (§8). Next ops pointer after docs commit: **M01 Tailscale** hardening (ACL Aryan-only + session auth design) — card before implementation.

---

## 7. Decision log (resolved; v1.1 finalization)

| # | Topic | Resolution |
|---|--------|------------|
| 1 | Cortex | **Gemini primary**; adapter for Claude/others later; offline stub = organs-only degraded mode |
| 2 | Channel | **Tailscale-only web HUD + chat**; ACL Aryan devices; session auth for Agent writes |
| 3 | Voice | **Tier A none**; **B PTT**; **C always-listen + voice-ID** |
| 4 | Actuation | Auto: body read, lifecycle/runs append, birth once, FACT append, Dream seal; whitelist Dream merge; confirm: FACT overwrite/delete, sensitive merges, first `dream.push`; deny: general web/email/HA |
| 5 | Identity & memory | Embodied personal aide; **no** consciousness claims; **dual-store** FACTS vs WORLDVIEW; Aryan may inspect/export/**delete** anytime |
| 6 | Cloud trust | Named rings: Tailscale ≠ Gemini ≠ backup; “no exfil” = no unallowlisted egress; future PII-redact research path |
| 7 | Quiet / faults | Heal-first overnight; wake only if recovery fails or urgent faults (body list) |
| 8 | Lab | Module research card before major slices; harder-but-correct when it teaches |
| — | Operator | **Aryan** sole command authority; people known by name, no order rights |
| — | Voice/personality | Full-stage witty roast energy (**she/her**); truth over charm; warmly forward + quiet 23:00–07:00 NZST |

Living-doc note: amend via constitution change process when locks move; patch this table when superseded.

---

## 8. Module research card gate (required before major slices)

**POLICY (lab).** Before Tier A/B capability work beyond trivial doc edits, write a short card (path suggestion: `docs/modules/<name>.md` when created — **do not invent modules early**). Networking / Tailscale harden = next candidate after this doc patch; card first.

**Required fields:**
1. Question / capability  
2. Lens tags (FANFICTION / EVIDENCE / FEASIBLE / POLICY)  
3. ≥2 citations or explicit “metal-only / systems practice”  
4. Pi 5 8GB feasibility note  
5. **Learning objective** (what Aryan/the lab should understand afterward)  
6. Harder-but-correct choice vs shortcut  
7. Won’t-chase for this slice  
8. Acceptance falsifiers (`eval.smoke` / body §10 style)  
9. Egress impact (which trust ring touches data)  

No card → no major slice. Tiny stubs/pointers allowed without full card; full organ implementation is not.

---

## References (selected)

- Yao et al., *ReAct* (2022) — https://arxiv.org/abs/2210.03629  
- Schick et al., *Toolformer* (2023) — https://arxiv.org/abs/2302.04761  
- Packer et al., *MemGPT* (2023) — https://arxiv.org/abs/2310.08560  
- Zhang et al., *A Survey on the Memory Mechanism of LLM-based Agents* (2024) — https://arxiv.org/abs/2404.13501  
- Park et al., *Generative Agents* (2023) — memory stream / reflection pattern  
- *The Horizon Gap…* (2026 survey) — https://arxiv.org/html/2608.06663  
- *The Long-Horizon Task Mirage?* (2026) — https://arxiv.org/html/2604.11978v1  
- Memory surveys 2026 — https://arxiv.org/html/2603.07670v1 , https://arxiv.org/html/2602.19320  
- Auto-Dreamer (2026) — https://arxiv.org/html/2605.20616 — offline consolidation lineage (**won’t train**)  
- *When Stored Evidence Stops Being Usable* (2026) — https://arxiv.org/html/2605.07313  
- LoCoMo (2024) — https://arxiv.org/abs/2402.17753 — optional homework, not v1 gate  
- LongMemEval (2024) — https://arxiv.org/abs/2410.10813 — optional homework, not v1 gate  
- *Agents That Know Too Much* (2026) — https://arxiv.org/html/2606.26627  
- Consent Integrity / LITL (2026) — https://arxiv.org/html/2606.02668v1  
- Progent (2025) — https://arxiv.org/pdf/2504.11703  
- MemPrivacy (2026) — https://arxiv.org/html/2605.09530v3 — future redact research  
- Pi5 local LLM / voice latency community benches (2025–26) — e.g. SpecPicks / offline voice writeups  

---

### Internal (downstream)
- [`01_BODY.md`](./01_BODY.md) — metal, organs, Dream/durability, acceptance  
- [`02_CONSTITUTION.md`](./02_CONSTITUTION.md) — normative charter v1.1  

---

*Research notes are living. §7 + constitution v1.1 supersede older open-question framing; deepen and amend as the system grows.*
