# Skill spec (motor registry)

Skills live in `skills/<id>.yaml` and load into the motor registry alongside playbooks.

## Schema

| Field | Required | Description |
|-------|----------|-------------|
| `id` | yes | Stable skill id |
| `description` | yes | Operator-facing summary |
| `risk_tier` | yes | `low` \| `medium` \| `high` |
| `ring` | yes | Manifest ring (typically `2`) |
| `motor_type` | yes | `workflow_enqueue` \| `ada_argv` \| `internal_fn` \| `goal_add` |
| `playbook_id` | when enqueue | Playbook registry id |
| `workflow_kind` | optional | Workflow kind hint |
| `op_command_id` | when ada_argv | Operator `CommandId` |
| `allowed_params` | no | Param allowlist |
| `required_params` | no | Required param names |
| `mission_required` | no | Default false |
| `require_approval` | no | Default false |

## Seed skills

- `daily_brief` — `goal_add` (SQL-grounded brief text; optional `goal_text` param)
- `weekly_research_goal` — `goal_add`
- `ingest_rss_mission` — `workflow_enqueue` → `ingest_rss_summarize`
- `publish_entity_v1` / `publish_keyword_v1` — high-risk enqueue
- `mission_tick_dry_run` — `ada_argv` dry-run tick

## Chat tool

`run_skill(skill_id, params_json?, mission_slug?, approved?)` → `motor.execute` with validation and `action_log` kind `motor_skill_run`.
