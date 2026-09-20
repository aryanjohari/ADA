# M26 time — Phase 2 cited domain memory (third vertical)

**Status:** **TIME CAPTURE CLOSED (2026-09-19, v1.3)** — food/gym-par organ. Phone **PHONE METAL** [`5a370eb0…`](../../../runs/2026-09-18/5a370eb019d44559a294111f3d90267f.jsonl): miss-stop `no_active_block` (no Gemini); `I'm starting gym commute` → `custom`/`gym commute`; `Im starting work` auto-stop; `What's running` active=work; `Stop timer` 24s; miss-stop again; `I'm at the gym` → **`life_gym_start`** not a timer; `What did I track yesterday` → `life_time_day` `date=`; `Time this week` → `life_time_week` `days=7`. Packs `time_start` / `time_stop` / `time_status` — **do not rebuild**. Remainders ≤4: diary / vocative / `time_status` UTC `blocks_today` vs NZ morning / calendar+habits+alias FACT — **not** a capture reopen. **Next ≠ join-as-gate** — people phone jsonl ([`M26_PEOPLE_DOMAIN.md`](./M26_PEOPLE_DOMAIN.md) v1.1 **PHONE OPEN**). Habits capture **CLOSED** ([`M26_HABITS_DOMAIN.md`](./M26_HABITS_DOMAIN.md) v1.3). Food 1–4 **PHONE METAL**; food 5–6 + vocative **OPEN later**. Gym capture **CLOSED** — do not reopen; do not rebuild `gym_start` / `gym_end` / `life_split_set`.  
**Date:** 2026-09-20 (v1.9)  
**Host:** `ada-pi5` (Raspberry Pi 5, 8 GiB) · windows: Mac / phone via Tailscale Serve  
**Branch:** `rewrite/v1-body`  
**Kind:** **Phase 2 cited domain memory** for **time only** — organ wiring + organism purpose + Dream contract. Not a time-management textbook. Not cortex prompt stuffing. Not P4 charts. Not a Google Calendar clone.  
**Depends on:** [`M26_DOMAIN_KNOWLEDGE.md`](./M26_DOMAIN_KNOWLEDGE.md) (organ · reference · reject; purpose lock — time = finite capacity; focus vs maintenance) · [`M19a_P0_LIFE_CAPTURE.md`](./M19a_P0_LIFE_CAPTURE.md) (time verbs, `kind` enum, `time_blocks`, `time_intent.py`, single-active + auto-stop) · [`M22_LIFE_TEACH_IN_FLOW.md`](./M22_LIFE_TEACH_IN_FLOW.md) (sticky FACTS via Confirm; empty kind-alias FACTs = teach-in, not a start gate) · [`M10_MEMORY_KNOWLEDGE.md`](./M10_MEMORY_KNOWLEDGE.md) (library ≠ logs) · [`M04_MEMORY_DREAM.md`](./M04_MEMORY_DREAM.md) (WORLDVIEW cites; Dream must not auto-merge kind aliases)

**Feeds:** time capture **CLOSED** (phone `5a370eb0…`). Habits capture **CLOSED** [`M26_HABITS_DOMAIN.md`](./M26_HABITS_DOMAIN.md) v1.3 (`4fdf27a6…` + `a1e48d77…`). Dues capture **CLOSED** ([`M26_DUES_DOMAIN.md`](./M26_DUES_DOMAIN.md) v1.2). Food+gym `local_day` join **OPEN later** — **Next ≠ join**. P4 `time_week` charts / calendar stay **OPEN later**.

**Name stays `M26_TIME_DOMAIN.md`:** git-tracked **reference know** for time. Sibling of [`M26_FOOD_DOMAIN.md`](./M26_FOOD_DOMAIN.md) and [`M26_GYM_DOMAIN.md`](./M26_GYM_DOMAIN.md) and the agnostic lock, not a charter dump. Runtime `memory/domain/time.md` is **not** shipped here — boot/brief cannot load that path (charter injects FACT slice + WORLDVIEW digest only; `paths.py` has no `domain/` dir). Module doc is the source of truth until a later chat wires a capped slice.

**Supersedes:** any reading that (a) “knowing time” = prompt time-management / calendar essay, (b) this essay belongs in charter, (c) RAG can replace `time_blocks` rows, (d) analysis / week charts / calendar UI before honest named-block capture, (e) Dream may invent `duration_s` or auto-merge kind aliases, (f) time = sleep/wake-only or sock-level gestures, (g) due / food / gym rows are time, (h) parallel timers are in-scope, (i) empty alias FACTs are a start gate, (j) each spine label (`morning cooking`, `gym commute`, …) needs its own YAML/regex door, (k) 7-pass order starts at smokes or SQL. **Does not supersede:** M26 three kinds of know; M19a time schemas + packs; M22 teach-in Confirm **design**; single-active UNIQUE + auto-stop; mouth ⊆ receipt; meal / lift / gym-start structural doors.

### Changelog

