# Components — ada hud

Optional localhost Streamlit UI (`pip install -e ".[streamlit]"` then `ada hud`). **Not** the agent: no orchestrator socket and no arbitrary shell.

## Components

| ID | Role | Evidence |
|----|------|----------|
| `operator-app` | Streamlit shell: sidebar config + operator tabs | [`observability/app.py`](../../../src/ada/observability/app.py), [`operator_streamlit.py`](../../../src/ada/observability/operator_streamlit.py) |
| `db-ro` | Read-only SQLite (`mode=ro` URI) | [`observability/db_ro.py`](../../../src/ada/observability/db_ro.py) |
| `argv-whitelist` | Closed command id set (mission list, goal list, dry-runs, …) | [`operator_whitelist.py`](../../../src/ada/observability/operator_whitelist.py) |
| `whitelisted-subprocess` | Runs only allowlisted `ada` argv | [`operator_subprocess.py`](../../../src/ada/observability/operator_subprocess.py) |
| `sql-guard` | Restricts ad-hoc SQL to safe SELECT patterns | [`sql_guard.py`](../../../src/ada/observability/sql_guard.py) |

Compat launcher under [`ada-control/`](../../../ada-control/) is a thin deprecated shell around the same idea—prefer `ada hud`.
