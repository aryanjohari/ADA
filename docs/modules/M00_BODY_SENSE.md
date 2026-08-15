# M00 — Body Sense (vitals · identity · birth / wake lifecycle)

**Status:** module research card (**doc-only** origin) — organs shipped; capacity/chat proprioception → [`M12_BODY_PROPRIOCEPTION.md`](./M12_BODY_PROPRIOCEPTION.md).  
**Date:** 2026-08-12  
**Host:** `ada-pi5` (Raspberry Pi 5 Model B Rev 1.1, Debian trixie)  
**Branch:** `rewrite/v1-body`  
**Depends on:** [`../01_BODY.md`](../01_BODY.md) §§1–6 & §10, [`../02_CONSTITUTION.md`](../02_CONSTITUTION.md) §§2, 6, 8, 13, 16, [`../00_ASSISTANT_RESEARCH.md`](../00_ASSISTANT_RESEARCH.md) §8  

**Slice rule:** this card admits **metal birth** — first `identity.yaml`, crash-safe lifecycle ledger, typed vitals organ, package + CLI scaffold design, and proof plan. It does **not** admit Dream/WORLDVIEW/Gemini, HUD/HTTP, Tailscale Serve, or chat cortex. For cores/arch/summary routing / `body_explain` / allowlisted readonly cmd see **M12**.

---

## 1. Question / goal / slice admission boundary

**Question.** How does ADA become a **grounded body** on this Pi — knowing *who she is*, *when she was born*, *that she woke*, and *what the metal currently reports* — without inventing feeling, Dream meaning, or cloud thoughts?

**Goal (M0 body organs).**

1. Define a **stable typed vitals schema** (+ extensible `extras`) from what this host can actually read.  
2. Define **first-write identity / birth** (`born_at` once) + **append-only lifecycle** events that are a simple lasting autobiography (birth / wake / fault / …).  
3. Specify **crash-safe write protocol** on `/mnt/ada-data` (ext4 HDD) and refusal rules when the mount is missing.  
4. Propose a **Python package + no-Gemini CLI** so organs are not forever-loose scripts.  
5. Specify **acceptance smokes (body §10 subset)** and **pytest** automated tests — production-minded for a personal lab.

**Admission boundary (in / out)**

| IN this slice (design now → code next) | OUT (later; same ledger OK) |
|----------------------------------------|-----------------------------|
| `body.vitals` reads | Gemini / any LLM cortex |
| `body.identity` + birth once | Dream seal / manage-pass / push |
| `lifecycle.append` v0 event set | WORLDVIEW digests / FACT merges beyond identity |
| Package under `src/ada/…` + CLI status/birth | HUD / HTTP / Tailscale Serve |
| Crash-safe IO + torn-line recovery | `runs/` chat transcripts as product |
| Manual smokes + pytest | systemd forever-service as gate (design pointer only) |
| Mount honesty hard-fault | Voice, camera, HA, embeddings |

**METAL snapshot (2026-08-12 re-inspect, readonly):**

| Fact | Value |
|------|--------|
| Hostname | `ada-pi5` |
| Board | Raspberry Pi 5 Model B Rev 1.1 (`Revision d04171`) |
| OS / kernel | Debian 13 (trixie); `6.18.39+rpt-rpi-2712` aarch64 |
| RAM / swap | ~7.9 GiB; 2.0 GiB zram swap |
| Temp / throttle | `vcgencmd measure_temp` ~47.7°C; `throttled=0x0` |
| Root | USB `rootfs` ext4 ~28G, ~22G free |
| Durable substrate | HDD `ada-data` → `/mnt/ada-data` ext4 ~916G, ~870G free |
| Tree present | `ADA/`, empty `memory/`, `runs/`, `scratch/` (no `dream/` yet) |
| Net | `wlan0` UP DHCP `192.168.7.134/22`; `eth0` DOWN; `tailscale0` present (`100.93.177.65`) |
| Time | `Pacific/Auckland`; NTP synchronized; HW RTC |
| Python | 3.13.5; PyYAML + Rich present; pydantic/pytest **not** installed yet |
| Sensors extras | `vcgencmd` present; `lm-sensors` / moreutils `ts` **absent** |

---

## 2. Lens tags

