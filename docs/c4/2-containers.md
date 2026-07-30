# Containers (C2)

Default map for operators, GitHub visitors, and the portfolio graph ([`architecture.graph.json`](../architecture.graph.json)).

ADA is **one installable Python package** with several process roles—not a Docker Compose stack.

## Containers

| ID | Label | Kind |
|----|-------|------|
| `cli-chat` | ada chat | Interactive CLI (Entity / Agent / Plan / Setup) |
| `host-scheduler` | cron / systemd | Host OS scheduling (outside the package) |
| `hud` | ada hud | Optional Streamlit; SELECT-only DB + argv whitelist |
| `orchestrator` | Orchestrator | Manual Gemini multi-leg turns + transcript persistence |
| `tool-executor` | Tool executor | Shell allowlist + YAML motor skills |
| `daemon` | ada daemon | Long-running goals + workflows (one owner per profile) |
| `ingest-clis` | Ingest CLIs | `ingest-rss`, GSC, brand, GETS, etc. |
| `graph-lite` | Graph-lite | Triage / extract-graph-lite / enrich-graph |
| `publish-workflows` | Publish workflows | Deterministic templates → S3 |
| `state-db` | state.db | Per-profile SQLite (WAL + FTS5) |
| `memory-files` | memory/*.md | soul / master and related files |
| `s3-out` | AWS S3 | Publish sink (shown as external system) |

Gemini appears as an **external system** on this diagram; the portfolio IR collapses it into edges from the orchestrator (“model turns”).

## Component zooms (C3)

| Container focus | Diagram |
|-----------------|--------|
| Orchestrator + tools + chat ingress | [`3-components/agent-core`](3-components/agent-core.md) |
| Daemon / job plane | [`3-components/daemon`](3-components/daemon.md) |
| Publish pipeline | [`3-components/publish-workflows`](3-components/publish-workflows.md) |

## Relationships (plain English)

- Chat **runs** orchestrator turns; tools **write** transcript rows to SQLite.
- Cron **runs** ingest/graph CLIs and **keeps** the daemon alive; daemon **advances** workflows and may **call** the orchestrator for goal turns.
- Publish **DEPLOY** uploads `page.json` and merges `manifest.json`.
- HUD **reads** the DB only—it is not the agent.
