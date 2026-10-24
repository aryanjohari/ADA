# Memory & Knowledge Scope Contract

ADA uses a **hybrid scope** model: profile-global kernel plus mission-bound overlays.

## Task scope

| Ingress | `tasks.mission_id` | Transcript |
|---------|-------------------|------------|
| Entity (`OPEN`) | `NULL` | Global concierge session |
| Work (`WORK`) | Mission id | Mission-attached chat task |

## Knowledge / graph scope

| Row scope | Visible in Entity | Visible in Work |
|-----------|-------------------|-----------------|
| `mission_id IS NULL` (global kernel) | Yes | Yes (plus mission rows) |
| `mission_id = <mission>` | No (unless search explicitly crosses — tools use session mission in Work) | Yes |

Entity chat uses `ENTITY_KNOWLEDGE_TOOLS`: `search_knowledge`, `get_entity_graph_context`, `add_knowledge_source` (rss/web only, host allowlist). It does **not** expose `record_entity`, `record_edge`, or other graph writes — use Work or `ada programme apply`.

Work chat uses the full knowledge bundle when `ADA_ENABLE_KNOWLEDGE_TOOLS=1`.

## Persona files

| File | Scope | Entity writes |
|------|-------|---------------|
| `memory/master.md` | Profile | `append_master_section` (bounded) |
| `memory/soul.md` | Profile | `append_soul_fragment` (bounded) |

Entity implements on **master guardrails**, not arbitrary shell or raw `defaults_json` in the system prompt.

## Programme mutations

Mission rows, schedules, and RSS pools are written only via:

- `ada programme apply` (validated packet)
- `ada mission apply-template` (CLI / motor closed path)
- Cron: `artifacts/cron/*.snippet` only — never auto-install crontab

## Cross-mission reads

Profile-wide flags and mission lists appear in Entity `ProfileDigest` and `get_mission_control_snapshot(profile_scope=True)`. See [CROSS_MISSION_READ.md](CROSS_MISSION_READ.md).
