# Operator logging (daemon / Pi)

Ada does not require a separate logging stack for normal operation. For **structured or durable logs** on a Raspberry Pi (or any Linux host), prefer the service manager:

- **systemd:** set `StandardOutput=journal` and `StandardError=journal` on the `ada daemon` unit, then use `journalctl -u your-unit -f` for a live tail.
- **Cron / one-shots:** redirect stdout and stderr to a file under your data directory, e.g. `>>/path/to/data/daemon.log 2>&1`, and rotate with `logrotate`.

Keep log files **off world-readable** paths if they might echo tool errors. Do not log environment variables that contain API keys.

## Operator UI audit (`action_log`)

The Streamlit operator app (`scripts/ada_observability_app.py`) may append SQLite **`action_log`** rows with kind **`operator_ui_bootstrap`**. Payloads are JSON and intentionally omit secrets; they include a **`client_action_id`** (UUID), an **`action`** discriminator (e.g. `env_snippet_generated`, `memory_save`, `whitelisted_ada`), optional **path digests** (hashes of absolute path strings), and a short **`argv_tokens`** prefix for whitelisted CLI runs.

- **Filter UI-driven rows:** `SELECT * FROM action_log WHERE kind = 'operator_ui_bootstrap' ORDER BY id DESC LIMIT 50;`
- **Distinguish from CLI:** most CLI subcommands log other `kind` values (see `README.md` `action_log` overview). UI rows are only emitted when an operator uses the Streamlit actions that perform audit logging.

Short writes use a SQLite busy timeout; avoid concurrent writes with a long-running `ada daemon` on the same `state.db` if you see lock errors.
