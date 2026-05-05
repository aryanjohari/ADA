"""
ADA operator panel — read-mostly Streamlit UI.
Run from repo root: streamlit run ada-control/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

st.set_page_config(page_title="ADA control", layout="wide")

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # type: ignore[misc]

from lib.db_ro import (
    connect_ro,
    costs_aggregate,
    missions_tasks_preview,
    observability_action_recent,
    observability_preset_failed_steps,
    overview_stats,
    run_safe_select,
    table_exists,
)
from lib.env_check import (
    SMOKE_REQUIRED_KEYS,
    keys_from_env_example,
    parse_dotenv_file,
)
from lib.paths_resolve import resolve_data_dir, resolve_memory_dir, resolve_state_db_path
from lib.schedule_audit import crontab_ada_commands, overlap_heuristic, parse_markdown_schedules
from lib.run_ada import AdaRunResult, format_result_for_logs, run_ada
from lib.sql_guard import validate_select_only
from lib.whitelist import WHITELIST_META, build_argv

CRON_COOKBOOK = r"""
**[dashboard only]** Copy-paste recipes; adjust paths, user, and logs.

**Rules (from runbook):** never put `ada daemon` in cron — use systemd. Cron = short commands only.

```cron
CRON_TZ=Pacific/Auckland

# Core knowledge + graph (example)
0 6,18 * * * cd /home/pi/ADA && . .venv/bin/activate && ada ingest-rss >> data/logs/ingest-rss.log 2>&1
15 6,18 * * * cd /home/pi/ADA && . .venv/bin/activate && ada triage >> data/logs/triage.log 2>&1
45 6,18 * * * cd /home/pi/ADA && . .venv/bin/activate && ada extract-graph-lite >> data/logs/extract-graph-lite.log 2>&1

# Matrix (real enqueues need ADA_MATRIX_ENABLE=1)
30 7 * * * cd /home/pi/ADA && . .venv/bin/activate && ada matrix-scan >> data/logs/matrix-scan.log 2>&1

# Optional mission tick (rate-limited inside ADA)
17 * * * * cd /home/pi/ADA && . .venv/bin/activate && ada mission tick --mission YOUR_SLUG >> data/logs/mission-tick.log 2>&1

# Dream (requires GEMINI_API_KEY)
30 23 * * * cd /home/pi/ADA && . .venv/bin/activate && ada dream >> data/logs/dream.log 2>&1
```

