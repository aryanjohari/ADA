# Mission control — setup assist contract

Setup assist is enabled with `ada chat --mission <slug> --setup` or `ADA_CHAT_SETUP_MODE=1`. It uses a **tight orchestration profile** (fewer tool rounds; web/GSC tools off by default) and a **read-only** `get_mission_control_snapshot` tool.

## Allowed

- Explain profile paths, mission slug, and schedule job ids from **SQL snapshot** or whitelisted CLI output.
- Call `get_mission_control_snapshot` for job/workflow/tick status (never guess).
- Allowlisted shell probes from `memory/shell_allowlist.txt` (read-only).
- Knowledge tools **with mission scope** when the chat task has `mission_id` set.
- Suggest `defaults_json` / cron edits as text for the operator to apply (Streamlit Profiles, `ada mission init`, or manual env).

Whitelisted `ada` subprocesses (Streamlit / operator UI only): see [`ada-control/README.md`](../ada-control/README.md) and `src/ada/observability/operator_whitelist.py`.

## Must refuse

- `ada daemon`, `ada workflow enqueue/retry`, live `ada mission tick`, live `ada matrix-scan`, `ada goal add`, ingest/triage/publish CLIs.
- Dumping raw `system_jobs.payload_json` or `.env` secrets into chat or workspace files.
- Operator-uploaded YAML/JSON in the system prompt.
- Ad-hoc SQL from the model.
- Cross-mission graph/knowledge writes when `mission_id` is NULL.

## Profile vs mission knobs

| Layer | Holds |
|-------|--------|
| Profile env | Secrets, paths, `ADA_JOB_QUEUE`, budgets, kill switch |
| `missions.defaults_json` | Playbook params |
| `missions.schedule_hint_json` | Tick schedule v1 |
| Playbooks | `allowed_params` / `required_params` in `playbooks/registry.yaml` |

## Related

- Flag catalog: [`mission-control-flags.md`](mission-control-flags.md)
- Job queue: [`JOB_QUEUE_SINGLE_OWNER.md`](JOB_QUEUE_SINGLE_OWNER.md)
- CLI: `ada mission status <slug>`, `ada doctor`