| Ver | Date | Delta |
|-----|------|-------|
| **v1.9** | 2026-09-20 | **OPEN #3 thickened (no time code):** UTC `started_at` vs NZ `local_day` mapping is a **fix later**, not park-and-forget. NZST = UTC+12 → morning “today” looks 12h behind (`time_status` `blocks_today` prefix + HUD raw UTC). Capture stays **CLOSED**. Next still people phone jsonl, not this fix, not join. |
| **v1.8** | 2026-09-19 | **Pointer (no time code):** people 7-pass **pytest METAL, PHONE OPEN** [`M26_PEOPLE_DOMAIN.md`](./M26_PEOPLE_DOMAIN.md) v1.1 — organ **not CLOSED**. Time stays **CLOSED**. **Next = people phone jsonl**, not join. |
| **v1.7** | 2026-09-19 | **Pointer (no time code):** dues capture **CLOSED** [`M26_DUES_DOMAIN.md`](./M26_DUES_DOMAIN.md) v1.2 — phone add+list `8002799b…`. Time stays **CLOSED**. **Next = people Phase 2**, not join. |
| **v1.6** | 2026-09-19 | **Pointer (no time code):** dues 7-pass **pytest METAL, PHONE OPEN** [`M26_DUES_DOMAIN.md`](./M26_DUES_DOMAIN.md) v1.1 — organ **not CLOSED**. Time stays **CLOSED**. **Next = dues phone jsonl**, then people, not join. |
| **v1.5** | 2026-09-19 | **Pointer (no time code):** dues Phase 2 card shipped [`M26_DUES_DOMAIN.md`](./M26_DUES_DOMAIN.md) v1.0 — 7-pass ready, organ **not CLOSED**. Time stays **CLOSED**. **Next = dues 7-pass**, not people implement, not join. |
| **v1.4** | 2026-09-19 | **Pointer (no time code):** habits capture **CLOSED** [`M26_HABITS_DOMAIN.md`](./M26_HABITS_DOMAIN.md) v1.3 — phone `4fdf27a6…` + week `a1e48d77…`. Time stays **CLOSED**. **Next = people Phase 2**, not join. |
| **v1.3** | 2026-09-19 | **Freeze stamp (no new Python).** Capture **PHONE METAL** [`5a370eb0…`](../../../runs/2026-09-18/5a370eb019d44559a294111f3d90267f.jsonl) — miss-stop; start-shape labels; auto-stop; status active; stop duration; gym not stolen; day/week `date`/`days`. No Gemini on the run. Organ **closed**. Park `time_status` UTC `blocks_today` empty at NZ morning — not a capture reopen. **Next = habits Phase 2**, not join. |
| **v1.2** | 2026-09-18 | **7-pass implement (pytest METAL, PHONE OPEN).** `is_time_start_utterance` after meal/lift/gym; `time_intent` strips start-shape prefixes; Confirm none proven; miss-stop mouth has no minutes; HUD smokes + `life_time_day`/`life_time_week` SQL. Three write/status packs unchanged. **No PHONE METAL jsonl** — organ **not CLOSED**. |
| **v1.1** | 2026-09-18 | **7-pass ready (no Python).** Pack-door default locked: start-shapes force `time_start` before cortex (hint optional; gym v1.2 analogue); `time_intent` still fills `{kind,label}`; **no** regex per spine example. Meal / lift / `I'm at the gym` doors **win first**. Confirm sticky = none on start/stop; alias FACT not this slice. 7-pass order restored: pack door → resolve → Confirm sticky → mouth ⊆ receipt → smokes → SQL day/week → doc. Next chat may implement. |
| **v1.0** | 2026-09-18 | First Phase 2 domain card: time purpose + honest METAL/GAP/PHONE OPEN audit + Dream contract + reject fence. **No Python.** Packs `time_start`/`time_stop`/`time_status` exist (`life_p0.yaml`) — do not rebuild. Not a diary-dump implement. Not join. |

---

## Metal audit (2026-09-19 — v1.3 freeze)

**Tags:** **METAL** = in-tree (pytest OK). **PHONE METAL** = live phone run cite. **PHONE OPEN** = code and/or HUD pytest, **no** phone jsonl — do not say SHIPPED. **GAP** = not in tree. Do **not** rebuild start / stop / status. Close cite: [`5a370eb0…`](../../../runs/2026-09-18/5a370eb019d44559a294111f3d90267f.jsonl).

