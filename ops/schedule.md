# ADA Ops Schedule (Raspberry Pi)

This document defines the production automation loop for ingestion, triage, nightly meta-synthesis enqueue, continuous daemon processing, and nightly dream compression.

## 1) Required cron schedule

Use these exact schedule lines as the canonical cadence:

```cron
0 */2 * * * ada ingest-rss
15 */2 * * * ada triage
0 23 * * * ada goal add "[META_SYNTH_24H] Review all new synthesis_edges and knowledge_synthesis records created in the last 24h. Merge isolated events into broader NZ market momentum, supply/demand gaps, and actionable Apex OS lead-generation opportunities. Produce one highly compressed consolidated summary for the 23:30 ada dream run. If there are no new rows in the last 24h, output a short 'no material updates' summary and exit normally (no failure). Hard output limit: maximum 600 words." --plan-json '{"ops_job":"nightly_meta_synthesis","tier":"meta","window_hours":24,"output_word_cap":600,"target_consumer":"ada_dream_2330"}'
30 23 * * * ada dream
```

For Raspberry Pi production, prefer explicit paths, virtualenv activation, and log files:

```cron
# Local timezone for all jobs in this file (recommended; see timezone section below)
CRON_TZ=Pacific/Auckland

0 */2 * * * cd /home/pi/ADA && . .venv/bin/activate && ada ingest-rss >> /home/pi/ADA/data/logs/ingest-rss.log 2>&1
15 */2 * * * cd /home/pi/ADA && . .venv/bin/activate && ada triage >> /home/pi/ADA/data/logs/triage.log 2>&1
0 23 * * * cd /home/pi/ADA && . .venv/bin/activate && /home/pi/ADA/ops/setup_cron.sh nightly-meta >> /home/pi/ADA/data/logs/nightly-meta.log 2>&1
30 23 * * * cd /home/pi/ADA && . .venv/bin/activate && ada dream >> /home/pi/ADA/data/logs/dream.log 2>&1
```

## 2) Nightly meta-synthesis enqueue (exact command)

Run this command at 23:00 local time:

```bash
ada goal add "[META_SYNTH_24H] Review all new synthesis_edges and knowledge_synthesis records created in the last 24h. Merge isolated events into broader NZ market momentum, supply/demand gaps, and actionable Apex OS lead-generation opportunities. Produce one highly compressed consolidated summary for the 23:30 ada dream run. If there are no new rows in the last 24h, output a short 'no material updates' summary and exit normally (no failure). Hard output limit: maximum 600 words." --plan-json '{"ops_job":"nightly_meta_synthesis","tier":"meta","window_hours":24,"output_word_cap":600,"target_consumer":"ada_dream_2330"}'
```

Notes:
- Prompt hardening is embedded directly in the goal text:
  - Explicit last-24h scope.
  - Fallback behavior (`no material updates`) when no new rows exist.
  - Strict output-size guard (max 600 words).
- Metadata remains within current architecture by using `task_kind=goal` with `plan_json` tags.

## 3) Tiered Triage Operating Model (for current architecture)

Current task model supports only `chat` and `goal`, so tiers are operationalized through goal text prefixes and/or `plan_json` metadata.

### Tier definitions

- Tier 1 (`impact_score` 8-10):
  - Use for macro shifts and hard-signal updates (policy changes, official data, concrete metrics).
  - Deep-dive output may write both `record_market_edge` and `record_synthesis`.
  - Prioritize numeric and date-anchored evidence.

- Tier 2 (`impact_score` 6-7):
  - Use for qualitative lead-generation opportunities and directional signals.
  - Write `record_synthesis` by default.
  - Write `record_market_edge` only when concrete numeric evidence is present.
  - Do not force metric edges for qualitative-only evidence.

### Representation pattern (no new schema/task kinds)

- Goal text prefix examples:
  - `[TIER1][KID:1234] Perform deep-dive synthesis on high-impact knowledge item ID: 1234`
  - `[TIER2][KID:5678] Perform qualitative lead-gen deep-dive on knowledge item ID: 5678`

