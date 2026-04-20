#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-/home/pi/ADA}"
VENV_ACTIVATE="${VENV_ACTIVATE:-$REPO_DIR/.venv/bin/activate}"
LOG_DIR="${LOG_DIR:-$REPO_DIR/data/logs}"
LOCK_DIR="${LOCK_DIR:-$REPO_DIR/data/locks}"
LOCK_FILE="$LOCK_DIR/nightly-meta.lock"

META_PROMPT="[META_SYNTH_24H] Review all new synthesis_edges and knowledge_synthesis records created in the last 24h. Merge isolated events into broader NZ market momentum, supply/demand gaps, and actionable Apex OS lead-generation opportunities. Produce one highly compressed consolidated summary for the 23:30 ada dream run. If there are no new rows in the last 24h, output a short 'no material updates' summary and exit normally (no failure). Hard output limit: maximum 600 words."
META_PLAN_JSON='{"ops_job":"nightly_meta_synthesis","tier":"meta","window_hours":24,"output_word_cap":600,"target_consumer":"ada_dream_2330"}'

install_cron() {
  mkdir -p "$LOG_DIR" "$LOCK_DIR"

  local tmp
  tmp="$(mktemp)"
  {
    echo "CRON_TZ=Pacific/Auckland"
    echo "0 */2 * * * cd $REPO_DIR && . $VENV_ACTIVATE && ada ingest-rss >> $LOG_DIR/ingest-rss.log 2>&1"
    echo "15 */2 * * * cd $REPO_DIR && . $VENV_ACTIVATE && ada triage >> $LOG_DIR/triage.log 2>&1"
    echo "0 23 * * * cd $REPO_DIR && . $VENV_ACTIVATE && $REPO_DIR/ops/setup_cron.sh nightly-meta >> $LOG_DIR/nightly-meta.log 2>&1"
    echo "30 23 * * * cd $REPO_DIR && . $VENV_ACTIVATE && ada dream >> $LOG_DIR/dream.log 2>&1"
  } >"$tmp"

  crontab "$tmp"
  rm -f "$tmp"
  echo "Installed ADA cron schedule."
  crontab -l
}

nightly_meta() {
  mkdir -p "$LOG_DIR" "$LOCK_DIR"

  if [ -f "$LOCK_FILE" ]; then
    echo "nightly-meta: lock exists at $LOCK_FILE; skipping enqueue."
    exit 0
  fi

  touch "$LOCK_FILE"
  trap 'rm -f "$LOCK_FILE"' EXIT

  # Idempotency check: skip if today's pending/running/completed meta goal already exists.
  if ada goal list --limit 200 | rg -q "META_SYNTH_24H"; then
    echo "nightly-meta: existing META_SYNTH_24H goal detected; skipping enqueue."
    exit 0
  fi

  ada goal add "$META_PROMPT" --plan-json "$META_PLAN_JSON"
  echo "nightly-meta: enqueued META_SYNTH_24H goal."
}

usage() {
  cat <<'EOF'
Usage:
  ops/setup_cron.sh install-cron
  ops/setup_cron.sh nightly-meta

Environment overrides:
  REPO_DIR, VENV_ACTIVATE, LOG_DIR, LOCK_DIR
EOF
}

main() {
  local cmd="${1:-}"
  case "$cmd" in
    install-cron) install_cron ;;
    nightly-meta) nightly_meta ;;
    *) usage; exit 2 ;;
  esac
}

main "$@"
