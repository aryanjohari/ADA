# Claude logic — norms and code pointers

Normative behavior for ADA’s harness is implemented in Python, not duplicated here. This document is the **index** operators and agents should follow.

## §1 Scope

- Single operator, local SQLite truth (`state.db` per profile).
- Model acts only through declared tools and allowlisted shell lines.
- No arbitrary SQL from the model (see `src/ada/tools/registry.py`).

## §2 Transcript (`messages`)

| Topic | Implementation |
|-------|----------------|
| §2.1 Schema / tombstone | [`src/ada/persistent/store.py`](../src/ada/persistent/store.py), [`src/ada/db/schema.sql`](../src/ada/db/schema.sql) |
| §2.2 Single writer | [`src/ada/query_engine.py`](../src/ada/query_engine.py) — debounced assistant persistence |
| §2.3 Load for API | `load_chain_for_api` — excludes `tombstone=1`, excludes `system` role |
| §2.4 Rewire after tombstone | `ADA_REWIRE_AFTER_TOMBSTONE` — [`src/ada/orchestrator.py`](../src/ada/orchestrator.py) |

Message JSON shape: [`src/ada/transcript_format.py`](../src/ada/transcript_format.py) — `parts[]` with `text` | `function_call` | `function_response`.

## §3 Message JSON

See `transcript_format.py` and README § transcript. Assistant rows may include `meta` (model, finish_reason, usage).

## §4 Sessions and tasks

- One `tasks` row per chat session (`task_kind=chat`) or queued goal (`task_kind=goal`).
- Mission binding: `tasks.mission_id` from `ada chat --mission` or `ADA_CHAT_DEFAULT_MISSION`.

## §5 Secrets

- Do not store API keys or credentials in workspace files the model can read.
- Operator UI redacts payloads: [`src/ada/observability/sanitize.py`](../src/ada/observability/sanitize.py) (dashboard only; not chat transcript).

## §6–7 Agentic loop and tools

| Component | File |
|-----------|------|
| Turn orchestration | [`src/ada/orchestrator.py`](../src/ada/orchestrator.py) |
| Streaming adapter | [`src/ada/gemini_stream.py`](../src/ada/gemini_stream.py) |
| Tool dispatch | [`src/ada/tool_executor.py`](../src/ada/tool_executor.py) |
| Tool declarations | [`src/ada/tools/registry.py`](../src/ada/tools/registry.py) |
| Allowlist manifest | [`docs/ALLOWLIST_MANIFEST.md`](ALLOWLIST_MANIFEST.md) |

## §8 Mission scope (knowledge / graph)

When `tasks.mission_id` is set, `knowledge_mission_scope` filters search to global kernel + mission-owned sources (`mission_id IS NULL OR mission_id = ?`). See [`docs/MEMORY_CONTRACT.md`](MEMORY_CONTRACT.md).

## §9 Job plane

One queue mode per `state.db`: [`docs/JOB_QUEUE_SINGLE_OWNER.md`](JOB_QUEUE_SINGLE_OWNER.md).

## §10 Operator surfaces

- Streamlit: SELECT-only SQL via [`src/ada/observability/sql_guard.py`](../src/ada/observability/sql_guard.py).
- Subprocess: `shell=False`, closed argv via [`src/ada/observability/operator_whitelist.py`](../src/ada/observability/operator_whitelist.py).

## §11 Memory files

| File | Harness |
|------|---------|
| `master.md` | Trusted `<master>` in [`src/ada/prompt.py`](../src/ada/prompt.py) |
| `soul.md` | Untrusted `<user_soul>` |
| `wakeup.md` | Boot user turn once per session |
| `intent.md` | **Not** in chat harness — data-plane only |

Appends: [`src/ada/memory_io.py`](../src/ada/memory_io.py). Dream: [`src/ada/dream/run.py`](../src/ada/dream/run.py).

## §12 System instruction

[`prompt.build_system_instruction`](../src/ada/prompt.py) — trusted harness only. Must **not** include `missions.defaults_json`, job payloads, or operator blobs.

Harness audit: [`docs/HARNESS_AUDIT.md`](HARNESS_AUDIT.md).

## Further reading

- [`docs/ADA_CORE.md`](ADA_CORE.md) — architecture
- [`docs/ADA_PHASE_A_CONTRACT.md`](ADA_PHASE_A_CONTRACT.md) — Phase A boundaries
