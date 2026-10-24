# Mission control flags

Deterministic flags from SQLite — **no LLM inference**. Implemented in [`src/ada/mission_control/flags.py`](../src/ada/mission_control/flags.py).

## Daily flags (Phase A)

Surfaced in `ada doctor` and Streamlit Control plane:

| Flag ID | Severity | Meaning |
|---------|----------|---------|
| `profile_fingerprint_mismatch` | error | `ADA_PROFILE` / data root does not match `state.profile.*` |
| `gemini_api_key_missing` | warn | `GEMINI_API_KEY` unset |
| `system_jobs_dead` | warn | Dead `system_jobs` rows (when using `system_jobs`) |
| `mission_tick_job_overdue` | warn | Scheduled tick job past `min_interval_hours` |
| `chat_task_missing_mission` | warn | Latest chat task has no `mission_id` |
| `workflow_step_failed` | error | Recent failed workflow step |

## Ops pack (deferred UI)

Collected by `collect_flags` but not promoted to daily doctor/Streamlit in Phase A:

- `system_jobs_expired_lease`, `system_jobs_pending_stale`
- `mission_pending_*`, `mission_tick_never_ran`
- `gate_step_failed_recent`, `publish_deploy_blocked`, `global_budget_block`
- `kill_switch_active`, `messages_tombstoned_recent`
- `double_job_plane_risk`, `job_queue_mode_invalid`

See [`docs/OPS_DAILY.md`](OPS_DAILY.md).

## Recovery hints

Static strings in `flags.RECOVERY` — shown in HUD and setup snapshot.

## Setup assist

`ada chat --setup` exposes `get_mission_control_snapshot` (bounded JSON). See [`docs/mission-control-setup-assist.md`](mission-control-setup-assist.md) if present, or README.

## API

```python
from ada.mission_control.flags import collect_flags, flags_to_dicts
```

`profile_scope=True` includes env/profile/system_jobs checks. Pass `mission_id` + `mission_slug` for mission-filtered workflow/gate flags.
