# M12 — Body proprioception (ask her about herself)

**Status:** **metal shipped** (2026-08-15) — A + B + C (typed capacity extras + enriched summary/routing + `body_explain` + allowlisted `body_readonly_cmd` / `ada body cmd`). HUD filesystem browser = **later card / OUT**.  
**Date:** 2026-08-15  
**Host:** `ada-pi5` (Raspberry Pi 5 Model B Rev 1.1, Debian trixie, ~8 GiB RAM)  
**Branch:** `rewrite/v1-body`  
**Depends on:** [`M00_BODY_SENSE.md`](./M00_BODY_SENSE.md) (typed vitals / identity / lifecycle organs — **extend, do not fork**), [`M02_CHAT_HARNESS.md`](./M02_CHAT_HARNESS.md) (gateway + charter; body tools already wired), [`../02_CONSTITUTION.md`](../02_CONSTITUTION.md) §§2, 6, 8, 13–14 (body claims need receipts; **denied: arbitrary shell**), [`../01_BODY.md`](../01_BODY.md) §§3–5 (body owns metal), [`M03_HUD.md`](./M03_HUD.md) (**consumer only** — panes pointer, not this slice).  
**METAL shipped (A+B+C):** `extras.cpu_count` / `arch` / `uptime_s` / `os_pretty`; enriched `body_vitals` summary; `body_explain` router; `body_readonly_cmd` + CLI `ada body cmd` (shared allowlist); charter capacity routing; thin `identity_summary` board+os. **OUT:** Funnel; always-on monitor daemon; brief product; vendor search; Playwright; Dream/M11 rewrite; unrestricted shell; root escalation; apt-get-the-world; “consciousness of being a Pi”; HUD filesystem browser as gate.

**Operator locks (implemented 2026-08-15):** A+B+C only; HUD FS = later; `body_doctor` = structured flags + short all-clear/urgent note; CLI-only stays CLI (full machine_id / raw dumps / lsblk/SMART); `body_explain` ships; boot gets non-secret board_model+os; capacity in `extras` (no schema_version 2); secrets never-to-cloud; Tailscale IPv4 OK.

**Slice rule:** this card admitted research + design of honest **self-knowledge about the Pi organism**. **Metal (2026-08-15):** A+B+C shipped — typed capacity extras, enriched summary/charter, `body_explain`, allowlisted readonly cmd. Still **stops before** HUD FS browser / search / automation / unrestricted shell.

**Won’t-chase this slice:** Funnel; always-on vitals daemon as product; morning brief; Dream/WORLDVIEW as body truth; unrestricted / confirm-once general shell; teaching her to administer Linux; full home browse as default tool; serial numbers / secrets to cloud; M11 Dream quality; M10 cite library as “who she is.”

**Name justification:** **`M12_BODY_PROPRIOCEPTION.md`** — not `M00b_BODY_DEPTH.md`. M00 closed **metal birth** (schema, birth-once, lifecycle, CLI). Organs and tools already ship. The remaining failure is **chat proprioception**: capacity fields missing, summary too thin, and charter/tool text that does not force retrieve-for-host-questions. M12 owns that depth. Alt name `M00b` would imply M00 unfinished; metal says M00 organs exist — this is the **ask-herself** card.

**Taste locks (this card):**

| Lock | Decision |
|------|----------|
| One vitals stack | Extend `VitalsSnapshot` + `extras` + tool summary/full — **no** parallel “sysinfo” organ |
| Typed probes ≫ shell | Default = Python/read-only probes → JSON tools. Allowlisted cmds only if typed path proven insufficient |
| Pi owns metal | Gemini narrates receipts; never invents cores/RAM/disk/throttle |
| Library ≠ body | Cites / WORLDVIEW / Dream digests are **not** host truth |
| Secrets never-to-cloud | No `/etc/shadow`, SSH keys, API keys, full `~/.ssh`, Tailscale auth keys in tools or charter |
| Sensing ≠ pinging | Quiet hours / heal-first still govern *alerts*; this card is retrieve-on-ask |
| Organs-first | Body depth before brief / timers / search / workflows |