| Item | In-tree | Tag |
|------|---------|-----|
| Pack `time_start` | [`life_p0.yaml`](../../src/ada/harness/packs/life_p0.yaml) + YAML aliases (sleep / wake / good morning / `start focus` / `start timer`); spine [`time_intent.py`](../../src/ada/harness/time_intent.py); Agent fast-path [`loop.py`](../../src/ada/harness/loop.py) `_maybe_pack_fast_path` → `life_time_start` → `life_time_status`. Deprecated `focus_start` `alias_of` `time_start`. Prefill chip `start focus: ` | **METAL** pytest. HUD canned `going to sleep` ([`M19a_P01g`](../reviews/M19a_P01g_HUD_SMOKE.md)). **PHONE METAL** [`5a370eb0…`](../../../runs/2026-09-18/5a370eb019d44559a294111f3d90267f.jsonl) `I'm starting gym commute` / `Im starting work` |
| Start-shape pack door | Prefix/structural `start focus` / `start timer` plus `is_time_start_utterance` — `I started {label}` / `I'm starting {label}` / `starting {label}` / `I'm {label}` **after** meal / lift / `is_gym_start_utterance` / `is_gym_end_utterance`. Hint optional. Fast-path before cortex. **Not** a YAML row per spine example | **METAL** pytest ([`test_time_pack_door.py`](../../tests/test_time_pack_door.py)). **PHONE METAL** `5a370eb0…` (no Gemini on the run) |
| Pack `time_stop` | YAML aliases (`stop timer` et al.); Agent fast-path `life_time_stop` → `life_time_status`. Finish utterance **optional** — next `time_start` is the default stop | **METAL** pytest. **PHONE METAL** `5a370eb0…` stop 24s + miss `no_active_block` |
| Pack `time_status` | aliases `what's running` → `life_time_status`; Observe+Agent read fast-path | **METAL** today-read. **PHONE METAL** `5a370eb0…` active=`work`. `blocks_today` [] at NZ morning (UTC `started_at` prefix) = remainder, not a capture reopen. Undated alias does **not** pass `date` |
| `life_time_start` / `life_time_stop` / `life_time_status` | [`life_tools.py`](../../src/ada/tools/life_tools.py) + [`toolspec.py`](../../src/ada/tools/toolspec.py) | **METAL** |
| `time_intent.py` | NL → `{kind, label}` inside pack fence; gateway writes | **METAL** (mapping table in M19a). Resolve is **kind+label**, not `exercise_id` / FDC |
| `kind` enum | P0: `focus_deep` · `focus_maint` · `chore` · `cooking` · `wake` · `sleep` · `custom` | **METAL** |
| UNIQUE one running | `CREATE UNIQUE INDEX idx_time_one_running ON time_blocks(status) WHERE status = 'running'` ([`M19a`](./M19a_P0_LIFE_CAPTURE.md) §4.4) | **METAL** schema + policy |
| Auto-stop prior | Next `time_start` closes the running block (`auto_stopped_by`); no parallel timers | **METAL**. **PHONE METAL** `5a370eb0…` commute → work |
| `time_blocks` | `/mnt/ada-data/logs/life_logs.db` — `block_id`, `kind`, `label`, `started_at`, `ended_at`, `duration_s`, `status` (`running`/`stopped`/`orphan_closed`) | **METAL** |
| Today running chip | [`today.py`](../../src/ada/hud/today.py) `running_timer` `{block_id, kind, label, started_at}` | **METAL** |
| `GET /api/life/day` | [`routes_api.py`](../../src/ada/hud/routes_api.py) — `nutrition_day` + `time_status` JSON | **METAL** (today concat). **Not** a day/week SQL organ |
| Due / food / gym | `due_*` / `meal_log` / `lift_log` / gym start-end are **other** organs — their structural doors **win first** | **POLICY** — must **not** be described as time |
| Kind-alias FACT teach-in | optional `facts/time_kind_aliases.yaml` (M19a: design only, not a P0 gate) | **OPEN** — Confirm sticky, **not this 7-pass slice**, not a start gate |
| `life_time_day` / `life_time_week` | [`time_reflection.py`](../../src/ada/logs/time_reflection.py) SQL + rules; packs `time_day`/`time_week`; Observe+Agent fast-path; CLI `ada life time-day` / `time-week`; pack must pass `date`/`days` | **METAL** pytest ([`test_time_reflection.py`](../../tests/test_time_reflection.py)). **PHONE METAL** `5a370eb0…` yesterday + this week. SQL tools ≠ charts. Do not substitute `life_time_status` |
| Diary dump into `time_blocks` | — | **GAP** — **OPEN later**; same table, not a second organ |
| Food+gym `local_day` join | — | **GAP** — **OPEN later**; not this card |

**Do not reopen as this card’s job:** rewrite the three time packs; food 1–4; food 5–6 + vocative; gym capture (start/end/split); join; Hevy; charts; HUD sheet; rank; wipe `custom_60kg`; habits product; people; dues; PTT; calendar; diary NL implement; decide-layer regex-per-phrase; kind-alias FACT as a capture gate.

---

## Implement lock (v1.3 — CLOSED)

**Pytest METAL + phone jsonl.** Do not shuffle the seven steps. Do not rebuild the three packs.

```text
pack door → resolve gate → Confirm sticky → mouth ⊆ receipt → smokes → SQL day/week → doc stamp
```

| Step | This 7-pass did | This 7-pass did **not** |
|------|-----------------|-------------------------|
| 1 Pack door | `is_time_start_utterance` start-shapes; hint optional; food/lift/gym doors first | YAML/regex per `morning cooking` / `gym commute` / … |
| 2 Resolve | Keep `time_intent` `{kind, label}`; strip start-shape prefixes; no catalog | FDC recover; gym fold; new time catalog |
| 3 Confirm sticky | Leave **none** on start/stop. Empty alias FACT is **not** a gate | `facts/time_kind_aliases.yaml` implement (OPEN later) |
| 4 Mouth | Ack ⊆ receipt; miss-stop never speaks minutes | Gemini narrate pass |
| 5 Smokes | Pytest + **PHONE METAL** `5a370eb0…` | Diary dump; vocative |
| 6 Reflection | `life_time_day` / `life_time_week` + pack `date`/`days` — **PHONE METAL** | Calendar UI; `time_week` charts; join |
| 7 Doc | This freeze | Claim CLOSED without jsonl |

**Start-shapes (locked):** `start focus:` / `start timer:` · `I started {label}` · `I'm starting {label}` · `starting {label}` · `I'm {label}`. Label = remainder; `time_intent` maps `kind`. Structural time **after** meal / lift / gym start/end. Bare `morning cooking` without a start-shape is **not** a pack door.

