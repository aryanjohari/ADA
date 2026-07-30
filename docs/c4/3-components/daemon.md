# Components — ada daemon

Long-running worker: **one daemon per profile / `state.db`**. Do not mix `ADA_JOB_QUEUE=legacy` and `system_jobs` on the same database ([`JOB_QUEUE_SINGLE_OWNER.md`](../../JOB_QUEUE_SINGLE_OWNER.md)).

## Components

| ID | Role |
|----|------|
| **Job worker** | Poll loop in `ada daemon` ([`src/ada/main.py`](../../../src/ada/main.py), [`src/ada/jobs/worker.py`](../../../src/ada/jobs/worker.py)) |
| **Job plane** | `legacy` pending goal tasks **or** `system_jobs` rows (`goal.run_turn`, `workflow.start`, `ingest.run`, `matrix.scan`, …) |
| **Goal turns** | Background objectives that may invoke the shared orchestrator |
| **Workflow runner** | Executes step handlers for enqueued workflows |
| **Workflow templates** | Code-defined kinds only: `rss_fetch_then_graph_then_synth`, `publish_entity_v1`, `publish_keyword_v1` |

## Scheduling

The daemon itself is not an in-process cron. Host **cron / systemd** starts or supervises it and runs short one-shot CLIs separately ([`ops/schedule.md`](../../../ops/schedule.md)).
