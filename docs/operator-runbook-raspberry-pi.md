# Operator runbook: Raspberry Pi, one profile

Single-site / single-client operation: one SQLite `state.db`, one data directory, one S3 prefix (`ADA_PROJECT_ID` / `ADA_CAMPAIGN_ID`). This runbook aligns with the code paths in `src/ada/main.py` (daemon), `src/ada/workflow/templates.py`, `src/ada/workflow/runner.py`, `src/ada/publish/matrix.py`, and `src/ada/config.py`.

## Hard rules

1. **One `ada daemon` per profile.** Run it under **systemd** (or one long-lived tmux session)—never schedule `ada daemon` from cron. Cron runs **short** commands only.
2. **Entity vs keyword** is which **scheduled jobs** you enable, not a single global “mode” env (unless you deliberately add one). You can run one track, both, or neither.
3. **Do not weaken** tool allowlists, file sandbox, or QueryEngine / PersistentState boundaries to ship faster. See [`claude_logic.md`](claude_logic.md) for transcript and security pointers.

---

## Two graph pipelines (do not conflate)

| Path | Commands / template | Populates |
|------|---------------------|-----------|
| **Cron / operator CLI graph** | `ada ingest-rss` → `ada triage` → `ada extract-graph-lite` | `entities`, `graph_edges`, `edge_evidence` from recent `knowledge_items` (batch Gemini JSON in `extract/graph_lite.py`) |
| **Legacy workflow graph** | Template `rss_fetch_then_graph_then_synth`: `FETCH` → **`EXTRACT`** → `SYNTHESIZE` | `EXTRACT` is a **workflow runner model step** in `workflow/runner.py`, **not** the same code as `extract-graph-lite` |

**Recommendation:** Standardize on **one** primary graph pipeline per site. If you still enqueue `rss_fetch_then_graph_then_synth` goals, document why (e.g. legacy synthesis) so operators do not assume a single graph source of truth.

---

## Entity publish track (matrix → entity workflows)

- **`ada matrix-scan`** scans publishable subject entities (with category edges) and enqueues **`publish_entity_v1` only** (`src/ada/publish/matrix.py`).
- **`ADA_MATRIX_ENABLE=1`** is required for real enqueues; **`ada matrix-scan --dry-run`** lists candidates without that flag.
- **`ADA_MATRIX_MAX_ENQUEUES`** caps how many entities are considered per run (default 20).
- **`ADA_MATRIX_ENTITY_TYPES`** optional comma list; default includes `service`, `regulation`, `organization`, `jurisdiction`.

**Matrix / PageProfile v1:** `PageProfileRegistry` and `profile_for` currently route every candidate to **`publish_entity_v1`** with `project_id` / `campaign_id` from env. **Niche** is derived from the triage **category code** (sanitized), not from dynamic per-entity-type tables—extend the code when you need richer routing.

**GATE (entity only):** `publish_entity_v1` steps are `ENRICH` → **`GATE`** → `DRAFT` → `DEPLOY`. **GATE** counts distinct non-empty `source_url` on active outgoing graph edges for the workflow `entity_id` and compares to **`ADA_PUBLISH_MIN_UNIQUE_FACTS`** (default 3). It does **not** apply to `publish_keyword_v1`.

**Publish approval (both kinds):** When **`ADA_REQUIRE_APPROVAL_FOR_PUBLISH=1`**, **`DEPLOY`** requires an approval row with `artifact_type=publish_deploy` and `artifact_ref=workflow:{workflow_id}:draft:{24-char-hash}` (hash of the validated draft `page` dict). The ref is easiest to copy from the daemon stderr / `action_log` entry `publish_deploy_blocked_no_approval` (`artifact_ref` in the payload).

---

## Keyword publish track (GSC → select → enqueue)

- **`ada ingest-gsc`** fills local `gsc_*` tables (**`ADA_ENABLE_GSC_INGEST=1`**, site URL, service account—see `.env.example`).
- **`ada keyword-select --entity-id ID --site URL --start-date YYYY-MM-DD --end-date YYYY-MM-DD`** prints **one JSON line** with `target_keyword_cluster`, `keyword_source`, `fallback_reason`; **exit code 1** if no cluster (script should stop).
- **`ada workflow enqueue --kind publish_keyword_v1`** with `--params-json` including **`project_id`**, **`campaign_id`**, **`niche`**, **`target_keyword_cluster`** (required by `workflow/templates.py`). Optional: **`--idempotency-key`** for safe reruns.

**GATE:** **`publish_keyword_v1`** has **no** `GATE` step (`ENRICH` → `DRAFT` → `DEPLOY`). **`ADA_REQUIRE_APPROVAL_FOR_PUBLISH`** still gates **`DEPLOY`** for keyword workflows the same way as entity workflows.

