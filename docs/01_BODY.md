# ADA — Body Document (`01_BODY`)

**Status:** living body design + inventory (v1.1 finalization)  
**Date:** 2026-08-12  
**Machine:** `ada-pi5` (Raspberry Pi 5 Model B Rev 1.1)  
**Branch:** `rewrite/v1-body`  
**Depends on:** [`00_ASSISTANT_RESEARCH.md`](./00_ASSISTANT_RESEARCH.md), [`VISION.md`](../VISION.md), [`02_CONSTITUTION.md`](./02_CONSTITUTION.md)

### Project intent (lab framing)

This body serves a **personal lab + daily-use companion + PhD-prep learning surface** — **not** a product to ship. Prefer **harder-but-correct** organ design when it teaches (typed tools, crash-safe writes, dual-store memory, explicit egress). Major new organs need a **module research card** first (research §8; constitution lab mode).

This document defines **the body**: the physical host, durable substrate, sensors, lifecycle memory, ingress, and the organs that ground the agent in reality. It is **research-cited** where claims leave the metal, and **machine-backed** where claims are about *this* Pi (inspection summary in §1; original collect pass 2026-08-11).

Lens tags (same as research notes):

| Tag | Meaning |
|-----|---------|
| **METAL** | Measured / observed on this host |
| **EVIDENCE** | Supported by papers, surveys, or established systems patterns |
| **POLICY** | Locked product decision for rewrite/v1-body |
| **FEASIBLE** | Practical on Pi 5 8GB with current peripherals |

### Cloud trust rings (POLICY)

| Ring | Path | Counterparty |
|------|------|--------------|
| Control plane | HUD / chat ingress | Tailscale (Aryan devices + session auth for Agent writes) |
| Cortex egress | Chat context + light Dream manage-pass deltas | Gemini (primary) |
| Backup egress | Sealed Dream packages | S3-compatible remote via `dream.push` |

**“No exfil”** = no **unallowlisted** egress. Hybrid Gemini is accepted; future lab harden = PII redact / quiet local small model before cloud (research path — not Tier A gate). Never-to-cloud: API keys, rclone creds, operator secrets.

### Smoke eval (shared pointer)

Acceptance criteria: **§10** below. Future runtime organ: `eval.smoke`. Cross-link: research metrics §2; constitution enforcement map. Do not invent passing numbers before the harness exists. When cortex/Dream/HUD land: **meter tokens and cloud usage** in logs/HUD (promise only — no fake dashboards yet).

---

## 0. Purpose of “body” (why this doc exists)

**FANFICTION pull:** Jarvis/Justine feel embodied — they know *their* lab/home state.  
**Engineering translation:** embodiment here means **grounded self-report + durable autobiography + constrained actuators on one always-on host**, not consciousness.

