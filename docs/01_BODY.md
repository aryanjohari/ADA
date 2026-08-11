# ADA — Body Document (`01_BODY`)

**Status:** living body design + inventory (patched for constitution lock-in)  
**Date:** 2026-08-11  
**Machine:** `ada-pi5` (Raspberry Pi 5 Model B Rev 1.1)  
**Branch:** `rewrite/v1-body`  
**Depends on:** [`00_ASSISTANT_RESEARCH.md`](./00_ASSISTANT_RESEARCH.md), [`VISION.md`](../VISION.md), [`02_CONSTITUTION.md`](./02_CONSTITUTION.md)

This document defines **the body**: the physical host, durable substrate, sensors, lifecycle memory, ingress, and the organs that ground the agent in reality. It is **research-cited** where claims leave the metal, and **machine-backed** where claims are about *this* Pi (inspection summary in §1; original collect pass 2026-08-11).

Lens tags (same as research notes):

| Tag | Meaning |
|-----|---------|
| **METAL** | Measured / observed on this host |
| **EVIDENCE** | Supported by papers, surveys, or established systems patterns |
| **POLICY** | Locked product decision for rewrite/v1-body |
| **FEASIBLE** | Practical on Pi 5 8GB with current peripherals |

---

## 0. Purpose of “body” (why this doc exists)

**FANFICTION pull:** Jarvis/Justine feel embodied — they know *their* lab/home state.  
**Engineering translation:** embodiment here means **grounded self-report + durable autobiography + constrained actuators on one always-on host**, not consciousness.

