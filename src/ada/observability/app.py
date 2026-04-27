"""Streamlit read-only observability UI (optional dependency: pip install ada[streamlit])."""

from __future__ import annotations

import json
import os
from typing import Any

import streamlit as st

from ada.observability.paths import resolve_state_db_path
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


def _env_caps() -> dict[str, str | None]:
    def g(name: str) -> str | None:
        v = os.environ.get(name, "").strip()
        return v if v else None

    return {
        "ADA_DATA_DIR": g("ADA_DATA_DIR"),
        "ADA_COMMERCIAL_DATA_DIR": g("ADA_COMMERCIAL_DATA_DIR"),
        "ADA_PROFILE": g("ADA_PROFILE"),
        "ADA_PROFILE_DATA_ROOT": g("ADA_PROFILE_DATA_ROOT"),
        "ADA_DAILY_TOKEN_BUDGET": g("ADA_DAILY_TOKEN_BUDGET"),
        "ADA_MONTHLY_TOKEN_BUDGET": g("ADA_MONTHLY_TOKEN_BUDGET"),
        "ADA_KILL_SWITCH": g("ADA_KILL_SWITCH"),
        "ADA_MAX_TASK_STEPS": g("ADA_MAX_TASK_STEPS"),
        "ADA_WEB_FETCH_MAX_URLS": g("ADA_WEB_FETCH_MAX_URLS"),
        "ADA_BRAND_INGEST_MAX_URLS": g("ADA_BRAND_INGEST_MAX_URLS"),
        "ADA_REQUIRE_PROFILE_ISOLATION": g("ADA_REQUIRE_PROFILE_ISOLATION"),
    }


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


def run_app() -> None:
    st.set_page_config(
        page_title="Ada observability",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.title("Ada observability (read-only)")
    st.caption(
        "Dashboard is not the agent: no tool execution, no writes, no CLI changes. "
        "Bind to localhost and use SSH tunnel / firewall in production."
    )

    with st.sidebar:
        st.subheader("Data path")
        try:
            db_path = resolve_state_db_path()
            st.code(str(db_path), language="text")
        except ValueError as e:
            st.error(str(e))
            st.stop()

    caps = _env_caps()
    with st.expander("Operator hygiene (PII / secrets)", expanded=False):
        st.markdown(
            "- **PII:** out of scope for this dashboard; do not paste secrets into chat.\n"
            "- **Raw leads:** not stored in Ada today; this UI avoids transcript/`messages`.\n"
            "- **Goal text / payloads:** shown as length + hash or truncated summaries only."
        )

    try:
        conn = open_readonly_connection(db_path)
    except OSError as e:
        st.error(f"Cannot open database (read-only): {e}")
        st.stop()

    with conn:
        tabs = st.tabs(
            [
                "Tasks",
                "Workflows",
                "Usage",
                "Action log",
                "Caps / env",
            ]
        )

        with tabs[0]:
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

        with tabs[1]:
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

        with tabs[2]:
            st.subheader("Usage rollups (UTC day)")
            try:
                st.dataframe(
                    usage_rollup_by_utc_day(conn, days=14),
                    use_container_width=True,
                    hide_index=True,
                )
            except Exception as e:
                st.exception(e)
            st.subheader("Usage rollups (ISO week)")
            try:
                st.dataframe(
                    usage_rollup_by_iso_week(conn, weeks=8),
                    use_container_width=True,
                    hide_index=True,
                )
            except Exception as e:
                st.exception(e)
            st.subheader("Top sessions by token volume (no goal text)")
            try:
                st.dataframe(
                    usage_by_session_and_kind(conn, limit_sessions=40),
                    use_container_width=True,
                    hide_index=True,
                )
            except Exception as e:
                st.exception(e)
            st.subheader("Web fetch volume (counts by week, no URLs)")
            try:
                st.dataframe(
                    web_source_counts_by_week(conn, weeks=8),
                    use_container_width=True,
                    hide_index=True,
                )
            except Exception as e:
                st.exception(e)

        with tabs[3]:
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

        with tabs[4]:
            st.subheader("Effective caps (from environment)")
            st.caption(
                "Values come from the shell environment only (not from .env files unless your "
                "process was started with them). Never commit API keys."
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
            st.markdown(
                "**Follow-up:** per-campaign URLs/week ceilings may need core support; "
                "this panel shows global env caps and aggregate `web_sources` counts only."
            )


def main() -> None:
    run_app()


if __name__ == "__main__":
    main()
