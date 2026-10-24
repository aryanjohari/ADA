# Graph and mission scope

When `mission_id` is NULL vs mission-owned. Code: [`src/ada/persistent/store.py`](../src/ada/persistent/store.py), [`src/ada/mission_control/audit_scope.py`](../src/ada/mission_control/audit_scope.py).

## Intentional NULL (`mission_id IS NULL`)

| Table | Meaning |
|-------|---------|
| `entities` | Global triage `category` namespace; legacy pre-mission rows |
| `knowledge_sources` | Shared RSS pool — all missions may search via `(NULL OR mission_id = ?)` |
| `graph_edges` | Legacy ambiguous edges; still visible in scoped reads: `(ge.mission_id IS NULL OR ge.mission_id = ?)` |
| `tasks` / `workflows` | Operator omitted `--mission` on enqueue |

## Shared brain (not duplicated per mission)

- Triage `category` entities (`type=category`, `mission_id NULL`)
- `market_metrics`, synthesis tables
- Global knowledge pool

## Mission-owned (greenfield programme work)

- Programme entities: `entities.mission_id = <mission>`
- New edges: `insert_graph_edge` sets `mission_id` from endpoints; rejects cross-mission unless `classified_as` category bridge

## Bug indicators

- Mission programme entities with NULL `mission_id`
- Edges between two mission-owned entities left NULL after insert
- Run **`ada mission audit-scope <slug>`** — **ops CLI only**, not a chat tool

## Greenfield aspiration

After first graph activity on `jarvis-ops`, audit-scope should show zero NULL-mission edges touching mission entities (non-blocking).

## Chat scope

With `ADA_CHAT_DEFAULT_MISSION`, knowledge tools use mission filter + global kernel. See [MEMORY_CONTRACT.md](MEMORY_CONTRACT.md).
