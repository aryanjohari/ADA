#!/usr/bin/env bash
# Post-install smoke: CLI help checks, mission list, optional goal enqueue (no Gemini for goal add).
#
# Env:
#   ADA_PI_SMOKE_DREAM_TEST=1 — also run `ada dream --dry-run` (calls Gemini; does not write memory files).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/_lib.sh"

ada_pi_resolve_root
ada_pi_bootstrap_cli

echo "== ada top-level help =="
ada --help >/dev/null
echo OK

echo "== ada goal --help =="
ada goal --help >/dev/null
echo OK

echo "== ada mission --help =="
ada mission --help >/dev/null
echo OK

echo "== ada ingest-rss --help =="
ada ingest-rss --help >/dev/null
echo OK

echo "== ada ingest-gsc --help =="
ada ingest-gsc --help >/dev/null
echo OK

echo "== ada mission list =="
ada mission list

echo "== ada goal add (SMOKE; no Gemini) =="
ada goal add "[SMOKE] Confirm goal queue wiring (scripts/pi/smoke.sh)."

if [[ "${ADA_PI_SMOKE_DREAM_TEST:-0}" == "1" ]]; then
  echo "== ada dream --dry-run (requires GEMINI_API_KEY; network) =="
  ada dream --dry-run
fi

echo "smoke.sh: finished."
