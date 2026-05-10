"""Operator bootstrap + observability Streamlit panels (tabs)."""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from pathlib import Path
from typing import Any

import streamlit as st

from ada.config import resolve_runtime_paths_from_environ
from ada.observability.audit_log import append_operator_action_log
from ada.observability.db_ro import (
    connect_ro,
    costs_aggregate,
    missions_tasks_preview,
    observability_action_recent,
    observability_preset_failed_steps,
    overview_stats,
    run_safe_select,
    table_exists,
)
from ada.observability.env_wizard import (
    build_environment_file_snippet,
    keys_from_env_example,
    merge_dotenv_into_environ,
    parse_dotenv_file,
    validate_paths_and_env,
)
from ada.observability.memory_files import (
    DEFAULT_BOOTSTRAP_BASENAMES,
    list_bootstrap_files,
    memory_write_allowed,
    resolve_memory_bootstrap_file,
)
from ada.observability.operator_subprocess import AdaRunResult, format_result_for_logs, run_ada
from ada.observability.operator_whitelist import WHITELIST_META, build_argv
from ada.observability.profile_snippets import list_profile_slugs
from ada.observability.queries import (
    action_log_recent,
    open_readonly_connection,
    task_status_counts,
    tasks_pending_failed,
    usage_by_session_and_kind,
    usage_rollup_by_iso_week,
    usage_rollup_by_utc_day,
    usage_today_month_totals,
    web_source_counts_by_week,
    workflow_status_counts,
    workflow_steps_recent,
    workflows_recent,
)
from ada.observability.schedule_audit import ScheduleRow, overlap_heuristic, parse_markdown_schedules
from ada.observability.sql_guard import validate_select_only


def _json_pretty(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, default=str)


def _flatten_for_df(row: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in row.items():
        if isinstance(v, (dict, list)):
            out[k] = json.dumps(v, ensure_ascii=False, default=str)
        else:
            out[k] = v
    return out


def _path_digest(path: Path) -> str:
    try:
        s = str(path.resolve())
    except OSError:
        s = str(path)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:24]


def _env_caps_from_merged(merged: dict[str, str]) -> dict[str, str | None]:
    def g(name: str) -> str | None:
        v = str(merged.get(name, "")).strip()
        return v if v else None

    return {
        "ADA_DATA_DIR": g("ADA_DATA_DIR"),
        "ADA_COMMERCIAL_DATA_DIR": g("ADA_COMMERCIAL_DATA_DIR"),
        "ADA_PROFILE": g("ADA_PROFILE"),
        "ADA_PROFILE_DATA_ROOT": g("ADA_PROFILE_DATA_ROOT"),
        "ADA_MEMORY_DIR": g("ADA_MEMORY_DIR"),
        "ADA_POLICY_ROOT": g("ADA_POLICY_ROOT"),
        "ADA_DAILY_TOKEN_BUDGET": g("ADA_DAILY_TOKEN_BUDGET"),
        "ADA_MONTHLY_TOKEN_BUDGET": g("ADA_MONTHLY_TOKEN_BUDGET"),
        "ADA_KILL_SWITCH": g("ADA_KILL_SWITCH"),
        "ADA_MAX_TASK_STEPS": g("ADA_MAX_TASK_STEPS"),
        "ADA_WEB_FETCH_MAX_URLS": g("ADA_WEB_FETCH_MAX_URLS"),
        "ADA_BRAND_INGEST_MAX_URLS": g("ADA_BRAND_INGEST_MAX_URLS"),
        "ADA_REQUIRE_PROFILE_ISOLATION": g("ADA_REQUIRE_PROFILE_ISOLATION"),
    }


def _init_session() -> None:
    if "last_ada_run" not in st.session_state:
        st.session_state.last_ada_run = None


