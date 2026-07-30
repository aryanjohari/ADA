# Containers (C2)

Default map for operators, GitHub visitors, and the portfolio zoom UI ([`portfolio-map.json`](portfolio-map.json)).

ADA is **one installable Python package** ([`pyproject.toml`](../../pyproject.toml)) with several process roles—not a Docker Compose stack. There is no HTTP agent API in this repo.

## Process vs library (important)

| Kind | Containers | Meaning |
|------|------------|---------|
| **OS processes / CLI runs** | `cli-chat`, `daemon`, `ingest-clis`, `graph-lite`, `hud`, plus host `cron/systemd` | Separate process or short-lived CLI invocation |
| **In-process libraries** | `orchestrator`, `tool-executor` | Imported by chat and daemon; **not** standalone daemons—shown as containers so C2 can name the turn loop and tool plane |

## Containers

| ID | Label | Kind | Evidence |
|----|-------|------|----------|
| `cli-chat` | ada chat | Interactive CLI (Entity / Agent / Plan / Setup) | [`chat_ingress.py`](../../src/ada/chat_ingress.py), [`chat_session.py`](../../src/ada/chat_session.py) |
| `host-scheduler` | cron / systemd | Host OS scheduling (outside the package) | [`ops/schedule.md`](../../ops/schedule.md), [`ops/setup_cron.sh`](../../ops/setup_cron.sh) |
| `hud` | ada hud | Optional Streamlit; SELECT-only DB + argv whitelist | [`observability/app.py`](../../src/ada/observability/app.py) |
| `orchestrator` | Orchestrator | Manual Gemini multi-leg turns + transcript persistence | [`orchestrator.py`](../../src/ada/orchestrator.py) |
| `tool-executor` | Tool executor | Shell allowlist + YAML motor skills | [`tool_executor.py`](../../src/ada/tool_executor.py), [`motor/`](../../src/ada/motor/) |
| `daemon` | ada daemon | Long-running goals + workflows (one owner per profile) | [`main.py`](../../src/ada/main.py), [`jobs/worker.py`](../../src/ada/jobs/worker.py) |
| `ingest-clis` | Ingest CLIs | `ingest-rss`, GSC, brand, GETS, keywords | [`ingest/`](../../src/ada/ingest/) |
| `graph-lite` | Graph-lite | Triage / extract-graph-lite / enrich-graph | [`triage/`](../../src/ada/triage/), [`extract/`](../../src/ada/extract/) |
| `publish-workflows` | Publish workflows | Deterministic templates → S3 | [`workflow/`](../../src/ada/workflow/), [`publish/`](../../src/ada/publish/) |
| `state-db` | state.db | Per-profile SQLite (WAL + FTS5) | [`persistent/store.py`](../../src/ada/persistent/store.py), [`db/schema.sql`](../../src/ada/db/schema.sql) |
| `memory-files` | memory/*.md | soul / master and related files | [`memory_io.py`](../../src/ada/memory_io.py), `ADA_MEMORY_DIR` |
| `s3-out` | AWS S3 | Publish sink (external system on the diagram) | [`publish/s3_publish.py`](../../src/ada/publish/s3_publish.py) |

Gemini appears as an **external system**; graph-lite and the orchestrator both call it.

## Collapsed into notes (not separate C2 boxes)

Mission control, programme apply, `ada dream`, `ada matrix-scan`, doctor/boot/reload, and approval CLIs are additional **CLI surfaces** in the same package—not separate deployables. See [`__main__.py`](../../src/ada/__main__.py).

## Component zooms (C3)

| Container focus | Diagram |
|-----------------|--------|
| Orchestrator + tools + chat ingress | [`3-components/agent-core`](3-components/agent-core.md) |
| Daemon / job plane | [`3-components/daemon`](3-components/daemon.md) |
| Ingest CLIs | [`3-components/ingest-clis`](3-components/ingest-clis.md) |
| Graph-lite | [`3-components/graph-lite`](3-components/graph-lite.md) |
| Publish pipeline | [`3-components/publish-workflows`](3-components/publish-workflows.md) |
| HUD | [`3-components/hud`](3-components/hud.md) |

## Relationships (plain English)

- Chat **runs** orchestrator turns; tools **write** transcript rows to SQLite.
- Cron **runs** ingest/graph CLIs and **keeps** the daemon alive; daemon **advances** workflows and may **call** the orchestrator for goal turns.
- Publish **DEPLOY** uploads `page.json` and merges `manifest.json`.
- HUD **reads** the DB only—it is not the agent.