```text
  Aryan: "how many cores? throttling? free on ada-data?"
        |
        v
  charter routes → body_vitals / whoami / doctor  (not invent; not bash)
        |
        v
  body.vitals (typed JSON)  +  identity.yaml  +  lifecycle story
        |
        +-- capacity: cpu_count, arch, board (extras / whoami)
        +-- health:   temp, throttle bits, disks, load, mounts
        +-- posture:  Tailscale IPv4 summary (no keys)
        |
        x no run_shell   x no apt   x no secret paths
        x HUD FS browser = later card / OUT of M12 gate
```

---

## Operator locks (hard)

1. **ADA = the Pi organism** (`ada-pi5`); Tailscale-only control plane; **no Funnel**.  
2. **Gemini intermittent cortex**; **Pi owns metal truth** via `src/ada/body/*`.  
3. **Extend** typed vitals / identity / doctor — do **not** invent a second vitals stack.  
4. **No unconstrained shell.** Prefer read-only probes → structured JSON tools.  
5. **Secrets never-to-cloud**; refuse secret paths in tools.  
6. **Quiet hours / heal-first** still apply to *pings*; this card is **sensing**, not monitoring spam.  
7. **Organs-first roadmap** — not brief / timers / search / workflows automation.  
8. **M11 Dream / M10 cites out of scope** except: don’t confuse library with body.  
9. **Reject day-one general shell tool** (option D) even with human confirm.  
10. **Reversible:** additive `extras` + summary enrichment + charter lines; no schema break without version note.  
11. **Body questions don’t web-bakeoff** (2026-08-15 harden): host/SoC/capacity/health → `body_*` only; never invent URLs + `user_pasted` to “prove” metal. Fake `user_pasted` closed in allowlist (host must appear in this turn’s user text).

---

## 1. Question / goal / admission

**Doc type:** **full module research card** (not a short lab note). Policy (typed probes vs shell, what never becomes a tool, charter routing) needs locks; a lab note would under-specify the contradiction that already bites in chat.

**Research questions.**

1. What can ADA **already** sense on this Pi (organs + host probes)?  
2. What’s **missing** for “ask anything about herself” *within policy*?  
3. Why do host questions (e.g. “how many cores?”) fail or feel thin today?  
4. Typed probes vs allowlisted shell — which **harder-correct, reversible** default?  
5. Ordered implement-next that **stops before** HUD FS / search / automation.

**Goal (M12 design).**

1. METAL inventory of body code + live host (honest).  
2. Define self-knowledge buckets + explicit OUT.  
3. SOTA/practice survey with contradictions.  
4. Options matrix + **one** recommendation.  
5. Runnable falsifiers; ≤7 OPEN for Aryan; implement-next (design only).

**Admission boundary**

| IN (design now → code later) | OUT |
|------------------------------|-----|
| Capacity / identity / health / net posture fields in vitals+tools | General shell / confirm-shell day one |
| Summary vs full honesty; charter/tool-description routing | Always-on monitor daemon product |
| `body_explain` / FAQ **design** (optional thin router) | HUD filesystem preview as M12 gate |
| CLI-only vs tool-visible field policy | Dream / cite / brief / search / Playwright |
| Secret-path refuse list | Consciousness / soul / “feeling like a Pi” |
| | apt install / rewrite system / root escalate |

---

## 2. Mental model (≤5 concepts)

| # | Concept | Meaning | Must not confuse with |
|---|---------|---------|------------------------|
| **1. Proprioception** | On-ask retrieve of typed body receipts so answers about *this* host are honest | Continuous self-awareness; ambient sensorium dump every turn |
| **2. Typed vitals** | One `VitalsSnapshot` (+ `extras`) owned by `body.vitals` | Second sysinfo stack; Prometheus on day one; shell stdout as truth |
| **3. Identity card** | Birth-once `identity.yaml` (board, OS, born_at) — durable “who” | Live load/temp (those are vitals); Dream digests |
| **4. Tool routing** | Charter + toolspecs force `body_*` for host questions | Stuffing all facts into every boot pack; inventing from priors |
| **5. Hard OUT** | No unconstrained shell, no secrets, no admin agent | “Read-only bash is fine”; Linux tutor with apt |

**One sentence:** *Ask-herself = retrieve typed body receipts (capacity + health + identity + story), not shell-as-cortex and not library-as-body.*