**Do not rebuild** `time_start` / `time_stop` / `time_status`.

---

## One-liner

Time domain = **honest durations for named blocks against finite daily capacity**. SQLite `time_blocks` (`kind`, `label`, `started_at`/`ended_at`, `duration_s`) are **truth**; this doc is a **lens** for briefs/Dream later — never a source of invented seconds, never a substitute for the live spine, never a calendar.

---

## Signal / organism purpose (reference know, cited)

Humans are signal-driven organisms. Time capture exists so ADA can later read **how long named things took** in a **mix of kinds** on a finite day — not so the cortex can role-play a calendar, a sleep coach, or a sock-level stopwatch.

Time is the same **job** as food lines and gym sets: one honest row per named bout. `kind` is the **rollup bucket** (existing P0 enum). `label` is the **named thing** (morning cooking, gym commute, shower/skincare). Sleep/wake are kinds on the spine, not the whole organ.

| Why log | What the signal is **for** |
|---------|----------------------------|
| Named block (`label`) | What took the capacity — operator surface, not a catalog id |
| `kind` | Mix of focus vs maintenance vs chore vs cooking vs sleep/wake vs custom — rollup later |
| Duration (`duration_s`) | How long it actually ran. **Never invent.** Null/absent until stop (or auto-stop / orphan close) |
| Single running block | One live spine. Next start closes prior. No parallel timers |
| Honest absence | Missing laundry / someone else cooked = **no row**, not a calendar organ filling the gap |
| Session vs other organs | Breakfast/lunch **clock** ≠ meal foods; gym **clock** ≠ sets; shower/skincare = **one** time block now; step checklists = habits **later** |

**Interpretive classes only — no invented durations.** A stopped block’s `duration_s` comes from tool close (or auto-stop / `orphan_closed`). This card does not assign “work = N minutes.” Kind aliases / labels come from `time_intent.py` + optional FACT teach-in — not this prose.