---

## Cron sketch (single profile)

Use explicit paths and one timezone. Adjust cadence to your pacing policy (see **Pacing** below).

```cron
# One TZ for the whole crontab
CRON_TZ=Pacific/Auckland

# Core knowledge + graph (example: twice daily)
0 6,18 * * * cd /home/pi/ADA && . .venv/bin/activate && ada ingest-rss >> data/logs/ingest-rss.log 2>&1
15 6,18 * * * cd /home/pi/ADA && . .venv/bin/activate && ada triage >> data/logs/triage.log 2>&1
45 6,18 * * * cd /home/pi/ADA && . .venv/bin/activate && ada extract-graph-lite >> data/logs/extract-graph-lite.log 2>&1

# Entity publish enqueue (example: daily; requires ADA_MATRIX_ENABLE=1 for non–dry-run)
30 7 * * * cd /home/pi/ADA && . .venv/bin/activate && ada matrix-scan >> data/logs/matrix-scan.log 2>&1

# Keyword track (example: weekly; set ADA_ENABLE_GSC_INGEST=1 and GSC_* env)
0 8 * * 1 cd /home/pi/ADA && . .venv/bin/activate && ./scripts/ada_keyword_track.sh >> data/logs/keyword-track.log 2>&1

# Optional: dream / meta goals — see ops/schedule.md (do not duplicate daemon here)
```

**Never** add a cron line that starts `ada daemon`. Use systemd below.

---

## Mission-parameterized schedules (multi-site in one profile)

Still **one** SQLite `state.db` and **one** `ada daemon` per profile (`ADA_DATA_DIR` / `ADA_COMMERCIAL_DATA_ROOT`). **`missions.slug`** scopes goals, workflows (`--mission`), and several ingest CLIs. Repeat the recipes below **per mission slug**—substitute **`$MISSION_SLUG`** and point each copy at that mission’s parameters (env file, `missions.defaults_json`, or operator shell exports).

**Conventions**

- **Workflow publishes:** always pass **`ada workflow enqueue … --mission "$MISSION_SLUG"`** so `tasks.mission_id` / `workflows.mission_id` are set and playbook params merge **`missions.defaults_json`** before `--params-json`.
- **Knowledge / graph (optional loop):** `ada ingest-rss --mission SLUG`, `ada ingest-gets --mission SLUG`, `ada extract-graph-lite --mission SLUG`, `ada triage --mission SLUG`.
- **`ada mission tick`** (optional): same DB; compares **`schedule_hint_json`** intervals against **`state`** keys **`mission.tick.<slug>.<job_id>`** (see appendix). Cron/systemd remains the authority for **when** the tick runs (e.g. hourly); tick rate-limits and runs **deterministic** steps only (**no matrix LLM planner**).

### Recipe: `GSC_keyword_publish_refresh`

Run in order (same cron row or sequential lines):

1. Ingest Search Analytics:

   ```bash
   ada ingest-gsc --site "$GSC_SITE" --days 28 \
     --dimensions "date,query,page,country,device" --row-limit 25000
   ```

2. Select keyword + enqueue (fail script if keyword-select exits 1):

   ```bash
   SEL="$(ada keyword-select \
     --entity-id "$KEYWORD_ENTITY_ID" \
     --site "$GSC_SITE" \
     --start-date "$KW_START" \
     --end-date "$KW_END")"
   ada workflow enqueue --kind publish_keyword_v1 \
     --mission "$MISSION_SLUG" \
     --goal "Publish keyword-led page: $(printf '%s' "$SEL" | jq -r .target_keyword_cluster)" \
     --params-json "$(printf '%s' "$SEL" | jq --arg pid "$ADA_PROJECT_ID" --arg cid "$ADA_CAMPAIGN_ID" --arg niche "$KW_NICHE" \
       '{target_keyword_cluster, keyword_source, project_id:$pid, campaign_id:$cid, niche:$niche}')"
   ```

Use the same pattern as [`scripts/ada_keyword_track.sh`](../scripts/ada_keyword_track.sh), or run that script with **`ADA_MISSION_SLUG`** set so the final enqueue is mission-tagged.

### Recipe: `matrix_entity_publish_refresh`

Deterministic entity queue (no LLM matrix planner):

```bash
ada matrix-scan --deterministic --mission "$MISSION_SLUG"
```

Requires **`ADA_MATRIX_ENABLE=1`** for real enqueues; **`--dry-run`** still lists candidates. If you use cron without `--deterministic`, ensure **`ADA_MATRIX_PLANNER=0`** so matrix-scan stays off the planner path.

### Cron matrix (per mission)

For **each** `MISSION_SLUG`, duplicate and adjust env (or use `/etc/ada/missions/<slug>.env` sourced by a thin wrapper):