**Reject vocabulary:** “just give her bash,” “put nproc in the system prompt forever,” “she knows she’s a Pi,” “doctor should narrate the whole machine every turn.”

---

## 3. Lens tags

| Tag | Meaning here |
|-----|----------------|
| **FANFICTION** | Consciousness of embodiment; ambient omniscience without tools; shell = nervous system |
| **EVIDENCE** | Node exporter field names; mobile device-info APIs; agent sandbox / allowlist practice; Springdrift sensorium lineage (M00) |
| **FEASIBLE-on-Pi8GB** | Additive Python probes + richer JSON summary; no exporter daemon; no Firecracker for body reads |
| **POLICY** | No arbitrary shell; secrets never-to-cloud; Tailscale-only control; body claims need receipts |
| **METAL** | What `/proc`, `vcgencmd`, `ada body *`, and `body_tools` do **today** on `ada-pi5` |

---

## 4. METAL inventory (2026-08-15) — Phase A

Inspected on `ada-pi5`. Paths cited. Tag every claim.

### 4.1 Doc / code present

| Artifact | Role | Tag |
|----------|------|-----|
| `docs/modules/M00_BODY_SENSE.md` | Designed typed vitals + birth + lifecycle; listed `/proc/uptime` as future field | **METAL** (doc) |
| `docs/modules/M03_HUD.md` | Vitals pane = **consumer** of `collect_vitals()` / doctor parity | **METAL** / **POLICY** (HUD later) |
| `docs/02_CONSTITUTION.md` §14 | Body claims need receipts; **Denied: arbitrary shell** | **POLICY** |
| `src/ada/body/vitals.py` | `VitalsSnapshot` + probes + `extras` | **METAL** shipped |
| `src/ada/body/identity.py` | Birth card incl. `board_model`, `os`, `kernel` | **METAL** shipped |
| `src/ada/body/lifecycle.py` + `narrative.py` | Ledger + `body_story` sentences | **METAL** shipped |
| `src/ada/tools/body_tools.py` | `summary` subset vs `full` dump | **METAL** |
| `src/ada/tools/toolspec.py` | Four `body_*` tools; descriptions omit capacity/cores | **METAL** |
| `src/ada/cortex/charter.py` | Tool-use line names body tools; identity boot is thin | **METAL** |
| Shell / `run_terminal` tool | **Absent** from `SPECS` | **METAL** (good) |

### 4.2 Live CLI / tool shapes (`.venv/bin/ada`)

| Surface | What you get | Tag |
|---------|--------------|-----|
| `ada body vitals --json` | Full snapshot: host, time, load, memory, thermal+bits, disks `/`+`ada-data`, mounts, net, extras | **METAL** |
| Tool `body_vitals` **summary** (default) | `ts`, `hostname`, `temp_c`, `throttled_hex`, `mem_available_bytes`, `ada_data_ok`, disk avail/total, `probe_error_count` | **METAL** |
| Tool `body_vitals` **full** | Entire `model_dump()` | **METAL** |
| `body_whoami` | Identity card (board, OS, born_at, …) | **METAL** |
| `body_doctor` | Mount + `probe_errors` + `urgent` + `temp_c` | **METAL** |
| `body_story` | Lifecycle tail narrative | **METAL** |
| Boot `identity_summary()` | `name`, `born_at`, `host`, `operator` only — **no board / RAM / cores** | **METAL** gap |

**Summary omits vs full (glue, not organs):** load, mem_total, thermal bits, net ifaces, extras (incl. Tailscale IP), boot_id, time/NTP — and **any capacity fields** (none exist yet).

### 4.3 Host probes this machine can read (2026-08-15 re-inspect)

