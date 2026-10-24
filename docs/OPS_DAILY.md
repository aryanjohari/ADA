# Daily ops surface (Phase A)

Frozen subset of flags, CLI, and Streamlit. Full ops pack remains in code but is hidden unless `ADA_OPERATOR_FULL_UI=1`.

## Six daily flags

Promoted in `ada doctor` and Streamlit Control plane:

1. `profile_fingerprint_mismatch`
2. `gemini_api_key_missing`
3. `system_jobs_dead`
4. `mission_tick_job_overdue`
5. `chat_task_missing_mission`
6. `workflow_step_failed`

All other flags: see [mission-control-flags.md](mission-control-flags.md) (ops pack).

## Five daily commands

1. `ada chat`
2. `ada doctor`
3. `ada daemon` (single job plane)
4. `ada mission list` / `ada mission tick --mission <slug>`
5. `ada dream` or `ada ingest-rss`

## Streamlit (daily)

| Visible | Hidden unless `ADA_OPERATOR_FULL_UI=1` |
|---------|------------------------------------------|
| Setup | Env, Profiles, Memory, Playbooks |
| Observability → Control plane | Overview, Tasks, Goal outputs, Workflows, Usage, Action log, Caps, Job plane |
| Observability → Missions | (same hidden sub-tabs) |

## Doctor

[`src/ada/doctor.py`](../src/ada/doctor.py) — `DAILY_FLAG_IDS` + `single_owner_reminder` only.
