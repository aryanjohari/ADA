# Hands contract — motor enforcement (H5)

## Overview

Programme **packs** and **`skills_enabled`** constrain which catalog **Actions** (skills) may run via the motor skill layer: `run_skill`, `ada` motor CLI paths, and `MotorRequest` → `execute` with `layer="skill"`.

Apply/propose validate packets before writes. Motor enforces at execution time using the mission row in SQLite.

## When enforcement applies (D1)

| `missions.defaults_json.skills_enabled` | Motor `run_skill` | ProgrammeDigest |
|----------------------------------------|-------------------|-----------------|
| Missing or `[]` | No block (legacy missions) | `skills_enforcement: false` |
| Non-empty list | Skill id must be in list; if `pack` is known, also in pack allowlist | `skills_enforcement: true`, `pack` when set |

Empty or missing `skills_enabled` does **not** mean deny-all.

## Pack allowlists

Canonical allowlists live in `src/ada/programme/packs.py` (`PACK_SKILL_ALLOWLIST`). Apply/propose reject unknown packs and skills outside the pack. See [PROGRAMME_TEMPLATES.md](PROGRAMME_TEMPLATES.md).

## Motor validation order

1. Skill exists in registry.
2. `validate_skill_params` (mission_required, allowed/required params).
3. `validate_skill_for_mission` (H5): load mission by `mission_slug`; check `skills_enabled` and pack when enforcement applies.
4. Approval gates (`require_approval`, high-risk) unchanged.

## Error messages

- Not enabled: `skill 'publish_keyword_v1' not enabled on mission 'jarvis-ops' (skills_enabled: [...])`
- Pack violation: `skill 'publish_keyword_v1' not allowed for pack 'core-ops'`
- Apply/propose: `unknown skill id(s): [...]`, `pack 'core-ops' requires explicit skills_enabled`, pack allowlist errors from `validate_programme_skills`.

## Bypass (out of H5 scope)

Direct **workflow enqueue** (`enqueue_workflow_via_tool`, CLI `ada workflow enqueue`, internal enqueue) does not pass through the motor skill gate. Operators can still start pipelines outside `skills_enabled` on those paths; document and optional H5.1 follow-up.

Chat and Plan surfaces do not expose `run_skill`; enforcement is N/A there.

## Concierge routing (H6)

Chat and Plan harness notes include **Concierge routing** guidance (`format_concierge_routing_note` in `src/ada/prompt.py`):

| Operator intent | Preferred tools / context |
|-----------------|-------------------------|
| Vague research | `search_knowledge`, `get_entity_graph_context`, optional `web_search` |
| Profile status | `get_mission_control_snapshot` (profile scope), **ProfileDigest** |
| Named programme slug in message | ProfileDigest row or read-only **ProgrammeDigest** inject (turn > 0); never invent counts |
| Execution | Agent mode or Streamlit **Run action** — not `run_skill` in Chat/Plan |

**ProfileDigest** mission rows expose `pack`, `skills_enforcement`, and `brief_md_preview` (bounded) for programme index context without raw `defaults_json`.

## Agent harness

Agent mode system note: only `run_skill` ids in mission `skills_enabled` / pack. ProgrammeDigest exposes `pack`, `skills_enforcement`, and the resolved skills list.
