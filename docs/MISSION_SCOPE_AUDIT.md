# Mission scope audit (substrate)

**Principle:** `missions.id` is the canonical scope for mission-owned rows. Slugs are UX and CLI entrypoints. Global rows use `mission_id IS NULL` only where intentionally shared (e.g. triage taxonomy parents, legacy pool).

## Graph

| Path | Mission filter |
|------|----------------|
| `PersistentState.insert_graph_edge` | Endpoints must share `mission_id` (or narrow `classified_as` bridge to category entities). |
| `load_subject_subgraph_context_pack(..., mission_scope=…)` | Restricts edges to matching `graph_edges.mission_id` (or legacy NULL). |

## Knowledge

| Area | Notes |
|------|--------|
| `knowledge_sources.mission_id` | Nullable = legacy global pool; otherwise scoped. |
| FTS / search helpers | Prefer passing mission filter where the query joins `knowledge_sources` or mission-tagged items. |

## Workflows / tasks

| Area | Notes |
|------|--------|
| `tasks.mission_id`, `workflows.mission_id` | Set when attaching to a mission. |
| `system_jobs.mission_id` | Set at ingress (ticks, `try_enqueue_ingest_run`, goal enqueue from task’s mission). |

## Ingest

| Area | Notes |
|------|--------|
| `ingest_jobs` | No `mission_id` on row (Phase 1); scope for observability comes from **`system_jobs.mission_id`** when enqueueing `ingest.run`. |

This matrix is the checklist for new readers and PRs that touch isolation boundaries.
