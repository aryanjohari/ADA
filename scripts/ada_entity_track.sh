#!/usr/bin/env bash
# Entity track: RSS → triage → graph-lite extract → matrix-scan (enqueues publish_entity_v1).
# Prerequisites: .env with GEMINI_API_KEY (triage, extract-graph-lite); ADA_MATRIX_ENABLE=1 for real enqueues.
# Usage: set ADA_REPO_ROOT to repo root, or run from repo after chmod +x.
set -euo pipefail

ROOT="${ADA_REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
cd "$ROOT"

if [[ -f "${ROOT}/.venv/bin/activate" ]]; then
  # shellcheck source=/dev/null
  source "${ROOT}/.venv/bin/activate"
fi

ada ingest-rss
ada triage
ada extract-graph-lite
# GATE applies only to publish_entity_v1 (not publish_keyword_v1). matrix-scan enqueues publish_entity_v1.
ada matrix-scan
