"""Entry for Streamlit operator UI (bootstrap + observability): run from repo root:

    streamlit run scripts/ada_observability_app.py

Requires: pip install -e '.[streamlit]' (or ada[streamlit]). Optional: python-dotenv for sidebar .env loading.
"""

from ada.observability.app import run_app

run_app()