See `docs/operator-runbook-raspberry-pi.md` and `ops/schedule.md` for full matrices and mission-parameterized duplicates.
"""


def init_session():
    if "last_ada_run" not in st.session_state:
        st.session_state.last_ada_run = None


def sidebar_config():
    st.sidebar.title("ADA control panel")
    st.sidebar.caption("**[dashboard only]** inspection + safe whitelisted `ada` runs.")

    repo_default = Path(__file__).resolve().parent.parent
    repo_root = Path(st.sidebar.text_input("ADA repo root", value=str(repo_default))).expanduser()

    env_path = Path(
        st.sidebar.text_input(".env path", value=str(repo_root / ".env"))
    ).expanduser()

    if load_dotenv and env_path.is_file():
        load_dotenv(env_path, override=False)

    dotenv_local = parse_dotenv_file(env_path) if env_path.is_file() else {}

    data_override = st.sidebar.text_input(
        "ADA_DATA_DIR override (optional)",
        value="",
        help="Leave empty to use ADA_DATA_DIR from environment or `<repo>/data`.",
    )
    if data_override.strip():
        data_dir = Path(data_override.strip()).expanduser()
        if not data_dir.is_absolute():
            data_dir = (repo_root / data_dir).resolve()
        data_dir = data_dir.resolve()
    else:
        data_dir = resolve_data_dir(repo_root, dotenv_hints=dotenv_local)

    state_db = resolve_state_db_path(data_dir)

    ada_bin = st.sidebar.text_input("ADA binary", value="ada").strip() or "ada"

    mission_filter = st.sidebar.text_input(
        "Mission slug filter (optional)",
        value="",
        help="Filters SQL previews and `--mission` on goal list.",
    ).strip()

    costs_days = st.sidebar.number_input("Costs window (days)", min_value=1, max_value=366, value=7)

    st.sidebar.markdown(
        "---\n"
        "**Paths**\n\n"
        f"- `state.db`: `{state_db}`\n"
        f"- `memory/` (hint): `{resolve_memory_dir(repo_root, dotenv_hints=dotenv_local)}`"
    )

    return {
        "repo_root": repo_root,
        "env_path": env_path,
        "data_dir": data_dir,
        "state_db": state_db,
        "ada_bin": ada_bin,
        "mission_filter": mission_filter,
        "costs_days": int(costs_days),
        "dotenv_local": dotenv_local,
    }


def db_conn_or_none(path: Path):
    try:
        return connect_ro(path)
    except Exception as e:
        st.error(f"Cannot open read-only DB: {e}")
        return None


def tab_overview(cfg, conn):
    st.subheader("Overview")
    st.markdown(
        "**Correlation:** `tasks.id` = session / task id; `workflows.id` = workflow id; "
        "`workflows.parent_task_id` links to `tasks`."
    )
    if conn is None:
        return
    stats = overview_stats(conn, cfg["mission_filter"] or None)
    c1, c2, c3 = st.columns(3)
    c1.metric("Missions", stats.get("missions", 0))
    if "tasks_filtered" in stats:
        c2.metric("Tasks (mission filter)", stats["tasks_filtered"])
    else:
        c2.metric("Tasks (all)", sum(stats.get("tasks_by_status", {}).values()))
    if "workflows_by_status" in stats:
        c3.metric("Workflows", sum(stats["workflows_by_status"].values()))
    st.write("**Tasks by status:**", stats.get("tasks_by_status", {}))
    if "workflows_by_status" in stats:
        st.write("**Workflows by status:**", stats["workflows_by_status"])
    if stats.get("recent_workflows"):
        st.dataframe(stats["recent_workflows"], use_container_width=True)


def tab_missions_tasks(cfg, conn):
    st.subheader("Missions & tasks")
    if conn is None:
        return
    missions, tasks = missions_tasks_preview(conn, cfg["mission_filter"] or None)
    st.write("**Missions**")
    st.dataframe(missions, use_container_width=True)
    st.write("**Recent tasks** (pending / failed are operator-hot)")
    st.dataframe(tasks, use_container_width=True)


def tab_sqlite_sandbox(cfg, conn):
    st.subheader("SQLite — SELECT sandbox")
    st.caption("Single `SELECT` or `WITH … SELECT` only; no writes, no `ATTACH`.")
    if conn is None:
        return
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = [r[0] for r in cur.fetchall()]
    st.multiselect("Tables (reference)", tables, disabled=True, key="tbl_ref")
    q = st.text_area("SQL", height=120, placeholder="SELECT * FROM missions LIMIT 10")
    if st.button("Run SELECT", key="run_select"):
        ok, err = validate_select_only(q)
        if not ok:
            st.error(err)
        else:
            try:
                rows = run_safe_select(conn, q)
                st.success(f"{len(rows)} row(s)")
                if rows:
                    st.dataframe(rows, use_container_width=True)
            except Exception as e:
                st.exception(e)


def tab_commands(cfg):
    st.subheader("Commands")
    st.markdown("Whitelisted `ada` runs only; `cwd` = repo root.")

    cmd_ids = list(WHITELIST_META.keys())
    labels = {k: WHITELIST_META[k].label for k in cmd_ids}
    choice = st.selectbox("Command", cmd_ids, format_func=lambda x: labels[x])
    meta = WHITELIST_META[choice]
    st.info(
        f"**Writes DB:** {meta.writes_db} · **Network:** {meta.needs_network} · "
        f"**Gemini:** {meta.needs_gemini}\n\n{meta.notes}"
    )

    mission_slug = cfg["mission_filter"] or st.text_input(
        "--mission (optional, some commands)", value="", key="cmd_mission"
    )
    mission_show_slug = st.text_input("mission show slug", value="", key="mshow_slug")
    workflow_id = st.number_input("workflow id", min_value=1, value=1, step=1)
    goal_status = st.text_input("goal --status", value="", key="g_status")
    goal_limit = st.number_input("goal/mission list limit", 1, 500, 50)
    gate_lim = st.number_input("gate-failures --limit", 1, 500, 50)
    gate_all = st.checkbox("gate-failures --all-kinds")
    mx_det = st.checkbox("matrix-scan --deterministic")

    if st.button("Run command", type="primary"):
        try:
            argv = build_argv(
                cfg["ada_bin"],
                command_id=choice,
                mission_slug=mission_slug if mission_slug else None,
                mission_show_slug=mission_show_slug,
                goal_status=goal_status or None,
                goal_limit=int(goal_limit),
                mission_limit=int(goal_limit),
                workflow_id=int(workflow_id),
                gate_failures_limit=int(gate_lim),
                gate_failures_all_kinds=gate_all,
                matrix_deterministic=mx_det,
            )
        except ValueError as e:
            st.error(str(e))
            return
        with st.spinner("Running…"):
            res = run_ada(argv, cwd=cfg["repo_root"])
        st.session_state.last_ada_run = res
        with st.expander("stdout", expanded=True):
            st.code(res.stdout or "(empty)", language="text")
        with st.expander("stderr"):
            st.code(res.stderr or "(empty)", language="text")
        st.caption(f"exit code: {res.returncode}")

    with st.expander("Cron cookbook (copy-paste)"):
        st.markdown(CRON_COOKBOOK)


def tab_env(cfg):
    st.subheader("Env checklist")
    ex_path = cfg["repo_root"] / ".env.example"
    example_keys = keys_from_env_example(ex_path)
    if not example_keys:
        st.warning(f"No keys parsed from `{ex_path}` (file missing?).")
    user_keys = parse_dotenv_file(cfg["env_path"])
    missing = [k for k in example_keys if k not in user_keys]
    empty = [k for k in example_keys if k in user_keys and user_keys[k].strip() == ""]

    st.write("**Missing keys** (in `.env.example` but absent from `.env`):", missing or "(none)")
    st.write("**Empty values** (key present but blank):", empty or "(none)")

    st.markdown("**Smoke checklist (convention)** — not enforced by ADA in this app:")
    for k in SMOKE_REQUIRED_KEYS:
        v = user_keys.get(k, "")
        st.write(f"- `{k}`: {'set' if v.strip() else '**missing/empty**'}")

    extra = sorted(set(user_keys) - set(example_keys))
    if extra:
        st.caption(f"Keys in `.env` not listed in `.env.example`: {', '.join(extra[:40])}")


def tab_costs(cfg, conn):
    st.subheader("Costs (usage_ledger)")
    if conn is None:
        return
    if not table_exists(conn, "usage_ledger"):
        st.info("`usage_ledger` table not present.")
        return
    rows, totals = costs_aggregate(conn, cfg["costs_days"])
    st.caption(f"Last **{totals.get('days', cfg['costs_days'])}** day(s), read-only.")
    st.metric("Total tokens (in+out)", totals.get("tokens", 0))
    if rows:
        st.dataframe(rows, use_container_width=True)


def tab_raw_logs():
    st.subheader("Raw logs — last subprocess")
    r: AdaRunResult | None = st.session_state.get("last_ada_run")
    if not r:
        st.info("No subprocess run yet from the Commands or Observability tabs.")
        return
    st.code(format_result_for_logs(r), language="text")


def tab_chat_modes():
    st.subheader("Chat modes (documentation)")
    st.markdown(
        """
