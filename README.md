# ADA

Visitor overview: see [`portfolio.yaml`](portfolio.yaml).

**ADA** is a headless **Python 3.11+ asyncio** agent harness for operators on their own hardware (e.g. Raspberry Pi). One install runs interactive Gemini chat, a background worker (`ada daemon`), offline ingest/graph CLIs, and deterministic pSEO/ISR publish workflows—all backed by a per-profile **SQLite** database.

It is **not** a hosted SaaS and ships **no HTTP agent API**. Surfaces are the CLI and an optional localhost Streamlit HUD.

## Features (verified)

- **Chat** — Entity / Agent (`--agent`) / Plan / Setup ingress; streaming Gemini with **manual** function calling
- **Daemon** — long-running goal + workflow worker (`ada daemon`)
- **Knowledge** — RSS / GSC / brand ingest, FTS5 search, optional embeddings
- **Graph-lite** — triage, extract, enrich; fact **GATE** on entity publish
- **Publish** — `publish_entity_v1` / `publish_keyword_v1` → S3 `page.json` + manifest
- **Safety** — shell allowlist, token budgets, kill switch, profile isolation
- **HUD** — optional Streamlit read-only observability (`ada hud`)

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env        # set GEMINI_API_KEY
```

```bash
ada chat
ada goal add "background objective"
ada daemon                  # separate terminal / systemd on Pi
ada ingest-rss
ada dream --dry-run
pytest -q
```

Optional HUD:

```bash
pip install -e ".[streamlit]"
ada hud
```

Bind Streamlit to localhost only; do not expose the HUD publicly.

## Config / env

Canonical list: [`.env.example`](.env.example). Parsed in `src/ada/config.py`.

| Area | Vars (examples) |
|------|-----------------|
| **Required for model turns** | `GEMINI_API_KEY` (optional `GEMINI_MODEL`, default `gemini-2.5-flash-lite`) |
| **Profile isolation** | `ADA_PROFILE`, `ADA_PROFILE_DATA_ROOT`, `ADA_MEMORY_DIR` |
| **Job plane** | `ADA_JOB_QUEUE=legacy` \| `system_jobs` (one owner per `state.db`) |
| **Control plane** | `ADA_KILL_SWITCH`, `ADA_DAILY_TOKEN_BUDGET`, `ADA_MONTHLY_TOKEN_BUDGET` |
| **Publish / S3** | `ADA_S3_BUCKET` / `S3_BUCKET_NAME`, `ADA_PUBLISH_MIN_UNIQUE_FACTS`, approval flags |
| **Knowledge tools** | `ADA_ENABLE_KNOWLEDGE_TOOLS`, optional `ADA_KNOWLEDGE_EMBEDDINGS` |

Policy pack: [`policies/default.yaml`](policies/default.yaml). Skills: [`skills/*.yaml`](skills/).

`GEMINI_API_KEY` is required for chat, daemon model turns, dream, triage, and graph extract/enrich. Not required for pure ops like `ada goal`, `ada doctor`, `ada ingest-rss` (HTTP-only), or `ada approval`.

## Tests / CI

```bash
pip install -e ".[dev]"
pytest -q
```

CI ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)): Python **3.11** and **3.12**, same install + `pytest -q`. Publisher tests use **moto** (no real S3).

## Architecture

Case study and tradeoffs: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)  
C4 maps (Context → Containers → Components): [`docs/c4/README.md`](docs/c4/README.md)  
Portfolio zoom index: [`docs/c4/portfolio-map.json`](docs/c4/portfolio-map.json)  
Containers Mermaid: [`docs/c4/2-containers.mmd`](docs/c4/2-containers.mmd) (alias: [`docs/architecture.mmd`](docs/architecture.mmd))

### Operator docs (Pi / pSEO)

Many operator/runbook files live under `docs/` locally; GitHub visitors should start from C4 + ARCHITECTURE. Tracked companion: [`docs/claude_logic.md`](docs/claude_logic.md) (transcript rules). Ops cadence: [`ops/schedule.md`](ops/schedule.md).

### Layout

| Path | Role |
|------|------|
| `src/ada/` | Installable package (CLI, orchestrator, persistence, workflows, ingest, HUD) |
| `tests/` | pytest suite |
| `skills/`, `playbooks/`, `policies/`, `templates/` | Motor skills, playbooks, policy, mission templates |
| `scripts/`, `ops/` | Cron helpers, Pi smoke, schedule notes |
| `docs/` | Operator + architecture depth |

### Not in this repo

- Next.js ISR site (blueprint only: [`isr.md`](isr.md))
- In-process scheduler, voice STT/TTS, Docker Compose
- Live public demo URL

## License

No license file is present in this repository; treat licensing as unspecified unless one is added.