| Tag | What it means here |
|-----|--------------------|
| **METAL** | Probes runnable on `ada-pi5` today (`/proc`, `vcgencmd`, `df`, mounts, net link) |
| **EVIDENCE** | Agent memory / lifecycle literature; host-metrics practice; crash-safe FS protocols |
| **FEASIBLE** | Pure Python (+ tiny deps) on Pi 5 8GB; no Prometheus stack required for v0 |
| **POLICY** | Body owns clocks/disks/logs; truth = receipts; Dream/cortex out of scope; Tailscale is access ring only |
| **FANFICTION** | “She woke up and remembered her childhood” — **rejected**. Birth = first durable card write; wake = process start receipt |

---

## 3. What “birth” means here vs Dream / awareness later

### 3.1 Engineering birth (this card)

**Birth** = the **first successful write** of `/mnt/ada-data/memory/facts/identity.yaml` while `ada-data` is mounted, plus a single lifecycle line `type: birth`.

- `born_at` is ISO-8601 UTC (store with explicit `Z` or offset).  
- Second process start → **`wake`**, never a second `birth`.  
- Narration allowed later: “I was born at … on host ada-pi5” **only** if card + ledger agree.  
- No consciousness, no REM, no invented outages ([constitution §2](../02_CONSTITUTION.md)).

### 3.2 Wake vs Dream vs “awareness”

| Concept | Meaning in ADA | This slice |
|---------|----------------|------------|
| **Wake** | Supervised process start → append `wake` with version + boot_id | **IN** |
| **Sleep / stop** | Clean shutdown → `sleep` | **IN** (emit API; systemd later) |
| **Fault** | Mount missing, OOM-kill observed, crash marker, disk critically low, sustained throttle | **IN** (detection subset; heal_* skeleton) |
| **Dream** | Offline consolidate + seal (+ later Gemini manage) | **OUT** — later attaches `dream_*` to **same** ledger |
| **WORLDVIEW** | Interpretive digests citing FACTS | **OUT** |
| **Ambient sensorium** (Springdrift-class prompt inject) | Always-on structured self-state each cortex cycle | **OUT for code**; schema here **is** the future receipt source |

