"""Entry for Streamlit: run from repo root:

    streamlit run scripts/ada_observability_app.py

Requires: pip install -e '.[streamlit]' (or ada[streamlit]).
"""

from ada.observability.app import run_app

run_app()
