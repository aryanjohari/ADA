# ada-control — Streamlit operator panel

**[dashboard only]** read-mostly UI for the ADA repo. It does **not** modify `src/ada/**`.

## Run (Python 3.11+)

```bash
cd /path/to/ADA
python -m venv .venv && . .venv/bin/activate
pip install -r ada-control/requirements.txt
streamlit run ada-control/app.py
```

Or from `ada-control/`:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Set **ADA repo root** in the sidebar if it is not the parent of `ada-control/`.

## Legend

- **`[dashboard only]`** — no ADA code changes; introspection and safe subprocesses only.
- **`[needs ADA change]`** — features called out in tabs (e.g. `ada chat --mission`) require work in `src/ada/`.

## Security

- No shell: subprocess uses `shell=False` and only **whitelisted** argv (see below).
- **`state.db`** is opened **`mode=ro`** (URI). The app does not write the database.
- The SQL sandbox allows a **single** `SELECT` / `WITH … SELECT` plus a block list (no `INSERT`, `UPDATE`, `ATTACH`, etc.).

## Whitelisted `ada` commands

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