- **Keyword refresh (example weekly, Monday 08:00):**

  ```cron
  0 8 * * 1 cd /home/pi/ADA && . .venv/bin/activate && \
    MISSION_SLUG=my-site-kw ADA_MISSION_SLUG=my-site-kw \
    /home/pi/ADA/scripts/ada_keyword_track.sh >> /home/pi/ADA/data/logs/keyword-track-my-site-kw.log 2>&1
  ```

- **Matrix entity refresh (example daily 07:30):**

  ```cron
  30 7 * * * cd /home/pi/ADA && . .venv/bin/activate && \
    MISSION_SLUG=my-site-entity ada matrix-scan --deterministic --mission my-site-entity \
    >> /home/pi/ADA/data/logs/matrix-scan-my-site-entity.log 2>&1
  ```

- **Optional tick fan-out (example hourly sanity check — tick still respects `min_interval_hours`):**

  ```cron
  17 * * * * cd /home/pi/ADA && . .venv/bin/activate && ada mission tick --mission my-site-combined >> data/logs/mission-tick-my-site-combined.log 2>&1
  ```

Keep **daemon** continuous under systemd once per profile—not per mission.

### systemd.timer sketches (recipe units)

Timers run **short** `ExecStart` commands; **never** invoke `ada daemon` from a timer.

**Keyword track timer** (`ada-keyword-track@.service` + `ada-keyword-track@.timer`): `ExecStart=` runs your wrapper exporting `MISSION_SLUG=%i` and calling `./scripts/ada_keyword_track.sh`. Set `EnvironmentFile=-/etc/ada/missions/%i.env`.

**Matrix timer:** `ExecStart=` `…/bin/ada matrix-scan --deterministic --mission %i` with `WorkingDirectory=` and `EnvironmentFile=/home/pi/ADA/.env`.

### Appendix: `missions.defaults_json` and `schedule_hint_json` (tick SSOT)

**`defaults_json`** (examples for playbook refresh; merge into workflow params when using `--mission`):

- `gsc_site_url` — Search Console property URL.
- `keyword_entity_id` — passed through for auditing / goal text; selection uses **`--site`** and dates.
- `keyword_start_date`, `keyword_end_date` — `YYYY-MM-DD` for **`keyword-select`** (if omitted during **`ada mission tick`**, computed from ingest window).
- `project_id`, `campaign_id`, `niche` — required for **`publish_keyword_v1`** enqueue (often mirror global env; storing them per mission avoids cross-mission mistakes).

**`schedule_hint_json` v1** (for **`ada mission tick`**) — illustrative only; cron decides wall-clock invocation:

```json
{
  "version": 1,
  "jobs": [
    {
      "id": "gsc_keyword_publish",
      "min_interval_hours": 168,
      "action": {
        "type": "gsc_keyword_publish",
        "ingest_days": 28,
        "dimensions": "date,query,page,country,device",
        "row_limit": 25000
      }
    },
    {
      "id": "matrix_entity_publish",
      "min_interval_hours": 24,
      "action": {
        "type": "matrix_entity_legacy_scan",
        "dry_run": false
      }
    }
  ]
}
```

---

## systemd: `ada daemon` (one unit per host profile)

Mirror of `ops/schedule.md` §4; keep **one** service.

```ini
[Unit]
Description=ADA goal and workflow daemon
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/home/pi/ADA
EnvironmentFile=/home/pi/ADA/.env
ExecStart=/home/pi/ADA/.venv/bin/ada daemon
Restart=on-failure
RestartSec=5
StandardOutput=append:/home/pi/ADA/data/logs/ada-daemon.log
StandardError=append:/home/pi/ADA/data/logs/ada-daemon.log

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ada-daemon.service
```

---

## Env matrix (one profile)

| Concern | Variables |
|--------|-----------|
| **Data / SQLite** | `ADA_DATA_DIR` **or** `ADA_COMMERCIAL_DATA_DIR` (latter wins for `data_dir` / `state.db`) |
| **S3 / ISR prefix** | `ADA_PROJECT_ID`, `ADA_CAMPAIGN_ID`; bucket: `S3_BUCKET_NAME` or `ADA_S3_BUCKET`; `AWS_REGION` + credentials |
| **Model** | `GEMINI_API_KEY`; model overrides per `.env.example` |
| **GSC (keyword track)** | `ADA_ENABLE_GSC_INGEST=1`, `GSC_SITE_URL` or `--site`, `GSC_SERVICE_ACCOUNT_JSON` or `GSC_SERVICE_ACCOUNT_FILE`, etc. |
| **Matrix (entity track)** | `ADA_MATRIX_ENABLE`, `ADA_MATRIX_MAX_ENQUEUES`, `ADA_MATRIX_ENTITY_TYPES` (optional) |