**Personal informatics:** collection (this organ) is the daily path; integration/reflection (day/week SQL, P4 charts, dynamic calendar) wait until logs are honest ([Li et al., CHI 2010](https://doi.org/10.1145/1753326.1753611); [Choe et al., CHI 2014](https://doi.org/10.1145/2556284.2556964)). Live spine is the required write. Diary dump into the **same** `time_blocks` table is **OPEN later**, not a 7-pass blocker, not a second organ.

| Claim | Tag | Pointer |
|-------|-----|---------|
| Collection vs reflection stages | **EVIDENCE** | [Li et al., 2010](https://doi.org/10.1145/1753326.1753611) |
| Self-trackers collect first, explore later | **EVIDENCE** | [Choe et al., 2014](https://doi.org/10.1145/2556284.2556964) |
| Purpose: finite capacity; focus vs maintenance; named-block durations | **POLICY** | [`M26_DOMAIN_KNOWLEDGE.md`](./M26_DOMAIN_KNOWLEDGE.md) operator domain signals |
| Durations from tools/SQLite, not prompt | **METAL** | `time_blocks.duration_s` · gateway `life_time_stop` · M19a: cortex must not invent duration |
| One running block; auto-stop | **METAL** | UNIQUE index + M19a time pipeline |
| Time ≠ due / food / gym | **POLICY** | this card · M19a verb families |

---

## Organ know — wiring map (METAL, file paths)

Time **organ know** lives in pack + code + SQLite — not in this markdown. Time has **no** FDC / `exercise_catalog` bind. Resolve is **kind + label**, not `exercise_id`.

### Input

| Channel | Shape |
|---------|--------|
| NL utterance | **Start-shapes** (pack door): `start focus:` / `start timer:` · `I started {label}` · `I'm starting {label}` · `starting {label}` · `I'm {label}`. Example labels (slots, **not** YAML doors): morning routine · morning cooking · breakfast-clock · relax · gym commute · gym-clock · commute home · shower/skincare · work · work-break · hang/wash/fold (laundry days) · lunch-clock. YAML aliases (already METAL): `going to sleep` / bedtime → `sleep`; `woke up` / good morning → `wake`. Cooking / meal-prep **cues inside** `time_intent` → `kind=cooking` once the pack already fired. Else `custom` + label |
| Start | `time_start` — insert **running** block. If one is already running → **auto-stop** prior (`auto_stopped_by`). Confirm class **`none`**. Bare `morning cooking` without a start-shape is **not** a door |
| Stop | `time_stop` / `stop timer` — close active block; write `duration_s`. **Optional.** Next start is the default stop. Stop with nothing running → `{ok:false, reason:no_active_block}` — **no fake duration** |
| Status | `what's running` / `time_status` — **today** local mix by kind + active block |
| Split from other organs | Breakfast/lunch clock ≠ `meal_log` foods. Gym clock ≠ `lift_log` sets. `I'm at the gym` stays **gym_start**. Due chips ≠ timers |
| Alias teach-in | Empty kind-alias / label FACTs → Confirm **later**, not a start gate, **not this 7-pass** |

**Write modes (encode, don’t fanfiction):** (1) **live spine** — required path, one running block; (2) **diary dump** into the **same** `time_blocks` table — named OPEN later, not a 7-pass blocker, not a second organ; (3) **live-fine** optional on named repeats, not every gesture.

### Spine

[`src/ada/harness/time_intent.py`](../../src/ada/harness/time_intent.py): utterance → `{kind, label}` inside the pack fence. Gateway owns the write (`life_time_start` / `life_time_stop`). Cortex fills slots only — **must not** invent `duration_s` or a second parallel block.

Fast path ([`loop.py`](../../src/ada/harness/loop.py)): Agent `time_start` / `time_stop` when args complete; Observe+Agent `time_status` / `time_day` / `time_week`. Pack hint from [`pack_router.py`](../../src/ada/harness/pack_router.py) (prefixes → YAML `aliases:` → structural `start focus`/`start timer` → `is_time_start_utterance` after meal/lift/gym-start/end). Sleep/wake/good morning/stop timer live in **YAML aliases**, not a decide-layer regex per spine phrase. Observe does not write. Mouth speaks from receipt only (M23).

**Do not** add a decide-layer regex for every named block on the example day. Labels are slots; `kind` is the enum bucket. Pack door = **start-shape**, not the label list.

### Tools

| Tool | Role | Confirm |
|------|------|---------|
| `life_time_start` | Auto-stop prior if running; insert `status=running`; `{block_id, kind, started_at}` | **`none`** |
| `life_time_stop` | Close active; `{block_id, duration_s, kind}`. None running → `no_active_block` | **`none`** |
| `life_time_status` | Active block + **today’s** blocks + `by_kind{}` | **`none`** |
| `life_time_day` | One **local** calendar day on `time_blocks`; pack must pass `date` | **`none`** |
| `life_time_week` | Last N local days — deterministic kind mix / named-block durations | **`none`** |

Handlers: [`src/ada/tools/life_tools.py`](../../src/ada/tools/life_tools.py). Pack: [`packs/life_p0.yaml`](../../src/ada/harness/packs/life_p0.yaml) verbs `time_start` · `time_stop` · `time_status` · `time_day` · `time_week`. Composer chip `focus` prefills the start door. Confirm **only** on sticky kind-alias FACT writes (M22, OPEN later) — not on start/stop/day/week. **Not in tree:** `life_time_fix` / diary-dump verb.

### DB / FACTS

| Store / door | Path / host |
|--------------|-------------|
| Block truth | `/mnt/ada-data/logs/life_logs.db` — `time_blocks` ([`M19a`](./M19a_P0_LIFE_CAPTURE.md) §4.4) |
| Kind-alias FACT (optional) | `facts/time_kind_aliases.yaml` — M19a design only; **not** required to start a block |
| Today strip | `running_timer` on [`build_today()`](../../src/ada/hud/today.py) |
| Life day JSON | `GET /api/life/day` includes `time_status` (today) |

Code: [`src/ada/logs/`](../../src/ada/logs/) (schema + writers; one `ada.logs` package) + [`life_tools.py`](../../src/ada/tools/life_tools.py). **No** food-style catalog / FDC cache on this path.

### Resolve chain

```text
TIME INTENT
  pack_router  (prefix / YAML aliases / start focus|timer / is_time_start_utterance)
  meal · lift · gym_start · gym_end  WIN FIRST
  time_intent  → {kind, label}   (enum kind + named label; no catalog id)

BIND (code, not cortex)
  kind ∈ P0 enum (else custom)
  label = named thing (operator surface)
  NO exercise_id / ref_id / FDC
  empty alias FACT → still start; teach-in Confirm is later (not a gate; not this 7-pass)

SINGLE ACTIVE
  if status='running' exists → auto-stop prior (auto_stopped_by)
  UNIQUE index forbids a second running row
  cortex must not sole-write a second running block

STOP
  active → duration_s from clock close
  none running → ok:false no_active_block  (never invent duration_s)

  Confirm none on start/stop
  Confirm only on sticky kind-alias FACT (OPEN — not this slice)
  mouth = receipt / Confirm / refuse only
```

Time has **no** food-style Confirm picker and **no** gym catalog fold. Miss a named block some days = honest absence. Do not copy FDC recover or gym rank here.

### Write shape

Per `time_blocks` row:

| Field | Meaning |
|-------|---------|
| `kind` | P0 enum rollup bucket |
| `label` | Named thing (nullable in schema; operator surface when present) |
| `started_at` | UTC ISO |
| `ended_at` | UTC ISO on stop / auto-stop / orphan close; null while running |
| `duration_s` | Integer seconds from close. **Never invented.** Null while running |
| `status` | `running` · `stopped` · `orphan_closed` |
| `auto_stopped_by` | Next `block_id` if chained single-active |
| `receipt_id` | Mandatory on write |

Start receipt (`life_time_start`): `{block_id, kind, started_at}` (+ prior auto-stop if any). Stop receipt: `{block_id, duration_s, kind}`. Gateway **refuses** a second running block (UNIQUE + auto-stop). Stop with none running: `{ok:false, reason:no_active_block}`.

Sleep spanning midnight: **one** block; local-day attribution = **start** day (M19a). Orphan heal: close with `orphan_closed`, `ended_at=now` — still not an invented duration from this prose.

**Mouth:** ack only from tool outcome. No “Logged 45 minutes” on `ok:false`. No duration on a still-running start receipt unless the tool wrote it. HUD fast-path may emit canned `token_delta` (M19a P0.5) — still ⊆ receipt. **PHONE METAL** [`5a370eb0…`](../../../runs/2026-09-18/5a370eb019d44559a294111f3d90267f.jsonl).

### ASCII flow

```text
utterance  ("going to sleep" / "start timer: morning cooking" / "I'm starting gym commute" / "I'm hanging clothes" / "stop timer" / "what's running")
   │
   ├─ pack_router
   │     meal / lift / gym_start / gym_end  → those organs (I'm at the gym stays gym)
   │     YAML aliases → sleep/wake/stop/status
   │     start focus|timer (METAL) + is_time_start_utterance (METAL pytest; PHONE METAL 5a370eb0)
   │        time_start  → time_intent {kind,label} → life_time_start
   │                         └─ auto-stop prior running (UNIQUE one)
   │     time_stop   → life_time_stop   (no_active_block if none)
   │     time_status → life_time_status (today only; undated `what's running`)
   │
  ├─ time_day / time_week
  │     pack must pass date / days — alias substring is not yesterday
   │
   ├─ time_blocks
   │     kind + label; duration_s only on close
   │     no FDC / no exercise_id
   │
   └─ mouth → receipt / Confirm (aliases only, later) / refuse only
   cortex (agent): slot-fill kind+label inside fence — never duration, never second running
```

---

## Reject fence

This doc (and any future capped slice) must **never**:

| Never | Why |
|-------|-----|
| Invent `duration_s` when no close / `no_active_block` | Truth > charm; M26 F-M26-1 |
| Domain essay in charter / pack prompt | Unbounded, unverifiable (F-M26-2) |
| RAG / WORLDVIEW as time log | Structured logs > RAG (`00` §3.3) |
| Dream auto-merge kind aliases | Teach-in Confirm only; Dream **must not** auto-merge FACT aliases ([`dream/merge.py`](../../src/ada/dream/merge.py)) |
| Charts / calendar UI as a capture gate | F-M26-3; P4 later |
| Cortex sole-write a second running block | UNIQUE + M19a F3; F-M26-6 analogue |
| Rebuild `time_start` / `time_stop` / `time_status` | Already METAL |
| Treat due / food / gym as time | Other organs; wrong signal |
| Decide-layer regex per spine phrase | Verb→Pack; labels are slots; door is **start-shape** |
| Steal `I'm at the gym` / lift / meal NL | Other organs’ structural doors win first |
| Mouth claim a duration when tool `ok:false` | M23 receipt honesty |
| Parallel timers | Denied P0; won’t-chase |

**Falsifiers copied (time-relevant):**

| ID | Fail if… |
|----|----------|
| **F-M26-1** | Block write uses `duration_s` **not in the tool receipt** because “domain knowledge” |
| **F-M26-2** | Charter or pack prompt contains a **time-management essay** as the daily capture path |
| **F-M26-3** | Analysis/brief charts or calendar views run on days where capture is **systematically empty/dishonest** without saying so |
| **F-M26-4** | Daily `time_start` triggers **unbounded web/search** or ReAct for domain facts |
| **F-M26-5** | This prose **overwrites** FACTS (kind aliases) or SQLite rows without Confirm |
| **F-M26-6** | Cortex **sole-writes** a second `running` row after reference doc retrieval |

M19a time falsifier still binds: two `running` blocks = parallel timer leak (F3). Stop with none running must not mint a duration. Pack door must not steal gym/meal/lift (`I'm at the gym` stays `gym_start`).

---

## Reflection contract (deterministic)

**Not Dream.** Reflection = SQL + rules on structured logs. No LLM for kind-mix / week patterns on the read path.

Food has `life_nutrition_day` + `life_nutrition_week`. Gym has `life_gym_day` + `life_gym_week` (**METAL** pytest; gym day/week **PHONE METAL** `2306ab59…` — gym organ, **not** this card). Time’s close is the same pattern on `time_blocks` — **PHONE METAL** [`5a370eb0…`](../../../runs/2026-09-18/5a370eb019d44559a294111f3d90267f.jsonl). Do not ship charts.

Today-status `life_time_status` remains the undated `what's running` door — **do not substitute it** for day/week queries. Alias `what's running` ≠ yesterday.

### Reads (inputs)

| Input | Source |
|-------|--------|
| Today’s blocks + active | `life_time_status` → `time_blocks` filtered to local today via `started_at` |
| One local day | `life_time_day` — must pass `date` |
| Week window | `life_time_week` — must pass `days`; M19a parks `time_week` / `v_time_by_kind` **UI** as **P4** |
| Kind mix | `by_kind{}` on today’s status; week mix waits on SQL |

| Tool (name lock) | Mirror of | Shape |
|------------------|-----------|-------|
| `life_time_status` | `life_gym_status` / today nutrition headline | **Today** only. Undated `what's running` does **not** set `date`. |
| `life_time_day` | `life_nutrition_day` / `life_gym_day` | One **local** calendar day on `time_blocks`; pack must pass `date`. **PHONE METAL** `5a370eb0…`. |
| `life_time_week` | `life_nutrition_week` / `life_gym_week` | Last N local days — deterministic kind mix / named-block durations. **PHONE METAL** `5a370eb0…`. `time_week` **UI** / Google Calendar rebuild = **won’t-chase**. |

**TZ note (same as food/gym):** stamps are UTC ISO; read `date` is operator `preferred_tz`. Sleep spanning midnight stays **one** block; local-day attribution = **start** day. Mouth must speak **local** date/window — not raw UTC.

### Writes (outputs)

| Output | Path |
|--------|------|
| Today status | tool receipt + Today `running_timer` (no time rollup table yet) |
| Week scratch | [`scratch/time_reflection_latest.json`](../../src/ada/logs/time_reflection.py) — not WORLDVIEW |

**No** WORLDVIEW time digests from reflection. **No** FACT auto-merge of kind aliases. **No** charts.

### Must not

- Invent `duration_s` or fill a miss-stop as 0 / guessed minutes.
- Run LLM for week kind-mix on Observe fast path.
- Auto-merge into FACTS (kind aliases).
- Treat calendar / `time_week` charts as a write gate (F-M26-3).
- Use `life_time_status` for yesterday because the alias contains “running.”

### LLM narrative

On-demand brief narrative = **later slice**. Numbers always from tools/SQL first.

---

## Analysis / brief (P4, later)

Once logs are honest, these become **possible** — they are **forbidden as a gate** for P0 write (F-M26-3).

| Later question | Needs |
|----------------|--------|
| Kind mix vs last week | `life_time_week` (**PHONE METAL** `5a370eb0…`) |
| Named-block durations on one day | `life_time_day` (**PHONE METAL** `5a370eb0…`) |
| Dynamic calendar / `time_week` UI | Later **reads** of honest rows — not a capture rebuild; Google Calendar clone = **won’t-chase** |
| Habits overlap (checklists vs clock) | P1 habits organ — shower/skincare clock stays **one** time block; steps are not this card |
| Food+gym+time synergy | **Join on `local_day`** — **OPEN later**, not this card |

Do not ship charts, a calendar product, or “am I using my time well?” coaching in this Phase 2 card.

---

## Domain close checklist (copy from M26)

Reusable close order — **path first, ranking last** ([`M26_DOMAIN_KNOWLEDGE.md`](./M26_DOMAIN_KNOWLEDGE.md)):

pack door → resolve gate → Confirm sticky → mouth = receipt → smokes → **reflection (deterministic SQL on logs)** → doc.

**Read path:** pack router must pass **`date` / `days` args** for time day/week reads — alias substring (`what's running`) alone is insufficient. **Time writes:** start-shape pack door → `time_intent` kind+label → `life_time_start` / `life_time_stop`; **no** catalog id. **Confirm:** none on start/stop; sticky kind aliases = ask-once teach-in (**OPEN later — not this 7-pass**), not a food picker. **Vocative (M26 v1.8, later):** strip `hi/hey ada` before verb scrape; still Verb→Pack, not a chat turn.

Time status on the seven steps:

1. **Pack door** — YAML aliases + `start focus`/`start timer` + `is_time_start_utterance` **METAL** pytest. **PHONE METAL** [`5a370eb0…`](../../../runs/2026-09-18/5a370eb019d44559a294111f3d90267f.jsonl) (`I'm starting gym commute` / `Im starting work`; `I'm at the gym` not stolen). Hint optional; meal/lift/gym doors first. Do not rebuild the three write packs. Do not regex a decide-layer for every spine label.
2. **Resolve gate** — **thin**: `kind` enum + `label` string; start-shape prefixes stripped. **PHONE METAL** `5a370eb0…` labels `gym commute` / `work`. Not FDC / `exercise_id`.
3. **Confirm sticky** — start/stop Confirm **`none`** (**METAL** pytest; **PHONE METAL** no Confirm on that run). Kind-alias FACT **OPEN later**.
4. **Mouth = receipt** — ack only from tool outcome. Miss-stop never speaks minutes. **METAL** pytest. **PHONE METAL** `5a370eb0…` (no Gemini).
5. **Smokes** — HUD pytest **METAL**. Close run **PHONE METAL** `5a370eb0…` (happy + miss-stop + auto-stop + gym-not-stolen + day/week).
6. **Reflection** — Today `life_time_status` **METAL** (active). Day/week SQL **PHONE METAL** `5a370eb0…`. `blocks_today` UTC prefix = remainder. Not charts.
7. **Doc** — this card **v1.3**; organ **CLOSED**. OPEN ≤4 remainders (not a capture reopen).

**Root-cause rank (same as food):** path bypass ≫ sticky poison ≫ rank demote ≫ mouth lie. Time has **no** catalog rank fight; do not start one here.

---

## Operator smoke / falsifiers

### Smokes (capture — do not skip)

Automated HUD-path pytest is **in-tree**. Close cite [`5a370eb0…`](../../../runs/2026-09-18/5a370eb019d44559a294111f3d90267f.jsonl). Do not regex a decide-layer for every phrase.

| Utterance | Expect | Evidence |
|-----------|--------|----------|
| `going to sleep` | `life_time_start` `kind=sleep` + `life_time_status`; Today running chip | **METAL** pytest ([`M19a_P01g`](../reviews/M19a_P01g_HUD_SMOKE.md) step 2) |
| `what's running` | `life_time_status`; Observe allowed; **today** only (not yesterday); active block | **METAL** pytest. **PHONE METAL** `5a370eb0…` active=`work`. `blocks_today` [] remainder |
| `woke up` / good morning | `life_time_start` `kind=wake`; auto-stop prior (e.g. sleep) | **METAL** YAML aliases (M19a) |
| `start timer: morning cooking` / `start focus: work` | `life_time_start`; `label` from body; `kind` from `time_intent`; **no** meal row; **no** gym set | Prefix **METAL** |
| `I'm starting gym commute` / `Im starting work` | `life_time_start` via `is_time_start_utterance`; labels `gym commute` / `work`; auto-stop prior | **METAL** pytest. **PHONE METAL** `5a370eb0…` |
| Bare `morning cooking` / `gym commute` (no start-shape) | **Not** a time pack door — do **not** add a YAML row | **METAL** pytest (not a door) |
| `I'm at the gym` | **`gym_start`**, not `time_start` | **PHONE METAL** `5a370eb0…`. Gym also `504fb6a5…` / `1a54acda…` |
| `stop timer` with a running block | `life_time_stop`; `duration_s` on receipt; chip clears | **PHONE METAL** `5a370eb0…` work 24s |
| `stop timer` with **nothing running** | `{ok:false, reason:no_active_block}`; **no** invented `duration_s`; no Gemini | **PHONE METAL** `5a370eb0…` (twice) |
| Next start while one is running | Auto-stop prior; **one** `running` row; `auto_stopped_by` set | **PHONE METAL** `5a370eb0…` commute → work |
| `what did I track yesterday` | `life_time_day` with local `date` (not `life_time_status`) | **PHONE METAL** `5a370eb0…` |
| `time this week` | `life_time_week` with `days` | **PHONE METAL** `5a370eb0…` |
| Shower/skincare as **one** block | Single `time_blocks` row (`kind=custom` + label) — not a checklist | **POLICY** M19a habits-vs-timer. Habits product **P1 PARK** |
| Laundry hang/wash/fold some days only | Row when logged; **honest absence** other days — not a calendar fill | **POLICY** |

### Fail if

| Fail | Anti-pattern |
|------|----------------|
| Invented duration | Stop-miss / still-running spoken as N seconds |
| Second running | Parallel timer; UNIQUE bypass; cortex sole-write |
| Pack rebuild | New `time_*` verbs instead of closing the three that exist |
| Decide-layer sprawl | YAML/regex per spine label instead of start-shapes + `time_intent` |
| Stolen gym/meal/lift | `I'm at the gym` / kg×reps / meal NL routed to `time_start` |
| Calendar-as-gate | Charts / Google Calendar before honest named blocks |
| Organ mix-up | Due / meal / lift described or stored as `time_blocks` |
| Lying mouth | Tool `ok:false` but text says logged / stopped with minutes |
| Alias as start gate | Refusing `time_start` until kind-alias FACT exists |

---

## OPEN (≤4) — later / parked (not this card’s implement)

| # | Question | Default until a later chat locks it |
|---|----------|-------------------------------------|
| 1 | **Diary dump into `time_blocks`?** | Live spine stays the required write. Same table, not a second organ — **OPEN later**. |
| 2 | **Vocative filler?** | `Hi Ada.` strip before scrape = food OPEN #4 later. Still Verb→Pack, not a chat turn. |
| 3 | **Fix UTC→NZ mapping (`blocks_today` + HUD clock)?** | **Must fix later** — not a capture reopen, not a pack rebuild. Stamps stay UTC ISO. `life_time_day`/`week` already use `preferred_tz`. `time_status` still string-prefixes UTC `started_at` with Auckland `local_day` (`>= "YYYY-MM-DDT"`), so NZST morning (UTC+12) drops today’s blocks for 12h; HUD prints raw `started_at` (20:12 looks like 8:12pm). Map status/strip/mouth through `utc_to_local_day` (same as day/week). Cite: operator 2026-09-20 morning + `5a370eb0…` empty `blocks_today`. |
| 4 | **Calendar view / habits overlap / kind-alias FACT?** | P4 calendar = later **read** of honest rows (won’t-chase Google Calendar). Habits checklists = **P1**. `facts/time_kind_aliases.yaml` = teach-in later. |

**Active reopen path for next chats:** people phone jsonl ([`M26_PEOPLE_DOMAIN.md`](./M26_PEOPLE_DOMAIN.md) v1.1 **PHONE OPEN**). Dues capture **CLOSED**. **Join stays OPEN later** — not the default gate. **Not OPEN here:** parallel timers; decide-layer regex-per-phrase; rebuild `time_start`/`stop`/`status`; alias FACT as a start gate.

**Do not reopen:** invent duration; essay in charter; Dream auto-merge aliases; charts/calendar-as-write-gate; cortex second running block; food 1–4; food 5–6 + vocative **implement**; gym capture; food+gym join **implement**; Hevy / gym HUD sheet / rank / wipe `custom_60kg`; habits product **on this card**; people; dues; PTT; diary NL as this card’s job.

---

**Next:** people phone jsonl ([`M26_PEOPLE_DOMAIN.md`](./M26_PEOPLE_DOMAIN.md) v1.1 **PHONE OPEN**). Food+gym `local_day` join **OPEN later**. Time capture is **closed**. Habits capture is **closed**. Dues capture is **closed**.

*End M26 time. Phase 2 freeze 2026-09-19 (v1.3) — PHONE METAL 5a370eb0; do not rebuild start/stop/status; join OPEN later; logs are truth; this doc is the lens.*
