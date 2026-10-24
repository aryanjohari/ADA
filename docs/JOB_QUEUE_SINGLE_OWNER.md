# Job queue — single owner per `state.db`

ADA supports two **mutually exclusive** job planes. Running both against the same `state.db` risks double execution and lease conflicts.

## Modes

| `ADA_JOB_QUEUE` | Daemon behavior | Typical use |
|-----------------|-----------------|-------------|
| `legacy` (code default) | Polls `tasks` where `task_kind=goal` and `status=pending` | Existing installs |
| `system_jobs` | `run_system_jobs_plane_loop` — claims rows in `system_jobs` | **Greenfield** ([`profiles/jarvis.env.example`](../profiles/jarvis.env.example)) |

Mission tick (`ada mission tick`) enqueues **`system_jobs`** rows even when the daemon runs in `legacy` mode. The worker must match your chosen plane.

## Rules

1. **One plane per database** — pick `legacy` **or** `system_jobs` for each profile’s `state.db`.
2. **One daemon process** per profile DB when using `system_jobs` (lease reclaim assumes single worker).
3. Do not run a legacy goal-polling daemon and a `system_jobs` worker on the same DB simultaneously.
4. Flag `double_job_plane_risk` (profile scope) reminds you to read this doc; it does not block startup.

## Greenfield

Set in profile `.env`:

```bash
ADA_JOB_QUEUE=system_jobs
```

Start work with:

```bash
ada daemon
# or inspect: ada jobs list
```

## Legacy migration

1. Drain or cancel pending goals/workflows you care about.
2. Set `ADA_JOB_QUEUE=system_jobs`.
3. Restart **only** the system_jobs daemon.
4. Run `ada doctor` — no `system_jobs_dead` / lease warnings.

## CLI reference

| Command | Plane |
|---------|--------|
| `ada daemon` | Dispatches per `ADA_JOB_QUEUE` |
| `ada jobs list` / `status` / `retry` / `cancel` | `system_jobs` only |
| `ada goal add` | Creates `tasks` rows; legacy daemon dequeues goals |

## Code pointers

- Config: [`src/ada/config.py`](../src/ada/config.py) — `Settings.ada_job_queue`
- Daemon branch: [`src/ada/main.py`](../src/ada/main.py)
- Schema: [`src/ada/db/schema.sql`](../src/ada/db/schema.sql) — `system_jobs` table
- Flags: [`src/ada/mission_control/flags.py`](../src/ada/mission_control/flags.py) — `job_queue_mode_invalid`, `double_job_plane_risk`