**[dashboard only]** Until ADA supports mission-scoped chat from the CLI:

- **Global chat:** `ada chat` today — system text from `build_system_instruction` using `memory/soul.md` and `memory/master.md`. Knowledge tools are **unscoped** unless the backing `tasks` row has `mission_id` set.
- **Future:** `ada chat --mission SLUG` — **[needs ADA change]** (e.g. `insert_task(..., mission_id=...)` + CLI flag).

Use the checkbox below only as a local reminder (Streamlit session); it does not write to SQLite.
        """
    )
    st.checkbox("Track mission chat as backlog item (local note only)", key="backlog_note")


def tab_persona_ops():
    st.subheader("Persona vs ops LLM (design note)")
    st.markdown(
        """
**[dashboard only]** Design split (see repo source for today’s behavior):

- **Operator legs** (`ada chat`, `ada daemon`): `build_system_instruction` in `src/ada/prompt.py` — trusted harness + `<master>` + `<user_soul>`; `worker_mode=True` adds the worker note (`src/ada/main.py`).
- **Batch / enrich / extraction-style legs:** `build_llm_context` in `src/ada/llm_context.py` — policy + `memory/intent.md` merge; **no soul block** on those paths today.
- Strict “ops-only, zero persona” everywhere internal — **[needs ADA change]** / orchestrator prompt split.