def build_sidebar_config() -> dict[str, Any]:
    _init_session()
    st.sidebar.title("Ada operator")
    st.sidebar.caption(
        "Not the agent: no orchestrator socket. Mutations = whitelisted `ada` argv, "
        "memory files under resolved memory_dir, or audit rows in action_log."
    )

    try:
        from dotenv import load_dotenv
    except ImportError:
        load_dotenv = None  # type: ignore[misc]

    repo_default = Path.cwd()
    py = Path(__file__).resolve()
    for parent in [py.parent, *py.parents]:
        if (parent / "pyproject.toml").exists():
            repo_default = parent
            break

    repo_root = Path(
        st.sidebar.text_input("ADA repo root", value=str(repo_default))
    ).expanduser().resolve()

    env_path = Path(
        st.sidebar.text_input(".env path", value=str(repo_root / ".env"))
    ).expanduser()

    dotenv_parsed: dict[str, str] = {}
    if env_path.is_file():
        dotenv_parsed = parse_dotenv_file(env_path)
    if load_dotenv is not None and env_path.is_file():
        load_dotenv(env_path, override=False)

    merged_environ = merge_dotenv_into_environ(os.environ, dotenv_parsed)

    rp = None
    rp_error: str | None = None
    try:
        rp = resolve_runtime_paths_from_environ(
            project_root=repo_root,
            environ=merged_environ,
            warn_policy_fallback=False,
        )
    except ValueError as e:
        rp_error = str(e)

    state_db = rp.state_db_path if rp else (repo_root / "data" / "state.db").resolve()

    ada_bin = st.sidebar.text_input("ADA binary", value="ada").strip() or "ada"
    mission_filter = st.sidebar.text_input(
        "Mission slug filter (optional)",
        value="",
        help="Filters some SQL previews and optional --mission on commands.",
    ).strip()
    costs_days = st.sidebar.number_input("Costs window (days)", min_value=1, max_value=366, value=7)

    st.sidebar.markdown("---")
    st.sidebar.subheader("Resolved paths")
    if rp_error:
        st.sidebar.error(rp_error)
    elif rp:
        st.sidebar.code(f"state.db\n{state_db}", language="text")
        st.sidebar.code(f"memory_dir\n{rp.memory_dir}", language="text")
        st.sidebar.code(f"policy_root\n{rp.policy_root}", language="text")

    return {
        "repo_root": repo_root,
        "env_path": env_path,
        "dotenv_parsed": dotenv_parsed,
        "merged_environ": merged_environ,
        "state_db_path": state_db,
        "ada_bin": ada_bin,
        "mission_filter": mission_filter,
        "costs_days": int(costs_days),
        "rp": rp,
        "rp_error": rp_error,
    }


def _try_audit(cfg: dict[str, Any], payload: dict[str, Any]) -> None:
    rid = append_operator_action_log(cfg["state_db_path"], payload)
    if rid is None and cfg["state_db_path"].is_file():
        st.warning("Could not write operator audit row (database busy or missing action_log).")


def render_setup_tab(cfg: dict[str, Any]) -> None:
    st.subheader("Setup")
    st.markdown(
        "- [Operator onboarding](docs/operator-onboarding.md) — profile → mission → playbook.\n"
        "- [README §9.0a](README.md) — multi-tenant profiles.\n"
        "- **Streamlit cannot set shell exports** for new terminals; use generated EnvironmentFile / `source`."
    )
    rp = cfg["rp"]
    if rp:
        st.json(
            {
                "data_dir": str(rp.data_dir),
                "memory_dir": str(rp.memory_dir),
                "policy_root": str(rp.policy_root),
                "require_profile_isolation": rp.require_profile_isolation,
                "active_profile_slug": rp.active_profile_slug,
                "policy_used_repo_fallback": rp.policy_used_repo_fallback,
                "profile_fingerprint": rp.profile_fingerprint,
            }
        )
    elif cfg["rp_error"]:
        st.error(cfg["rp_error"])

    with st.expander("Schedules audit (markdown docs)", expanded=False):
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
            st.info("No schedule rows parsed from known docs.")
        else:
            st.dataframe(all_rows, use_container_width=True)
            for msg, a, b in _fix_overlap_call(all_rows):
                st.warning(f"{msg}\n- {a}\n- {b}")

        cr = st.text_area("Paste crontab -l", height=100, key="crontab_paste_setup")
        if st.button("Compare ada subcommands", key="cmp_cr_setup"):
            from ada.observability.schedule_audit import crontab_ada_commands

            md_cmds: set[str] = set()
            for r in all_rows:
                md_cmds.update(r["ada_subcommands"])
            ct_cmds = crontab_ada_commands(cr)
            st.write("**In pasted crontab:**", sorted(ct_cmds))
            st.write("**In markdown:**", sorted(md_cmds))

    st.subheader("SQLite — SELECT sandbox")
    st.caption("Single SELECT or WITH … SELECT only.")
    db_path = cfg["state_db_path"]
    if not db_path.is_file():
        st.info("No state.db — SELECT sandbox and costs disabled until the database exists.")
    else:
        try:
            conn = connect_ro(db_path)
        except Exception as e:
            st.error(str(e))
        else:
            with conn:
                cur = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                )
                tables = [r[0] for r in cur.fetchall()]
                st.multiselect("Tables (reference)", tables, disabled=True, key="tbl_ref_setup")
                q = st.text_area(
                    "SQL",
                    height=100,
                    placeholder="SELECT * FROM missions LIMIT 10",
                    key="sql_setup",
                )
                if st.button("Run SELECT", key="run_select_setup"):
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

        st.subheader("Costs (usage_ledger)")
        try:
            c2 = connect_ro(db_path)
        except Exception:
            pass
        else:
            with c2:
                if not table_exists(c2, "usage_ledger"):
                    st.info("No usage_ledger table.")
                else:
                    rows, totals = costs_aggregate(c2, cfg["costs_days"])
                    st.caption(
                        f"Last **{totals.get('days', cfg['costs_days'])}** day(s), read-only."
                    )
                    st.metric("Total tokens (in+out)", totals.get("tokens", 0))
                    if rows:
                        st.dataframe(rows, use_container_width=True)


