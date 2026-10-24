# ADA Phase A contract

Phase A **freezes boundaries and documents** the daily operator surface. It does **not** add new domains, workflow kinds, or a unified motor package.

## In scope

- Documentation: core, allowlist manifest, memory, env migration, harness audit, greenfield checklist, graph scope, ops daily
- Slim profile template: [`profiles/jarvis.env.example`](../profiles/jarvis.env.example)
- Harness note when chat mission is bound (`_WORK_MODE_MISSION_NOTE`)
- Ops subset: doctor + Streamlit daily flags/tabs (`ADA_OPERATOR_FULL_UI`)
- Mission-over-env for **tick `gsc_site_url` + matrix `project_id`/`campaign_id` only** (A10)
- Restore `docs/` stubs referenced by README

## Out of scope (Phase A non-goals)

- New `workflow_kind`s, playbooks, or LLM tools (except docs/schemas)
- `ada/motor` package (Phase B)
- Voice, push notifications, HUD chat tab, programme compiler
- Deleting legacy code (mark deprecated only, e.g. `ada-control/lib/whitelist.py`)
- Loosening `insert_graph_edge`, file sandbox, or approval gates
- Ingest/triage/matrix-scan mission-over-env (Phase B)
- `get_mission_control_snapshot` in normal work chat (Phase B)
- Mission-required fail-fast CLI

## Operator decisions (locked)

| Topic | Decision |
|-------|----------|
| Chat | `ADA_CHAT_DEFAULT_MISSION=jarvis-ops` in jarvis template; unset env → global-capable chat |
| Job queue | Greenfield: `system_jobs`; code default remains `legacy` |
| A10 | Tick + matrix ISR keys only |

## Success criteria

- Stand up jarvis via [GREENFIELD_PROFILE.md](GREENFIELD_PROFILE.md)
- Explain ADA in [ADA_CORE.md](ADA_CORE.md)
- One allowlist: [ALLOWLIST_MANIFEST.md](ALLOWLIST_MANIFEST.md)
- Daily surface without maintaining full Streamlit
- Phase B motor handoff without re-litigating boundaries — see Phase B bullets in plan README / [ADA_CORE.md](ADA_CORE.md)

## Phase B handoff (motor)

1. `ada/motor/` single `execute()` routing rings 1–3 from allowlist manifest
2. CI drift test: manifest ↔ `build_agent_tools` + operator whitelist + shell file
3. Mission-bound snapshot in work chat
4. Consolidated host allowlist config
5. Optional `ADA_REQUIRE_CHAT_MISSION`