**Open in editor (paths only):**
- `src/ada/prompt.py`
- `src/ada/main.py`
- `src/ada/llm_context.py`
        """
    )
    st.code(
        "Operator (chat/daemon)  -->  build_system_instruction (soul + master)\n"
        "Batch enrich / extract     -->  build_llm_context (intent + policy)\n",
        language="text",
    )


def tab_observability(cfg, conn):
    st.subheader("Observability")
    st.markdown(
        "**[dashboard only]** DB reads below. Whitelisted probes use the same subprocess guard as Commands."
    )
    if conn is None:
        return

    ms = (cfg["mission_filter"] or "").strip()
    lim = 25
    try:
        if table_exists(conn, "workflows"):
            if ms and table_exists(conn, "missions"):
                wq = """SELECT w.id, w.kind, w.status, w.parent_task_id, w.mission_id, m.slug AS mission_slug,
                          w.created_at
                          FROM workflows w
                          LEFT JOIN missions m ON m.id = w.mission_id
                          WHERE m.slug = ?
                          ORDER BY w.id DESC LIMIT ?"""
                wf_rows = run_safe_select(conn, wq, params=(ms, lim))
            else:
                wq = """SELECT w.id, w.kind, w.status, w.parent_task_id, w.mission_id,
                          w.created_at
                          FROM workflows w
                          ORDER BY w.id DESC LIMIT ?"""
                wf_rows = run_safe_select(conn, wq, params=(lim,))
            st.write("**Recent workflows**")
            st.dataframe(wf_rows, use_container_width=True)
            if table_exists(conn, "workflow_steps"):
                sq = """SELECT ws.id, ws.workflow_id, ws.step_index, ws.step_type, ws.status, ws.error,
                          ws.updated_at
                          FROM workflow_steps ws
                          ORDER BY ws.id DESC LIMIT ?"""
                st.write("**Recent workflow steps**")
                st.dataframe(run_safe_select(conn, sq, params=(lim,)), use_container_width=True)
    except Exception as e:
        st.exception(e)

    kind_like = st.text_input("action_log kind contains", value="", key="alog_kind")

    cols = st.columns(2)
    with cols[0]:
        if st.button("Refresh failed workflow steps"):
            st.session_state.obs_fail_steps = observability_preset_failed_steps(conn, 80)
    with cols[1]:
        if st.button("Refresh action_log slice"):
            st.session_state.obs_alog = observability_action_recent(
                conn,
                kinds_like=kind_like or None,
                mission_slug=cfg["mission_filter"] or None,
                limit=100,
            )

    if "obs_fail_steps" in st.session_state:
        st.write("**Failed workflow steps**")
        st.dataframe(st.session_state.obs_fail_steps, use_container_width=True)

    if "obs_alog" in st.session_state:
        st.write("**Recent action_log**")
        st.dataframe(st.session_state.obs_alog, use_container_width=True)

    if st.button("Run: failed tasks + gate-failures snapshot", key="obs_goals_gate"):
        try:
            fq = """SELECT id, status, task_kind, mission_id, substr(goal,1,120) AS goal_preview
                    FROM tasks WHERE status = 'failed' ORDER BY id DESC LIMIT 40"""
            failed_tasks = run_safe_select(conn, fq)
            st.write("**Failed tasks**")
            st.dataframe(failed_tasks, use_container_width=True)
        except Exception as e:
            st.exception(e)

        argv = build_argv(cfg["ada_bin"], command_id="gate_failures", gate_failures_limit=30)
        res = run_ada(argv, cwd=cfg["repo_root"])
        st.session_state.last_ada_run = res
        with st.expander("gate-failures stderr"):
            st.code(res.stderr, language="text")
        with st.expander("gate-failures stdout"):
            st.code(res.stdout, language="text")

    st.markdown("#### Whitelisted subprocess (observability)")
    obs_cmd = st.selectbox(
        "Probe",
        ("workflow_status", "gate_failures", "mission_tick_dry_run", "matrix_scan_dry_run"),
        key="obs_which",
    )
    wf_id_obs = st.number_input("workflow id (for status)", 1, 10_000_000, 1, key="wf_obs")
    if st.button("Run observability probe"):
        try:
            if obs_cmd == "workflow_status":
                argv = build_argv(
                    cfg["ada_bin"],
                    command_id="workflow_status",
                    workflow_id=int(wf_id_obs),
                )
            elif obs_cmd == "gate_failures":
                argv = build_argv(cfg["ada_bin"], command_id="gate_failures")
            elif obs_cmd == "mission_tick_dry_run":
                sl = cfg["mission_filter"] or ""
                argv = build_argv(
                    cfg["ada_bin"], command_id="mission_tick_dry_run", mission_slug=sl or None
                )
            elif obs_cmd == "matrix_scan_dry_run":
                argv = build_argv(
                    cfg["ada_bin"],
                    command_id="matrix_scan_dry_run",
                    mission_slug=cfg["mission_filter"] or None,
                    matrix_deterministic=True,
                )
            else:
                return
        except ValueError as e:
            st.error(str(e))
            return
        res = run_ada(argv, cwd=cfg["repo_root"])
        st.session_state.last_ada_run = res
        st.code(format_result_for_logs(res), language="text")


def tab_schedules_audit(cfg):
    st.subheader("Schedules audit")
    st.caption(
        "**[dashboard only]** Parsed from ```cron``` / ```bash``` fences. "
        "Dream/timer: infer from docs or systemd — no timer manifest in repo."
    )
    paths = [
        cfg["repo_root"] / "ops" / "schedule.md",
        cfg["repo_root"] / "docs" / "operator-runbook-raspberry-pi.md",
    ]
    all_rows: list[dict] = []
    for p in paths:
        if not p.is_file():
            continue
        rows = parse_markdown_schedules(p.read_text(encoding="utf-8", errors="replace"))
        for r in rows:
            all_rows.append(
                {
                    "section": r.section,
                    "cron_schedule": r.cron_schedule,
                    "line_raw": r.line_raw,
                    "ada_subcommands": list(r.ada_subcommands),
                    "scripts": list(r.scripts),
                    "source_file": str(p),
                }
            )
    if not all_rows:
        st.warning("No schedule rows parsed.")
    else:
        st.dataframe(all_rows, use_container_width=True)
        for msg, a, b in _fix_overlap_call(all_rows):
            st.warning(f"{msg}\n- {a}\n- {b}")

    cr = st.text_area("Paste crontab -l", height=120, key="crontab_paste")
    if st.button("Compare ada subcommands", key="cmp_cr"):
        md_cmds: set[str] = set()
        for r in all_rows:
            md_cmds.update(r["ada_subcommands"])
        ct_cmds = crontab_ada_commands(cr)
        st.write("**In pasted crontab:**", sorted(ct_cmds))
        st.write("**In markdown:**", sorted(md_cmds))
        st.write("**Intersection:**", sorted(ct_cmds & md_cmds))
        st.write("**Crontab-only:**", sorted(ct_cmds - md_cmds))


def _fix_overlap_call(all_rows: list):
    """Build ScheduleRow-like list for heuristic."""
    from lib.schedule_audit import ScheduleRow

    out: list[ScheduleRow] = []
    for d in all_rows:
        out.append(
            ScheduleRow(
                section=d["section"],
                cron_schedule=d["cron_schedule"],
                line_raw=d["line_raw"],
                ada_subcommands=tuple(d["ada_subcommands"]),
                scripts=tuple(d["scripts"]),
            )
        )
    return overlap_heuristic(out)


def main():
    init_session()
    cfg = sidebar_config()

    tabs = st.tabs(
        [
            "Overview",
            "Missions & tasks",
            "SQLite",
            "Commands",
            "Env",
            "Costs",
            "Raw logs",
            "Chat modes",
            "Persona vs ops",
            "Observability",
            "Schedules audit",
        ]
    )

    if not cfg["state_db"].is_file():
        st.warning(f"`state.db` not found at `{cfg['state_db']}`. Tabs using DB will show errors.")

    conn = db_conn_or_none(cfg["state_db"]) if cfg["state_db"].is_file() else None
    try:
        with tabs[0]:
            tab_overview(cfg, conn)
        with tabs[1]:
            tab_missions_tasks(cfg, conn)
        with tabs[2]:
            tab_sqlite_sandbox(cfg, conn)
        with tabs[3]:
            tab_commands(cfg)
        with tabs[4]:
            tab_env(cfg)
        with tabs[5]:
            tab_costs(cfg, conn)
        with tabs[6]:
            tab_raw_logs()
        with tabs[7]:
            tab_chat_modes()
        with tabs[8]:
            tab_persona_ops()
        with tabs[9]:
            tab_observability(cfg, conn)
        with tabs[10]:
            tab_schedules_audit(cfg)
    finally:
        if conn is not None:
            conn.close()

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        "**Memory files (paths only)** — open in your editor; this app does not write them.\n\n"
        f"- `{resolve_memory_dir(cfg['repo_root'], dotenv_hints=cfg['dotenv_local']) / 'soul.md'}`\n"
        f"- `{resolve_memory_dir(cfg['repo_root'], dotenv_hints=cfg['dotenv_local']) / 'master.md'}`\n"
        f"- `{resolve_memory_dir(cfg['repo_root'], dotenv_hints=cfg['dotenv_local']) / 'intent.md'}` (batch context)"
    )


if __name__ == "__main__":
    main()
