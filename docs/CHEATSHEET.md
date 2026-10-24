# ADA operator cheat sheet (Raspberry Pi / one profile)

Tiers overview: [`operator-pi-tiers.md`](operator-pi-tiers.md). Full cron, matrix vs keyword, approval gates: [`operator-runbook-raspberry-pi.md`](operator-runbook-raspberry-pi.md). **`ada daemon`** is **never** a cron entry — see [`daemon-help.sh`](../scripts/pi/daemon-help.sh).

## Install (outline)

[Raspberry Pi OS Lite](https://www.raspberrypi.com/software/) or any Linux with **Python ≥ 3.11**. From the README ([§10 Setup and tests](../README.md#10-setup-and-tests)):

```bash
cd /home/pi/ADA
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # edit next section
chmod +x scripts/pi/*.sh
```

Publisher-only hosts can install without `[dev]` if you align dependencies yourself; **`ada`** CLI must resolve from the install.

## Minimum `.env` (fill manually)

Always:

- **`GEMINI_API_KEY`** — required for **`ada chat`**, **`ada daemon`**, **`ada dream`**, **`ada triage`**, **`ada extract-graph-lite`**, **`ada enrich-graph`**, and Gemini-backed ingest gates (see [.env.example](../.env.example)).

Paths (pick one mental model):

- **`ADA_DATA_DIR=/home/pi/ADA/data`** — SQLite **`state.db`** and logs, **or**
- **Profile isolation:** **`ADA_PROFILE=myprofile`** + **`ADA_PROFILE_DATA_ROOT=/home/pi/ada-profiles`** (per [`operator-onboarding.md`](operator-onboarding.md)).

Often needed for workflows / daemon:

- **`ADA_ENABLE_KNOWLEDGE_TOOLS=1`** — knowledge + graph-lite tools during turns (defaults off elsewhere; [.env.example](../.env.example) shows operator-ready `=1`).
- **`GEMINI_MODEL`** — optional override (default **`gemini-2.5-flash-lite`** in [.env.example](../.env.example)).

If deploying **ISR/S3**:

- **`S3_BUCKET_NAME`**, **`AWS_REGION`**, AWS credentials vars from [.env.example](../.env.example); **`ADA_MATRIX_ENABLE=1`** for real **`matrix-scan`** enqueues; approval toggles **`ADA_REQUIRE_APPROVAL_FOR_*`** as needed.

Optional **keyword track**:

- **`ADA_ENABLE_GSC_INGEST=1`**, **`GSC_SITE_URL`**, **`GSC_SERVICE_ACCOUNT_FILE`** / **`GSC_SERVICE_ACCOUNT_JSON`**, …

Scripts under **`scripts/pi/`** auto-load **`${PWD}/.env`** when **`ADA_REPO_ROOT`** points at the checkout (defaults to inferred repo root).

## One profile snippet (literal example)

```
ADA_PROFILE=myprofile
ADA_PROFILE_DATA_ROOT=/home/pi/ada-profiles
GEMINI_API_KEY=...
ADA_ENABLE_KNOWLEDGE_TOOLS=1
```

## Quick commands (interactive)

First-time checks:

```bash
cd /home/pi/ADA
./scripts/pi/smoke.sh
./scripts/pi/daemon-help.sh
```

Daily RSS (+ optional GSC when enabled in `.env`):

```bash
MISSION_SLUG=my-site ./scripts/pi/ingest-day.sh
```

Mission tick (**requires** scheduled mission **`schedule_hint_json`** — see onboarding):

```bash
./scripts/pi/mission-tick.sh my-site
# or ADA_PI_TICK_DRY_RUN=1 ./scripts/pi/mission-tick.sh my-site
```

GSC → keyword enqueue (weekly pattern; needs **`jq`** + keyword env vars from [`scripts/ada_keyword_track.sh`](../scripts/ada_keyword_track.sh)):

```bash
MISSION_SLUG=my-site ./scripts/pi/keyword-weekly.sh
```

Entity/matrix pipeline shortcut (RSS → triage → graph → matrix-scan): [`scripts/ada_entity_track.sh`](../scripts/ada_entity_track.sh).

## Cron (copy-paste template)

Pick one TZ; reuse paths from YOUR checkout (`/home/pi/ADA` below).

```
CRON_TZ=Pacific/Auckland

# Logs
# mkdir -p /home/pi/ADA/data/logs

0 6 * * * cd /home/pi/ADA && ./scripts/pi/ingest-day.sh >> /home/pi/ADA/data/logs/pi-ingest-day.log 2>&1

# Optional hourly tick (cron fires; tick honours min_interval in DB):
17 * * * * cd /home/pi/ADA && ./scripts/pi/mission-tick.sh my-site >> /home/pi/ADA/data/logs/mission-tick.log 2>&1

# From ops schedule / runbook: triage / graph-lite (often after ingest — needs GEMINI_API_KEY)
15 6 * * * cd /home/pi/ADA && . .venv/bin/activate && ada triage >> /home/pi/ADA/data/logs/triage.log 2>&1
45 6 * * * cd /home/pi/ADA && . .venv/bin/activate && ada extract-graph-lite >> /home/pi/ADA/data/logs/extract-graph-lite.log 2>&1

# Publisher frequency is policy — weekly keyword example:

0 8 * * 1 cd /home/pi/ADA && MISSION_SLUG=my-site ./scripts/pi/keyword-weekly.sh >> /home/pi/ADA/data/logs/keyword-weekly.log 2>&1

# Never cron `ada daemon` — install systemd unit from `./scripts/pi/daemon-help.sh`.
```

RSS rows must exist in **`knowledge_sources`** (**`ada add-rss-source URL`**) before **`ingest-rss`** pulls anything meaningful.

## If this breaks — check …

| Symptom | Check |
|---------|------|
| **Command not found: ada** | `source .venv/bin/activate`; **`pip install -e …`** (README §10). |
| **ingest-rss succeeds but zero items** | Feeds registered? **`ada add-rss-source`**; **`sqlite3`** list `knowledge_sources`. |
| **ingest-gsc failures** | `.env`: **`ADA_ENABLE_GSC_INGEST=1`**, **`GSC_*`**, scope URL; **`ada ingest-gsc verify --date …`** (needs network). |
| **Daemon ignores work** | **`systemctl status ada-daemon`**, **`GEMINI_API_KEY`**, **`ADA_KILL_SWITCH`**, **`ADA_DAILY_TOKEN_BUDGET` / monthly** caps (UTC — [runbook “Don’t bleed money”](operator-runbook-raspberry-pi.md)). |
| **Goals stay failed** | **`ada goal list --status failed --limit 20`**, **`ada goal show <id>`**, daemon log. |
| **DEPLOY blocked** | **[Approval flow](operator-runbook-raspberry-pi.md)** — **`ADA_REQUIRE_APPROVAL_FOR_PUBLISH`**, **`ada approval`**. |

## Network + keys summary

| Action | Network | Keys / flags |
|--------|---------|----------------|
| `ada --help` / subcommands `--help` | No | none |
| `ada goal add` | No | none |
| `ada mission …` (incl. `tick --dry-run`) | No | SQLite only |
| `ada ingest-rss` | Yes (HTTP feeds) | Gemini only if ingest gate / embeddings enabled |
| `ada ingest-gsc`, `verify` | Yes | `ADA_ENABLE_GSC_INGEST=1` + **`GSC_*`** |
| `ada dream --dry-run` | Yes | **`GEMINI_API_KEY`** (`--dry-run` still calls the model) |
| `./scripts/pi/keyword-weekly.sh` | Yes (GSC) | **`jq`**, GSC vars, **`ADA_KEYWORD_*`** per script header |