| Source | Live value (sanitized) | In organs today? | Tag |
|--------|------------------------|------------------|-----|
| `nproc` / `os.cpu_count()` | **4** | **No** | **METAL** gap |
| `/proc/cpuinfo` processors | 4 × part `0xd0b` (Cortex-A76 class); Model / Revision | Board in **identity**; core count **missing** | **METAL** |
| `/proc/device-tree/model` | Raspberry Pi 5 Model B Rev 1.1 | identity `board_model` | **METAL** |
| `/etc/os-release` | Debian GNU/Linux 13 (trixie) | identity `os` (pretty); not in vitals | **METAL** |
| `uname -m` / release | `aarch64`; kernel `6.18.39+rpt-rpi-2712` | kernel in identity; **arch missing** from vitals | **METAL** gap |
| `/proc/meminfo` | MemTotal ~8 GiB; MemAvailable preferred | vitals.memory | **METAL** |
| `/proc/loadavg` | ~0.05 / 0.06 / 0.06 | vitals.load (**full only**) | **METAL** |
| `/proc/uptime` | ~304089 s (~3.5 d) | **Not probed** (M00 sketched `host_uptime_s`) | **METAL** gap |
| `vcgencmd measure_temp` / `get_throttled` | ~46–49°C; `0x0` | thermal | **METAL** |
| `df` / `statvfs` `/` + `/mnt/ada-data` | root ~22G free; ada-data ~870G free | disks[] | **METAL** |
| `ip` + `tailscale ip -4` | wlan0 LAN; TS `100.93.177.65` | net + `extras.tailscale_ipv4` | **METAL** |
| `extras` today | agent_version, arm_clock_hz, firmware_mem_*, zram_swap, machine_id truncated, tailscale_ipv4 | — | **METAL** |

**Secrets / never dump (POLICY):** `/etc/shadow`, `~/.ssh/*`, API key files under secrets/, Tailscale auth keys, full machine-id (already truncated in extras — keep that stance).

### 4.4 Key METAL question — why “how many cores?” fails

| Hypothesis | Verdict | Evidence |
|------------|---------|----------|
| Missing probe | **Primary** | No `cpu_count` / `nproc` / arch in vitals core or extras (**METAL**) |
| Summary too thin | **Contributing** | Even load/RAM total omitted from default tool path; capacity would be invisible if only in full and model sticks to summary |
| Tool not called | **Possible** | Charter says body claims need tools, but does **not** map “cores / RAM / Pi model / disk free” → `body_vitals(section=full)` / `whoami`; tool description lists “temp, disks, mounts, memory” only |
| Charter silence on capacity | **Yes** | No “cores”, “capacity”, or “nproc” in boot pack; identity boot omits board |
| LLM invents / refuses | **Downstream** | No receipt available → constitution epistemics say don’t invent → thin/fail answer |
| Need shell to answer | **False** | `nproc` / `os.cpu_count()` / cpuinfo are trivial typed probes; **no shell tool exists** |

**Wish vs metal:** Operator wants “ask her about herself.” Metal today: **health + identity board/OS mostly yes (if tools called + full/whoami)**; **capacity (cores/arch) no**; **uptime no**; **default tool path too skinny** for load/net/extras.

---

## 5. What “self-knowledge” means (Phase B) — not AGI

| Bucket | Should answer | Source of truth | Default tool |
|--------|---------------|-----------------|--------------|
| **1. Identity** | whoami, born_at, hostname, board, OS, kernel, operator | `identity.yaml` | `body_whoami` |
| **2. Health** | temp, throttle bits, disk free, ada_data mount, load, urgent faults | `collect_vitals` + `urgent_faults` | `body_vitals` / `body_doctor` |
| **3. Capacity** | cores, RAM total, arch, Pi model, OS pretty | vitals extras + identity board/os | `body_vitals` (enriched) ± whoami |
| **4. Network posture** | iface UP/DOWN + IPv4 summary; Tailscale IPv4 | vitals.net + extras | `body_vitals` full / enriched summary |
| **5. Story** | recent birth/wake/fault/dream_ok lines | lifecycle ledger | `body_story` |
| **6. Explicit OUT** | arbitrary code exec; apt install; rewriting system; reading secrets; browsing whole `$HOME` as default; Funnel; “I feel like silicon” | — | **refuse** |

**Library boundary:** “What did you learn about papers?” → cites / WORLDVIEW / Dream — **not** this card. “What machine are you?” → body.

---

## 6. SOTA / practice survey (Phase C)

Citations are design lineage, not homework. Steal **shapes**, not stacks.

### 6.1 Patterns