---

## “Don’t bleed money” and execution gates

| Variable | Effect |
|----------|--------|
| **`ADA_KILL_SWITCH`** | When truthy, **`ada daemon`** does not dequeue goals (tasks stay `pending`); enqueue CLIs may still insert work. |
| **`ADA_DAILY_TOKEN_BUDGET`** / **`ADA_MONTHLY_TOKEN_BUDGET`** | Optional **global** caps on summed `usage_ledger` tokens (input+output) for **current UTC** calendar day / month; daemon skips execution like kill switch when exceeded. |
| **`ADA_MAX_SESSION_TOKENS`** | Per-session / per-leg orchestration cap; exceeding fails the task (see `orchestrator.py`). |
| **`ADA_MATRIX_MAX_ENQUEUES`** | Caps **matrix-scan** candidate processing per invocation. |
| **`ADA_MATRIX_ENABLE`** | Must be on for matrix-scan to enqueue (except `--dry-run`). |
| **`ADA_REQUIRE_APPROVAL_FOR_ENQUEUE`** | `ada workflow enqueue` and **`ada matrix-scan`** enqueues go through **`workflow_enqueue`** approval (see below). |
| **`ADA_REQUIRE_APPROVAL_FOR_PUBLISH`** | **`DEPLOY`** blocked until **`publish_deploy`** approval (both **`publish_entity_v1`** and **`publish_keyword_v1`**). |

**UTC:** Day/month budgets use **UTC** boundaries in the daemon (`budget.py` / usage totals)—align expectations with cron local time.

---

## Approval flow (`ada approval`)

Subcommands: **`request`**, **`decide`**, **`show`** (`src/ada/approval_cli.py`). Durable rows in SQLite; no LLM.

### Enqueue gate (`ADA_REQUIRE_APPROVAL_FOR_ENQUEUE=1`)

- **`artifact_type`:** `workflow_enqueue`
- **`artifact_ref`:** If you passed **`--idempotency-key`** to `ada workflow enqueue` (or matrix-scan’s internal key `publish:{entity_id}:{hash}`), that **exact string** is the ref. If no idempotency key was used, the ref is a **24-character hash** of `{kind, goal, params}`—use `ada workflow enqueue` once, read stderr / logs for the blocked response fields `artifact_type` / `artifact_ref`, or precompute by always setting **`--idempotency-key`** for operator enqueues.

Example (matrix row known in advance—use dry-run to see idempotency keys):

```bash
ada approval request --artifact-type workflow_enqueue --artifact-ref 'publish:42:abcdef0123456789abcd' --reason 'nightly matrix'
ada approval decide --artifact-type workflow_enqueue --artifact-ref 'publish:42:abcdef0123456789abcd' --status approved --approved-by operator
```

### Publish / DEPLOY gate (`ADA_REQUIRE_APPROVAL_FOR_PUBLISH=1`)

1. Let the workflow reach **DRAFT** (or fail at DEPLOY once).
2. From **`publish_deploy_blocked_no_approval`** in `action_log`, or stderr: copy **`artifact_ref`** (form `workflow:{id}:draft:{hash}`).
3. Request + approve:

```bash
ada approval request --artifact-type publish_deploy --artifact-ref 'workflow:7:draft:0123456789abcdef01234567' --reason 'ISR deploy OK'
ada approval decide --artifact-type publish_deploy --artifact-ref 'workflow:7:draft:0123456789abcdef01234567' --status approved --approved-by operator
```

4. Re-run or let the daemon retry the goal per your retry policy.

---

## Pacing and ISR / Next.js

The **Next.js ISR consumer** is **out of this repository**. Keep the **`page.json` v1** contract stable: canonical schema in [`src/ada/publish/page_schema_v1.py`](../src/ada/publish/page_schema_v1.py); human summary in [`pseo-isr-contract.md`](pseo-isr-contract.md) and narrative in [`isr.md`](../isr.md).

**Operator pacing** (e.g. 1–2 new pages per day, sitemap refresh weekly/monthly) is enforced by **cron frequency**, **`ADA_MATRIX_MAX_ENQUEUES`**, and **approval gates**—not by a new autonomous “revenue” loop inside Ada.

---

## Related docs

- [`ops/schedule.md`](../ops/schedule.md) — ingest / triage / dream cron + systemd template (cross-schedule with this runbook).
- [`scripts/ada_entity_track.sh`](../scripts/ada_entity_track.sh), [`scripts/ada_keyword_track.sh`](../scripts/ada_keyword_track.sh) — shell wrappers for the two publish tracks.
- [`docs/legal-ops-checklist.md`](legal-ops-checklist.md) — ranking, leads, retention, PII (not legal advice).
