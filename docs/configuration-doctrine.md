# Configuration doctrine

Operator-facing rules for where configuration lives, how layers interact, and what must not be duplicated. Goal: **low cognitive load** — env for transport and secrets, numeric policy for shared ceilings, prose memory for intent and persona, SQLite for per-run and workflow facts.

**Authoritative code:** [`src/ada/config.py`](../src/ada/config.py) (`Settings.load`), [`src/ada/policy/load.py`](../src/ada/policy/load.py) (`load_merged_policy`, `clamp_graph_lite_job_limits`), [`policies/default.yaml`](../policies/default.yaml), [`src/ada/db/schema.sql`](../src/ada/db/schema.sql).

---

## 1. Classification of `ADA_*` environment variables

Variables below are read by `Settings.load()` unless noted. A name may be **secret**, **path/hosting**, **rail**, or **provider**; “policy-only” vars are listed separately because they merge with YAML rather than filling `Settings`.

### 1.1 Secrets (env or secret manager only; never YAML)

Treat these like credentials. **Do not** paste them into `policies/*.yaml` or committed mission files.

| Variable | Role |
|----------|------|
| `ADA_JINA_API_KEY` | Jina Reader / fetch auth when used. |
| `ADA_SERPER_API_KEY` | Web search (Serper); falls back to `SERPER_API_KEY`. |
| `ADA_UNSPLASH_ACCESS_KEY` | Image API; falls back to `UNSPLASH_ACCESS_KEY`. |

**Related non-`ADA_*` secrets** (same rules): `GEMINI_API_KEY`; `DATAFORSEO_LOGIN` / `DATAFORSEO_PASSWORD`; `GSC_SERVICE_ACCOUNT_JSON` / `GSC_SERVICE_ACCOUNT_FILE`; AWS credentials (instance role or standard env); `S3_BUCKET_NAME` (or `ADA_S3_BUCKET` alias for the same bucket name).

### 1.2 Paths, hosting, tenant isolation

| Variable | Role |
|----------|------|
| `ADA_DATA_DIR` | Root for `state.db`, artifacts, audit (non-profile default under repo `data/`). |
| `ADA_COMMERCIAL_DATA_DIR` | Legacy alternate `data_dir` (mutually exclusive with profile vars). |
| `ADA_PROFILE` | Tenant slug; pairs with `ADA_PROFILE_DATA_ROOT`. |
| `ADA_PROFILE_DATA_ROOT` | Absolute parent directory for per-profile data dirs. |
| `ADA_MEMORY_DIR` | Soul/master/intent/allowlist location override. |
| `ADA_POLICY_ROOT` | Directory containing `default.yaml` (policy merge root). |
| `ADA_REQUIRE_PROFILE_ISOLATION` | Enforce profile + memory/policy outside project tree. |
| `ADA_FILE_SANDBOX_ROOTS` | File-tool sandbox roots (comma-separated). |
| `ADA_FILE_DENY_PREFIXES` | Extra deny prefixes for file tools. |
| `ADA_FILE_DENYLIST_FILE` | File listing additional denied paths. |
| `ADA_JINA_READER_URL` | Jina base URL; also honors `JINA_READER_BASE_URL`. |
| `ADA_GETS_POLL_URL` | NZ GETS poll endpoint default override. |

### 1.3 Global safety rails

| Variable | Role |
|----------|------|
| `ADA_KILL_SWITCH` | Daemon stops dequeuing goals (pending stays pending). |
| `ADA_DAILY_TOKEN_BUDGET` / `ADA_MONTHLY_TOKEN_BUDGET` | Global UTC caps on `usage_ledger`; blocks execution when exceeded. |
| `ADA_MAX_SESSION_TOKENS` | Per-session token ceiling (fail task when exceeded). |
| `ADA_MAX_TASK_STEPS` | Workflow enqueue rejected if template step count exceeds cap. |
| `ADA_MAX_TOOL_ROUNDS` | Agentic tool loop bound. |
| `ADA_PERSIST_DEBOUNCE_MS` | SQLite persist debounce. |
| `ADA_SHELL_MAX_OUTPUT_BYTES` / `ADA_SHELL_TIMEOUT_SEC` | Shell tool caps. |
| `ADA_STREAM_CHUNK_IDLE_SEC` / `ADA_STREAM_LEG_MAX_SEC` | Stream hardening. |
| `ADA_REWIRE_AFTER_TOMBSTONE` | Message graph behavior after tombstone. |
| `ADA_ENABLE_MEMORY_TOOLS` / `ADA_ENABLE_PLAN_TOOLS` / `ADA_ENABLE_GOAL_RECALL_TOOL` | Task/memory/plan tools. |
| `ADA_MEMORY_MAX_APPEND_BYTES` / `ADA_MEMORY_MAX_FILE_BYTES` | Memory I/O limits. |
| `ADA_DREAM_MAX_SOUL_BYTES` / `ADA_DREAM_MAX_MESSAGES` | Dream mode bounds. |
| `ADA_ENABLE_FILE_TOOLS` | File tools master toggle. |
| `ADA_FILE_MAX_READ_BYTES` / `ADA_FILE_MAX_WRITE_BYTES` / `ADA_FILE_MAX_LIST_ENTRIES` / `ADA_FILE_DENY_BASENAMES` / `ADA_FILE_AUDIT_DENIALS` | File tool limits and audit. |
| `ADA_ENABLE_WEB_TOOLS` / `ADA_ENABLE_WEB_SOURCES_TOOL` | Web tools. |
| `ADA_DEBUG_STREAM` | Verbose stream logging (operational hazard if left on in prod). |
| `ADA_ENABLE_KNOWLEDGE_TOOLS` | Knowledge tools. |
| `ADA_REQUIRE_APPROVAL_FOR_ENQUEUE` / `ADA_REQUIRE_APPROVAL_FOR_PUBLISH` | Human approval gates. |

