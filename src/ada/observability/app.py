"""Streamlit operator UI: bootstrap/setup + read-only observability (optional: pip install ada[streamlit])."""

from __future__ import annotations

import streamlit as st

from ada.observability.operator_streamlit import build_sidebar_config, render_operator_tabs


def run_app() -> None:
    st.set_page_config(
        page_title="Ada operator",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.title("Ada operator")
    st.caption(
        "Dashboard is not the agent: no orchestrator socket or arbitrary shell. "
        "Bind to localhost; use SSH tunnel / firewall in production."
    )

    cfg = build_sidebar_config()
    render_operator_tabs(cfg)


def main() -> None:
    run_app()


if __name__ == "__main__":
    main()