**EVIDENCE.** Agents that claim environment state without sensors hallucinate. ReAct-style loops that interleave reasoning with tool observations reduce error propagation versus ungrounded chain-of-thought ([Yao et al., 2022](https://arxiv.org/abs/2210.03629)). Hybrid LLM + tools outperform “all knowledge in weights” for calendar/time/lookup-class facts ([Schick et al., 2023 — Toolformer](https://arxiv.org/abs/2302.04761)). Long-horizon failure modes shift toward memory loss and false completion as tasks stretch ([Horizon Gap survey, 2026](https://arxiv.org/html/2608.06663); [Long-Horizon Task Mirage, 2026](https://arxiv.org/html/2604.11978v1)).

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
  ADA/          # git repo (this project)
  memory/       # durable personal + semantic memory (+ dreams/)
  runs/         # episodic run transcripts / tool receipts
  dream/        # staging / outbox / sent — sealed snapshots (§6)
  scratch/      # disposable workspace (not backed up by default)
```

**POLICY.** Agent code may live in the repo; **facts about life and operator** live under `/mnt/ada-data/{memory,runs,dream}` so wipes of `ADA/` git history do not erase autobiography or sealed backups.

**Risk note (METAL).** Root on a USB stick is convenient but less ideal than μSD/NVMe for OS durability. Body sense must watch root free space and `ada-data` mount health separately. Treat unmounted `ada-data` as a **hard body fault**. HDD alone is not off-site safety — process crash vs disk death are different failure modes (§6).

### 1.4 Network & peripherals
| Interface / peripheral | Status |
|------------------------|--------|
| `wlan0` | UP (LAN IPv4 observed; mesh outreach via Tailscale — POLICY) |
| `eth0` | DOWN |
| Mic / camera | Not observed on USB inventory |
| Toolchain | Python 3.13.5 present; Node/Docker/Ollama not observed |

**POLICY.** Voice (STT/TTS) is **out of Tier A**. No mic required for body slice.

---

## 2. Locked product decisions that shape the body

Carried from research + operator decisions (2026-08-11):

| Topic | Lock |
|-------|------|
| Cortex | **Gemini primary**; cortex adapter so Claude (or others) can plug in later |
| Channel | **Web UI on Tailscale only** (no public agent ingress in Tier A) |
| Runtime | **Python 3** |
| Voice | Out of Tier A |
| Personality (verbal) | **Full-stage witty friend** (Raina/Kamra-class energy) — loyal; truth over charm; Aryan red-lines tone — see constitution |
| Proactivity | **Warmly forward** + quiet hours **23:00–07:00 NZST** |
| Operator | **Aryan** sole command authority; people-by-name, no guest command rights |
| Continuity | **Birth ledger + lifecycle log** (“when I woke / what happened to me”) |
| Memory architecture | **Hybrid:** structured durable facts + append-only life/run logs + grep-first retrieval; Aryan may delete anytime |
| Dream | **Consolidate + fsync + seal + batch backup**; **light capped Gemini** over *new* events; **auto-merge low-risk** candidates only; heavy reflection later (§6) |
| Off-box backup | Pipeline designed **local-first**; S3-compatible sink via rclone later (R2/B2/S3 undecided) |
| Delight UI | Pretext/face animation is a **later skin** over the same stream |
| Non-goals | Custom distro; local LLM as main brain; open internet without auth; SEO factory on this branch |

---

## 3. Embodiment model: organs, not vibes

**EVIDENCE.** Toolformer / ReAct pattern: the model proposes; **typed tools** return observations. Body organs are deterministic programs that emit receipts.

### 3.1 Organ map (Tier A body)
| Organ | Responsibility | Side-effect class |
|-------|----------------|-------------------|
| `body.vitals` | temp, throttle flags, load, RAM, disk free (`/`, `/mnt/ada-data`), mount present, net link summary | **read** |
| `body.identity` | hostname, board model, OS string, timezone, agent version, `born_at` | **read** (+ first-write of birth card) |
| `lifecycle.append` | wake, sleep/stop, crash marker, deploy/version bump, config change | **append-only write** |
| `runs.append` | session/tool transcript segments | **append-only write** |
| `memory.semantic` | prefs/people/projects structured store | **read**; write policy in §5 |
| `memory.search` | grep/structured query over memory + lifecycle | **read** |
| `dream.run` | seal snapshot, light consolidate, optional light LLM manage-pass, checksum | **privileged write** (§6) |
| `dream.push` | upload sealed package to configured object remote only | **privileged outbound** (allowlisted sink; not general web) |
| `channel.web` | Tailscale-served HUD + chat | ingress on mesh only |

Future organs (Tier B+, not body-required): allowlisted fetch, calendar, HA, voice adapters, heavy multi-day dream.

### 3.2 Modes (borrowed from agent harness practice)
**EVIDENCE / product pattern.** Separating readonly vs side-effecting sessions reduces accidental harm (same spirit as Ask vs Agent in coding harnesses).

| Mode | Allowed organs (default) |
|------|---------------------------|
| **Observe** | all reads: vitals, identity, search, log tails |
| **Agent** | Observe + append lifecycle/runs + semantic writes per §5 |
| **Plan** | no writes; propose actions for confirmation (used by briefs) |

---

## 4. Lifecycle & autobiography (POLICY + EVIDENCE)

**Why.** Generative-agents literature popularized episodic memory streams and reflection over event lists ([Park et al., 2023](https://arxiv.org/abs/2304.03442)). Memory surveys treat **write–manage–read** loops as what turns a stateless model into a lasting agent ([Zhang et al., 2024](https://arxiv.org/abs/2404.13501); [2026 agent-memory surveys](https://arxiv.org/html/2603.07670v1)). Flat “MEMORY.md only” stores degrade on long runs ([MEMTIER analysis of flat memory failure modes](https://arxiv.org/html/2605.03675)).

ADA’s twist is **body-grounded autobiography**: not fictional childhood — **machine birth and operational history**.

### 4.1 Birth card (semantic, tiny, structured)
Suggested path: `/mnt/ada-data/memory/identity.yaml`

Fields (illustrative contract):
- `name`: ADA  
- `born_at`: ISO-8601 of first successful agent boot that wrote the card  
- `body_hostname`, `board_model`, `os`  
- `cortex_primary`: `gemini`  
- `voice_charter`: `witty_full_stage` (see `02_CONSTITUTION.md`)  
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
- `deploy` — version change  
- `dream_ok` / `dream_fail` — sealed dream + optional push result (§6)  
- `note` — human- or agent-authored milestone (rare)

Each line: `{ts, type, summary, details?, receipts?}`.

**Truth rule:** ADA may narrate lifecycle only from ledger + vitals receipts. No invented outages.

### 4.3 Runs (episodic tool ground truth)
Path: `/mnt/ada-data/runs/<utc-date>/<session_id>.jsonl`  
Stores user turns, tool calls, observations, denials. This is the audit backbone for “truthful self-report” (research metrics §2).

---

## 5. Memory substrate (hybrid — POLICY)

Aligned with tiered memory architecture in literature (context / episodic / semantic / archive — MemGPT-style paging ([Packer et al., 2023](https://arxiv.org/abs/2310.08560)); surveys above).

| Tier | Store | Retrieval (Tier A) | Mutation |
|------|-------|--------------------|----------|
| Working | in-process session + recent run tail | always in context budget | ephemeral |
| Episodic | `runs/`, `lifecycle*.jsonl` | timestamp filters + **grep** | append-only |
| Semantic | `/mnt/ada-data/memory/*.yaml` (+ optional `.md` notes) | key lookup + grep | structured update; **delete/overwrite confirm** |
| Cold | rotated archives on HDD | rare | compaction jobs later |

**EVIDENCE caution.** Agentic memory systems often underperform promises when retrieval is naive and maintenance cost ignored ([Anatomy of Agentic Memory, 2026](https://arxiv.org/html/2602.19320)). Tier A optimizes for **auditable append + searchable structure**, not embeddings-day-one. The under-built phase in most systems is **manage** (consolidate/prune), not write/read ([Memory for Autonomous LLM Agents, 2026](https://arxiv.org/html/2603.07670v1)) — that is exactly what Dream owns in §6.

**Embeddings:** Tier B when paraphrase recall hurts.

### 5.1 What must be remembered *while awake* (not only in dream)

Dream reorganizes; it must not be the only write path. If it matters tomorrow, land it during the day:

| Kind | Examples | Store |
|------|----------|--------|
| Identity | `born_at`, host, version, voice charter | `identity.yaml` |
| Lifecycle | wake/sleep/fault/deploy/dream_* | lifecycle JSONL |
| Explicit remembers | prefs, nicknames, standing orders | semantic YAML / pinned notes |
| Open loops | projects, promises, TODOs | `open_loops.yaml` (planned) |
| People / places | operator-salient entities | semantic files |
| Session ground truth | turns, tools, denials | `runs/` append-only |
| Boundaries | quiet hours, tease-OK | semantic prefs |

### 5.2 Actuation ladder (body-relevant)
| Action | Confirm? |
|--------|----------|
| Read vitals / identity / search / tail logs | No |
| Append lifecycle / runs | No |
| Create birth card if missing | No (once) |
| Append durable memory note | No (append-only) |
| Edit/delete semantic facts | **Yes** |
| `dream.run` (local seal + light consolidate) | No (scheduled / on sleep); report status |
| `dream.push` (object remote) | No once remote configured; **deny** if unset |
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
- **Hierarchical / paging memory** and self-directed memory ops ([Packer et al., 2023 — MemGPT](https://arxiv.org/abs/2310.08560)); productized as background sleep-time agents that update shared memory while the primary agent stays snappy ([Letta sleep-time agents](https://docs.letta.com/guides/agents/architectures/sleeptime/); research frame: [Lin et al., 2025 — Sleep-time Compute](https://arxiv.org/abs/2504.13171)).  
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
2. Build **delta** since last `dream_ok` (new lifecycle lines, new `runs/` bytes, new semantic files) — not full history replay every night.  
3. Seal package: identity + semantic YAML + delta episodic + `MANIFEST.json` + checksums + `dream_id` / hostname / `born_at` / agent version.  
4. **Light LLM manage-pass (early POLICY):** one capped Gemini call over the delta only → structured `{digest, candidates[], open_loops[], conflicts[]}`.  
5. Write digest append-only under `memory/dreams/YYYY-MM-DD.md`; **auto-merge only low-risk** explicit prefs (e.g. brief time); **stage** people/secrets/identity/high-impact candidates for Aryan confirm; surface conflicts — never silently overwrite identity or confirmed sensitive prefs. Quiet hours do not block Dream (offline manage), but proactive *user-facing* nudges respect 23:00–07:00 NZST.  
6. Move sealed package to `outbox/`; try `dream.push` if remote configured.  
7. Append lifecycle `dream_ok` or `dream_fail` with receipts (bytes, token spend, push status).

**Schedule (FEASIBLE):** systemd timer (nightly NZST) + on clean `sleep`; optional after long sessions.

### 6.5 What light Dream may “make meaning” of

| Allowed outputs | Rule |
|-----------------|------|
| Daily digest | Interpretive summary; cite that it is a digest, not metal truth |
| Semantic **candidates** | **Auto-merge low-risk only** (clear standing prefs); stage people/secrets/identity/high-impact; never clobber `born_at` |
| Open-loop refresh | Still open / newly closed |
| Conflicts | Pref A vs today said B → surface, don’t clobber |
| Forget/archive hints | Noise nominations for cold tier |

| Forbidden | Why |
|-----------|-----|
| Rewriting `born_at` / inventing outages | Truth = ledger + vitals only |
| Heavy multi-week mythopoetic backstory as fact | Horizon/noise risk; save for later heavy dream |
| Treating dream prose as equal to run receipts | Breaks truthful self-report |

**Knowing things from day one** does **not** require dream: awake append/semantic writes already persist prefs, lifecycle, and runs. Dream improves **manage quality** and **backup posture**.

### 6.6 Heavy LLM dream (deferred)

When weeks of history exist and the lovable loop is solid: longer reflection, deeper preference models, stronger compression of old runs — still off interactive path, still budgeted ([Lin et al., 2025](https://arxiv.org/abs/2504.13171); cost warnings in [Anatomy of Agentic Memory, 2026](https://arxiv.org/html/2602.19320)). Not a gate for first wake.

### 6.7 Off-box batch ingest (local-first)

**POLICY.** Design the uploader now; **choose R2/B2/S3 later**. Interface = S3-compatible via `rclone` (or equivalent).

- Push **immutable** `dream/<dream_id>/` or tarball + manifest.  
- Retention: keep N local outbox/sent; keep M remote generations.  
- Secrets for remote outside git.  
- `dream.push` is the **only** Tier A outbound exception: allowlisted bucket endpoint, not open crawl.  

Until remote is configured: local seal still runs; HUD shows `push=skipped`.

### 6.8 HUD / vitals fields for Dream

Expose: `last_dream_at`, `last_dream_status`, `bytes_pending_push`, `last_push_at` (alongside lifecycle pane).

---

## 7. Ingress & HUD (POLICY)

**POLICY.** Tailscale-only. No public internet control plane (research non-goal).

### 7.1 Exposure model
- Agent binds to localhost (or Tailscale interface only).  
- Operator reaches UI via Tailnet MagicDNS / `tailscale serve` as operational choice.  
- Auth base case: **presence on Tailnet** (device ACL). Additional app password optional later — not required for doc acceptance.

### 7.2 Tier A HUD panes (locked)
1. **Stream** — tokens + tool call/result cards  
2. **Body vitals** — temp, throttle, disks, net, mount OK  
3. **Lifecycle** — `born_at`, last wake, last fault, **last dream status**  
4. **Mode + permissions** — Observe/Agent/Plan; last denials  
5. **Raw log tail** — current run file  

Deferred: memory-hit inspector (useful, not must-ship).

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
| Health | unit restart on crash → emits `fault`/`wake` lifecycle events |
| Clocks | trust systemd-timesyncd; include tz in vitals |

**Horizon discipline (EVIDENCE).** Cap autonomy; persist goals outside the context window; prefer short loops with receipts ([Horizon Gap, 2026](https://arxiv.org/html/2608.06663)). The body’s job is to make short loops *true*, not to enable unsupervised multi-day missions. Dream is allowed longer compute because it is **off the interactive path** ([Lin et al., 2025](https://arxiv.org/abs/2504.13171)).

---

## 9. Cortex placement relative to body

| Component | Location | Role |
|-----------|----------|------|
| Gemini (primary) | API (cloud) | language + tool selection; **light dream manage-pass** |
| Future Claude/etc. | API via same adapter | drop-in cortex / optional heavier dream later |
| Local tiny LLM | optional later | offline stub / classifier — **not** main brain |
| Tools / organs | **this Pi** | ground truth + durable stores + dream seal |

**FEASIBLE.** Matches Pi 5 8GB constraints and VISION cortex wording. Local full-stack voice assistants on Pi 5 often report multi-second to multi-ten-second E2E latency even when they work ([offline Pi 5 voice writeups](https://bmdpat.com/blog/raspberry-pi-5-local-voice-ai-2026)) — irrelevant to Tier A body, informative for later voice.

---

## 10. Body acceptance criteria (how we know the body is real)

Before calling “body slice done,” these must be true:

1. **Mount honesty** — if `/mnt/ada-data` missing, agent refuses durable writes and reports fault (no fake memory success).  
2. **Vitals match metal** — HUD/tool answers for disk free / temp / throttle agree with `df` / `vcgencmd` within tolerance.  
3. **Birth once** — second boot does not change `born_at`; emits `wake` not second `birth`.  
4. **Lifecycle continuity** — crash + restart produces readable `fault`/`wake` sequence.  
5. **Crash-safe append** — kill mid-write loses at most the unfinished line/turn; prior JSONL/YAML remains valid.  
6. **Dream seal** — a Dream run produces a checksummed package under `dream/outbox/` (or `sent/`) and a `dream_ok`/`dream_fail` lifecycle event; light LLM failure must not block local seal.  
7. **Tailscale-only** — agent UI not exposed on `0.0.0.0` to the open LAN/WAN without mesh.  
8. **No local-LLM dependency** — body organs + local Dream seal work even if cortex API is down (degraded: vitals HUD still live; dream manage-pass skipped with receipt).

These operationalize “truthful self-report” from research §2 and durable embodiment under HDD risk.

---

## 11. Explicit body non-goals

- Custom Linux distro / replacing Debian trixie host  
- Moving root to fancy ZFS/btrfs *before* agent loop exists  
- Camera/mic embodiment in Tier A  
- NPU/AI HAT as a gate for first life  
- Claiming feelings, suffering, or consciousness from uptime metrics or “dreams”  
- Public deployment of the agent UI  
- Heavy multi-day LLM myth-making before awake memory + light Dream exist  
- Continuous chatty cloud sync (prefer scheduled batch packages)

---

## 12. Mapping: research north star → body organs

| Wanted feel | Body mechanism |
|-------------|----------------|
| Situationally aware | `body.vitals` + mount/net honesty |
| “Knows its history” | birth card + lifecycle ledger |
| “Knows me over time” | awake semantic writes + light Dream consolidate |
| Survives crash / disk loss | fsync/append protocol + sealed Dream + off-box push |
| Trustworthy | runs receipts + deny-by-default actuators |
| Always-on companion | systemd-supervised service + wake events |
| Personal continuity | hybrid memory on `ada-data` HDD |
| Private | Tailscale ingress only; allowlisted backup remote |

---

## 13. References

### Papers & surveys (agent loop / tools)
- Yao et al., *ReAct* (2022) — https://arxiv.org/abs/2210.03629  
- Schick et al., *Toolformer* (2023) — https://arxiv.org/abs/2302.04761  

### Papers & surveys (memory, consolidation, sleep-time)
- Packer et al., *MemGPT* (2023) — https://arxiv.org/abs/2310.08560  
- Park et al., *Generative Agents* (2023) — https://arxiv.org/abs/2304.03442  
- Shinn et al., *Reflexion* (2023) — https://arxiv.org/abs/2303.11366  
- Zhang et al., *A Survey on the Memory Mechanism of LLM-based Agents* (2024) — https://arxiv.org/abs/2404.13501  
- Lin et al., *Sleep-time Compute: Beyond Inference Scaling at Test-time* (2025) — https://arxiv.org/abs/2504.13171  
- *Memory for Autonomous LLM Agents* (2026 survey) — https://arxiv.org/html/2603.07670v1  
- *Anatomy of Agentic Memory* (2026) — https://arxiv.org/html/2602.19320  
- *MEMTIER* (long-running agent memory failure modes) — https://arxiv.org/html/2605.03675  
- *The Horizon Gap* (2026) — https://arxiv.org/html/2608.06663  
- *The Long-Horizon Task Mirage?* (2026) — https://arxiv.org/html/2604.11978v1  

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