### 1.4 Ingest and provider-specific

| Variable | Role |
|----------|------|
| **RSS / knowledge / embeddings / gate / triage** | `ADA_INGEST_RSS_*`, `ADA_KNOWLEDGE_*`, `ADA_KNOWLEDGE_EMBEDDINGS`, `ADA_KNOWLEDGE_EMBEDDING_*`, `ADA_KNOWLEDGE_DEFAULT_RETENTION_DAYS`, `ADA_INGEST_GATEKEEPER`, `ADA_INGEST_GATE_MODEL`, `ADA_INGEST_GATE_MAX_OUTPUT_TOKENS`, `ADA_TRIAGE_*`, `ADA_KNOWLEDGE_TOOL_*` |
| **Allowlists** | `ADA_WEB_FETCH_HOST_ALLOWLIST`, `ADA_KNOWLEDGE_FEED_HOST_ALLOWLIST`, `ADA_GOV_API_HOST_ALLOWLIST` |
| **Web fetch/search** | `ADA_WEB_SEARCH_*`, `ADA_WEB_FETCH_*`, `ADA_WEB_FETCH_MODE` |
| **Brand / keyword / gov** | `ADA_BRAND_*`, `ADA_KEYWORD_*`, `ADA_DATAFORSEO_USE_LIVE` |
| **Graph-lite / publish / enrich** | `ADA_ENABLE_GRAPH_LITE`, `ADA_GRAPH_LITE_*`, `ADA_PUBLISH_*`, `ADA_ENRICH_SUFF_*` |
| **Matrix** | `ADA_MATRIX_ENABLE`, `ADA_MATRIX_MAX_ENQUEUES`, `ADA_MATRIX_ENTITY_TYPES`, `ADA_MATRIX_PLANNER`, `ADA_MATRIX_PLANNER_LEGACY_FALLBACK`, `ADA_MATRIX_PLANNER_MODEL` |
| **Workflows** | `ADA_ENABLE_WORKFLOW_TOOLS` |
| **GSC** | `ADA_ENABLE_GSC_INGEST`, `ADA_GSC_*`, `ADA_ENABLE_GSC_READ_TOOLS`, `GSC_SITE_URL`, `GSC_AUTH_MODE`, `GSC_API_BASE_URL`, `GSC_SERVICE_ACCOUNT_*` (secrets in §1.1) |

Host/infra for publishing: `AWS_REGION`, `AWS_ENDPOINT_URL`, `S3_BUCKET_NAME` / `ADA_S3_BUCKET` (non-secret names; credentials are §1.1).

### 1.5 Policy plane (`ADA_*` that merge with `default.yaml`)

Consumed by `load_merged_policy()` in [`src/ada/policy/load.py`](../src/ada/policy/load.py), not as arbitrary `Settings` fields:

| Variable | Overrides YAML key / behavior |
|----------|-------------------------------|
| `ADA_POLICY_PACK` | Optional overlay file or directory (merged after `default.yaml`). |
| `ADA_INTENT_MAX_BYTES` | `intent_max_bytes` |
| `ADA_MATRIX_PLANNER_TOP_K` | `matrix_planner_top_k` |
| `ADA_GRAPH_LITE_POLICY_MAX_ITEMS` | `graph_lite_max_items_per_job` |
| `ADA_GRAPH_LITE_POLICY_TOKEN_CAP` | `graph_lite_token_cap_per_job` |
| `ADA_BATCH_ENRICH_MAX_ENTITIES` | `batch_enrich_max_entities` |
| `ADA_BATCH_ENRICH_MAX_TOOL_ROUNDS` | `batch_enrich_max_tool_rounds` |

### 1.6 Deprecated or consolidation candidates

Not removed from code; reduce reliance over time:

