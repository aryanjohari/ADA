# ada-control — compatibility launcher

The operator UI now lives in **`src/ada/observability/`** (bootstrap + env + profiles + memory + observability). This directory keeps a thin **`app.py`** that delegates to the package implementation.

## Run (Python 3.11+)

**Preferred:**

```bash
cd /path/to/ADA
python -m venv .venv && . .venv/bin/activate
pip install -e '.[streamlit]'
streamlit run scripts/ada_observability_app.py
```

**Still supported:**

```bash
pip install -e '.[streamlit]'
streamlit run ada-control/app.py
```

Or from `ada-control/` with the repo on `PYTHONPATH` / editable install: `streamlit run app.py`.

Set **ADA repo root** in the sidebar when it differs from the detected project root.

## Legend

- **`[dashboard only]`** — no ADA code changes; introspection and safe subprocesses only.
- **`ada chat --mission`** and **`ada chat --setup`** are implemented in `src/ada/cli.py` (mission-scoped knowledge tools + setup assist snapshot).
- **Control plane** flags: Streamlit Observability → **Control plane** tab (`src/ada/mission_control/`).

## Security

- No shell: subprocess uses `shell=False` and only **whitelisted** argv (see below).
- **`state.db`** is opened **`mode=ro`** (URI). The app does not write the database.
- The SQL sandbox allows a **single** `SELECT` / `WITH … SELECT` plus a block list (no `INSERT`, `UPDATE`, `ATTACH`, etc.).
- Optional **audit** rows: operator actions may append `action_log` kind **`operator_ui_bootstrap`** (see `docs/OPERATOR_LOGGING.md`).

## Whitelist source of truth

Canonical closed argv map: **`src/ada/observability/operator_whitelist.py`** (documented in [`docs/ALLOWLIST_MANIFEST.md`](../docs/ALLOWLIST_MANIFEST.md)).

`ada-control/lib/whitelist.py` is a **deprecated re-export** for older tests only — do not extend it.

## Whitelisted `ada` commands

Canonical whitelist: **`src/ada/observability/operator_whitelist.py`** (closed argv builder).

| Command | Writes SQLite | Network / keys |
|--------|---------------|----------------|
| `ada --help` | no | no |
| `ada mission list` | no | no |
| `ada mission show <slug>` | no | no |
| `ada goal list [--mission] [--status]` | no | no |
| `ada workflow status <id>` | no | no |
| `ada gate-failures [--limit] [--all-kinds]` | no | no |
| `ada mission tick --mission SLUG --dry-run` | no | no |
| `ada matrix-scan --dry-run [--mission] [--deterministic]` | no | no |
| `ada mission init …` | **yes** | no |
| `ada mission migrate-env <slug>` (no `--apply`) | no | no |

**Not whitelisted (use the real CLI):** `ada chat`, `ada daemon`, `ada goal add`, `ada workflow enqueue/retry`, ingest, triage, publish matrix without `--dry-run`, etc.

Mission slugs must match `^[a-z0-9][a-z0-9_-]{1,63}$` (same spirit as ADA CLI).

## Smoke env checklist

The **Env** tab compares your `.env` to `.env.example`. A minimal **convention** for any model-backed ADA use is `GEMINI_API_KEY` (see main ADA `README.md`). Profile / S3 / publisher keys depend on your deployment.

## Related docs (in main repo)

- `README.md` — data model & CLI
- `docs/operator-runbook-raspberry-pi.md` — cron / systemd
- `ops/schedule.md` — cadence snippets
- `.env.example`

`docs/operator-onboarding.md` is linked from the main README but may be missing in some trees; the panel does not depend on it.

## Tests (optional)

From repo root:

```bash
pytest ada-control/tests/
```
