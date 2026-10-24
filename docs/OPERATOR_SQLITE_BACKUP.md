# SQLite backup and restore (operator drill)

This note covers Ada’s primary SQLite file, `state.db` (under `ADA_DATA_DIR`, `ADA_COMMERCIAL_DATA_DIR`, or the profile path from `ADA_PROFILE` + `ADA_PROFILE_DATA_ROOT`). The daemon and CLI use WAL mode; treat hot copies with care.

## Preferred: logical backup with sqlite3

1. **Stop the writer** (`ada daemon` and any other process using that `state.db`) so the file set (`state.db`, `-wal`, `-shm`) is quiescent.
2. Run a backup into a new file:

```bash
sqlite3 /path/to/state.db ".backup '/path/to/state-backup-$(date -u +%Y%m%d).db'"
```

3. Confirm the backup opens read-only:

```bash
sqlite3 "file:/path/to/state-backup.db?mode=ro" "PRAGMA integrity_check;"
```

## Filesystem copy (when daemon is stopped)

With the daemon stopped, copy `state.db` and, if present, `state.db-wal` and `state.db-shm` together, or copy only after a clean checkpoint (simplest is still to use `.backup` above).

**Hot copy caveat:** copying `state.db` while another process writes can produce an inconsistent snapshot unless you use the SQLite backup API or stop writers first.

## Restore drill

1. Stop Ada processes using the database.
2. Move aside the current `state.db` (rename, not delete, until you verify).
3. Restore from your backup file by copying it to `state.db` (or use `.backup` from the good file into a fresh `state.db`).
4. Start `ada daemon` and spot-check: `ada goal list`, `ada workflow status` (if you use workflows).

## Optional observability dashboard

The read-only Streamlit dashboard (`streamlit run scripts/ada_observability_app.py` after `pip install -e ".[streamlit]"`) opens `state.db` with `mode=ro`. For a **frozen** forensic snapshot, point the app at a **backup copy** (set `ADA_DATA_DIR` to the directory containing the copied file, named `state.db`) rather than the live file.
