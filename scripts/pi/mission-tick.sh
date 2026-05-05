#!/usr/bin/env bash
# Run `ada mission tick` for a mission using schedule_hint_json (rate-limited in DB).
#
# Env:
#   MISSION_SLUG — required unless passed as first argument (non-option).
#   ADA_PI_TICK_DRY_RUN=1 — print due jobs only; no writes.
#   ADA_PI_TICK_FORCE=1 — run every scheduled job ignoring min_interval.
#   ADA_PI_SCRIPT_HELP_FIRST=1 — show `ada mission tick --help` and exit 0 (no tick).
#
# Usage:
#   MISSION_SLUG=my-site ./scripts/pi/mission-tick.sh
#   ./scripts/pi/mission-tick.sh my-site
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/_lib.sh"

ada_pi_resolve_root
ada_pi_bootstrap_cli

slug="${MISSION_SLUG:-}"
if [[ "${#}" -gt 0 ]]; then
  case "${1}" in -*) ;; *) slug="$1"; shift ;; esac
fi
if [[ -z "${slug}" ]]; then
  echo "mission-tick.sh: set MISSION_SLUG or pass slug as first argument." >&2
  exit 2
fi

if [[ "${ADA_PI_SCRIPT_HELP_FIRST:-0}" == "1" ]]; then
  exec ada mission tick --help
fi

TICK_CMD=(mission tick --mission "${slug}")
if [[ "${ADA_PI_TICK_DRY_RUN:-0}" == "1" ]]; then
  TICK_CMD+=(--dry-run)
fi
if [[ "${ADA_PI_TICK_FORCE:-0}" == "1" ]]; then
  TICK_CMD+=(--force)
fi

echo "mission-tick: ada ${TICK_CMD[*]}"
exec ada "${TICK_CMD[@]}"