def _fix_overlap_call(all_rows: list) -> list:
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


def render_env_tab(cfg: dict[str, Any]) -> None:
    st.subheader("Env wizard")
    ex_path = cfg["repo_root"] / ".env.example"
    example_keys = keys_from_env_example(ex_path)
    user_keys = parse_dotenv_file(cfg["env_path"])
    merged = cfg["merged_environ"]

    if not example_keys:
        st.warning(f"No keys parsed from `{ex_path}`.")
    missing = [k for k in example_keys if k not in user_keys]
    empty = [k for k in example_keys if k in user_keys and user_keys[k].strip() == ""]

    st.write("**Missing keys** (in `.env.example` but absent from sidebar `.env`):", missing or "(none)")
    st.write("**Empty values** (key present but blank):", empty or "(none)")

    publisher_track = st.checkbox("Publisher / S3 track (stricter env checks)", value=False)
    errs, warns = validate_paths_and_env(
        repo_root=cfg["repo_root"],
        merged_environ=merged,
        publisher_track=publisher_track,
    )
    for w in warns:
        st.warning(w)
    for e in errs:
        st.error(e)

    st.subheader("Generate EnvironmentFile snippet")
    st.caption("Does not write secrets. Log this action for audit, then download.")
    slug = st.text_input("Profile slug (for snippet)", value=str(merged.get("ADA_PROFILE", "") or ""))
    pdr = st.text_input(
        "ADA_PROFILE_DATA_ROOT (absolute)",
        value=str(merged.get("ADA_PROFILE_DATA_ROOT", "") or ""),
    )
    mem = st.text_input(
        "ADA_MEMORY_DIR (optional, absolute recommended)",
        value=str(merged.get("ADA_MEMORY_DIR", "") or ""),
    )
    pol = st.text_input(
        "ADA_POLICY_ROOT (optional)",
        value=str(merged.get("ADA_POLICY_ROOT", "") or ""),
    )
    iso = st.selectbox("ADA_REQUIRE_PROFILE_ISOLATION", ("1", "0"), index=0)

    if st.button("Log + prepare EnvironmentFile", key="env_snip_go"):
        aid = str(uuid.uuid4())
        text = build_environment_file_snippet(
            profile_slug=slug.strip() or "your_profile",
            profile_data_root=pdr.strip() or "/var/lib/ada-profiles",
            ada_memory_dir=mem.strip(),
            ada_policy_root=pol.strip(),
            require_isolation=iso,
        )
        st.session_state["env_snippet_text"] = text
        st.session_state["env_snippet_aid"] = aid
        _try_audit(
            cfg,
            {
                "action": "env_snippet_generated",
                "client_action_id": aid,
                "profile": slug.strip() or None,
                "paths": {
                    "profile_data_root_sha256": _path_digest(Path(pdr)) if pdr.strip() else None,
                },
            },
        )
        st.success("Audit row appended (if state.db writable).")

    if st.session_state.get("env_snippet_text"):
        st.code(st.session_state["env_snippet_text"], language="bash")
        st.download_button(
            "Download ada-profile.env fragment",
            st.session_state["env_snippet_text"],
            file_name="ada-profile.env.fragment",
            mime="text/plain",
            key="dl_env_frag",
        )

    st.markdown(
        "**Shell:** `set -a; source /path/to/profile.env; set +a` — then run Streamlit or `ada` from that shell."
    )


