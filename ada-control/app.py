"""
Compatibility entry for the unified operator UI in ``ada.observability``.

Prefer from repo root:

    pip install -e '.[streamlit]'
    streamlit run scripts/ada_observability_app.py

This file delegates to the same implementation so existing ``streamlit run ada-control/app.py`` flows keep working.
"""

from __future__ import annotations

from ada.observability.app import run_app

run_app()