- **`ADA_COMMERCIAL_DATA_DIR`** — overlaps the documented **`ADA_PROFILE` + `ADA_PROFILE_DATA_ROOT`** model ([README §9.0a](../README.md)); prefer profiles for new deployments.
- **`S3_BUCKET_NAME` vs `ADA_S3_BUCKET`** — same semantic; pick one convention per environment.
- **Mission-shaped content in env** — e.g. `ADA_KEYWORD_TERMS`, `ADA_BRAND_SITE_URL` — candidates to move to **`workflows.params_json`** or a future **mission defaults** store so env stays transport + secrets.

---

## 2. Precedence and duplication rules

### Three planes (different jobs; not all comparable)

1. **`Settings` (environment)** — [`Settings.load()`](../src/ada/config.py) is the single parser for almost all runtime knobs. **Env wins** for those keys.

2. **Merged numeric policy (`PolicyConfig`)** — Merge order: **`default.yaml`** at the effective policy directory → **`ADA_POLICY_PACK`** overlays → **subset** of env overrides listed in §1.5. Malformed `default.yaml` when present → fail closed (`ValueError`).

3. **Prose memory** — **`memory/soul.md`**, **`memory/master.md`**: chat / daemon harness (`build_system_instruction`). **`memory/intent.md`**: data-plane goals; length capped by merged **`intent_max_bytes`**, not by duplicating those numbers in prose.

**Graph-lite special case:** CLI or env may set per-run limits; **`clamp_graph_lite_job_limits`** applies policy ceilings on top (env/CLI first, then clamp) — see [`policies/default.yaml`](../policies/default.yaml) header comment.

### Per-goal / workflow (today)

Stored in SQLite: **`tasks.goal`**, **`tasks.plan_json`**, **`workflows.params_json`**, **`workflow_steps.input_json` / `output_json`**. **`mission.defaults`** is **not** implemented as a first-class layer yet; until it exists, treat **enqueue params** as authoritative for that run.

### Must NEVER duplicate

- **Secrets or credential material in YAML policy** — repo policy is **numeric limits and toggles only** ([`policies/default.yaml`](../policies/default.yaml), [README §9.0](../README.md)).

- **Persona prose inside policy YAML** — keep policy numeric; soul/master stay in **`memory/`**.

---

## 3. Phase A: isolation (single DB vs database per mission)

**Doctrine:** Prefer **one `state.db` per deployment profile** and **scope missions inside the DB** (e.g. nullable **`mission_id`** on relevant rows + indexes), **unless** compliance requires filesystem-hard separation.

**Rationale:** One backup, one daemon process model, one observability target. Tables such as `knowledge_items`, `entities`, `workflows` are today **global to the DB**; adding a column is **additive**. **Separate SQLite files per mission** multiply systemd units, restores, and cross-mission queries — reserve for later or for the same reasons you use **`ADA_PROFILE`** for **customer-level** isolation ([README §9.0a](../README.md)).

**Containment:** **Strong isolation between customers** remains **`ADA_PROFILE`** + distinct env files (keys, `data_dir`). Mission scoping is **in-database organization within one tenant**.

---

## 4. Schema alignment

No new conceptual stores are required by this doctrine. Future **mission** linkage should align with existing tables:

| Area | Tables |
|------|--------|
| Work & chat | `tasks`, `messages`, `usage_ledger`, `state`, `action_log` |
| Workflows | `workflows`, `workflow_steps` (`parent_task_id` → `tasks`) |
| Knowledge | `knowledge_sources`, `knowledge_items`, `knowledge_synthesis`, optional embeddings / FTS |
| Graph | `entities`, `graph_edges`, `edge_evidence` |
| Ingest / analytics | `ingest_jobs`, `ingest_raw`, `analytics_providers`, `analytics_snapshots`, GSC tables |
| Approvals | `approval_records`, `campaign_opportunities` |
| Market kernel | `market_metrics`, `synthesis_edges` |

See full DDL in [`src/ada/db/schema.sql`](../src/ada/db/schema.sql).

---

## 5. Open decisions (max eight)

1. Is **mission** a first-class **row** (e.g. `missions` table) or a **naming convention** / `state` KV only?

2. Should **mission defaults** live in **DB JSON** (e.g. row or column) or **per-mission files under memory/**?

3. **Cross-mission knowledge:** partition `knowledge_items` with `mission_id`, or one corpus with filters?

4. **Token budgets:** add **per-mission** caps, or keep **global** day/month only (current `usage_ledger` behavior)?

5. **Retire `ADA_COMMERCIAL_DATA_DIR`:** timeline and migration path to **`ADA_PROFILE`**.

6. **Policy isolation:** should profile mode **fail closed** when it would fall back to repo `policies/` (today: stderr hint; stricter mode may be added)?

7. **Enqueue inheritance:** which **`params_json` keys** inherit from mission defaults vs must be explicit on each **`ada workflow enqueue`**?

8. **Phase A scope:** which tables get **`mission_id` first** (`tasks`, `workflows`, `knowledge_sources`, `entities`, …) so the graph and knowledge layers stay consistent?