- `plan_json` examples:

```json
{"triage_tier":"tier1","score_band":"8-10","knowledge_id":1234,"mode":"hard_signal"}
```

```json
{"triage_tier":"tier2","score_band":"6-7","knowledge_id":5678,"mode":"qualitative_lead_gen"}
```

### Queue governance and spend control

- Cap Tier-2 deep dives at max 10 per day to limit token spend and noise.
- Keep Tier-1 uncapped for score 8-10 unless system load requires emergency throttling.
- Operational enforcement options (without code/schema changes):
  - Prefix/filter goals via `ada goal list` and triage logs.
  - Optional wrapper script can skip enqueue when Tier-2 daily count reaches 10.

## 4) Systemd: continuous `ada daemon` worker

`ada daemon` should run continuously under systemd (not cron).

Create `/etc/systemd/system/ada-daemon.service`:

```ini
[Unit]
Description=ADA Goal Daemon
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

Enable and run:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ada-daemon.service
sudo systemctl status ada-daemon.service
```

## 5) Timezone guidance (cron + host)

Use a single explicit local timezone for production scheduling:

```bash
timedatectl
sudo timedatectl set-timezone Pacific/Auckland
timedatectl
```

Recommended cron hardening:
- Add `CRON_TZ=Pacific/Auckland` at top of crontab.
- Keep host timezone aligned (`timedatectl`) so logs and systemd timestamps match cron behavior.

## 6) Idempotency note for nightly meta enqueue

Nightly meta goal should enqueue once per night.

Recommended operational lock/check approach (documented; not schema/code change):
- Use a lockfile in `/tmp` or `/home/pi/ADA/data/locks/`.
- Before enqueue, check if a meta goal already exists today by querying recent goals for `ops_job=nightly_meta_synthesis` or `[META_SYNTH_24H]`.
- If already present, skip enqueue and exit 0.

Example check command:

```bash
ada goal list --status pending --limit 200 | rg "META_SYNTH_24H"
```

## 7) Runbook

### Install/update cron entries

```bash
mkdir -p /home/pi/ADA/data/logs
crontab -e
# Paste cron block from section (1), save, then:
crontab -l
```

Optional helper:

```bash
chmod +x /home/pi/ADA/ops/setup_cron.sh
/home/pi/ADA/ops/setup_cron.sh install-cron
crontab -l
```

### Reload/enable systemd daemon

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ada-daemon.service
sudo systemctl restart ada-daemon.service
sudo systemctl status ada-daemon.service
```

### Quick smoke tests

```bash
cd /home/pi/ADA && . .venv/bin/activate
ada ingest-rss
ada triage
ada goal add "[SMOKE] Confirm goal queue and daemon processing path."
ada dream --dry-run
```

### Verify Tier-1 vs Tier-2 behavior using existing fields/logs

Check queued and recent goal content:

```bash
ada goal list --limit 100
ada goal show <goal_id>
```

Expected operational markers:
- Goal text contains prefix `[TIER1]` or `[TIER2]`.
- `plan_json` includes `triage_tier` and `score_band`.
- `status` transitions: `pending` -> `executing` -> `completed` or `failed`.
- `current_output` reflects qualitative-only handling for Tier-2 unless numeric evidence is present.

Optional SQLite validation:

```bash
sqlite3 /home/pi/ADA/data/state.db "SELECT id,status,substr(goal,1,80),plan_json,updated_at FROM tasks WHERE task_kind='goal' ORDER BY id DESC LIMIT 30;"
```

## 8) Logs and verification commands

Verify cron firing:

```bash
crontab -l
rg "ingest-rss|triage|nightly-meta|dream" /home/pi/ADA/data/logs/*.log
```

Verify daemon health:

```bash
systemctl status ada-daemon.service
journalctl -u ada-daemon.service -n 200 --no-pager
```

Verify recent goal execution:

```bash
ada goal list --status pending --limit 20
ada goal list --status executing --limit 20
ada goal list --status completed --limit 20
ada goal list --status failed --limit 20
ada goal show <goal_id>
```
