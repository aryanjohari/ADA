# House bucket

Autonomic nervous system — `ada_ops` only. Canonical map: [ADA_ENTITY_BUCKETS.md](../ADA_ENTITY_BUCKETS.md).

Depth: [ADA_CORE_OPS.md](../ADA_CORE_OPS.md) (do not duplicate that runbook here).

---

## Purpose

Daily brief, mission tick inspection, optional dream cron, NULL-kernel RSS only when **you** schedule it. House is **not** Entity chat and **not** ISR publish.

---

## `ada_ops` fields

Source: [`templates/missions/ada_ops.yaml`](../../templates/missions/ada_ops.yaml).

| Field | Value |
|-------|--------|
| Slug | `ada_ops` |
| Pack | `core-ops` |
| `skills_enabled` | `daily_brief`, `mission_tick_dry_run` |
| `schedule_hint_json` | `daily_brief` goal enqueue hint |
| `knowledge_sources` | `[]` (no default RSS on ops) |

Legacy Pi DBs may still show `jarvis-ops` until first `ada boot` (one-time rename to `ada_ops` when no collision).

---

## Recommended cron (copy-safe)

Install manually after `ada mission apply-template ada_ops`:

```cron
# Daily deterministic brief
0 7 * * * ada brief --mission ada_ops
# Mission tick (weekly example — adjust cadence)
0 6 * * 0 ada mission tick --mission ada_ops
```

Snippet file: `{data_dir}/artifacts/cron/ada_ops.snippet`.

Optional profile cron (not in default template):

```cron
# Transcript compression — example weekly
30 3 * * 0 cd /path/to/ADA && . .venv/bin/activate && ada dream >>/path/to/dream.log 2>&1
```

---

## Operator surfaces

| Surface | Use |
|---------|-----|
| Cron | `ada brief`, `ada mission tick` |
| CLI | `ada dream` (manual or scheduled) |
| Agent / HUD Run action | `daily_brief`, `mission_tick_dry_run` on `ada_ops` |
| Daemon | Dequeues goals — not `base_ops` personal todos |

---

## House must never

- Run `publish_entity_v1` / `publish_keyword_v1` on default `ada_ops` (pack H5 denies).
- Schedule matrix/GSC publish on `ada_ops` cron.
- Use Entity Chat `enqueue_workflow` for ops.
- Treat `ada dream` as knowledge-graph enrichment ([MEMORY_OPS.md](../MEMORY_OPS.md)).

---

## Related

- [FRIEND.md](FRIEND.md) · [LAB.md](LAB.md)
- [MEMORY_OPS.md](../MEMORY_OPS.md) — cron matrix, dream semantics
- [HANDS_CONTRACT.md](../HANDS_CONTRACT.md) — skill enforcement