**EVIDENCE.** Agents that claim environment state without sensors hallucinate. ReAct-style loops that interleave reasoning with tool observations reduce error propagation versus ungrounded chain-of-thought ([Yao et al., 2022](https://arxiv.org/abs/2210.03629)). Hybrid LLM + tools outperform “all knowledge in weights” for calendar/time/lookup-class facts ([Schick et al., 2023 — Toolformer](https://arxiv.org/abs/2302.04761)). Long-horizon failure modes shift toward memory loss and false completion as tasks stretch ([Horizon Gap survey, 2026](https://arxiv.org/html/2608.06663); [Long-Horizon Task Mirage, 2026](https://arxiv.org/html/2604.11978v1)). Offline consolidation as a second timescale ([Auto-Dreamer, 2026](https://arxiv.org/html/2605.20616) — cite lineage; don’t train).

**POLICY (VISION).** The LLM is **cortex/orchestrator**, not the whole organism. The body owns clocks, disks, process health, and lifecycle logs.

---

## 1. Hardware & host inventory (METAL)

Collected readonly on 2026-08-11 (`hostnamectl`, `free`, `lsblk`, `df`, `timedatectl`, `ip`, `vcgencmd`, `lscpu`, `lsusb`). Serial numbers intentionally omitted from this doc.

### 1.1 Compute identity
| Field | Value |
|-------|--------|
| Hostname | `ada-pi5` |
| Board | Raspberry Pi 5 Model B Rev 1.1 (`Revision d04171`) |
| SoC cores | 4× ARM Cortex-A76 |
| Clock | up to 2400 MHz (min 1500 MHz) |
| Userspace | `aarch64` / 64-bit |
| OS | Debian GNU/Linux 13 (trixie) |
| Kernel | `6.18.39+rpt-rpi-2712` |
| Timezone | `Pacific/Auckland` (NZST); NTP synchronized; hardware RTC present |

### 1.2 Memory & thermal (idle inspect)
| Field | Value |
|-------|--------|
| RAM | ~7.9 GiB total; ~7.1 GiB available idle |
| Swap | 2.0 GiB zram |
| Temp | ~45°C idle; `throttled=0x0` |
| Firmware mem split | ~1020M ARM / ~4M GPU (headless-leaning) |

**FEASIBLE implication.** Interactive RAM is the scarce resource. A concurrent local 7B+ LLM + STT + agent runtime is a bad default on 8GB ([community Pi 5 llama.cpp benches ~3–7 tok/s at 3–4B Q4; tighter/swappy at 7–8B](https://specpicks.com/reviews/raspberry-pi-5-local-llm-2026)). **API cortex + local organs** is the body-correct split (see research §4 Tier A).

### 1.3 Storage topology
| Device (role) | Mount / FS | Capacity (approx) | Role |
|---------------|------------|-------------------|------|
| SanDisk Cruzer Blade USB | `/boot/firmware` (vfat), `/` (ext4) | ~28G root, ~22G free | OS + packages |
| Seagate Expansion HDD (`LABEL=ada-data`) | `/mnt/ada-data` (ext4) | ~916G, ~870G free | **Durable organism substrate** |

**LAYOUT (present + planned durability trees):**
```text
/mnt/ada-data/
  ADA/                 # git repo (this project)
  memory/
    facts/             # strict semantic FACTS (prefs, identity stubs, …)
    worldview/         # freer digests / takes that cite facts
    dreams/            # dream digests (append-oriented)
    lifecycle*.jsonl   # or events/YYYY/MM.jsonl
  runs/                # episodic run transcripts / tool receipts
  dream/               # staging / outbox / sent — sealed snapshots (§6)
  scratch/             # disposable workspace (not backed up by default)
```

**POLICY.** Agent code may live in the repo; **facts about life and operator** live under `/mnt/ada-data/{memory,runs,dream}` so wipes of `ADA/` git history do not erase autobiography or sealed backups.

### 1.3.1 USB-root risk (accepted) + mitigations (POLICY + METAL)

**Accepted:** OS root on a USB stick is convenient and less durable than μSD/NVMe. Operator accepts this lab tradeoff for now.

**Mitigations (body must implement when organs land):**
1. Watch **root free space** and **ada-data mount health** as separate vitals.  
2. Treat unmounted `/mnt/ada-data` as a **hard body fault** (refuse durable writes; no fake memory success).  
3. Keep autobiography on HDD, not only on root USB.  
4. Crash-safe local write protocol (§6.2) + Dream seal + off-box package for disk-loss mode.  
5. Optional later: move root to μSD/NVMe — **not** a gate for first life; don’t ZFS-before-loop.

HDD alone is not off-site safety — process crash vs disk death are different failure modes (§6).

### 1.4 Network & peripherals
| Interface / peripheral | Status |
|------------------------|--------|
| `wlan0` | UP (LAN IPv4 observed; mesh outreach via Tailscale — POLICY) |
| `eth0` | DOWN |
| Mic / camera | Not observed on USB inventory |
| Toolchain | Python 3.13.5 present; Node/Docker/Ollama not observed |

**POLICY.** Voice: **Tier A none**; Tier B push-to-talk; Tier C always-listen + voice-ID. No mic required for body slice.

---

## 2. Locked product decisions that shape the body

Carried from research + operator decisions (2026-08-11 / finalization 2026-08-12):

| Topic | Lock |
|-------|------|
| Intent | Personal lab + daily companion + PhD-prep learning — not a product |
| Cortex | **Gemini primary**; cortex adapter so Claude (or others) can plug in later |
| Channel | **Web UI on Tailscale only**; ACL **Aryan devices**; session auth for **Agent** writes |
| Runtime | **Python 3** |
| Voice | Tier A none / B PTT / C always-listen+voice-ID |
| Pronouns | **she/her** |
| Personality (verbal) | **Full-stage witty friend** (Raina/Kamra-class energy) — loyal; truth over charm |
| Proactivity | **Warmly forward** + quiet hours **23:00–07:00 NZST**; **heal-first** faults overnight |
| Operator | **Aryan** sole command authority; people-by-name, no guest command rights |
| Continuity | **Birth ledger + lifecycle log** |
| Memory | **Dual-store:** FACTS (strict) + WORLDVIEW (freer, cites facts); whitelist Dream auto-merge |
| Dream | Consolidate + fsync + seal + light capped Gemini on deltas; batch backup after one-time push confirm |
| Off-box backup | Local-first; S3-compatible via rclone later (R2/B2/S3 undecided) |
| Cloud metering | Meter tokens/egress when cortex/Dream/HUD land (promise; no fake numbers) |
| Delight UI | Pretext/face animation is a **later skin** over the same stream |
| Non-goals | Custom distro; local LLM as main brain; open unauth control; SEO factory on this branch |

---

## 3. Embodiment model: organs, not vibes

**EVIDENCE.** Toolformer / ReAct pattern: the model proposes; **typed tools** return observations. Body organs are deterministic programs that emit receipts. Confirm UIs must render **real tool name + args from the gateway**, not model prose ([Consent Integrity, 2026](https://arxiv.org/html/2606.02668v1); least-privilege gateways: [Progent, 2025](https://arxiv.org/pdf/2504.11703)).

### 3.1 Organ map (Tier A body + control/privacy stubs)
| Organ | Responsibility | Side-effect class |
|-------|----------------|-------------------|
| `body.vitals` | temp, throttle flags, load, RAM, disk free (`/`, `/mnt/ada-data`), mount present, net link summary | **read** |
| `body.identity` | hostname, board model, OS string, timezone, agent version, `born_at` | **read** (+ first-write of birth card) |
| `lifecycle.append` | wake, sleep/stop, crash marker, deploy/version bump, config change, dream_*, heal/retry | **append-only write** |
| `runs.append` | session/tool transcript segments | **append-only write** |
| `memory.facts` | strict structured FACTS (prefs, people stubs, identity fields) | **read**; write policy §5 |
| `memory.worldview` | digests / takes that cite FACTS; never overwrite FACTS | **write** (Dream + approved synthesis) |
| `memory.search` | grep/structured query over facts + worldview + lifecycle | **read** |
| `memory.open_loops` | projects, promises, TODOs | **read/append**; overwrite confirm |
| `dream.run` | seal snapshot, light consolidate, optional light LLM manage-pass, checksum | **privileged write** (§6) |
| `dream.push` | upload sealed package to configured object remote only | **privileged outbound** (§6.7) |
| `channel.web` | Tailscale-served HUD + chat | ingress on mesh only |
| `auth.session` | bind Agent writes to Aryan session (beyond mere Tailnet presence) | **auth gate** |
| `schedule.quiet` | quiet hours 23:00–07:00 NZST; proactive suppress | **read/config** |
| `control.mute` | mute / chill / kill-switch for proactivity | **write** (operator) |
| `privacy.egress` / redact | classify egress ring; never-send secrets; future redact hook | **gate** |
| `secrets.load` | load Gemini / rclone secrets from outside git | **read** (privileged) |
| `eval.smoke` | run body acceptance / memory smokes; log results under `runs/` | **read** (+ append results) |

Procedural skills live in **git-tracked** code/docs (research procedural tier) — loader later; not a separate store of “beliefs.”

Future organs (Tier B+, not body-required): allowlisted fetch, calendar, HA, voice adapters, heavy multi-day dream, local PII-redact model.

### 3.2 Modes (borrowed from agent harness practice)
**EVIDENCE / product pattern.** Separating readonly vs side-effecting sessions reduces accidental harm (same spirit as Ask vs Agent in coding harnesses).

| Mode | Allowed organs (default) |
|------|---------------------------|
| **Observe** | all reads: vitals, identity, search, log tails |
| **Agent** | Observe + append lifecycle/runs + FACT writes per §5 — requires valid `auth.session` |
| **Plan** | no writes; propose actions for confirmation (used by briefs) |

---

## 4. Lifecycle & autobiography (POLICY + EVIDENCE)

**Why.** Generative-agents literature popularized episodic memory streams and reflection over event lists ([Park et al., 2023](https://arxiv.org/abs/2304.03442)). Memory surveys treat **write–manage–read** loops as what turns a stateless model into a lasting agent ([Zhang et al., 2024](https://arxiv.org/abs/2404.13501); [2026 agent-memory surveys](https://arxiv.org/html/2603.07670v1)). Flat “MEMORY.md only” stores degrade on long runs ([MEMTIER analysis of flat memory failure modes](https://arxiv.org/html/2605.03675)).

ADA’s twist is **body-grounded autobiography**: not fictional childhood — **machine birth and operational history**.

### 4.1 Birth card (semantic FACT, tiny, structured)
Suggested path: `/mnt/ada-data/memory/facts/identity.yaml`

Fields (illustrative contract):
- `name`: ADA  
- `born_at`: ISO-8601 of first successful agent boot that wrote the card  
- `body_hostname`, `board_model`, `os`  
- `cortex_primary`: `gemini`  
- `voice_charter`: `witty_full_stage`  
- `pronouns`: `she/her`  
- `operator`: `Aryan`  
- `version`: agent package/version string  

**First-boot rule:** if card missing and `ada-data` mounted → create once; never silently rewrite `born_at`.

### 4.2 Lifecycle ledger (episodic, append-only)
Suggested path: `/mnt/ada-data/memory/lifecycle.jsonl` (or `events/YYYY/MM.jsonl`)

Event types (minimum):
- `birth` — first card write  
- `wake` — service start  
- `sleep` — clean stop  
- `fault` — crash / OOM / disk/mount failure observed  
- `heal_retry` / `heal_ok` / `heal_give_up` — overnight recovery attempts  
- `deploy` — version change  
- `dream_ok` / `dream_fail` — sealed dream + optional push result (§6)  
- `note` — human- or agent-authored milestone (rare)

Each line: `{ts, type, summary, details?, receipts?}`.

**Truth rule:** ADA may narrate lifecycle only from ledger + vitals receipts. No invented outages.

### 4.3 Runs (episodic tool ground truth)
Path: `/mnt/ada-data/runs/<utc-date>/<session_id>.jsonl`  
Stores user turns, tool calls, observations, denials. This is the audit backbone for “truthful self-report” (research metrics §2).

---

## 5. Memory substrate (dual-store hybrid — POLICY)

Aligned with tiered memory architecture in literature (context / episodic / semantic / archive — MemGPT-style paging ([Packer et al., 2023](https://arxiv.org/abs/2310.08560)); surveys above).

| Tier | Store | Retrieval (Tier A) | Mutation |
|------|-------|--------------------|----------|
| Working | in-process session + recent run tail | always in context budget | ephemeral |
| Episodic | `runs/`, `lifecycle*.jsonl` | timestamp filters + **grep** | append-only |
| **FACTS** | `/mnt/ada-data/memory/facts/*` | key lookup + grep | append OK; **overwrite/delete confirm**; whitelist Dream auto-merge only |
| **WORLDVIEW** | `/mnt/ada-data/memory/worldview/*` + `memory/dreams/*.md` | grep + dated digests | freer Dream/awake synthesis; **must cite FACT keys / run receipts**; **never overwrite FACTS** |
| Cold | rotated archives on HDD | rare | compaction jobs later |

**EVIDENCE caution.** Agentic memory systems often underperform promises when retrieval is naive and maintenance cost ignored ([Anatomy of Agentic Memory, 2026](https://arxiv.org/html/2602.19320)). Tier A optimizes for **auditable append + searchable structure**, not embeddings-day-one. The under-built phase in most systems is **manage** (consolidate/prune), not write/read ([Memory for Autonomous LLM Agents, 2026](https://arxiv.org/html/2603.07670v1)) — that is exactly what Dream owns in §6. Reliability can drop as irrelevant history grows ([usable-scale eval, 2026](https://arxiv.org/html/2605.07313)).

**Embeddings:** Tier B when paraphrase recall hurts.

### 5.1 Dual-store rules (FACTS vs WORLDVIEW)

| | FACTS | WORLDVIEW |
|---|-------|-----------|
| Content | Standing prefs, identity fields, operator-salient entities, open loops | Daily digests, interpretations, consolidations, “takes” |
| Truth class | Metal-ish / operator-confirmed | Interpretive |
| Dream | Auto-merge **only whitelist keys** (§5.3) | Primary writer for digests |
| Overwrite | Confirm (or Aryan delete order) | May revise own digests; must not clobber FACTS |
| Cite | N/A (are the citations target) | Must point at FACT keys and/or run/lifecycle receipts |

Knowing things from day one does **not** require Dream: awake FACT appends already persist prefs, lifecycle, and runs.

### 5.2 What must be remembered *while awake* (not only in dream)

| Kind | Examples | Store |
|------|----------|--------|
| Identity | `born_at`, host, version, voice charter, pronouns | `facts/identity.yaml` |
| Lifecycle | wake/sleep/fault/deploy/dream_*/heal_* | lifecycle JSONL |
| Explicit remembers | prefs, nicknames, standing orders | `facts/` |
| Open loops | projects, promises, TODOs | `facts/open_loops.yaml` (via `memory.open_loops`) |
| People / places | operator-salient entities | `facts/` |
| Session ground truth | turns, tools, denials | `runs/` append-only |
| Boundaries | quiet hours, mute, tease-OK | `facts/` whitelist-aligned keys |
| Digests / takes | overnight meaning-making | `worldview/` + `dreams/` |

### 5.3 Dream FACT auto-merge whitelist (default = stage)

**POLICY.** Vague “low-risk” is retired. Auto-merge **only** these FACT keys when the Dream candidate is a well-typed clear value; **everything else stages** for Aryan confirm:

| Whitelist key | Expected shape (illustrative) |
|---------------|-------------------------------|
| `brief_time` | `HH:MM` local |
| `quiet_hours_start` / `quiet_hours_end` | `HH:MM` (defaults 23:00 / 07:00 NZST) |
| `mute_proactivity` | bool |
| `tease_ok` | bool |
| `preferred_tz` | IANA tz string (default Pacific/Auckland) |
| `brief_enabled` | bool |

**Always stage (never auto-merge):** people graphs, secrets, identity fields (`born_at`, operator, pronouns), open financial/health, conflicting values vs existing FACT, any key not listed above.

### 5.4 Actuation ladder (body-relevant)
| Action | Confirm? |
|--------|----------|
| Read vitals / identity / search / tail logs | No |
| Append lifecycle / runs | No |
| Create birth card if missing | No (once) |
| Append durable FACT note | No (append-only) |
| Edit/delete FACTS | **Yes** (unless Aryan delete order) |
| Write WORLDVIEW digest | No (must cite; never overwrite FACTS) |
| Dream whitelist auto-merge | No (keys in §5.3 only) |
| Dream staged merge | **Yes** |
| `dream.run` (local seal + light consolidate) | No (scheduled / on sleep); report status |
| **First** `dream.push` after remote configured | **Yes** (one-time autobiography confirm) |
| Later `dream.push` batch | No (same remote); **deny** if unset |
| General outbound HTTP / email / HA / arbitrary shell | **Denied in Tier A** |

---

## 6. Durability, Dream, and batch off-box backup (POLICY + EVIDENCE)

### 6.1 Two failure modes (do not conflate)

| Failure | What can die | Body response |
|---------|--------------|---------------|
| Process crash / OOM / unclean power | Unflushed buffers; half-written files | Crash-safe local write protocol (§6.2) |
| Disk death / theft / wipe of `/mnt/ada-data` | Entire autobiography + runs | Sealed Dream packages + off-box batch upload (§6.4–6.5) |

Cloud backup without local fsync still loses the last turns on crash. Local durability without off-box copy still dies with the Seagate.

### 6.2 Crash-safe local writes (METAL + systems practice)

**EVIDENCE (storage systems, not agent papers).** Durable apps treat OS write buffers as hostile: sync barriers matter; some stacks document that `fsync`/`FlushFileBuffers` assumptions can fail on lying hardware ([SQLite atomic commit notes](https://www.sqlite.org/atomiccommit.html)). Append-only logs + checksummed frames (e.g. SQLite WAL) tolerate torn writes by ignoring incomplete tails ([SQLite WAL](https://www.sqlite.org/wal.html)).

**ADA Tier A file protocol (FEASIBLE on ext4 HDD):**
1. **Append-only JSONL/MD** for lifecycle + runs (never rewrite history in place).  
2. **Structured files:** write `*.tmp` → `fsync` file → **atomic `rename`** → `fsync` parent directory.  
3. On start: if last JSONL line is truncated/invalid → emit `fault`, skip bad line, continue.  
4. Optional later: SQLite WAL for hot structured indexes — not required for first life.  
5. Bound loss goal: at most the **current unfinished turn**, not days of memory.

### 6.3 What “Dream” means here (not consciousness)

**FANFICTION risk:** “dreaming” sounds like REM / inner life.  
**Engineering meaning:** an **offline manage pass** over memory — consolidate, re-represent, prune candidates — off the interactive critical path.

**EVIDENCE lineage:**
- **Write–manage–read** as the formal memory loop; manage is often neglected ([Memory for Autonomous LLM Agents, 2026](https://arxiv.org/html/2603.07670v1)).  
- **Episodic → semantic consolidation** and reflection over memory streams ([Park et al., 2023 — Generative Agents](https://arxiv.org/abs/2304.03442)); episodic reflection/consolidation as a named mechanism family ([Anatomy of Agentic Memory, 2026](https://arxiv.org/html/2602.19320)).  
- **Hierarchical / paging memory** and self-directed memory ops ([Packer et al., 2023 — MemGPT](https://arxiv.org/abs/2310.08560)); productized as background sleep-time agents ([Letta sleep-time agents](https://docs.letta.com/guides/agents/architectures/sleeptime/); [Lin et al., 2025 — Sleep-time Compute](https://arxiv.org/abs/2504.13171)).  
- **Two-timescale offline consolidation** ([Auto-Dreamer, 2026](https://arxiv.org/html/2605.20616) — cite; won’t train).  
- **Verbal reflection into episodic memory** without weight updates ([Shinn et al., 2023 — Reflexion](https://arxiv.org/abs/2303.11366)).  
- Flat single-file memory degrades on long-running agents ([MEMTIER, 2026](https://arxiv.org/html/2605.03675)).  
- Maintenance latency/cost is a first-class limit of agentic memory ([Anatomy of Agentic Memory, 2026](https://arxiv.org/html/2602.19320)) — hence **caps** on early LLM dream.

Biological sleep-consolidation (hippocampal replay) is a **metaphor** for offline reorganization, not a claim that ADA sleeps or is conscious ([Rasch & Born, 2013](https://pubmed.ncbi.nlm.nih.gov/23589831/) is the classic review often cited in this analogy — useful color only).

### 6.4 Dream pipeline (locked shape)

**POLICY.** Dream = **consolidate + fsync + seal (+ light LLM manage) + batch ingest toward cloud**.

Suggested tree:
```text
/mnt/ada-data/dream/
  staging/    # snapshot being built
  outbox/     # sealed, checksummed packages ready to upload
  sent/       # local copies/records of successfully pushed manifests
```

**Steps (each run):**
1. Quiesce open appends; fsync journals.  
2. Build **delta** since last `dream_ok` (new lifecycle lines, new `runs/` bytes, new FACT/WORLDVIEW files) — not full history replay every night.  
3. Seal package: identity + FACT YAML + WORLDVIEW delta + episodic delta + `MANIFEST.json` + checksums + `dream_id` / hostname / `born_at` / agent version.  
4. **Light LLM manage-pass (early POLICY):** one capped Gemini call over the delta only → structured `{digest, fact_candidates[], worldview_notes[], open_loops[], conflicts[]}` — this is **cortex egress** (trust ring).  
5. Write WORLDVIEW digest under `memory/worldview/` / `memory/dreams/YYYY-MM-DD.md` with citations; **auto-merge only §5.3 whitelist** FACT keys; **stage** all else; surface conflicts — never silently overwrite identity or non-whitelist FACTS. Quiet hours do not block Dream (offline manage), but user-facing nudges respect 23:00–07:00 NZST.  
6. Move sealed package to `outbox/`; try `dream.push` per §6.7 if remote configured.  
7. Append lifecycle `dream_ok` or `dream_fail` with receipts (bytes, token spend when metering exists, push status).

**Schedule (FEASIBLE):** systemd timer (nightly NZST) + on clean `sleep`; optional after long sessions.

### 6.5 What light Dream may “make meaning” of

| Allowed outputs | Rule |
|-----------------|------|
| Daily WORLDVIEW digest | Interpretive; cite FACTS/receipts; not equal to metal truth |
| FACT **candidates** | Auto-merge **whitelist only** (§5.3); else stage |
| Open-loop refresh | Still open / newly closed |
| Conflicts | Pref A vs today said B → surface, don’t clobber |
| Forget/archive hints | Noise nominations for cold tier |

| Forbidden | Why |
|-----------|-----|
| Rewriting `born_at` / inventing outages | Truth = ledger + vitals only |
| Overwriting FACTS from WORLDVIEW prose | Dual-store integrity |
| Heavy multi-week mythopoetic backstory as FACT | Horizon/noise risk |
| Treating dream prose as equal to run receipts | Breaks truthful self-report |

### 6.6 Heavy LLM dream (deferred)

When weeks of history exist and the lovable loop is solid: longer reflection, deeper preference models, stronger compression of old runs — still off interactive path, still budgeted ([Lin et al., 2025](https://arxiv.org/abs/2504.13171); cost warnings in [Anatomy of Agentic Memory, 2026](https://arxiv.org/html/2602.19320)). Not a gate for first wake.

### 6.7 Off-box batch ingest (local-first)

**POLICY.** Design the uploader now; **choose R2/B2/S3 later**. Interface = S3-compatible via `rclone` (or equivalent).

- Push **immutable** `dream/<dream_id>/` or tarball + manifest.  
- Retention: keep N local outbox/sent; keep M remote generations.  
- Secrets for remote outside git (`secrets.load`).  
- `dream.push` is the **only** Tier A outbound backup path: allowlisted bucket endpoint, not open crawl.  
- **First successful configuration of remote + first push:** require **one-time Aryan confirm** acknowledging autobiography leaves the Pi. Subsequent scheduled pushes to that same remote may batch without per-push confirm.  
- Changing remote / credentials resets the one-time confirm.

Until remote is configured: local seal still runs; HUD shows `push=skipped`.

### 6.8 HUD / vitals fields for Dream

Expose: `last_dream_at`, `last_dream_status`, `bytes_pending_push`, `last_push_at`, and (when metering lands) approximate token/egress counters (alongside lifecycle pane).

### 6.9 Quiet hours & overnight faults (heal-first)

**POLICY.** Quiet hours **23:00–07:00 NZST**: no user-facing proactive chat pings.

**Heal-first:** on fault overnight, organs retry + cleanup first; emit `heal_retry` / `heal_ok` / `heal_give_up`. Prefer morning brief of overnight recoveries over chatty pages.

**May pierce quiet hours with a single alert** only if recovery fails **or** an urgent fault holds:

| Urgent fault | Why wake |
|--------------|----------|
| `/mnt/ada-data` unmounted / missing | Autobiography + durable writes blocked |
| Root or `ada-data` free space below threshold | Imminent write failure |
| `throttled` flags ≠ `0x0` sustained | Thermal/power integrity |
| Agent service crash loop / repeated wake↔fault without heal_ok | Body not staying up |

Non-urgent errors: log + retry; no night ping.

---

## 7. Ingress & HUD (POLICY)

**POLICY.** Tailscale-only. No public internet control plane (research non-goal).

### 7.1 Exposure model
- Agent binds to localhost (or Tailscale interface only).  
- Operator reaches UI via Tailnet MagicDNS / `tailscale serve` as operational choice.  
- **Auth:** Tailscale ACL limited to **Aryan’s devices**; **Agent-mode writes** require `auth.session` (app session / password) — not “any Tailnet peer.” Observe may stay mesh-gated.  
- Confirm dialogs: gateway renders tool name + args (consent integrity).

### 7.2 Tier A HUD panes (locked)
1. **Stream** — tokens + tool call/result cards  
2. **Body vitals** — temp, throttle, disks, net, mount OK  
3. **Lifecycle** — `born_at`, last wake, last fault/heal, **last dream status**  
4. **Mode + permissions** — Observe/Agent/Plan; last denials; session auth state  
5. **Raw log tail** — current run file  

Deferred: memory-hit inspector; token/egress meters (promise when cortex lands).

**Delight:** pretext “face” consumes the **same stream**; must not block body truthfulness or dream durability work.

---

## 8. Service shape on the host (FEASIBLE)

Not implemented here; contract for upcoming code:

| Piece | Intent |
|-------|--------|
| systemd user or system unit `ada-agent.service` | supervised always-on process |
| systemd timer `ada-dream.timer` | nightly (+ on sleep) Dream seal / light LLM / optional push |
| Python package under `ADA/` | vitals, lifecycle, memory, dream, agent loop, web HUD |
| Secrets | outside git — Gemini API key; later rclone/S3 credentials |
| Health | unit restart on crash → emits `fault`/`wake`/`heal_*` lifecycle events |
| Clocks | trust systemd-timesyncd; include tz in vitals |

**Horizon discipline (EVIDENCE).** Cap autonomy; persist goals outside the context window; prefer short loops with receipts ([Horizon Gap, 2026](https://arxiv.org/html/2608.06663)). The body’s job is to make short loops *true*, not to enable unsupervised multi-day missions. Dream is allowed longer compute because it is **off the interactive path** ([Lin et al., 2025](https://arxiv.org/abs/2504.13171)).

---

## 9. Cortex placement relative to body

| Component | Location | Role |
|-----------|----------|------|
| Gemini (primary) | API (cloud) — **cortex egress ring** | language + tool selection; **light dream manage-pass** |
| Future Claude/etc. | API via same adapter | drop-in cortex / optional heavier dream later |
| Local tiny LLM | optional later | offline stub / classifier / **future PII redact research** — **not** main brain |
| `privacy.egress` | **this Pi** | never-send secrets; classify ring; future redact hook |
| Tools / organs | **this Pi** | ground truth + durable stores + dream seal |

**Egress classes to Gemini (when live):**
- **Chat:** user text + selected tool schemas + retrieved FACT/WORLDVIEW slices for the turn + tool observations.  
- **Dream manage-pass:** delta package summary only (capped).  
Never: raw API keys, rclone config, git-ignored secret files.

**FEASIBLE.** Matches Pi 5 8GB constraints and VISION cortex wording. Local full-stack voice assistants on Pi 5 often report multi-second to multi-ten-second E2E latency even when they work ([offline Pi 5 voice writeups](https://bmdpat.com/blog/raspberry-pi-5-local-voice-ai-2026)) — irrelevant to Tier A body, informative for later voice.

---

## 10. Body acceptance criteria (how we know the body is real)

Before calling “body slice done,” these must be true (`eval.smoke` will automate when coded):

1. **Mount honesty** — if `/mnt/ada-data` missing, agent refuses durable writes and reports fault (no fake memory success).  
2. **Vitals match metal** — HUD/tool answers for disk free / temp / throttle agree with `df` / `vcgencmd` within tolerance.  
3. **Birth once** — second boot does not change `born_at`; emits `wake` not second `birth`.  
4. **Lifecycle continuity** — crash + restart produces readable `fault`/`wake` (and heal_*) sequence.  
5. **Crash-safe append** — kill mid-write loses at most the unfinished line/turn; prior JSONL/YAML remains valid.  
6. **Dream seal** — a Dream run produces a checksummed package under `dream/outbox/` (or `sent/`) and a `dream_ok`/`dream_fail` lifecycle event; light LLM failure must not block local seal.  
7. **Dual-store** — WORLDVIEW write cannot change FACT values; whitelist merge only touches §5.3 keys.  
8. **Tailscale-only** — agent UI not exposed on `0.0.0.0` to the open LAN/WAN without mesh; Agent writes require session auth.  
9. **No local-LLM dependency** — body organs + local Dream seal work even if cortex API is down (degraded: vitals HUD still live; dream manage-pass skipped with receipt).  
10. **Quiet / mute** — no non-urgent proactive ping in quiet hours; mute honors immediately.  
11. **First-push confirm** — push blocked until one-time operator confirm after remote config.  
12. **Digest ≠ metal** — ADA must distinguish WORLDVIEW digests from lifecycle/vitals when asked.

These operationalize “truthful self-report” from research §2 and durable embodiment under HDD + USB-root risk.

---

## 11. Explicit body non-goals

- Custom Linux distro / replacing Debian trixie host  
- Moving root to fancy ZFS/btrfs *before* agent loop exists (USB-root accepted with mitigations)  
- Camera/mic embodiment in Tier A  
- NPU/AI HAT as a gate for first life  
- Claiming feelings, suffering, or consciousness from uptime metrics or “dreams”  
- Public deployment of the agent UI  
- Heavy multi-day LLM myth-making before awake FACT memory + light Dream exist  
- Continuous chatty cloud sync (prefer scheduled batch packages)  
- Training Auto-Dreamer / chasing LoCoMo as v1 gate  

---

## 12. Mapping: research north star → body organs

| Wanted feel | Body mechanism |
|-------------|----------------|
| Situationally aware | `body.vitals` + mount/net honesty |
| “Knows its history” | birth card + lifecycle ledger |
| “Knows me over time” | awake FACT writes + WORLDVIEW Dream consolidates with cites |
| Survives crash / disk loss | fsync/append protocol + sealed Dream + off-box push |
| Trustworthy | runs receipts + deny-by-default actuators + consent-integrity confirms |
| Always-on companion | systemd-supervised service + wake/heal events |
| Personal continuity | dual-store memory on `ada-data` HDD |
| Private *enough* | Tailscale control plane; named cortex/backup trust rings |

---

## 13. References

### Papers & surveys (agent loop / tools)
- Yao et al., *ReAct* (2022) — https://arxiv.org/abs/2210.03629  
- Schick et al., *Toolformer* (2023) — https://arxiv.org/abs/2302.04761  
- Progent (2025) — https://arxiv.org/pdf/2504.11703  
- Consent Integrity (2026) — https://arxiv.org/html/2606.02668v1  

### Papers & surveys (memory, consolidation, sleep-time)
- Packer et al., *MemGPT* (2023) — https://arxiv.org/abs/2310.08560  
- Park et al., *Generative Agents* (2023) — https://arxiv.org/abs/2304.03442  
- Shinn et al., *Reflexion* (2023) — https://arxiv.org/abs/2303.11366  
- Zhang et al., *A Survey on the Memory Mechanism of LLM-based Agents* (2024) — https://arxiv.org/abs/2404.13501  
- Lin et al., *Sleep-time Compute* (2025) — https://arxiv.org/abs/2504.13171  
- *Memory for Autonomous LLM Agents* (2026 survey) — https://arxiv.org/html/2603.07670v1  
- *Anatomy of Agentic Memory* (2026) — https://arxiv.org/html/2602.19320  
- *MEMTIER* — https://arxiv.org/html/2605.03675  
- Auto-Dreamer (2026) — https://arxiv.org/html/2605.20616 — lineage only  
- *When Stored Evidence Stops Being Usable* (2026) — https://arxiv.org/html/2605.07313  
- *The Horizon Gap* (2026) — https://arxiv.org/html/2608.06663  
- *The Long-Horizon Task Mirage?* (2026) — https://arxiv.org/html/2604.11978v1  

### Privacy / cloud trust (cite; don’t invent unused systems)
- *Agents That Know Too Much* (2026) — https://arxiv.org/html/2606.26627  
- MemPrivacy (2026) — https://arxiv.org/html/2605.09530v3 — future redact research path  

### Systems durability (local crash safety)
- SQLite, *Atomic Commit In SQLite* — https://www.sqlite.org/atomiccommit.html  
- SQLite, *Write-Ahead Logging* — https://www.sqlite.org/wal.html  

### Metaphor only (not evidence ADA is conscious)
- Rasch & Born, sleep-dependent memory consolidation review (2013) — https://pubmed.ncbi.nlm.nih.gov/23589831/  

### Product / architecture docs (sleep-time agents)
- Letta, Sleep-time agents — https://docs.letta.com/guides/agents/architectures/sleeptime/  

### Hardware / edge feasibility (community measured)
- Pi 5 local LLM token/s reports — e.g. https://specpicks.com/reviews/raspberry-pi-5-local-llm-2026  
- Pi 5 offline voice latency reports — e.g. https://bmdpat.com/blog/raspberry-pi-5-local-voice-ai-2026  

### Internal
- [`00_ASSISTANT_RESEARCH.md`](./00_ASSISTANT_RESEARCH.md)  
- [`02_CONSTITUTION.md`](./02_CONSTITUTION.md)  
- [`VISION.md`](../VISION.md)  

---

*Body document is living. Normative law lives in the constitution; metal and organs live here.*
