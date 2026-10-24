# Mission knowledge isolation (Phase A)

## FTS and query layer

- `knowledge_items_fts` remains a single global FTS5 index; rowids still match `knowledge_items.id`.
- Mission filtering is enforced in SQL by joining `knowledge_items` → `knowledge_sources` and keeping rows where `mission_id IS NULL` (shared/global pool) or `mission_id` equals the consumer’s mission.
- FTS may still retrieve candidate rowids outside the mission before the join filters them; acceptable for modest corpora.

## Follow-ups if this becomes hot path

1. Composite index `(mission_id, id)` or similar on `knowledge_sources` if listing sources by mission dominates.
2. Partitioned or per-mission FTS (or external/content-table FTS) if profiling shows large multi-tenant regressions.
3. Optional strict mode (`ks.mission_id = ?` only, excluding globals) for hardened tenant isolation configs.