def render_profiles_tab(cfg: dict[str, Any]) -> None:
    st.subheader("Profiles")
    st.caption(
        "Discover profiles under ADA_PROFILE_DATA_ROOT. Selecting a name here does not persist; "
        "apply env via systemd EnvironmentFile= or shell exports."
    )
    merged = cfg["merged_environ"]
    root_raw = st.text_input(
        "Scan profile data root",
        value=str(merged.get("ADA_PROFILE_DATA_ROOT", "") or ""),
        key="prof_scan_root",
    )
    if root_raw.strip():
        slugs = list_profile_slugs(Path(root_raw.strip()))
        st.write("**Detected profile directories:**", slugs or "(none or path missing)")
    else:
        st.info("Set ADA_PROFILE_DATA_ROOT to list profile slug directories.")

    st.markdown("---")
    st.subheader("First mission — `ada mission init`")
    st.markdown(
        "See [docs/operator-onboarding.md](docs/operator-onboarding.md) §1 for `defaults_json` examples."
    )
    mslug = st.text_input("Mission slug", key="mw_slug")
    mtitle = st.text_input("Title (required)", key="mw_title")
    mniche = st.text_input("Niche (optional)", key="mw_niche")
    mtopic = st.text_input("Topic (optional)", key="mw_topic")
    mdj = st.text_area("defaults-json (optional object JSON)", height=120, key="mw_dj")
    msj = st.text_area("schedule-hint-json (optional object JSON)", height=80, key="mw_sj")

    st.subheader("Whitelisted CLI")
    cmd_ids = list(WHITELIST_META.keys())
    labels = {k: WHITELIST_META[k].label for k in cmd_ids}
    choice = st.selectbox("Command", cmd_ids, format_func=lambda x: labels[x])
    meta = WHITELIST_META[choice]
    st.info(
        f"**Writes DB:** {meta.writes_db} · **Network:** {meta.needs_network} · "
        f"**Gemini:** {meta.needs_gemini}\n\n{meta.notes}"
    )

    mission_slug = cfg["mission_filter"] or st.text_input(
        "--mission (optional)", value="", key="cmd_mission_pf"
    )
    mission_show_slug = st.text_input("mission show slug", value="", key="mshow_slug_pf")
    workflow_id = st.number_input("workflow id", min_value=1, value=1, step=1)
    goal_status = st.text_input("goal --status", value="", key="g_status_pf")
    goal_limit = st.number_input("goal/mission list limit", 1, 500, 50)
    gate_lim = st.number_input("gate-failures --limit", 1, 500, 50)
    gate_all = st.checkbox("gate-failures --all-kinds")
    mx_det = st.checkbox("matrix-scan --deterministic")
    mig_only = st.text_input("migrate-env --only (comma env names)", value="", key="mig_only_pf")

    if st.button("Run whitelisted command", type="primary", key="run_whitelist_pf"):
        aid = str(uuid.uuid4())
        eff_mission = (cfg["mission_filter"] or mission_slug or mslug or "").strip()
        try:
            if choice == "mission_init":
                argv = build_argv(
                    cfg["ada_bin"],
                    command_id="mission_init",
                    mission_init_slug=mslug,
                    mission_init_title=mtitle,
                    mission_init_niche=mniche,
                    mission_init_topic=mtopic,
                    mission_init_defaults_json=mdj,
                    mission_init_schedule_json=msj,
                )
            elif choice == "mission_migrate_env_dry":
                argv = build_argv(
                    cfg["ada_bin"],
                    command_id="mission_migrate_env_dry",
                    mission_slug=eff_mission if eff_mission else None,
                    mission_migrate_only=mig_only,
                )
            else:
                argv = build_argv(
                    cfg["ada_bin"],
                    command_id=choice,
                    mission_slug=eff_mission if eff_mission else None,
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
            res = run_ada(argv, cwd=cfg["repo_root"], env=dict(cfg["merged_environ"]))
        st.session_state.last_ada_run = res
        payload = {
            "action": "whitelisted_ada",
            "client_action_id": aid,
            "command_id": choice,
            "argv_tokens": argv[:12],
            "exit_code": res.returncode,
        }
        if choice == "mission_init" and mslug.strip():
            payload["paths"] = {"mission_slug_hash": _path_digest(Path(mslug))}
        _try_audit(cfg, payload)
        with st.expander("stdout", expanded=True):
            st.code(res.stdout or "(empty)", language="text")
        with st.expander("stderr"):
            st.code(res.stderr or "(empty)", language="text")
        st.caption(f"exit code: {res.returncode}")

    r: AdaRunResult | None = st.session_state.get("last_ada_run")
    if r:
        with st.expander("Raw subprocess log"):
            st.code(format_result_for_logs(r), language="text")


def render_memory_tab(cfg: dict[str, Any]) -> None:
    st.subheader("Memory files")
    rp = cfg["rp"]
    if not rp:
        st.error("Resolve paths first (fix env / profile errors in sidebar).")
        return
    mem = rp.memory_dir
    st.write(f"**memory_dir:** `{mem}`")
    names = list_bootstrap_files(mem)
    pick = st.selectbox("File", names, format_func=lambda x: x)
    path = resolve_memory_bootstrap_file(mem, pick)

    ok, reason = memory_write_allowed(
        target=path,
        memory_dir=mem,
        project_root=cfg["repo_root"],
        require_profile_isolation=rp.require_profile_isolation,
    )
    if not path.is_file():
        st.info(f"File does not exist yet — you can create it below if writes are allowed.\n`{path}`")

    content = ""
    if path.is_file():
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            st.error(str(e))
            return
    body = st.text_area(f"Edit {pick}", value=content, height=320, key=f"mem_edit_{pick}")
    if not ok:
        st.error(reason)
        st.caption("Copy the path and open in your editor.")
        return

    if st.button("Save (allowlisted path only)", key=f"mem_save_{pick}"):
        aid = str(uuid.uuid4())
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
        except OSError as e:
            st.error(str(e))
            return
        _try_audit(
            cfg,
            {
                "action": "memory_save",
                "client_action_id": aid,
                "paths": {
                    "memory_basename": pick,
                    "path_digest": _path_digest(path),
                },
            },
        )
        st.success("Saved and audit row appended (if DB writable).")

    st.caption(f"Allowlisted basenames: {', '.join(DEFAULT_BOOTSTRAP_BASENAMES)}")


def render_observability_tab(cfg: dict[str, Any]) -> None:
    st.subheader("Observability (read-only SQL)")
    db_path = cfg["state_db_path"]
    if not db_path.is_file():
        st.warning(f"No database at `{db_path}`.")
        return

    caps = _env_caps_from_merged(cfg["merged_environ"])
    with st.expander("Operator hygiene (PII / secrets)", expanded=False):
        st.markdown(
            "- **PII:** do not paste secrets into chat.\n"
            "- **action_log:** filter UI-driven rows: `kind = 'operator_ui_bootstrap'` "
            "(see docs/OPERATOR_LOGGING.md)."
        )

    try:
        conn = open_readonly_connection(db_path)
    except OSError as e:
        st.error(f"Cannot open database (read-only): {e}")
        return

    with conn:
        sub = st.tabs(["Overview", "Tasks", "Workflows", "Usage", "Action log", "Caps / budgets"])

        with sub[0]:
            try:
                c2 = connect_ro(db_path)
            except Exception as e:
                st.error(str(e))
            else:
                with c2:
                    stats = overview_stats(c2, cfg["mission_filter"] or None)
                    st.json(stats)

        with sub[1]:
            st.subheader("Missions & tasks")
            try:
                c2 = connect_ro(db_path)
            except Exception as e:
                st.error(str(e))
            else:
                with c2:
                    missions, tasks = missions_tasks_preview(
                        c2, cfg["mission_filter"] or None
                    )
                    st.dataframe(missions, use_container_width=True)
                    st.dataframe(tasks, use_container_width=True)

        with sub[2]:
            st.subheader("Pending / failed tasks (sanitized)")
            try:
                rows = tasks_pending_failed(conn, limit=200)
                st.dataframe(
                    [_flatten_for_df(r) for r in rows],
                    use_container_width=True,
                    hide_index=True,
                )
                st.subheader("Task status counts")
                st.json(task_status_counts(conn))
            except Exception as e:
                st.exception(e)
            st.subheader("Recent workflows")
            try:
                wf = workflows_recent(conn, limit=80)
                st.dataframe(
                    [_flatten_for_df(r) for r in wf],
                    use_container_width=True,
                    hide_index=True,
                )
                st.json({"workflow_status_counts": workflow_status_counts(conn)})
            except Exception as e:
                st.exception(e)
            st.subheader("Recent workflow steps")
            try:
                st.dataframe(
                    [_flatten_for_df(r) for r in workflow_steps_recent(conn, limit=150)],
                    use_container_width=True,
                    hide_index=True,
                )
            except Exception as e:
                st.exception(e)

            kind_like = st.text_input("action_log kind contains", value="operator_ui", key="alog_kind_obs")
            cols = st.columns(2)
            with cols[0]:
                if st.button("Refresh failed workflow steps", key="obs_fail"):
                    c3 = connect_ro(db_path)
                    with c3:
                        st.session_state.obs_fail_steps = observability_preset_failed_steps(c3, 80)
            with cols[1]:
                if st.button("Refresh action_log slice", key="obs_alog_btn"):
                    c3 = connect_ro(db_path)
                    with c3:
                        st.session_state.obs_alog = observability_action_recent(
                            c3,
                            kinds_like=kind_like or None,
                            mission_slug=cfg["mission_filter"] or None,
                            limit=100,
                        )
            if "obs_fail_steps" in st.session_state:
                st.dataframe(st.session_state.obs_fail_steps, use_container_width=True)
            if "obs_alog" in st.session_state:
                st.dataframe(st.session_state.obs_alog, use_container_width=True)

        with sub[3]:
            st.subheader("Usage rollups (UTC day)")
            try:
                st.dataframe(
                    usage_rollup_by_utc_day(conn, days=14),
                    use_container_width=True,
                )
            except Exception as e:
                st.exception(e)
            st.subheader("Usage rollups (ISO week)")
            try:
                st.dataframe(
                    usage_rollup_by_iso_week(conn, weeks=8),
                    use_container_width=True,
                )
            except Exception as e:
                st.exception(e)
            st.subheader("Top sessions by token volume (no goal text)")
            try:
                st.dataframe(
                    usage_by_session_and_kind(conn, limit_sessions=40),
                    use_container_width=True,
                )
            except Exception as e:
                st.exception(e)
            st.subheader("Web fetch volume (counts by week, no URLs)")
            try:
                st.dataframe(
                    web_source_counts_by_week(conn, weeks=8),
                    use_container_width=True,
                )
            except Exception as e:
                st.exception(e)

        with sub[4]:
            st.subheader("Recent action_log (payloads sanitized)")
            try:
                rows = action_log_recent(conn, limit=120)
                st.dataframe(
                    [
                        {
                            "id": r["id"],
                            "created_at": r["created_at"],
                            "kind": r["kind"],
                            "session_id": r["session_id"],
                            "payload_safe": _json_pretty(r["payload_safe"]),
                        }
                        for r in rows
                    ],
                    use_container_width=True,
                    hide_index=True,
                )
            except Exception as e:
                st.exception(e)

        with sub[5]:
            st.subheader("Effective caps (merged env + process)")
            st.caption(
                "Merged from process environment and sidebar `.env` (dotenv override=False rules). "
                "Never commit API keys."
            )
            st.json(caps)
            st.subheader("Derived usage vs budgets (UTC)")
            try:
                totals = usage_today_month_totals(conn)
                st.json(totals)
                daily = caps.get("ADA_DAILY_TOKEN_BUDGET")
                monthly = caps.get("ADA_MONTHLY_TOKEN_BUDGET")
                if daily:
                    st.metric("Day token total / daily budget", f"{totals['day_total']} / {daily}")
                if monthly:
                    st.metric(
                        "Month token total / monthly budget",
                        f"{totals['month_total']} / {monthly}",
                    )
            except Exception as e:
                st.exception(e)


def render_operator_tabs(cfg: dict[str, Any]) -> None:
    tabs = st.tabs(["Setup", "Env", "Profiles", "Memory", "Observability"])
    with tabs[0]:
        render_setup_tab(cfg)
    with tabs[1]:
        render_env_tab(cfg)
    with tabs[2]:
        render_profiles_tab(cfg)
    with tabs[3]:
        render_memory_tab(cfg)
    with tabs[4]:
        render_observability_tab(cfg)
