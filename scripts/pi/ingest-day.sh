#!/usr/bin/env bash
# Daily RSS ingest (+ optional Search Console ingestion).
#
# Env:
#   MISSION_SLUG — optional; passed as `ada ingest-rss --mission` when set (same meaning as onboarding docs).
#   ADA_ENABLE_GSC_INGEST=1 — also run ingest-gsc (needs GSC_* keys and network).
#   ADA_PI_GSC_DRY_RUN=1 — pass --dry-run to ingest-gsc (no DB writes from GSC path when dry-run clears).
#   ADA_PI_INGEST_HELP_FIRST=1 — print ingest-rss --help before work.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/_lib.sh"

ada_pi_resolve_root
ada_pi_bootstrap_cli

if [[ "${ADA_PI_INGEST_HELP_FIRST:-0}" == "1" ]]; then
  ada ingest-rss --help
fi

RSS_ARGS=(ingest-rss)
if [[ -n "${MISSION_SLUG:-}" ]]; then
  RSS_ARGS+=(--mission "${MISSION_SLUG}")
fi

echo "ingest-day: ada ${RSS_ARGS[*]}"
ada "${RSS_ARGS[@]}"

if [[ "${ADA_ENABLE_GSC_INGEST:-0}" == "1" ]]; then
  GSC_DAYS="${ADA_INGEST_GSC_DAYS:-28}"
  ROW_LIMIT="${ADA_INGEST_GSC_ROW_LIMIT:-25000}"
  GSC_CMD=(ingest-gsc --days "${GSC_DAYS}" --dimensions "date,query,page,country,device" --row-limit "${ROW_LIMIT}")
  if [[ "${ADA_PI_GSC_DRY_RUN:-0}" == "1" ]]; then
    GSC_CMD+=(--dry-run)
    echo "ingest-day: GSC ingest (dry-run)"
  else
    echo "ingest-day: GSC ingest (live; requires credentials + network)"
  fi
  ada "${GSC_CMD[@]}"
else
  echo "ingest-day: skipping GSC (set ADA_ENABLE_GSC_INGEST=1 to enable)."
fi