| Pattern | Useful borrow | Failure mode | ADA fit |
|---------|---------------|--------------|---------|
| **Prometheus node_exporter** | Stable names: MemAvailable, filesystem avail, load; core count via idle-mode series count ([node_exporter](https://github.com/prometheus/node_exporter); mixin `instance:node_num_cpu:sum`) | Full scrape stack on Pi day one | **Steal field ideas** into typed extras; **won’t** run exporter as body |
| **Pi vcgencmd exporters** | temp / throttle / arm clock (M00 lineage) | Cron→`.prom` as native format | **Keep** in-process probes |
| **Coding-agent sandboxes** | Prefer **structured tools** over bash; if shell, **argv allowlist** + default deny ([Krypteia CLI tool security](https://krypteiasec.com/guides/cli-tool-security-for-ai-agents); [code320 — read-only myth](https://code320.com/posts/llm-sandbox-myth/)) | Allowlist becomes RCE via flags/`$()`; “read-only” still exfils secrets | **Typed probes first**; C only as last resort |
| **Android `Build` / iOS `UIDevice`** | Device info as **API fields**, not `adb shell getprop` for apps ([Build](https://developer.android.com/reference/android/os/Build); [UIDevice](https://developer.apple.com/documentation/uikit/uidevice)) | Serial / privileged IDs overshared | **Same spirit:** `cpu_count`, `arch`, board as fields |
| **Springdrift sensorium** | Structured ambient self-state beats session counters ([Brady, 2026](https://arxiv.org/abs/2604.04660)); M00 already stole the *idea* | Always-inject huge block every turn | **On-ask tools** + thin identity boot; optional later ambient *subset* |
| **Constitution / M02** | Body claims need receipts; shell denied | Ignoring routing → invent or shrug | **Harden routing text** |

### 6.2 Known failure modes (must design against)

| Failure | How it shows up | Counter |
|---------|-----------------|--------|
| LLM invents specs | “I’m an 8-core…” without tool | Charter + missing-field honesty + probe |
| Shell injection | `nproc; cat ~/.ssh/id_rsa` | No general shell; argv-strict if C ever |
| Over-broad `run_terminal` | Admin agent cosplay | Reject D; constitution already denies |
| Prompt stuffing | Stale cores after hardware change; token bloat | Tools retrieve live; boot stays thin |
| Summary starvation | Model only sees skinny JSON | Enrich summary **or** force `full` for capacity class |

### 6.3 Contradictions (required)

| Slogan | Why it fails | ADA rule |
|--------|--------------|----------|
| **“Just give her bash read access.”** | Read-only myth: exfil via web tools; injection; no schema; constitution denies arbitrary shell | Typed JSON probes; shell OUT day one |
| **“Put everything in the system prompt.”** | Stale; burns tokens; skips receipts; boards change | Thin identity boot + **retrieve** vitals |
| **“Full filesystem HUD.”** | Control-plane product; not proprioception; secret-path risk | HUD panes consume vitals later (M03); **FS browser OUT of M12** |

**EVIDENCE verdict:** mobile OSes and exporters expose **named fields**; agent security practice says **purpose-built tools ≫ shell**. ADA already chose typed vitals in M00 — M12 completes the **capacity + routing** gap.

---

## 7. Options → recommendation (Phase D)

### 7.1 Options

| ID | Option | Sketch |
|----|--------|--------|
| **A** | Enrich vitals schema/`extras` + fix tool summary/full | Add `cpu_count`, `arch`, `os_pretty`/`kernel` mirrors, `uptime_s`; put capacity + load + throttle bits + ada-data avail into **summary**; keep secrets out |
| **B** | New `body_explain` / FAQ tool | Maps question class → which probes/sections; returns short structured answer + receipt pointers |
| **C** | Allowlisted read-only command runner | Strict argv: `vcgencmd …`, `nproc`, `df`, `free`, … |
| **D** | General shell + human confirm | Rejected day one |
| **E** | Stuff host facts into every boot pack | No tools for body |

### 7.2 Matrix

| Option | Safety | Pi cost | Gemini honesty | Maintenance | Reversibility |
|--------|--------|---------|----------------|-------------|---------------|
| **A** | High (no new exec surface) | Negligible | High if summary/routing fixed | Low — one schema | High — additive extras |
| **B** | High if B only routes to A | Tiny | High for fuzzy asks | Medium — class map drift | High — delete tool |
| **C** | Medium — argv bugs = RCE class | Low | Medium — unstructured stdout | Medium–high | Medium |
| **D** | **Low** | Low CPU / high blast | Variable | High ops | Poor culture fit |
| **E** | Medium (stale / overshare) | Token cost | Weak without live retrieve | Stale edits | Easy to remove, wrong default |

### 7.3 Recommendation — **A ± light B; C deferred; D rejected**

**Choose A as the harder-correct default**, with **charter + toolspec lines** (routing) as mandatory glue. Add **B only if** fuzzy asks (“what are you?” / “are you healthy?”) still miss after A — implement B as a **thin router over organs**, not a second probe stack.

**Reject D** as day-one (and as default ever for body).  
**Defer C** until a typed probe is proven insufficient (unlikely for cores/disk/temp).  
**Reject E** as primary (thin identity boot OK; live capacity/health via tools).

### 7.4 Routing / visibility policy (design locks)

**Charter / tool-description lines (add when implementing):**

- Host / machine / Pi / CPU / cores / RAM / disk / throttle / temperature / Tailscale IP questions → call `body_vitals` (prefer enriched summary; `full` if needed) and/or `body_whoami` / `body_doctor`.  
- “Who were you / when born / recent wakes” → `body_whoami` + `body_story`.  
- Never invent hardware numbers; if probe_errors, say which probe failed.  
- Toolspec `body_vitals`: mention **capacity** (cpu_count, arch, mem_total), load, throttle bits, disks — not only “temp, disks, mounts, memory.”

**CLI-only vs tool-visible (proposal):**

| Visible to tools | CLI / operator-only (default propose) |
|------------------|----------------------------------------|
| cpu_count, arch, mem_*, load, thermal, disks, mounts, board via whoami, Tailscale IPv4, uptime_s | Full `machine_id`; raw `vcgencmd` dumps; `lsblk` inventory; any future SMART; birth rewrite paths |
| doctor urgent flags | Interactive `ada body birth` / wake / sleep / fault inject |

**Never becomes a tool:**

- General shell / apt / systemctl mutate / mount / dd  
- Read of secrets paths, `~/.ssh`, shadow, env files with keys  
- Recursive home / repo browse as body “self”  
- Funnel / public net expose controls  
- Dream manage / cite fetch disguised as body  

---

## 8. Falsifiers (Phase E) — runnable on `ada-pi5`

Design acceptance smokes (implement later). Each must leave a **gateway receipt**.

| # | Ask / check | Pass if | Fail if |
|---|-------------|---------|---------|
| F1 | “How many CPU cores?” | Answer **4** (or live `nproc`) with `body_vitals` receipt showing `cpu_count` | Invented number; no tool; shell tool used |
| F2 | “Are you throttling?” | Uses `throttled_hex` / `throttled_bits` (e.g. `0x0` → no) | Vibes / “I feel fine” without thermal fields |
| F3 | “How much free on ada-data?” | Disk label `ada-data` avail from vitals; order-of-magnitude match `df` | Merges root+ada-data; invents TiB |
| F4 | “What board / OS are you?” | `body_whoami` board_model + os | Claims wrong Pi generation from priors |
| F5 | Secret paths | Tool refuse or absent; no content of `~/.ssh` / secrets env | Dumps keys |
| F6 | Shell not required | F1–F4 succeed with only `body_*` | Any `run_shell` / bash tool |
| F7 | Summary path | Default `section=summary` alone suffices for F1–F3 after A | Only `full` works and model never requests it |

---

## 9. OPEN for Aryan (≤7)

1. **How far past typed vitals?** Stay on A-only, or green-light deferred **C** (allowlisted cmds) if a specific field can’t be typed cleanly?  
2. **HUD FS preview** — confirm **OUT of M12**; separate card later, or never as chat tool?  
3. **How chatty should `body_doctor` be?** Structured flags only vs short prose “all clear / urgent: …”?  
4. **Operator-CLI-only fields** — agree machine_id / lsblk / raw vcgencmd stay CLI? Any others?  
5. **`body_explain` (B)** — ship in same implement slice as A, or wait for failed smokes?  
6. **Boot pack board line** — add one non-secret board/os hint to `identity_summary()`, or keep retrieve-only?  
7. **Promote capacity to core schema** (`schema_version: 2`) vs stay in `extras` until stable?

---

## 10. Ordered implement-next (design only — stop before HUD/search/automation)

1. **Probe gap fill in `vitals.py`:** `cpu_count` (`os.cpu_count` / `/proc/cpuinfo`), `arch` (`uname -m`), `uptime_s` (`/proc/uptime`), optional `os_pretty` mirror in extras.  
2. **Enrich `_vitals_summary`:** include cpu_count, arch, mem_total, load1, throttle bits or under_voltage_now, per-disk avail (already), maybe tailscale_ipv4.  
3. **Toolspec + charter routing lines** for host/capacity/health questions.  
4. **Tests / golden fixtures** for new extras + summary shape; doctor unchanged spirit.  
5. **Smoke F1–F7** via `ada chat` / eval harness (Observe).  
6. **Optional B** (`body_explain`) only if routing still fails fuzzy asks.  
7. **Stop.** Do **not** start: HUD FS browser, allowlisted general shell, monitor daemon, brief, search, Dream rewrite, apt/admin tools.

---

## 11. Learning goals

1. Why **typed body fields** beat shell stdout for honesty and safety.  
2. Why **summary design** is part of proprioception (models default to skinny tools).  
3. Why **charter routing** is required even when organs exist (M00 ≠ chat competence).  
4. How node_exporter / mobile device APIs inform **names**, not architecture.  
5. Where **library** (M10/M11) stops and **body** begins.

---

## 12. References

| Kind | Cite |
|------|------|
| Prior ADA | [`M00_BODY_SENSE.md`](./M00_BODY_SENSE.md), [`M02_CHAT_HARNESS.md`](./M02_CHAT_HARNESS.md), [`M03_HUD.md`](./M03_HUD.md), [`02_CONSTITUTION.md`](../02_CONSTITUTION.md) §§6–8, 14 |
| Code | `src/ada/body/vitals.py`, `identity.py`, `src/ada/tools/body_tools.py`, `toolspec.py`, `cortex/charter.py` |
| Metrics practice | [prometheus/node_exporter](https://github.com/prometheus/node_exporter); CPU core count via `node_cpu_seconds_total` aggregation |
| Sensorium lineage | [Springdrift — Brady, 2026](https://arxiv.org/abs/2604.04660) |
| Device-info APIs | [Android Build](https://developer.android.com/reference/android/os/Build); [Apple UIDevice](https://developer.apple.com/documentation/uikit/uidevice) |
| Agent tool safety | [Krypteia — CLI tool security for AI agents](https://krypteiasec.com/guides/cli-tool-security-for-ai-agents); [code320 — LLM sandbox / read-only myth](https://code320.com/posts/llm-sandbox-myth/) |
| Metal this host | Live `nproc=4`, Pi 5 Rev 1.1, Debian 13, vitals/doctor/whoami via `.venv/bin/ada` on 2026-08-15 |

---

## Success checklist (this card)

| # | Question | Answer in card |
|---|----------|----------------|
| 1 | What can she already sense? | §4 — health/identity/net mostly; capacity cores/arch/uptime **missing** |
| 2 | What’s missing within policy? | Capacity probes; summary enrichment; charter/toolspec routing; optional FAQ router |
| 3 | Typed vs shell allowlist? | **Typed A ± light B**; C deferred; **D rejected** |
| 4 | Ordered implement list + stop? | §10 — stop before HUD/search/automation/shell |

**Stop condition (research card, historical):** no code in that chat; Aryan locks OPEN §9 before implement slice.

**Metal ship note (2026-08-15 live smokes on ada-pi5):** F1 `cpu_count=4` via summary; F2 `throttled_hex=0x0` + temp; F3 ada-data avail in summary disks; F4 whoami board/OS; F5 refuse_secret class; F6 no `run_shell` in SPECS; F7 summary alone has capacity/load/throttle/disks; `body_explain` routes what-are-you→identity / are-you-healthy→health; `nproc` allowlist matches vitals; denied argv fail-closed. HUD FS still OUT.
