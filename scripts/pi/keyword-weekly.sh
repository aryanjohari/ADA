#!/usr/bin/env bash
# Thin wrapper around scripts/ada_keyword_track.sh (GSC → keyword-select → publish_keyword_v1 enqueue).
#
# Prerequisites: jq; ADA_ENABLE_GSC_INGEST=1 and GSC_* in .env; keyword env vars documented in ada_keyword_track.sh.
# Env: MISSION_SLUG or ADA_MISSION_SLUG — forwarded to enqueue --mission.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/_lib.sh"

ada_pi_resolve_root
ada_pi_load_dotenv
ada_pi_maybe_venv

KW_SCRIPT="${ROOT}/scripts/ada_keyword_track.sh"
if [[ ! -f "${KW_SCRIPT}" ]]; then
  echo "keyword-weekly.sh: missing ${KW_SCRIPT}" >&2
  exit 1
fi

export ADA_REPO_ROOT="${ROOT}"

echo "keyword-weekly: delegating to scripts/ada_keyword_track.sh"
exec bash "${KW_SCRIPT}"
