# Components — ada daemon

Long-running worker: **one daemon per profile / `state.db`**. Do not mix `ADA_JOB_QUEUE=legacy` and `system_jobs` on the same database.

## Components

| ID | Role | Evidence |
|----|------|----------|
| `job-worker` | Poll loop in `ada daemon` | [`main.py`](../../../src/ada/main.py), [`jobs/worker.py`](../../../src/ada/jobs/worker.py) |
| `job-plane` | `legacy` pending goal tasks **or** `system_jobs` rows | `ADA_JOB_QUEUE` in config; worker plane loop |
| `goal-turns` | Background objectives that may invoke the shared orchestrator | [`daemon_goal.py`](../../../src/ada/daemon_goal.py) |
| `workflow-runner` | Executes step handlers for enqueued workflows | [`workflow/runner.py`](../../../src/ada/workflow/runner.py) |
| `workflow-templates` | Code-defined kinds only | [`workflow/templates.py`](../../../src/ada/workflow/templates.py): `rss_fetch_then_graph_then_synth`, `publish_entity_v1`, `publish_keyword_v1` |
| `system-jobs-handlers` | `workflow.start`, `ingest.run`, matrix / tick slices | [`jobs/handlers.py`](../../../src/ada/jobs/handlers.py) |

## Scheduling

The daemon itself is not an in-process cron. Host **cron / systemd** starts or supervises it and runs short one-shot CLIs separately ([`ops/schedule.md`](../../../ops/schedule.md)).
