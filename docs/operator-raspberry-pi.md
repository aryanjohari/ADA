# Operator runbook — Raspberry Pi (single profile)

Checklist for running one ADA profile on a Pi: one `state.db`, many missions, one job-queue owner.

## 1. Single-sourced environment

- [ ] Maintain **one** `.env` at a known path (e.g. `/home/pi/ada/.env` or profile data dir).
- [ ] Set `ADA_PROFILE` and `ADA_PROFILE_DATA_ROOT` (absolute path to profile data root).
- [ ] Optional: `ADA_MEMORY_DIR`, `ADA_POLICY_ROOT` if not using profile defaults.
- [ ] Set `ADA_JOB_QUEUE` to `legacy` **or** `system_jobs` — never run both planes (see [JOB_QUEUE_SINGLE_OWNER.md](JOB_QUEUE_SINGLE_OWNER.md)).
- [ ] Set `GEMINI_API_KEY` in `.env` only on the device; never commit.

**CLI and Streamlit must see the same values:**

- Shell: `set -a; source /path/to/.env; set +a` before `ada` commands.
- Streamlit operator: point sidebar **`.env path`** at the same file (loads with `override=False` for process env).

## 2. Paths and database

- [ ] `state.db` lives under `{ADA_PROFILE_DATA_ROOT}/{ADA_PROFILE}/state.db`.
- [ ] Run `ada doctor` after deploy; fix any `profile_mismatch` errors before starting daemon.
- [ ] SQLite uses **WAL**; Streamlit opens **read-only** URI — safe alongside one writer (`ada daemon`).

## 3. systemd / cron

- [ ] **One** long-running unit for `ada daemon` (example):

```ini
[Service]
EnvironmentFile=/home/pi/ada/.env
WorkingDirectory=/home/pi/ada/ADA
ExecStart=/home/pi/ada/venv/bin/ada daemon
Restart=on-failure
```

- [ ] Mission ticks via cron (not a second daemon), e.g. `ada mission tick --mission SLUG` — see `ops/schedule.md`.
- [ ] Do not start a second daemon if cron also runs goal polling elsewhere.

## 4. Missions and chat

- [ ] Create missions: `ada mission create ...`
- [ ] Mission-scoped chat: `ada chat --mission SLUG` (or `ADA_CHAT_DEFAULT_MISSION=SLUG`).
- [ ] First-time setup help: `ada chat --mission SLUG --setup` (or `ADA_CHAT_SETUP_MODE=1`).

## 5. Observability

- [ ] Operator UI: `streamlit run src/ada/observability/operator_streamlit.py` (same `.env` path in sidebar).
- [ ] Use **Missions** / **Job plane** tabs; raw `system_jobs` payloads hidden unless `ADA_OPERATOR_SHOW_JOB_PAYLOADS=1`.
- [ ] `ada jobs list` for CLI inspection.

## 6. Data semantics (multi-mission)

- [ ] **Graph / knowledge** are mission-scoped when tasks carry `mission_id`.
- [ ] **`market_metrics` / `synthesis_edges`** are **profile-global** (Business Kernel) — missions must not assume isolation there.
- [ ] **`ingest_jobs`** mission context is in `params_json` until a future schema adds `mission_id` (optional P2).

## 7. Smoke check (after changes)

1. `ada doctor` → exit 0, no `profile_mismatch`.
2. Sidebar Streamlit paths match `ada doctor` / `resolve_runtime_paths_from_environ`.
3. `ada jobs list --limit 5` (if `system_jobs` mode) — no duplicate workers on same DB.

## Optional: ingest_jobs mission column (P2)

Defer unless multi-mission ingest filtering in SQL becomes necessary. Until then, pass mission in ingest params and tag `system_jobs.mission_id` when enqueueing `ingest.run`.

## Daily brief timer (Phase C)

Deterministic brief (no LLM in cron path):

```bash
# After copying artifacts/cron/jarvis-ops.snippet from programme apply
0 7 * * * cd /home/pi/ada/ADA && set -a && source /home/pi/ada/.env && set +a && ada brief --mission jarvis-ops
```

Optional LLM synthesis via daemon:

```bash
0 7 * * * ... ada brief --mission jarvis-ops --enqueue
```

Example **systemd timer** (operator installs manually — ADA never writes crontab):

```ini
[Unit]
Description=ADA daily brief

[Timer]
OnCalendar=*-*-* 07:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

```ini
[Service]
Type=oneshot
EnvironmentFile=/home/pi/ada/.env
WorkingDirectory=/home/pi/ada/ADA
ExecStart=/home/pi/ada/venv/bin/ada brief --mission jarvis-ops
```
