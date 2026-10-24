# Memory ops — entity operator guide

Companion to [MEMORY_CONTRACT.md](MEMORY_CONTRACT.md) for **Friend / House / Lab** operators. Normative scope rules live in the contract; this doc covers **what to run**, **where data lands**, and **tag conventions** (not enforced in code yet).

See also: [ADA_ENTITY_BUCKETS.md](ADA_ENTITY_BUCKETS.md), [buckets/FRIEND.md](buckets/FRIEND.md), [TOOL_EXTENSION_GUIDE.md](TOOL_EXTENSION_GUIDE.md).

---

## Memory layers

| Layer | Storage | Write path | Read in Entity Chat |
|-------|---------|------------|---------------------|
| **Soul / master / wakeup** | Profile `memory_dir` (`soul.md`, `master.md`, `wakeup.md`) | `append_soul_fragment`, `append_master_section`; **`ada dream`** (transcript compression) | Injected into system prompt |
| **Base items** | Knowledge source `ada://memory/base` on `base_ops` | `run_primitive` → `log_memory` | `run_primitive` → `recall_memory` |
| **NULL kernel** | `knowledge_items`, graph rows with `mission_id IS NULL` | `add_knowledge_source`, `ada ingest-rss`, ingest skills | `search_knowledge`, `get_entity_graph_context` |
| **Mission overlay** | Mission-scoped knowledge + graph | Work chat, `ada programme apply`, Lab skills/workflows | Work session tools; Entity sees kernel only unless bridged |

Personal base memory (`ada://memory/base`) is **not** the global NULL-mission pool. See [MEMORY_CONTRACT.md](MEMORY_CONTRACT.md) § Knowledge / graph scope.

---

## Typed learning: `ada dream`

| Does | Does not |
|------|----------|
| Compress **chat transcript** (`messages`) into bounded **master** / **soul** markdown | Enrich `knowledge_items` or mission graph |
| Run manually: `ada dream` (`--dry-run`, `--session`, `--max-messages`) | Auto-merge Lab graph into `ada://memory/base` |
| Optional operator cron (external) | Replace `log_memory` for structured personal notes |

House may schedule `ada dream` on the profile; it is **not** a substitute for Friend `log_memory` / `recall_memory`.

---

## `log_memory` tag conventions

Normative for future specs and use-case docs — **not validated** in handlers today. Prefer short, lowercase, hyphenated tags.

| Tag | Use |
|-----|-----|
| `person` | Named contact, relationship note |
| `preference` | Likes, dislikes, standing prefs |
| `deadline` | Date-bound commitment |
| `lab-summary` | Operator-approved Lab → Friend bridge (see [ADA_ENTITY_BUCKETS.md](ADA_ENTITY_BUCKETS.md)) |
| `habit` | Recurring personal pattern (prefer primitive + tags over new mission) |
| `location` | Places, addresses (no secrets in tags) |

Example: `log_memory` with `content` and `tags: ["person", "preference"]`.

---

## Cron matrix (operator-owned)

ADA does not install crontab. You copy snippets from `{data_dir}/artifacts/cron/<slug>.snippet` after apply.

| Job | Bucket | Mission / scope | Notes |
|-----|--------|-----------------|-------|
| `ada brief --mission ada_ops` | House | `ada_ops` | Daily ops brief |
| `ada mission tick --mission ada_ops` | House | `ada_ops` | Schedule-aware tick / dry-run |
| `ada dream` | House | Profile transcript | Soul/master compression |
| `ada ingest-rss` | House (optional) | **NULL** kernel only | RSS pool on profile-global sources — not default `ada_ops` template |
| GSC / publish / ISR tick | Lab | Lab mission slug | Per-mission `defaults_json.gsc_site_url`; defer ISR until House loop is stable |
| Matrix / GSC on `ada_ops` | — | **Forbidden** on default ops cron | Use a Lab programme slug |

Full autonomic runbook: [ADA_CORE_OPS.md](ADA_CORE_OPS.md).

---

## Lab → Friend bridge

Lab work stays mission-scoped until the operator copies an approved summary into Friend:

1. Review Lab output (graph, brief, skill artifact).
2. Paste or paraphrase into Entity Chat (or HUD primitive).
3. `log_memory` with tag `lab-summary` (and optional `person` / `deadline`).

**Never:** silent graph→base merge, broad `ada consolidate`, or automatic promotion of mission rows to `ada://memory/base`.

---

## Pi smoke (entity memory path)

After [ADA_CORE_OPS.md](ADA_CORE_OPS.md) J-track boot assumptions:

1. `ada boot` — prints `base_ops` / `ada_ops` ids.
2. Entity Chat or HUD: `run_primitive` `log_memory` then `recall_memory` with a test phrase.
3. `run_primitive` `body_check` — use returned counts only.
4. `ada brief --mission ada_ops` (stdout brief; dry path acceptable).
5. Optional: `ada dream --dry-run` if dream cron is planned.

---

## Related docs

- [MEMORY_CONTRACT.md](MEMORY_CONTRACT.md) — hybrid scope, Entity tool allowlist
- [ADA_ENTITY_BUCKETS.md](ADA_ENTITY_BUCKETS.md) — Friend / House / Lab map
- [buckets/FRIEND.md](buckets/FRIEND.md) — primitives and personal memory
- [ADA_CORE_OPS.md](ADA_CORE_OPS.md) — `ada_ops`, cron, verification appendix
