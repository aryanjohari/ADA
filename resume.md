# ADA

Ground-truth evidence for CV bullets and cover letters. Fill in every section with verified facts only.

## One-line summary

Headless Python asyncio agent harness for a local operator on edge devices (e.g. Raspberry Pi), with SQLite persistence, Google Gemini streaming chat, background goal worker, knowledge ingest, graph-lite extraction, and deterministic pSEO/ISR publish workflows to S3.

## Context

- **Role:** Solo developer [inferred from codebase — all 37 git commits attributed to Aryan Johari / `johari.aryan16@gmail.com`; no other contributors in `git shortlog`]
- **Dates:** Apr 2026 -- May 2026 [inferred from git: first commit `2026-04-06`, latest `2026-05-25`]
- **Institution / org:** N/A (personal project on GitHub under `aryanjohari`)
- **Links:** https://github.com/aryanjohari/ADA.git; demo URL not recorded; operator docs under `docs/` in repo

## Problem

Operators running a local AI assistant on constrained edge hardware need a durable agent loop (chat, background goals, scheduled ingest) without a hosted multi-tenant backend. The project also targets programmatic SEO / ISR page generation: ingest market signals (RSS, GSC, brand crawl, keywords), build a lightweight knowledge graph, gate publish quality on cited facts, draft structured `page.json`, and deploy to S3 for a separate Next.js consumer (documented as out of repo). Security and cost control matter: allowlisted shell, file sandboxes, token budgets, and human approval gates for risky actions.

## Your contributions

- Built the project end-to-end as sole committer [inferred from git history]
- Implemented core agent loop: `orchestrator.py` multi-leg Gemini streaming (`generate_content_stream`), manual function calling, tool rounds capped by `ADA_MAX_TOOL_ROUNDS`, tombstone/retry on failed legs [inferred from codebase]
- Designed SQLite persistence layer (`persistent/store.py`, `query_engine.py`): transcript chain (`messages` with `parent_uuid`, `sequence`, tombstones), tasks/goals, `usage_ledger`, `action_log`, schema migrations on connect
- Wrote `tool_executor.py` with env-gated tools: allowlisted shell, memory append (`master.md` / `soul.md` with backups), plan clipboard, workspace file sandbox, optional web search/fetch (Serper, httpx/Jina), knowledge search (FTS5 + optional embeddings), graph-lite record tools
- Built CLI entry surface (`ada` console script → `__main__.py`): chat REPL (Entity / Agent / Plan / Setup ingress modes), `ada daemon` worker, `ada goal`, `ada dream`, ingest/triage/graph CLIs, workflow enqueue/status/retry, `ada matrix-scan`, `ada hud` (Streamlit HUD)
- Implemented two-face Entity vs Work architecture (`chat_ingress.py`, `docs/ADA_CORE.md`): global concierge chat vs mission-scoped agent with `run_skill`
- Added mission/programme control plane: `missions` table, programme packets (`propose_programme` / `apply_programme`), mission templates under `templates/missions/`, `ada mission tick` with `system_jobs` job plane
- Built knowledge ingest pipelines: RSS (`ingest/rss.py`, `ada ingest-rss`), brand crawl, GSC Search Analytics, DataForSEO keywords, GETS tenders; triage with impact scoring; optional Gemini ingest gatekeeper
- Implemented graph-lite extraction (`extract/graph_lite.py`) and batch enrich (`enrich-graph`) over `entities` / `graph_edges` / `edge_evidence`
- Built deterministic publish workflows (`workflow/`): three template kinds — `rss_fetch_then_graph_then_synth`, `publish_entity_v1` (ENRICH → GATE → DRAFT → DEPLOY), `publish_keyword_v1` (no GATE); `page.json` v1 schema (`publish/page_schema_v1.py`); S3 deploy via boto3; optional WordPress CSV delivery
- Added motor/skills layer (`motor/`, `skills/*.yaml`): argv-whitelisted `run_skill` execution with approval gates for high-risk skills
- Built optional Streamlit operator HUD (`observability/app.py`, `ada hud`): read-only SQLite queries, whitelisted subprocess actions, mission flags/snapshots — not an in-process agent
- Wrote operator documentation (57 markdown files in `docs/`): Raspberry Pi runbook, pSEO/ISR contract, cron/systemd patterns, backup/logging, legal-ops checklist
- Set up GitHub Actions CI (`.github/workflows/ci.yml`): pytest on Python 3.11 and 3.12; publisher tests use moto for S3 mocking
- Authored test suite: 531 test functions across 127 test files under `tests/` [counted via `rg` on `^def test_|^async def test_`]

## Tech stack

Python 3.11+, asyncio, setuptools, google-genai, aiosqlite, SQLite (WAL), Pydantic, PyYAML, httpx, feedparser, boto3, pytest, pytest-asyncio, moto, Streamlit (optional), python-dotenv (optional), GitHub Actions, Gemini API, AWS S3, Serper API (optional, web search), Jina Reader (optional, web fetch), Google Search Console API (optional ingest), DataForSEO API (optional keyword ingest), systemd and cron (documented operator deployment on Raspberry Pi)

## Architecture (optional but helpful)

Single-process local harness; one `state.db` per profile (`ADA_PROFILE` / `ADA_PROFILE_DATA_ROOT` for multi-tenant isolation).