**EVIDENCE (lineage, not cosplay).** Generative Agents treat autobiography as an **append-only memory stream** of observations, with reflection as a *later* manage pass ([Park et al., 2023](https://arxiv.org/abs/2304.03442)). Memory surveys call this write–manage–read; **manage** is often neglected ([Zhang et al., 2024](https://arxiv.org/abs/2404.13501); [*Memory for Autonomous LLM Agents*, 2026](https://arxiv.org/html/2603.07670v1); [*Memory in the Age of AI Agents*, 2025/26](https://arxiv.org/abs/2512.13564)). Springdrift’s **sensorium** shows the value of structured ambient host/self state without tool round-trips ([Brady, 2026 — Springdrift](https://arxiv.org/abs/2604.04660)) — ADA steals the *idea* (typed vitals block), not the OTP/XML runtime.

```text
  [metal probes] --> body.vitals (typed JSON)
  [first boot]   --> identity.yaml + lifecycle birth
  [every start]  --> lifecycle wake
  [crashes]      --> lifecycle fault (+ later heal_*)
        |
        v
  SAME ledger later receives dream_ok / dream_fail  (NOT this slice)
        |
        v
  Cortex / HUD consume receipts  (NOT this slice)
```

---

## 4. Prior art — Feasible on Pi

### 4.1 Host agents & metrics shapes

| Source | Useful borrow | Won’t copy blindly |
|--------|---------------|--------------------|
| **Prometheus Node Exporter** | Stable names for CPU/mem/fs/net; prefer **MemAvailable** over MemFree; expose filesystem **avail bytes** ([Node Exporter guide](https://prometheus.io/docs/guides/node-exporter/)) | Full Prometheus + scrape stack on day one |
| **Pi textfile / vcgencmd exporters** | Temperature, ARM clock, throttle flags via `vcgencmd` ([raspberrypi_exporter pattern](https://github.com/fahlke/raspberrypi_exporter)) | Cron→`.prom` file as ADA’s native format |
| **OpenTelemetry host + agent observ.** | Separation of host metrics vs agent spans ([OTel AI agent observ.](https://opentelemetry.io/blog/2025/ai-agent-observability/)) | OTLP exporter requirement for v0 |
| **Springdrift sensorium** | Ambient structured self-state; history-backed vitals beat session counters ([arXiv:2604.04660](https://arxiv.org/abs/2604.04660)) | Gleam/OTP port; injecting into Gemini yet |

### 4.2 Agent lifecycle logs

| Source | Useful borrow | Won’t chase |
|--------|---------------|-------------|
| **Generative Agents memory stream** | Timestamped append-only observations ([Park 2023](https://arxiv.org/abs/2304.03442)) | Embedding importance scoring day one |
| **Agent Lifecycle Protocol (ALP)** | Named transitions: genesis ≈ birth; failed/suspend ([ALP whitepaper / store.py JSONL](https://github.com/alexfleetcommander/agent-lifecycle-protocol)) | Reputation inheritance, fork/succession contracts |
| **AIP-37-style event taxonomies** | Explicit envelope: id, type, ts, payload | Full multi-workspace bus |
| **OpenAI Agents lifecycle hooks** | `agent_start` / `agent_end` as process boundaries | JS runtime coupling |
| **Promptise / durable journals** | Crash recovery from durable journal | Multi-agent cluster runtime |

**ADA twist (POLICY):** lifecycle is **body autobiography**, not enterprise agent HR. Event set stays small, greppable, narratable — Dream/WORLDVIEW later *read* it; they must not rewrite it.

### 4.3 Crash-safe append / fsync / rename

| Practice | Contract |
|----------|----------|
| **Atomic replace** | write temp → `fsync` file → `rename` → `fsync` parent dir ([SQLite atomic commit notes](https://www.sqlite.org/atomiccommit.html); POSIX rename atomicity) |
| **Append journals** | append frames → `fsync` (or periodic group-commit); on restart, **truncate/skip torn last line** |
| **USB-root risk** | identity + lifecycle live on **HDD** `ada-data`, not only root stick (body §1.3.1) |

**FEASIBLE on Pi 5:** Python `os.fsync` / `os.replace` on ext4 HDD is enough for Tier A; SQLite WAL optional later (body §6.2).

---

## 5. METAL inventory — probes this machine can actually run

All probes below are **readonly** and verified present or explicitly absent on 2026-08-12.

### 5.1 Probe → vital field map

| Probe (readonly) | Feeds | Notes |
|------------------|-------|-------|
| `hostname` / `hostnamectl` | identity + vitals.host | |
| `/proc/device-tree/model` or `/proc/cpuinfo` Model/Revision | identity.board_* | Serial **omit** from durable public docs; may store hashed later if needed |
| `/etc/os-release` + `uname -r` | identity.os / kernel | |
| `timedatectl` / tz via `zoneinfo` | vitals.time | NTP sync boolean |
| `/proc/uptime` | vitals.host_uptime_s | |
| `/proc/loadavg` | vitals.load | 1/5/15 |
| `/proc/meminfo` | vitals.memory | Prefer MemAvailable + MemTotal + Swap* |
| `/proc/stat` (optional) | extras.cpu_* | Soft freqs / idle deltas — extras for now |
| `vcgencmd measure_temp` | vitals.thermal.temp_c | Primary Pi path |
| `/sys/class/thermal/thermal_zone0/temp` | vitals.thermal.temp_c fallback | millidegC / 1000 |
| `vcgencmd get_throttled` | vitals.thermal.throttled_hex + flags | Parse bits; `0x0` = clean |
| `vcgencmd measure_clock arm` | extras.arm_clock_hz | Pi-specific |
| `vcgencmd get_mem arm|gpu` | extras.firmware_mem | Informative split |
| `df` / `os.statvfs` on `/` and `/mnt/ada-data` | vitals.disks[] | Separate roots — never merge |
| `findmnt` / `/proc/mounts` | vitals.mounts.ada_data_ok | **Hard honesty gate** |
| `lsblk` / by-label | extras.block_devices | Role labels: rootfs / ada-data |
| `ip -br link/addr` | vitals.net.ifaces[] | operstate, IPv4 summary; **no** secret keys |
| `tailscale ip -4` (if CLI present) | extras.tailscale_ipv4 | Access ring metadata only |
| `/proc/sys/kernel/random/boot_id` | lifecycle wake details | Correlate wakes within same boot |
| `/etc/machine-id` | extras.machine_id | Stable host id; treat as local |
| `swapon --show` / `/proc/swaps` | vitals.memory.swap + extras.zram | |

### 5.2 Explicitly absent / optional

| Thing | Status | Schema stance |
|-------|--------|---------------|
| `lm-sensors` (`sensors`) | **not installed** | Do not require |
| moreutils `ts` | **not installed** | CLI can format times in Python |
| Mic / camera | not on USB inventory | out of body sense |
| SMART via `smartctl` | not assumed installed | `extras` later if added |
| `node_exporter` daemon | not running | won’t require |

### 5.3 Honesty rules (POLICY + METAL)

1. If `/mnt/ada-data` is **not** mounted → vitals report `ada_data_ok=false`; **refuse** identity birth and lifecycle append; emit in-memory / stderr fault only (no fake success).  
2. If `vcgencmd` fails → set thermal fields null + error in `probe_errors[]`; still return other vitals.  
3. Never invent disk free or throttle bits from LLM / banter.

---

## 6. Options compared → chosen design

### 6.1 Comparison

| Option | Accurate? | Stable schema? | Teach? | Ops burden | Verdict |
|--------|-----------|----------------|--------|------------|---------|
| Shell one-liners forever | Yes if careful | No | Weak | High drift | Shortcut — reject |
| Shell out every probe, unstructured JSON | Yes | Fragile | Medium | Medium | Temporary only |
| Full Prometheus + Grafana | Excellent | External | High ops | Heavy for lab | **Won’t-chase v0** |
| SQLite vitals history TSDB | Strong | Strong | High | Premature | Later optional |
| **Typed Pydantic (or dataclass) snapshot + extras** | Yes | **Yes** | High | Low | **Chosen** |
| Loose `MEMORY.md` autobiography | Narrative only | No metal truth | Tempting | Lies easily | Reject for birth/wake |

| Lifecycle layout | Pros | Cons | Verdict |
|------------------|------|------|---------|
| **Single `memory/lifecycle.jsonl`** | Simplest greppable autobiography; one fsync path; matches body default | Large-file grow later | **Chosen v0** (operator: researcher’s call) |
| `events/YYYY/MM.jsonl` from day one | Natural sharding | More code before first wake; narrative join cost | **Defer** — rotate *into* this later as manage job |
| SQLite event table | Query power | Heavier; teach FS protocol first | Later index optional |

**Harder-but-correct vs shortcut**

| Shortcut | Harder-correct (chosen) |
|----------|-------------------------|
| `echo born > born.txt` | Typed `identity.yaml` + immutable `born_at` |
| Print `vcgencmd` raw in CLI only | Stable schema + Pi `extras` |
| Rewrite identity on every boot | Birth once; wake forever after |
| Skip fsync “it’s only a lab” | tmp→fsync→rename + torn-line recovery (**USB power cuts are real here**) |
| Loose scripts in `scratch/` | Installable package `src/ada/` |

### 6.2 Paths under `/mnt/ada-data` (chosen)

```text
/mnt/ada-data/
  ADA/                          # git repo (code) — wipe≠erase autobiography
  memory/
    facts/
      identity.yaml             # birth card (atomic replace writes)
    lifecycle.jsonl             # append-only autobiography (v0)
    # later: worldview/, dreams/, facts/*.yaml …
  runs/                         # later: session transcripts (out of M0 code duty)
  dream/                        # later: staging/outbox/sent
  scratch/                      # disposable
```

Create `memory/facts/` on first birth if missing. Do **not** invent WORLDVIEW files in this slice.

### 6.3 Schema sketch — vitals (stable core + extras)

**Version the document:** `schema_version: 1`. Additive fields go in `extras` first; promote to core only with a version bump + migration note.

```yaml
# Logical shape of body.vitals snapshot (JSON in code; YAML OK for golden fixtures)
schema_version: 1
ts: "2026-08-12T21:29:45Z"          # UTC capture time
host:
  hostname: ada-pi5
  boot_id: "…"                       # from /proc/sys/kernel/random/boot_id
time:
  timezone: Pacific/Auckland
  utc_offset: "+12:00"
  ntp_synchronized: true
load:
  load1: 0.10
  load5: 0.12
  load15: 0.14
memory:
  mem_total_bytes: 8454012928
  mem_available_bytes: 7581286400    # prefer Available, not Free
  swap_total_bytes: 2147483648
  swap_used_bytes: 0
thermal:
  temp_c: 47.7                       # null if both probes fail
  temp_source: vcgencmd              # or thermal_zone0 | null
  throttled_hex: "0x0"
  throttled_bits:                    # decoded convenience; hex remains source of truth
    under_voltage_now: false
    freq_capped_now: false
    throttled_now: false
    soft_temp_limit_now: false
    # … sticky counterparts as needed
  under_voltage_now: false           # denormalized urgent flags for HUD/alerts
disks:
  - mount: /
    label: rootfs
    fstype: ext4
    total_bytes: …
    used_bytes: …
    avail_bytes: …
    used_pct: …
  - mount: /mnt/ada-data
    label: ada-data
    fstype: ext4
    total_bytes: …
    used_bytes: …
    avail_bytes: …
    used_pct: …
mounts:
  ada_data_ok: true
  ada_data_source: /dev/sda1
net:
  ifaces:
    - name: wlan0
      operstate: UP
      ipv4: ["192.168.7.134/22"]
    - name: eth0
      operstate: DOWN
      ipv4: []
    - name: tailscale0
      operstate: UNKNOWN             # WireGuard often reports UNKNOWN; IP still useful
      ipv4: ["100.93.177.65/32"]
probe_errors: []                     # [{probe, message}]
extras:                              # extensible — do not redesign core for every Pi quirk
  arm_clock_hz: 2400000000
  firmware_mem_arm_m: 1020
  firmware_mem_gpu_m: 4
  zram_swap: true
  machine_id: "2b049a78…"            # local only
  tailscale_ipv4: "100.93.177.65"    # optional convenience
  agent_version: "0.0.0+body"        # from package metadata when present
```

**Urgent-fault helpers** (compute from snapshot; align body §6.9):  
`ada_data_ok == false` · root or ada-data `avail` below threshold (config; suggest 1 GiB root / 5 GiB ada-data start) · `throttled` *now* bits set.

### 6.4 Schema sketch — identity (birth card)

Path: `/mnt/ada-data/memory/facts/identity.yaml`

```yaml
schema_version: 1
name: ADA
pronouns: she/her
operator: Aryan
born_at: "2026-08-12T…"          # IMMUTABLE after first write
body_hostname: ada-pi5
board_model: "Raspberry Pi 5 Model B Rev 1.1"
board_revision: d04171
os: "Debian GNU/Linux 13 (trixie)"
kernel: "6.18.39+rpt-rpi-2712"
timezone: Pacific/Auckland
cortex_primary: gemini            # declared intent; cortex not required for birth
voice_charter: witty_full_stage
version: "0.1.0"                  # package version at birth; deploy events track later bumps
# Do NOT put API keys here.
```

**First-boot rule:** if missing and mount OK → write once + lifecycle `birth`. If present → never change `born_at` (even if hostname drifts — record drift as `note` / `deploy` details instead).

### 6.5 Lifecycle events — v0 set vs waits

**Envelope (every line):**

```json
{
  "schema_version": 1,
  "id": "01J…", 
  "ts": "2026-08-12T21:30:00Z",
  "type": "wake",
  "summary": "ada body service start",
  "details": {"agent_version": "0.1.0", "boot_id": "…", "pid": 1234},
  "receipts": {}
}
```

Use ULID or UUID4 for `id`. One JSON object per line.

| `type` | When | v0? |
|--------|------|-----|
| `birth` | First identity write | **Yes** |
| `wake` | Process / service start | **Yes** |
| `sleep` | Clean stop | **Yes** |
| `fault` | Mount missing, crash marker, disk critical, throttle-now, uncaught abort path | **Yes** |
| `heal_retry` / `heal_ok` / `heal_give_up` | Overnight recovery skeleton | **Yes emit API**; heuristics can be minimal |
| `deploy` | Package version change detected vs identity or last wake | **Yes** (compare versions) |
| `note` | Rare human/agent milestone | **Yes** (CLI) |
| `dream_ok` / `dream_fail` | Dream organ | **Wait** — same file later |
| `config_change` | Material config edits | **Wait** or rare `note` |
| ALP fork/succession/migrate | Multi-agent HR | **Won’t-chase** |

**Narrative contract:** a readable autobiography is `birth` → many `wake`/`sleep` → occasional `fault`/`heal_*`/`deploy`. CLI `ada body story` (or `status --story`) prints the last N events as plain sentences from ledger only.

---

## 7. Crash-safe write protocol

### 7.1 Two writers

| Store | Pattern |
|-------|---------|
| `identity.yaml` (replace) | Write `identity.yaml.tmp.<pid>` → full bytes → `flush` + `os.fsync` → `os.replace` → `fsync` parent dir `facts/` |
| `lifecycle.jsonl` (append) | `open(…, "a")` → write one line ending `\n` → `flush` + `fsync` file (group-commit optional later) |

### 7.2 Start-up recovery

1. If `ada-data` missing → **no writes**; return structured fault; nonempty exit code for CLI.  
2. If `identity.yaml.tmp.*` left behind → ignore/delete temps; never promote without successful protocol.  
3. If last `lifecycle.jsonl` line fails `json.loads` → emit `fault` with `details.reason=torn_line` (to stderr / in-memory if append also impossible), **skip** bad line, continue. Prefer truncate only the incomplete trailing line after length check — never rewrite history.  
4. Bound loss: at most the **current unfinished line**, not the file.

### 7.3 Concurrency (v0)

Single-writer assumption: one body CLI/service. Optional `fcntl.flock` on lifecycle later if HUD + service co-exist. Document: do not hand-edit JSONL mid-flight.

### 7.4 Power note (METAL lesson)

Outlet / dirty cut hurts USB root **and** unfinished HDD buffers. Protocol does not fix lying USB sticks; it bounds software-visible corruption. Keep autobiography on HDD; keep Pi on always-on power (M01 ops).

---

## 8. Package / CLI layout proposal

### 8.1 Package layout (chosen)

```text
ADA/
  pyproject.toml                 # package ada; entrypoint ada
  src/
    ada/
      __init__.py                # __version__
      py.typed
      body/
        __init__.py
        vitals.py                # probe + VitalsSnapshot
        identity.py              # read/create birth card
        lifecycle.py             # append + tail + parse
        narrative.py             # ledger → simple sentences (no LLM)
      io/
        __init__.py
        atomic.py                # replace + fsync helpers
        paths.py                 # ADA_DATA root resolution
      cli/
        __init__.py
        main.py                  # typer or argparse
  tests/
    test_vitals_schema.py
    test_identity_birth_once.py
    test_lifecycle_append.py
    test_atomic_io.py
    fixtures/
      …                          # golden vitals JSON; fake mounts via tmp_path
  scripts/
    smoke_body.sh                # manual acceptance driver (optional)
```

**Deps (recommend):**

| Dep | Why |
|-----|-----|
| PyYAML | already on host; identity card |
| pydantic ≥2 | typed vitals/identity (install) |
| typer or argparse | CLI; Typer nicer UX if we accept dep |
| pytest | automated tests (install) |
| rich | already present; pretty status |

No Gemini SDK. No network client required for body sense.

**Data root:** default `/mnt/ada-data`; override `ADA_DATA_ROOT` for tests.

### 8.2 CLI UX (no Gemini) — recommend

Binary name: **`ada`** (console script).

```text
ada body status          # vitals summary + identity born_at + last wake/fault (human)
ada body status --json   # machine snapshot
ada body vitals          # vitals only
ada body whoami          # identity card (error if missing)
ada body birth           # create identity once if missing; idempotent message if exists
ada body wake            # append wake (also called by future systemd ExecStartPost / service)
ada body sleep           # append sleep
ada body fault --summary "…"   # manual / test fault
ada body story [-n 20]   # plain autobiography from ledger (receipts only)
ada body doctor          # mount + probe_errors + urgent flags (exit ≠0 if hard fault)
```

**UX principles:**  

1. Human default; `--json` for scripts.  
2. `birth` is explicit so first life is intentional (also callable from first `wake` if `--ensure-birth`).  
3. `story` never invents — if ledger empty, say so.  
4. Exit codes: `0` ok; `2` soft degrade (probe miss); `3` hard body fault (no ada-data).

---

## 9. Test + smoke plan

### 9.1 Automated (pytest) — must ship with first code

| Test | Asserts |
|------|---------|
| `test_vitals_schema_roundtrip` | Snapshot validates; extras open for unknown keys |
| `test_vitals_prefers_mem_available` | Fixture meminfo → available not free-as-total-lie |
| `test_mount_missing_refuses_writes` | Fake root without ada-data → birth/append raise/deny |
| `test_birth_once` | Second `create_identity` keeps `born_at` |
| `test_wake_not_birth_when_identity_exists` | Sequence birth, wake, wake |
| `test_atomic_replace_survives_partial_tmp` | Kill-style leave tmp; reader still sees old/new consistent |
| `test_lifecycle_skips_torn_line` | Truncated last line ignored; prior lines readable |
| `test_lifecycle_append_fsync_contract` | Mock/spy that fsync path invoked (unit) |
| `test_throttled_parse` | Known hex vectors → flags |
| `test_narrative_uses_only_ledger` | story() output ⊆ event summaries |
| `test_cli_status_json` | CliRunner / subprocess `--json` parses |

Use `tmp_path` as `ADA_DATA_ROOT`. Optionally monkeypatch probe functions with fixtures captured from this Pi (sanitize serials).

### 9.2 Manual smokes (body §10 subset for M0)

Map to body acceptance; Dream/Tailscale/HUD items stay unchecked until those organs.

| # | Smoke | Pass look |
|---|-------|-----------|
| 1 | Mount honesty | Unmount simulation / wrong `ADA_DATA_ROOT` → refuse writes; `doctor` ≠0 |
| 2 | Vitals match metal | `ada body vitals --json` temp within ~2°C of `vcgencmd`; avail disk within ~1% of `df` |
| 3 | Birth once | `birth` twice → same `born_at`; second is no-op |
| 4 | Lifecycle continuity | `wake` / kill -9 / `wake` → readable fault or at least wake sequence; no second birth |
| 5 | Crash-safe append | `dd`-truncate last line / kill mid-write test → file remains parseable except torn tail |
| 9 | No cortex dependency | All CLI works with network down / no API keys |
| — | Package import | `python -c "import ada; print(ada.__version__)"` |

(body §10.6–8, 10–12 wait for Dream/HUD/dual-store.)

### 9.3 Eval organ pointer

When coded, `eval.smoke` wraps §9.2 and appends results under `runs/` — **not** required to finish M0 organ code, but design tests so the harness can call them.

---

## 10. Learning objectives + acceptance falsifiers

### Learning objectives (Aryan should explain out loud)

1. Why **MemAvailable** and **separate** `/` vs `/mnt/ada-data` disks matter on a USB-root + HDD body.  
2. Why **birth ≠ wake** and why `born_at` is sacred.  
3. The **tmp → fsync → rename → fsync-dir** vs **append → fsync** protocols and what power loss can still destroy.  
4. Why vitals are a **versioned schema + extras**, not an ever-growing grab bag of shell fields.  
5. How this ledger stays honest when Dream/Gemini later attach (`dream_*` events; digests ≠ metal).  
6. Why a **package + CLI** beats eternally growing `scratch/` scripts for a PhD-prep lab.

### Falsifiers (slice not done if…)

- Second boot / second `birth` changes `born_at`.  
- CLI claims memory saved while `ada-data` unmounted.  
- Vitals disagree wildly with `df` / `vcgencmd` and we call it fine.  
- Only manual demos exist — **no pytest**.  
- Implementation is Gemini chat that “summarizes” `/proc` without typed organs.  
- Autobiography is only a blog.md rewritten each week.

### Egress impact (research §8 field)

| Ring | Touched by M0? |
|------|----------------|
| Control plane (Tailscale) | **No** (may *read* `tailscale0` address into extras) |
| Cortex (Gemini) | **No** |
| Backup (`dream.push`) | **No** |
| Local durable | **Yes** — identity + lifecycle on HDD |

---

## 11. Won’t-chase

| Topic | Why not now |
|-------|-------------|
| Dream / WORLDVIEW / Gemini manage-pass | Separate organ; attach to same ledger later |
| HUD / FastAPI / Tailscale Serve | Needs M01 access + later UI card |
| Full Prometheus / Grafana / OTLP pipeline | Excellent later homework; not birth gate |
| SQLite WAL / RocksDB vitals TSDB | Premature; JSONL teaches durability first |
| ALP fork/succession/reputation | Multi-agent enterprise folklore |
| Embeddings for lifecycle search | grep + date filters enough |
| lm-sensors / smartctl requirement | Not installed; extras if added |
| Consciousness / sensorium-as-soul rhetoric | Constitution forbid |
| Custom distro / move root off USB as gate | Accepted risk + mitigations |
| Training Auto-Dreamer / LoCoMo as pass bar | Research §5 won’t-chase |

---

## 12. Ordered “do this next” (implement — still no code in *this* pass)

1. **Deps + package skeleton** — `pyproject.toml`, `src/ada/`, pytest in dev deps; `ADA_DATA_ROOT` override.  
2. **`ada.io.atomic` + `paths`** — implement replace/append fsync helpers with unit tests first.  
3. **`body.vitals`** — probes + pydantic model + golden fixtures from this Pi (sanitized).  
4. **`body.identity`** — birth-once writer; CLI `whoami` / `birth`.  
5. **`body.lifecycle`** — envelope + wake/sleep/fault/deploy/note; torn-line recovery tests.  
6. **`narrative` + CLI `status` / `story` / `doctor`** — human UX; exit codes.  
7. **Run pytest green** + manual §9.2 smokes on real metal (with care: don’t unmount HDD casually — use env override for refuse-write tests).  
8. **Only then** — optional thin systemd user unit that calls `ada body wake` on start / `sleep` on stop (can be tiny follow-up).  
9. **Do not start** Dream/Gemini/HUD until M0 smokes + M01 access checklist are honest.

---

## 13. References

### Papers & surveys (agent memory / lifecycle / self-state)

- Park et al., *Generative Agents* (2023) — https://arxiv.org/abs/2304.03442  
- Packer et al., *MemGPT* (2023) — https://arxiv.org/abs/2310.08560  
- Zhang et al., *A Survey on the Memory Mechanism of LLM-based Agents* (2024) — https://arxiv.org/abs/2404.13501  
- Shinn et al., *Reflexion* (2023) — https://arxiv.org/abs/2303.11366  
- *Memory for Autonomous LLM Agents* (2026) — https://arxiv.org/html/2603.07670v1  
- *Memory in the Age of AI Agents* (survey, 2025/26) — https://arxiv.org/abs/2512.13564  
- *Anatomy of Agentic Memory* (2026) — https://arxiv.org/html/2602.19320  
- Brady, *Springdrift* — ambient sensorium / persistent retainer runtime (2026) — https://arxiv.org/abs/2604.04660  
- Yao et al., *ReAct* (2022) — https://arxiv.org/abs/2210.03629  
- Agent Lifecycle Protocol (ALP) — genesis/lineage + JSONL store — https://github.com/alexfleetcommander/agent-lifecycle-protocol  

### Host metrics practice

- Prometheus, *Monitoring Linux host metrics with the Node Exporter* — https://prometheus.io/docs/guides/node-exporter/  
- Raspberry Pi `vcgencmd` exporter patterns — e.g. https://github.com/fahlke/raspberrypi_exporter  
- OpenTelemetry, AI agent observability overview (2025) — https://opentelemetry.io/blog/2025/ai-agent-observability/  

### Crash-safe local durability

- SQLite, *Atomic Commit In SQLite* — https://www.sqlite.org/atomiccommit.html  
- SQLite, *Write-Ahead Logging* — https://www.sqlite.org/wal.html  
- POSIX atomic rename + fsync-parent directory practice (write-file-atomic discussions; fsys-style journals)

### Internal ADA docs

- [`../01_BODY.md`](../01_BODY.md) — metal inventory; organs; §4 lifecycle; §6.2 writes; §10 acceptance  
- [`../02_CONSTITUTION.md`](../02_CONSTITUTION.md) — birth immutability; epistemics; permission ladder; lab mode  
- [`../00_ASSISTANT_RESEARCH.md`](../00_ASSISTANT_RESEARCH.md) — §8 module card gate  
- [`M01_NETWORK_ACCESS.md`](./M01_NETWORK_ACCESS.md) — Tailscale access (parallel track; not a code dep for vitals)

---

## Operator fork resolution (recorded)

**Lifecycle path:** single `/mnt/ada-data/memory/lifecycle.jsonl` for v0; document a later **rotate-to-`events/YYYY/MM.jsonl`** manage job when size/grep pain appears. Rationale: first life optimizes for one autobiography file + one recovery path; month sharding is a compression/ops concern, not a birth blocker.

No remaining design forks require Aryan input before implementation.

---

*End of M00. Doc admits body-sense design + proof plan; it does not admit Dream, Gemini, HUD, or implementation code.*