| Path | Role |
|------|------|
| `src/ada/orchestrator.py` + `adapters/gemini_stream.py` | Model turn loop, streaming, timeouts |
| `src/ada/persistent/store.py` + `db/schema.sql` | All SQL DDL (27 tables), migrations |
| `src/ada/query_engine.py` | App-facing DB API, debounced assistant stream flushes |
| `src/ada/tool_executor.py` + `tools/registry.py` | Tool dispatch and Gemini declarations |
| `src/ada/chat_session.py` + `chat_ingress.py` | REPL + ingress mode resolution |
| `src/ada/daemon_goal.py` + `jobs/worker.py` | Background worker (`legacy` goals or `system_jobs`) |
| `src/ada/workflow/` | Template expansion, step runner (FETCH/EXTRACT/SYNTHESIZE/ENRICH/GATE/DRAFT/DEPLOY) |
| `src/ada/ingest/` + `extract/` + `triage/` | Offline data-plane batch jobs |
| `src/ada/publish/` | Matrix scan, draft JSON, S3/CSV deploy |
| `src/ada/motor/` + `skills/` | YAML-defined operator skills |
| `src/ada/mission_control/` + `observability/` | HUD snapshots, flags, Streamlit UI |
| `memory/` | Persona files (`soul.md`, `master.md`, `wakeup.md`, shell allowlist) |
| `policies/default.yaml` | Numeric policy limits (no prose prompts) |
| `playbooks/registry.yaml` | Named workflow parameter allowlists |

Data flow (publish track): cron `ada ingest-rss` → `ada triage` → `ada extract-graph-lite` → optional `ada enrich-graph` → `ada matrix-scan` enqueues `publish_entity_v1` → `ada daemon` runs ENRICH/GATE/DRAFT/DEPLOY → S3 `page.json` + `manifest.json` per `docs/pseo-isr-contract.md`.

## Outcomes & metrics (verified only)

| Metric | Value | How measured | Notes |
|--------|-------|--------------|-------|
| Git commits | 37 | `git rev-list --count HEAD` | Solo author in history |
| Active development window | ~7 weeks | First commit 2026-04-06, latest 2026-05-25 | From `git log` |
| Python source files (`src/ada/`) | 152 | `find src/ada -name '*.py' \| wc -l` | |
| Python LOC (`src/ada/`) | ~44,767 | `wc -l` on `src/ada/**/*.py` | Includes blanks/comments |
| Test functions | 531 | `rg` count of `^def test_\|^async def test_` in `tests/` | |
| Test files | 127 | `find tests -name 'test_*.py' \| wc -l` | |
| SQLite tables in canonical schema | 27 | `CREATE TABLE` count in `src/ada/db/schema.sql` | |
| Workflow template kinds (code-defined) | 3 | `WORKFLOW_KINDS` in `workflow/templates.py` | `rss_fetch_then_graph_then_synth`, `publish_entity_v1`, `publish_keyword_v1` |
| Motor skill YAML specs | 6 | Files in `skills/` | |
| Mission programme templates | 7 | Files in `templates/missions/` | |
| Playbook definitions | 3 | `playbooks/registry.yaml` | `ingest_rss_summarize`, `publish_entity_v1`, `publish_keyword_v1` |
| Operator markdown docs | 57 | `find docs -name '*.md' \| wc -l` | |
| CI Python versions | 3.11, 3.12 | `.github/workflows/ci.yml` matrix | |
| Default GATE minimum unique facts | 3 | `ADA_PUBLISH_MIN_UNIQUE_FACTS` default per README | Applies to `publish_entity_v1` only |
| Default matrix enqueue cap per scan | 20 | `ADA_MATRIX_MAX_ENQUEUES` per `docs/operator-runbook-raspberry-pi.md` | |
| Production users / traffic | not recorded | | |
| Model accuracy / benchmark scores | not recorded | | |
| Revenue or lead counts | not recorded | | |

## Keywords for tailoring

Python, asyncio, agent harness, LLM tool calling, Google Gemini, SQLite, edge computing, Raspberry Pi, CLI design, pytest, workflow engine, programmatic SEO, ISR, S3, knowledge graph, RSS ingest, Search Console, Streamlit, operator tooling, allowlist security, token budgets, human-in-the-loop approvals

## Do not claim

- Production traffic, paying customers, or enterprise deployments — not documented in repo
- Multi-engineer team or team lead role — git history shows solo authorship only
- Hosted SaaS or multi-tenant cloud service — README states "no hosted multi-tenant session ingress"
- Full RAG over chat transcript, vector DB, MCP transport, or plugin DAGs — listed as not implemented or north-star in README §1 and §14
- Built-in in-process scheduler — cron/systemd documented as external operator responsibility
- Next.js ISR consumer app — explicitly out of repo per `docs/pseo-isr-contract.md`
- Automated scheduled dream mode — only manual `ada dream` + external cron documented
- Embeddings enabled by default — requires `ADA_KNOWLEDGE_EMBEDDINGS=1`
- Commercial scale metrics (users, pages published, API QPS) — not recorded
- Legal/compliance certification — `docs/legal-ops-checklist.md` is operator checklist, not legal advice

## Suggested CV tags

`python, asyncio, llm-agents, sqlite, edge-iot`

Alternative sets: `backend, cli, workflows, aws-s3` or `ml-ops, gemini, pytest, streamlit`

## Open questions for Aryan

- Confirm **role label** for CV: solo founder, side project, capstone, or contract work?
- Confirm **dates** for CV: use Apr 2026 -- May 2026, or is development ongoing past 2026-05-25?
- Did this **deploy to production** on a Raspberry Pi or VPS with real S3 publishes, or is it lab/demo/WIP only? [VERIFY]
- Any **verified metrics** to add: pages deployed, feeds ingested, token spend caps hit, Pi hardware model?
- Is there a **live demo URL**, deployed ISR site, or public case study beyond the GitHub repo?
- Was the **Next.js ISR consumer** built separately by you, and should it be cross-referenced on the CV?
- Any **institution or org** affiliation (university, employer, client name) for context section?
- Confirm whether **DataForSEO**, **GSC**, or **GETS** integrations were used in a real operator profile or only implemented/tested in code
